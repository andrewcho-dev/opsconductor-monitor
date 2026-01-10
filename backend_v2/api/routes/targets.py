"""
Targets API Routes

CRUD operations for polling targets (devices/servers to monitor).
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend_v2.api.auth import get_current_user, require_role, Role, User
from backend_v2.core.db import query, query_one, execute

router = APIRouter(prefix="/targets", tags=["targets"])


class TargetCreate(BaseModel):
    name: str
    ip_address: str
    addon_id: Optional[str] = None
    poll_interval: int = 300
    enabled: bool = True
    config: Dict[str, Any] = {}


class TargetUpdate(BaseModel):
    name: Optional[str] = None
    ip_address: Optional[str] = None
    addon_id: Optional[str] = None
    poll_interval: Optional[int] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


@router.get("")
async def list_targets(
    addon_id: Optional[str] = None,
    enabled_only: bool = False,
    user: User = Depends(get_current_user)
):
    """List all targets, optionally filtered by addon."""
    sql = "SELECT * FROM targets WHERE 1=1"
    params = []
    
    if addon_id:
        sql += " AND addon_id = %s"
        params.append(addon_id)
    
    if enabled_only:
        sql += " AND enabled = true"
    
    sql += " ORDER BY name"
    
    targets = query(sql, tuple(params) if params else None)
    return {"items": targets, "total": len(targets)}


@router.get("/{target_id}")
async def get_target(
    target_id: int,
    user: User = Depends(get_current_user)
):
    """Get a specific target."""
    target = query_one("SELECT * FROM targets WHERE id = %s", (target_id,))
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    return target


@router.post("")
async def create_target(
    data: TargetCreate,
    user: User = Depends(require_role(Role.OPERATOR))
):
    """Create a new target."""
    import json
    
    # Check for duplicate IP for this addon
    if data.addon_id:
        existing = query_one(
            "SELECT id FROM targets WHERE ip_address = %s AND addon_id = %s",
            (data.ip_address, data.addon_id)
        )
        if existing:
            raise HTTPException(status_code=409, detail="Target with this IP already exists for this addon")
    
    # Get addon's default poll interval if not specified
    poll_interval = data.poll_interval
    if data.addon_id and poll_interval == 300:  # Default value, check addon
        addon = query_one("SELECT manifest FROM addons WHERE id = %s", (data.addon_id,))
        if addon and addon.get('manifest'):
            manifest = addon['manifest'] if isinstance(addon['manifest'], dict) else json.loads(addon['manifest'])
            poll_interval = manifest.get('default_poll_interval', 300)
    
    result = query_one("""
        INSERT INTO targets (name, ip_address, addon_id, poll_interval, enabled, config)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING *
    """, (
        data.name,
        data.ip_address,
        data.addon_id,
        poll_interval,
        data.enabled,
        json.dumps(data.config)
    ))
    
    return result


@router.put("/{target_id}")
async def update_target(
    target_id: int,
    data: TargetUpdate,
    user: User = Depends(require_role(Role.OPERATOR))
):
    """Update a target."""
    import json
    
    existing = query_one("SELECT * FROM targets WHERE id = %s", (target_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Target not found")
    
    updates = []
    params = []
    
    if data.name is not None:
        updates.append("name = %s")
        params.append(data.name)
    if data.ip_address is not None:
        updates.append("ip_address = %s")
        params.append(data.ip_address)
    if data.addon_id is not None:
        updates.append("addon_id = %s")
        params.append(data.addon_id if data.addon_id else None)
    if data.poll_interval is not None:
        updates.append("poll_interval = %s")
        params.append(data.poll_interval)
    if data.enabled is not None:
        updates.append("enabled = %s")
        params.append(data.enabled)
    if data.config is not None:
        updates.append("config = %s")
        params.append(json.dumps(data.config))
    
    if not updates:
        return existing
    
    params.append(target_id)
    sql = f"UPDATE targets SET {', '.join(updates)} WHERE id = %s RETURNING *"
    
    result = query_one(sql, tuple(params))
    return result


@router.delete("/{target_id}")
async def delete_target(
    target_id: int,
    user: User = Depends(require_role(Role.ADMIN))
):
    """Delete a target."""
    existing = query_one("SELECT * FROM targets WHERE id = %s", (target_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Target not found")
    
    execute("DELETE FROM targets WHERE id = %s", (target_id,))
    return {"status": "deleted", "id": target_id}


@router.post("/{target_id}/poll")
async def trigger_poll(
    target_id: int,
    user: User = Depends(require_role(Role.OPERATOR))
):
    """Trigger an immediate poll for a target."""
    target = query_one("SELECT * FROM targets WHERE id = %s", (target_id,))
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    if not target.get('addon_id'):
        raise HTTPException(status_code=400, detail="Target has no addon configured")
    
    from backend_v2.tasks.tasks import poll_addon
    poll_addon.delay(target['addon_id'], target_id)
    
    return {"status": "poll_triggered", "target_id": target_id}
