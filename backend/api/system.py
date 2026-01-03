"""
System API Blueprint.

Routes for system health, progress, and scan operations.
"""

import threading
from flask import Blueprint, request, jsonify
from ..utils.responses import success_response, error_response
from ..utils.errors import AppError


system_bp = Blueprint('system', __name__)

# Scan state (shared with legacy routes)
_scan_state = {
    'status': 'idle',
    'scanned': 0,
    'total': 0,
    'online': 0,
    'cancel_requested': False,
}
_scan_lock = threading.Lock()


def get_scan_state():
    """Get current scan state."""
    with _scan_lock:
        return dict(_scan_state)


def update_scan_state(**kwargs):
    """Update scan state."""
    with _scan_lock:
        _scan_state.update(kwargs)


@system_bp.errorhandler(AppError)
def handle_app_error(error):
    return jsonify(error_response(error.code, error.message, error.details)), error.status_code


@system_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify(success_response({
        'status': 'healthy',
        'service': 'opsconductor-backend'
    }))


@system_bp.route('/progress', methods=['GET'])
def get_progress():
    """Get scan progress."""
    state = get_scan_state()
    return jsonify(state)


@system_bp.route('/cancel_scan', methods=['POST'])

def cancel_scan():
    """Cancel running scan."""
    update_scan_state(cancel_requested=True)
    return jsonify(success_response(message='Scan cancellation requested'))


@system_bp.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint."""
    return jsonify(success_response({'message': 'Backend is running'}))


@system_bp.route('/check-tool', methods=['GET'])

def check_tool():
    """
    Check if a tool is available on the system.
    
    Query params:
        tool: Name of the tool to check (e.g., 'ping', 'nmap', 'traceroute')
    
    Returns:
        available: bool
        version: str (if available)
        path: str (if available)
    """
    import subprocess
    import shutil
    
    tool = request.args.get('tool')
    if not tool:
        return jsonify(error_response('Tool name required')), 400
    
    # Security: only allow specific known tools
    allowed_tools = {
        'ping', 'nmap', 'traceroute', 'arp-scan', 'ssh', 'snmpget', 'snmpwalk',
        'curl', 'wget', 'python3', 'python', 'node', 'npm'
    }
    
    if tool not in allowed_tools:
        return jsonify(error_response(f'Tool "{tool}" is not in the allowed list')), 400
    
    # Check if tool exists
    tool_path = shutil.which(tool)
    
    if not tool_path:
        return jsonify(success_response({
            'tool': tool,
            'available': False,
        }))
    
    # Try to get version
    version = None
    try:
        version_flags = {
            'ping': ['-V'],
            'nmap': ['--version'],
            'traceroute': ['--version'],
            'arp-scan': ['--version'],
            'ssh': ['-V'],
            'snmpget': ['-V'],
            'snmpwalk': ['-V'],
            'curl': ['--version'],
            'wget': ['--version'],
            'python3': ['--version'],
            'python': ['--version'],
            'node': ['--version'],
            'npm': ['--version'],
        }
        
        flag = version_flags.get(tool, ['--version'])
        result = subprocess.run(
            [tool] + flag,
            capture_output=True,
            text=True,
            timeout=5
        )
        version = (result.stdout or result.stderr).strip().split('\n')[0][:100]
    except Exception:
        pass
    
    return jsonify(success_response({
        'tool': tool,
        'available': True,
        'path': tool_path,
        'version': version,
    }))


@system_bp.route('/check-network', methods=['GET'])

def check_network():
    """Check network connectivity."""
    import socket
    
    # Check basic network
    network_available = True
    internet_available = False
    
    try:
        # Try to resolve a common domain
        socket.gethostbyname('google.com')
        internet_available = True
    except socket.gaierror:
        pass
    
    return jsonify(success_response({
        'available': network_available,
        'internet': internet_available,
    }))


@system_bp.route('/check-database', methods=['GET'])

def check_database():
    """Check database connectivity."""
    from backend.database import get_db
    
    try:
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute('SELECT 1')
        return jsonify(success_response({
            'available': True,
            'type': 'postgresql',
        }))
    except Exception as e:
        return jsonify(success_response({
            'available': False,
            'error': str(e),
        }))


@system_bp.route('/api/system/logging/settings', methods=['GET'])
@system_bp.route('/logging/settings', methods=['GET'])

def get_logging_settings():
    """Get logging settings."""
    from database import DatabaseManager
    
    db = DatabaseManager()
    settings = {
        'log_level': 'INFO',
        'file_logging_enabled': True,
        'database_logging_enabled': True,
        'json_logging_enabled': True,
        'max_file_size_mb': 10,
        'backup_count': 10,
        'retention_days': 30,
        'console_logging_enabled': True,
    }
    
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT key, value FROM system_settings 
                WHERE key LIKE 'logging_%'
            """)
            rows = cursor.fetchall()
        
        for row in rows:
            key = row['key'].replace('logging_', '')
            settings[key] = row['value']
    except Exception as e:
        pass  # Return defaults if table doesn't exist
    
    return jsonify(success_response(settings))


@system_bp.route('/api/system/logging/settings', methods=['PUT'])
@system_bp.route('/logging/settings', methods=['PUT'])

def update_logging_settings():
    """Update logging settings."""
    from database import DatabaseManager
    
    db = DatabaseManager()
    data = request.get_json() or {}
    
    try:
        with db.cursor() as cursor:
            for key, value in data.items():
                cursor.execute("""
                    INSERT INTO system_settings (key, value, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = NOW()
                """, (f'logging_{key}', str(value), str(value)))
            db.get_connection().commit()
        
        return jsonify(success_response(message='Logging settings saved'))
    except Exception as e:
        return jsonify(error_response('SAVE_ERROR', str(e))), 500
