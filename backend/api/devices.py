"""
Device API Blueprint.

Routes for device CRUD operations.
All routes use standardized response format and error handling.
"""

from flask import Blueprint, request, jsonify
from ..utils.responses import success_response, error_response, list_response
from ..utils.errors import AppError, NotFoundError, ValidationError


devices_bp = Blueprint('devices', __name__, url_prefix='/api/devices')


def get_device_service():
    """Get device service instance (lazy import to avoid circular deps)."""
    from database import DatabaseManager
    from ..repositories.device_repo import DeviceRepository
    from ..repositories.group_repo import GroupRepository
    from ..services.device_service import DeviceService
    
    db = DatabaseManager()
    device_repo = DeviceRepository(db)
    group_repo = GroupRepository(db)
    return DeviceService(device_repo, group_repo)


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
    List all devices with optional filtering.
    
    Query params:
        filter_type: 'network', 'group', 'status'
        filter_id: Filter value
        search: Search term
    
    Returns:
        List of devices
    """
    service = get_device_service()
    
    filter_type = request.args.get('filter_type')
    filter_id = request.args.get('filter_id')
    search = request.args.get('search')
    
    devices = service.list_devices(
        filter_type=filter_type,
        filter_id=filter_id,
        search=search
    )
    
    return jsonify(list_response(devices))


@devices_bp.route('/<ip_address>', methods=['GET'])
def get_device(ip_address):
    """
    Get a single device by IP address.
    
    Args:
        ip_address: Device IP address
    
    Query params:
        include_groups: Include group memberships (default: false)
    
    Returns:
        Device record
    """
    service = get_device_service()
    
    include_groups = request.args.get('include_groups', 'false').lower() == 'true'
    
    if include_groups:
        device = service.get_device_with_groups(ip_address)
    else:
        device = service.get_device(ip_address)
    
    return jsonify(success_response(device))


@devices_bp.route('', methods=['POST'])
def create_device():
    """
    Create or update a device.
    
    Body:
        ip_address: Device IP address (required)
        ping_status: Ping status
        network_range: Network CIDR
        snmp_status: SNMP status
        ssh_status: SSH status
        rdp_status: RDP status
        snmp_data: SNMP data dictionary
    
    Returns:
        Created/updated device
    """
    service = get_device_service()
    data = request.get_json() or {}
    
    if 'ip_address' not in data:
        raise ValidationError('ip_address is required', field='ip_address')
    
    device = service.create_or_update_device(
        ip_address=data['ip_address'],
        ping_status=data.get('ping_status'),
        network_range=data.get('network_range'),
        snmp_status=data.get('snmp_status'),
        ssh_status=data.get('ssh_status'),
        rdp_status=data.get('rdp_status'),
        snmp_data=data.get('snmp_data')
    )
    
    return jsonify(success_response(device, message='Device saved')), 201


@devices_bp.route('/<ip_address>', methods=['DELETE'])
def delete_device(ip_address):
    """
    Delete a device by IP address.
    
    Args:
        ip_address: Device IP address
    
    Returns:
        Success message
    """
    service = get_device_service()
    service.delete_device(ip_address)
    
    return jsonify(success_response(message=f'Device {ip_address} deleted'))


@devices_bp.route('/summary/networks', methods=['GET'])
def get_network_summary():
    """
    Get summary of devices grouped by network.
    
    Returns:
        List of network summaries
    """
    service = get_device_service()
    summary = service.get_network_summary()
    
    return jsonify(list_response(summary))


@devices_bp.route('/summary/stats', methods=['GET'])
def get_device_stats():
    """
    Get overall device statistics.
    
    Returns:
        Statistics dictionary
    """
    service = get_device_service()
    stats = service.get_device_stats()
    
    return jsonify(success_response(stats))


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
