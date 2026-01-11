"""
Alert Routes

RESTful API for alert management.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.api.auth import get_current_user, require_role, Role, User
from backend.core.alert_engine import get_engine, Alert, Severity, Status
from backend.core.addon_registry import get_registry

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _get_alert_description(addon_id: str, alert_type: str) -> Optional[str]:
    """Get alert description from addon manifest."""
    registry = get_registry()
    addon = registry.get(addon_id)
    if not addon:
        return None
    
    for group in addon.manifest.get('alert_mappings', []):
        for alert in group.get('alerts', []):
            if alert.get('alert_type') == alert_type:
                return alert.get('description')
    return None


def _enrich_alert_response(alert: Alert) -> dict:
    """Enrich alert dict with description from manifest."""
    data = alert.to_dict()
    data['description'] = _get_alert_description(alert.addon_id, alert.alert_type)
    return data


class AlertResponse(BaseModel):
    """Alert response model."""
    id: str
    addon_id: Optional[str]
    fingerprint: Optional[str]
    device_ip: str
    device_name: Optional[str]
    alert_type: str
    severity: str
    category: str
    title: str
    description: Optional[str]  # From manifest alert_mappings
    message: Optional[str]
    status: str
    is_clear: bool
    occurred_at: str
    received_at: str
    created_at: Optional[str]
    acknowledged_at: Optional[str]
    resolved_at: Optional[str]
    occurrence_count: int
    raw_data: Optional[dict]  # Contains threshold values, etc.

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
        items=[AlertResponse(**_enrich_alert_response(a)) for a in alerts],
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
    
    return AlertResponse(**_enrich_alert_response(alert))


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
    return AlertResponse(**_enrich_alert_response(alert))


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
    return AlertResponse(**_enrich_alert_response(alert))


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
