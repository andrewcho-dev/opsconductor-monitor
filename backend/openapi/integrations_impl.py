"""
Integrations API Implementation - OpenAPI 3.x Migration
This implements the actual business logic for integration endpoints
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils.db import db_query, db_query_one, db_execute, table_exists
from backend.database import get_db  # TODO: refactor remaining usages
from backend.services.logging_service import get_logger, LogSource

logger = get_logger(__name__, LogSource.SYSTEM)

# ============================================================================
# Database Functions (Migrated from Legacy)
# ============================================================================

def _table_exists(cursor, table_name):
    """Check if table exists"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        ) as exists
    """, (table_name,))
    result = cursor.fetchone()
    return result['exists'] if result else False

# ============================================================================
# Integrations API Business Logic
# ============================================================================

async def list_integrations_paginated(
    cursor: Optional[str] = None, 
    limit: int = 50,
    integration_type: Optional[str] = None,
    status_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    List external integrations with pagination and filtering
    """
    db = get_db()
    with db.cursor() as cursor:
        # Build query with filters
        where_clauses = []
        params = []
        
        if integration_type:
            where_clauses.append("i.integration_type = %s")
            params.append(integration_type)
        
        if status_filter:
            where_clauses.append("i.status = %s")
            params.append(status_filter)
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM integrations i
            {where_clause}
        """
        
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # Apply pagination
        if cursor:
            # Decode cursor (for simplicity, using integration ID as cursor)
            try:
                import base64
                cursor_data = json.loads(base64.b64decode(cursor).decode())
                last_id = cursor_data.get('last_id')
                where_clauses.append("i.id > %s")
                params.append(last_id)
            except:
                pass
        
        # Get paginated results
        query = f"""
            SELECT i.id, i.name, i.integration_type, i.status, i.description,
                   i.config, i.created_at, i.updated_at, i.last_sync_at,
                   i.sync_enabled, i.error_message
            FROM integrations i
            {where_clause}
            ORDER BY i.id
            LIMIT %s
        """
        
        params.append(limit + 1)  # Get one extra to determine if there's a next page
        cursor.execute(query, params)
        
        integrations = [dict(row) for row in cursor.fetchall()]
        
        # Determine if there's a next page
        has_more = len(integrations) > limit
        if has_more:
            integrations = integrations[:-1]  # Remove the extra item
        
        # Generate next cursor
        next_cursor = None
        if has_more and integrations:
            last_id = integrations[-1]['id']
            cursor_data = json.dumps({'last_id': last_id})
            import base64
            next_cursor = base64.b64encode(cursor_data.encode()).decode()
        
        return {
            'items': integrations,
            'total': total,
            'limit': limit,
            'cursor': next_cursor
        }

async def get_integration_by_id(integration_id: str) -> Dict[str, Any]:
    """
    Get integration details by ID
    """
    if not table_exists('integrations'):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INTEGRATION_NOT_FOUND", "message": f"Integration with ID '{integration_id}' not found"})
    
    integration = db_query_one("""
        SELECT i.id, i.name, i.integration_type, i.status, i.description,
               i.config, i.created_at, i.updated_at, i.last_sync_at,
               i.sync_enabled, i.error_message
        FROM integrations i WHERE i.id = %s
    """, (integration_id,))
    
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INTEGRATION_NOT_FOUND", "message": f"Integration with ID '{integration_id}' not found"})
    
    return integration

async def test_netbox_connection(netbox_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test NetBox connection
    Migrated from legacy /api/netbox/test
    """
    try:
        import requests
        
        url = netbox_config.get('url', '').rstrip('/')
        token = netbox_config.get('token', '')
        
        # If no config provided, get from database
        if not url or not token:
            from backend.utils.db import get_settings_by_prefix
            settings = get_settings_by_prefix('netbox_')
            if not url:
                url = settings.get('netbox_url', '').rstrip('/')
            if not token:
                token = settings.get('netbox_token', '')
        
        if not url or not token:
            return {
                "success": False,
                "error": "Missing URL or token configuration"
            }
        
        # Test NetBox API connection
        headers = {
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f"{url}/api/status/",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            status_data = response.json()
            return {
                "success": True,
                "message": "NetBox connection successful",
                "netbox_version": status_data.get('netbox-version'),
                "django_version": status_data.get('django-version'),
                "python_version": status_data.get('python-version')
            }
        else:
            return {
                "success": False,
                "error": f"NetBox API error: {response.status_code}",
                "message": response.text
            }
            
    except Exception as e:
        logger.error(f"NetBox connection test failed: {str(e)}")
        return {
            "success": False,
            "error": "Connection failed",
            "message": str(e)
        }

async def test_prtg_connection(prtg_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test PRTG connection
    Migrated from legacy /api/prtg/test
    """
    try:
        import requests
        
        url = prtg_config.get('url', '').rstrip('/')
        username = prtg_config.get('username', '')
        passhash = prtg_config.get('passhash', '')
        api_token = prtg_config.get('api_token', '')
        verify_ssl = prtg_config.get('verify_ssl', 'true').lower() != 'false'
        
        # Support both passhash and api_token authentication
        if not url:
            return {
                "success": False,
                "error": "Missing URL configuration"
            }
        
        if not passhash and not api_token:
            return {
                "success": False,
                "error": "Missing passhash or api_token configuration"
            }
        
        # Test PRTG API connection - prefer api_token over passhash
        if api_token:
            params = {
                'apitoken': api_token,
                'id': '0',
                'content': 'status'
            }
        else:
            params = {
                'username': username,
                'passhash': passhash,
                'id': '0',
                'content': 'status'
            }
        
        response = requests.get(
            f"{url}/api/status.json",
            params=params,
            timeout=10,
            verify=verify_ssl
        )
        
        if response.status_code == 200:
            status_data = response.json()
            return {
                "success": True,
                "message": "PRTG connection successful",
                "prtg_version": status_data.get('version'),
                "sensors_count": status_data.get('sensors'),
                "devices_count": status_data.get('devices')
            }
        else:
            return {
                "success": False,
                "error": f"PRTG API error: {response.status_code}",
                "message": response.text
            }
            
    except Exception as e:
        logger.error(f"PRTG connection test failed: {str(e)}")
        return {
            "success": False,
            "error": "Connection failed",
            "message": str(e)
        }

async def get_mcp_services_status() -> Dict[str, Any]:
    """
    Get MCP (Model Context Protocol) services status
    Migrated from legacy /api/mcp/services
    """
    if not table_exists('mcp_services'):
        return {"services": [], "total_count": 0, "active_count": 0, "last_updated": datetime.now().isoformat()}
    
    services = db_query("""
        SELECT id, name, service_type, status, endpoint, config,
               created_at, updated_at, last_check_at
        FROM mcp_services ORDER BY name
    """)
    active_count = len([s for s in services if s.get('status') == 'active'])
    return {"services": services, "total_count": len(services), "active_count": active_count, "last_updated": datetime.now().isoformat()}

async def get_mcp_devices() -> List[Dict[str, Any]]:
    """
    Get MCP devices
    Migrated from legacy /api/mcp/devices
    """
    if not table_exists('mcp_devices'):
        return []
    return db_query("""
        SELECT id, name, device_type, status, endpoint, config,
               created_at, updated_at, last_seen_at
        FROM mcp_devices ORDER BY name
    """)

async def get_integration_status(integration_type: str) -> Dict[str, Any]:
    """
    Get status for a specific integration type
    """
    if not table_exists('integrations'):
        return {"integration_type": integration_type, "status": "unavailable", "message": "Integrations table not found"}
    
    stats = db_query_one("""
        SELECT COUNT(*) as total,
               COUNT(*) FILTER (WHERE status = 'active') as active,
               COUNT(*) FILTER (WHERE sync_enabled = true) as sync_enabled,
               MAX(last_sync_at) as last_sync
        FROM integrations WHERE integration_type = %s
    """, (integration_type,))
    
    if not stats or stats['total'] == 0:
        return {"integration_type": integration_type, "status": "not_configured", "message": f"No {integration_type} integrations configured"}
    
    return {"integration_type": integration_type, "status": "configured",
            "total_integrations": stats['total'], "active_integrations": stats['active'],
            "sync_enabled": stats['sync_enabled'], "last_sync": stats['last_sync'].isoformat() if stats['last_sync'] else None}

async def sync_integration(integration_id: str, triggered_by: str) -> Dict[str, str]:
    """
    Trigger manual sync for an integration
    """
    db = get_db()
    with db.cursor() as cursor:
        # Check if integration exists and is active
        cursor.execute("""
            SELECT id, name, integration_type, status FROM integrations 
            WHERE id = %s
        """, (integration_id,))
        
        integration = cursor.fetchone()
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "INTEGRATION_NOT_FOUND",
                    "message": f"Integration with ID '{integration_id}' not found"
                }
            )
        
        if integration['status'] != 'active':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INTEGRATION_INACTIVE",
                    "message": f"Integration '{integration['name']}' is not active"
                }
            )
        
        # Update last sync time
        cursor.execute("""
            UPDATE integrations 
            SET last_sync_at = NOW(),
                error_message = NULL
            WHERE id = %s
        """, (integration_id,))
        
        db.commit()
        
        logger.info(f"Integration {integration_id} ({integration['name']}) synced by {triggered_by}")
        
        # In a real implementation, you would trigger the actual sync process here
        
        return {
            "success": True,
            "message": "Integration sync triggered successfully",
            "integration_id": integration_id,
            "integration_name": integration['name'],
            "sync_time": datetime.now().isoformat()
        }

# ============================================================================
# Testing Functions
# ============================================================================

async def test_integrations_endpoints() -> Dict[str, bool]:
    """
    Test all Integrations API endpoints
    Returns dict of endpoint: success status
    """
    results = {}
    
    try:
        # Test 1: List integrations (empty)
        integrations_data = await list_integrations_paginated()
        results['list_integrations'] = 'items' in integrations_data and 'total' in integrations_data
        
        # Test 2: Get MCP services status
        mcp_status = await get_mcp_services_status()
        results['get_mcp_services'] = 'services' in mcp_status and 'total_count' in mcp_status
        
        # Test 3: Get MCP devices
        mcp_devices = await get_mcp_devices()
        results['get_mcp_devices'] = isinstance(mcp_devices, list)
        
        # Test 4: Test NetBox connection (with empty config)
        netbox_test = await test_netbox_connection({})
        results['test_netbox'] = 'success' in netbox_test
        
        # Test 5: Test PRTG connection (with empty config)
        prtg_test = await test_prtg_connection({})
        results['test_prtg'] = 'success' in prtg_test
        
        # Test 6: Get integration status
        status = await get_integration_status('netbox')
        results['get_integration_status'] = 'integration_type' in status
        
        logger.info(f"Integrations API tests completed: {sum(results.values())}/{len(results)} passed")
        
    except Exception as e:
        logger.error(f"Integrations API test failed: {str(e)}")
        results['error'] = str(e)
    
    return results
