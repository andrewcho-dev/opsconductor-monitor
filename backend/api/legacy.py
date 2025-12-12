"""
Legacy API Blueprint.

Routes that maintain backward compatibility with existing frontend.
These routes delegate to the new modular services.
"""

import os
import json
import threading
from datetime import datetime
from flask import Blueprint, request, jsonify
from ..utils.responses import success_response, error_response, list_response
from ..utils.errors import AppError, ValidationError


legacy_bp = Blueprint('legacy', __name__)


def get_db():
    """Get database manager instance."""
    from database import DatabaseManager
    return DatabaseManager()


def get_settings():
    """Load settings from file."""
    settings_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'settings.json')
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
                for key, value in default_settings.items():
                    if key not in settings:
                        settings[key] = value
                return settings
    except:
        pass
    return default_settings


@legacy_bp.errorhandler(AppError)
def handle_app_error(error):
    return jsonify(error_response(error.code, error.message, error.details)), error.status_code


# ============================================================================
# Device Data Routes
# ============================================================================

@legacy_bp.route('/data', methods=['GET'])
def get_data():
    """Get all devices - main data endpoint."""
    db = get_db()
    from ..repositories.device_repo import DeviceRepository
    
    repo = DeviceRepository(db)
    devices = repo.get_all_devices()
    return jsonify(devices)


@legacy_bp.route('/delete_selected', methods=['POST'])
def delete_selected():
    """Delete selected devices."""
    data = request.get_json() or {}
    ips = data.get('ips', [])
    
    if not ips:
        return jsonify({'error': 'No IPs provided'}), 400
    
    db = get_db()
    from ..repositories.device_repo import DeviceRepository
    repo = DeviceRepository(db)
    
    deleted = 0
    for ip in ips:
        if repo.delete_by_ip(ip):
            deleted += 1
    
    return jsonify({'deleted': deleted})


@legacy_bp.route('/delete_device', methods=['POST'])
def delete_device():
    """Delete a single device."""
    data = request.get_json() or {}
    ip = data.get('ip')
    
    if not ip:
        return jsonify({'error': 'No IP provided'}), 400
    
    db = get_db()
    from ..repositories.device_repo import DeviceRepository
    repo = DeviceRepository(db)
    
    if repo.delete_by_ip(ip):
        return jsonify({'success': True})
    return jsonify({'error': 'Device not found'}), 404


@legacy_bp.route('/delete/<ip_address>', methods=['DELETE'])
def delete_device_by_path(ip_address):
    """Delete device by IP in path."""
    db = get_db()
    from ..repositories.device_repo import DeviceRepository
    repo = DeviceRepository(db)
    
    if repo.delete_by_ip(ip_address):
        return jsonify({'success': True})
    return jsonify({'error': 'Device not found'}), 404


# ============================================================================
# Network Groups Routes
# ============================================================================

@legacy_bp.route('/network_groups', methods=['GET'])
def get_network_groups():
    """Get network groups (auto-generated from scan results)."""
    db = get_db()
    from ..repositories.device_repo import DeviceRepository
    repo = DeviceRepository(db)
    
    summary = repo.get_network_summary()
    return jsonify(summary)


@legacy_bp.route('/api/network-ranges', methods=['GET'])
def get_network_ranges():
    """Get network ranges."""
    db = get_db()
    from ..repositories.device_repo import DeviceRepository
    repo = DeviceRepository(db)
    
    summary = repo.get_network_summary()
    
    # Format for frontend
    ranges = []
    for item in summary:
        ranges.append({
            'range': item.get('network_range', 'Unknown'),
            'device_count': item.get('device_count', 0),
        })
    
    return jsonify(ranges)


@legacy_bp.route('/api/network-groups', methods=['GET'])
def get_network_groups_api():
    """Get network groups API."""
    return get_network_groups()


@legacy_bp.route('/api/custom-groups', methods=['GET'])
def get_custom_groups():
    """Get custom device groups."""
    db = get_db()
    from ..repositories.group_repo import GroupRepository
    repo = GroupRepository(db)
    
    groups = repo.get_all_groups()
    return jsonify(groups)


# ============================================================================
# Settings Routes (legacy paths)
# ============================================================================

@legacy_bp.route('/get_settings', methods=['GET'])
def get_settings_route():
    """Get settings."""
    settings = get_settings()
    return jsonify(settings)


@legacy_bp.route('/save_settings', methods=['POST'])
def save_settings_route():
    """Save settings."""
    settings_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'settings.json')
    data = request.get_json() or {}
    
    try:
        with open(settings_path, 'w') as f:
            json.dump(data, f, indent=2)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@legacy_bp.route('/test_settings', methods=['POST'])
def test_settings_route():
    """Test settings."""
    data = request.get_json() or {}
    return jsonify({'success': True, 'message': 'Settings test not implemented in legacy mode'})


# ============================================================================
# Interface/Scan Routes
# ============================================================================

@legacy_bp.route('/get_ssh_cli_interfaces', methods=['POST'])
def get_ssh_cli_interfaces():
    """Get SSH CLI interfaces for a device."""
    data = request.get_json() or {}
    ip = data.get('ip')
    
    if not ip:
        return jsonify({'error': 'No IP provided'}), 400
    
    db = get_db()
    from ..repositories.scan_repo import ScanRepository
    repo = ScanRepository(db)
    
    interfaces = repo.get_latest_scans_for_device(ip)
    return jsonify(interfaces)


