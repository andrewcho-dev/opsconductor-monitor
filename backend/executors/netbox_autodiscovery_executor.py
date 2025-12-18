"""
NetBox Autodiscovery Executor.

Comprehensive network discovery with automatic NetBox device creation.
Discovers hosts, identifies vendors/models via SNMP, and syncs to NetBox.
"""

import logging
import ipaddress
import re
import socket
import time
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from .base import BaseExecutor
from .registry import register_executor
from .ping_executor import PingExecutor
from .snmp_executor import SNMPExecutor

logger = logging.getLogger(__name__)


# Vendor identification patterns from sysDescr
VENDOR_PATTERNS = [
    # Cisco
    (r'Cisco\s+(IOS|NX-OS|Adaptive Security|ASA)', 'Cisco', 'network'),
    (r'Cisco\s+(\S+)', 'Cisco', 'network'),
    
    # Juniper
    (r'Juniper\s+Networks', 'Juniper', 'network'),
    (r'JUNOS', 'Juniper', 'network'),
    
    # Arista
    (r'Arista\s+Networks\s+EOS', 'Arista', 'network'),
    
    # HP/Aruba
    (r'ProCurve', 'HP', 'network'),
    (r'Aruba', 'Aruba', 'network'),
    (r'HPE\s+OfficeConnect', 'HPE', 'network'),
    
    # Dell
    (r'Dell\s+(EMC|Networking|PowerConnect)', 'Dell', 'network'),
    (r'Force10', 'Dell', 'network'),
    
    # Ubiquiti
    (r'Ubiquiti', 'Ubiquiti', 'network'),
    (r'EdgeOS', 'Ubiquiti', 'network'),
    (r'UniFi', 'Ubiquiti', 'network'),
    
    # MikroTik
    (r'MikroTik|RouterOS', 'MikroTik', 'network'),
    
    # Fortinet
    (r'Fortinet|FortiGate|FortiOS', 'Fortinet', 'firewall'),
    
    # Palo Alto
    (r'Palo Alto|PAN-OS', 'Palo Alto', 'firewall'),
    
    # Linux
    (r'Linux\s+(\S+)\s+(\d+\.\d+)', 'Linux', 'server'),
    (r'Ubuntu', 'Linux', 'server'),
    (r'CentOS', 'Linux', 'server'),
    (r'Red Hat|RHEL', 'Linux', 'server'),
    (r'Debian', 'Linux', 'server'),
    
    # Windows
    (r'Windows', 'Microsoft', 'server'),
    (r'Microsoft', 'Microsoft', 'server'),
    
    # VMware
    (r'VMware\s+ESXi?', 'VMware', 'server'),
    
    # Ciena
    (r'Ciena|SAOS', 'Ciena', 'network'),
    
    # Axis (cameras)
    (r'AXIS', 'Axis', 'camera'),
    
    # Synology
    (r'Synology', 'Synology', 'storage'),
    
    # QNAP
    (r'QNAP', 'QNAP', 'storage'),
    
    # APC (UPS)
    (r'APC\s+Web/SNMP', 'APC', 'pdu'),
    
    # TP-Link / Omada
    (r'Omada', 'TP-Link', 'network'),
    (r'TP-Link', 'TP-Link', 'network'),
    
    # Proxmox
    (r'Proxmox', 'Proxmox', 'server'),
    
    # Generic
    (r'Net-SNMP', 'Generic Linux', 'server'),
]

