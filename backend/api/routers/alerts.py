"""
Alerts API Router - FastAPI.

Routes for alert management.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, List
import logging

from backend.database import get_db
from backend.utils.responses import success_response, error_response, list_response

logger = logging.getLogger(__name__)

router = APIRouter()


class AlertRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    condition_type: str  # threshold, pattern, absence
    condition_config: dict
    severity: str = "warning"  # info, warning, critical
    notification_targets: Optional[List[int]] = None
    enabled: bool = True


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    condition_config: Optional[dict] = None
    severity: Optional[str] = None
    notification_targets: Optional[List[int]] = None
    enabled: Optional[bool] = None


class AlertAcknowledge(BaseModel):
    acknowledged_by: str
    notes: Optional[str] = None


@router.get("")
async def list_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List active alerts."""
    db = get_db()
    
    query = """
        SELECT id, rule_id, alert_key, severity, category, title, message, 
               details, status, triggered_at, acknowledged_at, acknowledged_by, resolved_at
        FROM alert_history
        WHERE 1=1
    """
    params = []
    
    if status:
        query += " AND status = %s"
        params.append(status)
    if severity:
        query += " AND severity = %s"
        params.append(severity)
    
    query += " ORDER BY triggered_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    with db.cursor() as cursor:
        cursor.execute(query, params)
        alerts = [dict(row) for row in cursor.fetchall()]
    
    return list_response(alerts)


@router.get("/stats")
async def get_alert_stats():
    """Get alert statistics."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'active') as active,
                COUNT(*) FILTER (WHERE status = 'acknowledged') as acknowledged,
                COUNT(*) FILTER (WHERE status = 'resolved') as resolved,
                COUNT(*) FILTER (WHERE severity = 'critical') as critical,
                COUNT(*) FILTER (WHERE severity = 'warning') as warning,
                COUNT(*) FILTER (WHERE severity = 'info') as info,
                COUNT(*) FILTER (WHERE triggered_at > NOW() - INTERVAL '24 hours') as last_24h
            FROM alert_history
        """)
        stats = dict(cursor.fetchone())
    return success_response(stats)


@router.get("/history")
async def get_alert_history(days: int = 7):
    """Get alert history for the specified number of days."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, rule_id, alert_key, severity, category, title, message,
                   status, triggered_at, acknowledged_at, resolved_at
            FROM alert_history
            WHERE triggered_at > NOW() - INTERVAL '%s days'
            ORDER BY triggered_at DESC
        """, (days,))
        history = [dict(row) for row in cursor.fetchall()]
    return list_response(history)


@router.get("/rules")
async def list_alert_rules():
    """List all alert rules."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, description, condition_type, condition_config,
                   severity, category, cooldown_minutes, enabled, created_at, updated_at
            FROM alert_rules
            ORDER BY name
        """)
        rules = [dict(row) for row in cursor.fetchall()]
    return list_response(rules)


@router.post("/rules")
async def create_alert_rule(req: AlertRuleCreate):
    """Create a new alert rule."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            INSERT INTO alert_rules 
            (name, description, condition_type, condition_config, severity, notification_targets, enabled)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, name, condition_type, severity, enabled, created_at
        """, (
            req.name, req.description, req.condition_type, req.condition_config,
            req.severity, req.notification_targets, req.enabled
        ))
        rule = dict(cursor.fetchone())
        db.commit()
    return success_response(rule)


@router.get("/rules/{rule_id}")
async def get_alert_rule(rule_id: int):
    """Get an alert rule by ID."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, description, condition_type, condition_config,
                   severity, notification_targets, enabled, created_at
            FROM alert_rules WHERE id = %s
        """, (rule_id,))
        rule = cursor.fetchone()
        if not rule:
            return error_response('NOT_FOUND', 'Alert rule not found')
    return success_response(dict(rule))


@router.put("/rules/{rule_id}")
async def update_alert_rule(rule_id: int, req: AlertRuleUpdate):
    """Update an alert rule."""
    updates = []
    params = []
    
    if req.name is not None:
        updates.append("name = %s")
        params.append(req.name)
    if req.description is not None:
        updates.append("description = %s")
        params.append(req.description)
    if req.condition_config is not None:
        updates.append("condition_config = %s")
        params.append(req.condition_config)
    if req.severity is not None:
        updates.append("severity = %s")
        params.append(req.severity)
    if req.notification_targets is not None:
        updates.append("notification_targets = %s")
        params.append(req.notification_targets)
    if req.enabled is not None:
        updates.append("enabled = %s")
        params.append(req.enabled)
    
    if not updates:
        return error_response('VALIDATION_ERROR', 'No fields to update')
    
    updates.append("updated_at = NOW()")
    params.append(rule_id)
    
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(f"""
            UPDATE alert_rules
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id, name, severity, enabled
        """, params)
        rule = cursor.fetchone()
        if not rule:
            return error_response('NOT_FOUND', 'Alert rule not found')
        db.commit()
    
    return success_response(dict(rule))


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(rule_id: int):
    """Delete an alert rule."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("DELETE FROM alert_rules WHERE id = %s RETURNING id", (rule_id,))
        deleted = cursor.fetchone()
        if not deleted:
            return error_response('NOT_FOUND', 'Alert rule not found')
        db.commit()
    return success_response({"deleted": True, "id": rule_id})


@router.get("/{alert_id}")
async def get_alert(alert_id: int):
    """Get an alert by ID."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT a.*, r.name as rule_name
            FROM alerts a
            LEFT JOIN alert_rules r ON a.rule_id = r.id
            WHERE a.id = %s
        """, (alert_id,))
        alert = cursor.fetchone()
        if not alert:
            return error_response('NOT_FOUND', 'Alert not found')
    return success_response(dict(alert))


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int, req: AlertAcknowledge):
    """Acknowledge an alert."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            UPDATE alerts
            SET status = 'acknowledged', acknowledged_at = NOW(), 
                acknowledged_by = %s, notes = %s
            WHERE id = %s AND status = 'active'
            RETURNING id
        """, (req.acknowledged_by, req.notes, alert_id))
        result = cursor.fetchone()
        if not result:
            return error_response('NOT_FOUND', 'Alert not found or already acknowledged')
        db.commit()
    return success_response({"acknowledged": True, "id": alert_id})


@router.post("/{alert_id}/resolve")
async def resolve_alert(alert_id: int):
    """Resolve an alert."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            UPDATE alerts
            SET status = 'resolved', resolved_at = NOW()
            WHERE id = %s AND status != 'resolved'
            RETURNING id
        """, (alert_id,))
        result = cursor.fetchone()
        if not result:
            return error_response('NOT_FOUND', 'Alert not found or already resolved')
        db.commit()
    return success_response({"resolved": True, "id": alert_id})


@router.get("/summary")
async def get_alerts_summary():
    """Get alerts summary."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE status = 'active') as active,
                COUNT(*) FILTER (WHERE status = 'acknowledged') as acknowledged,
                COUNT(*) FILTER (WHERE status = 'resolved' AND resolved_at > NOW() - INTERVAL '24 hours') as resolved_24h,
                COUNT(*) FILTER (WHERE severity = 'critical' AND status = 'active') as critical_active,
                COUNT(*) FILTER (WHERE severity = 'warning' AND status = 'active') as warning_active
            FROM alerts
        """)
        summary = dict(cursor.fetchone())
    return success_response(summary)
