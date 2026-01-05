"""
Notifications API Router - FastAPI.

Routes for notification management and testing.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, List
import logging

from backend.database import get_db
from backend.utils.responses import success_response, error_response, list_response

logger = logging.getLogger(__name__)

router = APIRouter()


class NotificationTargetCreate(BaseModel):
    name: str
    type: str  # email, slack, teams, webhook, etc.
    config: dict
    enabled: bool = True


class NotificationTargetUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    config: Optional[dict] = None
    enabled: Optional[bool] = None


class TestNotificationRequest(BaseModel):
    target_id: Optional[int] = None
    message: Optional[str] = "This is a test notification from OpsConductor"
    title: Optional[str] = "Test Notification"


@router.get("/targets")
async def list_notification_targets():
    """List all notification targets."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, type, config, enabled, created_at, updated_at
            FROM notification_targets
            ORDER BY name
        """)
        targets = [dict(row) for row in cursor.fetchall()]
    return list_response(targets)


@router.post("/targets")
async def create_notification_target(req: NotificationTargetCreate):
    """Create a new notification target."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            INSERT INTO notification_targets (name, type, config, enabled)
            VALUES (%s, %s, %s, %s)
            RETURNING id, name, type, config, enabled, created_at
        """, (req.name, req.type, req.config, req.enabled))
        target = dict(cursor.fetchone())
        db.commit()
    return success_response(target)


@router.get("/targets/{target_id}")
async def get_notification_target(target_id: int):
    """Get a notification target by ID."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, type, config, enabled, created_at, updated_at
            FROM notification_targets WHERE id = %s
        """, (target_id,))
        target = cursor.fetchone()
        if not target:
            return error_response('NOT_FOUND', 'Notification target not found')
    return success_response(dict(target))


@router.put("/targets/{target_id}")
async def update_notification_target(target_id: int, req: NotificationTargetUpdate):
    """Update a notification target."""
    db = get_db()
    
    updates = []
    params = []
    
    if req.name is not None:
        updates.append("name = %s")
        params.append(req.name)
    if req.type is not None:
        updates.append("type = %s")
        params.append(req.type)
    if req.config is not None:
        updates.append("config = %s")
        params.append(req.config)
    if req.enabled is not None:
        updates.append("enabled = %s")
        params.append(req.enabled)
    
    if not updates:
        return error_response('VALIDATION_ERROR', 'No fields to update')
    
    updates.append("updated_at = NOW()")
    params.append(target_id)
    
    with db.cursor() as cursor:
        cursor.execute(f"""
            UPDATE notification_targets
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id, name, type, config, enabled, created_at, updated_at
        """, params)
        target = cursor.fetchone()
        if not target:
            return error_response('NOT_FOUND', 'Notification target not found')
        db.commit()
    
    return success_response(dict(target))


@router.delete("/targets/{target_id}")
async def delete_notification_target(target_id: int):
    """Delete a notification target."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("DELETE FROM notification_targets WHERE id = %s RETURNING id", (target_id,))
        deleted = cursor.fetchone()
        if not deleted:
            return error_response('NOT_FOUND', 'Notification target not found')
        db.commit()
    return success_response({"deleted": True, "id": target_id})


@router.post("/test")
async def test_notification(req: TestNotificationRequest):
    """Test sending a notification."""
    try:
        from notification_service import send_notification
        
        result = send_notification(
            title=req.title,
            message=req.message,
            level='info'
        )
        
        return success_response({'sent': True, 'result': result})
    except ImportError:
        return error_response('NOT_CONFIGURED', 'Notification service not configured')
    except Exception as e:
        logger.error(f"Notification test error: {e}")
        return error_response('SEND_FAILED', str(e))


@router.get("/history")
async def get_notification_history(limit: int = 50, offset: int = 0):
    """Get notification history."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, target_id, title, message, level, status, sent_at, error_message
            FROM notification_history
            ORDER BY sent_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        history = [dict(row) for row in cursor.fetchall()]
    return list_response(history)


@router.get("/types")
async def get_notification_types():
    """Get available notification types."""
    return success_response({
        "types": [
            {"id": "email", "name": "Email", "description": "Send notifications via email"},
            {"id": "slack", "name": "Slack", "description": "Send notifications to Slack channel"},
            {"id": "teams", "name": "Microsoft Teams", "description": "Send notifications to Teams channel"},
            {"id": "webhook", "name": "Webhook", "description": "Send notifications to a webhook URL"},
            {"id": "discord", "name": "Discord", "description": "Send notifications to Discord channel"},
        ]
    })


# =============================================================================
# CHANNELS
# =============================================================================

@router.get("/channels")
async def list_notification_channels():
    """List all notification channels."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, channel_type, config, enabled, created_at, updated_at,
                   last_test_at, last_test_success
            FROM notification_channels
            ORDER BY name
        """)
        channels = [dict(row) for row in cursor.fetchall()]
    return success_response({"channels": channels})


@router.get("/channels/{channel_id}")
async def get_notification_channel(channel_id: int):
    """Get a notification channel by ID."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, channel_type, config, enabled, created_at, updated_at,
                   last_test_at, last_test_success
            FROM notification_channels WHERE id = %s
        """, (channel_id,))
        channel = cursor.fetchone()
        if not channel:
            return error_response('NOT_FOUND', 'Channel not found')
    return success_response(dict(channel))


# =============================================================================
# RULES
# =============================================================================

@router.get("/rules")
async def list_notification_rules():
    """List all notification rules."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, description, enabled, trigger_type, trigger_config,
                   channel_ids, severity_filter, category_filter, cooldown_minutes,
                   last_triggered_at, created_at, updated_at, template_id
            FROM notification_rules
            ORDER BY name
        """)
        rules = [dict(row) for row in cursor.fetchall()]
    return success_response({"rules": rules})


@router.get("/rules/{rule_id}")
async def get_notification_rule(rule_id: int):
    """Get a notification rule by ID."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, description, enabled, trigger_type, trigger_config,
                   channel_ids, severity_filter, category_filter, cooldown_minutes,
                   last_triggered_at, created_at, updated_at, template_id
            FROM notification_rules WHERE id = %s
        """, (rule_id,))
        rule = cursor.fetchone()
        if not rule:
            return error_response('NOT_FOUND', 'Rule not found')
    return success_response(dict(rule))


# =============================================================================
# TEMPLATES
# =============================================================================

@router.get("/templates")
async def list_notification_templates():
    """List all notification templates."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, description, template_type, title_template, body_template,
                   available_variables, is_default, enabled, created_at, updated_at
            FROM notification_templates
            ORDER BY name
        """)
        templates = [dict(row) for row in cursor.fetchall()]
    return success_response({"templates": templates})


@router.get("/templates/{template_id}")
async def get_notification_template(template_id: int):
    """Get a notification template by ID."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, name, description, template_type, title_template, body_template,
                   available_variables, is_default, enabled, created_at, updated_at
            FROM notification_templates WHERE id = %s
        """, (template_id,))
        template = cursor.fetchone()
        if not template:
            return error_response('NOT_FOUND', 'Template not found')
    return success_response(dict(template))
