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
    
    def execute(self, node: Dict, context) -> Dict:
        """Execute the SNMP walker based on command."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Debug: Log context type and contents
        logger.warning(f"SNMP Walker execute called. Context type: {type(context)}")
        if hasattr(context, 'variables'):
            logger.warning(f"SNMP Walker: context.variables keys: {list(context.variables.keys())}")
            for k, v in context.variables.items():
                if isinstance(v, dict):
                    logger.warning(f"SNMP Walker: '{k}' is dict with keys: {list(v.keys())[:10]}")
        
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
    
    def _get_targets(self, params: Dict, context) -> List[Dict]:
        """Extract targets from parameters or context."""
        target_source = params.get('target_source', 'from_autodiscovery')
        targets = []
        
        # Handle both dict context and ExecutionContext dataclass
        if hasattr(context, 'variables'):
            variables = context.variables
        elif isinstance(context, dict):
            variables = context.get('variables', {})
        else:
            variables = {}
        
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
            # Get targets from variables (set by previous node outputs)
            input_targets = variables.get('targets', [])
            if not input_targets:
                input_targets = variables.get('snmp_hosts', [])
            
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
            # Try to get from autodiscovery outputs stored in variables
            # Look for skipped_devices or created_devices in any dict variable
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"SNMP Walker: Looking for targets in variables. Keys: {list(variables.keys())}")
            
            # Collect all potential targets from all sources
            all_skipped = []
            all_created = []
            created = []  # Initialize created list
            
            for key, value in variables.items():
                if isinstance(value, dict):
                    # Collect skipped_devices (existing devices that were found)
                    skipped = value.get('skipped_devices', [])
                    if skipped and isinstance(skipped, list):
                        logger.warning(f"SNMP Walker: Found {len(skipped)} skipped_devices in '{key}'")
                        all_skipped.extend(skipped)
                    
                    # Collect created_devices (newly created devices)
                    created_list = value.get('created_devices', [])
                    if created_list and isinstance(created_list, list):
                        logger.warning(f"SNMP Walker: Found {len(created_list)} created_devices in '{key}'")
                        all_created.extend(created_list)
            
            # Use skipped_devices first (existing devices), then created_devices
            if all_skipped:
                created = all_skipped
                logger.warning(f"SNMP Walker: Using {len(created)} skipped_devices as targets")
            elif all_created:
                created = all_created
                logger.warning(f"SNMP Walker: Using {len(created)} created_devices as targets")
            else:
                # Fallback to direct variable access
                created = variables.get('skipped_devices', [])
                if not created:
                    created = variables.get('created_devices', [])
                if not created:
                    created = variables.get('snmp_active', [])
            
            logger.warning(f"SNMP Walker: Final target count: {len(created)}")
            if created:
                logger.warning(f"SNMP Walker: First target sample: {created[0] if created else 'none'}")
            
            for device in created:
                if isinstance(device, dict):
                    # Extract IP address - check ip_address first, then primary_ip
                    ip = device.get('ip_address')
                    if not ip:
                        primary_ip = device.get('primary_ip')
                        if isinstance(primary_ip, dict):
                            ip = primary_ip.get('address', '').split('/')[0]
                        elif isinstance(primary_ip, str):
                            ip = primary_ip.split('/')[0]
                    
                    if ip:
                        targets.append({
                            'ip_address': ip,
                            'community': device.get('snmp_community') or params.get('snmp_community', 'public'),
                            'device_id': device.get('id') or device.get('netbox_id'),
                            'device_name': device.get('name'),
                        })
                elif isinstance(device, str):
                    targets.append({
                        'ip_address': device,
                        'community': params.get('snmp_community', 'public'),
                    })
        
        return targets
    
    def _walk_comprehensive(self, params: Dict, context: Dict) -> Dict:
        """Perform comprehensive SNMP walk on all targets and sync to NetBox."""
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
        version = params.get('snmp_version', '2c')
        sync_to_netbox = params.get('sync_to_netbox', True)  # Default to syncing
        
        # Auto-detect optimal parallelism based on system resources
        import os
        cpu_count = os.cpu_count() or 4
        parallel = min(cpu_count * 10, len(targets), 200)  # 10x cores, max 200
        logger.info(f"SNMP walk using {parallel} threads for {len(targets)} targets (CPU cores: {cpu_count})")
        
        logger.info(
            f"Starting comprehensive SNMP walk on {len(targets)} targets",
            category='walk',
            details={'tables': walk_tables, 'parallel': parallel, 'sync_to_netbox': sync_to_netbox}
        )
        
        walk_results = []
        failed_hosts = []
        all_interfaces = []
        all_neighbors = []
        
        # NetBox sync stats
        netbox_stats = {
            'interfaces_created': 0,
            'interfaces_updated': 0,
            'interfaces_skipped': 0,
            'sync_errors': [],
        }
        
        # Get NetBox service if syncing
        netbox_service = None
        if sync_to_netbox:
            try:
                from ...api.netbox import get_netbox_service
                netbox_service = get_netbox_service()
                if not netbox_service.is_configured:
                    logger.warning("NetBox not configured, skipping sync")
                    netbox_service = None
            except Exception as e:
                logger.warning(f"Could not initialize NetBox service: {e}")
        
        # Walk targets in parallel - collect results first, then sync to NetBox
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
                        walk_results.append((result, target))  # Store tuple for later sync
                        all_interfaces.extend(result.get('interfaces', []))
                        all_neighbors.extend(result.get('lldp_neighbors', []))
                        all_neighbors.extend(result.get('cdp_neighbors', []))
                    else:
                        failed_hosts.append(target['ip_address'])
                except Exception as e:
                    logger.error(f"Walk failed for {target['ip_address']}: {e}")
                    failed_hosts.append(target['ip_address'])
        
        # Sync to NetBox in parallel AFTER all walks complete
        if netbox_service and walk_results:
            logger.info(f"Starting parallel NetBox sync for {len(walk_results)} devices")
            
            def sync_device(result_target):
                result, target = result_target
                if result.get('device_id'):
                    try:
                        return self._sync_device_to_netbox(netbox_service, result, target)
                    except Exception as e:
                        logger.error(f"NetBox sync failed for {target['ip_address']}: {e}")
                        return {'created': 0, 'updated': 0, 'skipped': 0, 'errors': [str(e)]}
                return {'created': 0, 'updated': 0, 'skipped': 0, 'errors': []}
            
            # Use parallel sync with optimal thread count
            sync_parallel = min(cpu_count * 5, len(walk_results), 100)  # 5x cores for API calls
            with concurrent.futures.ThreadPoolExecutor(max_workers=sync_parallel) as sync_executor:
                sync_results = list(sync_executor.map(sync_device, walk_results))
                for sync_result in sync_results:
                    netbox_stats['interfaces_created'] += sync_result.get('created', 0)
                    netbox_stats['interfaces_updated'] += sync_result.get('updated', 0)
                    netbox_stats['interfaces_skipped'] += sync_result.get('skipped', 0)
                    if sync_result.get('errors'):
                        netbox_stats['sync_errors'].extend(sync_result['errors'])
            
            # Convert back to just results for return value
            walk_results = [r for r, t in walk_results]
        
        duration = time.time() - start_time
        
        summary = {
            'total_targets': len(targets),
            'successful': len(walk_results),
            'failed': len(failed_hosts),
            'total_interfaces': len(all_interfaces),
            'total_neighbors': len(all_neighbors),
            'duration_seconds': round(duration, 2),
            'netbox_sync': netbox_stats if sync_to_netbox else None,
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
            'netbox_sync': netbox_stats if sync_to_netbox else None,
        }
    
    def _sync_device_to_netbox(self, netbox_service, walk_result: Dict, target: Dict) -> Dict:
        """Sync discovered data for a single device to NetBox using batch operations."""
        device_id = walk_result.get('device_id') or target.get('device_id')
        device_name = walk_result.get('device_name') or target.get('device_name')
        
        created = 0
        updated = 0
        skipped = 0
        errors = []
        
        if not device_id:
            return {'created': 0, 'updated': 0, 'skipped': 0, 'errors': ['No device_id']}
        
        try:
            # Get existing interfaces for this device
            existing = netbox_service.get_interfaces(device_id=device_id, limit=1000)
            existing_names = {i['name']: i for i in existing.get('results', [])}
            
            # Build batch lists for create and update
            to_create = []
            to_update = []
            
            for iface in walk_result.get('interfaces', []):
                iface_name = iface.get('name', '')
                if not iface_name:
                    continue
                
                # Map SNMP interface type to NetBox type
                netbox_type = self._map_interface_type(iface)
                
                # Build interface data
                iface_data = {
                    'name': iface_name,
                    'type': netbox_type,
                    'enabled': iface.get('admin_status') == 'up',
                    'description': iface.get('description', ''),
                }
                
                # Add MAC address if available
                mac = iface.get('mac_address')
                if mac and mac != '00:00:00:00:00:00':
                    iface_data['mac_address'] = mac.upper()
                
                # Add speed if available
                speed = iface.get('speed_mbps')
                if speed and speed > 0:
                    iface_data['speed'] = speed * 1000  # NetBox uses kbps
                
                if iface_name in existing_names:
                    # Queue for batch update
                    existing_iface = existing_names[iface_name]
                    iface_data['id'] = existing_iface['id']
                    to_update.append(iface_data)
                else:
                    # Queue for batch create
                    iface_data['device'] = device_id
                    to_create.append(iface_data)
            
            # Batch create new interfaces (single API call)
            if to_create:
                try:
                    netbox_service._request('POST', 'dcim/interfaces/', json=to_create)
                    created = len(to_create)
                except Exception as e:
                    logger.warning(f"Batch create failed for {device_name}, falling back to individual: {e}")
                    # Fallback to individual creates
                    for iface_data in to_create:
                        try:
                            netbox_service._request('POST', 'dcim/interfaces/', json=iface_data)
                            created += 1
                        except Exception as e2:
                            skipped += 1
            
            # Batch update existing interfaces (single API call)
            if to_update:
                try:
                    netbox_service._request('PATCH', 'dcim/interfaces/', json=to_update)
                    updated = len(to_update)
                except Exception as e:
                    logger.warning(f"Batch update failed for {device_name}, falling back to individual: {e}")
                    # Fallback to individual updates
                    for iface_data in to_update:
                        try:
                            iface_id = iface_data.pop('id')
                            netbox_service._request('PATCH', f'dcim/interfaces/{iface_id}/', json=iface_data)
                            updated += 1
                        except Exception as e2:
                            skipped += 1
            
            # Update device with system info if available
            system_info = walk_result.get('system_info', {})
            if system_info:
                device_update = {}
                
                # Update serial number if found
                if system_info.get('sysDescr'):
                    # Try to extract serial from sysDescr or store in comments
                    device_update['comments'] = f"SNMP sysDescr: {system_info.get('sysDescr', '')[:500]}"
                
                if device_update:
                    try:
                        netbox_service._request('PATCH', f'dcim/devices/{device_id}/', json=device_update)
                    except Exception as e:
                        logger.warning(f"Failed to update device {device_name}: {e}")
            
            logger.info(f"NetBox sync for {device_name}: created={created}, updated={updated}, skipped={skipped}")
            
        except Exception as e:
            logger.error(f"Failed to sync device {device_name} to NetBox: {e}")
            errors.append({'device': device_name, 'error': str(e)})
        
        return {
            'created': created,
            'updated': updated,
            'skipped': skipped,
            'errors': errors,
        }
    
    def _map_interface_type(self, iface: Dict) -> str:
        """Map SNMP interface type to NetBox interface type."""
        snmp_type = iface.get('type')
        speed = iface.get('speed_mbps', 0)
        name = iface.get('name', '').lower()
        
        # Map based on speed first
        if speed >= 100000:
            return '100gbase-x-qsfp28'
        elif speed >= 40000:
            return '40gbase-x-qsfpp'
        elif speed >= 25000:
            return '25gbase-x-sfp28'
        elif speed >= 10000:
            return '10gbase-x-sfpp'
        elif speed >= 1000:
            return '1000base-t'
        elif speed >= 100:
            return '100base-tx'
        elif speed >= 10:
            return '10base-t'
        
        # Map based on name patterns
        if 'gig' in name or 'ge' in name:
            return '1000base-t'
        if 'fast' in name or 'fe' in name:
            return '100base-tx'
        if 'ten' in name or 'te' in name or '10g' in name:
            return '10gbase-x-sfpp'
        if 'vlan' in name:
            return 'virtual'
        if 'loopback' in name or name == 'lo':
            return 'virtual'
        if 'mgmt' in name or 'management' in name:
            return '1000base-t'
        
        # Default based on SNMP type
        # Type 6 = ethernetCsmacd
        # Type 24 = softwareLoopback
        # Type 1 = other
        if snmp_type == '24' or snmp_type == 24:
            return 'virtual'
        
        return '1000base-t'  # Default
    
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
