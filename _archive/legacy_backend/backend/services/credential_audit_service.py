"""
Credential Audit Service

Provides comprehensive audit logging for all credential operations.
Tracks every action: creation, updates, deletions, access, usage, expiration, rotation.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# Try to import Flask for legacy compatibility, but don't require it
try:
    from flask import request as flask_request, has_request_context
except ImportError:
    flask_request = None
    def has_request_context():
        return False

from backend.database import get_db
from backend.utils.time import now_utc

logger = logging.getLogger(__name__)


class CredentialAuditService:
    """
    Service for comprehensive credential audit logging.
    
    Tracks all credential operations with full context including:
    - Who performed the action
    - What was changed
    - When it happened
    - Where it was used (device, workflow, job)
    - Success/failure status
    """
    
    # Action types
    ACTION_CREATED = 'created'
    ACTION_UPDATED = 'updated'
    ACTION_DELETED = 'deleted'
    ACTION_ACCESSED = 'accessed'  # Secret was viewed/retrieved
    ACTION_USED = 'used'  # Used for authentication
    ACTION_EXPIRED = 'expired'
    ACTION_ROTATED = 'rotated'
    ACTION_EXPORTED = 'exported'
    ACTION_IMPORTED = 'imported'
    ACTION_ENABLED = 'enabled'
    ACTION_DISABLED = 'disabled'
    ACTION_REVOKED = 'revoked'
    
    def __init__(self):
        pass
    
    def _get_request_context(self) -> Dict[str, Any]:
        """Extract context from the current request if available."""
        context = {
            'performed_by_ip': None,
            'performed_by_user_agent': None,
            'session_id': None,
            'request_id': None,
        }
        
        if has_request_context() and flask_request:
            context['performed_by_ip'] = flask_request.remote_addr
            context['performed_by_user_agent'] = flask_request.headers.get('User-Agent')
            context['session_id'] = flask_request.headers.get('X-Session-ID')
            context['request_id'] = flask_request.headers.get('X-Request-ID')
        
        return context
    
    def log_action(
        self,
        action: str,
        credential_id: int = None,
        credential_name: str = None,
        credential_type: str = None,
        performed_by: str = None,
        action_detail: str = None,
        target_device: str = None,
        target_service: str = None,
        workflow_id: int = None,
        workflow_name: str = None,
        job_id: int = None,
        job_name: str = None,
        success: bool = True,
        error_message: str = None,
        previous_values: Dict = None,
        new_values: Dict = None,
    ) -> int:
        """
        Log a credential action to the audit log.
        
        Args:
            action: Type of action (created, updated, deleted, accessed, used, etc.)
            credential_id: ID of the credential
            credential_name: Name of the credential
            credential_type: Type of credential (ssh, snmp, certificate, etc.)
            performed_by: Who performed the action (user, system, workflow name)
            action_detail: Additional details about the action
            target_device: Device IP/hostname if credential was used
            target_service: Service name (SSH, WinRM, SNMP, etc.)
            workflow_id: Workflow ID if used in a workflow
            workflow_name: Workflow name
            job_id: Job ID if used in a job
            job_name: Job name
            success: Whether the action was successful
            error_message: Error message if action failed
            previous_values: Non-sensitive previous values (for updates)
            new_values: Non-sensitive new values (for updates)
        
        Returns:
            ID of the audit log entry
        """
        import json
        
        # Get request context
        ctx = self._get_request_context()
        
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO credential_audit_log (
                    credential_id, credential_name, credential_type,
                    action, action_detail,
                    performed_by, performed_by_ip, performed_by_user_agent,
                    target_device, target_service,
                    workflow_id, workflow_name, job_id, job_name,
                    success, error_message,
                    previous_values, new_values,
                    session_id, request_id,
                    performed_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
            """, (
                credential_id, credential_name, credential_type,
                action, action_detail,
                performed_by or 'system', ctx['performed_by_ip'], ctx['performed_by_user_agent'],
                target_device, target_service,
                workflow_id, workflow_name, job_id, job_name,
                success, error_message,
                json.dumps(previous_values) if previous_values else None,
                json.dumps(new_values) if new_values else None,
                ctx['session_id'], ctx['request_id'],
                now_utc()
            ))
            
            row = cursor.fetchone()
            db.get_connection().commit()
            
            log_id = row['id'] if row else None
            
            # Also log to application logger for immediate visibility
            log_msg = f"CREDENTIAL_AUDIT: {action} - {credential_name or credential_id}"
            if target_device:
                log_msg += f" -> {target_device}"
            if not success:
                log_msg += f" [FAILED: {error_message}]"
            
            if success:
                logger.info(log_msg)
            else:
                logger.warning(log_msg)
            
            return log_id
    
    def log_created(
        self,
        credential_id: int,
        credential_name: str,
        credential_type: str,
        performed_by: str = None,
        **kwargs
    ) -> int:
        """Log credential creation."""
        return self.log_action(
            action=self.ACTION_CREATED,
            credential_id=credential_id,
            credential_name=credential_name,
            credential_type=credential_type,
            performed_by=performed_by,
            action_detail=f"Created new {credential_type} credential",
            **kwargs
        )
    
    def log_updated(
        self,
        credential_id: int,
        credential_name: str,
        credential_type: str,
        performed_by: str = None,
        fields_changed: List[str] = None,
        previous_values: Dict = None,
        new_values: Dict = None,
        **kwargs
    ) -> int:
        """Log credential update."""
        detail = "Updated credential"
        if fields_changed:
            detail += f": {', '.join(fields_changed)}"
        
        return self.log_action(
            action=self.ACTION_UPDATED,
            credential_id=credential_id,
            credential_name=credential_name,
            credential_type=credential_type,
            performed_by=performed_by,
            action_detail=detail,
            previous_values=previous_values,
            new_values=new_values,
            **kwargs
        )
    
    def log_deleted(
        self,
        credential_id: int,
        credential_name: str,
        credential_type: str,
        performed_by: str = None,
        **kwargs
    ) -> int:
        """Log credential deletion."""
        return self.log_action(
            action=self.ACTION_DELETED,
            credential_id=credential_id,
            credential_name=credential_name,
            credential_type=credential_type,
            performed_by=performed_by,
            action_detail="Credential deleted (soft delete)",
            **kwargs
        )
    
    def log_accessed(
        self,
        credential_id: int,
        credential_name: str,
        credential_type: str,
        performed_by: str = None,
        access_reason: str = None,
        **kwargs
    ) -> int:
        """Log when credential secret is accessed/viewed."""
        return self.log_action(
            action=self.ACTION_ACCESSED,
            credential_id=credential_id,
            credential_name=credential_name,
            credential_type=credential_type,
            performed_by=performed_by,
            action_detail=access_reason or "Secret data accessed",
            **kwargs
        )
    
    def log_used(
        self,
        credential_id: int,
        credential_name: str,
        credential_type: str,
        target_device: str,
        target_service: str,
        performed_by: str = None,
        success: bool = True,
        error_message: str = None,
        workflow_id: int = None,
        workflow_name: str = None,
        job_id: int = None,
        job_name: str = None,
        **kwargs
    ) -> int:
        """Log when credential is used for authentication."""
        return self.log_action(
            action=self.ACTION_USED,
            credential_id=credential_id,
            credential_name=credential_name,
            credential_type=credential_type,
            performed_by=performed_by,
            target_device=target_device,
            target_service=target_service,
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            job_id=job_id,
            job_name=job_name,
            success=success,
            error_message=error_message,
            action_detail=f"Used for {target_service} authentication to {target_device}",
            **kwargs
        )
    
    def log_expired(
        self,
        credential_id: int,
        credential_name: str,
        credential_type: str,
        **kwargs
    ) -> int:
        """Log credential expiration."""
        return self.log_action(
            action=self.ACTION_EXPIRED,
            credential_id=credential_id,
            credential_name=credential_name,
            credential_type=credential_type,
            performed_by='system',
            action_detail="Credential expired",
            **kwargs
        )
    
    def log_rotated(
        self,
        credential_id: int,
        credential_name: str,
        credential_type: str,
        performed_by: str = None,
        rotation_type: str = 'manual',
        **kwargs
    ) -> int:
        """Log credential rotation."""
        return self.log_action(
            action=self.ACTION_ROTATED,
            credential_id=credential_id,
            credential_name=credential_name,
            credential_type=credential_type,
            performed_by=performed_by,
            action_detail=f"Credential rotated ({rotation_type})",
            **kwargs
        )
    
    def get_audit_log(
        self,
        credential_id: int = None,
        action: str = None,
        performed_by: str = None,
        target_device: str = None,
        success: bool = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get audit log entries with filtering.
        
        Returns:
            Dict with 'entries' list and 'total' count
        """
        db = get_db()
        
        # Build query
        conditions = []
        params = []
        
        if credential_id is not None:
            conditions.append("credential_id = %s")
            params.append(credential_id)
        
        if action:
            conditions.append("action = %s")
            params.append(action)
        
        if performed_by:
            conditions.append("performed_by ILIKE %s")
            params.append(f"%{performed_by}%")
        
        if target_device:
            conditions.append("target_device ILIKE %s")
            params.append(f"%{target_device}%")
        
        if success is not None:
            conditions.append("success = %s")
            params.append(success)
        
        if start_date:
            conditions.append("performed_at >= %s")
            params.append(start_date)
        
        if end_date:
            conditions.append("performed_at <= %s")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        with db.cursor() as cursor:
            # Get total count
            cursor.execute(f"""
                SELECT COUNT(*) as total
                FROM credential_audit_log
                WHERE {where_clause}
            """, params)
            total = cursor.fetchone()['total']
            
            # Get entries
            cursor.execute(f"""
                SELECT 
                    id, credential_id, credential_name, credential_type,
                    action, action_detail,
                    performed_by, performed_by_ip,
                    target_device, target_service,
                    workflow_id, workflow_name, job_id, job_name,
                    success, error_message,
                    previous_values, new_values,
                    performed_at
                FROM credential_audit_log
                WHERE {where_clause}
                ORDER BY performed_at DESC
                LIMIT %s OFFSET %s
            """, params + [limit, offset])
            
            entries = [dict(row) for row in cursor.fetchall()]
            
            return {
                'entries': entries,
                'total': total,
                'limit': limit,
                'offset': offset
            }
    
    def get_credential_history(self, credential_id: int, limit: int = 50) -> List[Dict]:
        """Get complete history for a specific credential."""
        result = self.get_audit_log(credential_id=credential_id, limit=limit)
        return result['entries']
    
    def get_recent_activity(self, limit: int = 50) -> List[Dict]:
        """Get recent audit activity across all credentials."""
        result = self.get_audit_log(limit=limit)
        return result['entries']
    
    def get_failed_authentications(self, hours: int = 24, limit: int = 100) -> List[Dict]:
        """Get failed authentication attempts in the last N hours."""
        from datetime import timedelta
        start_date = now_utc() - timedelta(hours=hours)
        
        result = self.get_audit_log(
            action=self.ACTION_USED,
            success=False,
            start_date=start_date,
            limit=limit
        )
        return result['entries']
    
    def get_audit_summary(self, credential_id: int = None, days: int = 30) -> Dict[str, Any]:
        """Get summary statistics for audit activity."""
        from datetime import timedelta
        start_date = now_utc() - timedelta(days=days)
        
        db = get_db()
        with db.cursor() as cursor:
            # Build base condition
            cred_condition = "AND credential_id = %s" if credential_id else ""
            params = [start_date]
            if credential_id:
                params.append(credential_id)
            
            # Action counts
            cursor.execute(f"""
                SELECT action, COUNT(*) as count
                FROM credential_audit_log
                WHERE performed_at >= %s {cred_condition}
                GROUP BY action
                ORDER BY count DESC
            """, params)
            action_counts = {row['action']: row['count'] for row in cursor.fetchall()}
            
            # Success/failure counts
            cursor.execute(f"""
                SELECT success, COUNT(*) as count
                FROM credential_audit_log
                WHERE performed_at >= %s {cred_condition}
                GROUP BY success
            """, params)
            success_counts = {str(row['success']): row['count'] for row in cursor.fetchall()}
            
            # Top users
            cursor.execute(f"""
                SELECT performed_by, COUNT(*) as count
                FROM credential_audit_log
                WHERE performed_at >= %s {cred_condition}
                GROUP BY performed_by
                ORDER BY count DESC
                LIMIT 10
            """, params)
            top_users = [{'user': row['performed_by'], 'count': row['count']} for row in cursor.fetchall()]
            
            # Top target devices
            cursor.execute(f"""
                SELECT target_device, COUNT(*) as count
                FROM credential_audit_log
                WHERE performed_at >= %s AND target_device IS NOT NULL {cred_condition}
                GROUP BY target_device
                ORDER BY count DESC
                LIMIT 10
            """, params)
            top_devices = [{'device': row['target_device'], 'count': row['count']} for row in cursor.fetchall()]
            
            return {
                'period_days': days,
                'action_counts': action_counts,
                'success_count': success_counts.get('True', 0),
                'failure_count': success_counts.get('False', 0),
                'top_users': top_users,
                'top_devices': top_devices,
            }


# Singleton instance
_audit_service = None


def get_audit_service() -> CredentialAuditService:
    """Get the credential audit service singleton."""
    global _audit_service
    if _audit_service is None:
        _audit_service = CredentialAuditService()
    return _audit_service
