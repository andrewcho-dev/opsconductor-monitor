"""
OpsConductor Alert Manager

Central processing hub for all normalized alerts.
Handles deduplication, correlation, storage, and event emission.
"""

import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from utils.db import db_query, db_query_one, db_execute

from .models import (
    NormalizedAlert, Alert, AlertStatus, Severity, Category,
    Priority, Impact, Urgency, AlertHistoryEntry
)
from .event_bus import get_event_bus, EventType

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Central alert processing service.
    
    Responsibilities:
    - Receive normalized alerts from connectors
    - Check for duplicates (fingerprint-based)
    - Correlate with device dependencies
    - Store alerts to database
    - Emit events for notifications
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._event_bus = get_event_bus()
        logger.info("AlertManager initialized")
    
    async def process_alert(self, normalized: NormalizedAlert) -> Alert:
        """
        Main entry point for processing incoming alerts.
        
        Args:
            normalized: NormalizedAlert from connector
            
        Returns:
            Stored Alert entity
        """
        logger.debug(f"Processing alert: {normalized.title} from {normalized.source_system}")
        
        # Generate fingerprint for deduplication
        fingerprint = self._generate_fingerprint(normalized)
        
        # Check for duplicate
        existing = await self._find_duplicate(fingerprint)
        
        if existing:
            # Update existing alert
            alert = await self._update_existing(existing, normalized)
            logger.debug(f"Updated existing alert {alert.id}")
        else:
            # Create new alert
            alert = await self._create_new(normalized, fingerprint)
            logger.info(f"Created new alert {alert.id}: {alert.title}")
            
            # Check for correlation (suppress if upstream has active alert)
            await self._check_correlation(alert)
            
            # Emit event for new alert
            await self._event_bus.publish(
                EventType.ALERT_CREATED,
                alert,
                source="alert_manager"
            )
        
        # Handle clear events
        if normalized.is_clear:
            await self._handle_clear_event(alert)
        
        return alert
    
    def _generate_fingerprint(self, normalized: NormalizedAlert) -> str:
        """Generate deduplication fingerprint."""
        # Key fields for fingerprint
        parts = [
            normalized.source_system,
            normalized.source_alert_id,
            normalized.device_ip or normalized.device_name or "",
            normalized.alert_type,
        ]
        fingerprint_str = ":".join(str(p) for p in parts)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()
    
    async def _find_duplicate(self, fingerprint: str) -> Optional[Alert]:
        """Find existing active alert with same fingerprint."""
        row = db_query_one("""
            SELECT * FROM alerts 
            WHERE fingerprint = %s 
            AND status IN ('active', 'acknowledged')
            ORDER BY occurred_at DESC
            LIMIT 1
        """, (fingerprint,))
        
        if row:
            return self._row_to_alert(row)
        return None
    
    async def _update_existing(self, existing: Alert, normalized: NormalizedAlert) -> Alert:
        """Update existing alert with new occurrence."""
        now = datetime.utcnow()
        
        db_execute("""
            UPDATE alerts SET
                occurrence_count = occurrence_count + 1,
                last_occurrence_at = %s,
                message = COALESCE(%s, message),
                updated_at = %s
            WHERE id = %s
        """, (now, normalized.message, now, str(existing.id)))
        
        existing.occurrence_count += 1
        existing.last_occurrence_at = now
        existing.updated_at = now
        
        # Emit update event
        await self._event_bus.publish(
            EventType.ALERT_UPDATED,
            existing,
            source="alert_manager"
        )
        
        return existing
    
    async def _create_new(self, normalized: NormalizedAlert, fingerprint: str) -> Alert:
        """Create new alert in database."""
        now = datetime.utcnow()
        
        # Create Alert from NormalizedAlert
        alert = Alert.from_normalized(normalized)
        alert.fingerprint = fingerprint
        alert.created_at = now
        alert.updated_at = now
        
        # Insert into database
        db_execute("""
            INSERT INTO alerts (
                id, source_system, source_alert_id,
                device_ip, device_name,
                severity, category, alert_type,
                title, message,
                status, is_clear,
                occurred_at, received_at,
                fingerprint, occurrence_count,
                raw_data, created_at, updated_at
            ) VALUES (
                %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s
            )
        """, (
            str(alert.id), alert.source_system, alert.source_alert_id,
            alert.device_ip, alert.device_name,
            alert.severity.value, alert.category.value, alert.alert_type,
            alert.title, alert.message,
            alert.status.value, alert.is_clear,
            alert.occurred_at, alert.received_at,
            alert.fingerprint, alert.occurrence_count,
            str(alert.raw_data), now, now
        ))
        
        # Add history entry
        await self._add_history(alert.id, "created", None, AlertStatus.ACTIVE)
        
        return alert
    
    async def _check_correlation(self, alert: Alert) -> None:
        """Check if alert should be suppressed due to upstream failure."""
        if not alert.device_ip:
            return
        
        # Import here to avoid circular import
        from .dependency_registry import get_dependency_registry
        
        registry = get_dependency_registry()
        parent_alert = await registry.find_upstream_alert(alert.device_ip)
        
        if parent_alert:
            # Suppress this alert
            await self.suppress_alert(
                alert.id,
                parent_alert.id,
                f"Upstream device {parent_alert.device_ip or parent_alert.device_name} has active alert"
            )
    
    async def _handle_clear_event(self, alert: Alert) -> None:
        """Handle clear/recovery event."""
        if alert.status == AlertStatus.ACTIVE:
            await self.resolve_alert(
                alert.id,
                resolved_by="system",
                notes="Auto-resolved by clear event"
            )
    
    async def acknowledge_alert(
        self,
        alert_id: UUID,
        user: str,
        notes: Optional[str] = None
    ) -> Alert:
        """Mark alert as acknowledged."""
        now = datetime.utcnow()
        
        db_execute("""
            UPDATE alerts SET
                status = %s,
                acknowledged_at = %s,
                acknowledged_by = %s,
                updated_at = %s
            WHERE id = %s
        """, (AlertStatus.ACKNOWLEDGED.value, now, user, now, str(alert_id)))
        
        alert = await self.get_alert(alert_id)
        
        await self._add_history(
            alert_id, "acknowledged",
            AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED,
            user_id=user, notes=notes
        )
        
        await self._event_bus.publish(
            EventType.ALERT_ACKNOWLEDGED,
            alert,
            source="alert_manager"
        )
        
        return alert
    
    async def resolve_alert(
        self,
        alert_id: UUID,
        resolved_by: str = "system",
        notes: Optional[str] = None
    ) -> Alert:
        """Mark alert as resolved."""
        now = datetime.utcnow()
        
        # Get current status for history
        current = await self.get_alert(alert_id)
        old_status = current.status if current else AlertStatus.ACTIVE
        
        db_execute("""
            UPDATE alerts SET
                status = %s,
                resolved_at = %s,
                resolved_by = %s,
                updated_at = %s
            WHERE id = %s
        """, (AlertStatus.RESOLVED.value, now, resolved_by, now, str(alert_id)))
        
        alert = await self.get_alert(alert_id)
        
        await self._add_history(
            alert_id, "resolved",
            old_status, AlertStatus.RESOLVED,
            user_id=resolved_by, notes=notes
        )
        
        await self._event_bus.publish(
            EventType.ALERT_RESOLVED,
            alert,
            source="alert_manager"
        )
        
        return alert
    
    async def suppress_alert(
        self,
        alert_id: UUID,
        correlated_to_id: UUID,
        reason: str
    ) -> Alert:
        """Mark alert as suppressed due to correlation."""
        now = datetime.utcnow()
        
        db_execute("""
            UPDATE alerts SET
                status = %s,
                correlated_to_id = %s,
                correlation_rule = %s,
                updated_at = %s
            WHERE id = %s
        """, (
            AlertStatus.SUPPRESSED.value,
            str(correlated_to_id),
            reason,
            now,
            str(alert_id)
        ))
        
        alert = await self.get_alert(alert_id)
        
        await self._add_history(
            alert_id, "suppressed",
            AlertStatus.ACTIVE, AlertStatus.SUPPRESSED,
            notes=reason
        )
        
        await self._event_bus.publish(
            EventType.ALERT_SUPPRESSED,
            alert,
            source="alert_manager"
        )
        
        logger.info(f"Suppressed alert {alert_id} - correlated to {correlated_to_id}")
        return alert
    
    async def add_note(
        self,
        alert_id: UUID,
        user: str,
        notes: str
    ) -> None:
        """Add a note to alert history."""
        await self._add_history(
            alert_id, "note_added",
            None, None,
            user_id=user, notes=notes
        )
    
    async def get_alert(self, alert_id: UUID) -> Optional[Alert]:
        """Get alert by ID."""
        row = db_query_one(
            "SELECT * FROM alerts WHERE id = %s",
            (str(alert_id),)
        )
        if row:
            return self._row_to_alert(row)
        return None
    
    async def get_alerts(
        self,
        status: Optional[List[AlertStatus]] = None,
        severity: Optional[List[Severity]] = None,
        category: Optional[List[Category]] = None,
        device_ip: Optional[str] = None,
        source_system: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Alert]:
        """Query alerts with filters."""
        conditions = []
        params = []
        
        if status:
            placeholders = ",".join(["%s"] * len(status))
            conditions.append(f"status IN ({placeholders})")
            params.extend([s.value for s in status])
        
        if severity:
            placeholders = ",".join(["%s"] * len(severity))
            conditions.append(f"severity IN ({placeholders})")
            params.extend([s.value for s in severity])
        
        if category:
            placeholders = ",".join(["%s"] * len(category))
            conditions.append(f"category IN ({placeholders})")
            params.extend([c.value for c in category])
        
        if device_ip:
            conditions.append("device_ip = %s")
            params.append(device_ip)
        
        if source_system:
            conditions.append("source_system = %s")
            params.append(source_system)
        
        if from_time:
            conditions.append("occurred_at >= %s")
            params.append(from_time)
        
        if to_time:
            conditions.append("occurred_at <= %s")
            params.append(to_time)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        params.extend([limit, offset])
        
        rows = db_query(f"""
            SELECT * FROM alerts
            WHERE {where_clause}
            ORDER BY occurred_at DESC
            LIMIT %s OFFSET %s
        """, tuple(params))
        
        return [self._row_to_alert(row) for row in rows]
    
    async def get_alert_count(
        self,
        status: Optional[List[AlertStatus]] = None,
        severity: Optional[List[Severity]] = None,
        category: Optional[List[Category]] = None,
    ) -> int:
        """Get count of alerts matching filters."""
        conditions = []
        params = []
        
        if status:
            placeholders = ",".join(["%s"] * len(status))
            conditions.append(f"status IN ({placeholders})")
            params.extend([s.value for s in status])
        
        if severity:
            placeholders = ",".join(["%s"] * len(severity))
            conditions.append(f"severity IN ({placeholders})")
            params.extend([s.value for s in severity])
        
        if category:
            placeholders = ",".join(["%s"] * len(category))
            conditions.append(f"category IN ({placeholders})")
            params.extend([c.value for c in category])
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        row = db_query_one(f"""
            SELECT COUNT(*) as count FROM alerts
            WHERE {where_clause}
        """, tuple(params))
        
        return row["count"] if row else 0
    
    async def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics."""
        # Active count by severity
        severity_rows = db_query("""
            SELECT severity, COUNT(*) as count
            FROM alerts
            WHERE status = 'active'
            GROUP BY severity
        """)
        
        by_severity = {row["severity"]: row["count"] for row in severity_rows}
        
        # Active count by category
        category_rows = db_query("""
            SELECT category, COUNT(*) as count
            FROM alerts
            WHERE status = 'active'
            GROUP BY category
        """)
        
        by_category = {row["category"]: row["count"] for row in category_rows}
        
        # Count by status
        status_rows = db_query("""
            SELECT status, COUNT(*) as count
            FROM alerts
            GROUP BY status
        """)
        
        by_status = {row["status"]: row["count"] for row in status_rows}
        
        return {
            "total_active": by_status.get("active", 0),
            "by_severity": by_severity,
            "by_category": by_category,
            "by_status": by_status,
        }
    
    async def get_alert_history(self, alert_id: UUID) -> List[Dict]:
        """Get history entries for an alert."""
        rows = db_query("""
            SELECT * FROM alert_history
            WHERE alert_id = %s
            ORDER BY created_at DESC
        """, (str(alert_id),))
        
        return [dict(row) for row in rows]
    
    async def _add_history(
        self,
        alert_id: UUID,
        action: str,
        old_status: Optional[AlertStatus],
        new_status: Optional[AlertStatus],
        user_id: Optional[str] = None,
        notes: Optional[str] = None,
        changes: Optional[Dict] = None
    ) -> None:
        """Add entry to alert history."""
        from uuid import uuid4
        
        db_execute("""
            INSERT INTO alert_history (
                id, alert_id, action,
                old_status, new_status,
                user_id, notes, changes,
                created_at
            ) VALUES (
                %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s
            )
        """, (
            str(uuid4()), str(alert_id), action,
            old_status.value if old_status else None,
            new_status.value if new_status else None,
            user_id, notes,
            str(changes) if changes else None,
            datetime.utcnow()
        ))
    
    def _row_to_alert(self, row: Dict) -> Alert:
        """Convert database row to Alert object."""
        return Alert(
            id=UUID(row["id"]) if isinstance(row["id"], str) else row["id"],
            source_system=row["source_system"],
            source_alert_id=row["source_alert_id"],
            device_ip=row.get("device_ip"),
            device_name=row.get("device_name"),
            severity=Severity(row["severity"]),
            category=Category(row["category"]),
            alert_type=row["alert_type"],
            title=row["title"],
            message=row.get("message"),
            status=AlertStatus(row["status"]),
            is_clear=row.get("is_clear", False),
            occurred_at=row["occurred_at"],
            received_at=row["received_at"],
            raw_data=row.get("raw_data", {}),
            impact=Impact(row["impact"]) if row.get("impact") else None,
            urgency=Urgency(row["urgency"]) if row.get("urgency") else None,
            priority=Priority(row["priority"]) if row.get("priority") else None,
            acknowledged_at=row.get("acknowledged_at"),
            acknowledged_by=row.get("acknowledged_by"),
            resolved_at=row.get("resolved_at"),
            resolved_by=row.get("resolved_by"),
            correlated_to_id=UUID(row["correlated_to_id"]) if row.get("correlated_to_id") else None,
            correlation_rule=row.get("correlation_rule"),
            fingerprint=row.get("fingerprint"),
            occurrence_count=row.get("occurrence_count", 1),
            last_occurrence_at=row.get("last_occurrence_at"),
            tags=row.get("tags", []),
            custom_fields=row.get("custom_fields", {}),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )


# Global instance
_alert_manager: AlertManager = None


def get_alert_manager() -> AlertManager:
    """Get the global AlertManager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
