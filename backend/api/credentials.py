"""
Credentials API

REST API endpoints for credential vault management.
"""

from flask import Blueprint, request, jsonify
import logging

from backend.database import get_db as get_db_connection
from backend.utils.responses import success_response, error_response
from backend.services.credential_service import get_credential_service
from backend.services.credential_audit_service import get_audit_service

logger = logging.getLogger(__name__)

credentials_bp = Blueprint('credentials', __name__, url_prefix='/api/credentials')


# =============================================================================
# CREDENTIALS
# =============================================================================

@credentials_bp.route('', methods=['GET'])

def list_credentials():
    """List all credentials (without sensitive data)."""
    credential_type = request.args.get('type')
    category = request.args.get('category')
    environment = request.args.get('environment')
    status = request.args.get('status')
    include_expired = request.args.get('include_expired', 'true').lower() == 'true'
    
    try:
        service = get_credential_service()
        credentials = service.list_credentials(
            credential_type=credential_type,
            category=category,
            environment=environment,
            status=status,
            include_expired=include_expired
        )
        return jsonify(success_response(data={'credentials': credentials}))
    except Exception as e:
        logger.error(f"Error listing credentials: {e}")
        return jsonify(error_response('LIST_ERROR', str(e))), 500


@credentials_bp.route('', methods=['POST'])

def create_credential():
    """Create a new credential."""
    data = request.get_json()
    
    if not data:
        return jsonify(error_response('NO_DATA', 'No data provided')), 400
    
    name = data.get('name')
    credential_type = data.get('credential_type', 'ssh')
    
    if not name:
        return jsonify(error_response('MISSING_NAME', 'Name is required')), 400
    
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
    elif credential_type == 'winrm':
        credential_data = {
            'username': data.get('username', ''),
            'password': data.get('password', ''),
            'domain': data.get('domain', ''),
            'transport': data.get('winrm_transport', 'ntlm'),
            'port': data.get('winrm_port', 5985),
        }
    elif credential_type in ('certificate', 'pki'):
        credential_data = {
            'certificate': data.get('certificate', ''),
            'private_key': data.get('private_key', ''),
            'passphrase': data.get('passphrase', ''),
            'ca_certificate': data.get('ca_certificate', ''),
        }
    elif credential_type == 'ldap':
        credential_data = {
            'server': data.get('ldap_server', ''),
            'port': data.get('ldap_port', 389),
            'use_ssl': data.get('ldap_use_ssl', False),
            'bind_dn': data.get('bind_dn', ''),
            'bind_password': data.get('bind_password', ''),
            'base_dn': data.get('base_dn', ''),
            'user_search_filter': data.get('user_search_filter', '(uid={username})'),
            'group_search_filter': data.get('group_search_filter', ''),
        }
    elif credential_type == 'active_directory':
        # Support both direct credential_data and individual fields
        if data.get('credential_data'):
            credential_data = data.get('credential_data')
        else:
            credential_data = {
                'host': data.get('domain_controller', data.get('host', '')),
                'domain': data.get('ad_domain', data.get('domain', '')),
                'port': data.get('ad_port', data.get('port', 636)),
                'use_ssl': data.get('ad_use_ssl', data.get('use_ssl', True)),
                'username': data.get('username', ''),
                'password': data.get('password', ''),
                'base_dn': data.get('base_dn', ''),
                'user_search_filter': data.get('user_search_filter', '(sAMAccountName={username})'),
                'bind_dn_template': data.get('bind_dn_template', '{username}@' + data.get('ad_domain', data.get('domain', ''))),
            }
    elif credential_type == 'tacacs':
        credential_data = {
            'server': data.get('tacacs_server', ''),
            'port': data.get('tacacs_port', 49),
            'secret_key': data.get('tacacs_secret', ''),
            'timeout': data.get('tacacs_timeout', 5),
            'authentication_type': data.get('tacacs_auth_type', 'ascii'),  # ascii, pap, chap
        }
    elif credential_type == 'radius':
        credential_data = {
            'server': data.get('radius_server', ''),
            'auth_port': data.get('radius_auth_port', 1812),
            'acct_port': data.get('radius_acct_port', 1813),
            'secret_key': data.get('radius_secret', ''),
            'timeout': data.get('radius_timeout', 5),
            'retries': data.get('radius_retries', 3),
            'nas_identifier': data.get('nas_identifier', ''),
        }
    else:
        # Generic - store whatever is provided
        credential_data = {k: v for k, v in data.items() 
                          if k not in ['name', 'description', 'credential_type', 'valid_from', 'valid_until', 
                                       'category', 'environment', 'owner', 'tags', 'notes']}
    
    # Parse dates if provided
    valid_from = None
    valid_until = None
    if data.get('valid_from'):
        from datetime import datetime
        try:
            valid_from = datetime.fromisoformat(data['valid_from'].replace('Z', '+00:00'))
        except:
            pass
    if data.get('valid_until'):
        from datetime import datetime
        try:
            valid_until = datetime.fromisoformat(data['valid_until'].replace('Z', '+00:00'))
        except:
            pass
    
    try:
        service = get_credential_service()
        credential = service.create_credential(
            name=name,
            credential_type=credential_type,
            credential_data=credential_data,
            description=data.get('description'),
            username=data.get('username'),
            created_by=data.get('created_by'),
            valid_from=valid_from,
            valid_until=valid_until,
            category=data.get('category'),
            environment=data.get('environment'),
            owner=data.get('owner'),
            tags=data.get('tags'),
            notes=data.get('notes'),
        )
        return jsonify(success_response(data={'credential': credential})), 201
    except Exception as e:
        logger.error(f"Error creating credential: {e}")
        if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
            return jsonify(error_response('DUPLICATE', 'A credential with this name already exists')), 409
        return jsonify(error_response('CREATE_ERROR', str(e))), 500


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
# USAGE LOG (Legacy - use /audit for comprehensive logging)
# =============================================================================