# MAC OUI to vendor mapping (first 3 octets)
MAC_OUI_VENDORS = {
    '00:00:0c': 'Cisco',
    '00:01:42': 'Cisco',
    '00:1a:a1': 'Cisco',
    '00:1b:54': 'Cisco',
    '00:50:56': 'VMware',
    '00:0c:29': 'VMware',
    '00:15:5d': 'Microsoft Hyper-V',
    '00:1c:42': 'Parallels',
    '08:00:27': 'VirtualBox',
    '52:54:00': 'QEMU/KVM',
    '00:1e:67': 'Intel',
    '00:25:90': 'Super Micro',
    '00:30:48': 'Super Micro',
    'b8:ac:6f': 'Dell',
    '00:14:22': 'Dell',
    '18:66:da': 'Dell',
    '00:17:a4': 'HP',
    '00:21:5a': 'HP',
    '3c:d9:2b': 'HP',
    '00:1f:29': 'HP',
    '00:0e:7f': 'HP',
    '00:1a:4b': 'HP',
    '00:23:7d': 'HP',
    '78:e7:d1': 'HP',
    '00:1e:c9': 'Dell',
    '00:22:19': 'Dell',
    '00:26:b9': 'Dell',
    '00:0d:56': 'Dell',
    '00:12:3f': 'Dell',
    '00:13:72': 'Dell',
    '00:15:c5': 'Dell',
    '00:18:8b': 'Dell',
    '00:19:b9': 'Dell',
    '00:1a:a0': 'Dell',
    '00:1d:09': 'Dell',
    '00:1e:4f': 'Dell',
    '00:21:9b': 'Dell',
    '00:22:19': 'Dell',
    '00:24:e8': 'Dell',
    '00:25:64': 'Dell',
    '00:26:b9': 'Dell',
    'd4:be:d9': 'Dell',
    'f0:4d:a2': 'Dell',
    '24:6e:96': 'Dell',
    '14:fe:b5': 'Dell',
    '44:a8:42': 'Dell',
    '80:18:44': 'Ubiquiti',
    '04:18:d6': 'Ubiquiti',
    '24:5a:4c': 'Ubiquiti',
    '68:72:51': 'Ubiquiti',
    '74:83:c2': 'Ubiquiti',
    '78:8a:20': 'Ubiquiti',
    'b4:fb:e4': 'Ubiquiti',
    'dc:9f:db': 'Ubiquiti',
    'f0:9f:c2': 'Ubiquiti',
    'fc:ec:da': 'Ubiquiti',
    # TP-Link
    '40:ed:00': 'TP-Link',
    '00:31:92': 'TP-Link',
    '14:cc:20': 'TP-Link',
    '14:eb:b6': 'TP-Link',
    '18:a6:f7': 'TP-Link',
    '1c:3b:f3': 'TP-Link',
    '30:b5:c2': 'TP-Link',
    '50:c7:bf': 'TP-Link',
    '54:c8:0f': 'TP-Link',
    '5c:a6:e6': 'TP-Link',
    '60:32:b1': 'TP-Link',
    '64:66:b3': 'TP-Link',
    '6c:5a:b0': 'TP-Link',
    '70:4f:57': 'TP-Link',
    '74:da:88': 'TP-Link',
    '78:44:76': 'TP-Link',
    '90:f6:52': 'TP-Link',
    '94:d9:b3': 'TP-Link',
    '98:da:c4': 'TP-Link',
    'a0:f3:c1': 'TP-Link',
    'ac:84:c6': 'TP-Link',
    'b0:4e:26': 'TP-Link',
    'b0:95:75': 'TP-Link',
    'c0:25:e9': 'TP-Link',
    'c4:6e:1f': 'TP-Link',
    'd4:6e:0e': 'TP-Link',
    'd8:07:b6': 'TP-Link',
    'e8:de:27': 'TP-Link',
    'ec:08:6b': 'TP-Link',
    'f4:f2:6d': 'TP-Link',
    'f8:1a:67': 'TP-Link',
    # Juniper
    '00:05:85': 'Juniper',
    '00:10:db': 'Juniper',
    '00:12:1e': 'Juniper',
    '00:14:f6': 'Juniper',
    '00:17:cb': 'Juniper',
    '00:19:e2': 'Juniper',
    '00:1d:b5': 'Juniper',
    '00:21:59': 'Juniper',
    '00:22:83': 'Juniper',
    '00:23:9c': 'Juniper',
    '00:24:dc': 'Juniper',
    '00:26:88': 'Juniper',
    '28:8a:1c': 'Juniper',
    '28:c0:da': 'Juniper',
    '2c:21:31': 'Juniper',
    '2c:6b:f5': 'Juniper',
    '3c:61:04': 'Juniper',
    '3c:8a:b0': 'Juniper',
    '40:a6:77': 'Juniper',
    '44:aa:50': 'Juniper',
    '44:f4:77': 'Juniper',
    '4c:96:14': 'Juniper',
    '50:c5:8d': 'Juniper',
    '54:1e:56': 'Juniper',
    '54:4b:8c': 'Juniper',
    '5c:45:27': 'Juniper',
    '5c:5e:ab': 'Juniper',
    '64:64:9b': 'Juniper',
    '64:87:88': 'Juniper',
    '78:19:f7': 'Juniper',
    '78:fe:3d': 'Juniper',
    '80:71:1f': 'Juniper',
    '80:ac:ac': 'Juniper',
    '84:18:88': 'Juniper',
    '84:b5:9c': 'Juniper',
    '84:c1:c1': 'Juniper',
    '88:a2:5e': 'Juniper',
    '88:e0:f3': 'Juniper',
    '9c:cc:83': 'Juniper',
    'a8:d0:e5': 'Juniper',
    'ac:4b:c8': 'Juniper',
    'b0:a8:6e': 'Juniper',
    'b0:c6:9a': 'Juniper',
    'cc:e1:7f': 'Juniper',
    'd4:04:ff': 'Juniper',
    'dc:38:e1': 'Juniper',
    'ec:13:db': 'Juniper',
    'ec:3e:f7': 'Juniper',
    'f0:1c:2d': 'Juniper',
    'f4:a7:39': 'Juniper',
    'f4:b5:2f': 'Juniper',
    'f4:cc:55': 'Juniper',
    # Arista
    '00:1c:73': 'Arista',
    '28:99:3a': 'Arista',
    '44:4c:a8': 'Arista',
    # MikroTik
    '00:0c:42': 'MikroTik',
    '08:55:31': 'MikroTik',
    '18:fd:74': 'MikroTik',
    '2c:c8:1b': 'MikroTik',
    '48:8f:5a': 'MikroTik',
    '4c:5e:0c': 'MikroTik',
    '64:d1:54': 'MikroTik',
    '6c:3b:6b': 'MikroTik',
    '74:4d:28': 'MikroTik',
    'b8:69:f4': 'MikroTik',
    'c4:ad:34': 'MikroTik',
    'cc:2d:e0': 'MikroTik',
    'd4:01:c3': 'MikroTik',
    'dc:2c:6e': 'MikroTik',
    'e4:8d:8c': 'MikroTik',
    # Fortinet
    '00:09:0f': 'Fortinet',
    '00:60:6e': 'Fortinet',
    '08:5b:0e': 'Fortinet',
    '70:4c:a5': 'Fortinet',
    '90:6c:ac': 'Fortinet',
    # Synology
    '00:11:32': 'Synology',
    # QNAP
    '00:08:9b': 'QNAP',
    '24:5e:be': 'QNAP',
    '00:27:22': 'Ubiquiti',
    '04:18:d6': 'Ubiquiti',
    '24:a4:3c': 'Ubiquiti',
    '68:72:51': 'Ubiquiti',
    '78:8a:20': 'Ubiquiti',
    'b4:fb:e4': 'Ubiquiti',
    'dc:9f:db': 'Ubiquiti',
    'e0:63:da': 'Ubiquiti',
    'f0:9f:c2': 'Ubiquiti',
    'fc:ec:da': 'Ubiquiti',
    '00:0c:42': 'MikroTik',
    '4c:5e:0c': 'MikroTik',
    '64:d1:54': 'MikroTik',
    '6c:3b:6b': 'MikroTik',
    'b8:69:f4': 'MikroTik',
    'cc:2d:e0': 'MikroTik',
    'd4:01:c3': 'MikroTik',
    'e4:8d:8c': 'MikroTik',
    '00:09:0f': 'Fortinet',
    '00:60:6e': 'Arista',
    '00:1c:73': 'Arista',
    '28:99:3a': 'Arista',
    '44:4c:a8': 'Arista',
    '00:05:86': 'Juniper',
    '00:10:db': 'Juniper',
    '00:12:1e': 'Juniper',
    '00:14:f6': 'Juniper',
    '00:17:cb': 'Juniper',
    '00:19:e2': 'Juniper',
    '00:1d:b5': 'Juniper',
    '00:21:59': 'Juniper',
    '00:22:83': 'Juniper',
    '00:24:dc': 'Juniper',
    '00:26:88': 'Juniper',
    '00:31:46': 'Juniper',
    '2c:21:31': 'Juniper',
    '2c:21:72': 'Juniper',
    '2c:6b:f5': 'Juniper',
    '3c:61:04': 'Juniper',
    '3c:8a:b0': 'Juniper',
    '40:a6:77': 'Juniper',
    '44:aa:50': 'Juniper',
    '44:f4:77': 'Juniper',
    '4c:96:14': 'Juniper',
    '50:c5:8d': 'Juniper',
    '54:1e:56': 'Juniper',
    '54:4b:8c': 'Juniper',
    '54:e0:32': 'Juniper',
    '5c:45:27': 'Juniper',
    '5c:5e:ab': 'Juniper',
    '64:64:9b': 'Juniper',
    '64:87:88': 'Juniper',
    '78:19:f7': 'Juniper',
    '78:fe:3d': 'Juniper',
    '80:71:1f': 'Juniper',
    '80:ac:ac': 'Juniper',
    '84:18:88': 'Juniper',
    '84:b5:9c': 'Juniper',
    '84:c1:c1': 'Juniper',
    '88:a2:5e': 'Juniper',
    '88:e0:f3': 'Juniper',
    '9c:cc:83': 'Juniper',
    'a8:d0:e5': 'Juniper',
    'ac:4b:c8': 'Juniper',
    'b0:a8:6e': 'Juniper',
    'b0:c6:9a': 'Juniper',
    'cc:e1:7f': 'Juniper',
    'd4:04:ff': 'Juniper',
    'dc:38:e1': 'Juniper',
    'ec:13:db': 'Juniper',
    'ec:3e:f7': 'Juniper',
    'f0:1c:2d': 'Juniper',
    'f4:a7:39': 'Juniper',
    'f4:b5:2f': 'Juniper',
    'f4:cc:55': 'Juniper',
    'f8:c0:01': 'Juniper',
}

