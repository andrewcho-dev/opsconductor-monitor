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
