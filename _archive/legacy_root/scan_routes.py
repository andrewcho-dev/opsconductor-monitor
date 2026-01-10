"""
Scan routes - Compatibility wrapper.

This module provides backward compatibility with code that imports from scan_routes.py.
It delegates to the new backend modules.
"""

import os
import sys
import threading

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.parsers.ciena import (
    CienaPortXcvrParser,
    CienaPortShowParser,
    CienaPortDiagnosticsParser,
    CienaLldpRemoteParser,
)
from backend.executors import SSHExecutor, PingExecutor, SNMPExecutor

# Scan state
_scan_cancel_flag = threading.Event()
_scan_progress = {
    'status': 'idle',
    'scanned': 0,
    'total': 0,
    'online': 0,
}


def get_settings():
    """Load settings from file."""
    import json
    settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
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


# Parser function wrappers for backward compatibility
def _parse_port_xcvr_show(output):
    """Parse 'port xcvr show' output."""
    parser = CienaPortXcvrParser()
    return parser.parse(output)


def _parse_port_show(output):
    """Parse 'port show' output."""
    parser = CienaPortShowParser()
    results = parser.parse(output)
    # Convert to dict format expected by old code
    return {r['cli_port']: r for r in results}


def _parse_port_xcvr_diagnostics(output):
    """Parse port diagnostics output."""
    parser = CienaPortDiagnosticsParser()
    results = parser.parse(output)
    if results:
        r = results[0]
        return r.get('tx_power'), r.get('rx_power'), r.get('temperature')
    return None, None, None


def _parse_lldp_neighbors(output):
    """Parse LLDP neighbors output."""
    parser = CienaLldpRemoteParser()
    return parser.to_dict(output)


# Executor function wrappers
def ping_fast(ip, timeout=5):
    """Fast ping check."""
    executor = PingExecutor()
    result = executor.execute(ip, config={'timeout': timeout, 'count': 1})
    return result.get('reachable', False)


def check_snmp_agent(ip, community='public', timeout=5):
    """Check if SNMP agent is responding."""
    executor = SNMPExecutor()
    return executor.check_agent(ip, {'community': community, 'timeout': timeout})


def check_port_fast(ip, port, timeout=5):
    """Check if a TCP port is open."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False


def _ssh_run_command(ip, command, settings=None):
    """Run SSH command on a device."""
    if settings is None:
        settings = get_settings()
    
    executor = SSHExecutor()
    config = {
        'username': settings.get('ssh_username', ''),
        'password': settings.get('ssh_password', ''),
        'port': settings.get('ssh_port', 22),
        'timeout': settings.get('scan_timeout', 30),
    }
    
    result = executor.execute(ip, command, config)
    
    if result.get('success'):
        return result.get('output', '')
    return None


# Scan functions
def start_scan():
    """Start a network scan."""
    settings = get_settings()
    # Implementation would go here
    pass


def scan_ips(ips):
    """Scan specific IPs."""
    # Implementation would go here
    pass


def start_snmp_scan():
    """Start SNMP scan."""
    # Implementation would go here
    pass


def start_ssh_scan(ips=None):
    """Start SSH scan."""
    # Implementation would go here
    pass


def cancel_scan():
    """Cancel running scan."""
    _scan_cancel_flag.set()


__all__ = [
    '_parse_port_xcvr_show',
    '_parse_port_show',
    '_parse_port_xcvr_diagnostics',
    '_parse_lldp_neighbors',
    'ping_fast',
    'check_snmp_agent',
    'check_port_fast',
    '_ssh_run_command',
    'start_scan',
    'scan_ips',
    'start_snmp_scan',
    'start_ssh_scan',
    'cancel_scan',
    'get_settings',
]
