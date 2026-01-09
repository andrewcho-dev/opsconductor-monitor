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
    limit: int = Query(10000, ge=1, le=100000),
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


@router.get("/netbox/devices/{device_id}/interfaces", summary="Get device interfaces")
async def netbox_device_interfaces(
    device_id: int = Path(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get interfaces for a NetBox device"""
    try:
        # Try to get interfaces from cache or return empty list
        interfaces = db_query("""
            SELECT interface_name as name, interface_type as type, enabled, 
                   mac_address, mtu, description
            FROM netbox_interface_cache 
            WHERE device_id = %s ORDER BY interface_name
        """, (device_id,))
        if interfaces:
            return {"interfaces": interfaces, "count": len(interfaces)}
        # Return empty list if no cached interfaces
        return {"interfaces": [], "count": 0}
    except Exception as e:
        logger.error(f"Get device interfaces error: {str(e)}")
        return {"interfaces": [], "count": 0}


@router.get("/netbox/settings", summary="Get NetBox settings")
async def netbox_settings(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get NetBox integration settings"""
    try:
        url = get_setting('netbox_url') or ''
        token = get_setting('netbox_token') or get_setting('netbox_api_token') or ''
        return {
            "success": True,
            "data": {
                "url": url,
                "token_configured": bool(token),
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
            'passhash': get_setting('prtg_passhash'),
            'api_token': get_setting('prtg_api_token'),
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
                        # Count Ciena devices from inventory
                        device_count = 0
                        try:
                            result = db_query_one("SELECT COUNT(*) as cnt FROM netbox_device_cache WHERE manufacturer ILIKE '%ciena%'")
                            device_count = result['cnt'] if result else 0
                        except:
                            pass
                        return {"success": True, "data": {"success": True, "message": "Connected successfully", "summary": {"devices": device_count}}}
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


# Ubiquiti UISP integration
@router.get("/ubiquiti/settings", summary="Get Ubiquiti UISP settings")
async def ubiquiti_settings(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get Ubiquiti UISP integration settings"""
    try:
        url = get_setting('ubiquiti_url') or ''
        token = get_setting('ubiquiti_api_token') or ''
        poll_interval = int(get_setting('ubiquiti_poll_interval') or '60')
        enabled = get_setting('ubiquiti_enabled') == 'true'
        cpu_warning = int(get_setting('ubiquiti_cpu_warning') or '80')
        memory_warning = int(get_setting('ubiquiti_memory_warning') or '80')
        return {
            "success": True,
            "data": {
                "url": url,
                "api_token": token,
                "enabled": enabled,
                "poll_interval": poll_interval,
                "thresholds": {
                    "cpu_warning": cpu_warning,
                    "memory_warning": memory_warning
                }
            }
        }
    except Exception as e:
        logger.error(f"Get Ubiquiti settings error: {str(e)}")
        return {"success": False, "error": str(e)}


@router.put("/ubiquiti/settings", summary="Update Ubiquiti UISP settings")
async def update_ubiquiti_settings(
    config: Dict[str, Any] = Body(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Update Ubiquiti UISP integration settings"""
    from backend.utils.db import set_setting
    try:
        if 'url' in config:
            set_setting('ubiquiti_url', config['url'])
        if 'api_token' in config:
            set_setting('ubiquiti_api_token', config['api_token'])
        if 'enabled' in config:
            set_setting('ubiquiti_enabled', 'true' if config['enabled'] else 'false')
        if 'poll_interval' in config:
            set_setting('ubiquiti_poll_interval', str(config['poll_interval']))
        if 'thresholds' in config:
            thresholds = config['thresholds']
            if 'cpu_warning' in thresholds:
                set_setting('ubiquiti_cpu_warning', str(thresholds['cpu_warning']))
            if 'memory_warning' in thresholds:
                set_setting('ubiquiti_memory_warning', str(thresholds['memory_warning']))
        return {"success": True, "message": "Settings saved"}
    except Exception as e:
        logger.error(f"Update Ubiquiti settings error: {str(e)}")
        return {"success": False, "error": str(e)}


@router.get("/ubiquiti/status", summary="Get Ubiquiti UISP status")
async def ubiquiti_status(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get Ubiquiti UISP connection status"""
    try:
        url = get_setting('ubiquiti_url')
        if not url:
            return {"success": True, "data": {"connected": False}}
        
        # Check connector status from database
        connector = db_query_one("""
            SELECT status, last_poll_at, error_message 
            FROM connectors WHERE connector_type = 'ubiquiti' LIMIT 1
        """)
        
        if connector:
            return {
                "success": True,
                "data": {
                    "connected": connector['status'] == 'connected',
                    "last_poll": connector['last_poll_at'].isoformat() if connector['last_poll_at'] else None,
                    "error": connector['error_message']
                }
            }
        return {"success": True, "data": {"connected": False}}
    except Exception as e:
        logger.error(f"Ubiquiti status error: {str(e)}")
        return {"success": True, "data": {"connected": False, "error": str(e)}}


@router.post("/ubiquiti/test", summary="Test Ubiquiti UISP connection")
async def test_ubiquiti(
    config: Dict[str, Any] = Body(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Test Ubiquiti UISP connection"""
    try:
        url = config.get('url') or get_setting('ubiquiti_url') or ''
        api_token = config.get('api_token') or get_setting('ubiquiti_api_token') or ''
        
        if not url:
            return {"success": True, "data": {"success": False, "message": "UISP URL not configured"}}
        if not api_token:
            return {"success": True, "data": {"success": False, "message": "API token not configured"}}
        
        import httpx
        async with httpx.AsyncClient(timeout=15.0, verify=True) as client:
            response = await client.get(
                f"{url.rstrip('/')}/nms/api/v2.1/devices?count=1",
                headers={"x-auth-token": api_token}
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "data": {
                        "success": True,
                        "message": "Connected to UISP",
                        "details": {"device_count": len(data) if isinstance(data, list) else 0}
                    }
                }
            elif response.status_code == 401:
                return {"success": True, "data": {"success": False, "message": "Invalid API token"}}
            else:
                return {"success": True, "data": {"success": False, "message": f"HTTP {response.status_code}"}}
    except Exception as e:
        return {"success": True, "data": {"success": False, "message": str(e)}}


@router.get("/test", include_in_schema=False)
async def test_api():
    """Test Integrations API"""
    try:
        results = await test_integrations_endpoints()
        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "error": str(e)}
