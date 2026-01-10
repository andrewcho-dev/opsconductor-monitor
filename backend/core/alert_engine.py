"""
Alert Engine

Core alert processing: normalize, deduplicate, store, emit events.
Single source of truth for all alert handling.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from uuid import UUID, uuid4
from enum import Enum

from .db import query, query_one, execute
from .parser import ParsedAlert
from .addon_registry import Addon

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Alert severity levels (RFC 5424 inspired)."""
    CRITICAL = 'critical'
    MAJOR = 'major'
    MINOR = 'minor'
    WARNING = 'warning'
    INFO = 'info'
    CLEAR = 'clear'


class Status(str, Enum):
    """Alert status values."""
    ACTIVE = 'active'
    ACKNOWLEDGED = 'acknowledged'
    SUPPRESSED = 'suppressed'
    RESOLVED = 'resolved'


@dataclass
class Alert:
    """Alert entity."""
    id: UUID
    addon_id: str
    fingerprint: str
    device_ip: str
    device_name: Optional[str]
    alert_type: str
    severity: str
    category: str
    title: str
    message: Optional[str]
    status: str
    is_clear: bool
    occurred_at: datetime
    received_at: datetime
    resolved_at: Optional[datetime]
    occurrence_count: int
    raw_data: Dict
    created_at: datetime
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': str(self.id),
            'addon_id': self.addon_id,
            'fingerprint': self.fingerprint,
            'device_ip': self.device_ip,
            'device_name': self.device_name,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'category': self.category,
            'title': self.title,
            'message': self.message,
            'status': self.status,
            'is_clear': self.is_clear,
            'occurred_at': self.occurred_at.isoformat() if self.occurred_at else None,
            'received_at': self.received_at.isoformat() if self.received_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'occurrence_count': self.occurrence_count,
            'raw_data': self.raw_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# Event callbacks for real-time updates
_event_callbacks: List[callable] = []


def register_event_callback(callback: callable) -> None:
    """Register callback for alert events (for WebSocket broadcast)."""
    _event_callbacks.append(callback)


async def _emit_event(event_type: str, alert: Alert) -> None:
    """Emit alert event to all registered callbacks and Redis pub/sub."""
    # Publish to Redis for cross-process communication (Celery -> FastAPI)
    try:
        import redis
        import json
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.publish('alert_events', json.dumps({
            'event_type': event_type,
            'alert': alert.to_dict()
        }))
    except Exception as e:
        logger.warning(f"Redis publish failed: {e}")
    
    # Also call local callbacks (for in-process handlers)
    for callback in _event_callbacks:
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(event_type, alert.to_dict())
            else:
                callback(event_type, alert.to_dict())
        except Exception as e:
            logger.error(f"Event callback error: {e}")


import asyncio


