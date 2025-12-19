"""
Ciena MCP Node Executors.

Workflow node executors for Ciena MCP integration - device sync, equipment inventory,
and topology discovery.
"""

import logging
from typing import Dict, Any, List
from .base import BaseNodeExecutor

logger = logging.getLogger(__name__)


class MCPDeviceSyncExecutor(BaseNodeExecutor):
    """Sync devices from Ciena MCP to NetBox."""
    
    node_type = 'mcp_device_sync'
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """
        Sync MCP devices to NetBox.
        
        Parameters:
            - sync_to_netbox: Whether to sync to NetBox (default True)
            - create_missing: Create devices not in NetBox (default True)
            - site_id: NetBox site ID for new devices
            - device_role_id: NetBox device role ID for new devices
        """
        from ..ciena_mcp_service import get_mcp_service, CienaMCPError
        
        params = node.get('parameters', {})
        sync_to_netbox = params.get('sync_to_netbox', True)
        create_missing = params.get('create_missing', True)
        site_id = params.get('site_id')
        device_role_id = params.get('device_role_id')
        
        try:
            mcp = get_mcp_service()
            
            if not mcp.is_configured:
                return {
                    'success': False,
                    'error': 'Ciena MCP is not configured. Set URL, username, and password in settings.',
                    'devices': []
                }
            
            # Get all devices from MCP
            logger.info("Fetching devices from Ciena MCP...")
            devices = mcp.get_all_devices()
            
            # Transform to standard format
            device_list = []
            for device in devices:
                attrs = device.get('attributes', {})
                display = attrs.get('displayData', {})
                
                device_list.append({
                    'mcp_id': device.get('id'),
                    'name': attrs.get('name') or display.get('displayName'),
                    'ip_address': attrs.get('ipAddress') or display.get('displayIpAddress'),
                    'mac_address': attrs.get('macAddress') or display.get('displayMACAddress'),
                    'serial_number': attrs.get('serialNumber'),
                    'device_type': attrs.get('deviceType'),
                    'software_version': attrs.get('softwareVersion'),
                    'vendor': attrs.get('vendor', 'Ciena'),
                    'sync_state': display.get('displaySyncState'),
                    'resource_state': attrs.get('resourceState'),
                    'association_state': display.get('displayAssociationState'),
                })
            
            result = {
                'success': True,
                'devices': device_list,
                'device_count': len(device_list),
            }
            
            # Sync to NetBox if enabled
            if sync_to_netbox:
                from ...api.netbox import get_netbox_service
                netbox = get_netbox_service()
                
                if netbox.is_configured:
                    sync_stats = mcp.sync_devices_to_netbox(
                        netbox, 
                        site_id=site_id,
                        device_role_id=device_role_id,
                        create_missing=create_missing
                    )
                    result['netbox_sync'] = sync_stats
                else:
                    result['netbox_sync'] = {'error': 'NetBox not configured'}
            
            logger.info(f"MCP device sync complete: {len(device_list)} devices")
            return result
            
        except CienaMCPError as e:
            logger.error(f"MCP device sync failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'devices': []
            }
        except Exception as e:
            logger.error(f"MCP device sync failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'devices': []
            }


