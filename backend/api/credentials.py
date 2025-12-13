"""
Credentials API

REST API endpoints for credential vault management.
"""

from flask import Blueprint, request, jsonify
import logging

from backend.database import get_db as get_db_connection
from backend.utils.responses import success_response, error_response
from backend.services.credential_service import get_credential_service

logger = logging.getLogger(__name__)

credentials_bp = Blueprint('credentials', __name__, url_prefix='/api/credentials')


# =============================================================================
# CREDENTIALS
# =============================================================================

@credentials_bp.route('', methods=['GET'])
def list_credentials():
    """List all credentials (without sensitive data)."""
    credential_type = request.args.get('type')
    
    try:
        service = get_credential_service()
        credentials = service.list_credentials(credential_type)
        return jsonify(success_response(data={'credentials': credentials}))
    except Exception as e:
        logger.error(f"Error listing credentials: {e}")
        return jsonify(error_response(str(e))), 500


@credentials_bp.route('', methods=['POST'])
def create_credential():
    """Create a new credential."""
    data = request.get_json()
    
    if not data:
        return jsonify(error_response('No data provided')), 400
    
    name = data.get('name')
    credential_type = data.get('credential_type', 'ssh')
    
    if not name:
        return jsonify(error_response('Name is required')), 400
    
    # Build credential data based on type
    credential_data = {}
    
    if credential_type == 'ssh':
        credential_data = {
            'username': data.get('username', ''),
            'password': data.get('password', ''),
            'private_key': data.get('private_key', ''),
            'passphrase': data.get('passphrase', ''),
            'port': data.get('port', 22),
        }
    elif credential_type == 'snmp':
        credential_data = {
            'version': data.get('snmp_version', '2c'),
            'community': data.get('community', ''),
            # SNMPv3
            'security_name': data.get('security_name', ''),
            'auth_protocol': data.get('auth_protocol', ''),
            'auth_password': data.get('auth_password', ''),
            'priv_protocol': data.get('priv_protocol', ''),
            'priv_password': data.get('priv_password', ''),
        }
    elif credential_type == 'api_key':
        credential_data = {
            'api_key': data.get('api_key', ''),
            'api_secret': data.get('api_secret', ''),
            'token': data.get('token', ''),
        }
    elif credential_type == 'password':
        credential_data = {
            'username': data.get('username', ''),
            'password': data.get('password', ''),
        }
    else:
        # Generic - store whatever is provided
        credential_data = {k: v for k, v in data.items() 
                          if k not in ['name', 'description', 'credential_type']}
    
    try:
        service = get_credential_service()
        credential = service.create_credential(
            name=name,
            credential_type=credential_type,
            credential_data=credential_data,
            description=data.get('description'),
            username=data.get('username'),
            created_by=data.get('created_by')
        )
        return jsonify(success_response(data={'credential': credential})), 201
    except Exception as e:
        logger.error(f"Error creating credential: {e}")
        if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
            return jsonify(error_response('A credential with this name already exists')), 409
        return jsonify(error_response(str(e))), 500


@credentials_bp.route('/<int:credential_id>', methods=['GET'])
def get_credential(credential_id):
    """Get a credential by ID."""
    try:
        service = get_credential_service()
        credential = service.get_credential(credential_id, include_secret=False)
        
        if not credential:
            return jsonify(error_response('Credential not found')), 404
        
        return jsonify(success_response(data={'credential': credential}))
    except Exception as e:
        logger.error(f"Error getting credential: {e}")
        return jsonify(error_response(str(e))), 500


@credentials_bp.route('/<int:credential_id>', methods=['PUT'])
def update_credential(credential_id):
    """Update a credential."""
    data = request.get_json()
    
    if not data:
        return jsonify(error_response('No data provided')), 400
    
    try:
        service = get_credential_service()
        
        # Get existing credential to determine type
        existing = service.get_credential(credential_id)
        if not existing:
            return jsonify(error_response('Credential not found')), 404
        
        # Build credential data if sensitive fields provided
        credential_data = None
        credential_type = existing['credential_type']
        
        # Check if any sensitive fields are being updated
        sensitive_fields = ['password', 'private_key', 'passphrase', 'community',
                          'auth_password', 'priv_password', 'api_key', 'api_secret', 'token']
        
        if any(field in data for field in sensitive_fields):
            # Rebuild credential data
            if credential_type == 'ssh':
                credential_data = {
                    'username': data.get('username', ''),
                    'password': data.get('password', ''),
                    'private_key': data.get('private_key', ''),
                    'passphrase': data.get('passphrase', ''),
                    'port': data.get('port', 22),
                }
            elif credential_type == 'snmp':
                credential_data = {
                    'version': data.get('snmp_version', '2c'),
                    'community': data.get('community', ''),
                    'security_name': data.get('security_name', ''),
                    'auth_protocol': data.get('auth_protocol', ''),
                    'auth_password': data.get('auth_password', ''),
                    'priv_protocol': data.get('priv_protocol', ''),
                    'priv_password': data.get('priv_password', ''),
                }
            elif credential_type == 'api_key':
                credential_data = {
                    'api_key': data.get('api_key', ''),
                    'api_secret': data.get('api_secret', ''),
                    'token': data.get('token', ''),
                }
            elif credential_type == 'password':
                credential_data = {
                    'username': data.get('username', ''),
                    'password': data.get('password', ''),
                }
        
        credential = service.update_credential(
            credential_id=credential_id,
            name=data.get('name'),
            description=data.get('description'),
            credential_data=credential_data,
            username=data.get('username')
        )
        
        if not credential:
            return jsonify(error_response('Credential not found')), 404
        
        return jsonify(success_response(data={'credential': credential}))
    except Exception as e:
        logger.error(f"Error updating credential: {e}")
        return jsonify(error_response(str(e))), 500


