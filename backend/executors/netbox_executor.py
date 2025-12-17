"""
NetBox Executor - Workflow functions for NetBox integration.

Provides CRUD operations and discovery functions for populating NetBox
device inventory from workflow jobs.
"""

import logging
import re
import socket
import subprocess
from typing import Dict, List, Optional, Any

from .base import BaseExecutor
from .registry import register_executor

logger = logging.getLogger(__name__)


def get_netbox_service():
    """Get configured NetBox service instance."""
    from backend.services.netbox_service import NetBoxService
    from backend.models import SystemSetting
    
    url = SystemSetting.get('netbox_url', '')
    token = SystemSetting.get('netbox_token', '')
    verify_ssl = SystemSetting.get('netbox_verify_ssl', True)
    
    return NetBoxService(url=url, token=token, verify_ssl=verify_ssl)


@register_executor
class NetBoxExecutor(BaseExecutor):
    """
    Executor for NetBox operations in workflows.
    
    Supports actions:
    - Device CRUD: device.create, device.update, device.delete, device.get, device.list
    - VM CRUD: vm.create, vm.update, vm.delete, vm.get, vm.list
    - Interface: interface.create, interface.update, interface.list, interface.assign_ip
    - IP Address: ip.create, ip.update, ip.list, ip.assign_primary
    - Discovery: discover.ping, discover.snmp, discover.hostname, discover.platform
    - Bulk: bulk.update_field, bulk.tag
    - Lookup: lookup.sites, lookup.roles, lookup.platforms, lookup.device_types
    """
    
    @property
    def executor_type(self) -> str:
        return 'netbox'
    
    def execute(self, target: str, command: str, config: Dict = None) -> Dict:
        """
        Execute a NetBox action.
        
        Args:
            target: Target device/IP (may be unused for some actions)
            command: Action to perform (e.g., 'device.create', 'discover.snmp')
            config: Action parameters
        
        Returns:
            Result dictionary with success, output, data, error
        """
        config = config or {}
        
        # Parse action from command
        action = command.lower().strip()
        
        # Route to appropriate handler
        handlers = {
            # Device CRUD
            'device.create': self._device_create,
            'device.update': self._device_update,
            'device.delete': self._device_delete,
            'device.get': self._device_get,
            'device.list': self._device_list,
            
            # VM CRUD
            'vm.create': self._vm_create,
            'vm.update': self._vm_update,
            'vm.delete': self._vm_delete,
            'vm.get': self._vm_get,
            'vm.list': self._vm_list,
            
            # Interface management
            'interface.create': self._interface_create,
            'interface.update': self._interface_update,
            'interface.list': self._interface_list,
            'interface.assign_ip': self._interface_assign_ip,
            
            # IP Address management
            'ip.create': self._ip_create,
            'ip.update': self._ip_update,
            'ip.list': self._ip_list,
            'ip.assign_primary': self._ip_assign_primary,
            
            # Discovery functions
            'discover.ping': self._discover_ping,
            'discover.snmp': self._discover_snmp,
            'discover.hostname': self._discover_hostname,
            'discover.platform': self._discover_platform,
            'discover.serial': self._discover_serial,
            'discover.interfaces': self._discover_interfaces,
            'discover.full': self._discover_full,
            
            # Bulk operations
            'bulk.update_field': self._bulk_update_field,
            'bulk.tag': self._bulk_tag,
            
            # Lookup/reference
            'lookup.sites': self._lookup_sites,
            'lookup.roles': self._lookup_roles,
            'lookup.platforms': self._lookup_platforms,
            'lookup.device_types': self._lookup_device_types,
            'lookup.manufacturers': self._lookup_manufacturers,
            'lookup.tags': self._lookup_tags,
        }
        
        handler = handlers.get(action)
        if not handler:
            return {
                'success': False,
                'output': '',
                'error': f"Unknown NetBox action: {action}. Available: {', '.join(handlers.keys())}",
                'data': None,
            }
        
        try:
            return handler(target, config)
        except Exception as e:
            logger.exception(f"NetBox action {action} failed: {e}")
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'data': None,
            }
    
    # ==================== DEVICE CRUD ====================
    
    def _device_create(self, target: str, config: Dict) -> Dict:
        """Create a new device in NetBox."""
        service = get_netbox_service()
        
        required = ['name', 'site_id', 'role_id', 'device_type_id']
        missing = [f for f in required if not config.get(f)]
        if missing:
            return {
                'success': False,
                'output': '',
                'error': f"Missing required fields: {', '.join(missing)}",
                'data': None,
            }
        
        device = service.create_device(
            name=config['name'],
            device_type_id=config['device_type_id'],
            role_id=config['role_id'],
            site_id=config['site_id'],
            status=config.get('status', 'active'),
            serial=config.get('serial'),
            asset_tag=config.get('asset_tag'),
            description=config.get('description'),
            comments=config.get('comments'),
            tags=config.get('tags'),
            custom_fields=config.get('custom_fields'),
        )
        
        return {
            'success': True,
            'output': f"Created device: {device['name']} (ID: {device['id']})",
            'error': None,
            'data': device,
        }
    
    def _device_update(self, target: str, config: Dict) -> Dict:
        """Update an existing device."""
        service = get_netbox_service()
        
        device_id = config.get('device_id')
        if not device_id:
            # Try to find by name or target IP
            device = service.get_device_by_name(config.get('name') or target)
            if not device:
                return {
                    'success': False,
                    'output': '',
                    'error': f"Device not found: {config.get('name') or target}",
                    'data': None,
                }
            device_id = device['id']
        
        # Build update data from config
        update_fields = ['name', 'status', 'serial', 'asset_tag', 'description', 
                        'comments', 'site', 'role', 'device_type', 'platform',
                        'primary_ip4', 'primary_ip6', 'custom_fields']
        update_data = {k: v for k, v in config.items() if k in update_fields and v is not None}
        
        if not update_data:
            return {
                'success': False,
                'output': '',
                'error': "No fields to update",
                'data': None,
            }
        
        device = service.update_device(device_id, **update_data)
        
        return {
            'success': True,
            'output': f"Updated device: {device['name']}",
            'error': None,
            'data': device,
        }
    
    def _device_delete(self, target: str, config: Dict) -> Dict:
        """Delete a device."""
        service = get_netbox_service()
        
        device_id = config.get('device_id')
        if not device_id:
            device = service.get_device_by_name(config.get('name') or target)
            if not device:
                return {
                    'success': False,
                    'output': '',
                    'error': f"Device not found: {config.get('name') or target}",
                    'data': None,
                }
            device_id = device['id']
            device_name = device['name']
        else:
            device_name = f"ID:{device_id}"
        
        service.delete_device(device_id)
        
        return {
            'success': True,
            'output': f"Deleted device: {device_name}",
            'error': None,
            'data': {'deleted_id': device_id},
        }
    
    def _device_get(self, target: str, config: Dict) -> Dict:
        """Get a device by ID or name."""
        service = get_netbox_service()
        
        device_id = config.get('device_id')
        if device_id:
            device = service.get_device(device_id)
        else:
            device = service.get_device_by_name(config.get('name') or target)
        
        if not device:
            return {
                'success': False,
                'output': '',
                'error': f"Device not found",
                'data': None,
            }
        
        return {
            'success': True,
            'output': f"Found device: {device['name']}",
            'error': None,
            'data': device,
        }
    
    def _device_list(self, target: str, config: Dict) -> Dict:
        """List devices with optional filters."""
        service = get_netbox_service()
        
        result = service.get_devices(
            site=config.get('site'),
            role=config.get('role'),
            manufacturer=config.get('manufacturer'),
            status=config.get('status'),
            tag=config.get('tag'),
            q=config.get('search'),
            limit=config.get('limit', 100),
            offset=config.get('offset', 0),
        )
        
        devices = result.get('results', [])
        
        return {
            'success': True,
            'output': f"Found {len(devices)} devices (total: {result.get('count', 0)})",
            'error': None,
            'data': {
                'devices': devices,
                'count': result.get('count', 0),
                'next': result.get('next'),
                'previous': result.get('previous'),
            },
        }
    
    # ==================== VM CRUD ====================
    
    def _vm_create(self, target: str, config: Dict) -> Dict:
        """Create a virtual machine in NetBox."""
        service = get_netbox_service()
        
        required = ['name', 'cluster_id']
        missing = [f for f in required if not config.get(f)]
        if missing:
            return {
                'success': False,
                'output': '',
                'error': f"Missing required fields: {', '.join(missing)}",
                'data': None,
            }
        
        data = {
            'name': config['name'],
            'cluster': config['cluster_id'],
            'status': config.get('status', 'active'),
        }
        
        optional = ['role', 'platform', 'vcpus', 'memory', 'disk', 'description', 'comments', 'tags']
        for field in optional:
            if config.get(field):
                data[field] = config[field]
        
        vm = service._request('POST', 'virtualization/virtual-machines/', json=data)
        
        return {
            'success': True,
            'output': f"Created VM: {vm['name']} (ID: {vm['id']})",
            'error': None,
            'data': vm,
        }
    
    def _vm_update(self, target: str, config: Dict) -> Dict:
        """Update a virtual machine."""
        service = get_netbox_service()
        
        vm_id = config.get('vm_id')
        if not vm_id:
            # Find by name
            result = service._request('GET', 'virtualization/virtual-machines/', 
                                      params={'name': config.get('name') or target})
            vms = result.get('results', [])
            if not vms:
                return {
                    'success': False,
                    'output': '',
                    'error': f"VM not found: {config.get('name') or target}",
                    'data': None,
                }
            vm_id = vms[0]['id']
        
        update_fields = ['name', 'status', 'cluster', 'role', 'platform', 
                        'vcpus', 'memory', 'disk', 'description', 'comments']
        update_data = {k: v for k, v in config.items() if k in update_fields and v is not None}
        
        vm = service._request('PATCH', f'virtualization/virtual-machines/{vm_id}/', json=update_data)
        
        return {
            'success': True,
            'output': f"Updated VM: {vm['name']}",
            'error': None,
            'data': vm,
        }
    
    def _vm_delete(self, target: str, config: Dict) -> Dict:
        """Delete a virtual machine."""
        service = get_netbox_service()
        
        vm_id = config.get('vm_id')
        if not vm_id:
            result = service._request('GET', 'virtualization/virtual-machines/', 
                                      params={'name': config.get('name') or target})
            vms = result.get('results', [])
            if not vms:
                return {
                    'success': False,
                    'output': '',
                    'error': f"VM not found: {config.get('name') or target}",
                    'data': None,
                }
            vm_id = vms[0]['id']
            vm_name = vms[0]['name']
        else:
            vm_name = f"ID:{vm_id}"
        
        service._request('DELETE', f'virtualization/virtual-machines/{vm_id}/')
        
        return {
            'success': True,
            'output': f"Deleted VM: {vm_name}",
            'error': None,
            'data': {'deleted_id': vm_id},
        }
    
    def _vm_get(self, target: str, config: Dict) -> Dict:
        """Get a VM by ID or name."""
        service = get_netbox_service()
        
        vm_id = config.get('vm_id')
        if vm_id:
            vm = service._request('GET', f'virtualization/virtual-machines/{vm_id}/')
        else:
            result = service._request('GET', 'virtualization/virtual-machines/', 
                                      params={'name': config.get('name') or target})
            vms = result.get('results', [])
            vm = vms[0] if vms else None
        
        if not vm:
            return {
                'success': False,
                'output': '',
                'error': "VM not found",
                'data': None,
            }
        
        return {
            'success': True,
            'output': f"Found VM: {vm['name']}",
            'error': None,
            'data': vm,
        }
    
    def _vm_list(self, target: str, config: Dict) -> Dict:
        """List VMs with optional filters."""
        service = get_netbox_service()
        
        params = {
            'limit': config.get('limit', 100),
            'offset': config.get('offset', 0),
        }
        
        if config.get('cluster'):
            params['cluster'] = config['cluster']
        if config.get('status'):
            params['status'] = config['status']
        if config.get('role'):
            params['role'] = config['role']
        if config.get('tag'):
            params['tag'] = config['tag']
        
        result = service._request('GET', 'virtualization/virtual-machines/', params=params)
        vms = result.get('results', [])
        
        return {
            'success': True,
            'output': f"Found {len(vms)} VMs (total: {result.get('count', 0)})",
            'error': None,
            'data': {
                'vms': vms,
                'count': result.get('count', 0),
            },
        }
    
    # ==================== INTERFACE MANAGEMENT ====================
    
    def _interface_create(self, target: str, config: Dict) -> Dict:
        """Create an interface on a device."""
        service = get_netbox_service()
        
        device_id = config.get('device_id')
        if not device_id:
            device = service.get_device_by_name(config.get('device_name') or target)
            if not device:
                return {
                    'success': False,
                    'output': '',
                    'error': f"Device not found: {config.get('device_name') or target}",
                    'data': None,
                }
            device_id = device['id']
        
        interface = service.create_interface(
            device_id=device_id,
            name=config.get('name', 'eth0'),
            type=config.get('type', '1000base-t'),
            enabled=config.get('enabled', True),
            description=config.get('description'),
            mac_address=config.get('mac_address'),
        )
        
        return {
            'success': True,
            'output': f"Created interface: {interface['name']}",
            'error': None,
            'data': interface,
        }
    
    def _interface_update(self, target: str, config: Dict) -> Dict:
        """Update an interface."""
        service = get_netbox_service()
        
        interface_id = config.get('interface_id')
        if not interface_id:
            return {
                'success': False,
                'output': '',
                'error': "interface_id is required",
                'data': None,
            }
        
        update_fields = ['name', 'type', 'enabled', 'description', 'mac_address', 'mtu']
        update_data = {k: v for k, v in config.items() if k in update_fields and v is not None}
        
        interface = service._request('PATCH', f'dcim/interfaces/{interface_id}/', json=update_data)
        
        return {
            'success': True,
            'output': f"Updated interface: {interface['name']}",
            'error': None,
            'data': interface,
        }
    
    def _interface_list(self, target: str, config: Dict) -> Dict:
        """List interfaces for a device."""
        service = get_netbox_service()
        
        device_id = config.get('device_id')
        device_name = config.get('device_name') or target
        
        result = service.get_interfaces(
            device_id=device_id,
            device=device_name if not device_id else None,
            limit=config.get('limit', 100),
        )
        
        interfaces = result.get('results', [])
        
        return {
            'success': True,
            'output': f"Found {len(interfaces)} interfaces",
            'error': None,
            'data': {'interfaces': interfaces},
        }
    
    def _interface_assign_ip(self, target: str, config: Dict) -> Dict:
        """Assign an IP address to an interface."""
        service = get_netbox_service()
        
        interface_id = config.get('interface_id')
        ip_address = config.get('ip_address') or target
        
        if not interface_id:
            return {
                'success': False,
                'output': '',
                'error': "interface_id is required",
                'data': None,
            }
        
        # Ensure IP has prefix
        if '/' not in ip_address:
            ip_address = f"{ip_address}/24"
        
        # Check if IP exists
        existing_ip = service.get_ip_address_by_address(ip_address.split('/')[0])
        
        if existing_ip:
            # Update existing IP to assign to interface
            ip_record = service.update_ip_address(
                existing_ip['id'],
                assigned_object_type='dcim.interface',
                assigned_object_id=interface_id
            )
        else:
            # Create new IP assigned to interface
            ip_record = service.create_ip_address(
                address=ip_address,
                assigned_object_type='dcim.interface',
                assigned_object_id=interface_id,
            )
        
        return {
            'success': True,
            'output': f"Assigned {ip_address} to interface",
            'error': None,
            'data': ip_record,
        }
    
    # ==================== IP ADDRESS MANAGEMENT ====================
    
    def _ip_create(self, target: str, config: Dict) -> Dict:
        """Create an IP address."""
        service = get_netbox_service()
        
        address = config.get('address') or target
        if '/' not in address:
            address = f"{address}/{config.get('prefix_length', 24)}"
        
        ip = service.create_ip_address(
            address=address,
            status=config.get('status', 'active'),
            description=config.get('description'),
            dns_name=config.get('dns_name'),
            tags=config.get('tags'),
        )
        
        return {
            'success': True,
            'output': f"Created IP: {ip['address']}",
            'error': None,
            'data': ip,
        }
    
    def _ip_update(self, target: str, config: Dict) -> Dict:
        """Update an IP address."""
        service = get_netbox_service()
        
        ip_id = config.get('ip_id')
        if not ip_id:
            address = config.get('address') or target
            existing = service.get_ip_address_by_address(address)
            if not existing:
                return {
                    'success': False,
                    'output': '',
                    'error': f"IP not found: {address}",
                    'data': None,
                }
            ip_id = existing['id']
        
        update_fields = ['status', 'description', 'dns_name', 'assigned_object_type', 'assigned_object_id']
        update_data = {k: v for k, v in config.items() if k in update_fields and v is not None}
        
        ip = service.update_ip_address(ip_id, **update_data)
        
        return {
            'success': True,
            'output': f"Updated IP: {ip['address']}",
            'error': None,
            'data': ip,
        }
    
    def _ip_list(self, target: str, config: Dict) -> Dict:
        """List IP addresses."""
        service = get_netbox_service()
        
        result = service.get_ip_addresses(
            device=config.get('device'),
            status=config.get('status'),
            limit=config.get('limit', 100),
        )
        
        ips = result.get('results', [])
        
        return {
            'success': True,
            'output': f"Found {len(ips)} IP addresses",
            'error': None,
            'data': {'ip_addresses': ips, 'count': result.get('count', 0)},
        }
    
    def _ip_assign_primary(self, target: str, config: Dict) -> Dict:
        """Set an IP as the primary IP for a device."""
        service = get_netbox_service()
        
        device_id = config.get('device_id')
        ip_id = config.get('ip_id')
        ip_version = config.get('ip_version', 4)
        
        if not device_id:
            device = service.get_device_by_name(config.get('device_name') or target)
            if not device:
                return {
                    'success': False,
                    'output': '',
                    'error': f"Device not found",
                    'data': None,
                }
            device_id = device['id']
        
        if not ip_id:
            address = config.get('ip_address')
            if address:
                ip = service.get_ip_address_by_address(address)
                if ip:
                    ip_id = ip['id']
        
        if not ip_id:
            return {
                'success': False,
                'output': '',
                'error': "ip_id or ip_address is required",
                'data': None,
            }
        
        field = 'primary_ip4' if ip_version == 4 else 'primary_ip6'
        device = service.update_device(device_id, **{field: ip_id})
        
        return {
            'success': True,
            'output': f"Set primary IPv{ip_version} for device",
            'error': None,
            'data': device,
        }
    
    # ==================== DISCOVERY FUNCTIONS ====================
    
    def _discover_ping(self, target: str, config: Dict) -> Dict:
        """
        Ping discovery - check if hosts are reachable and optionally create in NetBox.
        
        Config:
            targets: List of IPs or CIDR range (or use target param)
            create_devices: Whether to create devices in NetBox for responding hosts
            site_id, role_id, device_type_id: Required if create_devices is True
        """
        from .ping_executor import PingExecutor
        
        targets = config.get('targets', [target]) if config.get('targets') else [target]
        create_devices = config.get('create_devices', False)
        
        ping_executor = PingExecutor()
        results = []
        responding = []
        
        for ip in targets:
            result = ping_executor.execute(ip, 'ping', {'count': 1, 'timeout': 2})
            results.append({
                'ip': ip,
                'reachable': result.get('success', False),
                'latency': result.get('data', {}).get('avg_latency'),
            })
            if result.get('success'):
                responding.append(ip)
        
        # Create devices for responding hosts if requested
        created_devices = []
        if create_devices and responding:
            service = get_netbox_service()
            for ip in responding:
                try:
                    result = service.upsert_discovered_device(
                        ip_address=ip,
                        site_id=config.get('site_id'),
                        role_id=config.get('role_id'),
                        device_type_id=config.get('device_type_id'),
                        tags=config.get('tags'),
                    )
                    created_devices.append(result)
                except Exception as e:
                    logger.warning(f"Failed to create device for {ip}: {e}")
        
        return {
            'success': True,
            'output': f"Pinged {len(targets)} hosts, {len(responding)} responding",
            'error': None,
            'data': {
                'results': results,
                'responding': responding,
                'created_devices': created_devices,
            },
        }
    
    def _discover_snmp(self, target: str, config: Dict) -> Dict:
        """
        SNMP discovery - get device info via SNMP and update NetBox.
        
        Config:
            community: SNMP community string
            version: SNMP version (1, 2c, 3)
            update_netbox: Whether to update device in NetBox
        """
        from .snmp_executor import SNMPExecutor
        
        snmp = SNMPExecutor()
        snmp_config = {
            'community': config.get('community', 'public'),
            'version': config.get('version', '2c'),
            'timeout': config.get('timeout', 5),
        }
        
        # Get system info
        sys_name_result = snmp.execute(target, '1.3.6.1.2.1.1.5.0', snmp_config)  # sysName
        sys_descr_result = snmp.execute(target, '1.3.6.1.2.1.1.1.0', snmp_config)  # sysDescr
        sys_contact_result = snmp.execute(target, '1.3.6.1.2.1.1.4.0', snmp_config)  # sysContact
        sys_location_result = snmp.execute(target, '1.3.6.1.2.1.1.6.0', snmp_config)  # sysLocation
        
        discovered = {
            'ip': target,
            'hostname': sys_name_result.get('data', {}).get('value') if sys_name_result.get('success') else None,
            'description': sys_descr_result.get('data', {}).get('value') if sys_descr_result.get('success') else None,
            'contact': sys_contact_result.get('data', {}).get('value') if sys_contact_result.get('success') else None,
            'location': sys_location_result.get('data', {}).get('value') if sys_location_result.get('success') else None,
        }
        
        # Try to detect platform from sysDescr
        if discovered['description']:
            discovered['platform'] = self._detect_platform(discovered['description'])
        
        # Update NetBox if requested
        if config.get('update_netbox') and (discovered['hostname'] or discovered['description']):
            service = get_netbox_service()
            try:
                result = service.upsert_discovered_device(
                    ip_address=target,
                    hostname=discovered['hostname'],
                    description=discovered['description'],
                    site_id=config.get('site_id'),
                    role_id=config.get('role_id'),
                    device_type_id=config.get('device_type_id'),
                )
                discovered['netbox_device'] = result.get('device')
            except Exception as e:
                discovered['netbox_error'] = str(e)
        
        return {
            'success': True,
            'output': f"SNMP discovery for {target}: hostname={discovered.get('hostname')}",
            'error': None,
            'data': discovered,
        }
    
    def _discover_hostname(self, target: str, config: Dict) -> Dict:
        """
        DNS/hostname discovery - resolve hostname and update NetBox.
        """
        discovered = {'ip': target}
        
        # Reverse DNS lookup
        try:
            hostname, _, _ = socket.gethostbyaddr(target)
            discovered['hostname'] = hostname
        except socket.herror:
            discovered['hostname'] = None
        
        # Forward lookup if we have a hostname
        if discovered['hostname']:
            try:
                resolved_ip = socket.gethostbyname(discovered['hostname'])
                discovered['forward_lookup'] = resolved_ip
                discovered['forward_matches'] = resolved_ip == target
            except socket.gaierror:
                discovered['forward_lookup'] = None
        
        # Update NetBox if requested
        if config.get('update_netbox') and discovered['hostname']:
            service = get_netbox_service()
            try:
                result = service.upsert_discovered_device(
                    ip_address=target,
                    hostname=discovered['hostname'],
                    site_id=config.get('site_id'),
                    role_id=config.get('role_id'),
                    device_type_id=config.get('device_type_id'),
                )
                discovered['netbox_device'] = result.get('device')
            except Exception as e:
                discovered['netbox_error'] = str(e)
        
        return {
            'success': True,
            'output': f"Hostname for {target}: {discovered.get('hostname', 'not found')}",
            'error': None,
            'data': discovered,
        }
    
    def _discover_platform(self, target: str, config: Dict) -> Dict:
        """
        Platform detection - detect OS/platform from SNMP or SSH.
        """
        platform = None
        method = None
        raw_info = None
        
        # Try SNMP first
        if config.get('snmp_community'):
            from .snmp_executor import SNMPExecutor
            snmp = SNMPExecutor()
            result = snmp.execute(target, '1.3.6.1.2.1.1.1.0', {
                'community': config['snmp_community'],
                'version': config.get('snmp_version', '2c'),
            })
            if result.get('success'):
                raw_info = result.get('data', {}).get('value')
                platform = self._detect_platform(raw_info)
                method = 'snmp'
        
        # Try SSH if SNMP didn't work
        if not platform and config.get('ssh_credential_id'):
            from .ssh_executor import SSHExecutor
            ssh = SSHExecutor()
            # Try common commands to detect platform
            for cmd in ['uname -a', 'show version', 'cat /etc/os-release']:
                result = ssh.execute(target, cmd, {
                    'credential_id': config['ssh_credential_id'],
                    'timeout': 10,
                })
                if result.get('success'):
                    raw_info = result.get('output')
                    platform = self._detect_platform(raw_info)
                    method = 'ssh'
                    break
        
        return {
            'success': platform is not None,
            'output': f"Platform for {target}: {platform or 'unknown'}",
            'error': None if platform else "Could not detect platform",
            'data': {
                'ip': target,
                'platform': platform,
                'method': method,
                'raw_info': raw_info,
            },
        }
    
    def _discover_serial(self, target: str, config: Dict) -> Dict:
        """
        Serial number discovery via SNMP or SSH.
        """
        serial = None
        method = None
        
        # Try SNMP - Entity MIB serial number OID
        if config.get('snmp_community'):
            from .snmp_executor import SNMPExecutor
            snmp = SNMPExecutor()
            # Try common serial number OIDs
            serial_oids = [
                '1.3.6.1.2.1.47.1.1.1.1.11.1',  # entPhysicalSerialNum
                '1.3.6.1.4.1.9.3.6.3.0',  # Cisco chassis serial
            ]
            for oid in serial_oids:
                result = snmp.execute(target, oid, {
                    'community': config['snmp_community'],
                    'version': config.get('snmp_version', '2c'),
                })
                if result.get('success') and result.get('data', {}).get('value'):
                    serial = result['data']['value']
                    method = 'snmp'
                    break
        
        # Update NetBox if requested
        if config.get('update_netbox') and serial:
            service = get_netbox_service()
            device = service.get_device_by_name(config.get('device_name') or target)
            if device:
                service.update_device(device['id'], serial=serial)
        
        return {
            'success': serial is not None,
            'output': f"Serial for {target}: {serial or 'not found'}",
            'error': None,
            'data': {
                'ip': target,
                'serial': serial,
                'method': method,
            },
        }
    
    def _discover_interfaces(self, target: str, config: Dict) -> Dict:
        """
        Interface discovery via SNMP - discover and sync interfaces to NetBox.
        """
        if not config.get('snmp_community'):
            return {
                'success': False,
                'output': '',
                'error': "snmp_community is required",
                'data': None,
            }
        
        from .snmp_executor import SNMPExecutor
        snmp = SNMPExecutor()
        snmp_config = {
            'community': config['snmp_community'],
            'version': config.get('snmp_version', '2c'),
        }
        
        # Walk interface table
        result = snmp.execute(target, '1.3.6.1.2.1.2.2.1.2', {**snmp_config, 'walk': True})  # ifDescr
        
        interfaces = []
        if result.get('success') and result.get('data', {}).get('results'):
            for item in result['data']['results']:
                interfaces.append({
                    'index': item.get('oid', '').split('.')[-1],
                    'name': item.get('value'),
                })
        
        # Sync to NetBox if requested
        synced = []
        if config.get('sync_netbox') and interfaces:
            service = get_netbox_service()
            device = service.get_device_by_name(config.get('device_name') or target)
            if device:
                for iface in interfaces:
                    try:
                        created = service.create_interface(
                            device_id=device['id'],
                            name=iface['name'],
                            type=config.get('interface_type', '1000base-t'),
                        )
                        synced.append(created)
                    except Exception as e:
                        logger.debug(f"Interface {iface['name']} may already exist: {e}")
        
        return {
            'success': True,
            'output': f"Discovered {len(interfaces)} interfaces on {target}",
            'error': None,
            'data': {
                'interfaces': interfaces,
                'synced': synced,
            },
        }
    
    def _discover_full(self, target: str, config: Dict) -> Dict:
        """
        Full discovery - run all discovery methods and create/update device in NetBox.
        """
        results = {
            'ip': target,
            'hostname': None,
            'description': None,
            'platform': None,
            'serial': None,
            'interfaces': [],
        }
        
        # Hostname discovery
        hostname_result = self._discover_hostname(target, {})
        if hostname_result.get('success'):
            results['hostname'] = hostname_result['data'].get('hostname')
        
        # SNMP discovery if community provided
        if config.get('snmp_community'):
            snmp_result = self._discover_snmp(target, {
                'community': config['snmp_community'],
                'version': config.get('snmp_version', '2c'),
            })
            if snmp_result.get('success'):
                data = snmp_result.get('data', {})
                results['hostname'] = results['hostname'] or data.get('hostname')
                results['description'] = data.get('description')
                results['platform'] = data.get('platform')
            
            # Serial discovery
            serial_result = self._discover_serial(target, {
                'snmp_community': config['snmp_community'],
                'snmp_version': config.get('snmp_version', '2c'),
            })
            if serial_result.get('success'):
                results['serial'] = serial_result['data'].get('serial')
            
            # Interface discovery
            iface_result = self._discover_interfaces(target, {
                'snmp_community': config['snmp_community'],
                'snmp_version': config.get('snmp_version', '2c'),
            })
            if iface_result.get('success'):
                results['interfaces'] = iface_result['data'].get('interfaces', [])
        
        # Create/update in NetBox if requested
        if config.get('update_netbox'):
            service = get_netbox_service()
            try:
                nb_result = service.upsert_discovered_device(
                    ip_address=target,
                    hostname=results['hostname'],
                    description=results['description'],
                    serial=results['serial'],
                    site_id=config.get('site_id'),
                    role_id=config.get('role_id'),
                    device_type_id=config.get('device_type_id'),
                    tags=config.get('tags'),
                )
                results['netbox_device'] = nb_result.get('device')
                results['netbox_created'] = nb_result.get('created')
            except Exception as e:
                results['netbox_error'] = str(e)
        
        return {
            'success': True,
            'output': f"Full discovery for {target}: {results.get('hostname', 'unknown')}",
            'error': None,
            'data': results,
        }
    
    # ==================== BULK OPERATIONS ====================
    
    def _bulk_update_field(self, target: str, config: Dict) -> Dict:
        """
        Update a field on multiple devices.
        
        Config:
            device_ids: List of device IDs
            field: Field name to update
            value: New value
        """
        service = get_netbox_service()
        
        device_ids = config.get('device_ids', [])
        field = config.get('field')
        value = config.get('value')
        
        if not device_ids or not field:
            return {
                'success': False,
                'output': '',
                'error': "device_ids and field are required",
                'data': None,
            }
        
        updated = []
        errors = []
        
        for device_id in device_ids:
            try:
                device = service.update_device(device_id, **{field: value})
                updated.append(device['id'])
            except Exception as e:
                errors.append({'device_id': device_id, 'error': str(e)})
        
        return {
            'success': len(errors) == 0,
            'output': f"Updated {len(updated)} devices, {len(errors)} errors",
            'error': None if not errors else f"{len(errors)} devices failed",
            'data': {
                'updated': updated,
                'errors': errors,
            },
        }
    
    def _bulk_tag(self, target: str, config: Dict) -> Dict:
        """
        Add or remove tags from multiple devices.
        
        Config:
            device_ids: List of device IDs
            tags: List of tag names to add
            remove_tags: List of tag names to remove
        """
        service = get_netbox_service()
        
        device_ids = config.get('device_ids', [])
        add_tags = config.get('tags', [])
        remove_tags = config.get('remove_tags', [])
        
        if not device_ids:
            return {
                'success': False,
                'output': '',
                'error': "device_ids is required",
                'data': None,
            }
        
        updated = []
        errors = []
        
        for device_id in device_ids:
            try:
                # Get current device
                device = service.get_device(device_id)
                current_tags = [t['name'] for t in device.get('tags', [])]
                
                # Modify tags
                new_tags = set(current_tags)
                new_tags.update(add_tags)
                new_tags -= set(remove_tags)
                
                # Update device
                service.update_device(device_id, tags=[{'name': t} for t in new_tags])
                updated.append(device_id)
            except Exception as e:
                errors.append({'device_id': device_id, 'error': str(e)})
        
        return {
            'success': len(errors) == 0,
            'output': f"Updated tags on {len(updated)} devices",
            'error': None if not errors else f"{len(errors)} devices failed",
            'data': {
                'updated': updated,
                'errors': errors,
            },
        }
    
    # ==================== LOOKUP FUNCTIONS ====================
    
    def _lookup_sites(self, target: str, config: Dict) -> Dict:
        """Get available sites."""
        service = get_netbox_service()
        result = service.get_sites(limit=config.get('limit', 500))
        sites = result.get('results', [])
        
        return {
            'success': True,
            'output': f"Found {len(sites)} sites",
            'error': None,
            'data': {'sites': sites},
        }
    
    def _lookup_roles(self, target: str, config: Dict) -> Dict:
        """Get available device roles."""
        service = get_netbox_service()
        result = service.get_device_roles(limit=config.get('limit', 500))
        roles = result.get('results', [])
        
        return {
            'success': True,
            'output': f"Found {len(roles)} roles",
            'error': None,
            'data': {'roles': roles},
        }
    
    def _lookup_platforms(self, target: str, config: Dict) -> Dict:
        """Get available platforms."""
        service = get_netbox_service()
        result = service._request('GET', 'dcim/platforms/', params={'limit': config.get('limit', 500)})
        platforms = result.get('results', [])
        
        return {
            'success': True,
            'output': f"Found {len(platforms)} platforms",
            'error': None,
            'data': {'platforms': platforms},
        }
    
    def _lookup_device_types(self, target: str, config: Dict) -> Dict:
        """Get available device types."""
        service = get_netbox_service()
        result = service.get_device_types(
            manufacturer=config.get('manufacturer'),
            limit=config.get('limit', 500)
        )
        types = result.get('results', [])
        
        return {
            'success': True,
            'output': f"Found {len(types)} device types",
            'error': None,
            'data': {'device_types': types},
        }
    
    def _lookup_manufacturers(self, target: str, config: Dict) -> Dict:
        """Get available manufacturers."""
        service = get_netbox_service()
        result = service.get_manufacturers(limit=config.get('limit', 500))
        manufacturers = result.get('results', [])
        
        return {
            'success': True,
            'output': f"Found {len(manufacturers)} manufacturers",
            'error': None,
            'data': {'manufacturers': manufacturers},
        }
    
    def _lookup_tags(self, target: str, config: Dict) -> Dict:
        """Get available tags."""
        service = get_netbox_service()
        result = service._request('GET', 'extras/tags/', params={'limit': config.get('limit', 500)})
        tags = result.get('results', [])
        
        return {
            'success': True,
            'output': f"Found {len(tags)} tags",
            'error': None,
            'data': {'tags': tags},
        }
    
    # ==================== HELPER METHODS ====================
    
    def _detect_platform(self, sys_descr: str) -> Optional[str]:
        """Detect platform from sysDescr or similar string."""
        if not sys_descr:
            return None
        
        sys_descr_lower = sys_descr.lower()
        
        # Common platform patterns
        patterns = [
            (r'cisco ios', 'cisco-ios'),
            (r'cisco nx-os', 'cisco-nxos'),
            (r'cisco adaptive security', 'cisco-asa'),
            (r'junos', 'juniper-junos'),
            (r'arista', 'arista-eos'),
            (r'palo alto', 'paloalto-panos'),
            (r'fortinet|fortigate', 'fortinet-fortios'),
            (r'linux', 'linux'),
            (r'ubuntu', 'ubuntu'),
            (r'debian', 'debian'),
            (r'centos', 'centos'),
            (r'red hat|rhel', 'rhel'),
            (r'windows', 'windows'),
            (r'vmware esx', 'vmware-esxi'),
            (r'proxmox', 'proxmox'),
            (r'freebsd', 'freebsd'),
            (r'openbsd', 'openbsd'),
            (r'mikrotik|routeros', 'mikrotik-routeros'),
            (r'ubiquiti|unifi', 'ubiquiti-unifi'),
            (r'hp procurve|aruba', 'hpe-aruba'),
            (r'dell emc|dell networking', 'dell-os10'),
        ]
        
        for pattern, platform in patterns:
            if re.search(pattern, sys_descr_lower):
                return platform
        
        return None
