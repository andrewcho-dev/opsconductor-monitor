"""Legacy routes router - FastAPI.

Maintains backward compatibility with existing frontend endpoints.
"""

import os
import json
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
import logging

from backend.database import get_db
from backend.utils.responses import success_response, error_response

logger = logging.getLogger(__name__)

router = APIRouter()


def get_netbox_settings():
    """Get NetBox settings from database."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT key, value FROM system_settings WHERE key LIKE 'netbox_%'")
        rows = cursor.fetchall()
        return {row['key'].replace('netbox_', ''): row['value'] for row in rows}


# ============================================================================
# Device Data Routes - NOW PROXIES TO NETBOX
# ============================================================================

@router.get("/data")
async def get_data():
    """Get all devices - main data endpoint."""
    try:
        from backend.services.netbox_service import NetBoxService
        from backend.api.routers.netbox import get_netbox_settings
        
        settings = get_netbox_settings()
        netbox = NetBoxService(
            url=settings.get('url', ''),
            token=settings.get('token', ''),
            verify_ssl=settings.get('verify_ssl', 'true').lower() == 'true'
        )
        
        if not netbox.is_configured:
            # Fall back to cache
            db = get_db()
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT netbox_device_id as id, netbox_device_id as netbox_id, 
                           device_name as hostname, device_ip as ip_address, 
                           device_type, manufacturer, site_name as site, role_name as role,
                           'online' as ping_status, 'YES' as snmp_status,
                           device_name as snmp_hostname, device_type as snmp_model,
                           '' as snmp_serial, manufacturer as snmp_vendor_name,
                           device_type as snmp_description, '' as network_range,
                           'netbox' as source, '' as netbox_url, cached_at as last_updated
                    FROM netbox_device_cache ORDER BY device_name
                """)
                return [dict(row) for row in cursor.fetchall()]
        
        result = netbox.get_devices(limit=10000)
        netbox_devices = result.get('results', [])
        
        devices = []
        for d in netbox_devices:
            primary_ip = d.get('primary_ip4') or d.get('primary_ip') or {}
            ip_address = primary_ip.get('address', '').split('/')[0] if primary_ip else None
            
            if not ip_address:
                continue
            
            devices.append({
                'ip_address': ip_address,
                'hostname': d.get('name', ''),
                'snmp_hostname': d.get('name', ''),
                'snmp_description': d.get('description', ''),
                'snmp_model': d.get('device_type', {}).get('model', '') if d.get('device_type') else '',
                'snmp_vendor_name': d.get('device_type', {}).get('manufacturer', {}).get('name', '') if d.get('device_type') else '',
                'snmp_serial': d.get('serial', ''),
                'ping_status': 'online' if d.get('status', {}).get('value') == 'active' else 'offline',
                'snmp_status': 'YES',
                'network_range': d.get('site', {}).get('name', '') if d.get('site') else '',
                'site': d.get('site', {}).get('name', '') if d.get('site') else '',
                'role': d.get('role', {}).get('name', '') if d.get('role') else '',
                'device_type': d.get('device_type', {}).get('model', '') if d.get('device_type') else '',
                'manufacturer': d.get('device_type', {}).get('manufacturer', {}).get('name', '') if d.get('device_type') else '',
                'status': d.get('status', {}).get('value', 'unknown'),
                'netbox_id': d.get('id'),
                'netbox_url': d.get('url'),
                'source': 'netbox',
            })
        
        return devices
        
    except Exception as e:
        logger.error(f"Error fetching devices from NetBox: {e}")
        return []


@router.post("/delete_selected")
async def delete_selected():
    """DEPRECATED: Devices are now managed in NetBox."""
    return {'error': 'Device deletion is now managed in NetBox.', 'deprecated': True}


@router.post("/delete_device")
async def delete_device():
    """DEPRECATED: Devices are now managed in NetBox."""
    return {'error': 'Device deletion is now managed in NetBox.', 'deprecated': True}


@router.delete("/delete/{ip_address}")
async def delete_device_by_path(ip_address: str):
    """DEPRECATED: Devices are now managed in NetBox."""
    return {'error': 'Device deletion is now managed in NetBox.', 'deprecated': True}


