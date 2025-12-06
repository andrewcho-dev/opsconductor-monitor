#!/usr/bin/env python3
"""Main Flask application - clean and minimal"""

import json
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from database import db
from scan_routes import (
    start_scan,
    scan_selected_devices,
    get_scan_progress,
    delete_selected_records,
    cancel_scan,
    snmp_scan_devices,
    ssh_scan_devices,
    get_ssh_cli_interfaces,
    get_combined_interfaces,
    get_network_groups,
)
from settings_routes import get_settings_route, save_settings_route, test_settings_route
from poller_routes import (
    get_poller_status,
    get_poller_configs,
    save_poller_config,
    start_discovery_poller,
    stop_discovery_poller,
    save_discovery_config,
    start_interface_poller,
    stop_interface_poller,
    save_interface_config,
    start_optical_poller,
    stop_optical_poller,
    save_optical_config,
    run_all_pollers,
    get_poller_logs,
    clear_poller_logs,
    get_poller_statistics,
    test_discovery_scan,
    test_interface_scan,
    test_optical_scan,
    initialize_poller_system,
)

app = Flask(__name__, static_folder='.')
CORS(app, origins=['http://localhost:3000', 'http://192.168.10.50:3000', 'http://localhost:5173', 'http://192.168.10.50:5173'])

# Static files
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# Main pages
@app.route('/')
def index():
    return send_from_directory('.', 'simple_table.html')

