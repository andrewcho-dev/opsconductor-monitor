"""
SNMP Walker Executor

Comprehensive SNMP walking for network discovery.
Collects interfaces, routing, ARP, neighbors, and system information.
"""

import subprocess
import re
import time
import concurrent.futures
from typing import Dict, List, Any, Optional, Tuple
from ..logging_service import get_logger, LogSource

logger = get_logger(__name__, LogSource.SNMP)

# Standard OID definitions
OIDS = {
    # System MIB
    'sysDescr': '1.3.6.1.2.1.1.1.0',
    'sysObjectID': '1.3.6.1.2.1.1.2.0',
    'sysUpTime': '1.3.6.1.2.1.1.3.0',
    'sysContact': '1.3.6.1.2.1.1.4.0',
    'sysName': '1.3.6.1.2.1.1.5.0',
    'sysLocation': '1.3.6.1.2.1.1.6.0',
    'sysServices': '1.3.6.1.2.1.1.7.0',
    
    # Interface tables
    'ifTable': '1.3.6.1.2.1.2.2',
    'ifXTable': '1.3.6.1.2.1.31.1.1',
    'ifDescr': '1.3.6.1.2.1.2.2.1.2',
    'ifType': '1.3.6.1.2.1.2.2.1.3',
    'ifMtu': '1.3.6.1.2.1.2.2.1.4',
    'ifSpeed': '1.3.6.1.2.1.2.2.1.5',
    'ifPhysAddress': '1.3.6.1.2.1.2.2.1.6',
    'ifAdminStatus': '1.3.6.1.2.1.2.2.1.7',
    'ifOperStatus': '1.3.6.1.2.1.2.2.1.8',
    'ifName': '1.3.6.1.2.1.31.1.1.1.1',
    'ifHighSpeed': '1.3.6.1.2.1.31.1.1.1.15',
    'ifAlias': '1.3.6.1.2.1.31.1.1.1.18',
    
    # IP Address table
    'ipAddrTable': '1.3.6.1.2.1.4.20',
    'ipAdEntAddr': '1.3.6.1.2.1.4.20.1.1',
    'ipAdEntIfIndex': '1.3.6.1.2.1.4.20.1.2',
    'ipAdEntNetMask': '1.3.6.1.2.1.4.20.1.3',
    
    # ARP/Neighbor table
    'ipNetToMediaTable': '1.3.6.1.2.1.4.22',
    'ipNetToMediaPhysAddress': '1.3.6.1.2.1.4.22.1.2',
    'ipNetToMediaNetAddress': '1.3.6.1.2.1.4.22.1.3',
    'ipNetToMediaType': '1.3.6.1.2.1.4.22.1.4',
    
    # IP Routing table
    'ipRouteTable': '1.3.6.1.2.1.4.21',
    'ipRouteDest': '1.3.6.1.2.1.4.21.1.1',
    'ipRouteIfIndex': '1.3.6.1.2.1.4.21.1.2',
    'ipRouteNextHop': '1.3.6.1.2.1.4.21.1.7',
    'ipRouteType': '1.3.6.1.2.1.4.21.1.8',
    'ipRouteMask': '1.3.6.1.2.1.4.21.1.11',
    
    # VLAN table (802.1Q)
    'dot1qVlanStaticTable': '1.3.6.1.2.1.17.7.1.4.3',
    'dot1qVlanStaticName': '1.3.6.1.2.1.17.7.1.4.3.1.1',
    
    # LLDP
    'lldpRemTable': '1.0.8802.1.1.2.1.4.1',
    'lldpRemChassisId': '1.0.8802.1.1.2.1.4.1.1.5',
    'lldpRemPortId': '1.0.8802.1.1.2.1.4.1.1.7',
    'lldpRemPortDesc': '1.0.8802.1.1.2.1.4.1.1.8',
    'lldpRemSysName': '1.0.8802.1.1.2.1.4.1.1.9',
    'lldpRemSysDesc': '1.0.8802.1.1.2.1.4.1.1.10',
    'lldpRemManAddr': '1.0.8802.1.1.2.1.4.2.1.4',
    
    # CDP (Cisco)
    'cdpCacheTable': '1.3.6.1.4.1.9.9.23.1.2.1',
    'cdpCacheDeviceId': '1.3.6.1.4.1.9.9.23.1.2.1.1.6',
    'cdpCacheDevicePort': '1.3.6.1.4.1.9.9.23.1.2.1.1.7',
    'cdpCachePlatform': '1.3.6.1.4.1.9.9.23.1.2.1.1.8',
    'cdpCacheAddress': '1.3.6.1.4.1.9.9.23.1.2.1.1.4',
    
    # Entity MIB
    'entPhysicalTable': '1.3.6.1.2.1.47.1.1.1',
    'entPhysicalDescr': '1.3.6.1.2.1.47.1.1.1.1.2',
    'entPhysicalClass': '1.3.6.1.2.1.47.1.1.1.1.5',
    'entPhysicalName': '1.3.6.1.2.1.47.1.1.1.1.7',
    'entPhysicalSerialNum': '1.3.6.1.2.1.47.1.1.1.1.11',
    'entPhysicalModelName': '1.3.6.1.2.1.47.1.1.1.1.13',
    
    # BGP
    'bgpPeerTable': '1.3.6.1.2.1.15.3',
    'bgpPeerState': '1.3.6.1.2.1.15.3.1.2',
    'bgpPeerRemoteAs': '1.3.6.1.2.1.15.3.1.9',
    
    # OSPF
    'ospfNbrTable': '1.3.6.1.2.1.14.10.1',
    'ospfNbrIpAddr': '1.3.6.1.2.1.14.10.1.1',
    'ospfNbrState': '1.3.6.1.2.1.14.10.1.6',
}


