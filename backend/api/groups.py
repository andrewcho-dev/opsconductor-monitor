"""
Groups API Blueprint.

Routes for device group CRUD operations and membership management.
"""

from flask import Blueprint, request, jsonify
from ..utils.responses import success_response, error_response, list_response
from ..utils.errors import AppError, NotFoundError, ValidationError


groups_bp = Blueprint('groups', __name__, url_prefix='/api/device_groups')


def get_group_service():
    """Get group service instance."""
    from database import DatabaseManager
    from ..repositories.group_repo import GroupRepository
    from ..services.group_service import GroupService
    
    db = DatabaseManager()
    group_repo = GroupRepository(db)
    return GroupService(group_repo)


@groups_bp.errorhandler(AppError)
def handle_app_error(error):
    """Handle application errors."""
    return jsonify(error_response(error.code, error.message, error.details)), error.status_code


@groups_bp.errorhandler(Exception)
def handle_generic_error(error):
    """Handle unexpected errors."""
    return jsonify(error_response('INTERNAL_ERROR', str(error))), 500


@groups_bp.route('', methods=['GET'])

def list_groups():
    """
    List all device groups with device counts.
    
    Returns:
        List of groups
    """
    service = get_group_service()
    groups = service.list_groups()
    
    return jsonify(list_response(groups))


@groups_bp.route('/<int:group_id>', methods=['GET'])

def get_group(group_id):
    """
    Get a single group by ID.
    
    Args:
        group_id: Group ID
    
    Query params:
        include_devices: Include device list (default: false)
    
    Returns:
        Group record
    """
    service = get_group_service()
    
    include_devices = request.args.get('include_devices', 'false').lower() == 'true'
    
    if include_devices:
        group = service.get_group_with_devices(group_id)
    else:
        group = service.get_group(group_id)
    
    return jsonify(success_response(group))


@groups_bp.route('', methods=['POST'])

def create_group():
    """
    Create a new device group.
    
    Body:
        group_name: Group name (required)
        description: Optional description
    
    Returns:
        Created group
    """
    service = get_group_service()
    data = request.get_json() or {}
    
    if 'group_name' not in data:
        raise ValidationError('group_name is required', field='group_name')
    
    group = service.create_group(
        group_name=data['group_name'],
        description=data.get('description')
    )
    
    return jsonify(success_response(group, message='Group created')), 201


@groups_bp.route('/<int:group_id>', methods=['PUT'])

def update_group(group_id):
    """
    Update a device group.
    
    Args:
        group_id: Group ID
    
    Body:
        group_name: New group name
        description: New description
    
    Returns:
        Updated group
    """
    service = get_group_service()
    data = request.get_json() or {}
    
    group = service.update_group(
        group_id=group_id,
        group_name=data.get('group_name'),
        description=data.get('description')
    )
    
    return jsonify(success_response(group, message='Group updated'))


@groups_bp.route('/<int:group_id>', methods=['DELETE'])

def delete_group(group_id):
    """
    Delete a device group.
    
    Args:
        group_id: Group ID
    
    Returns:
        Success message
    """
    service = get_group_service()
    service.delete_group(group_id)
    
    return jsonify(success_response(message='Group deleted'))


@groups_bp.route('/<int:group_id>/devices', methods=['GET'])

def get_group_devices(group_id):
    """
    Get all devices in a group.
    
    Args:
        group_id: Group ID
    
    Returns:
        List of devices
    """
    service = get_group_service()
    group = service.get_group_with_devices(group_id)
    
    return jsonify(list_response(group.get('devices', [])))


@groups_bp.route('/<int:group_id>/devices', methods=['POST'])

def add_device_to_group(group_id):
    """
    Add a device to a group.
    
    Args:
        group_id: Group ID
    
    Body:
        ip_address: Device IP address (for single device)
        ip_addresses: List of IP addresses (for multiple devices)
    
    Returns:
        Success message or result summary
    """
    service = get_group_service()
    data = request.get_json() or {}
    
    # Handle multiple devices
    if 'ip_addresses' in data:
        result = service.add_devices(group_id, data['ip_addresses'])
        return jsonify(success_response(result, message=f"Added {result['added']} devices"))
    
    # Handle single device
    if 'ip_address' not in data:
        raise ValidationError('ip_address or ip_addresses is required')
    
    service.add_device(group_id, data['ip_address'])
    return jsonify(success_response(message='Device added to group'))


@groups_bp.route('/<int:group_id>/devices/<ip_address>', methods=['DELETE'])

def remove_device_from_group(group_id, ip_address):
    """
    Remove a device from a group.
    
    Args:
        group_id: Group ID
        ip_address: Device IP address
    
    Returns:
        Success message
    """
    service = get_group_service()
    service.remove_device(group_id, ip_address)
    
    return jsonify(success_response(message='Device removed from group'))
