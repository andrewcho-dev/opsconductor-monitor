"""
NetBox Node Executors.

Executors for NetBox-related workflow nodes.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class NetBoxAutodiscoveryExecutor:
    """
    Executor for the netbox:autodiscovery node.
    
    Performs comprehensive network discovery and syncs results to NetBox.
    """
    
    def execute(self, node: Dict, context: Any) -> Dict[str, Any]:
        """
        Execute the autodiscovery node.
        
        Args:
            node: Node definition with parameters
            context: Execution context
        
        Returns:
            Discovery results
        """
        from ...executors.netbox_autodiscovery_executor import NetBoxAutodiscoveryExecutor as BackendExecutor
        
        params = node.get('data', {}).get('parameters', {})
        
        logger.info(f"Starting NetBox autodiscovery with params: {params}")
        
        # Get input targets if provided from previous node
        input_targets = None
        if params.get('target_type') == 'from_input':
            # Try to get targets from context variables
            input_targets = context.variables.get('targets', [])
            if not input_targets:
                input_targets = context.variables.get('online', [])
            params['input_targets'] = input_targets
        
        try:
            # Create and execute the backend executor
            executor = BackendExecutor()
            result = executor.execute(params)
            
            # Store outputs in context for downstream nodes
            if result.get('success'):
                context.variables['created_devices'] = result.get('created_devices', [])
                context.variables['updated_devices'] = result.get('updated_devices', [])
                context.variables['failed_hosts'] = result.get('failed_hosts', [])
                context.variables['discovery_report'] = result.get('discovery_report', {})
            
            return result
            
        except Exception as e:
            logger.exception(f"NetBox autodiscovery failed: {e}")
            return {
                'success': False,
                'error': str(e),
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
                    'errors': [str(e)],
                    'duration_seconds': 0,
                },
            }


class NetBoxDeviceCreateExecutor:
    """
    Executor for the netbox:device-create node.
    """
    
    def execute(self, node: Dict, context: Any) -> Dict[str, Any]:
        """Execute device creation in NetBox."""
        from ...api.netbox import get_netbox_service
        
        params = node.get('data', {}).get('parameters', {})
        
        try:
            service = get_netbox_service()
            
            # Check if batch mode
            mode = params.get('mode', 'single')
            
            if mode == 'batch':
                # Get items from context
                items = context.variables.get('items', [])
                if not items:
                    items = context.variables.get('results', [])
                
                created = []
                errors = []
                
                for item in items:
                    try:
                        # Resolve field mappings
                        device_data = {
                            'name': self._resolve_field(params.get('name'), item),
                            'device_type': params.get('device_type'),
                            'role': params.get('role'),
                            'site': params.get('site'),
                            'status': params.get('status', 'active'),
                        }
                        
                        if params.get('serial'):
                            device_data['serial'] = self._resolve_field(params.get('serial'), item)
                        
                        result = service.create_device(**device_data)
                        created.append(result)
                    except Exception as e:
                        errors.append({'item': item, 'error': str(e)})
                
                return {
                    'success': len(errors) == 0,
                    'created': created,
                    'errors': errors,
                    'count': len(created),
                }
            else:
                # Single device creation
                device_data = {
                    'name': params.get('name'),
                    'device_type': params.get('device_type'),
                    'role': params.get('role'),
                    'site': params.get('site'),
                    'status': params.get('status', 'active'),
                }
                
                if params.get('serial'):
                    device_data['serial'] = params.get('serial')
                if params.get('description'):
                    device_data['description'] = params.get('description')
                
                result = service.create_device(**device_data)
                
                return {
                    'success': True,
                    'device': result,
                    'device_id': result.get('id'),
                }
                
        except Exception as e:
            logger.exception(f"NetBox device creation failed: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    def _resolve_field(self, field_spec: str, item: Dict) -> Any:
        """Resolve a field specification against an item."""
        if not field_spec:
            return None
        
        # Simple expression resolution: {{field_name}}
        if field_spec.startswith('{{') and field_spec.endswith('}}'):
            field_name = field_spec[2:-2].strip()
            return item.get(field_name)
        
        return field_spec


class NetBoxInterfaceSyncExecutor:
    """
    Executor for the netbox:snmp-interface-sync node.
    
    Takes SNMP interface data from previous nodes and syncs to NetBox.
    """
    
    def execute(self, node: Dict, context: Any) -> Dict[str, Any]:
        """
        Execute interface sync to NetBox.
        
        Args:
            node: Node definition with parameters
            context: Execution context with SNMP data from previous nodes
        
        Returns:
            Sync results
        """
        from ...api.netbox import get_netbox_service
        
        params = node.get('data', {}).get('parameters', {})
        
        logger.info("Starting NetBox interface sync")
        
        # Get interface data from context (from SNMP Walker node)
        interfaces = []
        
        # Handle both dict context and ExecutionContext dataclass
        if hasattr(context, 'variables'):
            variables = context.variables
        elif isinstance(context, dict):
            variables = context.get('variables', {})
        else:
            variables = {}
        
        # Look for interfaces in node outputs
        for key, value in variables.items():
            if isinstance(value, dict):
                # Check for interfaces_discovered from SNMP walker
                if value.get('interfaces_discovered'):
                    interfaces.extend(value.get('interfaces_discovered', []))
                # Also check walk_results which contain per-device interfaces
                if value.get('walk_results'):
                    for walk_result in value.get('walk_results', []):
                        if walk_result.get('interfaces'):
                            for iface in walk_result.get('interfaces', []):
                                # Add source device info to interface
                                iface['source_ip'] = walk_result.get('ip_address')
                                iface['device_id'] = walk_result.get('device_id')
                                iface['device_name'] = walk_result.get('device_name')
                                interfaces.append(iface)
        
        if not interfaces:
            logger.warning("No interfaces found in context to sync")
            return {
                'success': True,
                'message': 'No interfaces found to sync',
                'synced': 0,
                'created': 0,
                'updated': 0,
                'skipped': 0,
                'errors': [],
            }
        
        logger.info(f"Found {len(interfaces)} interfaces to sync to NetBox")
        
        try:
            service = get_netbox_service()
            
            created = 0
            updated = 0
            skipped = 0
            errors = []
            
            # Group interfaces by device
            device_interfaces = {}
            for iface in interfaces:
                device_id = iface.get('device_id')
                if device_id:
                    if device_id not in device_interfaces:
                        device_interfaces[device_id] = []
                    device_interfaces[device_id].append(iface)
            
            # Sync interfaces for each device using batch operations
            def sync_device_interfaces(device_id_ifaces):
                device_id, device_ifaces = device_id_ifaces
                local_created = 0
                local_updated = 0
                local_skipped = 0
                local_errors = []
                
                try:
                    # Get existing interfaces for this device
                    existing = service.get_interfaces(device_id=device_id, limit=1000)
                    existing_names = {i['name']: i for i in existing.get('results', [])}
                    
                    # Build batch lists
                    to_create = []
                    to_update = []
                    
                    for iface in device_ifaces:
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
                            existing_iface = existing_names[iface_name]
                            iface_data['id'] = existing_iface['id']
                            to_update.append(iface_data)
                        else:
                            iface_data['device'] = device_id
                            to_create.append(iface_data)
                    
                    # Batch create
                    if to_create:
                        try:
                            service._request('POST', 'dcim/interfaces/', json=to_create)
                            local_created = len(to_create)
                        except Exception as e:
                            logger.warning(f"Batch create failed, falling back: {e}")
                            for iface_data in to_create:
                                try:
                                    service._request('POST', 'dcim/interfaces/', json=iface_data)
                                    local_created += 1
                                except:
                                    local_skipped += 1
                    
                    # Batch update
                    if to_update:
                        try:
                            service._request('PATCH', 'dcim/interfaces/', json=to_update)
                            local_updated = len(to_update)
                        except Exception as e:
                            logger.warning(f"Batch update failed, falling back: {e}")
                            for iface_data in to_update:
                                try:
                                    iface_id = iface_data.pop('id')
                                    service._request('PATCH', f'dcim/interfaces/{iface_id}/', json=iface_data)
                                    local_updated += 1
                                except:
                                    local_skipped += 1
                                    
                except Exception as e:
                    logger.error(f"Failed to sync interfaces for device {device_id}: {e}")
                    local_errors.append({'device_id': device_id, 'error': str(e)})
                
                return (local_created, local_updated, local_skipped, local_errors)
            
            # Process devices in parallel
            from concurrent.futures import ThreadPoolExecutor
            import os
            cpu_count = os.cpu_count() or 4
            max_workers = max(1, min(cpu_count * 5, len(device_interfaces), 100))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(sync_device_interfaces, device_interfaces.items()))
            
            for local_created, local_updated, local_skipped, local_errors in results:
                created += local_created
                updated += local_updated
                skipped += local_skipped
                errors.extend(local_errors)
            
            return {
                'success': len(errors) == 0 or (created + updated) > 0,
                'synced': created + updated,
                'created': created,
                'updated': updated,
                'skipped': skipped,
                'errors': errors,
                'devices_processed': len(device_interfaces),
            }
            
        except Exception as e:
            logger.exception(f"NetBox interface sync failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'synced': 0,
                'created': 0,
                'updated': 0,
                'skipped': 0,
                'errors': [str(e)],
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


class NetBoxLookupExecutor:
    """
    Executor for NetBox lookup nodes (sites, roles, device-types, etc).
    """
    
    def __init__(self, lookup_type: str):
        self.lookup_type = lookup_type
    
    def execute(self, node: Dict, context: Any) -> Dict[str, Any]:
        """Execute a NetBox lookup."""
        from ...api.netbox import get_netbox_service
        
        params = node.get('data', {}).get('parameters', {})
        limit = params.get('limit', 500)
        
        try:
            service = get_netbox_service()
            
            if self.lookup_type == 'sites':
                result = service.get_sites(limit=limit)
            elif self.lookup_type == 'device-roles':
                result = service.get_device_roles(limit=limit)
            elif self.lookup_type == 'device-types':
                manufacturer = params.get('manufacturer')
                result = service.get_device_types(manufacturer=manufacturer, limit=limit)
            elif self.lookup_type == 'manufacturers':
                result = service.get_manufacturers(limit=limit)
            elif self.lookup_type == 'tags':
                result = service._request('GET', 'extras/tags/', params={'limit': limit})
            else:
                return {
                    'success': False,
                    'error': f'Unknown lookup type: {self.lookup_type}',
                }
            
            items = result.get('results', [])
            
            return {
                'success': True,
                self.lookup_type.replace('-', '_'): items,
                'count': len(items),
            }
            
        except Exception as e:
            logger.exception(f"NetBox lookup failed: {e}")
            return {
                'success': False,
                'error': str(e),
            }
