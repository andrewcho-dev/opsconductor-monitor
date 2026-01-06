"""
Inventory API Implementation - OpenAPI 3.x Migration
This implements the actual business logic for inventory endpoints
"""

import os
import sys
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils.db import db_query, db_query_one, db_execute, table_exists, db_paginate
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
# Inventory API Business Logic
# ============================================================================

async def list_devices_paginated(
    cursor_str: Optional[str] = None,
    limit: int = 50,
    site_id: Optional[str] = None,
    device_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    List devices with pagination and filtering.
    Uses EXACT same query as legacy /api/devices endpoint.
    """
    where_clauses = ["1=1"]
    params = []
    
    if site_id:
        where_clauses.append("site_name = %s")
        params.append(site_id)
    
    if device_type:
        where_clauses.append("device_type = %s")
        params.append(device_type)
    
    if search:
        where_clauses.append("(device_name ILIKE %s OR device_ip::text ILIKE %s)")
        search_param = f"%{search}%"
        params.extend([search_param, search_param])
    
    where_clause = "WHERE " + " AND ".join(where_clauses)
    
    return db_paginate(
        f"""SELECT netbox_device_id::text as id, device_name as name, 
               COALESCE(device_ip::text, '') as ip_address, COALESCE(device_type, '') as device_type, 
               COALESCE(manufacturer, '') as vendor, COALESCE(site_name, '') as site_name, 
               COALESCE(role_name, '') as role, COALESCE(site_id::text, '') as site_id, 
               cached_at as created_at, cached_at as updated_at, cached_at as last_seen
            FROM netbox_device_cache {where_clause} ORDER BY device_name""",
        f"SELECT COUNT(*) as total FROM netbox_device_cache {where_clause}",
        params, limit
    )

async def get_device_by_id(device_id: str) -> Dict[str, Any]:
    """
    Get device details by ID
    Uses netbox_device_cache table (same as legacy)
    """
    device = db_query_one("""
        SELECT netbox_device_id as id, device_name as name, device_ip::text as ip_address,
               device_type, manufacturer as vendor, site_name, role_name as role,
               site_id, cached_at as created_at, cached_at as updated_at, cached_at as last_seen
        FROM netbox_device_cache WHERE netbox_device_id = %s OR device_ip::text = %s
    """, (device_id, device_id))
    
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DEVICE_NOT_FOUND", "message": f"Device with ID '{device_id}' not found"})
    
    return device

async def list_device_interfaces(device_id: str) -> List[Dict[str, Any]]:
    """
    List interfaces for a specific device
    Returns empty list - interfaces not stored in current schema
    """
    # Current schema doesn't have interfaces table - return empty
    return []

async def get_network_topology() -> Dict[str, Any]:
    """
    Get network topology graph
    Uses netbox_device_cache table (same as legacy)
    """
    devices = db_query("""
        SELECT netbox_device_id as id, device_name as name, device_ip::text as ip_address,
               device_type, manufacturer as vendor, site_name
        FROM netbox_device_cache ORDER BY device_name
    """)
    
    nodes = [{"id": str(d['id']), "name": d['name'], "ip": d['ip_address'],
              "type": d['device_type'], "vendor": d['vendor'], "site": d['site_name'], "status": "active"}
             for d in devices]
    
    links = []
    if table_exists('links'):
        link_rows = db_query("SELECT source_device_id, target_device_id, link_type, bandwidth, status FROM links WHERE status = 'active'")
        links = [{"source": str(l['source_device_id']), "target": str(l['target_device_id']),
                  "type": l['link_type'], "bandwidth": l['bandwidth'], "status": l['status']} for l in link_rows]
    
    return {"nodes": nodes, "links": links, "metadata": {"total_devices": len(nodes), "total_links": len(links), "last_updated": datetime.now().isoformat()}}

async def list_sites() -> List[Dict[str, Any]]:
    """
    List all sites
    Migrated from legacy /api/inventory/sites
    """
    if not table_exists('sites'):
        return []
    return db_query("""
        SELECT s.id, s.name, s.description, s.address, s.city,
               s.state, s.country, s.latitude, s.longitude,
               s.created_at, s.updated_at,
               (SELECT COUNT(*) FROM netbox_device_cache d WHERE d.site_id = s.id) as device_count
        FROM sites s ORDER BY s.name
    """)

async def list_modules(device_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List device modules
    Migrated from legacy /api/inventory/modules
    """
    if not table_exists('modules'):
        return []
    
    if device_id:
        return db_query("""
            SELECT m.id, m.device_id, m.name, m.description, m.type,
                   m.part_number, m.serial_number, m.status, m.created_at, m.updated_at,
                   d.name as device_name
            FROM modules m LEFT JOIN devices d ON m.device_id = d.id
            WHERE m.device_id = %s ORDER BY m.device_id, m.name
        """, (device_id,))
    return db_query("""
        SELECT m.id, m.device_id, m.name, m.description, m.type,
               m.part_number, m.serial_number, m.status, m.created_at, m.updated_at,
               d.name as device_name
        FROM modules m LEFT JOIN devices d ON m.device_id = d.id ORDER BY m.device_id, m.name
    """)

async def list_racks(site_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List racks
    Migrated from legacy /api/inventory/racks
    """
    if not table_exists('racks'):
        return []
    
    if site_id:
        return db_query("""
            SELECT r.id, r.site_id, r.name, r.description, r.height,
                   r.position, r.status, r.created_at, r.updated_at, s.name as site_name
            FROM racks r LEFT JOIN sites s ON r.site_id = s.id
            WHERE r.site_id = %s ORDER BY r.site_id, r.name
        """, (site_id,))
    return db_query("""
        SELECT r.id, r.site_id, r.name, r.description, r.height,
               r.position, r.status, r.created_at, r.updated_at, s.name as site_name
        FROM racks r LEFT JOIN sites s ON r.site_id = s.id ORDER BY r.site_id, r.name
    """)

# ============================================================================
# Testing Functions
# ============================================================================

async def test_inventory_endpoints() -> Dict[str, bool]:
    """
    Test all Inventory API endpoints
    Returns dict of endpoint: success status
    """
    results = {}
    
    try:
        # Test 1: List devices (empty)
        devices_data = await list_devices_paginated()
        results['list_devices'] = 'items' in devices_data and 'total' in devices_data
        
        # Test 2: List sites
        sites = await list_sites()
        results['list_sites'] = isinstance(sites, list)
        
        # Test 3: Get topology
        topology = await get_network_topology()
        results['get_topology'] = 'nodes' in topology and 'links' in topology
        
        # Test 4: List modules
        modules = await list_modules()
        results['list_modules'] = isinstance(modules, list)
        
        # Test 5: List racks
        racks = await list_racks()
        results['list_racks'] = isinstance(racks, list)
        
        logger.info(f"Inventory API tests completed: {sum(results.values())}/{len(results)} passed")
        
    except Exception as e:
        logger.error(f"Inventory API test failed: {str(e)}")
        results['error'] = str(e)
    
    return results
