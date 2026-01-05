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

from backend.database import get_db
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
        )
    """, (table_name,))
    return cursor.fetchone()[0]

# ============================================================================
# Inventory API Business Logic
# ============================================================================

async def list_devices_paginated(
    cursor: Optional[str] = None, 
    limit: int = 50,
    site_id: Optional[str] = None,
    device_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    List devices with pagination and filtering
    Migrated from legacy /api/devices and /api/inventory/devices
    """
    db = get_db()
    with db.cursor() as cursor:
        # Build query with filters
        where_clauses = []
        params = []
        
        if search:
            where_clauses.append("(d.name ILIKE %s OR d.ip_address ILIKE %s OR d.hostname ILIKE %s)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
        
        if site_id:
            where_clauses.append("d.site_id = %s")
            params.append(site_id)
        
        if device_type:
            where_clauses.append("d.device_type = %s")
            params.append(device_type)
        
        if status_filter:
            where_clauses.append("d.status = %s")
            params.append(status_filter)
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM devices d
            {where_clause}
        """
        
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # Apply pagination
        if cursor:
            # Decode cursor (for simplicity, using device ID as cursor)
            try:
                import base64
                cursor_data = json.loads(base64.b64decode(cursor).decode())
                last_id = cursor_data.get('last_id')
                where_clauses.append("d.id > %s")
                params.append(last_id)
            except:
                pass
        
        # Get paginated results
        query = f"""
            SELECT d.id, d.name, d.ip_address, d.hostname, d.device_type,
                   d.vendor, d.model, d.os_version, d.site_id, d.status,
                   d.created_at, d.updated_at, d.last_seen,
                   s.name as site_name
            FROM devices d
            LEFT JOIN sites s ON d.site_id = s.id
            {where_clause}
            ORDER BY d.id
            LIMIT %s
        """
        
        params.append(limit + 1)  # Get one extra to determine if there's a next page
        cursor.execute(query, params)
        
        devices = [dict(row) for row in cursor.fetchall()]
        
        # Determine if there's a next page
        has_more = len(devices) > limit
        if has_more:
            devices = devices[:-1]  # Remove the extra item
        
        # Generate next cursor
        next_cursor = None
        if has_more and devices:
            last_id = devices[-1]['id']
            cursor_data = json.dumps({'last_id': last_id})
            import base64
            next_cursor = base64.b64encode(cursor_data.encode()).decode()
        
        return {
            'items': devices,
            'total': total,
            'limit': limit,
            'cursor': next_cursor
        }

async def get_device_by_id(device_id: str) -> Dict[str, Any]:
    """
    Get device details by ID
    Migrated from legacy device endpoints
    """
    db = get_db()
    with db.cursor() as cursor:
        if not _table_exists(cursor, 'devices'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "DEVICE_NOT_FOUND",
                    "message": f"Device with ID '{device_id}' not found"
                }
            )
        
        cursor.execute("""
            SELECT d.id, d.name, d.ip_address, d.hostname, d.device_type,
                   d.vendor, d.model, d.os_version, d.site_id, d.status,
                   d.created_at, d.updated_at, d.last_seen,
                   s.name as site_name, s.description as site_description
            FROM devices d
            LEFT JOIN sites s ON d.site_id = s.id
            WHERE d.id = %s
        """, (device_id,))
        
        device = cursor.fetchone()
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "DEVICE_NOT_FOUND",
                    "message": f"Device with ID '{device_id}' not found"
                }
            )
        
        return dict(device)

async def list_device_interfaces(device_id: str) -> List[Dict[str, Any]]:
    """
    List interfaces for a specific device
    Migrated from legacy /api/inventory/interfaces
    """
    db = get_db()
    with db.cursor() as cursor:
        # First verify device exists
        cursor.execute("SELECT id FROM devices WHERE id = %s", (device_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "DEVICE_NOT_FOUND",
                    "message": f"Device with ID '{device_id}' not found"
                }
            )
        
        if not _table_exists(cursor, 'interfaces'):
            return []
        
        cursor.execute("""
            SELECT i.id, i.name, i.description, i.if_index, i.if_type,
                   i.admin_status, i.oper_status, i.speed, i.mtu,
                   i.mac_address, i.created_at, i.updated_at
            FROM interfaces i
            WHERE i.device_id = %s
            ORDER BY i.if_index, i.name
        """, (device_id,))
        
        interfaces = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        
        return interfaces

async def get_network_topology() -> Dict[str, Any]:
    """
    Get network topology graph
    Migrated from legacy /api/topology
    """
    db = get_db()
    with db.cursor() as cursor:
        if not _table_exists(cursor, 'devices'):
            return {
                "nodes": [],
                "links": [],
                "metadata": {
                    "total_devices": 0,
                    "total_links": 0,
                    "last_updated": datetime.now().isoformat()
                }
            }
        
        # Get devices as nodes
        cursor.execute("""
            SELECT d.id, d.name, d.ip_address, d.device_type, d.vendor,
                   d.status, d.site_id, s.name as site_name
            FROM devices d
            LEFT JOIN sites s ON d.site_id = s.id
            WHERE d.status = 'active'
            ORDER BY d.name
        """)
        
        devices = cursor.fetchall()
        nodes = []
        for device in devices:
            nodes.append({
                "id": str(device['id']),
                "name": device['name'],
                "ip": device['ip_address'],
                "type": device['device_type'],
                "vendor": device['vendor'],
                "site": device['site_name'],
                "status": device['status']
            })
        
        # Get links (if links table exists)
        links = []
        if _table_exists(cursor, 'links'):
            cursor.execute("""
                SELECT l.source_device_id, l.target_device_id, l.link_type,
                       l.bandwidth, l.status
                FROM links l
                WHERE l.status = 'active'
            """)
            
            for link in cursor.fetchall():
                links.append({
                    "source": str(link['source_device_id']),
                    "target": str(link['target_device_id']),
                    "type": link['link_type'],
                    "bandwidth": link['bandwidth'],
                    "status": link['status']
                })
        
        return {
            "nodes": nodes,
            "links": links,
            "metadata": {
                "total_devices": len(nodes),
                "total_links": len(links),
                "last_updated": datetime.now().isoformat()
            }
        }

async def list_sites() -> List[Dict[str, Any]]:
    """
    List all sites
    Migrated from legacy /api/inventory/sites
    """
    db = get_db()
    with db.cursor() as cursor:
        if not _table_exists(cursor, 'sites'):
            return []
        
        cursor.execute("""
            SELECT s.id, s.name, s.description, s.address, s.city,
                   s.state, s.country, s.latitude, s.longitude,
                   s.created_at, s.updated_at,
                   (SELECT COUNT(*) FROM devices d WHERE d.site_id = s.id) as device_count
            FROM sites s
            ORDER BY s.name
        """)
        
        sites = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        
        return sites

async def list_modules(device_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List device modules
    Migrated from legacy /api/inventory/modules
    """
    db = get_db()
    with db.cursor() as cursor:
        if not _table_exists(cursor, 'modules'):
            return []
        
        where_clause = ""
        params = []
        
        if device_id:
            where_clause = "WHERE m.device_id = %s"
            params.append(device_id)
        
        cursor.execute(f"""
            SELECT m.id, m.device_id, m.name, m.description, m.type,
                   m.part_number, m.serial_number, m.status,
                   m.created_at, m.updated_at,
                   d.name as device_name
            FROM modules m
            LEFT JOIN devices d ON m.device_id = d.id
            {where_clause}
            ORDER BY m.device_id, m.name
        """, params)
        
        modules = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        
        return modules

async def list_racks(site_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List racks
    Migrated from legacy /api/inventory/racks
    """
    db = get_db()
    with db.cursor() as cursor:
        if not _table_exists(cursor, 'racks'):
            return []
        
        where_clause = ""
        params = []
        
        if site_id:
            where_clause = "WHERE r.site_id = %s"
            params.append(site_id)
        
        cursor.execute(f"""
            SELECT r.id, r.site_id, r.name, r.description, r.height,
                   r.position, r.status, r.created_at, r.updated_at,
                   s.name as site_name
            FROM racks r
            LEFT JOIN sites s ON r.site_id = s.id
            {where_clause}
            ORDER BY r.site_id, r.name
        """, params)
        
        racks = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        
        return racks

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
