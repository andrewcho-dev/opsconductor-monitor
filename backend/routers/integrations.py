"""
Integrations API Router (/integrations/v1)

Handles NetBox, PRTG, MCP, and other external system integrations.
"""

from fastapi import APIRouter, Query, Path, Body, Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import requests

from backend.database import get_db
from backend.openapi.integrations_impl import (
    list_integrations_paginated, get_integration_by_id, test_netbox_connection,
    test_prtg_connection, get_mcp_services_status, get_mcp_devices,
    get_integration_status, sync_integration, test_integrations_endpoints
)

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/integrations/v1", tags=["integrations", "netbox", "prtg", "mcp"])


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
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("SELECT key, value FROM system_settings WHERE key LIKE 'netbox_%'")
            settings = {row['key']: row['value'] for row in cursor.fetchall()}
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
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT netbox_device_id as id, device_name as name, 
                       device_ip::text as primary_ip4, device_type, 
                       manufacturer as vendor, site_name as site,
                       role_name as role, cached_at
                FROM netbox_device_cache ORDER BY device_name LIMIT %s
            """, (limit,))
            devices = [dict(row) for row in cursor.fetchall()]
            cursor.execute("SELECT COUNT(*) as total FROM netbox_device_cache")
            total = cursor.fetchone()['total']
        return {"data": devices, "count": total}
    except Exception as e:
        logger.error(f"Get NetBox devices error: {str(e)}")
        return {"data": [], "count": 0}


@router.get("/netbox/prefixes", summary="Get NetBox prefixes")
async def netbox_prefixes(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get IP prefixes from NetBox API"""
    try:
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("SELECT value FROM system_settings WHERE key = 'netbox_url'")
            row = cursor.fetchone()
            url = row['value'].rstrip('/') if row else ''
            cursor.execute("SELECT value FROM system_settings WHERE key = 'netbox_token'")
            row = cursor.fetchone()
            token = row['value'] if row else ''
        
        if not url or not token:
            return []
        
        headers = {'Authorization': f'Token {token}'}
        response = requests.get(f"{url}/api/ipam/prefixes/?limit=500", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return [{'id': p['id'], 'prefix': p['prefix'], 'description': p.get('description', ''),
                    'site': p.get('site', {}).get('name') if p.get('site') else None} 
                   for p in data.get('results', [])]
        return []
    except Exception as e:
        logger.error(f"Get NetBox prefixes error: {str(e)}")
        return []


@router.get("/netbox/ip-ranges", summary="Get NetBox IP ranges")
async def netbox_ip_ranges(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get IP ranges from NetBox API"""
    try:
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("SELECT value FROM system_settings WHERE key = 'netbox_url'")
            row = cursor.fetchone()
            url = row['value'].rstrip('/') if row else ''
            cursor.execute("SELECT value FROM system_settings WHERE key = 'netbox_token'")
            row = cursor.fetchone()
            token = row['value'] if row else ''
        
        if not url or not token:
            return []
        
        headers = {'Authorization': f'Token {token}'}
        response = requests.get(f"{url}/api/ipam/ip-ranges/?limit=500", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return [{'id': r['id'], 'start_address': r['start_address'].split('/')[0],
                    'end_address': r['end_address'].split('/')[0], 
                    'description': r.get('description', ''), 'size': r.get('size', 0)} 
                   for r in data.get('results', [])]
        return []
    except Exception as e:
        logger.error(f"Get NetBox IP ranges error: {str(e)}")
        return []


@router.get("/netbox/tags", summary="Get NetBox tags")
async def netbox_tags(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get tags from NetBox"""
    return {"tags": []}


# PRTG integration
@router.get("/prtg/status", summary="Get PRTG status")
async def prtg_status(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get PRTG connection status"""
    return {"connected": False}


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
@router.get("/mcp/settings", summary="Get MCP settings")
async def mcp_settings(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get MCP settings"""
    return {"url": "", "enabled": False}


@router.post("/mcp/test", summary="Test MCP connection")
async def test_mcp(
    config: Dict[str, Any] = Body(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Test MCP connection"""
    return {"success": False, "error": "Not configured"}


@router.get("/mcp/services", summary="Get MCP services")
async def mcp_services(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get MCP services"""
    try:
        data = await get_mcp_services_status()
        return data
    except Exception as e:
        logger.error(f"Get MCP services error: {str(e)}")
        return {"services": [], "total_count": 0, "active_count": 0}


@router.get("/mcp/services/summary", summary="Get MCP services summary")
async def mcp_summary(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get MCP services summary"""
    try:
        data = await get_mcp_services_status()
        return {
            "total_services": data.get('total_count', 0),
            "active_services": data.get('active_count', 0),
            "last_updated": data.get('last_updated', datetime.now().isoformat())
        }
    except Exception as e:
        return {"total_services": 0, "active_services": 0}


@router.get("/mcp/services/rings", summary="Get MCP rings")
async def mcp_rings(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get MCP service rings"""
    return {"rings": []}


@router.get("/mcp/devices", summary="Get MCP devices")
async def mcp_devices(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get MCP devices"""
    try:
        return await get_mcp_devices()
    except Exception as e:
        logger.error(f"Get MCP devices error: {str(e)}")
        return []


@router.get("/test", include_in_schema=False)
async def test_api():
    """Test Integrations API"""
    try:
        results = await test_integrations_endpoints()
        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "error": str(e)}
