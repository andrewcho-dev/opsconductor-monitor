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
# Device Data Routes - NOW PROXIES TO NETBOX
# ============================================================================

@legacy_bp.route('/data', methods=['GET'])
def get_data():
    """
    Get all devices - main data endpoint.
    
    UPDATED: Now fetches from NetBox as the source of truth.
    Returns devices in a format compatible with legacy code.
    """
    try:
        from ..services.netbox_service import NetBoxService
        from ..api.netbox import get_netbox_settings
        
        settings = get_netbox_settings()
        netbox = NetBoxService(
            url=settings.get('url', ''),
            token=settings.get('token', ''),
            verify_ssl=settings.get('verify_ssl', 'true').lower() == 'true'
        )
        
        if not netbox.is_configured:
            # Fall back to empty list if NetBox not configured
            return jsonify([])
        
        # Fetch all devices from NetBox
        result = netbox.get_devices(limit=10000)
        netbox_devices = result.get('results', [])
        
        # Transform to legacy format for backwards compatibility
        devices = []
        for d in netbox_devices:
            primary_ip = d.get('primary_ip4') or d.get('primary_ip') or {}
            ip_address = primary_ip.get('address', '').split('/')[0] if primary_ip else None
            
            if not ip_address:
                continue  # Skip devices without IP
            
            devices.append({
                'ip_address': ip_address,
                'hostname': d.get('name', ''),
                'snmp_hostname': d.get('name', ''),
                'snmp_description': d.get('description', ''),
                'snmp_model': d.get('device_type', {}).get('model', '') if d.get('device_type') else '',
                'snmp_vendor_name': d.get('device_type', {}).get('manufacturer', {}).get('name', '') if d.get('device_type') else '',
                'snmp_serial': d.get('serial', ''),
                'ping_status': 'online' if d.get('status', {}).get('value') == 'active' else 'offline',
                'snmp_status': 'YES',  # Assume SNMP if in NetBox
                'network_range': d.get('site', {}).get('name', '') if d.get('site') else '',
                'site': d.get('site', {}).get('name', '') if d.get('site') else '',
                'role': d.get('role', {}).get('name', '') if d.get('role') else '',
                'device_type': d.get('device_type', {}).get('model', '') if d.get('device_type') else '',
                'manufacturer': d.get('device_type', {}).get('manufacturer', {}).get('name', '') if d.get('device_type') else '',
                'status': d.get('status', {}).get('value', 'unknown'),
                'netbox_id': d.get('id'),
                'netbox_url': d.get('url'),
                'source': 'netbox',
            })
        
        return jsonify(devices)
        
    except Exception as e:
        logger.error(f"Error fetching devices from NetBox: {e}")
        # Return empty list on error
        return jsonify([])


@legacy_bp.route('/delete_selected', methods=['POST'])
def delete_selected():
    """
    Delete selected devices.
    
    DEPRECATED: Devices are now managed in NetBox.
    This endpoint is kept for backwards compatibility but returns an error.
    """
    return jsonify({
        'error': 'Device deletion is now managed in NetBox. Please delete devices directly in NetBox.',
        'deprecated': True
    }), 400


@legacy_bp.route('/delete_device', methods=['POST'])
def delete_device():
    """
    Delete a single device.
    
    DEPRECATED: Devices are now managed in NetBox.
    """
    return jsonify({
        'error': 'Device deletion is now managed in NetBox. Please delete devices directly in NetBox.',
        'deprecated': True
    }), 400


@legacy_bp.route('/delete/<ip_address>', methods=['DELETE'])
def delete_device_by_path(ip_address):
    """
    Delete device by IP in path.
    
    DEPRECATED: Devices are now managed in NetBox.
    """
    return jsonify({
        'error': 'Device deletion is now managed in NetBox. Please delete devices directly in NetBox.',
        'deprecated': True
    }), 400


# ============================================================================
# Network Groups Routes - NOW SOURCES FROM NETBOX SITES
# ============================================================================

@legacy_bp.route('/network_groups', methods=['GET'])
def get_network_groups():
    """
    Get network groups.
    
    UPDATED: Now returns NetBox sites as network groups.
    """
    try:
        from ..services.netbox_service import NetBoxService
        from ..api.netbox import get_netbox_settings
        
        settings = get_netbox_settings()
        netbox = NetBoxService(
            url=settings.get('url', ''),
            token=settings.get('token', ''),
            verify_ssl=settings.get('verify_ssl', 'true').lower() == 'true'
        )
        
        if not netbox.is_configured:
            return jsonify([])
        
        # Get sites from NetBox
        sites_result = netbox.get_sites(limit=1000)
        sites = sites_result.get('results', [])
        
        # Get device counts per site
        devices_result = netbox.get_devices(limit=10000)
        devices = devices_result.get('results', [])
        
        # Count devices per site
        site_counts = {}
        for d in devices:
            site_name = d.get('site', {}).get('name', 'Unknown') if d.get('site') else 'Unknown'
            site_counts[site_name] = site_counts.get(site_name, 0) + 1
        
        # Build summary
        summary = []
        for site in sites:
            site_name = site.get('name', 'Unknown')
            summary.append({
                'network_range': site_name,
                'device_count': site_counts.get(site_name, 0),
                'online_count': site_counts.get(site_name, 0),  # Assume all active
                'snmp_count': site_counts.get(site_name, 0),
                'ssh_count': 0,
                'site_id': site.get('id'),
                'site_slug': site.get('slug'),
            })
        
        return jsonify(summary)
        
    except Exception as e:
        logger.error(f"Error fetching network groups from NetBox: {e}")
        return jsonify([])