@app.route('/settings.html')
def settings_page():
    try:
        with open('settings.html', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "Settings page not found", 404

@app.route('/topology.html')
def topology_page():
    """Serve the topology visualization page"""
    return send_from_directory('.', 'topology.html')

@app.route('/device_detail.html')
def device_detail_page():
    try:
        with open('device_detail.html', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "Device detail page not found", 404

# Core data routes
@app.route('/data')
def get_data():
    """Get all scan results"""
    try:
        return jsonify(db.get_all_devices())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/progress')
def get_progress():
    return get_scan_progress()

# Scan routes
@app.route('/scan', methods=['POST'])
def scan():
    return start_scan()

@app.route('/scan_selected', methods=['POST'])
def scan_selected():
    return scan_selected_devices()

@app.route('/snmp_scan', methods=['POST'])
def snmp_scan():
    return snmp_scan_devices()

@app.route('/ssh_scan', methods=['POST'])
def ssh_scan():
    return ssh_scan_devices()

# Delete routes (consolidated)
@app.route('/delete_selected', methods=['POST'])
def delete_selected():
    return delete_selected_records()

@app.route('/delete_device', methods=['POST'])
def delete_device():
    """Delete single device by IP (POST body)"""
    try:
        data = request.get_json()
        ip_address = data.get('ip_address')
        if not ip_address:
            return jsonify({'error': 'No IP address provided'}), 400
        
        deleted = db.delete_device(ip_address)
        if deleted:
            return jsonify({'status': 'success', 'message': f'Device {ip_address} deleted'})
        return jsonify({'error': 'IP address not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete/<ip_address>', methods=['DELETE'])
def delete_scan_result(ip_address):
    """Delete single device by IP (URL param)"""
    try:
        deleted = db.delete_device(ip_address)
        if deleted:
            return jsonify({'status': 'success', 'message': f'Deleted {ip_address}'})
        return jsonify({'error': 'IP address not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Scan cancellation
@app.route('/cancel_scan', methods=['POST'])
def cancel():
    return cancel_scan()

# Settings routes
@app.route('/get_settings', methods=['GET'])
def get_settings():
    return get_settings_route()

@app.route('/save_settings', methods=['POST'])
def save_settings():
    return save_settings_route()

@app.route('/test_settings', methods=['POST'])
def test_settings():
    return test_settings_route()

@app.route('/get_ssh_cli_interfaces', methods=['POST'])
def get_ssh_cli_interfaces_route():
    return get_ssh_cli_interfaces()

@app.route('/get_combined_interfaces', methods=['POST'])
def get_combined_interfaces_route():
    return get_combined_interfaces()

@app.route('/network_groups', methods=['GET'])
def get_network_groups_route():
    return get_network_groups()

# Poller System Routes
@app.route('/poller/status', methods=['GET'])
def poller_status_route():
    return get_poller_status()

@app.route('/poller/config', methods=['GET'])
def poller_configs_route():
    return get_poller_configs()

@app.route('/poller/config', methods=['POST'])
def poller_save_config_route():
    return save_poller_config()

@app.route('/poller/discovery/start', methods=['POST'])
def poller_start_discovery_route():
    return start_discovery_poller()

@app.route('/poller/discovery/stop', methods=['POST'])
def poller_stop_discovery_route():
    return stop_discovery_poller()

@app.route('/poller/discovery/config', methods=['POST'])
def poller_save_discovery_config_route():
    return save_discovery_config()

@app.route('/poller/discovery/test', methods=['POST'])
def poller_test_discovery_route():
    return test_discovery_scan()

@app.route('/poller/interface/start', methods=['POST'])
def poller_start_interface_route():
    return start_interface_poller()

@app.route('/poller/interface/stop', methods=['POST'])
def poller_stop_interface_route():
    return stop_interface_poller()

@app.route('/poller/interface/config', methods=['POST'])
def poller_save_interface_config_route():
    return save_interface_config()

@app.route('/poller/interface/test', methods=['POST'])
def poller_test_interface_route():
    return test_interface_scan()

@app.route('/poller/optical/start', methods=['POST'])
def poller_start_optical_route():
    return start_optical_poller()

@app.route('/poller/optical/stop', methods=['POST'])
def poller_stop_optical_route():
    return stop_optical_poller()

@app.route('/poller/optical/config', methods=['POST'])
def poller_save_optical_config_route():
    return save_optical_config()

@app.route('/poller/optical/test', methods=['POST'])
def poller_test_optical_route():
    return test_optical_scan()

@app.route('/poller/run_all', methods=['POST'])
def poller_run_all_route():
    return run_all_pollers()

@app.route('/poller/logs', methods=['GET'])
def poller_logs_route():
    return get_poller_logs()

@app.route('/poller/logs/clear', methods=['POST'])
def poller_clear_logs_route():
    return clear_poller_logs()

@app.route('/poller/statistics', methods=['GET'])
def poller_statistics_route():
    return get_poller_statistics()

@app.route('/topology_data', methods=['POST'])
def topology_data():
    """Get topology data for selected devices"""
    try:
        data = request.get_json()
        ip_list = data.get('ip_list', [])
        if not ip_list:
            return jsonify({'nodes': [], 'edges': []})
        
        nodes = []
        edges = []
        node_ids = set()
        edge_dict = {}  # key: (ip1, ip2) -> edge info
        
        # Get all devices for hostname lookup
        all_devices = db.get_all_devices()
        ip_to_hostname = {d['ip_address']: d['snmp_hostname'] for d in all_devices if d['snmp_hostname']}
        
        for ip in ip_list:
            # Get LLDP data for this IP
            interfaces = db.get_ssh_cli_scans(ip)
            hostname = ip_to_hostname.get(ip, ip)
            
            if ip not in node_ids:
                nodes.append({'id': ip, 'label': hostname or ip})
                node_ids.add(ip)
            
            for iface in interfaces:
                neighbor_ip = None
                neighbor_hostname = iface.get('lldp_remote_system_name')
                neighbor_mgmt = iface.get('lldp_remote_mgmt_addr')
                local_port = iface.get('cli_port') or iface.get('interface_index')
                remote_port = iface.get('lldp_remote_port')
                speed = iface.get('speed')
                status = iface.get('status')
                
                # Try to match neighbor to an IP in our list
                if neighbor_mgmt and neighbor_mgmt in ip_list:
                    neighbor_ip = neighbor_mgmt
                elif neighbor_hostname:
                    # Check if hostname matches an IP's hostname
                    for nip, hname in ip_to_hostname.items():
                        if hname == neighbor_hostname and nip in ip_list:
                            neighbor_ip = nip
                            break
                
                if neighbor_ip and neighbor_ip != ip:
                    edge_key = tuple(sorted([ip, neighbor_ip]))
                    
                    if edge_key not in edge_dict:
                        edge_dict[edge_key] = {
                            'from': edge_key[0],
                            'to': edge_key[1],
                            'title': '',
                            'links': [],
                            'seen_ports': set()
                        }
                    
                    # Create a unique key for this port pair to avoid duplicates
                    port_pair = tuple(sorted([
                        f"{ip}:{local_port}",
                        f"{neighbor_ip}:{remote_port}"
                    ]))
                    
                    if port_pair not in edge_dict[edge_key]['seen_ports']:
                        edge_dict[edge_key]['seen_ports'].add(port_pair)
                        # Add link info
                        link_info = {
                            'from_ip': ip,
                            'from_host': hostname,
                            'from_port': local_port,
                            'to_ip': neighbor_ip,
                            'to_host': ip_to_hostname.get(neighbor_ip, neighbor_ip),
                            'to_port': remote_port,
                            'speed': speed,
                            'status': status
                        }
                        edge_dict[edge_key]['links'].append(link_info)
                    
                    if neighbor_ip not in node_ids:
                        nodes.append({'id': neighbor_ip, 'label': ip_to_hostname.get(neighbor_ip, neighbor_ip)})
                        node_ids.add(neighbor_ip)
        
        # Build edge titles from link info
        for edge_key, edge in edge_dict.items():
            title_lines = []
            for link in edge['links']:
                line = f"{link['from_host']} port {link['from_port']} ↔ {link['to_host']} port {link['to_port']}"
                if link['speed']:
                    line += f" ({link['speed']})"
                if link['status']:
                    line += f" [{link['status']}]"
                title_lines.append(line)
            edge['title'] = '\n'.join(title_lines)
            edge['label'] = f"{len(edge['links'])} link(s)" if len(edge['links']) > 1 else ''
            del edge['links']  # Don't send raw links to frontend
            del edge['seen_ports']  # Don't send tracking set to frontend
            edges.append(edge)
        
        return jsonify({'nodes': nodes, 'edges': edges})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/power_history', methods=['POST'])
def power_history():
    """Get optical power history for devices"""
    try:
        data = request.get_json()
        
        # Support both old format (ip_list) and new format (ip_addresses)
        ip_list = data.get('ip_list', data.get('ip_addresses', []))
        hours = data.get('hours', 24)
        interface_index = data.get('interface_index')  # New: specific interface filter
        
        if not ip_list:
            return jsonify({'error': 'No devices specified'})
        
        history = []
        for ip in ip_list:
            if interface_index is not None:
                # Get power history for specific interface
                power_data = db.get_optical_power_history(
                    ip, 
                    interface_index, 
                    hours=hours
                )
                
                # Get interface name for this specific interface
                interfaces = db.get_ssh_cli_scans(ip)
                target_interface = next((i for i in interfaces if i.get('interface_index') == interface_index), None)
                interface_name = target_interface.get('interface_name', f'Port {interface_index}') if target_interface else f'Port {interface_index}'
                
                for reading in power_data:
                    history.append({
                        'ip_address': ip,
                        'interface_index': interface_index,
                        'interface_name': interface_name,
                        'cli_port': target_interface.get('cli_port') if target_interface else None,
                        'measurement_timestamp': reading['measurement_timestamp'].isoformat(),
                        'tx_power': float(reading['tx_power']) if reading['tx_power'] else None,
                        'rx_power': float(reading['rx_power']) if reading['rx_power'] else None,
                        'temperature': float(reading['temperature']) if reading['temperature'] else None
                    })
            else:
                # Get optical interfaces for this IP (old behavior)
                interfaces = db.get_ssh_cli_scans(ip)
                optical_interfaces = [i for i in interfaces if i.get('is_optical')]
                
                for iface in optical_interfaces:
                    power_data = db.get_optical_power_history(
                        ip, 
                        iface['interface_index'], 
                        hours=hours
                    )
                    
                    for reading in power_data:
                        history.append({
                            'ip_address': ip,
                            'interface_index': iface['interface_index'],
                            'interface_name': iface['interface_name'],
                            'cli_port': iface['cli_port'],
                            'measurement_timestamp': reading['measurement_timestamp'].isoformat(),
                            'tx_power': float(reading['tx_power']) if reading['tx_power'] else None,
                            'rx_power': float(reading['rx_power']) if reading['rx_power'] else None,
                            'temperature': float(reading['temperature']) if reading['temperature'] else None
                        })
        
        # Sort by timestamp
        history.sort(key=lambda x: x['measurement_timestamp'])
        return jsonify({'history': history})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Simple test route
@app.route('/test')
def test():
    return "Server is working"


# Device Groups API Routes
@app.route('/device_groups', methods=['GET'])
def get_device_groups():
    """Get all device groups"""
    try:
        groups = db.get_all_device_groups()
        group_list = []
        
        for group in groups:
            group_list.append({
                'id': group[0],
                'group_name': group[1],
                'description': group[2],
                'created_at': group[3].strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': group[4].strftime('%Y-%m-%d %H:%M:%S'),
                'device_count': group[5]
            })
            
        return jsonify(group_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/device_groups/<int:group_id>', methods=['GET'])
def get_device_group(group_id):
    """Get a specific device group with its devices"""
    try:
        group_data = db.get_device_group(group_id)
        
        if not group_data:
            return jsonify({'error': 'Group not found'}), 404
            
        group_info = group_data['group_info']
        devices = group_data['devices']
        
        result = {
            'id': group_info[0],
            'group_name': group_info[1],
            'description': group_info[2],
            'created_at': group_info[3].strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': group_info[4].strftime('%Y-%m-%d %H:%M:%S'),
            'devices': [{'ip_address': device[0], 'added_at': device[1].strftime('%Y-%m-%d %H:%M:%S')} for device in devices]
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/device_groups', methods=['POST'])
def create_device_group():
    """Create a new device group"""
    try:
        data = request.get_json()
        
        if not data or 'group_name' not in data:
            return jsonify({'error': 'Group name is required'}), 400
            
        group_name = data['group_name'].strip()
        description = data.get('description', '').strip()
        
        if not group_name:
            return jsonify({'error': 'Group name cannot be empty'}), 400
            
        result = db.create_device_group(group_name, description if description else None)
        
        if result:
            return jsonify({
                'success': True,
                'group': {
                    'id': result[0][0],
                    'group_name': result[0][1],
                    'description': result[0][2],
                    'created_at': result[0][3].strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_at': result[0][4].strftime('%Y-%m-%d %H:%M:%S')
                }
            })
        else:
            return jsonify({'error': 'Failed to create group'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/device_groups/<int:group_id>', methods=['PUT'])
def update_device_group(group_id):
    """Update a device group"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        group_name = data.get('group_name')
        description = data.get('description')
        
        if group_name is not None:
            group_name = group_name.strip()
            if not group_name:
                return jsonify({'error': 'Group name cannot be empty'}), 400
                
        success = db.update_device_group(group_id, group_name, description)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Group not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/device_groups/<int:group_id>', methods=['DELETE'])
def delete_device_group(group_id):
    """Delete a device group"""
    try:
        success = db.delete_device_group(group_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Group not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/device_groups/<int:group_id>/devices', methods=['POST'])
def add_device_to_group(group_id):
    """Add devices to a group"""
    try:
        data = request.get_json()
        
        if not data or 'ip_addresses' not in data:
            return jsonify({'error': 'IP addresses are required'}), 400
            
        ip_addresses = data['ip_addresses']
        if isinstance(ip_addresses, str):
            ip_addresses = [ip_addresses]
            
        success_count = 0
        for ip_address in ip_addresses:
            if db.add_device_to_group(group_id, ip_address.strip()):
                success_count += 1
                
        return jsonify({
            'success': True,
            'added_count': success_count,
            'total_requested': len(ip_addresses)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/device_groups/<int:group_id>/devices/<ip_address>', methods=['DELETE'])
def remove_device_from_group(group_id, ip_address):
    """Remove a device from a group"""
    try:
        success = db.remove_device_from_group(group_id, ip_address)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Device not found in group'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/device_groups/<int:group_id>/devices', methods=['GET'])
def get_group_devices(group_id):
    """Get all devices in a group"""
    try:
        devices = db.get_group_devices(group_id)
        
        device_list = []
        for device in devices:
            device_list.append({
                'ip_address': device[0],
                'added_at': device[1].strftime('%Y-%m-%d %H:%M:%S')
            })
            
        return jsonify(device_list)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Initialize poller system
    try:
        poller_success = initialize_poller_system()
        if poller_success:
            print("✅ Poller system initialized successfully")
        else:
            print("⚠️ Poller system initialization failed")
    except Exception as e:
        print(f"❌ Poller system initialization error: {e}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