class AlertEngine:
    """
    Core alert processing engine.
    
    Responsibilities:
    - Receive parsed alerts
    - Apply severity/category mappings from addon
    - Generate fingerprint for deduplication
    - Store to database
    - Emit events for real-time updates
    
    Usage:
        engine = AlertEngine()
        alert = await engine.process(parsed_alert, addon)
    """
    
    async def process(self, parsed: ParsedAlert, addon: Addon) -> Optional[Alert]:
        """
        Process a parsed alert through the engine.
        
        Args:
            parsed: ParsedAlert from parser
            addon: Addon that produced this alert
            
        Returns:
            Stored Alert entity, or None if alert type is disabled
        """
        # Check if this alert type is enabled
        if not addon.is_alert_enabled(parsed.alert_type):
            logger.debug(f"Alert type {parsed.alert_type} is disabled for addon {addon.id}")
            return None
        
        now = datetime.utcnow()
        
        # Apply severity mapping from addon
        severity = addon.severity_mappings.get(parsed.alert_type, 'warning')
        
        # Apply category mapping from addon
        category = addon.category_mappings.get(parsed.alert_type, addon.category)
        
        # Generate title from mapping or default
        title = addon.title_mappings.get(parsed.alert_type) or self._generate_title(parsed, addon)
        
        # Generate fingerprint for deduplication
        fingerprint = self._generate_fingerprint(parsed, addon)
        
        # Check for existing alert with same fingerprint
        existing = await self._find_duplicate(fingerprint)
        
        if existing:
            # Update existing alert
            alert = await self._update_existing(existing, parsed, now)
            action = 'updated'
        else:
            # Create new alert
            alert = await self._create_new(parsed, addon, fingerprint, severity, category, title, now)
            action = 'created'
        
        # Handle clear events
        if parsed.is_clear and alert.status != Status.RESOLVED.value:
            alert = await self.resolve_alert(alert.id, resolution_source='clear_event')
            action = 'resolved'
        
        # Emit event for real-time updates
        await _emit_event(f'alert_{action}', alert)
        
        logger.debug(f"Alert {action}: {alert.id} - {alert.title}")
        return alert
    
    def _generate_fingerprint(self, parsed: ParsedAlert, addon: Addon) -> str:
        """Generate deduplication fingerprint."""
        parts = [
            addon.id,
            parsed.alert_type,
            parsed.device_ip or '',
        ]
        fingerprint_str = ':'.join(str(p) for p in parts)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:32]
    
    def _generate_title(self, parsed: ParsedAlert, addon: Addon) -> str:
        """Generate alert title."""
        alert_type_display = parsed.alert_type.replace('_', ' ').title()
        device = parsed.device_ip or parsed.device_name or 'Unknown'
        return f"{addon.name}: {alert_type_display} on {device}"
    
    async def _find_duplicate(self, fingerprint: str) -> Optional[Alert]:
        """Find existing non-resolved alert with same fingerprint."""
        row = query_one("""
            SELECT * FROM alerts 
            WHERE fingerprint = %s 
            AND status != 'resolved'
            ORDER BY occurred_at DESC
            LIMIT 1
        """, (fingerprint,))
        
        if row:
            return self._row_to_alert(row)
        return None
    
    async def _update_existing(self, existing: Alert, parsed: ParsedAlert, now: datetime) -> Alert:
        """Update existing alert with new occurrence."""
        execute("""
            UPDATE alerts SET
                occurrence_count = occurrence_count + 1,
                message = COALESCE(%s, message),
                raw_data = %s
            WHERE id = %s
        """, (parsed.message, json.dumps(parsed.raw_data), str(existing.id)))
        
        existing.occurrence_count += 1
        existing.message = parsed.message or existing.message
        return existing
    
    async def _create_new(
        self, 
        parsed: ParsedAlert, 
        addon: Addon, 
        fingerprint: str,
        severity: str,
        category: str,
        title: str,
        now: datetime
    ) -> Alert:
        """Create new alert in database."""
        alert_id = uuid4()
        occurred_at = parsed.timestamp or now
        
        execute("""
            INSERT INTO alerts (
                id, addon_id, fingerprint, device_ip, device_name,
                alert_type, severity, category, title, message,
                status, is_clear, occurred_at, received_at,
                occurrence_count, raw_data, created_at
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s
            )
        """, (
            str(alert_id), addon.id, fingerprint, parsed.device_ip, parsed.device_name,
            parsed.alert_type, severity, category, title, parsed.message,
            Status.ACTIVE.value, parsed.is_clear, occurred_at, now,
            1, json.dumps(parsed.raw_data), now
        ))
        
        return Alert(
            id=alert_id,
            addon_id=addon.id,
            fingerprint=fingerprint,
            device_ip=parsed.device_ip,
            device_name=parsed.device_name,
            alert_type=parsed.alert_type,
            severity=severity,
            category=category,
            title=title,
            message=parsed.message,
            status=Status.ACTIVE.value,
            is_clear=parsed.is_clear,
            occurred_at=occurred_at,
            received_at=now,
            resolved_at=None,
            occurrence_count=1,
            raw_data=parsed.raw_data,
            created_at=now
        )
    
    async def resolve_alert(
        self, 
        alert_id: UUID, 
        resolution_source: str = 'manual'
    ) -> Alert:
        """Resolve an alert."""
        now = datetime.utcnow()
        
        execute("""
            UPDATE alerts SET
                status = %s,
                resolved_at = %s
            WHERE id = %s
        """, (Status.RESOLVED.value, now, str(alert_id)))
        
        alert = await self.get_alert(alert_id)
        await _emit_event('alert_resolved', alert)
        
        return alert
    
    async def auto_resolve(
        self,
        addon_id: str,
        alert_type: str,
        device_ip: str
    ) -> bool:
        """
        Auto-resolve active alerts when condition clears.
        
        Returns True if an alert was resolved.
        """
        # Find active alert for this device/type
        row = query_one("""
            SELECT id FROM alerts
            WHERE addon_id = %s
            AND alert_type = %s
            AND device_ip = %s
            AND status != 'resolved'
            LIMIT 1
        """, (addon_id, alert_type, device_ip))
        
        if row:
            await self.resolve_alert(UUID(row['id']), resolution_source='auto_clear')
            return True
        
        return False
    
    async def acknowledge_alert(self, alert_id: UUID) -> Alert:
        """Acknowledge an alert."""
        execute("""
            UPDATE alerts SET status = %s
            WHERE id = %s AND status = 'active'
        """, (Status.ACKNOWLEDGED.value, str(alert_id)))
        
        alert = await self.get_alert(alert_id)
        await _emit_event('alert_updated', alert)
        
        return alert
    
    async def get_alert(self, alert_id: UUID) -> Optional[Alert]:
        """Get alert by ID."""
        row = query_one("SELECT * FROM alerts WHERE id = %s", (str(alert_id),))
        if row:
            return self._row_to_alert(row)
        return None
    
    async def get_alerts(
        self,
        status: Optional[List[str]] = None,
        severity: Optional[List[str]] = None,
        addon_id: Optional[str] = None,
        device_ip: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Alert]:
        """Query alerts with filters."""
        conditions = []
        params = []
        
        if status:
            placeholders = ','.join(['%s'] * len(status))
            conditions.append(f"status IN ({placeholders})")
            params.extend(status)
        
        if severity:
            placeholders = ','.join(['%s'] * len(severity))
            conditions.append(f"severity IN ({placeholders})")
            params.extend(severity)
        
        if addon_id:
            conditions.append("addon_id = %s")
            params.append(addon_id)
        
        if device_ip:
            conditions.append("device_ip = %s")
            params.append(device_ip)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.extend([limit, offset])
        
        rows = query(f"""
            SELECT * FROM alerts
            WHERE {where_clause}
            ORDER BY occurred_at DESC
            LIMIT %s OFFSET %s
        """, tuple(params))
        
        return [self._row_to_alert(row) for row in rows]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get alert statistics."""
        by_severity = query("""
            SELECT severity, COUNT(*) as count
            FROM alerts WHERE status != 'resolved'
            GROUP BY severity
        """)
        
        by_status = query("""
            SELECT status, COUNT(*) as count
            FROM alerts
            GROUP BY status
        """)
        
        by_addon = query("""
            SELECT addon_id, COUNT(*) as count
            FROM alerts WHERE status != 'resolved'
            GROUP BY addon_id
        """)
        
        return {
            'by_severity': {row['severity']: row['count'] for row in by_severity},
            'by_status': {row['status']: row['count'] for row in by_status},
            'by_addon': {row['addon_id']: row['count'] for row in by_addon},
            'total_active': sum(row['count'] for row in by_severity),
        }
    
    async def delete_alert(self, alert_id: UUID) -> bool:
        """Delete an alert."""
        result = execute("DELETE FROM alerts WHERE id = %s", (str(alert_id),))
        return result > 0
    
    def _row_to_alert(self, row: Dict) -> Alert:
        """Convert database row to Alert object."""
        return Alert(
            id=UUID(row['id']) if isinstance(row['id'], str) else row['id'],
            addon_id=row['addon_id'],
            fingerprint=row['fingerprint'],
            device_ip=row['device_ip'],
            device_name=row.get('device_name'),
            alert_type=row['alert_type'],
            severity=row['severity'],
            category=row['category'],
            title=row['title'],
            message=row.get('message'),
            status=row['status'],
            is_clear=row.get('is_clear', False),
            occurred_at=row['occurred_at'],
            received_at=row['received_at'],
            resolved_at=row.get('resolved_at'),
            occurrence_count=row.get('occurrence_count', 1),
            raw_data=row.get('raw_data', {}),
            created_at=row.get('created_at', row['received_at'])
        )


# Global engine instance
_engine: Optional[AlertEngine] = None


def get_engine() -> AlertEngine:
    """Get global alert engine instance."""
    global _engine
    if _engine is None:
        _engine = AlertEngine()
    return _engine


async def process_alert(parsed: ParsedAlert, addon: Addon) -> Alert:
    """Convenience function to process alert using global engine."""
    return await get_engine().process(parsed, addon)