@credentials_bp.route('/usage', methods=['GET'])
def get_usage_log():
    """Get credential usage log (legacy endpoint)."""
    credential_id = request.args.get('credential_id', type=int)
    limit = request.args.get('limit', 100, type=int)
    
    try:
        service = get_credential_service()
        log = service.get_usage_log(credential_id=credential_id, limit=limit)
        return jsonify(success_response(data={'usage_log': log}))
    except Exception as e:
        logger.error(f"Error getting usage log: {e}")
        return jsonify(error_response('USAGE_LOG_ERROR', str(e))), 500


# =============================================================================
# AUDIT LOG
# =============================================================================

@credentials_bp.route('/audit', methods=['GET'])
def get_audit_log():
    """Get comprehensive credential audit log."""
    credential_id = request.args.get('credential_id', type=int)
    action = request.args.get('action')
    performed_by = request.args.get('performed_by')
    target_device = request.args.get('target_device')
    success = request.args.get('success')
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Parse success as boolean
    success_bool = None
    if success is not None:
        success_bool = success.lower() == 'true'
    
    try:
        audit_service = get_audit_service()
        result = audit_service.get_audit_log(
            credential_id=credential_id,
            action=action,
            performed_by=performed_by,
            target_device=target_device,
            success=success_bool,
            limit=limit,
            offset=offset
        )
        return jsonify(success_response(data=result))
    except Exception as e:
        logger.error(f"Error getting audit log: {e}")
        return jsonify(error_response('AUDIT_LOG_ERROR', str(e))), 500


@credentials_bp.route('/audit/summary', methods=['GET'])
def get_audit_summary():
    """Get audit activity summary statistics."""
    credential_id = request.args.get('credential_id', type=int)
    days = request.args.get('days', 30, type=int)
    
    try:
        audit_service = get_audit_service()
        summary = audit_service.get_audit_summary(credential_id=credential_id, days=days)
        return jsonify(success_response(data={'summary': summary}))
    except Exception as e:
        logger.error(f"Error getting audit summary: {e}")
        return jsonify(error_response('AUDIT_SUMMARY_ERROR', str(e))), 500


@credentials_bp.route('/<int:credential_id>/history', methods=['GET'])
def get_credential_history(credential_id):
    """Get complete audit history for a specific credential."""
    limit = request.args.get('limit', 50, type=int)
    
    try:
        audit_service = get_audit_service()
        history = audit_service.get_credential_history(credential_id, limit=limit)
        return jsonify(success_response(data={'history': history}))
    except Exception as e:
        logger.error(f"Error getting credential history: {e}")
        return jsonify(error_response('HISTORY_ERROR', str(e))), 500


# =============================================================================
# STATISTICS & EXPIRATION
# =============================================================================

@credentials_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """Get credential vault statistics."""
    try:
        service = get_credential_service()
        stats = service.get_credential_statistics()
        return jsonify(success_response(data={'statistics': stats}))
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify(error_response('STATS_ERROR', str(e))), 500


