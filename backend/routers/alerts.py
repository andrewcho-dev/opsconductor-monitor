"""
OpsConductor Alerts API Router

REST endpoints for alert management.
"""

import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from core.models import AlertStatus, Severity, Category
from core.alert_manager import get_alert_manager

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class AlertResponse(BaseModel):
    """Alert response model."""
    id: str
    source_system: str
    source_alert_id: str
    device_ip: Optional[str]
    device_name: Optional[str]
    severity: str
    category: str
    alert_type: str
    title: str
    message: Optional[str]
    status: str
    source_status: Optional[str]
    is_clear: bool
    priority: Optional[str]
    impact: Optional[str]
    urgency: Optional[str]
    occurred_at: datetime
    received_at: datetime
    resolved_at: Optional[datetime]
    correlated_to_id: Optional[str]
    correlation_rule: Optional[str]
    occurrence_count: int
    tags: List[str] = []

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """Paginated alert list response."""
    success: bool = True
    data: List[AlertResponse]
    meta: dict


class AlertDetailResponse(BaseModel):
    """Single alert detail response."""
    success: bool = True
    data: AlertResponse


class AlertStatsResponse(BaseModel):
    """Alert statistics response."""
    success: bool = True
    data: dict


class AcknowledgeRequest(BaseModel):
    """Request to acknowledge an alert."""
    notes: Optional[str] = None


class ResolveRequest(BaseModel):
    """Request to resolve an alert."""
    notes: Optional[str] = None


class AddNoteRequest(BaseModel):
    """Request to add a note to an alert."""
    notes: str


class BulkActionRequest(BaseModel):
    """Request for bulk alert actions."""
    alert_ids: List[str]
    notes: Optional[str] = None


class BulkActionResponse(BaseModel):
    """Response for bulk actions."""
    success: bool = True
    data: dict


# =============================================================================
# Helper Functions
# =============================================================================

def alert_to_response(alert) -> AlertResponse:
    """Convert Alert model to response."""
    return AlertResponse(
        id=str(alert.id),
        source_system=alert.source_system,
        source_alert_id=alert.source_alert_id,
        device_ip=alert.device_ip,
        device_name=alert.device_name,
        severity=alert.severity.value if hasattr(alert.severity, 'value') else alert.severity,
        category=alert.category.value if hasattr(alert.category, 'value') else alert.category,
        alert_type=alert.alert_type,
        title=alert.title,
        message=alert.message,
        status=alert.status.value if hasattr(alert.status, 'value') else alert.status,
        source_status=alert.source_status,
        is_clear=alert.is_clear,
        priority=alert.priority.value if alert.priority and hasattr(alert.priority, 'value') else alert.priority,
        impact=alert.impact.value if alert.impact and hasattr(alert.impact, 'value') else alert.impact,
        urgency=alert.urgency.value if alert.urgency and hasattr(alert.urgency, 'value') else alert.urgency,
        occurred_at=alert.occurred_at,
        received_at=alert.received_at,
        resolved_at=alert.resolved_at,
        correlated_to_id=str(alert.correlated_to_id) if alert.correlated_to_id else None,
        correlation_rule=alert.correlation_rule,
        occurrence_count=alert.occurrence_count,
        tags=alert.tags or [],
    )