# Port to service/role mapping
PORT_SERVICE_MAP = {
    22: ('SSH', 'server'),
    23: ('Telnet', 'network'),
    80: ('HTTP', None),
    443: ('HTTPS', None),
    161: ('SNMP', None),
    162: ('SNMP Trap', None),
    3389: ('RDP', 'server'),
    5900: ('VNC', 'server'),
    5985: ('WinRM-HTTP', 'server'),
    5986: ('WinRM-HTTPS', 'server'),
    8080: ('HTTP-Alt', None),
    8443: ('HTTPS-Alt', None),
    179: ('BGP', 'network'),
    389: ('LDAP', 'server'),
    636: ('LDAPS', 'server'),
    445: ('SMB', 'server'),
    135: ('RPC', 'server'),
    139: ('NetBIOS', 'server'),
    1433: ('MSSQL', 'server'),
    3306: ('MySQL', 'server'),
    5432: ('PostgreSQL', 'server'),
    6379: ('Redis', 'server'),
    27017: ('MongoDB', 'server'),
    9100: ('Printer', 'printer'),
    515: ('LPD', 'printer'),
    631: ('IPP', 'printer'),
    554: ('RTSP', 'camera'),
    8554: ('RTSP-Alt', 'camera'),
}


@register_executor
class NetBoxAutodiscoveryExecutor(BaseExecutor):
    """
    Comprehensive network autodiscovery executor.
    
    Performs multi-stage discovery:
    1. Expand targets (CIDR, ranges, lists)
    2. Ping scan to find online hosts
    3. Port scan to identify services
    4. SNMP discovery for device details
    5. SSH discovery for Linux hosts (optional)
    6. DNS reverse lookup
    7. Vendor/model identification
    8. NetBox sync (create/update devices, interfaces, IPs)
    """
    
    executor_type = 'netbox_autodiscovery'
    
    def __init__(self):
        super().__init__()
        self.ping_executor = PingExecutor()
        self.snmp_executor = SNMPExecutor()
    
    def execute(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute comprehensive autodiscovery.
        
        Args:
            config: Discovery configuration from node parameters
        
        Returns:
            Discovery results with created/updated devices
        """
        start_time = time.time()
        
        # Initialize result structure
        result = {
            'success': False,
            'created_devices': [],
            'updated_devices': [],
            'skipped_devices': [],
            'failed_hosts': [],
            'discovery_report': {
                'total_targets': 0,
                'hosts_online': 0,
                'snmp_success': 0,
                'devices_created': 0,
                'devices_updated': 0,
                'devices_skipped': 0,
                'errors': [],
                'duration_seconds': 0,
            },
        }
        
        try:
            # Stage 1: Expand targets
            targets = self._expand_targets(config)
            result['discovery_report']['total_targets'] = len(targets)
            
            if not targets:
                result['discovery_report']['errors'].append('No targets to scan')
                return result
            
            logger.info(f"Starting autodiscovery of {len(targets)} targets")
            
            # Stage 2: Ping scan
            online_hosts = self._ping_scan(targets, config)
            result['discovery_report']['hosts_online'] = len(online_hosts)
            
            if not online_hosts:
                result['success'] = True
                result['discovery_report']['errors'].append('No hosts responded to ping')
                return result
            
            logger.info(f"Found {len(online_hosts)} online hosts")
            
            # Stage 3-7: Discover each host using ThreadPoolExecutor
            # Note: Celery parallel discovery is disabled because result.get() cannot be called within a task
            # ThreadPoolExecutor with 200 threads provides excellent parallelism within a single worker
            logger.info(f"Discovering {len(online_hosts)} hosts using ThreadPoolExecutor")
            discovered_devices = self._discover_hosts(online_hosts, config)
            
            result['discovery_report']['snmp_success'] = sum(
                1 for d in discovered_devices if d.get('snmp_success')
            )
            
            # Stage 8: Sync to NetBox
            sync_results = self._sync_to_netbox(discovered_devices, config)
            
            result['created_devices'] = sync_results['created']
            result['updated_devices'] = sync_results['updated']
            result['skipped_devices'] = sync_results['skipped']
            result['failed_hosts'] = sync_results['failed']
            
            result['discovery_report']['devices_created'] = len(sync_results['created'])
            result['discovery_report']['devices_updated'] = len(sync_results['updated'])
            result['discovery_report']['devices_skipped'] = len(sync_results['skipped'])
            result['discovery_report']['errors'].extend(sync_results['errors'])
            
            result['success'] = True
            
        except Exception as e:
            logger.exception(f"Autodiscovery failed: {e}")
            result['discovery_report']['errors'].append(str(e))
        
        result['discovery_report']['duration_seconds'] = round(time.time() - start_time, 2)
        
        return result
    
    def _expand_targets(self, config: Dict[str, Any]) -> List[str]:
        """Expand target specification to list of IPs."""
        targets = []
        target_type = config.get('target_type', 'network_range')
        exclude_ips = set()
        
        # Parse exclusions
        if config.get('exclude_ips'):
            for line in config['exclude_ips'].strip().split('\n'):
                line = line.strip()
                if line:
                    exclude_ips.add(line)
        
        if target_type == 'network_range':
            # CIDR notation
            network = config.get('network_range', '')
            if network:
                targets = self._expand_cidr(network)
        
        elif target_type == 'ip_range':
            # Start-end range
            start_ip = config.get('ip_range_start', '')
            end_ip = config.get('ip_range_end', '')
            if start_ip and end_ip:
                targets = self._expand_ip_range(start_ip, end_ip)
        
        elif target_type == 'ip_list':
            # List of IPs (supports ranges in each line)
            ip_list = config.get('ip_list', '')
            for line in ip_list.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                if '-' in line and not line.startswith('-'):
                    # Range like 10.0.0.1-10.0.0.10
                    parts = line.split('-')
                    if len(parts) == 2:
                        targets.extend(self._expand_ip_range(parts[0].strip(), parts[1].strip()))
                elif '/' in line:
                    # CIDR
                    targets.extend(self._expand_cidr(line))
                else:
                    # Single IP
                    targets.append(line)
        
        elif target_type == 'from_input':
            # From previous node (already expanded)
            input_targets = config.get('input_targets', [])
            if isinstance(input_targets, list):
                targets = input_targets
            elif isinstance(input_targets, str):
                targets = [t.strip() for t in input_targets.split('\n') if t.strip()]
        
        elif target_type == 'netbox_prefix':
            # Get IPs from NetBox prefix
            targets = self._get_netbox_prefix_ips(config.get('netbox_prefix_id'))
        
        elif target_type == 'netbox_ip_range':
            # Get IPs from NetBox IP range
            targets = self._get_netbox_ip_range_ips(config.get('netbox_ip_range_id'))
        
        # Remove exclusions
        targets = [ip for ip in targets if ip not in exclude_ips]
        
        return targets
    
    def _expand_cidr(self, network: str) -> List[str]:
        """Expand CIDR notation to list of IPs."""
        try:
            net = ipaddress.ip_network(network, strict=False)
            if net.prefixlen < 31:
                return [str(ip) for ip in net.hosts()]
            else:
                return [str(ip) for ip in net]
        except ValueError as e:
            logger.error(f"Invalid CIDR: {network} - {e}")
            return []
    
    def _expand_ip_range(self, start: str, end: str) -> List[str]:
        """Expand IP range to list of IPs."""
        try:
            start_ip = ipaddress.ip_address(start)
            end_ip = ipaddress.ip_address(end)
            
            if start_ip > end_ip:
                start_ip, end_ip = end_ip, start_ip
            
            ips = []
            current = start_ip
            while current <= end_ip:
                ips.append(str(current))
                current += 1
            
            return ips
        except ValueError as e:
            logger.error(f"Invalid IP range: {start}-{end} - {e}")
            return []
    
    def _get_netbox_prefix_ips(self, prefix_id: int) -> List[str]:
        """Get all IPs from a NetBox prefix."""
        if not prefix_id:
            return []
        
        try:
            from ..services.netbox_service import NetBoxService
            from ..api.netbox import get_netbox_settings
            
            settings = get_netbox_settings()
            service = NetBoxService(
                url=settings.get('url'),
                token=settings.get('token'),
                verify_ssl=settings.get('verify_ssl', 'true').lower() == 'true'
            )
            
            prefix = service._request('GET', f'ipam/prefixes/{prefix_id}/')
            if prefix and prefix.get('prefix'):
                return self._expand_cidr(prefix['prefix'])
        except Exception as e:
            logger.error(f"Failed to get NetBox prefix {prefix_id}: {e}")
        
        return []
    
    def _get_netbox_ip_range_ips(self, range_id: int) -> List[str]:
        """Get all IPs from a NetBox IP range."""
        if not range_id:
            return []
        
        try:
            from ..services.netbox_service import NetBoxService
            from ..api.netbox import get_netbox_settings
            
            settings = get_netbox_settings()
            service = NetBoxService(
                url=settings.get('url'),
                token=settings.get('token'),
                verify_ssl=settings.get('verify_ssl', 'true').lower() == 'true'
            )
            
            ip_range = service._request('GET', f'ipam/ip-ranges/{range_id}/')
            if ip_range:
                start = ip_range.get('start_address', '').split('/')[0]
                end = ip_range.get('end_address', '').split('/')[0]
                if start and end:
                    return self._expand_ip_range(start, end)
        except Exception as e:
            logger.error(f"Failed to get NetBox IP range {range_id}: {e}")
        
        return []
    
    def _ping_scan(self, targets: List[str], config: Dict[str, Any]) -> List[str]:
        """Ping scan to find online hosts."""
        online = []
        timeout = config.get('ping_timeout', 1)
        count = config.get('ping_count', 2)
        
        # Auto-detect optimal concurrency based on system resources
        import os
        cpu_count = os.cpu_count() or 4
        concurrency = min(cpu_count * 50, len(targets), 1000)  # 50x cores, max 1000
        logger.info(f"Ping scan using {concurrency} threads for {len(targets)} targets (CPU cores: {cpu_count})")
        
        def ping_host(ip: str) -> Optional[str]:
            try:
                result = self.ping_executor.execute(ip, config={
                    'timeout': timeout,
                    'count': count,
                })
                if result.get('reachable'):
                    return ip
            except Exception as e:
                logger.debug(f"Ping failed for {ip}: {e}")
            return None
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {executor.submit(ping_host, ip): ip for ip in targets}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    online.append(result)
        
        return online
    
    def _discover_hosts(self, hosts: List[str], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Discover detailed information for each host."""
        discovered = []
        
        # Auto-detect optimal concurrency based on system resources
        import os
        cpu_count = os.cpu_count() or 4
        concurrency = min(cpu_count * 50, len(hosts), 1000)  # 50x cores, max 1000
        logger.info(f"Host discovery using {concurrency} threads for {len(hosts)} hosts (CPU cores: {cpu_count})")
        
        def discover_host(ip: str) -> Dict[str, Any]:
            device = {
                'ip_address': ip,
                'hostname': None,
                'dns_name': None,
                'mac_address': None,
                'vendor': None,
                'model': None,
                'device_role': None,
                'os_version': None,
                'serial': None,
                'description': None,
                'location': None,
                'contact': None,
                'uptime': None,
                'open_ports': [],
                'services': [],
                'interfaces': [],
                'snmp_success': False,
                'ssh_success': False,
            }
            
            # DNS reverse lookup
            if config.get('discovery_methods', []) and 'dns' in config.get('discovery_methods', ['dns']):
                device['dns_name'] = self._dns_reverse_lookup(ip)
            
            # Get MAC from ARP cache (works for devices on same subnet)
            device['mac_address'] = self._get_mac_from_arp(ip)
            
            # Port scan
            if config.get('port_scan_enabled', True):
                ports_str = config.get('ports_to_scan', '22,23,80,135,139,161,443,445,3389,5985,5986,8080,8443')
                ports = self._parse_ports(ports_str)
                device['open_ports'] = self._port_scan(ip, ports, config)
                device['services'] = [PORT_SERVICE_MAP.get(p, (f'port-{p}', None))[0] 
                                     for p in device['open_ports']]
            
            # SNMP discovery
            if config.get('snmp_enabled', True):
                snmp_data = self._snmp_discover(ip, config)
                if snmp_data.get('success'):
                    device['snmp_success'] = True
                    device['hostname'] = snmp_data.get('hostname')
                    device['description'] = snmp_data.get('description')
                    device['location'] = snmp_data.get('location')
                    device['contact'] = snmp_data.get('contact')
                    device['uptime'] = snmp_data.get('uptime')
                    device['interfaces'] = snmp_data.get('interfaces', [])
                    
                    # Get MAC from interfaces
                    for iface in device['interfaces']:
                        if iface.get('mac_address'):
                            device['mac_address'] = iface['mac_address']
                            break
                    
                    # Identify vendor/model from sysDescr
                    vendor_info = self._identify_vendor_from_sysdescr(snmp_data.get('description', ''))
                    device['vendor'] = vendor_info.get('vendor')
                    device['model'] = vendor_info.get('model')
                    device['device_role'] = vendor_info.get('role')
                    device['os_version'] = vendor_info.get('os_version')
            
            # MAC OUI lookup if no vendor identified
            if not device['vendor'] and device['mac_address'] and config.get('use_mac_oui', True):
                device['vendor'] = self._identify_vendor_from_mac(device['mac_address'])
            
            # Identify Windows servers from port signature
            if not device['vendor'] and device['open_ports']:
                windows_ports = {135, 139, 445, 3389, 5985, 5986}
                if len(set(device['open_ports']) & windows_ports) >= 2:
                    device['vendor'] = 'Microsoft'
                    device['description'] = device.get('description') or 'Windows Server (detected via ports)'
            
            # Infer role from open ports if not set
            if not device['device_role'] and device['open_ports']:
                device['device_role'] = self._infer_role_from_ports(device['open_ports'])
            
            # Use DNS name as hostname if SNMP didn't provide one
            if not device['hostname'] and device['dns_name']:
                device['hostname'] = device['dns_name'].split('.')[0]
            
            return device
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {executor.submit(discover_host, ip): ip for ip in hosts}
            for future in as_completed(futures):
                try:
                    device = future.result()
                    discovered.append(device)
                except Exception as e:
                    ip = futures[future]
                    logger.error(f"Discovery failed for {ip}: {e}")
                    discovered.append({
                        'ip_address': ip,
                        'error': str(e),
                    })
        
        return discovered
    
    def _dns_reverse_lookup(self, ip: str) -> Optional[str]:
        """Perform reverse DNS lookup."""
        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
            return hostname
        except (socket.herror, socket.gaierror):
            return None
    
    def _get_mac_from_arp(self, ip: str) -> Optional[str]:
        """Get MAC address from ARP cache."""
        import subprocess
        
        try:
            # Try ip neigh first (Linux)
            result = subprocess.run(
                ['ip', 'neigh', 'show', ip],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                # Format: "192.168.1.1 dev eth0 lladdr aa:bb:cc:dd:ee:ff REACHABLE"
                parts = result.stdout.strip().split()
                for i, part in enumerate(parts):
                    if part == 'lladdr' and i + 1 < len(parts):
                        mac = parts[i + 1]
                        if ':' in mac and len(mac) == 17:
                            logger.debug(f"Found MAC for {ip}: {mac}")
                            return mac.lower()
            
            # Try arp command as fallback
            result = subprocess.run(
                ['arp', '-n', ip],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                # Format varies, look for MAC pattern
                import re
                mac_pattern = r'([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}'
                match = re.search(mac_pattern, result.stdout)
                if match:
                    mac = match.group(0).replace('-', ':').lower()
                    logger.debug(f"Found MAC for {ip} via arp: {mac}")
                    return mac
        except Exception as e:
            logger.debug(f"Failed to get MAC for {ip}: {e}")
        
        return None
    
    def _parse_ports(self, ports_str: str) -> List[int]:
        """Parse port specification string."""
        ports = []
        for part in ports_str.split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-')
                ports.extend(range(int(start), int(end) + 1))
            else:
                ports.append(int(part))
        return ports
    
    def _port_scan(self, ip: str, ports: List[int], config: Dict[str, Any]) -> List[int]:
        """Scan for open ports - parallel scanning for speed."""
        timeout = config.get('port_scan_timeout', 1)  # Reduced from 2s to 1s
        
        def check_port(port: int) -> Optional[int]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, port))
                sock.close()
                if result == 0:
                    return port
            except Exception:
                pass
            return None
        
        # Scan all ports in parallel
        open_ports = []
        with ThreadPoolExecutor(max_workers=len(ports)) as executor:
            futures = {executor.submit(check_port, port): port for port in ports}
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    open_ports.append(result)
        
        return sorted(open_ports)
    
    def _snmp_discover(self, ip: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Discover device info via SNMP."""
        result = {'success': False}
        
        communities = ['public']
        if config.get('snmp_communities'):
            communities = [c.strip() for c in config['snmp_communities'].split('\n') if c.strip()]
        
        timeout = config.get('snmp_timeout', 2)  # Reduced from 5s to 2s
        retries = config.get('snmp_retries', 1)  # Reduced from 2 to 1
        
        # Standard MIB-2 system OIDs
        oids = {
            'description': '1.3.6.1.2.1.1.1.0',    # sysDescr
            'vendor_oid': '1.3.6.1.2.1.1.2.0',     # sysObjectID
            'uptime': '1.3.6.1.2.1.1.3.0',         # sysUpTime
            'contact': '1.3.6.1.2.1.1.4.0',        # sysContact
            'hostname': '1.3.6.1.2.1.1.5.0',       # sysName
            'location': '1.3.6.1.2.1.1.6.0',       # sysLocation
        }
        
        # Try each community string
        for community in communities:
            snmp_config = {
                'community': community,
                'timeout': timeout,
                'retries': retries,
            }
            
            # Query all OIDs in parallel for speed
            def query_oid(field_oid):
                field, oid = field_oid
                try:
                    snmp_result = self.snmp_executor.execute(ip, oid, snmp_config)
                    if snmp_result.get('success'):
                        value = snmp_result.get('output', '')
                        if isinstance(value, bytes):
                            value = value.decode('utf-8', errors='ignore')
                        return (field, str(value).strip() if value else None, True)
                except Exception as e:
                    logger.debug(f"SNMP {field} failed for {ip}: {e}")
                return (field, None, False)
            
            with ThreadPoolExecutor(max_workers=len(oids)) as executor:
                futures = list(executor.map(query_oid, oids.items()))
                for field, value, success in futures:
                    if success:
                        result['success'] = True
                        result[field] = value
            
            if result['success']:
                # Found working community, try to get interfaces
                result['interfaces'] = self._snmp_get_interfaces(ip, snmp_config)
                break
        
        return result
    
    def _snmp_get_interfaces(self, ip: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get interface information via SNMP."""
        interfaces = []
        
        # Interface OIDs
        if_index_oid = '1.3.6.1.2.1.2.2.1.1'      # ifIndex
        if_descr_oid = '1.3.6.1.2.1.2.2.1.2'      # ifDescr
        if_type_oid = '1.3.6.1.2.1.2.2.1.3'       # ifType
        if_speed_oid = '1.3.6.1.2.1.2.2.1.5'      # ifSpeed
        if_phys_addr_oid = '1.3.6.1.2.1.2.2.1.6'  # ifPhysAddress
        if_admin_status_oid = '1.3.6.1.2.1.2.2.1.7'  # ifAdminStatus
        if_oper_status_oid = '1.3.6.1.2.1.2.2.1.8'   # ifOperStatus
        
        # This would require SNMP walk functionality
        # For now, return empty list - can be enhanced later
        
        return interfaces
    
    def _identify_vendor_from_sysdescr(self, sysdescr: str) -> Dict[str, Any]:
        """Identify vendor, model, and role from sysDescr."""
        result = {
            'vendor': None,
            'model': None,
            'role': None,
            'os_version': None,
        }
        
        if not sysdescr:
            return result
        
        for pattern, vendor, role in VENDOR_PATTERNS:
            match = re.search(pattern, sysdescr, re.IGNORECASE)
            if match:
                result['vendor'] = vendor
                result['role'] = role
                
                # Try to extract model from sysDescr
                # Common patterns: "Cisco IOS Software, C3750 Software..."
                # "Juniper Networks, Inc. ex4300-48t..."
                model_patterns = [
                    r'(?:Model|model)[:\s]+(\S+)',
                    r'(?:Cisco|Juniper|Arista|HP|Dell)\s+(\S+)',
                    r'Software,\s+(\S+)\s+Software',
                ]
                
                for mp in model_patterns:
                    model_match = re.search(mp, sysdescr, re.IGNORECASE)
                    if model_match:
                        result['model'] = model_match.group(1)
                        break
                
                # Try to extract version
                version_match = re.search(r'Version\s+([\d.]+)', sysdescr, re.IGNORECASE)
                if version_match:
                    result['os_version'] = version_match.group(1)
                
                break
        
        return result
    
    def _identify_vendor_from_mac(self, mac: str) -> Optional[str]:
        """Identify vendor from MAC address OUI."""
        if not mac:
            return None
        
        # Normalize MAC address
        mac = mac.lower().replace('-', ':')
        oui = ':'.join(mac.split(':')[:3])
        
        return MAC_OUI_VENDORS.get(oui)
    
    def _infer_role_from_ports(self, ports: List[int]) -> Optional[str]:
        """Infer device role from open ports."""
        roles = set()
        
        for port in ports:
            service_info = PORT_SERVICE_MAP.get(port)
            if service_info and service_info[1]:
                roles.add(service_info[1])
        
        # Priority: network > firewall > server > camera > printer > storage > pdu
        priority = ['network', 'firewall', 'server', 'camera', 'printer', 'storage', 'pdu']
        
        for role in priority:
            if role in roles:
                return role
        
        return None
    
    def _sync_to_netbox(self, devices: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        """Sync discovered devices to NetBox."""
        result = {
            'created': [],
            'updated': [],
            'skipped': [],
            'failed': [],
            'errors': [],
        }
        
        sync_mode = config.get('sync_mode', 'create_update')
        match_by = config.get('match_by', 'ip_or_name')
        device_naming = config.get('device_naming', 'hostname_or_ip')
        name_prefix = config.get('name_prefix', '')
        
        try:
            from ..services.netbox_service import NetBoxService
            from ..api.netbox import get_netbox_settings
            
            settings = get_netbox_settings()
            
            if not settings.get('url') or not settings.get('token'):
                result['errors'].append('NetBox not configured')
                result['failed'] = [d['ip_address'] for d in devices]
                return result
            
            service = NetBoxService(
                url=settings.get('url'),
                token=settings.get('token'),
                verify_ssl=settings.get('verify_ssl', 'true').lower() == 'true'
            )
            
            # Get defaults
            default_site = config.get('default_site') or int(settings.get('default_site_id', 0)) or None
            default_role = config.get('default_role') or int(settings.get('default_role_id', 0)) or None
            default_device_type = config.get('default_device_type') or int(settings.get('default_device_type_id', 0)) or None
            default_status = config.get('default_status', 'active')
            
            if not all([default_site, default_role, default_device_type]):
                result['errors'].append('NetBox defaults not configured (site, role, device type required)')
                result['failed'] = [d['ip_address'] for d in devices]
                return result
            
            # Process devices in parallel for speed
            def sync_single_device(device):
                device_result = {'type': None, 'data': None, 'error': None}
                try:
                    # Determine device name
                    name = self._get_device_name(device, device_naming, name_prefix)
                    if not name:
                        device_result['type'] = 'skipped'
                        device_result['data'] = {
                            'ip_address': device['ip_address'],
                            'reason': 'Could not determine device name',
                        }
                        return device_result
                    
                    # Check if device exists
                    existing = self._find_existing_device(service, device, name, match_by)
                    
                    if existing:
                        if sync_mode == 'create_only':
                            device_result['type'] = 'skipped'
                            device_result['data'] = {
                                'ip_address': device['ip_address'],
                                'name': name,
                                'reason': 'Device exists (create_only mode)',
                                'netbox_id': existing.get('id'),
                            }
                            return device_result
                        
                        # Update existing device
                        updated = self._update_device(service, existing, device, config)
                        if updated:
                            device_result['type'] = 'updated'
                            device_result['data'] = updated
                        else:
                            device_result['type'] = 'skipped'
                            device_result['data'] = {
                                'ip_address': device['ip_address'],
                                'name': name,
                                'reason': 'No changes needed',
                                'netbox_id': existing.get('id'),
                            }
                        device['netbox_device_id'] = existing.get('id')
                    else:
                        if sync_mode == 'update_only':
                            device_result['type'] = 'skipped'
                            device_result['data'] = {
                                'ip_address': device['ip_address'],
                                'name': name,
                                'reason': 'Device not found (update_only mode)',
                            }
                            return device_result
                        
                        # Create new device
                        created = self._create_device(
                            service, device, name, 
                            default_site, default_role, default_device_type, 
                            default_status, config
                        )
                        if created:
                            device_result['type'] = 'created'
                            device_result['data'] = created
                            device['netbox_device_id'] = created.get('id')
                    
                    # Create interfaces if enabled
                    if config.get('create_interfaces', True) and device.get('interfaces'):
                        self._create_interfaces(service, device, config)
                    
                    # Create IP address if enabled
                    if config.get('create_ip_addresses', True) and device.get('netbox_device_id'):
                        self._create_ip_address(service, device, config)
                    
                except Exception as e:
                    logger.error(f"Failed to sync device {device.get('ip_address')}: {e}")
                    device_result['type'] = 'failed'
                    device_result['error'] = f"{device.get('ip_address')}: {str(e)}"
                
                return device_result
            
            # Use parallel processing for NetBox sync
            import os
            cpu_count = os.cpu_count() or 4
            sync_parallel = min(cpu_count * 5, len(devices), 100)  # 5x cores for API calls
            
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=sync_parallel) as executor:
                sync_results = list(executor.map(sync_single_device, devices))
            
            for device_result in sync_results:
                if device_result['type'] == 'created':
                    result['created'].append(device_result['data'])
                elif device_result['type'] == 'updated':
                    result['updated'].append(device_result['data'])
                elif device_result['type'] == 'skipped':
                    result['skipped'].append(device_result['data'])
                elif device_result['type'] == 'failed':
                    result['failed'].append(device_result['error'].split(':')[0])
                    result['errors'].append(device_result['error'])
            
        except Exception as e:
            logger.exception(f"NetBox sync failed: {e}")
            result['errors'].append(str(e))
            result['failed'] = [d['ip_address'] for d in devices]
        
        return result
    
    def _get_device_name(self, device: Dict[str, Any], naming: str, prefix: str) -> Optional[str]:
        """Determine device name based on naming strategy."""
        if naming == 'hostname_or_ip':
            return device.get('hostname') or device.get('ip_address')
        elif naming == 'hostname_only':
            return device.get('hostname')
        elif naming == 'ip_only':
            return device.get('ip_address')
        elif naming == 'prefix_ip':
            return f"{prefix}{device.get('ip_address')}"
        elif naming == 'dns_reverse':
            return device.get('dns_name') or device.get('hostname') or device.get('ip_address')
        
        return device.get('hostname') or device.get('ip_address')
    
    def _find_existing_device(self, service, device: Dict[str, Any], name: str, match_by: str) -> Optional[Dict[str, Any]]:
        """Find existing device in NetBox."""
        try:
            if match_by == 'ip':
                # Search by IP using ipam/ip-addresses API (more reliable)
                ip_result = service._request('GET', 'ipam/ip-addresses/', params={
                    'address': device['ip_address'],
                })
                if ip_result.get('results'):
                    ip_obj = ip_result['results'][0]
                    assigned = ip_obj.get('assigned_object')
                    if assigned and assigned.get('device'):
                        device_id = assigned['device']['id']
                        found = service._request('GET', f"dcim/devices/{device_id}/")
                        if found and found.get('id'):
                            logger.info(f"Found existing device by IP {device['ip_address']}: {found.get('name')} (ID: {found.get('id')})")
                            return found
            
            elif match_by == 'name':
                result = service._request('GET', 'dcim/devices/', params={
                    'name__ie': name,  # Use exact match (case-insensitive)
                })
                logger.info(f"NetBox search by name '{name}': {len(result.get('results', []))} results")
                if result.get('results'):
                    found = result['results'][0]
                    logger.info(f"Found existing device by name: {found.get('name')} (ID: {found.get('id')})")
                    return found
            
            elif match_by == 'ip_or_name':
                # Try IP first using ipam/ip-addresses API (more reliable)
                ip_result = service._request('GET', 'ipam/ip-addresses/', params={
                    'address': device['ip_address'],
                })
                if ip_result.get('results'):
                    ip_obj = ip_result['results'][0]
                    assigned = ip_obj.get('assigned_object')
                    if assigned and assigned.get('device'):
                        device_id = assigned['device']['id']
                        found = service._request('GET', f"dcim/devices/{device_id}/")
                        if found and found.get('id'):
                            logger.info(f"Found existing device by IP {device['ip_address']}: {found.get('name')} (ID: {found.get('id')})")
                            return found
                
                # Use exact name match to avoid false positives
                result = service._request('GET', 'dcim/devices/', params={
                    'name__ie': name,  # Exact match (case-insensitive)
                })
                logger.info(f"NetBox search by name '{name}': {len(result.get('results', []))} results")
                if result.get('results'):
                    found = result['results'][0]
                    # Verify the name actually matches exactly
                    if found.get('name', '').lower() == name.lower():
                        logger.info(f"Found existing device by name: {found.get('name')} (ID: {found.get('id')})")
                        return found
                    else:
                        logger.info(f"Name mismatch: searched for '{name}', found '{found.get('name')}'")
                
                logger.info(f"No existing device found for {device['ip_address']} / {name}")
            
            elif match_by == 'mac' and device.get('mac_address'):
                # Search by MAC in interfaces
                result = service._request('GET', 'dcim/interfaces/', params={
                    'mac_address': device['mac_address'],
                })
                if result.get('results') and result['results'][0].get('device'):
                    device_id = result['results'][0]['device']['id']
                    return service._request('GET', f'dcim/devices/{device_id}/')
            
            elif match_by == 'serial' and device.get('serial'):
                result = service._request('GET', 'dcim/devices/', params={
                    'serial': device['serial'],
                })
                if result.get('results'):
                    return result['results'][0]
        
        except Exception as e:
            logger.debug(f"Error finding existing device: {e}")
        
        return None
    
    def _create_device(self, service, device: Dict[str, Any], name: str,
                      site_id: int, role_id: int, device_type_id: int,
                      status: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create new device in NetBox."""
        try:
            # Try to use discovered vendor/model to find or create proper device type
            actual_device_type_id = device_type_id
            actual_role_id = role_id
            
            if device.get('vendor') and config.get('auto_create_manufacturers', False):
                # Try to find or create manufacturer and device type
                manufacturer_id = self._get_or_create_manufacturer(service, device['vendor'])
                if manufacturer_id and device.get('model'):
                    discovered_type_id = self._get_or_create_device_type(
                        service, manufacturer_id, device['model'], config
                    )
                    if discovered_type_id:
                        actual_device_type_id = discovered_type_id
                        logger.info(f"Using discovered device type {device['model']} (ID: {discovered_type_id})")
            elif device.get('vendor'):
                # Try to find existing manufacturer and device type (don't create)
                manufacturer_id = self._find_manufacturer(service, device['vendor'])
                if manufacturer_id and device.get('model'):
                    discovered_type_id = self._find_device_type(service, manufacturer_id, device['model'])
                    if discovered_type_id:
                        actual_device_type_id = discovered_type_id
                        logger.info(f"Found existing device type {device['model']} (ID: {discovered_type_id})")
            
            # Try to use discovered role
            if device.get('device_role'):
                discovered_role_id = self._find_device_role(service, device['device_role'])
                if discovered_role_id:
                    actual_role_id = discovered_role_id
                    logger.info(f"Using discovered role {device['device_role']} (ID: {discovered_role_id})")
            
            data = {
                'name': name,
                'device_type': actual_device_type_id,
                'role': actual_role_id,
                'site': site_id,
                'status': status,
            }
            
            if device.get('serial'):
                data['serial'] = device['serial']
            
            # Use SNMP description if available
            if device.get('description'):
                data['description'] = device['description'][:200]  # NetBox limit
            
            # Add discovery tag if enabled
            if config.get('add_discovery_tag', True):
                # Try to get or create the autodiscovered tag
                try:
                    tag_result = service._request('GET', 'extras/tags/', params={'slug': 'autodiscovered'})
                    if tag_result.get('results'):
                        data['tags'] = [tag_result['results'][0]['id']]
                    else:
                        # Create the tag
                        new_tag = service._request('POST', 'extras/tags/', json={
                            'name': 'autodiscovered',
                            'slug': 'autodiscovered',
                            'color': '2196f3',
                            'description': 'Automatically discovered by OpsConductor'
                        })
                        data['tags'] = [new_tag['id']]
                except Exception as e:
                    logger.warning(f"Could not add autodiscovered tag: {e}")
            
            logger.info(f"Creating device in NetBox: {data}")
            result = service._request('POST', 'dcim/devices/', json=data)
            
            return {
                'id': result.get('id'),
                'name': name,
                'ip_address': device['ip_address'],
                'vendor': device.get('vendor'),
                'model': device.get('model'),
                'device_type': result.get('device_type', {}).get('display'),
                'device_role': result.get('role', {}).get('display'),
                'site': result.get('site', {}).get('display'),
            }
        
        except Exception as e:
            logger.error(f"Failed to create device {name}: {e}")
            raise
    
    def _update_device(self, service, existing: Dict[str, Any], device: Dict[str, Any], 
                      config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update existing device in NetBox."""
        try:
            updates = {}
            
            # Only update if we have new info
            if device.get('serial') and not existing.get('serial'):
                updates['serial'] = device['serial']
            
            if device.get('description') and not existing.get('description'):
                updates['description'] = device['description'][:200]
            
            if not updates:
                return None
            
            result = service._request('PATCH', f"dcim/devices/{existing['id']}/", json=updates)
            
            return {
                'id': existing['id'],
                'name': existing.get('name'),
                'ip_address': device['ip_address'],
                'vendor': device.get('vendor'),
                'model': device.get('model'),
                'updates': list(updates.keys()),
            }
        
        except Exception as e:
            logger.error(f"Failed to update device {existing.get('name')}: {e}")
            raise
    
    def _create_interfaces(self, service, device: Dict[str, Any], config: Dict[str, Any]):
        """Create interfaces for device in NetBox."""
        # Implementation depends on having device ID and interface data
        pass
    
    def _create_ip_address(self, service, device: Dict[str, Any], config: Dict[str, Any]):
        """Create IP address record in NetBox and assign to device."""
        if not device.get('netbox_device_id'):
            logger.warning(f"Cannot create IP address - no NetBox device ID for {device.get('ip_address')}")
            return
        
        ip_address = device.get('ip_address')
        if not ip_address:
            return
        
        try:
            # Check if IP already exists
            existing_ip = service._request('GET', 'ipam/ip-addresses/', params={
                'address': ip_address,
            })
            
            if existing_ip.get('results'):
                # IP exists, update it to assign to this device
                ip_id = existing_ip['results'][0]['id']
                logger.info(f"IP {ip_address} already exists (ID: {ip_id}), updating assignment")
                
                # Create or get an interface for the device
                interface_id = self._get_or_create_interface(service, device)
                
                if interface_id:
                    service._request('PATCH', f'ipam/ip-addresses/{ip_id}/', json={
                        'assigned_object_type': 'dcim.interface',
                        'assigned_object_id': interface_id,
                    })
                    
                    # Set as primary IP on device
                    service._request('PATCH', f"dcim/devices/{device['netbox_device_id']}/", json={
                        'primary_ip4': ip_id,
                    })
                    logger.info(f"Assigned existing IP {ip_address} to device {device['netbox_device_id']}")
            else:
                # Create new IP address
                interface_id = self._get_or_create_interface(service, device)
                
                ip_data = {
                    'address': f"{ip_address}/24",  # Default to /24, could be configurable
                    'status': 'active',
                    'description': f"Discovered by OpsConductor autodiscovery",
                }
                
                if interface_id:
                    ip_data['assigned_object_type'] = 'dcim.interface'
                    ip_data['assigned_object_id'] = interface_id
                
                new_ip = service._request('POST', 'ipam/ip-addresses/', json=ip_data)
                logger.info(f"Created IP address {ip_address} (ID: {new_ip.get('id')})")
                
                # Set as primary IP on device
                if new_ip.get('id'):
                    service._request('PATCH', f"dcim/devices/{device['netbox_device_id']}/", json={
                        'primary_ip4': new_ip['id'],
                    })
                    logger.info(f"Set {ip_address} as primary IP for device {device['netbox_device_id']}")
        
        except Exception as e:
            logger.error(f"Failed to create/assign IP address {ip_address}: {e}")
    
    def _find_manufacturer(self, service, vendor_name: str) -> Optional[int]:
        """Find manufacturer by name."""
        try:
            result = service._request('GET', 'dcim/manufacturers/', params={
                'name__ic': vendor_name,  # Case-insensitive contains
            })
            if result.get('results'):
                return result['results'][0]['id']
        except Exception as e:
            logger.debug(f"Error finding manufacturer {vendor_name}: {e}")
        return None
    
    def _get_or_create_manufacturer(self, service, vendor_name: str) -> Optional[int]:
        """Find or create manufacturer."""
        # First try to find existing
        manufacturer_id = self._find_manufacturer(service, vendor_name)
        if manufacturer_id:
            return manufacturer_id
        
        # Create new manufacturer
        try:
            slug = vendor_name.lower().replace(' ', '-').replace('/', '-')[:50]
            result = service._request('POST', 'dcim/manufacturers/', json={
                'name': vendor_name,
                'slug': slug,
            })
            logger.info(f"Created manufacturer {vendor_name} (ID: {result.get('id')})")
            return result.get('id')
        except Exception as e:
            logger.error(f"Failed to create manufacturer {vendor_name}: {e}")
        return None
    
    def _find_device_type(self, service, manufacturer_id: int, model: str) -> Optional[int]:
        """Find device type by manufacturer and model."""
        try:
            result = service._request('GET', 'dcim/device-types/', params={
                'manufacturer_id': manufacturer_id,
                'model__ic': model,  # Case-insensitive contains
            })
            if result.get('results'):
                return result['results'][0]['id']
        except Exception as e:
            logger.debug(f"Error finding device type {model}: {e}")
        return None
    
    def _get_or_create_device_type(self, service, manufacturer_id: int, model: str, config: Dict[str, Any]) -> Optional[int]:
        """Find or create device type."""
        # First try to find existing
        device_type_id = self._find_device_type(service, manufacturer_id, model)
        if device_type_id:
            return device_type_id
        
        if not config.get('auto_create_device_types', False):
            return None
        
        # Create new device type
        try:
            slug = model.lower().replace(' ', '-').replace('/', '-')[:50]
            result = service._request('POST', 'dcim/device-types/', json={
                'manufacturer': manufacturer_id,
                'model': model,
                'slug': slug,
            })
            logger.info(f"Created device type {model} (ID: {result.get('id')})")
            return result.get('id')
        except Exception as e:
            logger.error(f"Failed to create device type {model}: {e}")
        return None
    
    def _find_device_role(self, service, role_name: str) -> Optional[int]:
        """Find device role by name."""
        # Map discovered role types to NetBox role names
        role_mapping = {
            'network': ['Router', 'Switch', 'Network', 'Backbone'],
            'firewall': ['Firewall', 'Security'],
            'server': ['Server', 'Virtualization Host', 'Compute'],
            'storage': ['Storage', 'NAS', 'SAN'],
            'camera': ['Camera', 'Surveillance'],
            'printer': ['Printer'],
            'pdu': ['PDU', 'Power'],
        }
        
        try:
            # First try exact match
            result = service._request('GET', 'dcim/device-roles/', params={
                'name__ic': role_name,
            })
            if result.get('results'):
                return result['results'][0]['id']
            
            # Try mapped names
            search_terms = role_mapping.get(role_name.lower(), [role_name])
            for term in search_terms:
                result = service._request('GET', 'dcim/device-roles/', params={
                    'name__ic': term,
                })
                if result.get('results'):
                    return result['results'][0]['id']
        except Exception as e:
            logger.debug(f"Error finding device role {role_name}: {e}")
        return None
    
    def _get_or_create_interface(self, service, device: Dict[str, Any]) -> Optional[int]:
        """Get or create a management interface for the device."""
        device_id = device.get('netbox_device_id')
        if not device_id:
            return None
        
        try:
            # Check if device has any interfaces
            interfaces = service._request('GET', 'dcim/interfaces/', params={
                'device_id': device_id,
            })
            
            if interfaces.get('results'):
                # Return first interface
                return interfaces['results'][0]['id']
            
            # Create a management interface
            new_interface = service._request('POST', 'dcim/interfaces/', json={
                'device': device_id,
                'name': 'mgmt0',
                'type': 'virtual',
                'description': 'Management interface (autodiscovered)',
            })
            
            logger.info(f"Created management interface for device {device_id}")
            return new_interface.get('id')
        
        except Exception as e:
            logger.error(f"Failed to get/create interface for device {device_id}: {e}")
            return None