class MCPEquipmentSyncExecutor(BaseNodeExecutor):
    """Sync equipment (SFPs, cards) from Ciena MCP."""
    
    node_type = 'mcp_equipment_sync'
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """
        Get equipment inventory from MCP.
        
        Parameters:
            - device_id: Optional MCP device ID to filter equipment
        """
        from ..ciena_mcp_service import get_mcp_service, CienaMCPError
        
        params = node.get('parameters', {})
        device_id = params.get('device_id')
        
        try:
            mcp = get_mcp_service()
            
            if not mcp.is_configured:
                return {
                    'success': False,
                    'error': 'Ciena MCP is not configured.',
                    'equipment': []
                }
            
            # Get equipment from MCP
            logger.info("Fetching equipment from Ciena MCP...")
            equipment = mcp.get_all_equipment(device_id=device_id)
            
            # Transform to standard format
            equipment_list = []
            for item in equipment:
                attrs = item.get('attributes', {})
                display = attrs.get('displayData', {})
                installed = attrs.get('installedSpec', {})
                locations = attrs.get('locations', [{}])
                location = locations[0] if locations else {}
                
                equipment_list.append({
                    'mcp_id': item.get('id'),
                    'name': display.get('displayName'),
                    'type': installed.get('type') or attrs.get('cardType'),
                    'serial_number': installed.get('serialNumber'),
                    'part_number': installed.get('partNumber'),
                    'manufacturer': installed.get('manufacturer'),
                    'hardware_version': installed.get('hardwareVersion'),
                    'slot': location.get('subslot'),
                    'device_name': location.get('neName'),
                    'state': attrs.get('state'),
                    'category': attrs.get('category'),
                })
            
            logger.info(f"MCP equipment sync complete: {len(equipment_list)} items")
            return {
                'success': True,
                'equipment': equipment_list,
                'equipment_count': len(equipment_list),
            }
            
        except CienaMCPError as e:
            logger.error(f"MCP equipment sync failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'equipment': []
            }
        except Exception as e:
            logger.error(f"MCP equipment sync failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'equipment': []
            }


class MCPTopologySyncExecutor(BaseNodeExecutor):
    """Sync network topology (links) from Ciena MCP."""
    
    node_type = 'mcp_topology_sync'
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """Get network links/topology from MCP."""
        from ..ciena_mcp_service import get_mcp_service, CienaMCPError
        
        try:
            mcp = get_mcp_service()
            
            if not mcp.is_configured:
                return {
                    'success': False,
                    'error': 'Ciena MCP is not configured.',
                    'links': []
                }
            
            # Get links from MCP
            logger.info("Fetching network topology from Ciena MCP...")
            links = mcp.get_all_links()
            
            # Transform to standard format
            link_list = []
            for link in links:
                attrs = link.get('attributes', {})
                display = attrs.get('displayData', {})
                utilization = attrs.get('utilizationData', {})
                
                link_list.append({
                    'mcp_id': link.get('id'),
                    'service_class': attrs.get('serviceClass'),
                    'layer_rate': attrs.get('layerRate'),
                    'protocol': attrs.get('protocol'),
                    'admin_state': attrs.get('adminState'),
                    'operation_state': attrs.get('operationState'),
                    'directionality': attrs.get('directionality'),
                    'total_capacity': utilization.get('totalCapacity'),
                    'used_capacity': utilization.get('usedCapacity'),
                    'utilization_percent': utilization.get('utilizationPercent'),
                    'capacity_units': utilization.get('capacityUnits'),
                })
            
            logger.info(f"MCP topology sync complete: {len(link_list)} links")
            return {
                'success': True,
                'links': link_list,
                'link_count': len(link_list),
            }
            
        except CienaMCPError as e:
            logger.error(f"MCP topology sync failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'links': []
            }
        except Exception as e:
            logger.error(f"MCP topology sync failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'links': []
            }


class MCPInventorySummaryExecutor(BaseNodeExecutor):
    """Get MCP inventory summary."""
    
    node_type = 'mcp_inventory_summary'
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """Get summary counts from MCP."""
        from ..ciena_mcp_service import get_mcp_service, CienaMCPError
        
        try:
            mcp = get_mcp_service()
            
            if not mcp.is_configured:
                return {
                    'success': False,
                    'error': 'Ciena MCP is not configured.',
                }
            
            summary = mcp.get_device_summary()
            
            if 'error' in summary:
                return {
                    'success': False,
                    'error': summary['error']
                }
            
            return {
                'success': True,
                'summary': summary,
                'device_count': summary.get('devices', 0),
                'equipment_count': summary.get('equipment', 0),
                'link_count': summary.get('links', 0),
            }
            
        except CienaMCPError as e:
            return {
                'success': False,
                'error': str(e)
            }


# Register executors
EXECUTORS = {
    'mcp_device_sync': MCPDeviceSyncExecutor,
    'mcp_equipment_sync': MCPEquipmentSyncExecutor,
    'mcp_topology_sync': MCPTopologySyncExecutor,
    'mcp_inventory_summary': MCPInventorySummaryExecutor,
}
