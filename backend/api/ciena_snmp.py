"""
Ciena SNMP API Blueprint.

Routes for SNMP polling of Ciena switches for real-time monitoring.
"""

from flask import Blueprint, request, jsonify
from ..utils.responses import success_response, error_response
from ..utils.errors import AppError, ValidationError
from ..services.ciena_snmp_service import (
    CienaSNMPService, CienaSNMPError,
    poll_switch, poll_multiple_switches
)

snmp_bp = Blueprint('snmp', __name__, url_prefix='/api/snmp')


@snmp_bp.route('/test', methods=['POST'])
def test_connection():
    """
    Test SNMP connectivity to a Ciena switch.
    
    Request body:
        {
            "host": "10.x.x.x",
            "community": "public"  // optional, defaults to "public"
        }
    """
    data = request.get_json() or {}
    host = data.get('host')
    community = data.get('community', 'public')
    
    if not host:
        return error_response('Host is required', code='VALIDATION_ERROR', status=400)
    
    try:
        service = CienaSNMPService(host, community)
        result = service.test_connection()
        
        if result['success']:
            return success_response(result, message=f"Successfully connected to {host}")
        else:
            return error_response(
                f"Failed to connect to {host}: {result.get('error', 'Unknown error')}",
                code='CONNECTION_ERROR',
                status=500
            )
    except Exception as e:
        return error_response(str(e), code='SNMP_ERROR', status=500)


@snmp_bp.route('/poll', methods=['POST'])
def poll_single():
    """
    Poll a single Ciena switch for all data.
    
    Request body:
        {
            "host": "10.x.x.x",
            "community": "public"  // optional
        }
    """
    data = request.get_json() or {}
    host = data.get('host')
    community = data.get('community', 'public')
    
    if not host:
        return error_response('Host is required', code='VALIDATION_ERROR', status=400)
    
    try:
        result = poll_switch(host, community)
        return success_response(result)
    except CienaSNMPError as e:
        return error_response(str(e), code='SNMP_ERROR', status=500)
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)


@snmp_bp.route('/poll/batch', methods=['POST'])
def poll_batch():
    """
    Poll multiple Ciena switches.
    
    Request body:
        {
            "hosts": ["10.x.x.x", "10.x.x.y"],
            "community": "public"  // optional
        }
    """
    data = request.get_json() or {}
    hosts = data.get('hosts', [])
    community = data.get('community', 'public')
    
    if not hosts:
        return error_response('Hosts list is required', code='VALIDATION_ERROR', status=400)
    
    try:
        results = poll_multiple_switches(hosts, community)
        return success_response({
            'count': len(results),
            'results': results,
        })
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)


@snmp_bp.route('/system/<host>', methods=['GET'])
def get_system_info(host):
    """Get system information from a switch."""
    community = request.args.get('community', 'public')
    
    try:
        service = CienaSNMPService(host, community)
        result = service.get_system_info()
        return success_response(result)
    except CienaSNMPError as e:
        return error_response(str(e), code='SNMP_ERROR', status=500)
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)


@snmp_bp.route('/rings/<host>', methods=['GET'])
def get_rings(host):
    """
    Get G.8032 ring status from a switch via SNMP.
    
    This provides real-time ring status directly from the switch,
    bypassing MCP.
    """
    community = request.args.get('community', 'public')
    
    try:
        service = CienaSNMPService(host, community)
        
        # Get global RAPS status
        raps_global = None
        try:
            raps_global = service.get_raps_global()
        except:
            pass
        
        # Get virtual rings
        rings = service.get_virtual_rings()
        
        return success_response({
            'host': host,
            'raps_global': raps_global,
            'rings': rings,
            'count': len(rings),
        })
    except CienaSNMPError as e:
        return error_response(str(e), code='SNMP_ERROR', status=500)
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)


@snmp_bp.route('/alarms/<host>', methods=['GET'])
def get_alarms(host):
    """
    Get active alarms from a switch via SNMP.
    
    This provides real-time alarm data directly from the switch,
    bypassing MCP FM service.
    """
    community = request.args.get('community', 'public')
    
    try:
        service = CienaSNMPService(host, community)
        alarms = service.get_active_alarms()
        
        # Group by severity
        by_severity = {}
        for alarm in alarms:
            sev = alarm.get('severity', 'unknown')
            by_severity[sev] = by_severity.get(sev, 0) + 1
        
        return success_response({
            'host': host,
            'alarms': alarms,
            'count': len(alarms),
            'by_severity': by_severity,
        })
    except CienaSNMPError as e:
        return error_response(str(e), code='SNMP_ERROR', status=500)
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)


