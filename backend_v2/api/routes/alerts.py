"""
Alert Routes

RESTful API for alert management.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend_v2.api.auth import get_current_user, require_role, Role, User
from backend_v2.core.alert_engine import get_engine, Alert, Severity, Status

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertResponse(BaseModel):
    """Alert response model."""
    id: str
    addon_id: Optional[str]
    device_ip: str
    device_name: Optional[str]
    alert_type: str
    severity: str
    category: str
    title: str
    message: Optional[str]
    status: str
    is_clear: bool
    occurred_at: str
    received_at: str
    resolved_at: Optional[str]
    occurrence_count: int

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """Paginated alert list."""
    items: List[AlertResponse]
    total: int
    limit: int
    offset: int


class AlertStatsResponse(BaseModel):
    """Alert statistics."""
    total_active: int
    by_severity: dict
    by_status: dict
    by_addon: dict


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    status: Optional[List[str]] = Query(None),
    severity: Optional[List[str]] = Query(None),
    addon_id: Optional[str] = None,
    device_ip: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user)
):
    """
    List alerts with filters.
    
    - **status**: Filter by status (active, acknowledged, suppressed, resolved)
    - **severity**: Filter by severity (critical, major, minor, warning, info)
    - **addon_id**: Filter by addon
    - **device_ip**: Filter by device IP
    """
    engine = get_engine()
    alerts = await engine.get_alerts(
        status=status,
        severity=severity,
        addon_id=addon_id,
        device_ip=device_ip,
        limit=limit,
        offset=offset
    )
    
    # Get total count for pagination
    stats = await engine.get_stats()
    total = stats.get('total_active', len(alerts))
    
    return AlertListResponse(
        items=[AlertResponse(**a.to_dict()) for a in alerts],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_stats(user: User = Depends(get_current_user)):
    """Get alert statistics by severity, status, and addon."""
    engine = get_engine()
    stats = await engine.get_stats()
    return AlertStatsResponse(**stats)


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: UUID,
    user: User = Depends(get_current_user)
):
    """Get alert by ID."""
    engine = get_engine()
    alert = await engine.get_alert(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return AlertResponse(**alert.to_dict())


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: UUID,
    user: User = Depends(require_role(Role.OPERATOR))
):
    """Acknowledge an alert."""
    engine = get_engine()
    
    alert = await engine.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    if alert.status != Status.ACTIVE.value:
        raise HTTPException(status_code=400, detail="Only active alerts can be acknowledged")
    
    alert = await engine.acknowledge_alert(alert_id)
    return AlertResponse(**alert.to_dict())


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: UUID,
    user: User = Depends(require_role(Role.OPERATOR))
):
    """Manually resolve an alert."""
    engine = get_engine()
    
    alert = await engine.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    if alert.status == Status.RESOLVED.value:
        raise HTTPException(status_code=400, detail="Alert already resolved")
    
    alert = await engine.resolve_alert(alert_id, resolution_source='manual')
    return AlertResponse(**alert.to_dict())


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: UUID,
    user: User = Depends(require_role(Role.ADMIN))
):
    """Delete an alert (admin only)."""
    engine = get_engine()
    
    success = await engine.delete_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"status": "deleted", "alert_id": str(alert_id)}
