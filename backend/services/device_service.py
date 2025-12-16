"""
Device service for business logic related to network devices.

Handles device operations, filtering, and coordination with groups.

DEPRECATION NOTICE:
This service uses the local scan_results table for device inventory.
For new deployments, use NetBox as the source of truth for device inventory.
See backend/services/netbox_service.py for the NetBox integration.

The local scan_results table will be maintained for backwards compatibility
but new features should use the NetBox integration.
"""

from typing import Dict, List, Optional, Any
from .base import BaseService
from ..repositories.device_repo import DeviceRepository
from ..repositories.group_repo import GroupRepository
from ..utils.errors import NotFoundError, ValidationError
from ..utils.validation import validate_ip_address, validate_required


class DeviceService(BaseService):
    """Service for device-related business logic."""
    
    def __init__(self, device_repo: DeviceRepository, group_repo: GroupRepository = None):
        """
        Initialize device service.
        
        Args:
            device_repo: Device repository instance
            group_repo: Optional group repository for group operations
        """
        super().__init__(device_repo)
        self.device_repo = device_repo
        self.group_repo = group_repo
    
    def get_device(self, ip_address: str) -> Dict:
        """
        Get a device by IP address.
        
        Args:
            ip_address: Device IP address
        
        Returns:
            Device record
        
        Raises:
            NotFoundError: If device not found
        """
        validate_ip_address(ip_address)
        device = self.device_repo.get_by_ip(ip_address)
        
        if not device:
            raise NotFoundError('Device', ip_address)
        
        return device
    
    def get_device_with_groups(self, ip_address: str) -> Dict:
        """
        Get a device with its group memberships.
        
        Args:
            ip_address: Device IP address
        
        Returns:
            Device record with 'groups' field
        
        Raises:
            NotFoundError: If device not found
        """
        device = self.get_device(ip_address)
        
        if self.group_repo:
            device['groups'] = self.group_repo.get_groups_for_device(ip_address)
        else:
            device['groups'] = []
        
        return device
    
    def list_devices(
        self, 
        filter_type: str = None,
        filter_id: str = None,
        search: str = None
    ) -> List[Dict]:
        """
        List devices with optional filtering.
        
        Args:
            filter_type: Filter type ('network', 'group', 'status')
            filter_id: Filter value (network range, group ID, status value)
            search: Search term for IP/hostname/description
        
        Returns:
            List of devices
        """
        if search:
            return self.device_repo.search_devices(search)
        
        if filter_type == 'network' and filter_id:
            return self.device_repo.get_devices_by_network(filter_id)
        
        if filter_type == 'group' and filter_id and self.group_repo:
            return self.group_repo.get_group_devices(int(filter_id))
        
        if filter_type == 'status' and filter_id:
            # Parse status filter (e.g., 'ping:online', 'snmp:YES')
            if ':' in filter_id:
                field, value = filter_id.split(':', 1)
                field_map = {
                    'ping': 'ping_status',
                    'snmp': 'snmp_status',
                    'ssh': 'ssh_status',
                    'rdp': 'rdp_status'
                }
                if field in field_map:
                    return self.device_repo.get_devices_by_status(field_map[field], value)
        
        return self.device_repo.get_all_devices()
    
    def create_or_update_device(
        self,
        ip_address: str,
        ping_status: str = None,
        network_range: str = None,
        snmp_status: str = None,
        ssh_status: str = None,
        rdp_status: str = None,
        snmp_data: Dict = None
    ) -> Dict:
        """
        Create or update a device record.
        
        Args:
            ip_address: Device IP address
            ping_status: Ping status
            network_range: Network CIDR
            snmp_status: SNMP status
            ssh_status: SSH status
            rdp_status: RDP status
            snmp_data: SNMP data dictionary
        
        Returns:
            Created/updated device record
        """
        validate_ip_address(ip_address)
        
        from ..utils.time import now_iso
        
        return self.device_repo.upsert_device(
            ip_address=ip_address,
            ping_status=ping_status,
            scan_timestamp=now_iso(),
            network_range=network_range,
            snmp_status=snmp_status,
            ssh_status=ssh_status,
            rdp_status=rdp_status,
            snmp_data=snmp_data
        )
    
    def delete_device(self, ip_address: str) -> bool:
        """
        Delete a device.
        
        Args:
            ip_address: Device IP address
        
        Returns:
            True if deleted
        
        Raises:
            NotFoundError: If device not found
        """
        validate_ip_address(ip_address)
        
        if not self.device_repo.delete_by_ip(ip_address):
            raise NotFoundError('Device', ip_address)
        
        return True
    
    def get_network_summary(self) -> List[Dict]:
        """
        Get summary of devices grouped by network.
        
        Returns:
            List of network summaries
        """
        return self.device_repo.get_network_summary()
    
    def get_device_stats(self) -> Dict:
        """
        Get overall device statistics.
        
        Returns:
            Statistics dictionary
        """
        devices = self.device_repo.get_all_devices()
        
        total = len(devices)
        ping_online = sum(1 for d in devices if d.get('ping_status', '').lower() in ['online', 'responds'])
        snmp_enabled = sum(1 for d in devices if d.get('snmp_status', '').upper() == 'YES')
        ssh_enabled = sum(1 for d in devices if d.get('ssh_status', '').upper() == 'YES')
        
        networks = set(d.get('network_range') for d in devices if d.get('network_range'))
        
        return {
            'total_devices': total,
            'ping_online': ping_online,
            'ping_offline': total - ping_online,
            'snmp_enabled': snmp_enabled,
            'ssh_enabled': ssh_enabled,
            'network_count': len(networks)
        }
