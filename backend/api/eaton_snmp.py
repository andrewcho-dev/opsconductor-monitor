"""
Eaton UPS SNMP API Blueprint
REST API endpoints for Eaton UPS SNMP monitoring
"""

from flask import Blueprint, request, jsonify
import logging

from backend.services.eaton_snmp_service import EatonSNMPService, EatonSNMPError

logger = logging.getLogger(__name__)

eaton_snmp_bp = Blueprint('eaton_snmp', __name__, url_prefix='/api/ups')


@eaton_snmp_bp.route('/test/<host>', methods=['GET'])
def test_connection(host):
    """Test SNMP connectivity to UPS"""
    community = request.args.get('community', 'public')
    version = int(request.args.get('version', 1))  # Default to SNMPv1
    try:
        service = EatonSNMPService(host, community, version=version)
        result = service.test_connection()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Test connection failed for {host}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@eaton_snmp_bp.route('/identity/<host>', methods=['GET'])
def get_identity(host):
    """Get UPS identity information"""
    community = request.args.get('community', 'public')
    version = int(request.args.get('version', 1))
    try:
        service = EatonSNMPService(host, community, version=version)
        data = service.get_identity()
        return jsonify({'success': True, 'data': data})
    except EatonSNMPError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Get identity failed for {host}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@eaton_snmp_bp.route('/battery/<host>', methods=['GET'])
def get_battery(host):
    """Get UPS battery status"""
    community = request.args.get('community', 'public')
    version = int(request.args.get('version', 1))
    try:
        service = EatonSNMPService(host, community, version=version)
        data = service.get_battery_status()
        return jsonify({'success': True, 'data': data})
    except EatonSNMPError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Get battery failed for {host}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@eaton_snmp_bp.route('/input/<host>', methods=['GET'])
def get_input(host):
    """Get UPS input power status"""
    community = request.args.get('community', 'public')
    version = int(request.args.get('version', 1))
    try:
        service = EatonSNMPService(host, community, version=version)
        data = service.get_input_status()
        return jsonify({'success': True, 'data': data})
    except EatonSNMPError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Get input failed for {host}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@eaton_snmp_bp.route('/output/<host>', methods=['GET'])
def get_output(host):
    """Get UPS output power status"""
    community = request.args.get('community', 'public')
    version = int(request.args.get('version', 1))
    try:
        service = EatonSNMPService(host, community, version=version)
        data = service.get_output_status()
        return jsonify({'success': True, 'data': data})
    except EatonSNMPError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Get output failed for {host}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@eaton_snmp_bp.route('/environment/<host>', methods=['GET'])
def get_environment(host):
    """Get UPS environmental data"""
    community = request.args.get('community', 'public')
    version = int(request.args.get('version', 1))
    try:
        service = EatonSNMPService(host, community, version=version)
        data = service.get_environment()
        return jsonify({'success': True, 'data': data})
    except EatonSNMPError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Get environment failed for {host}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@eaton_snmp_bp.route('/alarms/<host>', methods=['GET'])
def get_alarms(host):
    """Get UPS active alarms"""
    community = request.args.get('community', 'public')
    version = int(request.args.get('version', 1))
    try:
        service = EatonSNMPService(host, community, version=version)
        data = service.get_alarms()
        return jsonify({'success': True, 'data': data})
    except EatonSNMPError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Get alarms failed for {host}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@eaton_snmp_bp.route('/config/<host>', methods=['GET'])
def get_config(host):
    """Get UPS configuration"""
    community = request.args.get('community', 'public')
    version = int(request.args.get('version', 1))
    try:
        service = EatonSNMPService(host, community, version=version)
        data = service.get_config()
        return jsonify({'success': True, 'data': data})
    except EatonSNMPError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Get config failed for {host}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@eaton_snmp_bp.route('/poll/<host>', methods=['GET'])
def poll_all(host):
    """Poll all UPS data"""
    community = request.args.get('community', 'public')
    version = int(request.args.get('version', 1))
    try:
        service = EatonSNMPService(host, community, version=version)
        data = service.poll_all()
        return jsonify({'success': True, 'data': data})
    except EatonSNMPError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Poll all failed for {host}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@eaton_snmp_bp.route('/poll', methods=['POST'])
def poll_ups():
    """Poll UPS with POST body"""
    data = request.get_json() or {}
    host = data.get('host')
    community = data.get('community', 'public')
    version = int(data.get('version', 1))
    
    if not host:
        return jsonify({'success': False, 'error': 'Host is required'}), 400
    
    try:
        service = EatonSNMPService(host, community, version=version)
        result = service.poll_all()
        return jsonify({'success': True, 'data': result})
    except EatonSNMPError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Poll UPS failed for {host}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
