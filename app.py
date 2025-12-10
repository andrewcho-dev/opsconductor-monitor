#!/usr/bin/env python3
"""Main Flask application - clean and minimal"""

import json
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from celery.result import AsyncResult

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
from notification_service import send_notification
from generic_job_scheduler import run_job_builder_job
from celery_app import celery_app

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


@app.route('/api/scheduler/jobs/<name>/executions/clear', methods=['POST'])
def api_scheduler_job_executions_clear(name):
    """Clear execution history for a scheduler job.

    Optional JSON body:
      - status: if provided, only executions with this status are cleared.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        status = data.get('status')
        if status:
            status = str(status).strip()
        db.clear_scheduler_job_executions(job_name=name, status=status)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scheduler/queues', methods=['GET'])
def api_scheduler_queues():
    """Return basic Celery queue/worker status (active/reserved/scheduled)."""
    try:
        insp = celery_app.control.inspect()

        if not insp:
            # No workers or broker not reachable; return empty stats instead of 500
            return jsonify({
                'workers': [],
                'active_total': 0,
                'reserved_total': 0,
                'scheduled_total': 0,
                'active_by_worker': {},
                'reserved_by_worker': {},
                'scheduled_by_worker': {},
            })

        try:
            active = insp.active() or {}
            reserved = insp.reserved() or {}
            scheduled = insp.scheduled() or {}
            stats = insp.stats() or {}
        except Exception:
            # If Celery inspect calls fail (e.g. broker down), return empty stats
            return jsonify({
                'workers': [],
                'active_total': 0,
                'reserved_total': 0,
                'scheduled_total': 0,
                'active_by_worker': {},
                'reserved_by_worker': {},
                'scheduled_by_worker': {},
            })

        def summarize(mapping):
            total = 0
            by_worker = {}
            for worker, tasks in (mapping or {}).items():
                count = len(tasks or [])
                total += count
                by_worker[worker] = count
            return total, by_worker

        active_total, active_by_worker = summarize(active)
        reserved_total, reserved_by_worker = summarize(reserved)
        scheduled_total, scheduled_by_worker = summarize(scheduled)

        workers = sorted(set(list(active_by_worker.keys()) + list(reserved_by_worker.keys()) + list(scheduled_by_worker.keys()) + list((stats or {}).keys())))

        # Build richer per-worker details including approximate concurrency where available.
        worker_details = {}
        for w in workers:
            s = (stats or {}).get(w) or {}
            pool = s.get('pool') or {}
            # Celery stats usually expose either max-concurrency or a processes list.
            concurrency = pool.get('max-concurrency')
            if concurrency is None:
                procs = pool.get('processes') or []
                try:
                    concurrency = len(procs)
                except Exception:
                    concurrency = None
            worker_details[w] = {
                'concurrency': concurrency,
                'active': active_by_worker.get(w, 0),
                'reserved': reserved_by_worker.get(w, 0),
                'scheduled': scheduled_by_worker.get(w, 0),
            }

        return jsonify({
            'workers': workers,
            'active_total': active_total,
            'reserved_total': reserved_total,
            'scheduled_total': scheduled_total,
            'active_by_worker': active_by_worker,
            'reserved_by_worker': reserved_by_worker,
            'scheduled_by_worker': scheduled_by_worker,
            'worker_details': worker_details,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scheduler/jobs/<name>/executions', methods=['GET'])
def api_scheduler_job_executions(name):
    """Return recent execution history for a given scheduler job name."""
    try:
        try:
            limit = int(request.args.get('limit', 100))
        except Exception:
            limit = 100

        rows = db.get_scheduler_job_executions(job_name=name, limit=limit)
        executions = []
        for row in rows:
            executions.append({
                'id': row['id'],
                'job_name': row['job_name'],
                'task_name': row['task_name'],
                'task_id': row['task_id'],
                'status': row['status'],
                'started_at': row['started_at'].isoformat() if row['started_at'] else None,
                'finished_at': row['finished_at'].isoformat() if row['finished_at'] else None,
                'error_message': row['error_message'],
                'result': row.get('result'),
            })

        return jsonify({'executions': executions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/jobs/run', methods=['POST'])
def api_jobs_run():
    """Enqueue a Job Builder style job definition as a Celery task.

    Expects JSON payload containing at minimum:
      - job_id: string
      - name: string
      - actions: list of Job Builder actions

    The job is executed asynchronously by the `opsconductor.jobbuilder.run`
    Celery task. This endpoint returns a task_id that the frontend can use
    with /api/jobs/status/<task_id> to query progress and results.
    """
    try:
        job_def = request.get_json(force=True, silent=True) or {}

        actions = job_def.get('actions') or []
        if not isinstance(actions, list) or not actions:
            return jsonify({'error': 'job definition must include a non-empty actions list'}), 400

        async_result = celery_app.send_task('opsconductor.jobbuilder.run', args=[job_def])

        return jsonify({
            'status': 'queued',
            'task_id': async_result.id,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/jobs/status/<task_id>', methods=['GET'])
def api_jobs_status(task_id):
    """Return Celery task state and result for a previously enqueued job."""
    try:
        result = AsyncResult(task_id, app=celery_app)

        response = {
            'task_id': task_id,
            'state': result.state,
            'ready': result.ready(),
        }

        if result.ready():
            if result.successful():
                response['result'] = result.result
            else:
                # When failed, result.result is usually an exception instance
                response['error'] = str(result.result)

        return jsonify(response)
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


@app.route('/api/network-ranges', methods=['GET'])
def api_network_ranges():
    """Return unique network ranges for use in the Job Builder."""
    try:
        devices = db.get_all_devices()
        ranges_set = set()
        for device in devices:
            network_range = device.get('network_range')
            if network_range and network_range.strip():
                ranges_set.add(network_range.strip())

        ranges = sorted(ranges_set)
        return jsonify({'ranges': ranges})
    except Exception as e:
        return jsonify({'error': str(e), 'ranges': []}), 500


@app.route('/api/custom-groups', methods=['GET'])
def api_custom_groups():
    """Return all device groups as custom target groups."""
    try:
        rows = db.get_all_device_groups()
        groups = []
        for row in rows:
            # row: (id, group_name, description, created_at, updated_at, device_count)
            group = {
                'id': row[0],
                'name': row[1],
                'description': row[2] or '',
                'device_count': row[5] if len(row) > 5 else 0,
            }
            groups.append(group)

        return jsonify({'groups': groups})
    except Exception as e:
        return jsonify({'error': str(e), 'groups': []}), 500


@app.route('/api/network-groups', methods=['GET'])
def api_network_groups():
    """Return network groups (network_range + device_count)."""
    try:
        devices = db.get_all_devices()
        network_groups = {}
        for device in devices:
            network_range = device.get('network_range')
            if network_range and network_range.strip():
                key = network_range.strip()
                if key not in network_groups:
                    network_groups[key] = {
                        'network_range': key,
                        'device_count': 0,
                    }
                network_groups[key]['device_count'] += 1

        groups = sorted(network_groups.values(), key=lambda x: x['network_range'])
        return jsonify({'groups': groups})
    except Exception as e:
        return jsonify({'error': str(e), 'groups': []}), 500


@app.route('/api/notify/test', methods=['POST'])
def api_notify_test():
    """Send a test notification using Apprise.

    Expects JSON payload with:
      - targets: list of Apprise URLs (required)
      - title: optional title string
      - body: optional body string
      - tag: optional tag/context string
    """

    try:
        data = request.get_json(force=True, silent=True) or {}
        targets = data.get('targets') or []
        title = data.get('title') or 'OpsConductor Test Notification'
        body = data.get('body') or 'This is a test notification from OpsConductor.'
        tag = data.get('tag') or 'test'

        if not isinstance(targets, list) or not targets:
            return jsonify({'error': 'targets must be a non-empty list of Apprise URLs'}), 400

        ok = send_notification(targets=targets, title=title, body=body, tag=tag)

        if not ok:
            return jsonify({'error': 'Notification send failed or no valid targets'}), 500

        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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


# Generic Celery-based scheduler management APIs

def _serialize_scheduler_job(row):
    """Convert a scheduler_jobs row to a JSON-serializable dict."""
    return {
        'name': row['name'],
        'task_name': row['task_name'],
        'config': row.get('config') or {},
        'enabled': row.get('enabled', False),
        'schedule_type': row.get('schedule_type') or 'interval',
        'interval_seconds': row.get('interval_seconds'),
        'cron_expression': row.get('cron_expression'),
        'start_at': row['start_at'].isoformat() if row.get('start_at') else None,
        'end_at': row['end_at'].isoformat() if row.get('end_at') else None,
        'max_runs': row.get('max_runs'),
        'run_count': row.get('run_count'),
        'last_run_at': row['last_run_at'].isoformat() if row.get('last_run_at') else None,
        'next_run_at': row['next_run_at'].isoformat() if row.get('next_run_at') else None,
        'created_at': row['created_at'].isoformat() if row.get('created_at') else None,
        'updated_at': row['updated_at'].isoformat() if row.get('updated_at') else None,
    }


@app.route('/api/scheduler/jobs', methods=['GET'])
def api_scheduler_jobs_list():
    """List generic scheduler jobs for the Celery-based scheduler.

    Optional query param:
      - enabled=true/false to filter by enabled flag.
    """
    try:
        enabled_param = request.args.get('enabled')
        enabled = None
        if enabled_param is not None:
            enabled_param = enabled_param.strip().lower()
            enabled = enabled_param in ('1', 'true', 'yes', 'on')

        rows = db.get_scheduler_jobs(enabled=enabled)
        jobs = [_serialize_scheduler_job(r) for r in rows]
        return jsonify({'jobs': jobs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scheduler/jobs', methods=['POST'])
def api_scheduler_jobs_upsert():
    """Create or update a scheduler job definition.

    Expected JSON body:
      - name: unique job name (required)
      - task_name: Celery task name string (required)
      - schedule_type: "interval" or "cron" (optional, default "interval")
      - interval_seconds: number of seconds between runs (required for interval)
      - cron_expression: cron string (required for cron)
      - start_at: ISO timestamp string for first allowed run (optional)
      - end_at: ISO timestamp string for last allowed run (optional)
      - max_runs: integer max number of runs (optional)
      - enabled: bool (optional, default True)
      - next_run_at: ISO timestamp string (optional; if omitted, will be NULL
        and treated as due on next scheduler tick)
    """
    try:
        data = request.get_json(force=True, silent=True) or {}

        name = (data.get('name') or '').strip()
        task_name = (data.get('task_name') or '').strip()
        if not name or not task_name:
            return jsonify({'error': 'name and task_name are required'}), 400

        schedule_type = (data.get('schedule_type') or 'interval').strip().lower()
        if schedule_type not in ('interval', 'cron'):
            return jsonify({'error': 'schedule_type must be "interval" or "cron"'}), 400

        interval_seconds = None
        cron_expression = None

        if schedule_type == 'interval':
            try:
                interval_seconds = int(data.get('interval_seconds'))
            except Exception:
                return jsonify({'error': 'interval_seconds must be an integer for interval schedules'}), 400
            if interval_seconds <= 0:
                return jsonify({'error': 'interval_seconds must be > 0'}), 400
        else:
            cron_expression = (data.get('cron_expression') or '').strip()
            if not cron_expression:
                return jsonify({'error': 'cron_expression is required for cron schedules'}), 400

        enabled = bool(data.get('enabled', True))
        config = data.get('config') or {}

        def parse_dt(field):
            value = data.get(field)
            if not value:
                return None
            try:
                return datetime.fromisoformat(value)
            except Exception:
                raise ValueError(f"{field} must be ISO 8601 timestamp")

        try:
            start_at = parse_dt('start_at')
            end_at = parse_dt('end_at')
            next_run_at = parse_dt('next_run_at')
        except ValueError as ve:
            return jsonify({'error': str(ve)}), 400

        max_runs = data.get('max_runs')
        if max_runs is not None:
            try:
                max_runs = int(max_runs)
            except Exception:
                return jsonify({'error': 'max_runs must be an integer if provided'}), 400

        row = db.upsert_scheduler_job(
            name=name,
            task_name=task_name,
            config=config,
            interval_seconds=interval_seconds,
            enabled=enabled,
            next_run_at=next_run_at,
            schedule_type=schedule_type,
            cron_expression=cron_expression,
            start_at=start_at,
            end_at=end_at,
            max_runs=max_runs,
        )

        if not row:
            return jsonify({'error': 'Failed to save scheduler job'}), 500

        return jsonify({'job': _serialize_scheduler_job(row)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scheduler/jobs/<name>/run-once', methods=['POST'])
def api_scheduler_jobs_run_once(name):
    """Enqueue a one-off run of the named scheduler job's Celery task."""
    try:
        job = db.get_scheduler_job_by_name(name)
        if not job:
            return jsonify({'error': f'No scheduler job found with name {name}'}), 404

        cfg = job.get('config') or {}
        task_name = job['task_name']
        now = datetime.utcnow()

        async_result = celery_app.send_task(task_name, args=[cfg])

        # Record this execution as queued so later updates from the task
        # (running/success/failed) have a row to update.
        db.create_scheduler_job_execution(
            job_name=name,
            task_name=task_name,
            task_id=async_result.id,
            status='queued',
            started_at=now,
            error_message=None,
            result={'config': cfg},
        )

        return jsonify({
            'status': 'queued',
            'job_name': name,
            'task_name': task_name,
            'task_id': async_result.id,
        })
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
