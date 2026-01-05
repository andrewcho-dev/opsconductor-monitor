"""
PRTG API Router - FastAPI.

Routes for PRTG integration.
"""

import os
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional
import logging

from backend.database import get_db
from backend.utils.responses import success_response, error_response, list_response

logger = logging.getLogger(__name__)

router = APIRouter()


def get_prtg_settings():
    """Get PRTG configuration from database or environment."""
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT key, value FROM system_settings 
                WHERE key LIKE 'prtg_%'
            """)
            settings = {row['key']: row['value'] for row in cursor.fetchall()}
            return {
                'url': settings.get('prtg_url', os.environ.get('PRTG_URL', '')),
                'username': settings.get('prtg_username', os.environ.get('PRTG_USERNAME', '')),
                'passhash': settings.get('prtg_passhash', os.environ.get('PRTG_PASSHASH', '')),
                'api_token': settings.get('prtg_api_token', os.environ.get('PRTG_API_TOKEN', '')),
                'verify_ssl': settings.get('prtg_verify_ssl', 'true'),
                'enabled': settings.get('prtg_enabled', 'false'),
            }
    except Exception:
        return {
            'url': os.environ.get('PRTG_URL', ''),
            'username': os.environ.get('PRTG_USERNAME', ''),
            'passhash': os.environ.get('PRTG_PASSHASH', ''),
            'api_token': os.environ.get('PRTG_API_TOKEN', ''),
            'verify_ssl': 'true',
            'enabled': 'false',
        }


class PRTGSettingsUpdate(BaseModel):
    url: Optional[str] = None
    username: Optional[str] = None
    passhash: Optional[str] = None


@router.get("/status")
async def get_prtg_status():
    """Get PRTG connection status."""
    settings = get_prtg_settings()
    # PRTG can be configured with either username/passhash OR api_token
    has_auth = (settings.get('username') and settings.get('passhash')) or settings.get('api_token')
    configured = bool(settings.get('url') and has_auth)
    
    if not configured:
        return success_response({
            "configured": False,
            "connected": False,
            "message": "PRTG not configured"
        })
    
    # Test connection would go here
    return success_response({
        "configured": True,
        "connected": True,
        "url": settings.get('url')
    })


@router.get("/settings")
async def get_settings():
    """Get PRTG settings (without passhash/token)."""
    settings = get_prtg_settings()
    has_auth = (settings.get('username') and settings.get('passhash')) or settings.get('api_token')
    return success_response({
        "url": settings.get('url', ''),
        "username": settings.get('username', ''),
        "has_api_token": bool(settings.get('api_token')),
        "verify_ssl": settings.get('verify_ssl', 'true').lower() == 'true',
        "enabled": settings.get('enabled', 'false').lower() == 'true',
        "configured": bool(settings.get('url') and has_auth)
    })


@router.put("/settings")
async def update_settings(req: PRTGSettingsUpdate):
    """Update PRTG settings."""
    db = get_db()
    with db.cursor() as cursor:
        if req.url is not None:
            cursor.execute("""
                INSERT INTO settings (key, value) VALUES ('prtg_url', %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (req.url,))
        if req.username is not None:
            cursor.execute("""
                INSERT INTO settings (key, value) VALUES ('prtg_username', %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (req.username,))
        if req.passhash is not None:
            cursor.execute("""
                INSERT INTO settings (key, value) VALUES ('prtg_passhash', %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (req.passhash,))
        db.commit()
    
    return success_response({"updated": True})


@router.get("/devices")
async def get_prtg_devices():
    """Get devices from PRTG."""
    try:
        from backend.services.prtg_service import PRTGService
        
        settings = get_prtg_settings()
        prtg = PRTGService(
            url=settings.get('url', ''),
            username=settings.get('username', ''),
            passhash=settings.get('passhash', '')
        )
        
        devices = prtg.get_devices()
        return success_response({
            "devices": devices,
            "count": len(devices)
        })
    except Exception as e:
        logger.error(f"PRTG devices error: {e}")
        return error_response('PRTG_ERROR', str(e))


@router.get("/sensors")
async def get_prtg_sensors(device_id: Optional[int] = None):
    """Get sensors from PRTG."""
    try:
        from backend.services.prtg_service import PRTGService
        
        settings = get_prtg_settings()
        prtg = PRTGService(
            url=settings.get('url', ''),
            username=settings.get('username', ''),
            passhash=settings.get('passhash', '')
        )
        
        sensors = prtg.get_sensors(device_id=device_id)
        return success_response({
            "sensors": sensors,
            "count": len(sensors)
        })
    except Exception as e:
        logger.error(f"PRTG sensors error: {e}")
        return error_response('PRTG_ERROR', str(e))


@router.get("/groups")
async def get_prtg_groups():
    """Get groups from PRTG."""
    try:
        from backend.services.prtg_service import PRTGService
        
        settings = get_prtg_settings()
        prtg = PRTGService(
            url=settings.get('url', ''),
            username=settings.get('username', ''),
            passhash=settings.get('passhash', '')
        )
        
        groups = prtg.get_groups()
        return success_response({
            "groups": groups,
            "count": len(groups)
        })
    except Exception as e:
        logger.error(f"PRTG groups error: {e}")
        return error_response('PRTG_ERROR', str(e))


@router.post("/test")
async def test_prtg_connection():
    """Test PRTG connection."""
    try:
        from backend.services.prtg_service import PRTGService
        
        settings = get_prtg_settings()
        prtg = PRTGService(
            url=settings.get('url', ''),
            username=settings.get('username', ''),
            passhash=settings.get('passhash', '')
        )
        
        result = prtg.test_connection()
        return success_response(result)
    except Exception as e:
        logger.error(f"PRTG test error: {e}")
        return error_response('PRTG_ERROR', str(e))
