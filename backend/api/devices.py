"""
Device API Blueprint.

DEPRECATION NOTICE:
==================
This API is DEPRECATED. Device inventory is now managed in NetBox.
Use /api/netbox/devices for device queries.

Routes for device CRUD operations.
All routes use standardized response format and error handling.
"""

from flask import Blueprint, request, jsonify
from ..utils.responses import success_response, error_response, list_response
from ..utils.errors import AppError, NotFoundError, ValidationError
from ..services.logging_service import get_logger, LogSource

logger = get_logger(__name__, LogSource.API)

devices_bp = Blueprint('devices', __name__, url_prefix='/api/devices')


def get_netbox_service():
    """Get configured NetBox service instance."""
    from ..services.netbox_service import NetBoxService
    from ..api.netbox import get_netbox_settings
    
    settings = get_netbox_settings()
    return NetBoxService(
        url=settings.get('url', ''),
        token=settings.get('token', ''),
        verify_ssl=settings.get('verify_ssl', 'true').lower() == 'true'
    )


@devices_bp.errorhandler(AppError)
def handle_app_error(error):
    """Handle application errors."""
    return jsonify(error_response(error.code, error.message, error.details)), error.status_code


@devices_bp.errorhandler(Exception)
def handle_generic_error(error):
    """Handle unexpected errors."""
    return jsonify(error_response('INTERNAL_ERROR', str(error))), 500


@devices_bp.route('', methods=['GET'])
def list_devices():
    """
    List all devices.
    
    UPDATED: Now fetches from NetBox as the source of truth.
    
    Query params:
        search: Search term
        site: Filter by site
        role: Filter by role
    
    Returns:
        List of devices from NetBox
    """
    try:
        netbox = get_netbox_service()
        
        if not netbox.is_configured:
            return jsonify(list_response([]))
        
        # Get filter params
        search = request.args.get('search') or request.args.get('q')
        site = request.args.get('site')
        role = request.args.get('role')
        
        result = netbox.get_devices(
            q=search,
            site=site,
            role=role,
            limit=10000
        )
        
        netbox_devices = result.get('results', [])
        
        # Transform to standard format
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
        
        return jsonify(list_response(devices))
        
    except Exception as e:
        logger.error(f"Error fetching devices from NetBox: {e}")
        return jsonify(list_response([]))


@devices_bp.route('/<ip_address>', methods=['GET'])
def get_device(ip_address):
    """
    Get a single device by IP address.
    
    UPDATED: Now fetches from NetBox.
    
    Args:
        ip_address: Device IP address
    
    Returns:
        Device record from NetBox
    """
    try:
        netbox = get_netbox_service()
        
        if not netbox.is_configured:
            return jsonify(error_response('NETBOX_NOT_CONFIGURED', 'NetBox is not configured')), 503
        
        # Get all devices and find by IP
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
                return jsonify(success_response(device))
        
        return jsonify(error_response('NOT_FOUND', f'Device {ip_address} not found in NetBox')), 404
        
    except Exception as e:
        logger.error(f"Error fetching device from NetBox: {e}")
        return jsonify(error_response('INTERNAL_ERROR', str(e))), 500


@devices_bp.route('', methods=['POST'])
def create_device():
    """
    Create or update a device.
    
    DEPRECATED: Devices are now managed in NetBox.
    Use /api/import/execute to import devices to NetBox.
    """
    return jsonify(error_response(
        'DEPRECATED', 
        'Device creation is now managed in NetBox. Use the PRTG → NetBox import or create devices directly in NetBox.'
    )), 400


@devices_bp.route('/<ip_address>', methods=['DELETE'])
def delete_device(ip_address):
    """
    Delete a device by IP address.
    
    DEPRECATED: Devices are now managed in NetBox.
    """
    return jsonify(error_response(
        'DEPRECATED',
        'Device deletion is now managed in NetBox. Please delete devices directly in NetBox.'
    )), 400


@devices_bp.route('/summary/networks', methods=['GET'])
def get_network_summary():
    """
    Get summary of devices grouped by network/site.
    
    UPDATED: Now returns NetBox sites with device counts.
    """
    try:
        netbox = get_netbox_service()
        
        if not netbox.is_configured:
            return jsonify(list_response([]))
        
        # Get sites and device counts
        sites_result = netbox.get_sites(limit=1000)
        sites = sites_result.get('results', [])
        
        devices_result = netbox.get_devices(limit=10000)
        devices = devices_result.get('results', [])
        
        # Count devices per site
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
        
        return jsonify(list_response(summary))
        
    except Exception as e:
        logger.error(f"Error fetching network summary from NetBox: {e}")
        return jsonify(list_response([]))


@devices_bp.route('/summary/stats', methods=['GET'])
def get_device_stats():
    """
    Get overall device statistics.
    
    UPDATED: Now returns stats from NetBox.
    
    Returns:
        Statistics dictionary
    """
    try:
        netbox = get_netbox_service()
        
        if not netbox.is_configured:
            return jsonify(success_response({
                'total_devices': 0,
                'active_count': 0,
                'site_count': 0,
            }))
        
        # Get devices and sites from NetBox
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
        
        return jsonify(success_response(stats))
        
    except Exception as e:
        logger.error(f"Error fetching device stats from NetBox: {e}")
        return jsonify(success_response({
            'total_devices': 0,
            'active_count': 0,
            'site_count': 0,
            'error': str(e),
        }))


@devices_bp.route('/<ip_address>/groups', methods=['GET'])
def get_device_groups(ip_address):
    """
    Get all groups a device belongs to.
    
    Args:
        ip_address: Device IP address
    
    Returns:
        List of groups
    """
    service = get_device_service()
    
    # Verify device exists
    service.get_device(ip_address)
    
    # Get groups from group service
    from ..repositories.group_repo import GroupRepository
    from database import DatabaseManager
    
    db = DatabaseManager()
    group_repo = GroupRepository(db)
    groups = group_repo.get_groups_for_device(ip_address)
    
    return jsonify(list_response(groups))