def get_current_user() -> str:
    """Get current user from auth context. Placeholder for now."""
    # TODO: Integrate with actual auth
    return "system"


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=AlertListResponse)
async def list_alerts(
    status: Optional[str] = Query(None, description="Filter by status (active, acknowledged, etc.)"),
    severity: Optional[str] = Query(None, description="Filter by severity (comma-separated)"),
    category: Optional[str] = Query(None, description="Filter by category (comma-separated)"),
    device_ip: Optional[str] = Query(None, description="Filter by device IP"),
    source_system: Optional[str] = Query(None, description="Filter by source system"),
    search: Optional[str] = Query(None, description="Search in title and message"),
    from_time: Optional[datetime] = Query(None, alias="from", description="Start time"),
    to_time: Optional[datetime] = Query(None, alias="to", description="End time"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(100, ge=1, le=1000, description="Items per page"),
):
    """
    List alerts with filtering and pagination.
    """
    manager = get_alert_manager()
    
    # Parse filters
    status_list = None
    if status and status != "all":
        status_list = [AlertStatus(s.strip()) for s in status.split(",")]
    
    severity_list = None
    if severity:
        severity_list = [Severity(s.strip()) for s in severity.split(",")]
    
    category_list = None
    if category:
        category_list = [Category(c.strip()) for c in category.split(",")]
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Query alerts
    alerts = await manager.get_alerts(
        status=status_list,
        severity=severity_list,
        category=category_list,
        device_ip=device_ip,
        source_system=source_system,
        from_time=from_time,
        to_time=to_time,
        limit=per_page,
        offset=offset,
    )
    
    # Get total count
    total = await manager.get_alert_count(
        status=status_list,
        severity=severity_list,
        category=category_list,
    )
    
    return AlertListResponse(
        data=[alert_to_response(a) for a in alerts],
        meta={
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }
    )


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_stats():
    """
    Get alert statistics (counts by severity, category, status).
    """
    manager = get_alert_manager()
    stats = await manager.get_alert_stats()
    
    return AlertStatsResponse(data=stats)


@router.get("/{alert_id}", response_model=AlertDetailResponse)
async def get_alert(alert_id: str):
    """
    Get a single alert by ID.
    """
    manager = get_alert_manager()
    
    try:
        uuid = UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")
    
    alert = await manager.get_alert(uuid)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return AlertDetailResponse(data=alert_to_response(alert))


@router.get("/{alert_id}/history")
async def get_alert_history(alert_id: str):
    """
    Get history entries for an alert.
    """
    manager = get_alert_manager()
    
    try:
        uuid = UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")
    
    history = await manager.get_alert_history(uuid)
    
    return {
        "success": True,
        "data": history,
    }


@router.post("/{alert_id}/acknowledge", response_model=AlertDetailResponse)
async def acknowledge_alert(alert_id: str, request: AcknowledgeRequest):
    """
    Acknowledge an alert.
    """
    manager = get_alert_manager()
    user = get_current_user()
    
    try:
        uuid = UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")
    
    try:
        alert = await manager.acknowledge_alert(uuid, user, request.notes)
        return AlertDetailResponse(data=alert_to_response(alert))
    except Exception as e:
        logger.exception(f"Error acknowledging alert {alert_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{alert_id}/resolve", response_model=AlertDetailResponse)
async def resolve_alert(alert_id: str, request: ResolveRequest):
    """
    Resolve an alert.
    """
    manager = get_alert_manager()
    user = get_current_user()
    
    try:
        uuid = UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")
    
    try:
        alert = await manager.resolve_alert(uuid, user, request.notes)
        return AlertDetailResponse(data=alert_to_response(alert))
    except Exception as e:
        logger.exception(f"Error resolving alert {alert_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{alert_id}/notes")
async def add_note(alert_id: str, request: AddNoteRequest):
    """
    Add a note to an alert.
    """
    manager = get_alert_manager()
    user = get_current_user()
    
    try:
        uuid = UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")
    
    try:
        await manager.add_note(uuid, user, request.notes)
        return {"success": True, "message": "Note added"}
    except Exception as e:
        logger.exception(f"Error adding note to alert {alert_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk/acknowledge", response_model=BulkActionResponse)
async def bulk_acknowledge(request: BulkActionRequest):
    """
    Acknowledge multiple alerts at once.
    """
    manager = get_alert_manager()
    user = get_current_user()
    
    success_count = 0
    error_count = 0
    
    for alert_id in request.alert_ids:
        try:
            uuid = UUID(alert_id)
            await manager.acknowledge_alert(uuid, user, request.notes)
            success_count += 1
        except Exception as e:
            logger.warning(f"Failed to acknowledge alert {alert_id}: {e}")
            error_count += 1
    
    return BulkActionResponse(
        data={
            "success_count": success_count,
            "error_count": error_count,
            "total": len(request.alert_ids),
        }
    )


@router.post("/bulk/resolve", response_model=BulkActionResponse)
async def bulk_resolve(request: BulkActionRequest):
    """
    Resolve multiple alerts at once.
    """
    manager = get_alert_manager()
    user = get_current_user()
    
    success_count = 0
    error_count = 0
    
    for alert_id in request.alert_ids:
        try:
            uuid = UUID(alert_id)
            await manager.resolve_alert(uuid, user, request.notes)
            success_count += 1
        except Exception as e:
            logger.warning(f"Failed to resolve alert {alert_id}: {e}")
            error_count += 1
    
    return BulkActionResponse(
        data={
            "success_count": success_count,
            "error_count": error_count,
            "total": len(request.alert_ids),
        }
    )


@router.post("/bulk/delete", response_model=BulkActionResponse)
async def bulk_delete(request: BulkActionRequest):
    """
    Permanently delete multiple alerts.
    This action cannot be undone.
    """
    manager = get_alert_manager()
    user = get_current_user()
    
    success_count = 0
    error_count = 0
    
    for alert_id in request.alert_ids:
        try:
            uuid = UUID(alert_id)
            await manager.delete_alert(uuid)
            success_count += 1
        except Exception as e:
            logger.warning(f"Failed to delete alert {alert_id}: {e}")
            error_count += 1
    
    logger.info(f"User {user} deleted {success_count} alerts")
    
    return BulkActionResponse(
        data={
            "success_count": success_count,
            "error_count": error_count,
            "total": len(request.alert_ids),
        }
    )
