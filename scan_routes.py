#!/usr/bin/env python3
"""Optimized scan routes - fast port detection with async support"""

from flask import jsonify, request
from database import db, DatabaseManager
from datetime import datetime
import subprocess
import ipaddress
import socket
import threading
import paramiko
import re
from config import get_settings
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global scan progress tracking with thread-safe access
_progress_lock = threading.Lock()
_scan_cancel_flag = threading.Event()  # For scan cancellation
scan_progress = {'scanned': 0, 'total': 0, 'online': 0, 'status': 'idle'}

def _increment_progress(key, value=1):
    """Thread-safe increment of scan_progress counters"""
    with _progress_lock:
        scan_progress[key] += value

def _set_progress(updates):
    """Thread-safe update of multiple scan_progress fields"""
    with _progress_lock:
        scan_progress.update(updates)

def check_port_fast(ip, port, timeout):
    """Ultra-fast port check using socket with minimal timeout"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False

def ping_fast(ip, timeout=1):
    """Fast ping check using system ping with configurable timeout"""
    try:
        # Convert timeout to integer (ping -W requires whole seconds)
        timeout_sec = max(1, int(float(timeout)))
        ping_cmd = ['ping', '-c', '1', '-W', str(timeout_sec), ip]
        result = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=timeout_sec + 0.5)
        return result.returncode == 0
    except Exception:
        return False

def check_snmp_agent(ip, settings):
    """Fast SNMP presence check using snmpget.

    Any successful response is treated as SNMP=YES. Uses the simple
    community/version settings from config.json and a very small timeout.
    """
    community = settings.get('snmp_community', 'public')
    version = settings.get('snmp_version', '2c')
    port = str(settings.get('snmp_port', '161'))
    timeout = float(settings.get('snmp_timeout', '1') or 1)
    success_status = settings.get('snmp_success_status', 'YES')
    fail_status = settings.get('snmp_fail_status', 'NO')

    # Simple sysDescr OID just to verify the agent responds
    cmd = [
        'snmpget',
        f'-v{version}',
        '-c', community,
        '-t', str(timeout),
        '-r', '0',             # no retries for speed
        f'{ip}:{port}',
        '1.3.6.1.2.1.1.1.0'    # sysDescr.0
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 0.5
        )
        # Look at combined output to distinguish timeout vs some response.
        out = (result.stdout or '') + (result.stderr or '')
        out_lower = out.lower()

        # Typical timeout text from net-snmp when there is no agent listening
        if 'timeout' in out_lower or 'no response' in out_lower:
            return fail_status

        # If we got any other output at all (even auth failure), the UDP
        # port is open and an SNMP agent is there.
        if out.strip():
            return success_status

        # Fallback: no useful output, treat as no SNMP
        return fail_status
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        # On timeout, missing snmpget, or any error, treat as no SNMP
        return fail_status

def scan_single_ip(ip_str, settings):
    """Scan single IP with all checks in parallel"""
    # Initialize all as failed
    ping_status = settings['offline_status']
    snmp_status = settings['snmp_fail_status']
    ssh_status = settings['ssh_fail_status']
    rdp_status = settings['rdp_fail_status']
    hostname = ''
    
    results = {}
    
    def check_ping():
        if ping_fast(ip_str):
            results['ping'] = settings['online_status']
        else:
            results['ping'] = settings['offline_status']
    
    def check_snmp():
        results['snmp'] = check_snmp_agent(ip_str, settings)
    
    def check_ssh():
        if check_port_fast(ip_str, int(settings['ssh_port']), float(settings['ssh_timeout'])):
            results['ssh'] = settings['ssh_success_status']
        else:
            results['ssh'] = settings['ssh_fail_status']
    
    def check_rdp():
        if check_port_fast(ip_str, int(settings['rdp_port']), float(settings['rdp_timeout'])):
            results['rdp'] = settings['rdp_success_status']
        else:
            results['rdp'] = settings['rdp_fail_status']
    
    def get_hostname():
        try:
            hostname = socket.gethostbyaddr(ip_str)[0]
            results['hostname'] = hostname
        except:
            results['hostname'] = ''
    
    # Run all checks in parallel threads
    threads = [
        threading.Thread(target=check_ping),
        threading.Thread(target=check_snmp),
        threading.Thread(target=check_ssh),
        threading.Thread(target=check_rdp),
        threading.Thread(target=get_hostname)
    ]
    
    for thread in threads:
        thread.start()
    
    for thread in threads:
        thread.join()
    
    # Get results
    ping_status = results.get('ping', settings['offline_status'])
    snmp_status = results.get('snmp', settings['snmp_fail_status'])
    ssh_status = results.get('ssh', settings['ssh_fail_status'])
    rdp_status = results.get('rdp', settings['rdp_fail_status'])
    hostname = results.get('hostname', '')
    
    return ping_status, snmp_status, ssh_status, rdp_status, hostname

def _run_scan_async(ip_list, network_range, settings):
    """Run scan in background thread"""
    try:
        # Clear cancel flag
        _scan_cancel_flag.clear()
        
        # Get batch size from settings (default 20, max 100)
        batch_size = min(100, max(1, int(settings.get('max_threads', 20))))
        
        for i in range(0, len(ip_list), batch_size):
            # Check for cancellation
            if _scan_cancel_flag.is_set():
                _set_progress({'status': 'cancelled'})
                return
            
            batch = ip_list[i:i + batch_size]
            batch_threads = []
            batch_results = {}
            batch_lock = threading.Lock()
            
            def scan_ip_in_batch(ip, settings_copy):
                ip_str = str(ip)
                try:
                    ping_status, snmp_status, ssh_status, rdp_status, hostname = scan_single_ip(ip_str, settings_copy)
                    with batch_lock:
                        batch_results[ip_str] = (ping_status, snmp_status, ssh_status, rdp_status, hostname)
                    _increment_progress('scanned')
                    if ping_status == settings_copy['online_status']:
                        _increment_progress('online')
                except Exception as e:
                    with batch_lock:
                        batch_results[ip_str] = (settings_copy['offline_status'], 'NO', 'NO', 'NO', '')
                    _increment_progress('scanned')
            
            # Start batch threads
            for ip in batch:
                thread = threading.Thread(target=scan_ip_in_batch, args=(ip, settings.copy()))
                thread.daemon = True
                thread.start()
                batch_threads.append(thread)
            
            # Wait for batch with timeout
            for thread in batch_threads:
                thread.join(timeout=15)
            
            # Store results in database
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                
                for ip_str, (ping_status, snmp_status, ssh_status, rdp_status, hostname) in batch_results.items():
                    scan_timestamp = datetime.now() if ping_status == settings['online_status'] else None
                    cursor.execute('''
                        INSERT INTO scan_results 
                            (ip_address, network_range, ping_status, scan_timestamp, snmp_status, ssh_status, rdp_status, snmp_hostname) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (ip_address) DO UPDATE SET
                            network_range = EXCLUDED.network_range,
                            ping_status = EXCLUDED.ping_status,
                            scan_timestamp = COALESCE(EXCLUDED.scan_timestamp, scan_results.scan_timestamp),
                            snmp_status = EXCLUDED.snmp_status,
                            ssh_status = EXCLUDED.ssh_status,
                            rdp_status = EXCLUDED.rdp_status,
                            snmp_hostname = COALESCE(NULLIF(EXCLUDED.snmp_hostname, ''), scan_results.snmp_hostname)
                    ''', (ip_str, network_range, ping_status, scan_timestamp, snmp_status, ssh_status, rdp_status, hostname))
                
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Database error: {e}")
        
        # Mark complete
        _set_progress({'status': 'complete'})
        
    except Exception as e:
        _set_progress({'status': 'error', 'error': str(e)})


def start_scan():
    """Start async capability scan - returns immediately, poll /progress for status"""
    try:
        # Check if scan already running
        with _progress_lock:
            if scan_progress['status'] == 'scanning':
                return jsonify({'error': 'Scan already in progress'}), 409
        
        data = request.get_json()
        network_range = data.get('network_range')
        
        if not network_range:
            return jsonify({'error': 'No network range provided'}), 400
        
        # Parse network range
        try:
            network = ipaddress.ip_network(network_range, strict=False)
        except ValueError:
            return jsonify({'error': 'Invalid network range format'}), 400
        
        settings = get_settings()
        ip_list = [str(ip) for ip in network.hosts()]
        
        # Initialize progress
        _set_progress({
            'scanned': 0,
            'total': len(ip_list),
            'online': 0,
            'status': 'scanning',
            'network_range': network_range
        })
        
        # Start scan in background thread
        scan_thread = threading.Thread(
            target=_run_scan_async,
            args=(ip_list, network_range, settings),
            daemon=True
        )
        scan_thread.start()
        
        return jsonify({
            'status': 'started',
            'message': f'Scan started for {len(ip_list)} hosts',
            'total': len(ip_list)
        })
        
    except Exception as e:
        _set_progress({'status': 'error'})
        return jsonify({'error': str(e)}), 500


def _ssh_run_command(ip, settings, command):
    """Run a single SSH command on the target IP and return combined stdout/stderr text."""
    username = settings.get('ssh_username', 'admin')
    password = settings.get('ssh_password', 'admin')
    port = int(settings.get('ssh_port', 22))
    # Paramiko needs enough time for SSH handshake; enforce a reasonable floor
    timeout = float(settings.get('ssh_timeout', 3) or 3)
    if timeout < 1.0:
        timeout = 1.0

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            ip,
            port=port,
            username=username,
            password=password,
            timeout=timeout,
            banner_timeout=timeout,
            auth_timeout=timeout,
            look_for_keys=False,
            allow_agent=False,
        )

        cmd_timeout = timeout
        if 'lldp show neighbors' in command:
            # LLDP can take slightly longer to respond; allow more time for this command
            cmd_timeout = max(timeout * 3, 5.0)

        stdin, stdout, stderr = client.exec_command(command, timeout=cmd_timeout)
        out = stdout.read().decode(errors='ignore')
        err = stderr.read().decode(errors='ignore')
        return (out or '') + (err or '')
    except Exception:
        return ''
    finally:
        try:
            client.close()
        except Exception:
            pass


def _parse_port_xcvr_show(output):
    """Parse 'port xcvr show' output from Ciena SAOS into interface dicts.

    The table has columns roughly:
      Port | Admin State | Oper State | Vendor Name & Part Number | Ciena Rev |
      Ether Medium & Connector Type | Diag Data
    """
    interfaces = []
    if not output:
        return interfaces

    for line in output.splitlines():
        line = line.rstrip('\r\n')
        if not line or not line.startswith('|'):
            continue

        # Strip leading/trailing '|' and split into columns
        parts = [p.strip() for p in line.strip().strip('|').split('|')]
        if not parts:
            continue

        # Skip header rows
        first_col = parts[0].lower()
        if first_col in ('port', 'port#'):
            continue

        # Data rows should start with numeric port
        if not parts[0].isdigit():
            continue

        # Ensure we have at least up to the Diag column
        if len(parts) < 7:
            continue

        port_str, admin_state, oper_state, vendor_part, ciena_rev, medium_connector, diag_data = (
            (parts + [''] * 7)[:7]
        )

        if not port_str.isdigit():
            continue

        port_num = int(port_str)
        # Use a high offset for interface_index so it never collides with SNMP
        # ifIndex values when we eventually combine views.
        interface_index = 10000 + port_num

        # Skip completely empty ports if clearly marked
        if vendor_part.lower().startswith('empty'):
            continue

        medium = medium_connector
        connector = ''
        if '/' in medium_connector:
            m, c = medium_connector.split('/', 1)
            medium = m.strip()
            connector = c.strip()

        speed = medium  # textual speed/medium description

        oper_lower = oper_state.lower()
        status = 'up' if oper_lower.startswith(('ena', 'up')) else 'down'

        medium_lower = medium.lower()
        connector_lower = connector.lower()

        # Classify optical vs electrical from medium/connector.
        # Copper indicators: BASE-T, RJ45, explicit 'copper'.
        is_optical = False
        if (
            any(tag in medium_lower for tag in ('lx', 'lr', 'sr', 'zx', 'sx', 'fx'))
            or any(tag in connector_lower for tag in ('lc', 'sc', 'fc', 'mtp', 'mpo'))
        ):
            is_optical = True
        if any(tag in medium_lower for tag in ('base-t', 'rj45', 'copper')) or 'rj45' in connector_lower:
            # Copper takes precedence if both appear
            is_optical = False

        interfaces.append({
            'interface_index': interface_index,
            'interface_name': f'Port {port_num}',
            'cli_port': port_num,
            'is_optical': is_optical,
            'medium': medium,
            'connector': connector,
            'speed': speed,
            'tx_power': '',
            'rx_power': '',
            'temperature': '',
            'status': status,
            'raw_output': line,
        })

    return interfaces


def _parse_port_xcvr_diagnostics(output):
    tx_dbm = None
    rx_dbm = None
    temperature = None

    if not output:
        return tx_dbm, rx_dbm, temperature

    for line in output.splitlines():
        line = line.rstrip('\r\n')
        if not line or not line.startswith('|'):
            continue

        parts = [p.strip() for p in line.strip().strip('|').split('|')]
        if len(parts) < 2:
            continue

        label = parts[0].lower()
        value = parts[1].strip()

        if tx_dbm is None and 'tx power' in label and 'dbm' in label:
            tx_dbm = value
        elif rx_dbm is None and 'rx power' in label and 'dbm' in label:
            rx_dbm = value
        elif temperature is None and ('temperature' in label or 'temp' in label) and 'c' in label.lower():
            temperature = value

        if tx_dbm is not None and rx_dbm is not None and temperature is not None:
            break

    return tx_dbm, rx_dbm, temperature


def _parse_port_show(output):
    """Parse 'port show' output into per-port operational info.

    Expected row example:
      | 5       |10/100/G | Up |  62d10h13m30s|    |FWD|1000/FD| On |Ena |1000/FD| On |
    """
    ports = {}
    if not output:
        return ports

    for line in output.splitlines():
        line = line.rstrip('\r\n')
        if not line or not line.startswith('|'):
            continue

        parts = [p.strip() for p in line.strip().strip('|').split('|')]
        if len(parts) < 3:
            continue

        col0 = parts[0].lower()
        col1 = parts[1].lower()

        # Skip header rows
        if col0 in ('port', 'port name') or col1 in ('port', 'type'):
            continue

        # Data rows start with numeric port
        if not parts[0] or not parts[0].isdigit():
            continue

        port_num = int(parts[0])
        port_type = parts[1]
        link = parts[2]
        mode = parts[6] if len(parts) > 6 else ''

        ports[port_num] = {
            'port_type': port_type,
            'link': link,
            'mode': mode,
        }

    return ports


def _parse_lldp_info_line(line, neighbor):
    text = line.strip()
    if not text:
        return
    lower = text.lower()

    if lower.startswith('chassis id:'):
        neighbor['lldp_remote_chassis_id'] = text.split(':', 1)[1].strip()
    elif lower.startswith('mgmt addr:'):
        addr = text.split(':', 1)[1].strip()
        if addr:
            neighbor['lldp_remote_mgmt_addr'] = addr
    elif lower.startswith('system name:'):
        neighbor['lldp_remote_system_name'] = text.split(':', 1)[1].strip()


def _parse_lldp_neighbors(output):
    """Parse 'lldp show neighbors' into local-port -> neighbor info mapping.

    More robust implementation using regex to match rows like:
      |21           |2                               |  Chassis Id: ... |
      |             |                                |   Mgmt Addr: ... |
    """
    neighbors = {}
    if not output:
        return neighbors

    # Match a new neighbor row: | <local> | <remote-port> | <info> |
    new_neighbor_re = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|?$")
    # Match continuation info row: |       |               | <info> |
    cont_re = re.compile(r"^\|\s*\|\s*\|\s*(.*?)\s*\|?$")

    current_local = None
    current_neighbor = None
    current_info_lines = []

    for line in output.splitlines():
        line = line.rstrip('\r\n')
        if not line or not line.startswith('|'):
            continue

        m_new = new_neighbor_re.match(line)
        if m_new:
            # Flush previous neighbor
            if current_local is not None and current_neighbor is not None:
                if current_info_lines and 'lldp_raw_info' not in current_neighbor:
                    current_neighbor['lldp_raw_info'] = '\n'.join(current_info_lines)
                neighbors[current_local] = current_neighbor

            local_port = int(m_new.group(1))
            remote_port = m_new.group(2).strip()
            info_text = m_new.group(3).strip()

            current_local = local_port
            current_neighbor = {
                'lldp_remote_port': remote_port,
            }
            current_info_lines = []

            if info_text:
                current_info_lines.append(info_text)
                _parse_lldp_info_line(info_text, current_neighbor)
            continue

        # Continuation line: additional Info for current neighbor
        m_cont = cont_re.match(line)
        if m_cont and current_local is not None and current_neighbor is not None:
            info_text = m_cont.group(1).strip()
            if not info_text:
                continue
            current_info_lines.append(info_text)
            _parse_lldp_info_line(info_text, current_neighbor)

    # Flush last neighbor
    if current_local is not None and current_neighbor is not None:
        if current_info_lines and 'lldp_raw_info' not in current_neighbor:
            current_neighbor['lldp_raw_info'] = '\n'.join(current_info_lines)
        neighbors[current_local] = current_neighbor

    return neighbors


def _run_ssh_scan_async(ip_list, settings):
    """Run an SSH/CLI scan in a background thread for the given IPs."""
    try:
        _scan_cancel_flag.clear()
        batch_size = min(100, max(1, int(settings.get('max_threads', 20))))

        for i in range(0, len(ip_list), batch_size):
            if _scan_cancel_flag.is_set():
                _set_progress({'status': 'cancelled'})
                return

            batch = ip_list[i:i + batch_size]
            batch_threads = []
            batch_results = {}
            batch_lock = threading.Lock()

            def scan_ssh_for_ip(ip_str, settings_copy):
                try:
                    output = _ssh_run_command(ip_str, settings_copy, 'port xcvr show')
                    interfaces = _parse_port_xcvr_show(output)
                    had_output = bool(output.strip())

                    # Per-port operational info (link state, type, mode)
                    port_show_out = _ssh_run_command(ip_str, settings_copy, 'port show')
                    port_show_info = _parse_port_show(port_show_out)

                    if interfaces:
                        for iface in interfaces:
                            # Apply port show info first (status/speed/medium/connector), for both
                            # copper and optical ports.
                            port_key = iface.get('cli_port')
                            if not port_key:
                                idx = iface.get('interface_index')
                                try:
                                    idx_int = int(idx)
                                    port_key = idx_int if idx_int < 10000 else idx_int - 10000
                                except Exception:
                                    port_key = None

                            if port_key and port_show_info:
                                pinfo = port_show_info.get(port_key)
                                if pinfo:
                                    link = (pinfo.get('link') or '').strip().lower()
                                    if link.startswith('up'):
                                        iface['status'] = 'up'
                                    elif link.startswith('down'):
                                        iface['status'] = 'down'

                                    mode = (pinfo.get('mode') or '').strip()
                                    if mode and not iface.get('speed'):
                                        iface['speed'] = mode

                                    ptype = (pinfo.get('port_type') or '').strip()
                                    ptype_lower = ptype.lower()

                                    # Fill in medium/connector for electrical ports
                                    if not iface.get('medium') and ptype:
                                        iface['medium'] = ptype
                                    if not iface.get('connector') and any(t in ptype_lower for t in ['10/100', 'g']):
                                        iface['connector'] = 'RJ45'

                            if not iface.get('is_optical'):
                                continue

                            # Always use CLI port number for device commands.
                            port_num = iface.get('cli_port')
                            if not port_num:
                                idx = iface.get('interface_index')
                                try:
                                    idx_int = int(idx)
                                    port_num = idx_int if idx_int < 10000 else idx_int - 10000
                                except Exception:
                                    continue
                            if not port_num:
                                continue

                            diag_cmd = f'port xcvr show port {port_num} diagnostics'
                            diag_output = _ssh_run_command(ip_str, settings_copy, diag_cmd)
                            tx_dbm, rx_dbm, temperature = _parse_port_xcvr_diagnostics(diag_output)

                            if tx_dbm is not None:
                                iface['tx_power'] = tx_dbm
                            if rx_dbm is not None:
                                iface['rx_power'] = rx_dbm
                            if temperature is not None:
                                iface['temperature'] = temperature

                        # LLDP neighbors for this device
                        lldp_output = _ssh_run_command(ip_str, settings_copy, 'lldp show neighbors')
                        lldp_neighbors = _parse_lldp_neighbors(lldp_output)

                        if lldp_neighbors:
                            for iface in interfaces:
                                # Map LLDP neighbors by physical port number, not interface_index.
                                port_key = iface.get('cli_port')
                                if not port_key:
                                    idx = iface.get('interface_index')
                                    try:
                                        idx_int = int(idx)
                                        port_key = idx_int if idx_int < 10000 else idx_int - 10000
                                    except Exception:
                                        continue
                                if not port_key:
                                    continue

                                neigh = lldp_neighbors.get(port_key)
                                if not neigh:
                                    continue

                                iface['lldp_remote_port'] = neigh.get('lldp_remote_port')
                                iface['lldp_remote_mgmt_addr'] = neigh.get('lldp_remote_mgmt_addr')
                                iface['lldp_remote_chassis_id'] = neigh.get('lldp_remote_chassis_id')
                                iface['lldp_remote_system_name'] = neigh.get('lldp_remote_system_name')
                                iface['lldp_raw_info'] = neigh.get('lldp_raw_info')

                                # If LLDP sees a live neighbor, treat the port as up
                                if iface.get('status') != 'up':
                                    iface['status'] = 'up'

                    with batch_lock:
                        batch_results[ip_str] = interfaces
                    _increment_progress('scanned')
                    if had_output:
                        _increment_progress('online')
                except Exception:
                    with batch_lock:
                        batch_results[ip_str] = []
                    _increment_progress('scanned')

            for ip in batch:
                thread = threading.Thread(target=scan_ssh_for_ip, args=(ip, settings.copy()))
                thread.daemon = True
                thread.start()
                batch_threads.append(thread)

            for thread in batch_threads:
                thread.join(timeout=30)

            # Store SSH/CLI interface data in the database
            try:
                for ip_str, interfaces in batch_results.items():
                    for iface in interfaces:
                        db.insert_ssh_cli_scan(
                            ip_str,
                            iface['interface_index'],
                            iface['interface_name'],
                            iface['cli_port'],
                            iface['is_optical'],
                            iface['medium'],
                            iface['connector'],
                            iface['speed'],
                            iface['tx_power'],
                            iface['rx_power'],
                            iface.get('temperature', ''),
                            iface['status'],
                            iface['raw_output'],
                            iface.get('lldp_remote_port'),
                            iface.get('lldp_remote_mgmt_addr'),
                            iface.get('lldp_remote_chassis_id'),
                            iface.get('lldp_remote_system_name'),
                            iface.get('lldp_raw_info'),
                        )
                        
                        # Save optical power readings to history table if available
                        if iface.get('is_optical') and (iface.get('tx_power') or iface.get('rx_power') or iface.get('temperature')):
                            try:
                                # Parse power values to decimal, handling various formats
                                tx_val = None
                                rx_val = None
                                temp_val = None
                                
                                if iface.get('tx_power'):
                                    tx_str = str(iface['tx_power']).replace('dBm', '').strip()
                                    try:
                                        tx_val = float(tx_str)
                                    except:
                                        tx_val = None
                                
                                if iface.get('rx_power'):
                                    rx_str = str(iface['rx_power']).replace('dBm', '').strip()
                                    try:
                                        rx_val = float(rx_str)
                                    except:
                                        rx_val = None
                                
                                if iface.get('temperature'):
                                    temp_str = str(iface['temperature']).replace('C', '').strip()
                                    try:
                                        temp_val = float(temp_str)
                                    except:
                                        temp_val = None
                                
                                if tx_val is not None or rx_val is not None or temp_val is not None:
                                    # Use a completely separate database connection for power history
                                    try:
                                        power_conn = psycopg2.connect(
                                            host=os.getenv('PG_HOST', 'localhost'),
                                            port=os.getenv('PG_PORT', '5432'),
                                            database=os.getenv('PG_DATABASE', 'network_scan'),
                                            user=os.getenv('PG_USER', 'postgres'),
                                            password=os.getenv('PG_PASSWORD', 'postgres')
                                        )
                                        power_cursor = power_conn.cursor()
                                        power_cursor.execute(
                                            '''INSERT INTO optical_power_history 
                                               (ip_address, interface_index, interface_name, cli_port, tx_power, rx_power, temperature)
                                               VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                                            (ip_str, iface['interface_index'], iface['interface_name'], 
                                             iface['cli_port'], tx_val, rx_val, temp_val)
                                        )
                                        power_conn.commit()
                                        power_cursor.close()
                                        power_conn.close()
                                    except Exception as e:
                                        print(f"Power history insert error for {ip_str}: {e}")
                            except Exception as e:
                                print(f"Power history insert error for {ip_str}: {e}")
            except Exception as e:
                print(f"SSH/CLI database error: {e}")

        _set_progress({'status': 'complete'})

    except Exception as e:
        _set_progress({'status': 'error', 'error': str(e)})


def ssh_scan_devices():
    """Start an SSH-only CLI scan over existing or selected devices (async)."""
    try:
        with _progress_lock:
            if scan_progress['status'] == 'scanning':
                return jsonify({'error': 'Scan already in progress'}), 409

        data = request.get_json(silent=True) or {}
        ip_list = data.get('ip_list')

        settings = get_settings()
        success_status = settings.get('ssh_success_status', 'YES')

        if ip_list:
            # Only include selected IPs that already have SSH detected
            # Filter out any non-string values (like True/False)
            filtered_ips = [ip for ip in ip_list if isinstance(ip, str) and ip.strip()]
            if not filtered_ips:
                return jsonify({'error': 'No valid IP addresses selected'}), 400
            
            conn = db.get_connection()
            cursor = conn.cursor()
            # Create placeholders for IN clause
            placeholders = ','.join(['%s'] * len(filtered_ips))
            cursor.execute(
                f'SELECT ip_address FROM scan_results '
                f'WHERE host(ip_address) IN ({placeholders}) AND ssh_status = %s '
                f'ORDER BY ip_address',
                filtered_ips + [success_status],
            )
            rows = cursor.fetchall()
            conn.close()
            targets = [str(r[0]) for r in rows]
        else:
            # Default: run SSH scan only against devices that already have SSH detected
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT ip_address FROM scan_results WHERE ssh_status = %s ORDER BY ip_address',
                (success_status,)
            )
            rows = cursor.fetchall()
            conn.close()
            targets = [str(r[0]) for r in rows]

        if not targets:
            return jsonify({'error': 'No devices with SSH detected are available for SSH scan'}), 400

        _set_progress({
            'scanned': 0,
            'total': len(targets),
            'online': 0,
            'status': 'scanning',
            'network_range': 'SSH Scan',
        })

        scan_thread = threading.Thread(
            target=_run_ssh_scan_async,
            args=(targets, settings),
            daemon=True,
        )
        scan_thread.start()

        return jsonify({
            'status': 'started',
            'message': f'SSH scan started for {len(targets)} devices',
            'total': len(targets),
        })

    except Exception as e:
        _set_progress({'status': 'error'})
        return jsonify({'error': str(e)}), 500


def get_ssh_cli_interfaces():
    """Return SSH/CLI interface data for a specific device."""
    try:
        data = request.get_json(silent=True) or {}
        ip = data.get('ip')
        limit = int(data.get('limit', 50))

        if not ip:
            return jsonify({'error': 'No IP provided'}), 400

        rows = db.get_ssh_cli_scans(ip, limit=limit)
        interfaces = []
        for row in rows:
            # ssh_cli_scans schema:
            # id, ip_address, scan_timestamp, interface_index, interface_name,
            # cli_port, is_optical, medium, connector, speed,
            # tx_power, rx_power, status, raw_output,
            # lldp_remote_port, lldp_remote_mgmt_addr,
            # lldp_remote_chassis_id, lldp_remote_system_name,
            # lldp_raw_info, temperature
            interfaces.append({
                'interface_index': row[3],
                'interface_name': row[4] or '',
                'cli_port': row[5],
                'is_optical': bool(row[6]),
                'medium': row[7] or '',
                'connector': row[8] or '',
                'speed': row[9] or '',
                'tx_power': row[10] or '',
                'rx_power': row[11] or '',
                'status': row[12] or '',
                'raw_output': row[13] or '',
                'lldp_remote_port': row[14] or '',
                'lldp_remote_mgmt_addr': row[15] or '',
                'lldp_remote_chassis_id': row[16] or '',
                'lldp_remote_system_name': row[17] or '',
                'lldp_raw_info': row[18] or '',
                'temperature': row[19] or '',
            })

        return jsonify({'interfaces': interfaces})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def get_combined_interfaces():
    """Return combined SNMP + SSH interface data.

    Placeholder implementation: returns an empty list so the frontend
    falls back to SSH/CLI-only data when available.
    """
    try:
        return jsonify({'interfaces': []})
    except Exception as e:
        return jsonify({'error': str(e), 'interfaces': []}), 500


def _snmp_get_value(ip, settings, oid):
    """Helper: run snmpget for a single OID and return the value text or ''."""
    community = settings.get('snmp_community', 'public')
    version = settings.get('snmp_version', '2c')
    port = str(settings.get('snmp_port', '161'))
    timeout = float(settings.get('snmp_timeout', '1') or 1)

    cmd = [
        'snmpget',
        '-On',
        f'-v{version}',
        '-c', community,
        '-t', str(timeout),
        '-r', '0',
        f'{ip}:{port}',
        oid
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 0.5
        )
        out = (result.stdout or '') + (result.stderr or '')
        out_lower = out.lower()

        if 'timeout' in out_lower or 'no response' in out_lower:
            return ''
        if 'no such object' in out_lower or 'no such instance' in out_lower:
            return ''

        if '=' in out:
            _, value_part = out.split('=', 1)
            value_part = value_part.strip()

            if ': ' in value_part:
                _, value_str = value_part.split(':', 1)
            else:
                value_str = value_part

            value_str = value_str.strip()

            if (value_str.startswith('"') and value_str.endswith('"')) or \
               (value_str.startswith("'") and value_str.endswith("'")):
                value_str = value_str[1:-1]

            return value_str.strip()

        return out.strip()
    except Exception:
        return ''


def _get_vendor_name_from_oid(objid):
    if not objid:
        return ''

    if objid.startswith('.'):
        objid = objid[1:]

    prefix = '1.3.6.1.4.1.'
    idx = objid.find(prefix)
    if idx == -1:
        return ''

    rest = objid[idx + len(prefix):]
    enterprise_id = ''
    for ch in rest:
        if ch.isdigit():
            enterprise_id += ch
        else:
            break

    if not enterprise_id:
        return ''

    mapping = {
        '9': 'Cisco',
        '11': 'HP',
        '2011': 'Huawei',
        '2636': 'Juniper',
        '1271': 'Ciena',
        '7737': 'Ciena',
        '6141': 'Ciena',
        '368': 'Axis',
        '534': 'Eaton/Powerware',
        '31926': 'Siklu',
        '5205': 'Ruby Tech',
        '52642': 'FS.com',
        '10456': 'Planet',
        '41112': 'Ubiquiti',
        '311': 'Microsoft',
    }
    return mapping.get(enterprise_id, '')


def get_snmp_basic_info(ip, settings):
    """Fetch basic SNMP system info for a single IP using existing settings.

    Populates the existing scan_results fields:
      snmp_status, snmp_description, snmp_hostname, snmp_location,
      snmp_contact, snmp_uptime, snmp_vendor_oid.
    """
    descr = _snmp_get_value(ip, settings, '1.3.6.1.2.1.1.1.0')
    objid = _snmp_get_value(ip, settings, '1.3.6.1.2.1.1.2.0')
    uptime = _snmp_get_value(ip, settings, '1.3.6.1.2.1.1.3.0')
    contact = _snmp_get_value(ip, settings, '1.3.6.1.2.1.1.4.0')
    name = _snmp_get_value(ip, settings, '1.3.6.1.2.1.1.5.0')
    location = _snmp_get_value(ip, settings, '1.3.6.1.2.1.1.6.0')

    vendor_name = _get_vendor_name_from_oid(objid)
    ent_model = _snmp_get_value(ip, settings, '1.3.6.1.2.1.47.1.1.1.1.2.1')
    ent_serial = _snmp_get_value(ip, settings, '1.3.6.1.2.1.47.1.1.1.1.11.1')
    chassis_mac = _snmp_get_value(ip, settings, '1.3.6.1.2.1.2.2.1.6.1')

    # Ciena-specific serial fallback (WWP-LEOS-CHASSIS-MIB::wwpLeosSystemSerialNumber.0)
    if not ent_serial and vendor_name == 'Ciena':
        ent_serial = _snmp_get_value(ip, settings, '1.3.6.1.4.1.6141.2.60.11.1.1.1.67.0')

    success_status = settings.get('snmp_success_status', 'YES')
    fail_status = settings.get('snmp_fail_status', 'NO')

    any_value = any([descr, objid, uptime, contact, name, location])
    snmp_status = success_status if any_value else fail_status

    model_value = ent_model or descr

    return {
        'snmp_status': snmp_status,
        'snmp_description': descr,
        'snmp_hostname': name,
        'snmp_location': location,
        'snmp_contact': contact,
        'snmp_uptime': uptime,
        'snmp_vendor_oid': objid,
        'snmp_vendor_name': vendor_name,
        'snmp_model': model_value,
        'snmp_chassis_mac': chassis_mac,
        'snmp_serial': ent_serial,
    }


def _run_snmp_scan_async(ip_list, settings):
    """Run a basic SNMP-only scan in a background thread for the given IPs."""
    try:
        _scan_cancel_flag.clear()
        batch_size = min(100, max(1, int(settings.get('max_threads', 20))))

        for i in range(0, len(ip_list), batch_size):
            if _scan_cancel_flag.is_set():
                _set_progress({'status': 'cancelled'})
                return

            batch = ip_list[i:i + batch_size]
            batch_threads = []
            batch_results = {}
            batch_lock = threading.Lock()

            def scan_snmp_for_ip(ip_str, settings_copy):
                try:
                    info = get_snmp_basic_info(ip_str, settings_copy)
                    with batch_lock:
                        batch_results[ip_str] = info
                    _increment_progress('scanned')
                    if info.get('snmp_status') == settings_copy.get('snmp_success_status', 'YES'):
                        _increment_progress('online')
                except Exception:
                    with batch_lock:
                        batch_results[ip_str] = {
                            'snmp_status': settings_copy.get('snmp_fail_status', 'NO'),
                            'snmp_description': '',
                            'snmp_hostname': '',
                            'snmp_location': '',
                            'snmp_contact': '',
                            'snmp_uptime': '',
                            'snmp_vendor_oid': '',
                            'snmp_vendor_name': '',
                            'snmp_model': '',
                            'snmp_chassis_mac': '',
                            'snmp_serial': '',
                        }
                    _increment_progress('scanned')

            for ip in batch:
                thread = threading.Thread(target=scan_snmp_for_ip, args=(ip, settings.copy()))
                thread.daemon = True
                thread.start()
                batch_threads.append(thread)

            for thread in batch_threads:
                thread.join(timeout=15)

            try:
                conn = db.get_connection()
                cursor = conn.cursor()

                for ip_str, info in batch_results.items():
                    cursor.execute('''
                        UPDATE scan_results
                        SET snmp_status = %s,
                            snmp_description = %s,
                            snmp_hostname = %s,
                            snmp_location = %s,
                            snmp_contact = %s,
                            snmp_uptime = %s,
                            snmp_vendor_oid = %s,
                            snmp_vendor_name = %s,
                            snmp_model = %s,
                            snmp_chassis_mac = %s,
                            snmp_serial = %s
                        WHERE ip_address = %s
                    ''', (
                        info['snmp_status'],
                        info['snmp_description'],
                        info['snmp_hostname'],
                        info['snmp_location'],
                        info['snmp_contact'],
                        info['snmp_uptime'],
                        info['snmp_vendor_oid'],
                        info['snmp_vendor_name'],
                        info['snmp_model'],
                        info['snmp_chassis_mac'],
                        info['snmp_serial'],
                        ip_str,
                    ))

                conn.commit()
                conn.close()
            except Exception as e:
                print(f"SNMP database error: {e}")

        _set_progress({'status': 'complete'})

    except Exception as e:
        _set_progress({'status': 'error', 'error': str(e)})


def snmp_scan_devices():
    """Start an SNMP-only scan over existing or selected devices (async)."""
    try:
        with _progress_lock:
            if scan_progress['status'] == 'scanning':
                return jsonify({'error': 'Scan already in progress'}), 409

        data = request.get_json(silent=True) or {}
        ip_list = data.get('ip_list')

        # Load settings first so we know what "SNMP detected" means
        settings = get_settings()
        success_status = settings.get('snmp_success_status', 'YES')

        if ip_list:
            # When the user has explicitly selected devices, honor that list exactly
            # and attempt SNMP against those IPs regardless of existing snmp_status.
            targets = [str(ip) for ip in ip_list]
        else:
            # Default: run SNMP scan only against devices that already have SNMP detected
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT ip_address FROM scan_results WHERE snmp_status = %s ORDER BY ip_address',
                (success_status,)
            )
            rows = cursor.fetchall()
            conn.close()
            targets = [str(r[0]) for r in rows]

        if not targets:
            return jsonify({'error': 'No devices with SNMP detected are available for SNMP scan'}), 400

        _set_progress({
            'scanned': 0,
            'total': len(targets),
            'online': 0,
            'status': 'scanning',
            'network_range': 'SNMP Scan'
        })

        scan_thread = threading.Thread(
            target=_run_snmp_scan_async,
            args=(targets, settings),
            daemon=True
        )
        scan_thread.start()

        return jsonify({
            'status': 'started',
            'message': f'SNMP scan started for {len(targets)} devices',
            'total': len(targets)
        })

    except Exception as e:
        _set_progress({'status': 'error'})
        return jsonify({'error': str(e)}), 500

def _run_selected_scan_async(ip_list, settings):
    """Run selected devices scan in background thread"""
    try:
        _scan_cancel_flag.clear()
        batch_size = min(100, max(1, int(settings.get('max_threads', 50))))
        
        for i in range(0, len(ip_list), batch_size):
            if _scan_cancel_flag.is_set():
                _set_progress({'status': 'cancelled'})
                return
            
            batch = ip_list[i:i + batch_size]
            batch_threads = []
            batch_results = {}
            batch_lock = threading.Lock()
            
            def scan_ip(ip_str, settings_copy):
                try:
                    ping_status, snmp_status, ssh_status, rdp_status, hostname = scan_single_ip(ip_str, settings_copy)
                    with batch_lock:
                        batch_results[ip_str] = (ping_status, snmp_status, ssh_status, rdp_status, hostname)
                    _increment_progress('scanned')
                    if ping_status == settings_copy['online_status']:
                        _increment_progress('online')
                except Exception:
                    with batch_lock:
                        batch_results[ip_str] = (settings_copy['offline_status'], 'NO', 'NO', 'NO', '')
                    _increment_progress('scanned')
            
            for ip in batch:
                thread = threading.Thread(target=scan_ip, args=(ip, settings.copy()))
                thread.daemon = True
                thread.start()
                batch_threads.append(thread)
            
            for thread in batch_threads:
                thread.join(timeout=15)
            
            # Store results
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                
                for ip_str, (ping_status, snmp_status, ssh_status, rdp_status, hostname) in batch_results.items():
                    scan_timestamp = datetime.now() if ping_status == settings['online_status'] else None
                    cursor.execute('''
                        INSERT INTO scan_results 
                            (ip_address, network_range, ping_status, scan_timestamp, snmp_status, ssh_status, rdp_status, snmp_hostname) 
                        VALUES (%s, 'Selected Devices', %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (ip_address) DO UPDATE SET
                            ping_status = EXCLUDED.ping_status,
                            scan_timestamp = COALESCE(EXCLUDED.scan_timestamp, scan_results.scan_timestamp),
                            snmp_status = EXCLUDED.snmp_status,
                            ssh_status = EXCLUDED.ssh_status,
                            rdp_status = EXCLUDED.rdp_status,
                            snmp_hostname = COALESCE(NULLIF(EXCLUDED.snmp_hostname, ''), scan_results.snmp_hostname)
                    ''', (ip_str, ping_status, scan_timestamp, snmp_status, ssh_status, rdp_status, hostname))
                
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Database error: {e}")
        
        _set_progress({'status': 'complete'})
        
    except Exception as e:
        _set_progress({'status': 'error', 'error': str(e)})


def scan_selected_devices():
    """Scan specific selected IP addresses - async"""
    try:
        with _progress_lock:
            if scan_progress['status'] == 'scanning':
                return jsonify({'error': 'Scan already in progress'}), 409
        
        data = request.get_json()
        ip_list = data.get('ip_list', [])
        
        if not ip_list:
            return jsonify({'error': 'No IP addresses provided'}), 400
        
        settings = get_settings()
        
        _set_progress({
            'scanned': 0,
            'total': len(ip_list),
            'online': 0,
            'status': 'scanning'
        })
        
        scan_thread = threading.Thread(
            target=_run_selected_scan_async,
            args=(ip_list, settings),
            daemon=True
        )
        scan_thread.start()
        
        return jsonify({
            'status': 'started',
            'message': f'Scan started for {len(ip_list)} selected devices',
            'total': len(ip_list)
        })
        
    except Exception as e:
        _set_progress({'status': 'error'})
        return jsonify({'error': str(e)}), 500

def get_scan_progress():
    """Get current scan progress - thread-safe"""
    with _progress_lock:
        return jsonify(dict(scan_progress))


def cancel_scan():
    """Cancel running scan"""
    with _progress_lock:
        if scan_progress['status'] != 'scanning':
            return jsonify({'error': 'No scan in progress'}), 400
    
    _scan_cancel_flag.set()
    return jsonify({'status': 'success', 'message': 'Scan cancellation requested'})

def delete_selected_records():
    """Delete selected records from database"""
    try:
        data = request.get_json()
        ip_list = data.get('ip_list', [])
        
        if not ip_list:
            return jsonify({'error': 'No IP addresses provided'}), 400
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Delete records for the specified IPs
        placeholders = ','.join(['%s'] * len(ip_list))
        cursor.execute(f'DELETE FROM scan_results WHERE ip_address IN ({placeholders})', ip_list)
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success', 
            'message': f'Deleted {deleted_count} records successfully',
            'deleted': deleted_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
