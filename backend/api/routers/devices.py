"""
Devices API Router - FastAPI.

DEPRECATION NOTICE: Device inventory is now managed in NetBox.
Use /api/netbox/devices for device queries.
"""

from fastapi import APIRouter, Query
from typing import Optional
import logging

from backend.utils.responses import success_response, error_response, list_response

logger = logging.getLogger(__name__)

router = APIRouter()


def get_netbox_service():
    """Get configured NetBox service instance."""
    from backend.services.netbox_service import NetBoxService
    from backend.api.routers.netbox import get_netbox_settings
    
    settings = get_netbox_settings()
    return NetBoxService(
        url=settings.get('url', ''),
        token=settings.get('token', ''),
        verify_ssl=settings.get('verify_ssl', 'true').lower() == 'true'
    )


@router.get("")
async def list_devices(
    search: Optional[str] = Query(None, alias="q"),
    site: Optional[str] = None,
    role: Optional[str] = None
):
    """
    List all devices.
    
    UPDATED: Now fetches from NetBox as the source of truth.
    """
    try:
        netbox = get_netbox_service()
        
        if not netbox.is_configured:
            return list_response([])
        
        result = netbox.get_devices(q=search, site=site, role=role, limit=10000)
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
                'device_type': d.get('device_type', {}).get('model', '') if d.get('device_type') else '',
                'manufacturer': d.get('device_type', {}).get('manufacturer', {}).get('name', '') if d.get('device_type') else '',
                'site': d.get('site', {}).get('name', '') if d.get('site') else '',
                'role': d.get('role', {}).get('name', '') if d.get('role') else '',
                'status': d.get('status', {}).get('value', 'unknown'),
                'netbox_id': d.get('id'),
                'source': 'netbox',
            })
        
        return list_response(devices)
        
    except Exception as e:
        logger.error(f"Error fetching devices from NetBox: {e}")
        return list_response([])


@router.get("/{ip_address}")
async def get_device(ip_address: str):
    """Get a single device by IP address."""
    try:
        netbox = get_netbox_service()
        
        if not netbox.is_configured:
            return error_response('NETBOX_NOT_CONFIGURED', 'NetBox is not configured')
        
        result = netbox.get_devices(limit=10000)
        netbox_devices = result.get('results', [])
        
        for d in netbox_devices:
            primary_ip = d.get('primary_ip4') or d.get('primary_ip') or {}
            device_ip = primary_ip.get('address', '').split('/')[0] if primary_ip else None
            
            if device_ip == ip_address:
                device = {
                    'ip_address': device_ip,
                    'hostname': d.get('name', ''),
                    'device_type': d.get('device_type', {}).get('model', '') if d.get('device_type') else '',
                    'manufacturer': d.get('device_type', {}).get('manufacturer', {}).get('name', '') if d.get('device_type') else '',
                    'site': d.get('site', {}).get('name', '') if d.get('site') else '',
                    'role': d.get('role', {}).get('name', '') if d.get('role') else '',
                    'status': d.get('status', {}).get('value', 'unknown'),
                    'serial': d.get('serial', ''),
                    'comments': d.get('comments', ''),
                    'netbox_id': d.get('id'),
                    'netbox_url': d.get('url'),
                    'source': 'netbox',
                }
                return success_response(device)
        
        return error_response('NOT_FOUND', f'Device {ip_address} not found in NetBox')
        
    except Exception as e:
        logger.error(f"Error fetching device from NetBox: {e}")
        return error_response('INTERNAL_ERROR', str(e))


@router.post("")
async def create_device():
    """DEPRECATED: Devices are now managed in NetBox."""
    return error_response(
        'DEPRECATED', 
        'Device creation is now managed in NetBox. Use the PRTG → NetBox import or create devices directly in NetBox.'
    )


@router.delete("/{ip_address}")
async def delete_device(ip_address: str):
    """DEPRECATED: Devices are now managed in NetBox."""
    return error_response(
        'DEPRECATED',
        'Device deletion is now managed in NetBox. Please delete devices directly in NetBox.'
    )


@router.get("/summary/networks")
async def get_network_summary():
    """Get summary of devices grouped by network/site."""
    try:
        netbox = get_netbox_service()
        
        if not netbox.is_configured:
            return list_response([])
        
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
                'site_id': site.get('id'),
            })
        
        return list_response(summary)
        
    except Exception as e:
        logger.error(f"Error fetching network summary from NetBox: {e}")
        return list_response([])


@router.get("/summary/stats")
async def get_device_stats():
    """Get overall device statistics."""
    try:
        netbox = get_netbox_service()
        
        if not netbox.is_configured:
            return success_response({
                'total_devices': 0,
                'active_count': 0,
                'site_count': 0,
            })
        
        devices_result = netbox.get_devices(limit=10000)
        devices = devices_result.get('results', [])
        
        sites_result = netbox.get_sites(limit=1000)
        sites = sites_result.get('results', [])
        
        active_count = sum(1 for d in devices if d.get('status', {}).get('value') == 'active')
        
        stats = {
            'total_devices': len(devices),
            'active_count': active_count,
            'inactive_count': len(devices) - active_count,
            'site_count': len(sites),
            'source': 'netbox',
        }
        
        return success_response(stats)
        
    except Exception as e:
        logger.error(f"Error fetching device stats from NetBox: {e}")
        return success_response({
            'total_devices': 0,
            'active_count': 0,
            'site_count': 0,
            'error': str(e),
        })
