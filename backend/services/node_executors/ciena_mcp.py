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
        Get equipment inventory from MCP and optionally sync to NetBox.
        
        Parameters:
            - device_id: Optional MCP device ID to filter equipment
            - sync_to_netbox: Whether to sync to NetBox as inventory items (default False)
        """
        from ..ciena_mcp_service import get_mcp_service, CienaMCPError
        
        params = node.get('parameters', {})
        device_id = params.get('device_id')
        sync_to_netbox = params.get('sync_to_netbox', False)
        
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
            
            result = {
                'success': True,
                'equipment': equipment_list,
                'equipment_count': len(equipment_list),
            }
            
            # Sync to NetBox if enabled
            if sync_to_netbox:
                from ...api.netbox import get_netbox_service
                netbox = get_netbox_service()
                
                if netbox.is_configured:
                    sync_stats = mcp.sync_equipment_to_netbox(netbox)
                    result['netbox_sync'] = sync_stats
                else:
                    result['netbox_sync'] = {'error': 'NetBox not configured'}
            
            logger.info(f"MCP equipment sync complete: {len(equipment_list)} items")
            return result
            
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


class MCPGetServicesExecutor(BaseNodeExecutor):
    """Get services/circuits from Ciena MCP."""
    
    node_type = 'mcp_get_services'
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """
        Get services from MCP.
        
        Parameters:
            - service_class: Optional filter by service class (Ring, EVC, Ethernet, etc.)
        """
        from ..ciena_mcp_service import get_mcp_service, CienaMCPError
        
        params = node.get('parameters', {})
        service_class = params.get('service_class')
        
        try:
            mcp = get_mcp_service()
            
            if not mcp.is_configured:
                return {
                    'success': False,
                    'error': 'Ciena MCP is not configured.',
                    'services': []
                }
            
            logger.info(f"Fetching services from Ciena MCP (class={service_class or 'all'})...")
            services = mcp.get_all_services(service_class=service_class if service_class else None)
            
            # Transform and count states
            service_list = []
            up_count = 0
            down_count = 0
            
            for svc in services:
                attrs = svc.get('attributes', {})
                display = attrs.get('displayData', {})
                utilization = attrs.get('utilizationData', {})
                add_attrs = attrs.get('additionalAttributes', {})
                
                op_state = (display.get('operationState') or attrs.get('operationState') or '').lower()
                if op_state == 'up':
                    up_count += 1
                elif op_state == 'down':
                    down_count += 1
                
                service_list.append({
                    'id': svc.get('id'),
                    'name': attrs.get('userLabel') or attrs.get('mgmtName') or svc.get('id'),
                    'service_class': attrs.get('serviceClass'),
                    'layer_rate': attrs.get('layerRate'),
                    'admin_state': display.get('adminState') or attrs.get('adminState'),
                    'operation_state': display.get('operationState') or attrs.get('operationState'),
                    'total_capacity': utilization.get('totalCapacity'),
                    'used_capacity': utilization.get('usedCapacity'),
                    'ring_id': add_attrs.get('ringId'),
                    'ring_state': add_attrs.get('ringState'),
                    'ring_status': add_attrs.get('ringStatus'),
                })
            
            logger.info(f"MCP services fetch complete: {len(service_list)} services (up={up_count}, down={down_count})")
            return {
                'success': True,
                'services': service_list,
                'service_count': len(service_list),
                'up_count': up_count,
                'down_count': down_count,
            }
            
        except CienaMCPError as e:
            logger.error(f"MCP get services failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'services': []
            }
        except Exception as e:
            logger.error(f"MCP get services failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'services': []
            }


class MCPGetRingsExecutor(BaseNodeExecutor):
    """Get G.8032 ring services from Ciena MCP."""
    
    node_type = 'mcp_get_rings'
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """Get G.8032 rings from MCP."""
        from ..ciena_mcp_service import get_mcp_service, CienaMCPError
        
        try:
            mcp = get_mcp_service()
            
            if not mcp.is_configured:
                return {
                    'success': False,
                    'error': 'Ciena MCP is not configured.',
                    'rings': []
                }
            
            logger.info("Fetching G.8032 rings from Ciena MCP...")
            rings = mcp.get_rings()
            
            ring_list = []
            ok_count = 0
            failed_count = 0
            
            for ring in rings:
                attrs = ring.get('attributes', {})
                add_attrs = attrs.get('additionalAttributes', {})
                
                ring_state = add_attrs.get('ringState', '').upper()
                ring_status = add_attrs.get('ringStatus', '').upper()
                
                if ring_state == 'OK' and ring_status == 'OK':
                    ok_count += 1
                else:
                    failed_count += 1
                
                ring_list.append({
                    'id': ring.get('id'),
                    'name': attrs.get('mgmtName') or attrs.get('userLabel') or ring.get('id'),
                    'ring_id': add_attrs.get('ringId'),
                    'ring_state': ring_state,
                    'ring_status': ring_status,
                    'ring_type': add_attrs.get('ringType'),
                    'ring_members': add_attrs.get('ringMembers'),
                    'logical_ring': add_attrs.get('logicalRingName'),
                    'virtual_ring': add_attrs.get('virtualRingName'),
                    'revertive': add_attrs.get('revertive'),
                    'raps_vid': add_attrs.get('rapsVid'),
                })
            
            logger.info(f"MCP rings fetch complete: {len(ring_list)} rings (ok={ok_count}, failed={failed_count})")
            return {
                'success': True,
                'rings': ring_list,
                'ring_count': len(ring_list),
                'ok_count': ok_count,
                'failed_count': failed_count,
            }
            
        except CienaMCPError as e:
            logger.error(f"MCP get rings failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'rings': []
            }
        except Exception as e:
            logger.error(f"MCP get rings failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'rings': []
            }


class MCPServiceSummaryExecutor(BaseNodeExecutor):
    """Get MCP service summary."""
    
    node_type = 'mcp_service_summary'
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """Get summary of all MCP services."""
        from ..ciena_mcp_service import get_mcp_service, CienaMCPError
        
        try:
            mcp = get_mcp_service()
            
            if not mcp.is_configured:
                return {
                    'success': False,
                    'error': 'Ciena MCP is not configured.',
                }
            
            summary = mcp.get_service_summary()
            
            return {
                'success': True,
                'total': summary.get('total', 0),
                'by_class': summary.get('by_class', {}),
                'by_state': summary.get('by_state', {}),
                'rings': summary.get('rings', []),
                'down_services': summary.get('down_services', []),
            }
            
        except CienaMCPError as e:
            return {
                'success': False,
                'error': str(e)
            }


class MCPMonitorServicesExecutor(BaseNodeExecutor):
    """Monitor MCP services and detect state changes."""
    
    node_type = 'mcp_monitor_services'
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """
        Poll MCP services and detect issues.
        
        Parameters:
            - alert_on_down: Generate alert when service goes down (default True)
            - alert_on_ring_failure: Generate alert when ring state is not OK (default True)
            - service_classes: List of service classes to monitor (empty = all)
        """
        from ..ciena_mcp_service import get_mcp_service, CienaMCPError
        
        params = node.get('parameters', {})
        alert_on_down = params.get('alert_on_down', True)
        alert_on_ring_failure = params.get('alert_on_ring_failure', True)
        service_classes = params.get('service_classes', [])
        
        try:
            mcp = get_mcp_service()
            
            if not mcp.is_configured:
                return {
                    'success': False,
                    'error': 'Ciena MCP is not configured.',
                }
            
            logger.info("Monitoring MCP services...")
            
            # Get service summary
            summary = mcp.get_service_summary()
            
            down_services = []
            ring_failures = []
            alerts = []
            
            # Check for down services
            for svc in summary.get('down_services', []):
                svc_class = svc.get('class', '')
                if not service_classes or svc_class in service_classes:
                    down_services.append(svc)
                    if alert_on_down:
                        alerts.append({
                            'type': 'service_down',
                            'severity': 'critical',
                            'service_id': svc.get('id'),
                            'service_name': svc.get('name'),
                            'service_class': svc_class,
                            'message': f"Service {svc.get('name')} ({svc_class}) is DOWN"
                        })
            
            # Check for ring failures
            for ring in summary.get('rings', []):
                ring_state = (ring.get('ring_state') or '').upper()
                ring_status = (ring.get('ring_status') or '').upper()
                
                if ring_state != 'OK' or ring_status != 'OK':
                    ring_failures.append(ring)
                    if alert_on_ring_failure:
                        alerts.append({
                            'type': 'ring_failure',
                            'severity': 'critical',
                            'ring_id': ring.get('ring_id'),
                            'ring_name': ring.get('name'),
                            'ring_state': ring_state,
                            'ring_status': ring_status,
                            'message': f"G.8032 Ring {ring.get('name')} (ID: {ring.get('ring_id')}) state={ring_state}, status={ring_status}"
                        })
            
            logger.info(f"MCP monitoring complete: {summary.get('total', 0)} services checked, "
                       f"{len(down_services)} down, {len(ring_failures)} ring failures, {len(alerts)} alerts")
            
            return {
                'success': True,
                'services_checked': summary.get('total', 0),
                'down_services': down_services,
                'ring_failures': ring_failures,
                'alerts': alerts,
                'summary': summary,
            }
            
        except CienaMCPError as e:
            logger.error(f"MCP monitoring failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"MCP monitoring failed: {e}")
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
    'mcp_get_services': MCPGetServicesExecutor,
    'mcp_get_rings': MCPGetRingsExecutor,
    'mcp_service_summary': MCPServiceSummaryExecutor,
    'mcp_monitor_services': MCPMonitorServicesExecutor,
}
