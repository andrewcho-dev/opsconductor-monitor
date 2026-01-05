"""
Settings API Blueprint.

Routes for application settings management.
"""

import os
from flask import Blueprint, request, jsonify
from ..utils.responses import success_response, error_response
from ..utils.errors import AppError, ValidationError


settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')


def get_settings_file_path():
    """Get path to settings file."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'settings.json')


@settings_bp.errorhandler(AppError)
def handle_app_error(error):
    return jsonify(error_response(error.code, error.message, error.details)), error.status_code


@settings_bp.route('', methods=['GET'])

def get_settings():
    """Get current settings."""
    import json
    
    settings_path = get_settings_file_path()
    
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
                # Merge with defaults
                for key, value in default_settings.items():
                    if key not in settings:
                        settings[key] = value
                return jsonify(success_response(settings))
    except Exception as e:
        pass
    
    return jsonify(success_response(default_settings))


@settings_bp.route('', methods=['POST'])

def save_settings():
    """Save settings."""
    import json
    
    settings_path = get_settings_file_path()
    data = request.get_json() or {}
    
    try:
        with open(settings_path, 'w') as f:
            json.dump(data, f, indent=2)
        return jsonify(success_response(data, message='Settings saved'))
    except Exception as e:
        raise AppError('SETTINGS_ERROR', f'Failed to save settings: {str(e)}', 500)


@settings_bp.route('/test', methods=['POST'])

def test_settings():
    """Test settings (connectivity test)."""
    data = request.get_json() or {}
    
    # Test SSH connectivity if credentials provided
    results = {
        'ssh': None,
        'snmp': None,
    }
    
    target = data.get('test_target')
    if not target:
        return jsonify(success_response(results, message='No test target specified'))
    
    # Test SSH
    if data.get('ssh_username') and data.get('ssh_password'):
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=target,
                port=data.get('ssh_port', 22),
                username=data['ssh_username'],
                password=data['ssh_password'],
                timeout=5
            )
            client.close()
            results['ssh'] = {'success': True, 'message': 'SSH connection successful'}
        except Exception as e:
            results['ssh'] = {'success': False, 'message': str(e)}
    
    # Test SNMP
    if data.get('snmp_community'):
        try:
            from pysnmp.hlapi.v3arch.asyncio import get_cmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
            
            iterator = get_cmd(
                SnmpEngine(),
                CommunityData(data['snmp_community']),
                UdpTransportTarget((target, 161), timeout=5, retries=0),
                ContextData(),
                ObjectType(ObjectIdentity('1.3.6.1.2.1.1.1.0'))
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            if errorIndication:
                results['snmp'] = {'success': False, 'message': str(errorIndication)}
            elif errorStatus:
                results['snmp'] = {'success': False, 'message': str(errorStatus)}
            else:
                results['snmp'] = {'success': True, 'message': 'SNMP connection successful'}
        except Exception as e:
            results['snmp'] = {'success': False, 'message': str(e)}
    
    return jsonify(success_response(results))


@settings_bp.route('/database', methods=['GET'])
def get_database_settings():
    """Get database connection settings."""
    import os
    return jsonify(success_response({
        'db_host': os.getenv('PG_HOST', 'localhost'),
        'db_port': int(os.getenv('PG_PORT', 5432)),
        'db_name': os.getenv('PG_DATABASE', 'opsconductor'),
        'db_username': os.getenv('PG_USER', 'postgres'),
        'db_ssl_mode': 'prefer',
    }))


@settings_bp.route('/database/test', methods=['POST'])
def test_database_connection():
    """Test database connection."""
    try:
        from database import DatabaseManager
        db = DatabaseManager()
        # Simple query to test connection
        result = db.execute_query("SELECT 1 as test")
        if result:
            return jsonify(success_response({'connected': True}, message='Database connection successful'))
        else:
            return jsonify(error_response('DB_ERROR', 'Query returned no results')), 500
    except Exception as e:
        return jsonify(error_response('DB_ERROR', f'Connection failed: {str(e)}')), 500


# Legacy routes for backward compatibility
@settings_bp.route('/get_settings', methods=['GET'])
def get_settings_legacy():
    """Legacy endpoint."""
    return get_settings()


@settings_bp.route('/save_settings', methods=['POST'])
def save_settings_legacy():
    """Legacy endpoint."""
    return save_settings()


@settings_bp.route('/test_settings', methods=['POST'])
def test_settings_legacy():
    """Legacy endpoint."""
    return test_settings()
