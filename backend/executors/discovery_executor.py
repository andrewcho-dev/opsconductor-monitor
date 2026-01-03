"""
Discovery Executor.

Performs network discovery (ping sweep + SNMP probe) and syncs results to NetBox.
"""

import logging
import ipaddress
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base import BaseExecutor
from .registry import register_executor
from .ping_executor import PingExecutor
from .snmp_executor import SNMPExecutor

logger = logging.getLogger(__name__)


@register_executor
class DiscoveryExecutor(BaseExecutor):
    """
    Executor for network discovery operations.
    
    Discovers active devices via ping, probes them with SNMP,
    and optionally syncs results to NetBox.
    """
    
    executor_type = 'discovery'
    
    def __init__(self):
        super().__init__()
        self.ping_executor = PingExecutor()
        self.snmp_executor = SNMPExecutor()
    
    def execute(self, target: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute discovery on a single target IP.
        
        Args:
            target: IP address to discover
            config: Discovery configuration
                - ping_timeout: Ping timeout in seconds (default: 2)
                - snmp_community: SNMP community string (default: public)
                - snmp_timeout: SNMP timeout in seconds (default: 3)
                - sync_to_netbox: Whether to sync to NetBox (default: True)
                - netbox_site_id: NetBox site ID for new devices
                - netbox_role_id: NetBox role ID for new devices
                - netbox_device_type_id: NetBox device type ID for new devices
        
        Returns:
            Discovery result dictionary
        """
        config = config or {}
        
        result = {
            'target': target,
            'ping_status': 'unknown',
            'snmp_status': 'unknown',
            'hostname': None,
            'description': None,
            'vendor': None,
            'model': None,
            'serial': None,
            'location': None,
            'contact': None,
            'uptime': None,
            'netbox_synced': False,
        }
        
        # Step 1: Ping check
        ping_result = self.ping_executor.execute(target, config={
            'timeout': config.get('ping_timeout', 2),
            'count': 1,
        })
        
        result['ping_status'] = 'online' if ping_result.get('reachable') else 'offline'
        result['response_time_ms'] = ping_result.get('response_time_ms')
        
        if not ping_result.get('reachable'):
            # Device not reachable, skip SNMP
            result['snmp_status'] = 'unreachable'
            return result
        
        # Step 2: SNMP probe
        snmp_config = {
            'community': config.get('snmp_community', 'public'),
            'timeout': config.get('snmp_timeout', 3),
        }
        
        # Try to get system info via SNMP
        snmp_data = self._probe_snmp(target, snmp_config)
        
        if snmp_data.get('success'):
            result['snmp_status'] = 'responding'
            result['hostname'] = snmp_data.get('hostname')
            result['description'] = snmp_data.get('description')
            result['location'] = snmp_data.get('location')
            result['contact'] = snmp_data.get('contact')
            result['uptime'] = snmp_data.get('uptime')
            result['vendor_oid'] = snmp_data.get('vendor_oid')
            
            # Try to determine vendor from sysObjectID
            vendor_info = self._identify_vendor(snmp_data.get('vendor_oid'))
            result['vendor'] = vendor_info.get('vendor')
            result['model'] = vendor_info.get('model')
        else:
            result['snmp_status'] = 'no_response'
        
        # Step 3: Sync to NetBox if enabled
        if config.get('sync_to_netbox', True):
            netbox_result = self._sync_to_netbox(result, config)
            result['netbox_synced'] = netbox_result.get('success', False)
            result['netbox_device_id'] = netbox_result.get('device_id')
            result['netbox_error'] = netbox_result.get('error')
        
        return result
    
    def execute_range(self, network: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute discovery on a network range.
        
        Args:
            network: Network CIDR (e.g., '192.168.1.0/24')
            config: Discovery configuration
                - max_workers: Max concurrent workers (default: 20)
                - skip_network_broadcast: Skip network/broadcast addresses (default: True)
        
        Returns:
            Discovery results for all IPs
        """
        config = config or {}
        skip_network_broadcast = config.get('skip_network_broadcast', True)
        
        # Auto-detect optimal concurrency based on system resources
        import os
        cpu_count = os.cpu_count() or 4
        
        try:
            net = ipaddress.ip_network(network, strict=False)
        except ValueError as e:
            return {
                'success': False,
                'error': f'Invalid network: {e}',
                'network': network,
            }
        
        # Generate list of IPs to scan
        if skip_network_broadcast and net.prefixlen < 31:
            # Skip network and broadcast addresses for /30 and larger
            ips = [str(ip) for ip in net.hosts()]
        else:
            ips = [str(ip) for ip in net]
        
        results = {
            'success': True,
            'network': network,
            'total_ips': len(ips),
            'online_count': 0,
            'snmp_responding_count': 0,
            'netbox_synced_count': 0,
            'devices': [],
        }
        
        # Execute discovery in parallel with optimal concurrency
        max_workers = min(cpu_count * 50, len(ips), 1000)  # 50x cores, max 1000
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ip = {
                executor.submit(self.execute, ip, config): ip 
                for ip in ips
            }
            
            for future in as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    device_result = future.result()
                    results['devices'].append(device_result)
                    
                    if device_result.get('ping_status') == 'online':
                        results['online_count'] += 1
                    if device_result.get('snmp_status') == 'responding':
                        results['snmp_responding_count'] += 1
                    if device_result.get('netbox_synced'):
                        results['netbox_synced_count'] += 1
                        
                except Exception as e:
                    logger.error(f"Discovery failed for {ip}: {e}")
                    results['devices'].append({
                        'target': ip,
                        'error': str(e),
                    })
        
        # Sort by IP
        results['devices'].sort(key=lambda d: ipaddress.ip_address(d.get('target', '0.0.0.0')))
        
        return results
    
    def _probe_snmp(self, target: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Probe device with SNMP to get system info."""
        result = {'success': False}
        
        # Standard MIB-2 system OIDs
        oids = {
            'description': '1.3.6.1.2.1.1.1.0',    # sysDescr
            'vendor_oid': '1.3.6.1.2.1.1.2.0',     # sysObjectID
            'uptime': '1.3.6.1.2.1.1.3.0',         # sysUpTime
            'contact': '1.3.6.1.2.1.1.4.0',        # sysContact
            'hostname': '1.3.6.1.2.1.1.5.0',       # sysName
            'location': '1.3.6.1.2.1.1.6.0',       # sysLocation
        }
        
        for field, oid in oids.items():
            try:
                snmp_result = self.snmp_executor.execute(target, oid, config)
                if snmp_result.get('success'):
                    result['success'] = True
                    value = snmp_result.get('output', '')
                    
                    # Clean up the value
                    if isinstance(value, bytes):
                        value = value.decode('utf-8', errors='ignore')
                    
                    result[field] = str(value).strip() if value else None
            except Exception as e:
                logger.debug(f"SNMP {field} failed for {target}: {e}")
        
        return result
    
    def _identify_vendor(self, sys_object_id: str) -> Dict[str, str]:
        """Identify vendor from sysObjectID."""
        if not sys_object_id:
            return {}
        
        # Common vendor OID prefixes
        vendor_map = {
            '1.3.6.1.4.1.9.': {'vendor': 'Cisco'},
            '1.3.6.1.4.1.2636.': {'vendor': 'Juniper'},
            '1.3.6.1.4.1.25506.': {'vendor': 'H3C/HPE'},
            '1.3.6.1.4.1.11.': {'vendor': 'HP'},
            '1.3.6.1.4.1.2011.': {'vendor': 'Huawei'},
            '1.3.6.1.4.1.6527.': {'vendor': 'Nokia/Alcatel-Lucent'},
            '1.3.6.1.4.1.1991.': {'vendor': 'Brocade/Foundry'},
            '1.3.6.1.4.1.30065.': {'vendor': 'Arista'},
            '1.3.6.1.4.1.12356.': {'vendor': 'Fortinet'},
            '1.3.6.1.4.1.9303.': {'vendor': 'Palo Alto'},
            '1.3.6.1.4.1.8072.': {'vendor': 'Net-SNMP (Linux)'},
            '1.3.6.1.4.1.311.': {'vendor': 'Microsoft'},
            '1.3.6.1.4.1.232.': {'vendor': 'HPE/Compaq'},
            '1.3.6.1.4.1.674.': {'vendor': 'Dell'},
            '1.3.6.1.4.1.2021.': {'vendor': 'UCD-SNMP'},
        }
        
        for prefix, info in vendor_map.items():
            if sys_object_id.startswith(prefix):
                return info
        
        return {'vendor': 'Unknown'}
    
    def _sync_to_netbox(self, device_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Sync discovered device to NetBox."""
        try:
            from ..services.netbox_service import NetBoxService, NetBoxError
            from ..api.netbox import get_netbox_settings
            
            # Get NetBox settings
            settings = get_netbox_settings()
            
            if not settings.get('url') or not settings.get('token'):
                return {
                    'success': False,
                    'error': 'NetBox not configured',
                }
            
            service = NetBoxService(
                url=settings.get('url'),
                token=settings.get('token'),
                verify_ssl=settings.get('verify_ssl', 'true').lower() == 'true'
            )
            
            # Get defaults from config or settings
            site_id = config.get('netbox_site_id') or int(settings.get('default_site_id', 0)) or None
            role_id = config.get('netbox_role_id') or int(settings.get('default_role_id', 0)) or None
            device_type_id = config.get('netbox_device_type_id') or int(settings.get('default_device_type_id', 0)) or None
            
            if not all([site_id, role_id, device_type_id]):
                return {
                    'success': False,
                    'error': 'NetBox defaults not configured (site, role, device type required)',
                }
            
            result = service.upsert_discovered_device(
                ip_address=device_data['target'],
                hostname=device_data.get('hostname'),
                description=device_data.get('description'),
                vendor=device_data.get('vendor'),
                serial=device_data.get('serial'),
                site_id=site_id,
                role_id=role_id,
                device_type_id=device_type_id,
                tags=['discovered', 'auto-discovered'],
                custom_fields={
                    'snmp_location': device_data.get('location'),
                    'snmp_contact': device_data.get('contact'),
                    'last_discovered': device_data.get('discovered_at'),
                } if device_data.get('location') or device_data.get('contact') else None,
            )
            
            return {
                'success': True,
                'device_id': result.get('device', {}).get('id'),
                'created': result.get('created', False),
            }
            
        except Exception as e:
            logger.error(f"NetBox sync failed for {device_data.get('target')}: {e}")
            return {
                'success': False,
                'error': str(e),
            }