@legacy_bp.route('/api/network-ranges', methods=['GET'])
def get_network_ranges():
    """
    Get network ranges.
    
    UPDATED: Now returns NetBox IP ranges.
    """
    try:
        from ..services.netbox_service import NetBoxService
        from ..api.netbox import get_netbox_settings
        
        settings = get_netbox_settings()
        netbox = NetBoxService(
            url=settings.get('url', ''),
            token=settings.get('token', ''),
            verify_ssl=settings.get('verify_ssl', 'true').lower() == 'true'
        )
        
        if not netbox.is_configured:
            return jsonify([])
        
        # Get IP ranges from NetBox
        ranges_result = netbox._request('GET', 'ipam/ip-ranges/', params={'limit': 1000})
        ip_ranges = ranges_result.get('results', [])
        
        # Format for frontend
        ranges = []
        for r in ip_ranges:
            ranges.append({
                'range': r.get('display', r.get('start_address', 'Unknown')),
                'device_count': r.get('size', 0),
                'id': r.get('id'),
            })
        
        return jsonify(ranges)
        
    except Exception as e:
        logger.error(f"Error fetching network ranges from NetBox: {e}")
        return jsonify([])


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
# Topology Routes - NOW SOURCES FROM NETBOX
# ============================================================================

@legacy_bp.route('/topology_data', methods=['POST'])
def get_topology_data():
    """
    Get topology data for visualization.
    
    UPDATED: Now sources devices from NetBox.
    """
    data = request.get_json() or {}
    group_type = data.get('group_type', 'network')
    group_id = data.get('group_id')
    
    db = get_db()
    
    # Get devices from NetBox
    try:
        from ..services.netbox_service import NetBoxService
        from ..api.netbox import get_netbox_settings
        
        settings = get_netbox_settings()
        netbox = NetBoxService(
            url=settings.get('url', ''),
            token=settings.get('token', ''),
            verify_ssl=settings.get('verify_ssl', 'true').lower() == 'true'
        )
        
        if not netbox.is_configured:
            return jsonify({'nodes': [], 'links': []})
        
        # Fetch devices from NetBox, optionally filtered by site
        params = {'limit': 10000}
        if group_type == 'network' and group_id:
            # group_id is site name for network groups
            params['site'] = group_id
        
        result = netbox.get_devices(**params)
        netbox_devices = result.get('results', [])
        
        # Transform to format expected by topology
        devices = []
        for d in netbox_devices:
            primary_ip = d.get('primary_ip4') or d.get('primary_ip') or {}
            ip_address = primary_ip.get('address', '').split('/')[0] if primary_ip else None
            
            if not ip_address:
                continue
            
            devices.append({
                'ip_address': ip_address,
                'hostname': d.get('name', ''),
                'ping_status': 'online' if d.get('status', {}).get('value') == 'active' else 'offline',
                'site': d.get('site', {}).get('name', '') if d.get('site') else '',
            })
    except Exception as e:
        logger.error(f"Error fetching devices from NetBox for topology: {e}")
        devices = []
    
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
    
    # Get LLDP neighbor data for links - parallel queries
    from ..repositories.scan_repo import ScanRepository
    from concurrent.futures import ThreadPoolExecutor
    import os
    
    scan_repo = ScanRepository(db)
    device_ips = {d.get('ip_address') for d in devices}
    
    def get_device_links(device):
        ip = device.get('ip_address')
        device_links = []
        scans = scan_repo.get_latest_scans_for_device(ip)
        
        for scan in scans:
            remote_ip = scan.get('lldp_remote_mgmt_addr')
            if remote_ip and remote_ip != ip and remote_ip in device_ips:
                device_links.append({
                    'source': ip,
                    'target': remote_ip,
                    'local_port': scan.get('interface_name'),
                    'remote_port': scan.get('lldp_remote_port'),
                })
        return device_links
    
    cpu_count = os.cpu_count() or 4
    max_workers = min(cpu_count * 5, len(devices), 100)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        all_links = list(executor.map(get_device_links, devices))
        for device_links in all_links:
            links.extend(device_links)
    
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