class SNMPWalkerExecutor:
    """Executor for comprehensive SNMP walking."""
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """Execute the SNMP walker based on command."""
        params = node.get('data', {}).get('parameters', {})
        command = node.get('data', {}).get('execution', {}).get('command', 'walk.comprehensive')
        
        if command == 'walk.comprehensive':
            return self._walk_comprehensive(params, context)
        elif command == 'walk.interfaces':
            return self._walk_interfaces(params, context)
        elif command == 'walk.neighbors':
            return self._walk_neighbors(params, context)
        else:
            return {'error': f'Unknown command: {command}', 'success': False}
    
    def _get_targets(self, params: Dict, context: Dict) -> List[Dict]:
        """Extract targets from parameters or context."""
        target_source = params.get('target_source', 'from_autodiscovery')
        targets = []
        
        if target_source == 'ip_list':
            ip_list = params.get('ip_list', '')
            for line in ip_list.strip().split('\n'):
                ip = line.strip()
                if ip:
                    targets.append({
                        'ip_address': ip,
                        'community': params.get('snmp_community', 'public'),
                    })
        elif target_source == 'from_input':
            input_targets = context.get('inputs', {}).get('targets', [])
            if not input_targets:
                input_targets = context.get('inputs', {}).get('snmp_hosts', [])
            
            for t in input_targets:
                if isinstance(t, str):
                    targets.append({
                        'ip_address': t,
                        'community': params.get('snmp_community', 'public'),
                    })
                elif isinstance(t, dict):
                    targets.append({
                        'ip_address': t.get('ip_address') or t.get('primary_ip') or t.get('ip'),
                        'community': t.get('snmp_community') or t.get('community') or params.get('snmp_community', 'public'),
                        'device_id': t.get('id'),
                        'device_name': t.get('name'),
                    })
        else:  # from_autodiscovery
            # Try to get from autodiscovery outputs
            created = context.get('inputs', {}).get('targets', [])
            if not created:
                created = context.get('variables', {}).get('created_devices', [])
            if not created:
                created = context.get('variables', {}).get('snmp_active', [])
            
            for device in created:
                if isinstance(device, dict):
                    ip = device.get('ip_address') or device.get('primary_ip', {}).get('address', '').split('/')[0]
                    if ip:
                        targets.append({
                            'ip_address': ip,
                            'community': device.get('snmp_community') or params.get('snmp_community', 'public'),
                            'device_id': device.get('id'),
                            'device_name': device.get('name'),
                        })
                elif isinstance(device, str):
                    targets.append({
                        'ip_address': device,
                        'community': params.get('snmp_community', 'public'),
                    })
        
        return targets
    
    def _walk_comprehensive(self, params: Dict, context: Dict) -> Dict:
        """Perform comprehensive SNMP walk on all targets."""
        start_time = time.time()
        targets = self._get_targets(params, context)
        
        if not targets:
            return {
                'error': 'No targets specified',
                'success': False,
                'walk_results': [],
            }
        
        walk_tables = params.get('walk_tables', ['system', 'interfaces', 'ip_addresses', 'arp'])
        timeout = params.get('timeout_seconds', 30)
        max_results = params.get('max_results_per_table', 500)
        parallel = params.get('parallel_walks', 5)
        version = params.get('snmp_version', '2c')
        
        logger.info(
            f"Starting comprehensive SNMP walk on {len(targets)} targets",
            category='walk',
            details={'tables': walk_tables, 'parallel': parallel}
        )
        
        walk_results = []
        failed_hosts = []
        all_interfaces = []
        all_neighbors = []
        
        # Walk targets in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as executor:
            future_to_target = {
                executor.submit(
                    self._walk_single_target,
                    target,
                    walk_tables,
                    version,
                    timeout,
                    max_results
                ): target
                for target in targets
            }
            
            for future in concurrent.futures.as_completed(future_to_target):
                target = future_to_target[future]
                try:
                    result = future.result()
                    if result.get('success'):
                        walk_results.append(result)
                        all_interfaces.extend(result.get('interfaces', []))
                        all_neighbors.extend(result.get('lldp_neighbors', []))
                        all_neighbors.extend(result.get('cdp_neighbors', []))
                    else:
                        failed_hosts.append(target['ip_address'])
                except Exception as e:
                    logger.error(f"Walk failed for {target['ip_address']}: {e}")
                    failed_hosts.append(target['ip_address'])
        
        duration = time.time() - start_time
        
        summary = {
            'total_targets': len(targets),
            'successful': len(walk_results),
            'failed': len(failed_hosts),
            'total_interfaces': len(all_interfaces),
            'total_neighbors': len(all_neighbors),
            'duration_seconds': round(duration, 2),
        }
        
        logger.info(
            f"SNMP walk complete: {summary['successful']}/{summary['total_targets']} successful",
            category='walk',
            details=summary
        )
        
        return {
            'success': len(walk_results) > 0,
            'walk_results': walk_results,
            'interfaces_discovered': all_interfaces,
            'neighbors_discovered': all_neighbors,
            'failed_hosts': failed_hosts,
            'summary': summary,
        }
    
    def _walk_single_target(
        self,
        target: Dict,
        walk_tables: List[str],
        version: str,
        timeout: int,
        max_results: int
    ) -> Dict:
        """Walk a single target for all requested tables."""
        ip = target['ip_address']
        community = target.get('community', 'public')
        
        result = {
            'ip_address': ip,
            'device_id': target.get('device_id'),
            'device_name': target.get('device_name'),
            'success': False,
        }
        
        try:
            # System info
            if 'system' in walk_tables:
                result['system_info'] = self._get_system_info(ip, community, version, timeout)
                result['hostname'] = result['system_info'].get('sysName', '')
            
            # Interfaces
            if 'interfaces' in walk_tables:
                result['interfaces'] = self._walk_interfaces_table(ip, community, version, timeout, max_results)
            
            # IP Addresses
            if 'ip_addresses' in walk_tables:
                result['ip_addresses'] = self._walk_ip_addresses(ip, community, version, timeout, max_results)
            
            # ARP table
            if 'arp' in walk_tables:
                result['arp_table'] = self._walk_arp_table(ip, community, version, timeout, max_results)
            
            # Routing table
            if 'routing' in walk_tables:
                result['routing_table'] = self._walk_routing_table(ip, community, version, timeout, max_results)
            
            # VLANs
            if 'vlans' in walk_tables:
                result['vlans'] = self._walk_vlans(ip, community, version, timeout, max_results)
            
            # LLDP neighbors
            if 'lldp' in walk_tables:
                result['lldp_neighbors'] = self._walk_lldp(ip, community, version, timeout, max_results)
            
            # CDP neighbors
            if 'cdp' in walk_tables:
                result['cdp_neighbors'] = self._walk_cdp(ip, community, version, timeout, max_results)
            
            # Entity MIB
            if 'entity' in walk_tables:
                result['entity_info'] = self._walk_entity(ip, community, version, timeout, max_results)
            
            # BGP peers
            if 'bgp' in walk_tables:
                result['bgp_peers'] = self._walk_bgp(ip, community, version, timeout, max_results)
            
            # OSPF neighbors
            if 'ospf' in walk_tables:
                result['ospf_neighbors'] = self._walk_ospf(ip, community, version, timeout, max_results)
            
            result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error walking {ip}: {e}")
        
        return result
    
    def _snmp_get(self, ip: str, community: str, oid: str, version: str, timeout: int) -> Optional[str]:
        """Perform SNMP GET for a single OID."""
        version_flag = f'-v{version}'
        try:
            result = subprocess.run(
                ['snmpget', '-Oqv', version_flag, '-c', community, '-t', str(timeout), ip, oid],
                capture_output=True,
                text=True,
                timeout=timeout + 5
            )
            if result.returncode == 0:
                return result.stdout.strip().strip('"')
            return None
        except Exception:
            return None
    
    def _snmp_walk(self, ip: str, community: str, oid: str, version: str, timeout: int, max_results: int) -> List[Tuple[str, str]]:
        """Perform SNMP WALK and return list of (oid, value) tuples."""
        version_flag = f'-v{version}'
        results = []
        try:
            result = subprocess.run(
                ['snmpwalk', '-Oqn', version_flag, '-c', community, '-t', str(timeout), ip, oid],
                capture_output=True,
                text=True,
                timeout=timeout + 10
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n')[:max_results]:
                    if ' ' in line:
                        parts = line.split(' ', 1)
                        oid_part = parts[0].strip()
                        value = parts[1].strip().strip('"') if len(parts) > 1 else ''
                        results.append((oid_part, value))
        except Exception as e:
            logger.warning(f"SNMP walk failed for {ip} OID {oid}: {e}")
        return results
    
    def _get_system_info(self, ip: str, community: str, version: str, timeout: int) -> Dict:
        """Get system MIB information."""
        info = {}
        for name, oid in [
            ('sysDescr', OIDS['sysDescr']),
            ('sysObjectID', OIDS['sysObjectID']),
            ('sysUpTime', OIDS['sysUpTime']),
            ('sysContact', OIDS['sysContact']),
            ('sysName', OIDS['sysName']),
            ('sysLocation', OIDS['sysLocation']),
        ]:
            value = self._snmp_get(ip, community, oid, version, timeout)
            if value:
                info[name] = value
        return info
    
    def _walk_interfaces_table(self, ip: str, community: str, version: str, timeout: int, max_results: int) -> List[Dict]:
        """Walk interface tables and combine data."""
        interfaces = {}
        
        # Get interface descriptions
        for oid, value in self._snmp_walk(ip, community, OIDS['ifDescr'], version, timeout, max_results):
            idx = oid.split('.')[-1]
            if idx not in interfaces:
                interfaces[idx] = {'index': int(idx)}
            interfaces[idx]['description'] = value
        
        # Get interface names (ifXTable)
        for oid, value in self._snmp_walk(ip, community, OIDS['ifName'], version, timeout, max_results):
            idx = oid.split('.')[-1]
            if idx in interfaces:
                interfaces[idx]['name'] = value
        
        # Get interface types
        for oid, value in self._snmp_walk(ip, community, OIDS['ifType'], version, timeout, max_results):
            idx = oid.split('.')[-1]
            if idx in interfaces:
                interfaces[idx]['type'] = value
        
        # Get MAC addresses
        for oid, value in self._snmp_walk(ip, community, OIDS['ifPhysAddress'], version, timeout, max_results):
            idx = oid.split('.')[-1]
            if idx in interfaces and value:
                # Convert hex string to MAC format
                mac = self._format_mac(value)
                if mac:
                    interfaces[idx]['mac_address'] = mac
        
        # Get admin status
        for oid, value in self._snmp_walk(ip, community, OIDS['ifAdminStatus'], version, timeout, max_results):
            idx = oid.split('.')[-1]
            if idx in interfaces:
                interfaces[idx]['admin_status'] = 'up' if value == '1' else 'down'
        
        # Get oper status
        for oid, value in self._snmp_walk(ip, community, OIDS['ifOperStatus'], version, timeout, max_results):
            idx = oid.split('.')[-1]
            if idx in interfaces:
                interfaces[idx]['oper_status'] = 'up' if value == '1' else 'down'
        
        # Get speed (ifHighSpeed in Mbps)
        for oid, value in self._snmp_walk(ip, community, OIDS['ifHighSpeed'], version, timeout, max_results):
            idx = oid.split('.')[-1]
            if idx in interfaces:
                try:
                    interfaces[idx]['speed_mbps'] = int(value)
                except ValueError:
                    pass
        
        # Get alias/description
        for oid, value in self._snmp_walk(ip, community, OIDS['ifAlias'], version, timeout, max_results):
            idx = oid.split('.')[-1]
            if idx in interfaces and value:
                interfaces[idx]['alias'] = value
        
        # Add source IP to each interface
        result = list(interfaces.values())
        for iface in result:
            iface['source_ip'] = ip
        
        return result
    
    def _walk_ip_addresses(self, ip: str, community: str, version: str, timeout: int, max_results: int) -> List[Dict]:
        """Walk IP address table."""
        addresses = {}
        
        # Get IP addresses
        for oid, value in self._snmp_walk(ip, community, OIDS['ipAdEntAddr'], version, timeout, max_results):
            addr = value
            addresses[addr] = {'address': addr}
        
        # Get interface index for each IP
        for oid, value in self._snmp_walk(ip, community, OIDS['ipAdEntIfIndex'], version, timeout, max_results):
            # Extract IP from OID
            parts = oid.split('.')
            if len(parts) >= 4:
                addr = '.'.join(parts[-4:])
                if addr in addresses:
                    addresses[addr]['interface_index'] = int(value)
        
        # Get netmask
        for oid, value in self._snmp_walk(ip, community, OIDS['ipAdEntNetMask'], version, timeout, max_results):
            parts = oid.split('.')
            if len(parts) >= 4:
                addr = '.'.join(parts[-4:])
                if addr in addresses:
                    addresses[addr]['netmask'] = value
        
        return list(addresses.values())
    
    def _walk_arp_table(self, ip: str, community: str, version: str, timeout: int, max_results: int) -> List[Dict]:
        """Walk ARP/neighbor table."""
        entries = []
        
        for oid, value in self._snmp_walk(ip, community, OIDS['ipNetToMediaPhysAddress'], version, timeout, max_results):
            # Extract IP from OID (last 4 octets)
            parts = oid.split('.')
            if len(parts) >= 4:
                neighbor_ip = '.'.join(parts[-4:])
                mac = self._format_mac(value)
                if mac:
                    entries.append({
                        'ip_address': neighbor_ip,
                        'mac_address': mac,
                        'source_ip': ip,
                    })
        
        return entries
    
    def _walk_routing_table(self, ip: str, community: str, version: str, timeout: int, max_results: int) -> List[Dict]:
        """Walk IP routing table."""
        routes = {}
        
        # Get destinations
        for oid, value in self._snmp_walk(ip, community, OIDS['ipRouteDest'], version, timeout, max_results):
            dest = value
            routes[dest] = {'destination': dest}
        
        # Get next hops
        for oid, value in self._snmp_walk(ip, community, OIDS['ipRouteNextHop'], version, timeout, max_results):
            parts = oid.split('.')
            if len(parts) >= 4:
                dest = '.'.join(parts[-4:])
                if dest in routes:
                    routes[dest]['next_hop'] = value
        
        # Get masks
        for oid, value in self._snmp_walk(ip, community, OIDS['ipRouteMask'], version, timeout, max_results):
            parts = oid.split('.')
            if len(parts) >= 4:
                dest = '.'.join(parts[-4:])
                if dest in routes:
                    routes[dest]['mask'] = value
        
        return list(routes.values())
    
    def _walk_vlans(self, ip: str, community: str, version: str, timeout: int, max_results: int) -> List[Dict]:
        """Walk VLAN table."""
        vlans = []
        
        for oid, value in self._snmp_walk(ip, community, OIDS['dot1qVlanStaticName'], version, timeout, max_results):
            vlan_id = oid.split('.')[-1]
            vlans.append({
                'vlan_id': int(vlan_id),
                'name': value,
                'source_ip': ip,
            })
        
        return vlans
    
    def _walk_lldp(self, ip: str, community: str, version: str, timeout: int, max_results: int) -> List[Dict]:
        """Walk LLDP neighbor table."""
        neighbors = {}
        
        # Get remote system names
        for oid, value in self._snmp_walk(ip, community, OIDS['lldpRemSysName'], version, timeout, max_results):
            parts = oid.split('.')
            if len(parts) >= 3:
                key = '.'.join(parts[-3:])
                neighbors[key] = {'remote_system': value, 'source_ip': ip, 'protocol': 'lldp'}
        
        # Get remote port IDs
        for oid, value in self._snmp_walk(ip, community, OIDS['lldpRemPortId'], version, timeout, max_results):
            parts = oid.split('.')
            if len(parts) >= 3:
                key = '.'.join(parts[-3:])
                if key in neighbors:
                    neighbors[key]['remote_port'] = value
        
        # Get remote port descriptions
        for oid, value in self._snmp_walk(ip, community, OIDS['lldpRemPortDesc'], version, timeout, max_results):
            parts = oid.split('.')
            if len(parts) >= 3:
                key = '.'.join(parts[-3:])
                if key in neighbors:
                    neighbors[key]['remote_port_desc'] = value
        
        # Get chassis IDs
        for oid, value in self._snmp_walk(ip, community, OIDS['lldpRemChassisId'], version, timeout, max_results):
            parts = oid.split('.')
            if len(parts) >= 3:
                key = '.'.join(parts[-3:])
                if key in neighbors:
                    neighbors[key]['remote_chassis_id'] = value
        
        return list(neighbors.values())
    
    def _walk_cdp(self, ip: str, community: str, version: str, timeout: int, max_results: int) -> List[Dict]:
        """Walk CDP neighbor table (Cisco)."""
        neighbors = {}
        
        # Get device IDs
        for oid, value in self._snmp_walk(ip, community, OIDS['cdpCacheDeviceId'], version, timeout, max_results):
            parts = oid.split('.')
            if len(parts) >= 2:
                key = '.'.join(parts[-2:])
                neighbors[key] = {'remote_system': value, 'source_ip': ip, 'protocol': 'cdp'}
        
        # Get remote ports
        for oid, value in self._snmp_walk(ip, community, OIDS['cdpCacheDevicePort'], version, timeout, max_results):
            parts = oid.split('.')
            if len(parts) >= 2:
                key = '.'.join(parts[-2:])
                if key in neighbors:
                    neighbors[key]['remote_port'] = value
        
        # Get platforms
        for oid, value in self._snmp_walk(ip, community, OIDS['cdpCachePlatform'], version, timeout, max_results):
            parts = oid.split('.')
            if len(parts) >= 2:
                key = '.'.join(parts[-2:])
                if key in neighbors:
                    neighbors[key]['remote_platform'] = value
        
        return list(neighbors.values())
    
    def _walk_entity(self, ip: str, community: str, version: str, timeout: int, max_results: int) -> List[Dict]:
        """Walk Entity MIB for hardware info."""
        entities = {}
        
        for oid, value in self._snmp_walk(ip, community, OIDS['entPhysicalDescr'], version, timeout, max_results):
            idx = oid.split('.')[-1]
            entities[idx] = {'index': int(idx), 'description': value}
        
        for oid, value in self._snmp_walk(ip, community, OIDS['entPhysicalName'], version, timeout, max_results):
            idx = oid.split('.')[-1]
            if idx in entities:
                entities[idx]['name'] = value
        
        for oid, value in self._snmp_walk(ip, community, OIDS['entPhysicalSerialNum'], version, timeout, max_results):
            idx = oid.split('.')[-1]
            if idx in entities and value:
                entities[idx]['serial_number'] = value
        
        for oid, value in self._snmp_walk(ip, community, OIDS['entPhysicalModelName'], version, timeout, max_results):
            idx = oid.split('.')[-1]
            if idx in entities and value:
                entities[idx]['model'] = value
        
        return list(entities.values())
    
    def _walk_bgp(self, ip: str, community: str, version: str, timeout: int, max_results: int) -> List[Dict]:
        """Walk BGP peer table."""
        peers = []
        
        for oid, value in self._snmp_walk(ip, community, OIDS['bgpPeerState'], version, timeout, max_results):
            parts = oid.split('.')
            if len(parts) >= 4:
                peer_ip = '.'.join(parts[-4:])
                state_map = {'1': 'idle', '2': 'connect', '3': 'active', '4': 'opensent', '5': 'openconfirm', '6': 'established'}
                peers.append({
                    'peer_ip': peer_ip,
                    'state': state_map.get(value, value),
                    'source_ip': ip,
                })
        
        return peers
    
    def _walk_ospf(self, ip: str, community: str, version: str, timeout: int, max_results: int) -> List[Dict]:
        """Walk OSPF neighbor table."""
        neighbors = []
        
        for oid, value in self._snmp_walk(ip, community, OIDS['ospfNbrState'], version, timeout, max_results):
            parts = oid.split('.')
            if len(parts) >= 4:
                nbr_ip = '.'.join(parts[-4:])
                state_map = {'1': 'down', '2': 'attempt', '3': 'init', '4': '2way', '5': 'exstart', '6': 'exchange', '7': 'loading', '8': 'full'}
                neighbors.append({
                    'neighbor_ip': nbr_ip,
                    'state': state_map.get(value, value),
                    'source_ip': ip,
                })
        
        return neighbors
    
    def _walk_interfaces(self, params: Dict, context: Dict) -> Dict:
        """Lightweight interface-only walk."""
        targets = self._get_targets(params, context)
        if not targets:
            return {'error': 'No targets', 'success': False}
        
        all_interfaces = []
        version = params.get('snmp_version', '2c')
        timeout = params.get('timeout_seconds', 30)
        
        for target in targets:
            interfaces = self._walk_interfaces_table(
                target['ip_address'],
                target.get('community', 'public'),
                version,
                timeout,
                500
            )
            all_interfaces.extend(interfaces)
        
        return {
            'success': True,
            'interfaces': all_interfaces,
            'synced_count': len(all_interfaces),
        }
    
    def _walk_neighbors(self, params: Dict, context: Dict) -> Dict:
        """Walk for LLDP/CDP neighbors only."""
        targets = self._get_targets(params, context)
        if not targets:
            return {'error': 'No targets', 'success': False}
        
        protocols = params.get('protocols', ['lldp', 'cdp'])
        version = params.get('snmp_version', '2c')
        timeout = params.get('timeout_seconds', 30)
        
        all_neighbors = []
        topology = {'nodes': [], 'links': []}
        
        for target in targets:
            ip = target['ip_address']
            community = target.get('community', 'public')
            
            if 'lldp' in protocols:
                neighbors = self._walk_lldp(ip, community, version, timeout, 500)
                all_neighbors.extend(neighbors)
            
            if 'cdp' in protocols:
                neighbors = self._walk_cdp(ip, community, version, timeout, 500)
                all_neighbors.extend(neighbors)
        
        # Build topology if requested
        if params.get('build_topology', True):
            nodes_set = set()
            for n in all_neighbors:
                nodes_set.add(n.get('source_ip'))
                nodes_set.add(n.get('remote_system'))
            topology['nodes'] = [{'id': n, 'label': n} for n in nodes_set if n]
            topology['links'] = [
                {
                    'source': n.get('source_ip'),
                    'target': n.get('remote_system'),
                    'source_port': n.get('local_port'),
                    'target_port': n.get('remote_port'),
                }
                for n in all_neighbors if n.get('source_ip') and n.get('remote_system')
            ]
        
        return {
            'success': True,
            'neighbors': all_neighbors,
            'topology': topology,
            'cables_created': 0,
        }
    
    def _format_mac(self, value: str) -> Optional[str]:
        """Format MAC address from various SNMP formats."""
        if not value:
            return None
        
        # Remove common prefixes
        value = value.replace('Hex-STRING: ', '').replace('STRING: ', '').strip()
        
        # Handle hex format like "00 1A 2B 3C 4D 5E"
        if ' ' in value:
            parts = value.split()
            if len(parts) == 6:
                return ':'.join(parts).upper()
        
        # Handle format like "0:1a:2b:3c:4d:5e"
        if ':' in value:
            parts = value.split(':')
            if len(parts) == 6:
                return ':'.join(p.zfill(2) for p in parts).upper()
        
        # Handle raw hex like "001a2b3c4d5e"
        value = re.sub(r'[^0-9a-fA-F]', '', value)
        if len(value) == 12:
            return ':'.join(value[i:i+2] for i in range(0, 12, 2)).upper()
        
        return None
