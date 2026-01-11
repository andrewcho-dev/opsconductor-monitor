"""
Addon Routes

RESTful API for addon management.
"""

from typing import List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from backend.api.auth import get_current_user, require_role, Role, User
from backend.core.addon_registry import (
    get_registry, reload_registry, list_all_addons,
    install_addon, uninstall_addon, enable_addon, disable_addon,
    get_addon_from_db, Addon
)

router = APIRouter(prefix="/addons", tags=["addons"])


class AddonResponse(BaseModel):
    """Addon response model."""
    id: str
    name: str
    version: str
    method: str
    category: str
    description: str
    enabled: bool

    class Config:
        from_attributes = True


class AddonDetailResponse(AddonResponse):
    """Addon detail with manifest."""
    manifest: dict


class AddonListResponse(BaseModel):
    """Addon list response."""
    items: List[AddonResponse]
    total: int


@router.get("", response_model=AddonListResponse)
async def list_addons(
    include_disabled: bool = False,
    user: User = Depends(get_current_user)
):
    """List all addons."""
    addons = list_all_addons(include_disabled=include_disabled)
    
    return AddonListResponse(
        items=[AddonResponse(
            id=a.id,
            name=a.name,
            version=a.version,
            method=a.method,
            category=a.category,
            description=a.description,
            enabled=a.enabled
        ) for a in addons],
        total=len(addons)
    )


@router.get("/{addon_id}", response_model=AddonDetailResponse)
async def get_addon(
    addon_id: str,
    user: User = Depends(get_current_user)
):
    """Get addon details including manifest."""
    addon = get_addon_from_db(addon_id)
    
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    
    return AddonDetailResponse(
        id=addon.id,
        name=addon.name,
        version=addon.version,
        method=addon.method,
        category=addon.category,
        description=addon.description,
        enabled=addon.enabled,
        manifest=addon.manifest
    )


class InstallAddonRequest(BaseModel):
    """Request to install addon from manifest."""
    manifest: dict


