"""
WinRM API Blueprint.

Routes for Windows Remote Management operations.
"""

from flask import Blueprint, request, jsonify
from ..utils.responses import success_response, error_response
from ..executors.winrm_executor import WinRMExecutor


winrm_bp = Blueprint('winrm', __name__, url_prefix='/api/winrm')
executor = WinRMExecutor()


@winrm_bp.route('/test', methods=['POST'])

def test_connection():
    """
    Test WinRM connectivity to a Windows target.
    
    Request body:
        target: IP address or hostname
        username: Windows username
        password: Windows password
        domain: Optional domain name
        transport: Authentication transport (ntlm, kerberos, basic)
        port: WinRM port (5985 for HTTP, 5986 for HTTPS)
    """
    data = request.get_json() or {}
    
    target = data.get('target')
    if not target:
        return jsonify(error_response('MISSING_TARGET', 'Target is required')), 400
    
    config = {
        'username': data.get('username', ''),
        'password': data.get('password', ''),
        'domain': data.get('domain', ''),
        'transport': data.get('transport', 'ntlm'),
        'port': data.get('port', 5985),
        'timeout': data.get('timeout', 30),
    }
    
    result = executor.test_connection(target, config)
    
    if result['success']:
        return jsonify(success_response(result))
    else:
        return jsonify(error_response('CONNECTION_FAILED', result.get('message', 'Connection failed'))), 400


@winrm_bp.route('/execute/cmd', methods=['POST'])

def execute_cmd():
    """
    Execute a CMD command on a Windows target.
    
    Request body:
        target: IP address or hostname
        command: CMD command to execute
        username, password, domain, transport, port: Auth config
    """
    data = request.get_json() or {}
    
    target = data.get('target')
    command = data.get('command')
    
    if not target:
        return jsonify(error_response('MISSING_TARGET', 'Target is required')), 400
    if not command:
        return jsonify(error_response('MISSING_COMMAND', 'Command is required')), 400
    
    config = {
        'username': data.get('username', ''),
        'password': data.get('password', ''),
        'domain': data.get('domain', ''),
        'transport': data.get('transport', 'ntlm'),
        'port': data.get('port', 5985),
        'timeout': data.get('timeout', 30),
    }
    
    result = executor.execute(target, command, config)
    return jsonify(success_response(result))


@winrm_bp.route('/execute/powershell', methods=['POST'])

def execute_powershell():
    """
    Execute a PowerShell script on a Windows target.
    
    Request body:
        target: IP address or hostname
        script: PowerShell script to execute
        username, password, domain, transport, port: Auth config
    """
    data = request.get_json() or {}
    
    target = data.get('target')
    script = data.get('script')
    
    if not target:
        return jsonify(error_response('MISSING_TARGET', 'Target is required')), 400
    if not script:
        return jsonify(error_response('MISSING_SCRIPT', 'Script is required')), 400
    
    config = {
        'username': data.get('username', ''),
        'password': data.get('password', ''),
        'domain': data.get('domain', ''),
        'transport': data.get('transport', 'ntlm'),
        'port': data.get('port', 5985),
        'timeout': data.get('timeout', 30),
    }
    
    result = executor.execute_powershell(target, script, config)
    return jsonify(success_response(result))


@winrm_bp.route('/system-info', methods=['POST'])

def get_system_info():
    """Get system information from a Windows target."""
    data = request.get_json() or {}
    
    target = data.get('target')
    if not target:
        return jsonify(error_response('MISSING_TARGET', 'Target is required')), 400
    
    config = {
        'username': data.get('username', ''),
        'password': data.get('password', ''),
        'domain': data.get('domain', ''),
        'transport': data.get('transport', 'ntlm'),
        'port': data.get('port', 5985),
    }
    
    result = executor.get_system_info(target, config)
    return jsonify(success_response(result))


@winrm_bp.route('/services', methods=['POST'])

def get_services():
    """Get Windows services from a target."""
    data = request.get_json() or {}
    
    target = data.get('target')
    if not target:
        return jsonify(error_response('MISSING_TARGET', 'Target is required')), 400
    
    config = {
        'username': data.get('username', ''),
        'password': data.get('password', ''),
        'domain': data.get('domain', ''),
        'transport': data.get('transport', 'ntlm'),
        'port': data.get('port', 5985),
    }
    
    result = executor.get_services(
        target,
        service_name=data.get('service_name'),
        status=data.get('status'),
        config=config
    )
    return jsonify(success_response(result))


@winrm_bp.route('/services/manage', methods=['POST'])

