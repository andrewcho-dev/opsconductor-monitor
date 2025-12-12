"""
System Alert Service

Provides alert evaluation, management, and notification capabilities.
Evaluates configurable alert rules against system data and manages
alert lifecycle (active -> acknowledged -> resolved).
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from enum import Enum

from backend.database import get_db
from backend.utils.time import now_utc


def _to_utc_iso(ts):
    """Convert timestamp to UTC ISO format with Z suffix."""
    if ts is None:
        return None
    if hasattr(ts, 'astimezone'):
        ts = ts.astimezone(timezone.utc)
    return ts.isoformat().replace('+00:00', 'Z')


class AlertSeverity:
    """Alert severity levels."""
    INFO = 'info'
    WARNING = 'warning'
    CRITICAL = 'critical'


class AlertStatus:
    """Alert status values."""
    ACTIVE = 'active'
    ACKNOWLEDGED = 'acknowledged'
    RESOLVED = 'resolved'
    EXPIRED = 'expired'


class AlertCategory:
    """Alert category values."""
    LOGS = 'logs'
    JOBS = 'jobs'
    INFRASTRUCTURE = 'infrastructure'
    CUSTOM = 'custom'


class AlertService:
    """
    Service for managing system alerts.
    
    Handles:
    - Evaluating alert rules against system data
    - Creating and updating alerts
    - Alert acknowledgment and resolution
    - Alert history management
    """
    
    def __init__(self, db=None):
        self.db = db or get_db()
    
    def get_active_alerts(self, 
                          severity: str = None, 
                          category: str = None,
                          limit: int = 50) -> List[Dict]:
        """Get all active alerts, optionally filtered."""
        query = """
            SELECT a.*, r.name as rule_name, r.description as rule_description
            FROM system_alerts a
            LEFT JOIN alert_rules r ON a.rule_id = r.id
            WHERE a.status IN ('active', 'acknowledged')
        """
        params = []
        
        if severity:
            query += " AND a.severity = %s"
            params.append(severity)
        
        if category:
            query += " AND a.category = %s"
            params.append(category)
        
        query += " ORDER BY a.triggered_at DESC LIMIT %s"
        params.append(limit)
        
        with self.db.cursor() as cursor:
            cursor.execute(query, params)
            alerts = []
            for row in cursor.fetchall():
                alert = dict(row)
                # Convert timestamps to UTC ISO format
                for ts_field in ['triggered_at', 'acknowledged_at', 'resolved_at', 'expires_at']:
                    if alert.get(ts_field):
                        alert[ts_field] = _to_utc_iso(alert[ts_field])
                alerts.append(alert)
            return alerts
    
    def get_alert_by_id(self, alert_id: int) -> Optional[Dict]:
        """Get a single alert by ID."""
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT a.*, r.name as rule_name, r.description as rule_description
                FROM system_alerts a
                LEFT JOIN alert_rules r ON a.rule_id = r.id
                WHERE a.id = %s
            """, (alert_id,))
            row = cursor.fetchone()
            if row:
                alert = dict(row)
                for ts_field in ['triggered_at', 'acknowledged_at', 'resolved_at', 'expires_at']:
                    if alert.get(ts_field):
                        alert[ts_field] = _to_utc_iso(alert[ts_field])
                return alert
            return None
    
    def acknowledge_alert(self, alert_id: int, acknowledged_by: str = None) -> bool:
        """Acknowledge an alert."""
        with self.db.cursor() as cursor:
            cursor.execute("""
                UPDATE system_alerts
                SET status = 'acknowledged',
                    acknowledged_at = %s,
                    acknowledged_by = %s
                WHERE id = %s AND status = 'active'
            """, (now_utc(), acknowledged_by, alert_id))
            return cursor.rowcount > 0
    
    def resolve_alert(self, alert_id: int) -> bool:
        """Resolve an alert and move to history."""
        alert = self.get_alert_by_id(alert_id)
        if not alert:
            return False
        
        with self.db.cursor() as cursor:
            # Archive to history
            cursor.execute("""
                INSERT INTO alert_history (
                    original_alert_id, rule_id, alert_key, severity, category,
                    title, message, details, status, triggered_at,
                    acknowledged_at, acknowledged_by, resolved_at
                )
                SELECT id, rule_id, alert_key, severity, category,
                       title, message, details, 'resolved', triggered_at,
                       acknowledged_at, acknowledged_by, %s
                FROM system_alerts WHERE id = %s
            """, (now_utc(), alert_id))
            
            # Delete from active alerts
            cursor.execute("DELETE FROM system_alerts WHERE id = %s", (alert_id,))
            return True
    
    def create_alert(self,
                     alert_key: str,
                     title: str,
                     message: str,
                     severity: str = AlertSeverity.WARNING,
                     category: str = AlertCategory.CUSTOM,
                     rule_id: int = None,
                     details: Dict = None,
                     expires_hours: int = 24) -> Optional[int]:
        """
        Create a new alert if one doesn't already exist with the same key.
        
        Returns:
            Alert ID if created, None if duplicate exists
        """
        expires_at = now_utc() + timedelta(hours=expires_hours)
        
        with self.db.cursor() as cursor:
            # Check for existing active alert with same key
            cursor.execute("""
                SELECT id FROM system_alerts 
                WHERE alert_key = %s AND status IN ('active', 'acknowledged')
            """, (alert_key,))
            
            if cursor.fetchone():
                return None  # Duplicate exists
            
            cursor.execute("""
                INSERT INTO system_alerts (
                    rule_id, alert_key, severity, category, title, message,
                    details, status, triggered_at, expires_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'active', %s, %s)
                RETURNING id
            """, (
                rule_id, alert_key, severity, category, title, message,
                json.dumps(details) if details else None,
                now_utc(), expires_at
            ))
            
            result = cursor.fetchone()
            return result['id'] if result else None
    
    def get_alert_rules(self, enabled_only: bool = True) -> List[Dict]:
        """Get all alert rules."""
        query = "SELECT * FROM alert_rules"
        if enabled_only:
            query += " WHERE enabled = TRUE"
        query += " ORDER BY category, name"
        
        with self.db.cursor() as cursor:
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_rule(self, rule_id: int, updates: Dict) -> bool:
        """Update an alert rule."""
        allowed_fields = ['enabled', 'severity', 'condition_config', 'cooldown_minutes', 'description']
        set_clauses = []
        params = []
        
        for field in allowed_fields:
            if field in updates:
                set_clauses.append(f"{field} = %s")
                value = updates[field]
                if field == 'condition_config' and isinstance(value, dict):
                    value = json.dumps(value)
                params.append(value)
        
        if not set_clauses:
            return False
        
        set_clauses.append("updated_at = %s")
        params.append(now_utc())
        params.append(rule_id)
        
        with self.db.cursor() as cursor:
            cursor.execute(f"""
                UPDATE alert_rules
                SET {', '.join(set_clauses)}
                WHERE id = %s
            """, params)
            return cursor.rowcount > 0
    
    def get_alert_stats(self) -> Dict:
        """Get alert statistics."""
        with self.db.cursor() as cursor:
            # Count by status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM system_alerts
                GROUP BY status
            """)
            by_status = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Count by severity (active only)
            cursor.execute("""
                SELECT severity, COUNT(*) as count
                FROM system_alerts
                WHERE status IN ('active', 'acknowledged')
                GROUP BY severity
            """)
            by_severity = {row['severity']: row['count'] for row in cursor.fetchall()}
            
            # Count by category (active only)
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM system_alerts
                WHERE status IN ('active', 'acknowledged')
                GROUP BY category
            """)
            by_category = {row['category']: row['count'] for row in cursor.fetchall()}
            
            return {
                'total_active': by_status.get('active', 0) + by_status.get('acknowledged', 0),
                'by_status': by_status,
                'by_severity': by_severity,
                'by_category': by_category,
            }
    
    def get_alert_history(self, 
                          days: int = 7,
                          limit: int = 100) -> List[Dict]:
        """Get alert history for the past N days."""
        since = now_utc() - timedelta(days=days)
        
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM alert_history
                WHERE triggered_at >= %s
                ORDER BY triggered_at DESC
                LIMIT %s
            """, (since, limit))
            
            history = []
            for row in cursor.fetchall():
                alert = dict(row)
                for ts_field in ['triggered_at', 'acknowledged_at', 'resolved_at', 'archived_at']:
                    if alert.get(ts_field):
                        alert[ts_field] = _to_utc_iso(alert[ts_field])
                history.append(alert)
            return history
    
    def cleanup_expired_alerts(self) -> int:
        """Move expired alerts to history."""
        now = now_utc()
        
        with self.db.cursor() as cursor:
            # Archive expired alerts
            cursor.execute("""
                INSERT INTO alert_history (
                    original_alert_id, rule_id, alert_key, severity, category,
                    title, message, details, status, triggered_at,
                    acknowledged_at, acknowledged_by, resolved_at
                )
                SELECT id, rule_id, alert_key, severity, category,
                       title, message, details, 'expired', triggered_at,
                       acknowledged_at, acknowledged_by, %s
                FROM system_alerts 
                WHERE expires_at < %s AND status IN ('active', 'acknowledged')
            """, (now, now))
            
            # Delete expired
            cursor.execute("""
                DELETE FROM system_alerts
                WHERE expires_at < %s AND status IN ('active', 'acknowledged')
            """, (now,))
            
            return cursor.rowcount


class AlertEvaluator:
    """
    Evaluates alert rules against system data.
    
    Runs periodically to check conditions and create alerts.
    """
    
    def __init__(self, db=None):
        self.db = db or get_db()
        self.alert_service = AlertService(self.db)
    
    def evaluate_all_rules(self) -> Dict[str, Any]:
        """Evaluate all enabled alert rules."""
        rules = self.alert_service.get_alert_rules(enabled_only=True)
        results = {
            'evaluated': 0,
            'alerts_created': 0,
            'alerts_resolved': 0,
            'errors': []
        }
        
        for rule in rules:
            try:
                alert_created = self._evaluate_rule(rule)
                results['evaluated'] += 1
                if alert_created:
                    results['alerts_created'] += 1
            except Exception as e:
                results['errors'].append({
                    'rule': rule['name'],
                    'error': str(e)
                })
        
        # Auto-resolve alerts whose conditions have cleared
        resolved = self._auto_resolve_cleared_alerts(rules)
        results['alerts_resolved'] = resolved
        
        # Cleanup expired alerts
        expired = self.alert_service.cleanup_expired_alerts()
        results['expired_cleaned'] = expired
        
        return results
    
    def _auto_resolve_cleared_alerts(self, rules: List[Dict]) -> int:
        """Auto-resolve alerts whose triggering conditions have cleared."""
        resolved_count = 0
        
        # Get all active/acknowledged alerts that have a rule_id
        active_alerts = self.alert_service.get_active_alerts(limit=100)
        
        for alert in active_alerts:
            if not alert.get('rule_id'):
                continue  # Manual alerts don't auto-resolve
            
            # Find the rule for this alert
            rule = next((r for r in rules if r['id'] == alert['rule_id']), None)
            if not rule:
                continue
            
            # Check if condition is still triggered
            try:
                config = rule['condition_config']
                if isinstance(config, str):
                    config = json.loads(config)
                
                evaluators = {
                    'error_rate': self._eval_error_rate,
                    'error_count': self._eval_error_count,
                    'job_failure_count': self._eval_job_failures,
                    'worker_count': self._eval_worker_count,
                    'long_running_job': self._eval_long_running_jobs,
                }
                
                evaluator = evaluators.get(rule['condition_type'])
                if not evaluator:
                    continue
                
                still_triggered, _ = evaluator(config)
                
                if not still_triggered:
                    # Condition cleared - auto-resolve the alert
                    self.alert_service.resolve_alert(alert['id'])
                    resolved_count += 1
                    
            except Exception:
                pass  # Don't fail on individual alert checks
        
        return resolved_count
    
    def _evaluate_rule(self, rule: Dict) -> bool:
        """Evaluate a single rule and create alert if triggered."""
        condition_type = rule['condition_type']
        config = rule['condition_config']
        if isinstance(config, str):
            config = json.loads(config)
        
        # Check cooldown
        if not self._check_cooldown(rule):
            return False
        
        # Evaluate based on condition type
        evaluators = {
            'error_rate': self._eval_error_rate,
            'error_count': self._eval_error_count,
            'job_failure_count': self._eval_job_failures,
            'worker_count': self._eval_worker_count,
            'long_running_job': self._eval_long_running_jobs,
        }
        
        evaluator = evaluators.get(condition_type)
        if not evaluator:
            return False
        
        triggered, details = evaluator(config)
        
        if triggered:
            alert_key = f"{rule['name']}_{rule['id']}"
            title = rule['name'].replace('_', ' ').title()
            message = self._build_message(rule, details)
            
            alert = self.alert_service.create_alert(
                alert_key=alert_key,
                title=title,
                message=message,
                severity=rule['severity'],
                category=rule['category'],
                rule_id=rule['id'],
                details=details,
            )
            
            # Send notifications for this alert
            if alert:
                self._send_alert_notifications(alert, rule)
            
            return True
        
        return False
    
    def _check_cooldown(self, rule: Dict) -> bool:
        """Check if rule is in cooldown period."""
        cooldown_minutes = rule.get('cooldown_minutes', 60)
        cutoff = now_utc() - timedelta(minutes=cooldown_minutes)
        
        with self.db.cursor() as cursor:
            # Check for recent alert from this rule
            cursor.execute("""
                SELECT id FROM system_alerts
                WHERE rule_id = %s AND triggered_at > %s
                LIMIT 1
            """, (rule['id'], cutoff))
            
            if cursor.fetchone():
                return False  # In cooldown
            
            # Also check history
            cursor.execute("""
                SELECT id FROM alert_history
                WHERE rule_id = %s AND triggered_at > %s
                LIMIT 1
            """, (rule['id'], cutoff))
            
            return cursor.fetchone() is None
    
    def _eval_error_rate(self, config: Dict) -> tuple:
        """Evaluate error rate condition."""
        threshold = config.get('threshold', 10)
        time_window = config.get('time_window_minutes', 60)
        levels = config.get('levels', ['ERROR', 'CRITICAL'])
        
        since = now_utc() - timedelta(minutes=time_window)
        
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM system_logs
                WHERE timestamp >= %s AND level = ANY(%s)
            """, (since, levels))
            
            count = cursor.fetchone()['count']
            
            if count >= threshold:
                return True, {
                    'error_count': count,
                    'threshold': threshold,
                    'time_window_minutes': time_window,
                    'levels': levels
                }
        
        return False, None
    
    def _eval_error_count(self, config: Dict) -> tuple:
        """Evaluate error count condition (same as rate but different semantics)."""
        return self._eval_error_rate(config)
    
    def _eval_job_failures(self, config: Dict) -> tuple:
        """Evaluate job failure count."""
        threshold = config.get('threshold', 3)
        time_window = config.get('time_window_minutes', 60)
        
        since = now_utc() - timedelta(minutes=time_window)
        
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as count, 
                       array_agg(DISTINCT job_name) as failed_jobs
                FROM scheduler_job_executions
                WHERE started_at >= %s AND status = 'failed'
            """, (since,))
            
            row = cursor.fetchone()
            count = row['count']
            
            if count >= threshold:
                return True, {
                    'failure_count': count,
                    'threshold': threshold,
                    'time_window_minutes': time_window,
                    'failed_jobs': row['failed_jobs'] or []
                }
        
        return False, None
    
    def _eval_worker_count(self, config: Dict) -> tuple:
        """Evaluate worker count condition."""
        min_workers = config.get('min_workers', 1)
        
        try:
            from celery_app import celery_app
            inspect = celery_app.control.inspect()
            active = inspect.active() or {}
            worker_count = len(active)
            
            if worker_count < min_workers:
                return True, {
                    'worker_count': worker_count,
                    'min_workers': min_workers,
                    'workers': list(active.keys())
                }
        except Exception as e:
            # Can't connect to Celery - this is an alert condition
            return True, {
                'worker_count': 0,
                'min_workers': min_workers,
                'error': str(e)
            }
        
        return False, None
    
    def _eval_long_running_jobs(self, config: Dict) -> tuple:
        """Evaluate long running jobs."""
        max_duration = config.get('max_duration_minutes', 30)
        
        cutoff = now_utc() - timedelta(minutes=max_duration)
        
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT id, job_name, started_at
                FROM scheduler_job_executions
                WHERE status = 'running' AND started_at < %s
            """, (cutoff,))
            
            long_running = [dict(row) for row in cursor.fetchall()]
            
            if long_running:
                for job in long_running:
                    if job.get('started_at'):
                        job['started_at'] = job['started_at'].isoformat()
                
                return True, {
                    'max_duration_minutes': max_duration,
                    'long_running_jobs': long_running
                }
        
        return False, None
    
    def _build_message(self, rule: Dict, details: Dict) -> str:
        """Build alert message from rule and details."""
        condition_type = rule['condition_type']
        
        messages = {
            'error_rate': f"Detected {details.get('error_count', 0)} errors in the last {details.get('time_window_minutes', 60)} minutes (threshold: {details.get('threshold', 0)})",
            'error_count': f"Detected {details.get('error_count', 0)} critical errors in the last {details.get('time_window_minutes', 60)} minutes",
            'job_failure_count': f"{details.get('failure_count', 0)} job failures in the last {details.get('time_window_minutes', 60)} minutes",
            'worker_count': f"Only {details.get('worker_count', 0)} workers online (minimum: {details.get('min_workers', 1)})",
            'long_running_job': f"{len(details.get('long_running_jobs', []))} jobs running longer than {details.get('max_duration_minutes', 30)} minutes",
        }
        
        return messages.get(condition_type, rule.get('description', 'Alert triggered'))
    
    def _send_alert_notifications(self, alert: Dict, rule: Dict):
        """Send notifications for a triggered alert."""
        try:
            # Get notification rules that match this alert
            with self.db.cursor() as cursor:
                cursor.execute("""
                    SELECT nr.*, nc.id as channel_id, nc.name as channel_name, 
                           nc.channel_type, nc.config as channel_config
                    FROM notification_rules nr
                    CROSS JOIN UNNEST(nr.channel_ids) AS cid
                    JOIN notification_channels nc ON nc.id = cid
                    WHERE nr.enabled = true 
                      AND nc.enabled = true
                      AND nr.trigger_type = 'alert'
                      AND (nr.severity_filter IS NULL OR %s = ANY(nr.severity_filter))
                      AND (nr.category_filter IS NULL OR %s = ANY(nr.category_filter))
                """, (alert.get('severity'), alert.get('category')))
                
                notification_targets = cursor.fetchall()
            
            if not notification_targets:
                return
            
            # Group by channel to avoid duplicate sends
            channels_to_notify = {}
            for target in notification_targets:
                cid = target['channel_id']
                if cid not in channels_to_notify:
                    channels_to_notify[cid] = {
                        'id': cid,
                        'name': target['channel_name'],
                        'channel_type': target['channel_type'],
                        'config': target['channel_config']
                    }
            
            # Send to each channel
            from backend.api.notifications import build_apprise_url
            from backend.services.notification_service import NotificationService
            
            title = f"[{alert.get('severity', 'INFO').upper()}] {alert.get('title', 'Alert')}"
            body = alert.get('message', '')
            
            for channel in channels_to_notify.values():
                config = channel['config']
                if isinstance(config, str):
                    import json
                    config = json.loads(config)
                
                apprise_url = build_apprise_url(channel['channel_type'], config)
                if not apprise_url:
                    continue
                
                service = NotificationService([apprise_url])
                success = service.send(title=title, body=body)
                
                # Log to notification history
                with self.db.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO notification_history 
                        (channel_id, title, message, trigger_type, trigger_id, status)
                        VALUES (%s, %s, %s, 'alert', %s, %s)
                    """, (
                        channel['id'],
                        title,
                        body,
                        str(alert.get('id')),
                        'sent' if success else 'failed'
                    ))
                    self.db.get_connection().commit()
                    
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send alert notifications: {e}")


# Singleton instance
_alert_service = None

def get_alert_service() -> AlertService:
    """Get the alert service singleton."""
    global _alert_service
    if _alert_service is None:
        _alert_service = AlertService()
    return _alert_service