@credentials_bp.route('/<int:credential_id>', methods=['DELETE'])
def delete_credential(credential_id):
    """Delete a credential."""
    try:
        service = get_credential_service()
        success = service.delete_credential(credential_id)
        
        if not success:
            return jsonify(error_response('Credential not found')), 404
        
        return jsonify(success_response(message='Credential deleted'))
    except Exception as e:
        logger.error(f"Error deleting credential: {e}")
        return jsonify(error_response(str(e))), 500


# =============================================================================
# CREDENTIAL GROUPS
# =============================================================================

@credentials_bp.route('/groups', methods=['GET'])
def list_groups():
    """List all credential groups."""
    try:
        service = get_credential_service()
        groups = service.list_groups()
        return jsonify(success_response(data={'groups': groups}))
    except Exception as e:
        logger.error(f"Error listing groups: {e}")
        return jsonify(error_response(str(e))), 500


@credentials_bp.route('/groups', methods=['POST'])
def create_group():
    """Create a credential group."""
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify(error_response('Name is required')), 400
    
    try:
        service = get_credential_service()
        group = service.create_group(
            name=data['name'],
            description=data.get('description')
        )
        return jsonify(success_response(data={'group': group})), 201
    except Exception as e:
        logger.error(f"Error creating group: {e}")
        return jsonify(error_response(str(e))), 500


@credentials_bp.route('/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    """Delete a credential group."""
    try:
        service = get_credential_service()
        success = service.delete_group(group_id)
        
        if not success:
            return jsonify(error_response('Group not found')), 404
        
        return jsonify(success_response(message='Group deleted'))
    except Exception as e:
        logger.error(f"Error deleting group: {e}")
        return jsonify(error_response(str(e))), 500


@credentials_bp.route('/groups/<int:group_id>/members', methods=['POST'])
def add_group_member(group_id):
    """Add a credential to a group."""
    data = request.get_json()
    
    if not data or not data.get('credential_id'):
        return jsonify(error_response('credential_id is required')), 400
    
    try:
        service = get_credential_service()
        success = service.add_to_group(data['credential_id'], group_id)
        
        if not success:
            return jsonify(error_response('Failed to add credential to group')), 400
        
        return jsonify(success_response(message='Credential added to group'))
    except Exception as e:
        logger.error(f"Error adding to group: {e}")
        return jsonify(error_response(str(e))), 500


@credentials_bp.route('/groups/<int:group_id>/members/<int:credential_id>', methods=['DELETE'])
def remove_group_member(group_id, credential_id):
    """Remove a credential from a group."""
    try:
        service = get_credential_service()
        success = service.remove_from_group(credential_id, group_id)
        
        if not success:
            return jsonify(error_response('Credential not in group')), 404
        
        return jsonify(success_response(message='Credential removed from group'))
    except Exception as e:
        logger.error(f"Error removing from group: {e}")
        return jsonify(error_response(str(e))), 500


# =============================================================================
# DEVICE ASSIGNMENTS
# =============================================================================

@credentials_bp.route('/devices/<ip_address>', methods=['GET'])
def get_device_credentials(ip_address):
    """Get credentials assigned to a device."""
    credential_type = request.args.get('type')
    
    try:
        service = get_credential_service()
        credentials = service.get_credentials_for_device(
            ip_address=ip_address,
            credential_type=credential_type,
            include_secret=False
        )
        return jsonify(success_response(data={'credentials': credentials}))
    except Exception as e:
        logger.error(f"Error getting device credentials: {e}")
        return jsonify(error_response(str(e))), 500


@credentials_bp.route('/devices/<ip_address>/assign', methods=['POST'])
def assign_credential_to_device(ip_address):
    """Assign a credential to a device."""
    data = request.get_json()
    
    if not data or not data.get('credential_id'):
        return jsonify(error_response('credential_id is required')), 400
    
    try:
        service = get_credential_service()
        success = service.assign_to_device(
            credential_id=data['credential_id'],
            ip_address=ip_address,
            credential_type=data.get('credential_type'),
            priority=data.get('priority', 0)
        )
        
        if not success:
            return jsonify(error_response('Failed to assign credential')), 400
        
        return jsonify(success_response(message='Credential assigned to device'))
    except Exception as e:
        logger.error(f"Error assigning credential: {e}")
        return jsonify(error_response(str(e))), 500


# =============================================================================
# USAGE LOG
# =============================================================================

@credentials_bp.route('/usage', methods=['GET'])
def get_usage_log():
    """Get credential usage log."""
    credential_id = request.args.get('credential_id', type=int)
    limit = request.args.get('limit', 100, type=int)
    
    try:
        service = get_credential_service()
        log = service.get_usage_log(credential_id=credential_id, limit=limit)
        return jsonify(success_response(data={'usage_log': log}))
    except Exception as e:
        logger.error(f"Error getting usage log: {e}")
        return jsonify(error_response(str(e))), 500