@credentials_bp.route('/expiring', methods=['GET'])
def get_expiring():
    """Get credentials expiring soon."""
    days = request.args.get('days', 30, type=int)
    
    try:
        service = get_credential_service()
        expiring = service.get_expiring_credentials(days_ahead=days)
        return jsonify(success_response(data={'expiring': expiring, 'days_ahead': days}))
    except Exception as e:
        logger.error(f"Error getting expiring credentials: {e}")
        return jsonify(error_response('EXPIRING_ERROR', str(e))), 500


@credentials_bp.route('/expired', methods=['GET'])
def get_expired():
    """Get all expired credentials."""
    try:
        service = get_credential_service()
        expired = service.get_expired_credentials()
        return jsonify(success_response(data={'expired': expired}))
    except Exception as e:
        logger.error(f"Error getting expired credentials: {e}")
        return jsonify(error_response('EXPIRED_ERROR', str(e))), 500


@credentials_bp.route('/check-expirations', methods=['POST'])
def check_expirations():
    """Update expiration status for all credentials."""
    try:
        service = get_credential_service()
        count = service.update_expiration_status()
        return jsonify(success_response(
            data={'newly_expired': count},
            message=f'{count} credentials marked as expired'
        ))
    except Exception as e:
        logger.error(f"Error checking expirations: {e}")
        return jsonify(error_response('EXPIRATION_CHECK_ERROR', str(e))), 500


# =============================================================================
# ENTERPRISE AUTHENTICATION
# =============================================================================

@credentials_bp.route('/enterprise/configs', methods=['GET'])
def list_enterprise_auth_configs():
    """List all enterprise auth server configurations."""
    auth_type = request.args.get('type')
    
    try:
        service = get_credential_service()
        configs = service.list_enterprise_auth_configs(auth_type=auth_type)
        return jsonify(success_response(data={'configs': configs}))
    except Exception as e:
        logger.error(f"Error listing enterprise auth configs: {e}")
        return jsonify(error_response('LIST_CONFIGS_ERROR', str(e))), 500


@credentials_bp.route('/enterprise/configs', methods=['POST'])
def create_enterprise_auth_config():
    """Create a new enterprise auth server configuration."""
    data = request.get_json()
    
    name = data.get('name')
    auth_type = data.get('auth_type')
    credential_id = data.get('credential_id')
    
    if not name or not auth_type or not credential_id:
        return jsonify(error_response('MISSING_FIELDS', 'name, auth_type, and credential_id are required')), 400
    
    if auth_type not in ('tacacs', 'radius', 'ldap', 'active_directory'):
        return jsonify(error_response('INVALID_AUTH_TYPE', 'auth_type must be tacacs, radius, ldap, or active_directory')), 400
    
    try:
        service = get_credential_service()
        config = service.create_enterprise_auth_config(
            name=name,
            auth_type=auth_type,
            credential_id=credential_id,
            is_default=data.get('is_default', False),
            priority=data.get('priority', 0)
        )
        return jsonify(success_response(data={'config': config}, message='Enterprise auth config created')), 201
    except Exception as e:
        logger.error(f"Error creating enterprise auth config: {e}")
        return jsonify(error_response('CREATE_CONFIG_ERROR', str(e))), 500


@credentials_bp.route('/enterprise/configs/<int:config_id>', methods=['GET'])
def get_enterprise_auth_config(config_id):
    """Get a specific enterprise auth configuration."""
    try:
        service = get_credential_service()
        # Use list and filter since we don't have a get by ID method
        configs = service.list_enterprise_auth_configs()
        config = next((c for c in configs if c['id'] == config_id), None)
        
        if not config:
            return jsonify(error_response('NOT_FOUND', 'Enterprise auth config not found')), 404
        
        return jsonify(success_response(data={'config': config}))
    except Exception as e:
        logger.error(f"Error getting enterprise auth config: {e}")
        return jsonify(error_response('GET_CONFIG_ERROR', str(e))), 500


@credentials_bp.route('/enterprise/configs/<int:config_id>', methods=['DELETE'])
def delete_enterprise_auth_config(config_id):
    """Delete an enterprise auth configuration."""
    try:
        from backend.database import get_db
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM enterprise_auth_configs WHERE id = %s RETURNING id", (config_id,))
            deleted = cursor.fetchone()
            db.get_connection().commit()
            
            if not deleted:
                return jsonify(error_response('NOT_FOUND', 'Enterprise auth config not found')), 404
        
        return jsonify(success_response(message='Enterprise auth config deleted'))
    except Exception as e:
        logger.error(f"Error deleting enterprise auth config: {e}")
        return jsonify(error_response('DELETE_CONFIG_ERROR', str(e))), 500