@snmp_bp.route('/raps/global/<host>', methods=['GET'])
def get_raps_global(host):
    """Get global RAPS configuration from a switch."""
    community = request.args.get('community', 'public')
    
    try:
        service = CienaSNMPService(host, community)
        result = service.get_raps_global()
        return success_response(result)
    except CienaSNMPError as e:
        return error_response(str(e), code='SNMP_ERROR', status=500)
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)


@snmp_bp.route('/ports/<host>', methods=['GET'])
def get_ports(host):
    """Get port status from a switch via SNMP."""
    community = request.args.get('community', 'public')
    
    try:
        service = CienaSNMPService(host, community)
        ports = service.get_ports()
        
        # Count by state
        up_count = sum(1 for p in ports if p.get('oper_state') == 'up')
        down_count = sum(1 for p in ports if p.get('oper_state') == 'down')
        
        return success_response({
            'host': host,
            'ports': ports,
            'count': len(ports),
            'up': up_count,
            'down': down_count,
        })
    except CienaSNMPError as e:
        return error_response(str(e), code='SNMP_ERROR', status=500)
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)


@snmp_bp.route('/transceivers/<host>', methods=['GET'])
def get_transceivers(host):
    """
    Get SFP/transceiver DOM data from a switch via SNMP.
    
    Returns optical power levels, temperature, and other DOM metrics.
    """
    community = request.args.get('community', 'public')
    
    try:
        service = CienaSNMPService(host, community)
        xcvrs = service.get_transceivers()
        
        return success_response({
            'host': host,
            'transceivers': xcvrs,
            'count': len(xcvrs),
        })
    except CienaSNMPError as e:
        return error_response(str(e), code='SNMP_ERROR', status=500)
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)


@snmp_bp.route('/port-stats/<host>', methods=['GET'])
def get_port_stats(host):
    """Get port traffic statistics from a switch via SNMP."""
    community = request.args.get('community', 'public')
    
    try:
        service = CienaSNMPService(host, community)
        stats = service.get_port_stats()
        
        return success_response({
            'host': host,
            'port_stats': stats,
            'count': len(stats),
        })
    except CienaSNMPError as e:
        return error_response(str(e), code='SNMP_ERROR', status=500)
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)


@snmp_bp.route('/chassis/<host>', methods=['GET'])
def get_chassis_health(host):
    """Get chassis health (power, fans, temperature) from a switch via SNMP."""
    community = request.args.get('community', 'public')
    
    try:
        service = CienaSNMPService(host, community)
        health = service.get_chassis_health()
        
        return success_response(health)
    except CienaSNMPError as e:
        return error_response(str(e), code='SNMP_ERROR', status=500)
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)


@snmp_bp.route('/lag/<host>', methods=['GET'])
def get_lag_status(host):
    """Get LAG/Link Aggregation status from a switch via SNMP."""
    community = request.args.get('community', 'public')
    
    try:
        service = CienaSNMPService(host, community)
        lags = service.get_lag_status()
        
        return success_response({
            'host': host,
            'lags': lags,
            'count': len(lags),
        })
    except CienaSNMPError as e:
        return error_response(str(e), code='SNMP_ERROR', status=500)
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)


@snmp_bp.route('/mstp/<host>', methods=['GET'])
def get_mstp_status(host):
    """Get MSTP/Spanning Tree status from a switch via SNMP."""
    community = request.args.get('community', 'public')
    
    try:
        service = CienaSNMPService(host, community)
        mstp = service.get_mstp_status()
        
        return success_response(mstp)
    except CienaSNMPError as e:
        return error_response(str(e), code='SNMP_ERROR', status=500)
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)


@snmp_bp.route('/ntp/<host>', methods=['GET'])
def get_ntp_status(host):
    """Get NTP synchronization status from a switch via SNMP."""
    community = request.args.get('community', 'public')
    
    try:
        service = CienaSNMPService(host, community)
        ntp = service.get_ntp_status()
        
        return success_response(ntp)
    except CienaSNMPError as e:
        return error_response(str(e), code='SNMP_ERROR', status=500)
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)


@snmp_bp.route('/cfm/<host>', methods=['GET'])
def get_cfm_status(host):
    """Get CFM/Ethernet OAM status from a switch via SNMP."""
    community = request.args.get('community', 'public')
    
    try:
        service = CienaSNMPService(host, community)
        cfm = service.get_cfm_status()
        
        return success_response(cfm)
    except CienaSNMPError as e:
        return error_response(str(e), code='SNMP_ERROR', status=500)
    except Exception as e:
        return error_response(str(e), code='INTERNAL_ERROR', status=500)