# ============================================================================
# Network Groups Routes
# ============================================================================

@router.get("/network_groups")
async def get_network_groups():
    """Get network groups from NetBox sites."""
    try:
        from backend.services.netbox_service import NetBoxService
        from backend.api.routers.netbox import get_netbox_settings
        
        settings = get_netbox_settings()
        netbox = NetBoxService(
            url=settings.get('url', ''),
            token=settings.get('token', ''),
            verify_ssl=settings.get('verify_ssl', 'true').lower() == 'true'
        )
        
        if not netbox.is_configured:
            return []
        
        sites_result = netbox.get_sites(limit=1000)
        sites = sites_result.get('results', [])
        
        devices_result = netbox.get_devices(limit=10000)
        devices = devices_result.get('results', [])
        
        site_counts = {}
        for d in devices:
            site_name = d.get('site', {}).get('name', 'Unknown') if d.get('site') else 'Unknown'
            site_counts[site_name] = site_counts.get(site_name, 0) + 1
        
        summary = []
        for site in sites:
            site_name = site.get('name', 'Unknown')
            summary.append({
                'network_range': site_name,
                'device_count': site_counts.get(site_name, 0),
                'online_count': site_counts.get(site_name, 0),
                'snmp_count': site_counts.get(site_name, 0),
                'ssh_count': 0,
                'site_id': site.get('id'),
                'site_slug': site.get('slug'),
            })
        
        return summary
        
    except Exception as e:
        logger.error(f"Error fetching network groups: {e}")
        return []


# ============================================================================
# Settings Routes (legacy paths)
# ============================================================================

def get_settings():
    """Load settings from file."""
    settings_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'settings.json')
    default_settings = {
        'network_ranges': [],
        'snmp_community': 'public',
        'ssh_username': '',
        'ssh_password': '',
        'ssh_port': 22,
        'scan_timeout': 5,
        'max_threads': 50,
    }
    try:
        if os.path.exists(settings_path):
            with open(settings_path, 'r') as f:
                settings = json.load(f)
                for key, value in default_settings.items():
                    if key not in settings:
                        settings[key] = value
                return settings
    except:
        pass
    return default_settings


@router.get("/get_settings")
async def get_settings_route():
    """Get settings."""
    return get_settings()


@router.post("/save_settings")
async def save_settings_route(request: Request):
    """Save settings."""
    settings_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'settings.json')
    data = await request.json()
    
    try:
        with open(settings_path, 'w') as f:
            json.dump(data, f, indent=2)
        return {'success': True}
    except Exception as e:
        return {'error': str(e)}


@router.post("/test_settings")
async def test_settings_route():
    """Test settings."""
    return {'success': True, 'message': 'Settings test not implemented in legacy mode'}


# ============================================================================
# Interface/Scan Routes
# ============================================================================

class InterfaceRequest(BaseModel):
    ip: str


class PowerHistoryRequest(BaseModel):
    ip: Optional[str] = None
    ip_list: Optional[List[str]] = None
    ip_addresses: Optional[List[str]] = None
    interface_index: Optional[int] = None
    hours: int = 24


@router.post("/get_ssh_cli_interfaces")
async def get_ssh_cli_interfaces(req: InterfaceRequest):
    """Get SSH CLI interfaces for a device."""
    if not req.ip:
        return {'error': 'No IP provided'}
    
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM interface_scans 
            WHERE device_ip = %s 
            ORDER BY collected_at DESC LIMIT 100
        """, (req.ip,))
        interfaces = [dict(row) for row in cursor.fetchall()]
    return interfaces


@router.post("/get_combined_interfaces")
async def get_combined_interfaces(req: InterfaceRequest):
    """Get combined interfaces for a device."""
    if not req.ip:
        return {'error': 'No IP provided'}
    
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT * FROM interface_scans 
            WHERE device_ip = %s 
            ORDER BY collected_at DESC LIMIT 100
        """, (req.ip,))
        interfaces = [dict(row) for row in cursor.fetchall()]
    return interfaces


