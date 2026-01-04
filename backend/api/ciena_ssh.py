"""
Ciena SSH API Blueprint.

Routes for SSH-based data collection from Ciena switches.
This is the primary data source for real-time monitoring.
"""

from flask import Blueprint, request, jsonify
from dataclasses import asdict
from ..utils.responses import success_response, error_response
from ..services.ciena_ssh_service import (
    CienaSSHService, CienaSSHError,
    get_ssh_service, poll_switch, poll_switches,
    SwitchData, OpticalDiagnostics, TrafficStats
)

ssh_bp = Blueprint('ssh', __name__, url_prefix='/api/ssh')


def _switch_data_to_dict(data: SwitchData) -> dict:
    """Convert SwitchData to JSON-serializable dict."""
    result = {
        'host': data.host,
        'collected_at': data.collected_at.isoformat() if data.collected_at else None,
        'collection_time_ms': data.collection_time_ms,
        'success': data.success,
        'error': data.error,
    }
    
    if data.system_info:
        result['system_info'] = asdict(data.system_info)
    
    if data.optical:
        result['optical'] = [asdict(o) for o in data.optical]
    
    if data.ports:
        result['ports'] = [asdict(p) for p in data.ports]
    
    if data.traffic:
        result['traffic'] = [asdict(t) for t in data.traffic]
    
    if data.alarms:
        result['alarms'] = [asdict(a) for a in data.alarms]
    
    if data.chassis:
        result['chassis'] = asdict(data.chassis)
    
    if data.rings:
        result['rings'] = [asdict(r) for r in data.rings]
    
    return result


@ssh_bp.route('/test', methods=['POST'])
def test_connection():
    """
    Test SSH connectivity to a Ciena switch.
    
    Request body:
        {
            "host": "10.x.x.x",
            "username": "su",  // optional
            "password": "wwp"  // optional
        }
    """
    data = request.get_json() or {}
    host = data.get('host')
    
    if not host:
        return error_response('Host is required', code='VALIDATION_ERROR', status=400)
    
    try:
        service = get_ssh_service()
        result = service.test_connection(host)
        
        if result['success']:
            return success_response(result, message=f"SSH connection to {host} successful")
        else:
            return error_response(
                f"Failed to connect to {host}: {result.get('error', 'Unknown error')}",
                code='CONNECTION_ERROR',
                status=500
            )
    except Exception as e:
        return error_response(str(e), code='SSH_ERROR', status=500)


@ssh_bp.route('/poll', methods=['POST'])
def poll_single():
    """
    Poll a single Ciena switch for all data via SSH.
    
    Request body:
        {
            "host": "10.x.x.x",
            "commands": ["port show", ...]  // optional, uses defaults if not provided
        }
    """
    data = request.get_json() or {}
    host = data.get('host')
    commands = data.get('commands')
    
    if not host:
        return error_response('Host is required', code='VALIDATION_ERROR', status=400)
    
    try:
        result = poll_switch(host, commands)
        return success_response(_switch_data_to_dict(result))
    except CienaSSHError as e:
        return error_response(str(e), code='SSH_ERROR', status=500)
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)


@ssh_bp.route('/poll/batch', methods=['POST'])
def poll_batch():
    """
    Poll multiple Ciena switches in parallel via SSH.
    
    Request body:
        {
            "hosts": ["10.x.x.x", "10.x.x.y"],
            "commands": ["port show", ...]  // optional
        }
    """
    data = request.get_json() or {}
    hosts = data.get('hosts', [])
    commands = data.get('commands')
    
    if not hosts:
        return error_response('Hosts list is required', code='VALIDATION_ERROR', status=400)
    
    try:
        results = poll_switches(hosts, commands)
        return success_response({
            'count': len(results),
            'successful': sum(1 for r in results if r.success),
            'failed': sum(1 for r in results if not r.success),
            'results': [_switch_data_to_dict(r) for r in results],
        })
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)


@ssh_bp.route('/optical/<host>', methods=['GET'])
def get_optical(host):
    """
    Get optical transceiver diagnostics from a switch via SSH.
    
    Query params:
        ports: Port range (default: 1-24)
    """
    ports = request.args.get('ports', '1-24')
    
    try:
        service = get_ssh_service()
        diagnostics = service.get_optical_diagnostics(host, ports)
        
        return success_response({
            'host': host,
            'diagnostics': [asdict(d) for d in diagnostics],
            'count': len(diagnostics),
        })
    except CienaSSHError as e:
        return error_response(str(e), code='SSH_ERROR', status=500)
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)


@ssh_bp.route('/traffic/<host>', methods=['GET'])
def get_traffic(host):
    """
    Get real-time traffic rates from a switch via SSH.
    
    Query params:
        ports: Port list (default: 1-24, comma-separated for PM command)
    """
    ports = request.args.get('ports', '1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24')
    
    try:
        service = get_ssh_service()
        stats = service.get_traffic_rates(host, ports)
        
        # Filter to only ports with traffic
        active_ports = [s for s in stats if s.tx_bytes_per_sec or s.rx_bytes_per_sec]
        
        return success_response({
            'host': host,
            'traffic': [asdict(s) for s in stats],
            'active_ports': [asdict(s) for s in active_ports],
            'total_ports': len(stats),
            'active_count': len(active_ports),
        })
    except CienaSSHError as e:
        return error_response(str(e), code='SSH_ERROR', status=500)
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)


@ssh_bp.route('/alarms/<host>', methods=['GET'])
def get_alarms(host):
    """
    Get active alarms from a switch via SSH.
    """
    try:
        service = get_ssh_service()
        alarms = service.get_alarms(host)
        
        # Group by severity
        by_severity = {}
        for alarm in alarms:
            sev = alarm.severity or 'unknown'
            by_severity[sev] = by_severity.get(sev, 0) + 1
        
        return success_response({
            'host': host,
            'alarms': [asdict(a) for a in alarms],
            'count': len(alarms),
            'by_severity': by_severity,
        })
    except CienaSSHError as e:
        return error_response(str(e), code='SSH_ERROR', status=500)
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)


@ssh_bp.route('/status', methods=['GET'])
def get_service_status():
    """
    Get SSH service status and configuration.
    """
    service = get_ssh_service()
    
    return success_response({
        'service': 'CienaSSHService',
        'status': 'active',
        'config': {
            'username': service.username,
            'timeout': service.timeout,
            'max_concurrent': service.max_concurrent,
            'command_delay': service.command_delay,
        },
        'default_commands': service.DEFAULT_COMMANDS,
    })
