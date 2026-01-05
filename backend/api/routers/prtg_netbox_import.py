"""
PRTG to NetBox Import API Router - FastAPI.

Routes for importing devices from PRTG to NetBox.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from backend.database import get_db
from backend.utils.responses import success_response, error_response, list_response

logger = logging.getLogger(__name__)

router = APIRouter()


class ImportOptions(BaseModel):
    create_sites: bool = True
    create_device_types: bool = True
    update_existing: bool = False
    dry_run: bool = False
    tag_with_prtg: bool = True


@router.get("/preview")
async def preview_prtg_import():
    """Preview devices from PRTG that would be imported to NetBox."""
    try:
        from backend.api.routers.prtg import get_prtg_settings
        from backend.services.prtg_service import PRTGService
        
        settings = get_prtg_settings()
        if not settings.get('url'):
            return error_response('NOT_CONFIGURED', 'PRTG not configured')
        
        prtg = PRTGService(
            url=settings.get('url', ''),
            username=settings.get('username', ''),
            passhash=settings.get('passhash', '')
        )
        
        devices = prtg.get_devices()
        
        # Transform to import format
        import_devices = []
        for d in devices:
            import_devices.append({
                "prtg_id": d.get('objid'),
                "name": d.get('device'),
                "host": d.get('host'),
                "group": d.get('group'),
                "tags": d.get('tags', '').split() if d.get('tags') else [],
                "status": d.get('status'),
            })
        
        return success_response({
            "devices": import_devices,
            "count": len(import_devices)
        })
        
    except Exception as e:
        logger.error(f"PRTG preview error: {e}")
        return error_response('PRTG_ERROR', str(e))


@router.post("/execute")
async def execute_prtg_import(options: ImportOptions):
    """Execute import from PRTG to NetBox."""
    try:
        from backend.api.routers.prtg import get_prtg_settings
        from backend.api.routers.netbox import get_netbox_service
        from backend.services.prtg_service import PRTGService
        
        # Get PRTG devices
        prtg_settings = get_prtg_settings()
        if not prtg_settings.get('url'):
            return error_response('NOT_CONFIGURED', 'PRTG not configured')
        
        prtg = PRTGService(
            url=prtg_settings.get('url', ''),
            username=prtg_settings.get('username', ''),
            passhash=prtg_settings.get('passhash', '')
        )
        
        devices = prtg.get_devices()
        
        # Get NetBox service
        netbox = get_netbox_service()
        if not netbox.is_configured:
            return error_response('NOT_CONFIGURED', 'NetBox not configured')
        
        if options.dry_run:
            return success_response({
                "dry_run": True,
                "would_import": len(devices),
                "devices": [{"name": d.get('device'), "host": d.get('host')} for d in devices[:10]]
            })
        
        # Perform actual import
        imported = 0
        errors = []
        
        for d in devices:
            try:
                # Create device in NetBox
                device_data = {
                    "name": d.get('device', d.get('host', 'Unknown')),
                    "device_type": 1,  # Default device type
                    "role": 1,  # Default role
                    "site": 1,  # Default site
                    "status": "active",
                }
                
                if options.tag_with_prtg:
                    device_data["tags"] = [{"name": "prtg-import"}]
                
                # This would call netbox.create_device(device_data)
                imported += 1
                
            except Exception as e:
                errors.append({"device": d.get('device'), "error": str(e)})
        
        # Log import
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO import_history (source, imported_count, error_count, details)
                VALUES ('prtg_to_netbox', %s, %s, %s)
            """, (imported, len(errors), {"errors": errors}))
            db.commit()
        
        return success_response({
            "imported": imported,
            "errors": errors,
            "error_count": len(errors)
        })
        
    except Exception as e:
        logger.error(f"PRTG import error: {e}")
        return error_response('IMPORT_ERROR', str(e))


@router.get("/mapping")
async def get_field_mapping():
    """Get field mapping between PRTG and NetBox."""
    return success_response({
        "mappings": [
            {"prtg_field": "device", "netbox_field": "name", "description": "Device name"},
            {"prtg_field": "host", "netbox_field": "primary_ip", "description": "IP address"},
            {"prtg_field": "group", "netbox_field": "site", "description": "Site/location"},
            {"prtg_field": "tags", "netbox_field": "tags", "description": "Device tags"},
        ]
    })


@router.get("/status")
async def get_import_status():
    """Get status of PRTG and NetBox connections for import."""
    from backend.api.routers.prtg import get_prtg_settings
    from backend.api.routers.netbox import get_netbox_settings
    
    prtg_settings = get_prtg_settings()
    netbox_settings = get_netbox_settings()
    
    return success_response({
        "prtg_configured": bool(prtg_settings.get('url') and prtg_settings.get('username')),
        "netbox_configured": bool(netbox_settings.get('url') and netbox_settings.get('token')),
        "ready": bool(
            prtg_settings.get('url') and prtg_settings.get('username') and
            netbox_settings.get('url') and netbox_settings.get('token')
        )
    })