@router.post("/power_history")
async def get_power_history(req: PowerHistoryRequest):
    """Get optical power history."""
    ip = req.ip
    ip_list = req.ip_list or req.ip_addresses or []
    
    if not ip and ip_list:
        ip = ip_list[0] if len(ip_list) == 1 else None
    
    if not ip and not ip_list:
        return {'error': 'No IP provided'}
    
    db = get_db()
    with db.cursor() as cursor:
        all_history = []
        ips_to_query = [ip] if ip else ip_list
        
        for device_ip in ips_to_query:
            query = """
                SELECT device_ip, port_id, port_name, rx_power_dbm, tx_power_dbm, collected_at
                FROM optical_metrics
                WHERE device_ip = %s AND collected_at > NOW() - INTERVAL '%s hours'
            """
            params = [device_ip, req.hours]
            
            if req.interface_index is not None:
                query += " AND port_id = %s"
                params.append(req.interface_index)
            
            query += " ORDER BY collected_at DESC"
            cursor.execute(query, params)
            all_history.extend([dict(row) for row in cursor.fetchall()])
    
    return {'history': all_history}


# ============================================================================
# Topology Routes
# ============================================================================

class TopologyRequest(BaseModel):
    group_type: str = "network"
    group_id: Optional[str] = None


@router.post("/topology_data")
async def get_topology_data(req: TopologyRequest):
    """Get topology data for visualization."""
    try:
        from backend.services.netbox_service import NetBoxService
        from backend.api.routers.netbox import get_netbox_settings
        
        settings = get_netbox_settings()
        netbox = NetBoxService(
            url=settings.get('url', ''),
            token=settings.get('token', ''),
            verify_ssl=settings.get('verify_ssl', 'true').lower() == 'true'
        )
        
        if not netbox.is_configured:
            return {'nodes': [], 'links': []}
        
        params = {'limit': 10000}
        if req.group_type == 'network' and req.group_id:
            params['site'] = req.group_id
        
        result = netbox.get_devices(**params)
        netbox_devices = result.get('results', [])
        
        nodes = []
        for d in netbox_devices:
            primary_ip = d.get('primary_ip4') or d.get('primary_ip') or {}
            ip_address = primary_ip.get('address', '').split('/')[0] if primary_ip else None
            
            if not ip_address:
                continue
            
            nodes.append({
                'id': ip_address,
                'label': d.get('name') or ip_address,
                'ip': ip_address,
                'status': 'online' if d.get('status', {}).get('value') == 'active' else 'offline',
            })
        
        return {'nodes': nodes, 'links': []}
        
    except Exception as e:
        logger.error(f"Error fetching topology: {e}")
        return {'nodes': [], 'links': []}


# ============================================================================
# Notification Routes
# ============================================================================

class NotifyTestRequest(BaseModel):
    message: Optional[str] = "This is a test notification from OpsConductor"


@router.post("/api/notify/test")
async def test_notification(req: NotifyTestRequest):
    """Test notification."""
    try:
        from notification_service import send_notification
        
        result = send_notification(
            title='Test Notification',
            message=req.message,
            level='info'
        )
        
        return {'success': True, 'result': result}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ============================================================================
# Scan Trigger Routes
# ============================================================================

@router.post("/scan")
async def trigger_scan():
    """Trigger a network scan."""
    return {'success': True, 'message': 'Scan triggered (placeholder)'}


@router.post("/scan_selected")
async def scan_selected(request: Request):
    """Scan selected IPs."""
    data = await request.json()
    ips = data.get('ips', [])
    
    if not ips:
        return {'error': 'No IPs provided'}
    
    return {'success': True, 'message': f'Scanning {len(ips)} IPs (placeholder)'}


@router.post("/snmp_scan")
async def snmp_scan():
    """Trigger SNMP scan."""
    return {'success': True, 'message': 'SNMP scan started (placeholder)'}


@router.post("/ssh_scan")
async def ssh_scan():
    """Trigger SSH scan."""
    return {'success': True, 'message': 'SSH scan started (placeholder)'}
