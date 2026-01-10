"""
Addon Management API Endpoints

REST API for managing connector/normalizer addons.
"""

import os
import tempfile
import shutil
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel

from backend.core.addon_manager import get_addon_manager, AddonInfo

router = APIRouter(prefix="/api/v1/addons", tags=["addons"])


class AddonResponse(BaseModel):
    """Response model for addon information."""
    id: str
    name: str
    version: str
    category: str
    description: str
    author: str
    enabled: bool
    installed: bool = True
    is_builtin: bool
    capabilities: List[str] = []


class AddonConfigUpdate(BaseModel):
    """Request model for updating addon config."""
    config: dict


class AddonActionResponse(BaseModel):
    """Response model for addon actions."""
    success: bool
    message: str
    addon_id: Optional[str] = None


@router.get("", response_model=List[AddonResponse])
async def list_addons(
    category: Optional[str] = Query(None, description="Filter by category: 'nms' or 'device'"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    include_uninstalled: bool = Query(False, description="Include uninstalled addons")
):
    """
    List all addons.
    
    Optionally filter by category or enabled status.
    Set include_uninstalled=true to also show uninstalled built-in addons.
    """
    manager = get_addon_manager()
    addons = manager.get_installed_addons(include_uninstalled=include_uninstalled)
    
    # Apply filters
    if category:
        addons = [a for a in addons if a.category == category]
    if enabled is not None:
        addons = [a for a in addons if a.enabled == enabled]
    
    return [
        AddonResponse(
            id=a.id,
            name=a.name,
            version=a.version,
            category=a.category,
            description=a.description,
            author=a.author,
            enabled=a.enabled,
            installed=getattr(a, 'installed', True),
            is_builtin=a.is_builtin,
            capabilities=a.manifest.get('capabilities', []),
        )
        for a in addons
    ]


@router.get("/{addon_id}", response_model=AddonResponse)
async def get_addon(addon_id: str):
    """Get details for a specific addon."""
    manager = get_addon_manager()
    addon = manager.get_addon(addon_id)
    
    if not addon:
        raise HTTPException(status_code=404, detail=f"Addon '{addon_id}' not found")
    
    return AddonResponse(
        id=addon.id,
        name=addon.name,
        version=addon.version,
        category=addon.category,
        description=addon.description,
        author=addon.author,
        enabled=addon.enabled,
        is_builtin=addon.is_builtin,
        capabilities=addon.manifest.get('capabilities', []),
    )


@router.post("/install", response_model=AddonActionResponse)
async def install_addon(file: UploadFile = File(...)):
    """
    Install an addon from a zip file upload.
    
    The zip file must contain:
    - manifest.json with addon metadata
    - backend/connector.py with Connector class
    - backend/normalizer.py with Normalizer class
    """
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a .zip archive")
    
    # Save uploaded file to temp location
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        # Install the addon
        manager = get_addon_manager()
        result = manager.install_addon(temp_path)
        
        if result['success']:
            return AddonActionResponse(
                success=True,
                message=f"Successfully installed addon '{result['name']}' v{result['version']}",
                addon_id=result['addon_id'],
            )
        else:
            raise HTTPException(status_code=400, detail=result['error'])
    
    finally:
        # Clean up temp files
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/{addon_id}/enable", response_model=AddonActionResponse)
async def enable_addon(addon_id: str):
    """Enable an addon."""
    manager = get_addon_manager()
    addon = manager.get_addon(addon_id)
    
    if not addon:
        raise HTTPException(status_code=404, detail=f"Addon '{addon_id}' not found")
    
    success = manager.enable_addon(addon_id)
    
    return AddonActionResponse(
        success=success,
        message=f"Addon '{addon_id}' enabled" if success else f"Failed to enable addon '{addon_id}'",
        addon_id=addon_id,
    )


@router.post("/{addon_id}/disable", response_model=AddonActionResponse)
async def disable_addon(addon_id: str):
    """Disable an addon."""
    manager = get_addon_manager()
    addon = manager.get_addon(addon_id)
    
    if not addon:
        raise HTTPException(status_code=404, detail=f"Addon '{addon_id}' not found")
    
    success = manager.disable_addon(addon_id)
    
    return AddonActionResponse(
        success=success,
        message=f"Addon '{addon_id}' disabled" if success else f"Failed to disable addon '{addon_id}'",
        addon_id=addon_id,
    )


@router.delete("/{addon_id}", response_model=AddonActionResponse)
async def uninstall_addon(addon_id: str):
    """
    Uninstall an addon.
    
    For built-in addons: Removes DB mappings, marks as uninstalled (can be reinstalled).
    For user addons: Removes DB mappings and deletes all addon files.
    """
    manager = get_addon_manager()
    addon = manager.get_addon(addon_id)
    
    if not addon:
        raise HTTPException(status_code=404, detail=f"Addon '{addon_id}' not found")
    
    success = manager.uninstall_addon(addon_id)
    
    action = "uninstalled" if not addon.is_builtin else "uninstalled (can be reinstalled)"
    return AddonActionResponse(
        success=success,
        message=f"Addon '{addon_id}' {action}" if success else f"Failed to uninstall addon '{addon_id}'",
        addon_id=addon_id,
    )


@router.post("/{addon_id}/reinstall", response_model=AddonActionResponse)
async def reinstall_addon(addon_id: str):
    """
    Reinstall a previously uninstalled built-in addon.
    
    Re-runs the install migration to restore DB mappings.
    """
    manager = get_addon_manager()
    addon = manager.get_addon(addon_id)
    
    if not addon:
        raise HTTPException(status_code=404, detail=f"Addon '{addon_id}' not found")
    
    if not addon.is_builtin:
        raise HTTPException(status_code=400, detail="Use /install for user addons")
    
    result = manager.reinstall_addon(addon_id)
    
    if result['success']:
        return AddonActionResponse(
            success=True,
            message=f"Addon '{addon_id}' reinstalled successfully",
            addon_id=addon_id,
        )
    else:
        raise HTTPException(status_code=400, detail=result.get('error', 'Reinstall failed'))


@router.put("/{addon_id}/config", response_model=AddonActionResponse)
async def update_addon_config(addon_id: str, body: AddonConfigUpdate):
    """Update addon configuration."""
    manager = get_addon_manager()
    addon = manager.get_addon(addon_id)
    
    if not addon:
        raise HTTPException(status_code=404, detail=f"Addon '{addon_id}' not found")
    
    success = manager.update_addon_config(addon_id, body.config)
    
    return AddonActionResponse(
        success=success,
        message=f"Configuration updated for addon '{addon_id}'" if success else f"Failed to update configuration",
        addon_id=addon_id,
    )


@router.get("/{addon_id}/config")
async def get_addon_config(addon_id: str):
    """Get addon configuration."""
    manager = get_addon_manager()
    addon = manager.get_addon(addon_id)
    
    if not addon:
        raise HTTPException(status_code=404, detail=f"Addon '{addon_id}' not found")
    
    return {
        "addon_id": addon_id,
        "config": addon.config,
        "config_schema": addon.manifest.get('config_schema', {}),
    }
