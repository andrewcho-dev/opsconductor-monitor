"""
Targets API Routes

CRUD operations for polling targets (devices/servers to monitor).
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.api.auth import get_current_user, require_role, Role, User
from backend.core.db import query, query_one, execute

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
    """Create a new target. Runs discovery if addon supports it."""
    import json
    from datetime import datetime
    from backend.core.addon_registry import get_registry
    from backend.core.clients import get_clients
    from backend.core.types import Credentials
    import logging
    import asyncio
    
    logger = logging.getLogger(__name__)
    
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
    addon = None
    manifest = {}
    if data.addon_id:
        addon_row = query_one("SELECT manifest FROM addons WHERE id = %s", (data.addon_id,))
        if addon_row and addon_row.get('manifest'):
            manifest = addon_row['manifest'] if isinstance(addon_row['manifest'], dict) else json.loads(addon_row['manifest'])
            if poll_interval == 300:  # Default value, check addon
                poll_interval = manifest.get('default_poll_interval', 300)
        
        # Get full addon with modules for discovery
        registry = get_registry()
        addon = registry.get(data.addon_id)
    
    # Start with provided config
    config = data.config.copy()
    
    # Run discovery if addon has discover module
    if addon and 'discover' in addon.modules:
        try:
            logger.info(f"Running discovery for {data.ip_address} on addon {data.addon_id}")
            
            # Get credentials from addon defaults
            default_creds = manifest.get('default_credentials', {})
            credentials = Credentials(
                username=config.get('username') or default_creds.get('username'),
                password=config.get('password') or default_creds.get('password'),
            )
            
            # Get HTTP client
            clients = get_clients()
            
            # Run discovery
            discover_module = addon.modules['discover']
            result = await discover_module.discover(
                ip=data.ip_address,
                credentials=credentials,
                http=clients.http,
                logger=logger
            )
            
            if result.success:
                # Merge discovery results into config
                discovery_config = result.to_config()
                discovery_config['discovery_timestamp'] = datetime.utcnow().isoformat()
                config.update(discovery_config)
                logger.info(f"Discovery successful for {data.ip_address}: model={result.model}, {len(result.supported_events)} events")
            else:
                logger.warning(f"Discovery failed for {data.ip_address}: {result.error}")
                config['discovered'] = False
                config['discovery_error'] = result.error
                
        except Exception as e:
            logger.error(f"Discovery error for {data.ip_address}: {e}")
            config['discovered'] = False
            config['discovery_error'] = str(e)
    
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
        json.dumps(config)
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
    resolve_alerts: bool = True,
    user: User = Depends(require_role(Role.ADMIN))
):
    """
    Delete a target.
    
    Args:
        target_id: ID of target to delete
        resolve_alerts: If True (default), auto-resolve active alerts for this device
    """
    existing = query_one("SELECT * FROM targets WHERE id = %s", (target_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Target not found")
    
    device_ip = existing['ip_address']
    addon_id = existing.get('addon_id')
    resolved_count = 0
    
    # Auto-resolve active alerts for this device
    if resolve_alerts and device_ip:
        result = execute("""
            UPDATE alerts 
            SET status = 'resolved', 
                resolved_at = NOW()
            WHERE device_ip = %s 
            AND status != 'resolved'
        """, (device_ip,))
        resolved_count = result if isinstance(result, int) else 0
    
    execute("DELETE FROM targets WHERE id = %s", (target_id,))
    
    return {
        "status": "deleted", 
        "id": target_id,
        "device_ip": device_ip,
        "alerts_resolved": resolved_count
    }


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
    
    from backend.tasks.tasks import poll_addon
    poll_addon.delay(target['addon_id'], target_id)
    
    return {"status": "poll_triggered", "target_id": target_id}


@router.post("/{target_id}/discover")
async def rediscover_target(
    target_id: int,
    user: User = Depends(require_role(Role.OPERATOR))
):
    """
    Re-run discovery for an existing target.
    
    Updates the target's config with fresh capability information.
    Useful after firmware upgrades or to fix discovery issues.
    """
    import json
    from datetime import datetime
    from backend.core.addon_registry import get_registry
    from backend.core.clients import get_clients
    from backend.core.types import Credentials
    import logging
    
    logger = logging.getLogger(__name__)
    
    target = query_one("SELECT * FROM targets WHERE id = %s", (target_id,))
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    addon_id = target.get('addon_id')
    if not addon_id:
        raise HTTPException(status_code=400, detail="Target has no addon configured")
    
    # Get addon with modules
    registry = get_registry()
    addon = registry.get(addon_id)
    
    if not addon or 'discover' not in addon.modules:
        raise HTTPException(status_code=400, detail="Addon does not support discovery")
    
    # Get credentials
    manifest = addon.manifest
    default_creds = manifest.get('default_credentials', {})
    config = target.get('config', {}) or {}
    
    credentials = Credentials(
        username=config.get('username') or default_creds.get('username'),
        password=config.get('password') or default_creds.get('password'),
    )
    
    # Run discovery
    clients = get_clients()
    discover_module = addon.modules['discover']
    
    try:
        result = await discover_module.discover(
            ip=target['ip_address'],
            credentials=credentials,
            http=clients.http,
            logger=logger
        )
    except Exception as e:
        logger.error(f"Discovery error for {target['ip_address']}: {e}")
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")
    
    if not result.success:
        raise HTTPException(status_code=400, detail=f"Discovery failed: {result.error}")
    
    # Update config with discovery results
    discovery_config = result.to_config()
    discovery_config['discovery_timestamp'] = datetime.utcnow().isoformat()
    config.update(discovery_config)
    
    # Save updated config
    execute(
        "UPDATE targets SET config = %s WHERE id = %s",
        (json.dumps(config), target_id)
    )
    
    return {
        "status": "discovered",
        "target_id": target_id,
        "model": result.model,
        "firmware_version": result.firmware_version,
        "supported_events_count": len(result.supported_events),
        "supported_events": result.supported_events,
        "has_ptz": result.has_ptz,
        "has_storage": result.has_storage,
    }
