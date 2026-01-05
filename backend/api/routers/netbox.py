"""
NetBox API Router - FastAPI.

Routes for NetBox integration.
"""

import os
from fastapi import APIRouter, Request, Query
from pydantic import BaseModel
from typing import Optional, List
import logging

from backend.database import get_db
from backend.utils.responses import success_response, error_response, list_response

logger = logging.getLogger(__name__)

router = APIRouter()


def get_netbox_settings():
    """Get NetBox configuration from database or environment."""
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT key, value FROM system_settings 
                WHERE key IN ('netbox_url', 'netbox_token', 'netbox_verify_ssl')
            """)
            settings = {row['key']: row['value'] for row in cursor.fetchall()}
            return {
                'url': settings.get('netbox_url', os.environ.get('NETBOX_URL', '')),
                'token': settings.get('netbox_token', os.environ.get('NETBOX_TOKEN', '')),
                'verify_ssl': settings.get('netbox_verify_ssl', 'true'),
            }
    except Exception:
        return {
            'url': os.environ.get('NETBOX_URL', ''),
            'token': os.environ.get('NETBOX_TOKEN', ''),
            'verify_ssl': 'true',
        }


def get_netbox_service():
    """Get configured NetBox service instance."""
    from backend.services.netbox_service import NetBoxService
    
    settings = get_netbox_settings()
    return NetBoxService(
        url=settings.get('url', ''),
        token=settings.get('token', ''),
        verify_ssl=settings.get('verify_ssl', 'true').lower() == 'true'
    )


class NetBoxSettingsUpdate(BaseModel):
    url: Optional[str] = None
    token: Optional[str] = None
    verify_ssl: Optional[bool] = None


@router.get("/status")
async def get_netbox_status():
    """Get NetBox connection status."""
    try:
        netbox = get_netbox_service()
        if not netbox.is_configured:
            return success_response({
                "configured": False,
                "connected": False,
                "message": "NetBox not configured"
            })
        
        # Test connection
        result = netbox.get_devices(limit=1)
        return success_response({
            "configured": True,
            "connected": True,
            "url": netbox.url
        })
    except Exception as e:
        return success_response({
            "configured": True,
            "connected": False,
            "error": str(e)
        })


@router.get("/settings")
async def get_settings():
    """Get NetBox settings (without token)."""
    settings = get_netbox_settings()
    return success_response({
        "url": settings.get('url', ''),
        "token": settings.get('token', ''),
        "verify_ssl": settings.get('verify_ssl', 'true') == 'true',
        "configured": bool(settings.get('url') and settings.get('token'))
    })


class NetBoxTestRequest(BaseModel):
    url: str
    token: str
    verify_ssl: bool = True


@router.post("/test")
async def test_netbox_connection(req: NetBoxTestRequest):
    """Test NetBox connectivity with provided credentials."""
    try:
        from backend.services.netbox_service import NetBoxService
        
        netbox = NetBoxService(
            url=req.url,
            token=req.token,
            verify_ssl=req.verify_ssl
        )
        
        # Test connection by fetching devices (limit 1)
        result = netbox.get_devices(limit=1)
        
        return success_response({
            "connected": True,
            "netbox_version": "connected",
            "url": req.url
        })
    except Exception as e:
        logger.error(f"NetBox test error: {e}")
        return success_response({
            "connected": False,
            "error": str(e)
        })


@router.put("/settings")
async def update_settings(req: NetBoxSettingsUpdate):
    """Update NetBox settings."""
    db = get_db()
    with db.cursor() as cursor:
        if req.url is not None:
            cursor.execute("""
                INSERT INTO settings (key, value) VALUES ('netbox_url', %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (req.url,))
        if req.token is not None:
            cursor.execute("""
                INSERT INTO settings (key, value) VALUES ('netbox_token', %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (req.token,))
        if req.verify_ssl is not None:
            cursor.execute("""
                INSERT INTO settings (key, value) VALUES ('netbox_verify_ssl', %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, ('true' if req.verify_ssl else 'false',))
        db.commit()
    
    return success_response({"updated": True})


@router.get("/devices")
async def get_devices(
    q: Optional[str] = None,
    site: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 1000
):
    """Get devices from NetBox."""
    try:
        netbox = get_netbox_service()
        if not netbox.is_configured:
            return list_response([])
        
        result = netbox.get_devices(q=q, site=site, role=role, status=status, limit=limit)
        return success_response({
            "devices": result.get('results', []),
            "count": result.get('count', 0)
        })
    except Exception as e:
        logger.error(f"NetBox devices error: {e}")
        return error_response('NETBOX_ERROR', str(e))


@router.get("/devices/{device_id}")
async def get_device(device_id: int):
    """Get a specific device from NetBox."""
    try:
        netbox = get_netbox_service()
        if not netbox.is_configured:
            return error_response('NOT_CONFIGURED', 'NetBox not configured')
        
        device = netbox.get_device(device_id)
        if not device:
            return error_response('NOT_FOUND', 'Device not found')
        
        return success_response(device)
    except Exception as e:
        logger.error(f"NetBox device error: {e}")
        return error_response('NETBOX_ERROR', str(e))


@router.get("/sites")
async def get_sites(limit: int = 1000):
    """Get sites from NetBox."""
    try:
        netbox = get_netbox_service()
        if not netbox.is_configured:
            return list_response([])
        
        result = netbox.get_sites(limit=limit)
        return success_response({
            "sites": result.get('results', []),
            "count": result.get('count', 0)
        })
    except Exception as e:
        logger.error(f"NetBox sites error: {e}")
        return error_response('NETBOX_ERROR', str(e))


@router.get("/device-types")
async def get_device_types(limit: int = 1000):
    """Get device types from NetBox."""
    try:
        netbox = get_netbox_service()
        if not netbox.is_configured:
            return list_response([])
        
        result = netbox.get_device_types(limit=limit)
        return success_response({
            "device_types": result.get('results', []),
            "count": result.get('count', 0)
        })
    except Exception as e:
        logger.error(f"NetBox device types error: {e}")
        return error_response('NETBOX_ERROR', str(e))


@router.get("/device-roles")
async def get_device_roles(limit: int = 1000):
    """Get device roles from NetBox."""
    try:
        netbox = get_netbox_service()
        if not netbox.is_configured:
            return list_response([])
        
        result = netbox.get_device_roles(limit=limit)
        return success_response({
            "device_roles": result.get('results', []),
            "count": result.get('count', 0)
        })
    except Exception as e:
        logger.error(f"NetBox device roles error: {e}")
        return error_response('NETBOX_ERROR', str(e))


@router.post("/sync")
async def sync_devices():
    """Sync devices from NetBox to local cache."""
    try:
        netbox = get_netbox_service()
        if not netbox.is_configured:
            return error_response('NOT_CONFIGURED', 'NetBox not configured')
        
        result = netbox.get_devices(limit=10000)
        devices = result.get('results', [])
        
        db = get_db()
        synced = 0
        with db.cursor() as cursor:
            for d in devices:
                primary_ip = d.get('primary_ip4') or d.get('primary_ip') or {}
                ip_address = primary_ip.get('address', '').split('/')[0] if primary_ip else None
                
                if not ip_address:
                    continue
                
                cursor.execute("""
                    INSERT INTO netbox_device_cache 
                    (netbox_device_id, device_name, device_ip, device_type, manufacturer, site_name, role_name, cached_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (netbox_device_id) DO UPDATE SET
                        device_name = EXCLUDED.device_name,
                        device_ip = EXCLUDED.device_ip,
                        device_type = EXCLUDED.device_type,
                        manufacturer = EXCLUDED.manufacturer,
                        site_name = EXCLUDED.site_name,
                        role_name = EXCLUDED.role_name,
                        cached_at = NOW()
                """, (
                    d.get('id'),
                    d.get('name', ''),
                    ip_address,
                    d.get('device_type', {}).get('model', '') if d.get('device_type') else '',
                    d.get('device_type', {}).get('manufacturer', {}).get('name', '') if d.get('device_type') else '',
                    d.get('site', {}).get('name', '') if d.get('site') else '',
                    d.get('role', {}).get('name', '') if d.get('role') else '',
                ))
                synced += 1
            db.commit()
        
        return success_response({
            "synced": synced,
            "total_in_netbox": len(devices)
        })
    except Exception as e:
        logger.error(f"NetBox sync error: {e}")
        return error_response('SYNC_ERROR', str(e))


@router.get("/cache")
async def get_cached_devices():
    """Get devices from local NetBox cache."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT netbox_device_id, device_name, device_ip, device_type, 
                   manufacturer, site_name, role_name, cached_at
            FROM netbox_device_cache
            ORDER BY device_name
        """)
        devices = [dict(row) for row in cursor.fetchall()]
    return list_response(devices)