@legacy_bp.route('/get_combined_interfaces', methods=['POST'])
def get_combined_interfaces():
    """Get combined interfaces for a device."""
    data = request.get_json() or {}
    ip = data.get('ip')
    
    if not ip:
        return jsonify({'error': 'No IP provided'}), 400
    
    db = get_db()
    from ..repositories.scan_repo import ScanRepository
    repo = ScanRepository(db)
    
    interfaces = repo.get_latest_scans_for_device(ip)
    return jsonify(interfaces)


@legacy_bp.route('/power_history', methods=['POST'])
def get_power_history():
    """Get optical power history."""
    data = request.get_json() or {}
    
    # Support multiple input formats: ip, ip_list, ip_addresses
    ip = data.get('ip')
    ip_list = data.get('ip_list') or data.get('ip_addresses') or []
    interface_index = data.get('interface_index')
    hours = data.get('hours', 24)
    
    # If ip_list provided, use first IP or aggregate
    if not ip and ip_list:
        if len(ip_list) == 1:
            ip = ip_list[0]
        else:
            # Multiple IPs - aggregate history from all
            db = get_db()
            from ..repositories.scan_repo import OpticalPowerRepository
            repo = OpticalPowerRepository(db)
            
            all_history = []
            for device_ip in ip_list:
                try:
                    history = repo.get_power_history(device_ip, interface_index, hours)
                    all_history.extend(history)
                except Exception:
                    pass
            return jsonify({'history': all_history})
    
    if not ip:
        return jsonify({'error': 'No IP provided'}), 400
    
    db = get_db()
    from ..repositories.scan_repo import OpticalPowerRepository
    repo = OpticalPowerRepository(db)
    
    history = repo.get_power_history(ip, interface_index, hours)
    return jsonify({'history': history})


# ============================================================================
# Topology Routes
# ============================================================================

@legacy_bp.route('/topology_data', methods=['POST'])
def get_topology_data():
    """Get topology data for visualization."""
    data = request.get_json() or {}
    group_type = data.get('group_type', 'network')
    group_id = data.get('group_id')
    
    db = get_db()
    
    # Get devices based on group
    if group_type == 'custom' and group_id:
        from ..repositories.group_repo import GroupRepository
        repo = GroupRepository(db)
        devices = repo.get_group_devices(int(group_id))
    else:
        from ..repositories.device_repo import DeviceRepository
        repo = DeviceRepository(db)
        if group_id:
            devices = repo.get_devices_by_network(group_id)
        else:
            devices = repo.get_all_devices()
    
    # Build topology nodes and links
    nodes = []
    links = []
    
    for device in devices:
        nodes.append({
            'id': device.get('ip_address'),
            'label': device.get('hostname') or device.get('ip_address'),
            'ip': device.get('ip_address'),
            'status': device.get('ping_status', 'unknown'),
        })
    
    # Get LLDP neighbor data for links
    from ..repositories.scan_repo import ScanRepository
    scan_repo = ScanRepository(db)
    
    for device in devices:
        ip = device.get('ip_address')
        scans = scan_repo.get_latest_scans_for_device(ip)
        
        for scan in scans:
            remote_ip = scan.get('lldp_remote_mgmt_addr')
            if remote_ip and remote_ip != ip:
                # Check if remote device is in our list
                if any(d.get('ip_address') == remote_ip for d in devices):
                    links.append({
                        'source': ip,
                        'target': remote_ip,
                        'local_port': scan.get('interface_name'),
                        'remote_port': scan.get('lldp_remote_port'),
                    })
    
    return jsonify({
        'nodes': nodes,
        'links': links,
    })


# ============================================================================
# Notification Routes
# ============================================================================

@legacy_bp.route('/api/notify/test', methods=['POST'])
def test_notification():
    """Test notification."""
    data = request.get_json() or {}
    
    try:
        from notification_service import send_notification
        
        result = send_notification(
            title='Test Notification',
            message=data.get('message', 'This is a test notification from OpsConductor'),
            level='info'
        )
        
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ============================================================================
# Scan Trigger Routes
# ============================================================================

@legacy_bp.route('/scan', methods=['POST'])
def trigger_scan():
    """Trigger a network scan."""
    try:
        from scan_routes import start_scan
        start_scan()
        return jsonify({'success': True, 'message': 'Scan started'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@legacy_bp.route('/scan_selected', methods=['POST'])
def scan_selected():
    """Scan selected IPs."""
    data = request.get_json() or {}
    ips = data.get('ips', [])
    
    if not ips:
        return jsonify({'error': 'No IPs provided'}), 400
    
    try:
        from scan_routes import scan_ips
        scan_ips(ips)
        return jsonify({'success': True, 'message': f'Scanning {len(ips)} IPs'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@legacy_bp.route('/snmp_scan', methods=['POST'])
def snmp_scan():
    """Trigger SNMP scan."""
    try:
        from scan_routes import start_snmp_scan
        start_snmp_scan()
        return jsonify({'success': True, 'message': 'SNMP scan started'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@legacy_bp.route('/ssh_scan', methods=['POST'])
def ssh_scan():
    """Trigger SSH scan."""
    data = request.get_json() or {}
    
    try:
        from scan_routes import start_ssh_scan
        start_ssh_scan(data.get('ips'))
        return jsonify({'success': True, 'message': 'SSH scan started'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
