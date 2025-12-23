"""
Group repository for device_groups and group_devices table operations.

Handles all database operations related to device groups.
"""

from typing import Dict, List, Optional, Any
from .base import BaseRepository
from ..utils.serialization import serialize_rows


class GroupRepository(BaseRepository):
    """Repository for device_groups operations."""
    
    table_name = 'device_groups'
    primary_key = 'id'
    resource_name = 'Device Group'
    
    def get_all_groups(self) -> List[Dict]:
        """
        Get all device groups with device counts.
        
        Returns:
            List of groups with device counts
        """
        query = """
            SELECT 
                dg.id,
                dg.group_name,
                dg.description,
                dg.created_at,
                COUNT(gd.ip_address) as device_count
            FROM device_groups dg
            LEFT JOIN group_devices gd ON dg.id = gd.group_id
            GROUP BY dg.id, dg.group_name, dg.description, dg.created_at
            ORDER BY dg.group_name
        """
        results = self.execute_query(query)
        
        return serialize_rows(results)
    
    def get_group_with_devices(self, group_id: int) -> Optional[Dict]:
        """
        Get a group with its device list.
        
        Args:
            group_id: Group ID
        
        Returns:
            Group with devices or None
        """
        # Get group info
        group = self.get_by_id(group_id)
        if not group:
            return None
        
        # Get devices in group
        devices = self.get_group_devices(group_id)
        group['devices'] = devices
        
        return group
    
    def create_group(self, group_name: str, description: str = None) -> Optional[Dict]:
        """
        Create a new device group.
        
        Args:
            group_name: Group name
            description: Optional description
        
        Returns:
            Created group
        """
        data = {'group_name': group_name}
        if description:
            data['description'] = description
        
        return self.create(data)
    
    def update_group(
        self, 
        group_id: int, 
        group_name: str = None, 
        description: str = None
    ) -> Optional[Dict]:
        """
        Update a device group.
        
        Args:
            group_id: Group ID
            group_name: New group name
            description: New description
        
        Returns:
            Updated group
        """
        data = {}
        if group_name is not None:
            data['group_name'] = group_name
        if description is not None:
            data['description'] = description
        
        if not data:
            return self.get_by_id(group_id)
        
        return self.update(group_id, data)
    
    def delete_group(self, group_id: int) -> bool:
        """
        Delete a device group and its device associations.
        
        Args:
            group_id: Group ID
        
        Returns:
            True if deleted
        """
        # Delete device associations first
        self.execute_query(
            "DELETE FROM group_devices WHERE group_id = %s",
            (group_id,),
            fetch=False
        )
        
        # Delete group
        return self.delete(group_id)
    
    def get_group_devices(self, group_id: int) -> List[Dict]:
        """
        Get all devices in a group.
        
        UPDATED: Now fetches device details from NetBox.
        Group membership (IP addresses) stored locally, device info from NetBox.
        
        Args:
            group_id: Group ID
        
        Returns:
            List of devices
        """
        # Get IP addresses in this group
        query = """
            SELECT ip_address::text as ip_address
            FROM group_devices
            WHERE group_id = %s
            ORDER BY ip_address
        """
        results = self.execute_query(query, (group_id,))
        group_ips = set(row['ip_address'] for row in results) if results else set()
        
        if not group_ips:
            return []
        
        # Fetch device details from NetBox
        try:
            from ..services.netbox_service import NetBoxService
            from ..api.netbox import get_netbox_settings
            
            settings = get_netbox_settings()
            netbox = NetBoxService(
                url=settings.get('url', ''),
                token=settings.get('token', ''),
                verify_ssl=settings.get('verify_ssl', 'true').lower() == 'true'
            )
            
            if not netbox.is_configured:
                # Return just IPs if NetBox not configured
                return [{'ip_address': ip} for ip in sorted(group_ips)]
            
            # Get all devices from NetBox and filter by group IPs
            result = netbox.get_devices(limit=10000)
            netbox_devices = result.get('results', [])
            
            devices = []
            for d in netbox_devices:
                primary_ip = d.get('primary_ip4') or d.get('primary_ip') or {}
                ip_address = primary_ip.get('address', '').split('/')[0] if primary_ip else None
                
                if ip_address and ip_address in group_ips:
                    devices.append({
                        'ip_address': ip_address,
                        'snmp_hostname': d.get('name', ''),
                        'snmp_description': d.get('description', ''),
                        'ping_status': 'online' if d.get('status', {}).get('value') == 'active' else 'offline',
                        'snmp_status': 'YES',
                        'ssh_status': '',
                        'site': d.get('site', {}).get('name', '') if d.get('site') else '',
                        'role': d.get('role', {}).get('name', '') if d.get('role') else '',
                    })
            
            return sorted(devices, key=lambda x: x.get('ip_address', ''))
            
        except Exception as e:
            # Fallback to just IPs on error
            return [{'ip_address': ip} for ip in sorted(group_ips)]
    
    def add_device_to_group(self, group_id: int, ip_address: str) -> bool:
        """
        Add a device to a group.
        
        Args:
            group_id: Group ID
            ip_address: Device IP address
        
        Returns:
            True if added (or already exists)
        """
        query = """
            INSERT INTO group_devices (group_id, ip_address)
            VALUES (%s, %s)
            ON CONFLICT (group_id, ip_address) DO NOTHING
        """
        self.execute_query(query, (group_id, ip_address), fetch=False)
        return True
    
    def add_devices_to_group(self, group_id: int, ip_addresses: List[str]) -> int:
        """
        Add multiple devices to a group.
        
        Args:
            group_id: Group ID
            ip_addresses: List of device IP addresses
        
        Returns:
            Number of devices added
        """
        added = 0
        for ip in ip_addresses:
            if self.add_device_to_group(group_id, ip):
                added += 1
        return added
    
    def remove_device_from_group(self, group_id: int, ip_address: str) -> bool:
        """
        Remove a device from a group.
        
        Args:
            group_id: Group ID
            ip_address: Device IP address
        
        Returns:
            True if removed
        """
        query = "DELETE FROM group_devices WHERE group_id = %s AND ip_address = %s RETURNING group_id"
        results = self.execute_query(query, (group_id, ip_address))
        return bool(results)
    
    def get_groups_for_device(self, ip_address: str) -> List[Dict]:
        """
        Get all groups a device belongs to.
        
        Args:
            ip_address: Device IP address
        
        Returns:
            List of groups
        """
        query = """
            SELECT dg.id, dg.group_name, dg.description
            FROM device_groups dg
            JOIN group_devices gd ON dg.id = gd.group_id
            WHERE gd.ip_address = %s
            ORDER BY dg.group_name
        """
        results = self.execute_query(query, (ip_address,))
        
        return serialize_rows(results)
    
    def is_device_in_group(self, group_id: int, ip_address: str) -> bool:
        """
        Check if a device is in a group.
        
        Args:
            group_id: Group ID
            ip_address: Device IP address
        
        Returns:
            True if device is in group
        """
        query = "SELECT 1 FROM group_devices WHERE group_id = %s AND ip_address = %s LIMIT 1"
        results = self.execute_query(query, (group_id, ip_address))
        return bool(results)