@credentials_bp.route('/enterprise/users', methods=['GET'])
def list_enterprise_auth_users():
    """List all enterprise auth users."""
    config_id = request.args.get('config_id', type=int)
    
    try:
        service = get_credential_service()
        users = service.list_enterprise_auth_users(auth_config_id=config_id)
        return jsonify(success_response(data={'users': users}))
    except Exception as e:
        logger.error(f"Error listing enterprise auth users: {e}")
        return jsonify(error_response('LIST_USERS_ERROR', str(e))), 500


@credentials_bp.route('/enterprise/users', methods=['POST'])
def create_enterprise_auth_user():
    """Create a new enterprise auth user (service account)."""
    data = request.get_json()
    
    name = data.get('name')
    auth_config_id = data.get('auth_config_id')
    username = data.get('username')
    password = data.get('password')
    
    if not name or not auth_config_id or not username or not password:
        return jsonify(error_response('MISSING_FIELDS', 'name, auth_config_id, username, and password are required')), 400
    
    try:
        service = get_credential_service()
        user = service.create_enterprise_auth_user(
            name=name,
            auth_config_id=auth_config_id,
            username=username,
            password=password,
            description=data.get('description'),
            is_service_account=data.get('is_service_account', True)
        )
        return jsonify(success_response(data={'user': user}, message='Enterprise auth user created')), 201
    except Exception as e:
        logger.error(f"Error creating enterprise auth user: {e}")
        return jsonify(error_response('CREATE_USER_ERROR', str(e))), 500


@credentials_bp.route('/enterprise/users/<int:user_id>', methods=['GET'])
def get_enterprise_auth_user(user_id):
    """Get a specific enterprise auth user."""
    try:
        service = get_credential_service()
        user = service.get_enterprise_auth_user(user_id=user_id, include_secret=False)
        
        if not user:
            return jsonify(error_response('NOT_FOUND', 'Enterprise auth user not found')), 404
        
        return jsonify(success_response(data={'user': user}))
    except Exception as e:
        logger.error(f"Error getting enterprise auth user: {e}")
        return jsonify(error_response('GET_USER_ERROR', str(e))), 500


@credentials_bp.route('/enterprise/users/<int:user_id>', methods=['DELETE'])
def delete_enterprise_auth_user(user_id):
    """Delete an enterprise auth user."""
    try:
        from backend.database import get_db
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM enterprise_auth_users WHERE id = %s RETURNING id", (user_id,))
            deleted = cursor.fetchone()
            db.get_connection().commit()
            
            if not deleted:
                return jsonify(error_response('NOT_FOUND', 'Enterprise auth user not found')), 404
        
        return jsonify(success_response(message='Enterprise auth user deleted'))
    except Exception as e:
        logger.error(f"Error deleting enterprise auth user: {e}")
        return jsonify(error_response('DELETE_USER_ERROR', str(e))), 500


@credentials_bp.route('/enterprise/test-connection', methods=['POST'])
def test_enterprise_connection():
    """Test connection to an enterprise auth server."""
    data = request.get_json()
    
    config_id = data.get('config_id')
    if not config_id:
        return jsonify(error_response('MISSING_CONFIG_ID', 'config_id is required')), 400
    
    try:
        service = get_credential_service()
        configs = service.list_enterprise_auth_configs()
        config = next((c for c in configs if c['id'] == config_id), None)
        
        if not config:
            return jsonify(error_response('NOT_FOUND', 'Enterprise auth config not found')), 404
        
        # Get the full credential with server details
        cred = service.get_credential(config['credential_id'], include_secret=True)
        if not cred:
            return jsonify(error_response('CREDENTIAL_NOT_FOUND', 'Server credential not found')), 404
        
        auth_type = config['auth_type']
        server_config = cred.get('secret_data', {})
        
        # TODO: Implement actual connection tests for each auth type
        # For now, return a placeholder response
        return jsonify(success_response(
            data={
                'auth_type': auth_type,
                'server': server_config.get('server') or server_config.get('domain_controller'),
                'status': 'connection_test_not_implemented',
                'message': f'Connection test for {auth_type} is not yet implemented'
            }
        ))
    except Exception as e:
        logger.error(f"Error testing enterprise connection: {e}")
        return jsonify(error_response('TEST_CONNECTION_ERROR', str(e))), 500