@router.post("/install", response_model=AddonResponse)
async def install_addon_endpoint(
    request: InstallAddonRequest,
    user: User = Depends(require_role(Role.ADMIN))
):
    """
    Install addon from manifest JSON.
    
    Required manifest fields:
    - id: Unique addon identifier
    - name: Display name
    - method: snmp_trap, webhook, api_poll, snmp_poll, or ssh
    """
    manifest = request.manifest
    
    # Validate required fields
    required = ['id', 'name', 'method']
    missing = [f for f in required if f not in manifest]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required manifest fields: {missing}"
        )
    
    # Validate method
    valid_methods = ['snmp_trap', 'webhook', 'api_poll', 'snmp_poll', 'ssh']
    if manifest['method'] not in valid_methods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid method. Must be one of: {valid_methods}"
        )
    
    try:
        addon = install_addon(manifest)
        reload_registry()
        
        return AddonResponse(
            id=addon.id,
            name=addon.name,
            version=addon.version,
            method=addon.method,
            category=addon.category,
            description=addon.description,
            enabled=addon.enabled
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_addon(
    file: UploadFile = File(...),
    user: User = Depends(require_role(Role.ADMIN))
):
    """
    Upload addon as ZIP file containing manifest.json.
    """
    import zipfile
    import io
    
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a ZIP archive")
    
    try:
        contents = await file.read()
        with zipfile.ZipFile(io.BytesIO(contents)) as zf:
            # Find manifest.json
            manifest_path = None
            for name in zf.namelist():
                if name.endswith('manifest.json'):
                    manifest_path = name
                    break
            
            if not manifest_path:
                raise HTTPException(status_code=400, detail="No manifest.json found in archive")
            
            manifest_data = zf.read(manifest_path)
            manifest = json.loads(manifest_data)
        
        addon = install_addon(manifest)
        reload_registry()
        
        return {
            "status": "installed",
            "addon_id": addon.id,
            "name": addon.name
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid manifest.json")
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{addon_id}")
async def uninstall_addon_endpoint(
    addon_id: str,
    user: User = Depends(require_role(Role.ADMIN))
):
    """Uninstall an addon."""
    addon = get_addon_from_db(addon_id)
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    
    success = uninstall_addon(addon_id)
    if success:
        reload_registry()
        return {"status": "uninstalled", "addon_id": addon_id}
    
    raise HTTPException(status_code=500, detail="Failed to uninstall addon")


@router.post("/{addon_id}/enable")
async def enable_addon_endpoint(
    addon_id: str,
    user: User = Depends(require_role(Role.OPERATOR))
):
    """Enable an addon."""
    addon = get_addon_from_db(addon_id)
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    
    success = enable_addon(addon_id)
    if success:
        reload_registry()
        return {"status": "enabled", "addon_id": addon_id}
    
    raise HTTPException(status_code=500, detail="Failed to enable addon")


@router.post("/{addon_id}/disable")
async def disable_addon_endpoint(
    addon_id: str,
    user: User = Depends(require_role(Role.OPERATOR))
):
    """Disable an addon."""
    addon = get_addon_from_db(addon_id)
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    
    success = disable_addon(addon_id)
    if success:
        reload_registry()
        return {"status": "disabled", "addon_id": addon_id}
    
    raise HTTPException(status_code=500, detail="Failed to disable addon")


class UpdateManifestRequest(BaseModel):
    """Request to update addon manifest."""
    manifest: dict


@router.put("/{addon_id}/manifest")
async def update_addon_manifest(
    addon_id: str,
    request: UpdateManifestRequest,
    user: User = Depends(require_role(Role.ADMIN))
):
    """
    Update addon manifest (for editing mappings, etc).
    Auto-resolves existing alerts for any alert types that were disabled.
    """
    from backend.core.db import execute, query
    
    addon = get_addon_from_db(addon_id)
    if not addon:
        raise HTTPException(status_code=404, detail="Addon not found")
    
    try:
        # Find alert types that are being disabled
        old_enabled = set()
        new_enabled = set()
        
        # Get currently enabled alert types
        for group in addon.manifest.get('alert_mappings', []):
            for alert in group.get('alerts', []):
                if alert.get('enabled', True):
                    old_enabled.add(alert['alert_type'])
        
        # Get newly enabled alert types from request
        for group in request.manifest.get('alert_mappings', []):
            for alert in group.get('alerts', []):
                if alert.get('enabled', True):
                    new_enabled.add(alert['alert_type'])
        
        # Alert types being disabled = was enabled, now not enabled
        disabled_types = old_enabled - new_enabled
        
        # Update manifest
        execute(
            "UPDATE addons SET manifest = %s, updated_at = NOW() WHERE id = %s",
            (json.dumps(request.manifest), addon_id)
        )
        
        # Auto-resolve alerts for disabled types
        resolved_count = 0
        for alert_type in disabled_types:
            result = execute(
                """UPDATE alerts 
                   SET status = 'resolved', resolved_at = NOW() 
                   WHERE addon_id = %s AND alert_type = %s AND status IN ('active', 'acknowledged')""",
                (addon_id, alert_type)
            )
            resolved_count += result
        
        # If poll interval changed, update all targets for this addon
        new_poll_interval = request.manifest.get('default_poll_interval')
        if new_poll_interval:
            execute(
                "UPDATE targets SET poll_interval = %s WHERE addon_id = %s",
                (int(new_poll_interval), addon_id)
            )
        
        reload_registry()
        return {
            "status": "updated", 
            "addon_id": addon_id, 
            "targets_updated": new_poll_interval is not None,
            "alerts_resolved": resolved_count,
            "disabled_types": list(disabled_types)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload")
async def reload_addons(
    user: User = Depends(require_role(Role.ADMIN))
):
    """Reload all addons from database."""
    count = reload_registry()
    return {"status": "reloaded", "addon_count": count}