def manage_service():
    """Start, stop, or restart a Windows service."""
    data = request.get_json() or {}
    
    target = data.get('target')
    service_name = data.get('service_name')
    action = data.get('action')
    
    if not target:
        return jsonify(error_response('MISSING_TARGET', 'Target is required')), 400
    if not service_name:
        return jsonify(error_response('MISSING_SERVICE', 'Service name is required')), 400
    if not action:
        return jsonify(error_response('MISSING_ACTION', 'Action is required')), 400
    
    config = {
        'username': data.get('username', ''),
        'password': data.get('password', ''),
        'domain': data.get('domain', ''),
        'transport': data.get('transport', 'ntlm'),
        'port': data.get('port', 5985),
    }
    
    result = executor.manage_service(target, service_name, action, config)
    return jsonify(success_response(result))


@winrm_bp.route('/processes', methods=['POST'])

def get_processes():
    """Get running processes from a Windows target."""
    data = request.get_json() or {}
    
    target = data.get('target')
    if not target:
        return jsonify(error_response('MISSING_TARGET', 'Target is required')), 400
    
    config = {
        'username': data.get('username', ''),
        'password': data.get('password', ''),
        'domain': data.get('domain', ''),
        'transport': data.get('transport', 'ntlm'),
        'port': data.get('port', 5985),
    }
    
    result = executor.get_processes(
        target,
        process_name=data.get('process_name'),
        config=config
    )
    return jsonify(success_response(result))


@winrm_bp.route('/event-log', methods=['POST'])

def get_event_log():
    """Get Windows Event Log entries."""
    data = request.get_json() or {}
    
    target = data.get('target')
    if not target:
        return jsonify(error_response('MISSING_TARGET', 'Target is required')), 400
    
    config = {
        'username': data.get('username', ''),
        'password': data.get('password', ''),
        'domain': data.get('domain', ''),
        'transport': data.get('transport', 'ntlm'),
        'port': data.get('port', 5985),
    }
    
    result = executor.get_event_log(
        target,
        log_name=data.get('log_name', 'System'),
        entry_type=data.get('entry_type'),
        newest=data.get('newest', 50),
        config=config
    )
    return jsonify(success_response(result))


@winrm_bp.route('/disk-space', methods=['POST'])

def get_disk_space():
    """Get disk space information from a Windows target."""
    data = request.get_json() or {}
    
    target = data.get('target')
    if not target:
        return jsonify(error_response('MISSING_TARGET', 'Target is required')), 400
    
    config = {
        'username': data.get('username', ''),
        'password': data.get('password', ''),
        'domain': data.get('domain', ''),
        'transport': data.get('transport', 'ntlm'),
        'port': data.get('port', 5985),
    }
    
    result = executor.get_disk_space(target, config)
    return jsonify(success_response(result))


@winrm_bp.route('/network-config', methods=['POST'])

def get_network_config():
    """Get network configuration from a Windows target."""
    data = request.get_json() or {}
    
    target = data.get('target')
    if not target:
        return jsonify(error_response('MISSING_TARGET', 'Target is required')), 400
    
    config = {
        'username': data.get('username', ''),
        'password': data.get('password', ''),
        'domain': data.get('domain', ''),
        'transport': data.get('transport', 'ntlm'),
        'port': data.get('port', 5985),
    }
    
    result = executor.get_network_config(target, config)
    return jsonify(success_response(result))


@winrm_bp.route('/reboot', methods=['POST'])

def reboot_system():
    """Reboot a Windows system."""
    data = request.get_json() or {}
    
    target = data.get('target')
    if not target:
        return jsonify(error_response('MISSING_TARGET', 'Target is required')), 400
    
    # Require confirmation
    if not data.get('confirm'):
        return jsonify(error_response('CONFIRMATION_REQUIRED', 'Confirmation required')), 400
    
    config = {
        'username': data.get('username', ''),
        'password': data.get('password', ''),
        'domain': data.get('domain', ''),
        'transport': data.get('transport', 'ntlm'),
        'port': data.get('port', 5985),
    }
    
    result = executor.reboot_system(
        target,
        force=data.get('force', False),
        delay_seconds=data.get('delay_seconds', 0),
        config=config
    )
    return jsonify(success_response(result))


@winrm_bp.route('/shutdown', methods=['POST'])

def shutdown_system():
    """Shutdown a Windows system."""
    data = request.get_json() or {}
    
    target = data.get('target')
    if not target:
        return jsonify(error_response('MISSING_TARGET', 'Target is required')), 400
    
    # Require confirmation
    if not data.get('confirm'):
        return jsonify(error_response('CONFIRMATION_REQUIRED', 'Confirmation required')), 400
    
    config = {
        'username': data.get('username', ''),
        'password': data.get('password', ''),
        'domain': data.get('domain', ''),
        'transport': data.get('transport', 'ntlm'),
        'port': data.get('port', 5985),
    }
    
    result = executor.shutdown_system(
        target,
        force=data.get('force', False),
        delay_seconds=data.get('delay_seconds', 0),
        config=config
    )
    return jsonify(success_response(result))
