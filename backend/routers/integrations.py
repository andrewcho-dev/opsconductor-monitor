"""
Integrations API Router (/integrations/v1)

Handles NetBox, PRTG, and other external system integrations.
"""

from fastapi import APIRouter, Query, Path, Body, Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from backend.utils.db import db_query, db_query_one, get_setting, get_settings_by_prefix, count_rows
from backend.utils.http import NetBoxClient
from backend.openapi.integrations_impl import (
    list_integrations_paginated, get_integration_by_id, test_netbox_connection,
    test_prtg_connection, get_integration_status, sync_integration, test_integrations_endpoints
)

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/integrations/v1", tags=["integrations", "netbox", "prtg"])


@router.get("/", summary="List integrations")
async def list_integrations(
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """List configured integrations"""
    try:
        return await list_integrations_paginated(limit, cursor)
    except Exception as e:
        logger.error(f"List integrations error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "LIST_ERROR", "message": str(e)})


@router.get("/{integration_id}", summary="Get integration")
async def get_integration(
    integration_id: int = Path(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get integration details"""
    try:
        return await get_integration_by_id(integration_id)
    except Exception as e:
        logger.error(f"Get integration error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "GET_ERROR", "message": str(e)})


# NetBox integration
@router.get("/netbox/status", summary="Get NetBox status")
async def netbox_status(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get NetBox connection status"""
    try:
        settings = get_settings_by_prefix('netbox_')
        return {
            "connected": bool(settings.get('netbox_url') and settings.get('netbox_token')),
            "url": settings.get('netbox_url', ''),
            "token_configured": bool(settings.get('netbox_token'))
        }
    except Exception as e:
        logger.error(f"NetBox status error: {str(e)}")
        return {"connected": False, "error": str(e)}


@router.post("/netbox/test", summary="Test NetBox connection")
async def test_netbox(
    config: Dict[str, Any] = Body(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Test NetBox API connection"""
    try:
        return await test_netbox_connection(config)
    except Exception as e:
        logger.error(f"Test NetBox error: {str(e)}")
        return {"success": False, "error": str(e)}


@router.get("/netbox/devices", summary="Get NetBox devices")
async def netbox_devices(
    limit: int = Query(1000, ge=1, le=10000),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get devices from NetBox cache"""
    try:
        devices = db_query("""
            SELECT netbox_device_id as id, device_name as name, 
                   device_ip::text as primary_ip4, device_type, 
                   manufacturer as vendor, site_name as site,
                   role_name as role, cached_at
            FROM netbox_device_cache ORDER BY device_name LIMIT %s
        """, (limit,))
        total = count_rows('netbox_device_cache')
        return {"data": devices, "count": total}
    except Exception as e:
        logger.error(f"Get NetBox devices error: {str(e)}")
        return {"data": [], "count": 0}


@router.get("/netbox/settings", summary="Get NetBox settings")
async def netbox_settings(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get NetBox integration settings"""
    try:
        url = get_setting('netbox_url') or ''
        token = get_setting('netbox_api_token') or ''
        return {
            "success": True,
            "data": {
                "url": url,
                "token": token,
                "verify_ssl": True,
                "enabled": bool(url)
            }
        }
    except Exception as e:
        logger.error(f"Get NetBox settings error: {str(e)}")
        return {"success": False, "error": str(e)}


@router.get("/netbox/prefixes", summary="Get NetBox prefixes")
async def netbox_prefixes(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get IP prefixes from NetBox API"""
    try:
        client = NetBoxClient()
        if not client.is_configured:
            return []
        prefixes = client.get_prefixes()
        return [{'id': p['id'], 'prefix': p['prefix'], 'description': p.get('description', ''),
                'site': p.get('site', {}).get('name') if p.get('site') else None} 
               for p in prefixes]
    except Exception as e:
        logger.error(f"Get NetBox prefixes error: {str(e)}")
        return []


@router.get("/netbox/ip-ranges", summary="Get NetBox IP ranges")
async def netbox_ip_ranges(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get IP ranges from NetBox API"""
    try:
        client = NetBoxClient()
        if not client.is_configured:
            return []
        ranges = client.get_ip_ranges()
        return [{'id': r['id'], 'start_address': r['start_address'].split('/')[0],
                'end_address': r['end_address'].split('/')[0], 
                'description': r.get('description', ''), 'size': r.get('size', 0)} 
               for r in ranges]
    except Exception as e:
        logger.error(f"Get NetBox IP ranges error: {str(e)}")
        return []


@router.get("/netbox/tags", summary="Get NetBox tags")
async def netbox_tags(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get tags from NetBox"""
    return {"tags": []}


# PRTG integration
@router.get("/prtg/settings", summary="Get PRTG settings")
async def prtg_settings(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get PRTG integration settings"""
    try:
        url = get_setting('prtg_url') or ''
        token = get_setting('prtg_api_token') or ''
        return {
            "success": True,
            "data": {
                "url": url,
                "token": token,
                "enabled": bool(url)
            }
        }
    except Exception as e:
        logger.error(f"Get PRTG settings error: {str(e)}")
        return {"success": False, "error": str(e)}


@router.get("/prtg/status", summary="Get PRTG status")
async def prtg_status(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get PRTG connection status"""
    try:
        url = get_setting('prtg_url')
        if not url:
            return {"success": True, "data": {"connected": False}}
        
        # Try to test PRTG connection
        result = await test_prtg_connection({
            'url': url,
            'username': get_setting('prtg_username'),
            'passhash': get_setting('prtg_passhash') or get_setting('prtg_api_token'),
            'verify_ssl': False
        })
        
        return {
            "success": True,
            "data": {
                "connected": result.get('success', False),
                "version": result.get('prtg_version'),
                "sensors": result.get('sensors_count'),
                "devices": result.get('devices_count')
            }
        }
    except Exception as e:
        logger.error(f"PRTG status error: {str(e)}")
        return {"success": True, "data": {"connected": False, "error": str(e)}}


@router.post("/prtg/test", summary="Test PRTG connection")
async def test_prtg(
    config: Dict[str, Any] = Body(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Test PRTG connection"""
    try:
        return await test_prtg_connection(config)
    except Exception as e:
        return {"success": False, "error": str(e)}

# MCP integration
@router.post("/mcp/test", summary="Test MCP connection")
async def test_mcp(
    config: Dict[str, Any] = Body(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Test MCP connection"""
    try:
        # Use provided URL or fall back to settings
        url = config.get('url') or get_setting('mcp_url') or ''
        if not url:
            return {"success": True, "data": {"success": False, "message": "MCP URL not configured"}}
        
        # Try to connect to MCP endpoint
        import httpx
        async with httpx.AsyncClient(timeout=10.0, verify=False, follow_redirects=True) as client:
            # Try common health check endpoints
            for endpoint in ['/api/health', '/health', '/api/v1/health', '/']:
                try:
                    response = await client.get(f"{url.rstrip('/')}{endpoint}")
                    if response.status_code in [200, 301, 302]:
                        return {"success": True, "data": {"success": True, "message": "Connected successfully"}}
                except:
                    continue
            return {"success": True, "data": {"success": False, "message": "No health endpoint responded"}}
    except Exception as e:
        return {"success": True, "data": {"success": False, "message": str(e)}}


@router.get("/mcp/settings", summary="Get MCP settings")
async def mcp_settings(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get MCP integration settings"""
    try:
        url = get_setting('mcp_url') or ''
        token = get_setting('mcp_api_token') or ''
        return {
            "success": True,
            "data": {
                "url": url,
                "token": token,
                "enabled": bool(url)
            }
        }
    except Exception as e:
        logger.error(f"Get MCP settings error: {str(e)}")
        return {"success": False, "error": str(e)}


@router.get("/test", include_in_schema=False)
async def test_api():
    """Test Integrations API"""
    try:
        results = await test_integrations_endpoints()
        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "error": str(e)}
