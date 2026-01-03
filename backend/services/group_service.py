"""
Group service for business logic related to device groups.

Handles group CRUD operations and device membership management.
"""

from typing import Dict, List, Optional
from .base import BaseService
from ..repositories.group_repo import GroupRepository
from ..utils.errors import NotFoundError, ValidationError, ConflictError
from ..utils.validation import validate_required, validate_ip_address, validate_positive_int


class GroupService(BaseService):
    """Service for device group business logic."""
    
    def __init__(self, group_repo: GroupRepository):
        """
        Initialize group service.
        
        Args:
            group_repo: Group repository instance
        """
        super().__init__(group_repo)
        self.group_repo = group_repo
    
    def get_group(self, group_id: int) -> Dict:
        """
        Get a group by ID.
        
        Args:
            group_id: Group ID
        
        Returns:
            Group record
        
        Raises:
            NotFoundError: If group not found
        """
        group = self.group_repo.get_by_id(group_id)
        if not group:
            raise NotFoundError('Device Group', str(group_id))
        return group
    
    def get_group_with_devices(self, group_id: int) -> Dict:
        """
        Get a group with its device list.
        
        Args:
            group_id: Group ID
        
        Returns:
            Group with devices
        
        Raises:
            NotFoundError: If group not found
        """
        group = self.group_repo.get_group_with_devices(group_id)
        if not group:
            raise NotFoundError('Device Group', str(group_id))
        return group
    
    def list_groups(self) -> List[Dict]:
        """
        List all device groups with device counts.
        
        Returns:
            List of groups
        """
        return self.group_repo.get_all_groups()
    
    def create_group(self, group_name: str, description: str = None) -> Dict:
        """
        Create a new device group.
        
        Args:
            group_name: Group name
            description: Optional description
        
        Returns:
            Created group
        
        Raises:
            ValidationError: If group_name is empty
        """
        validate_required(group_name, 'group_name')
        
        return self.group_repo.create_group(group_name, description)
    
    def update_group(
        self, 
        group_id: int, 
        group_name: str = None, 
        description: str = None
    ) -> Dict:
        """
        Update a device group.
        
        Args:
            group_id: Group ID
            group_name: New group name
            description: New description
        
        Returns:
            Updated group
        
        Raises:
            NotFoundError: If group not found
        """
        # Verify group exists
        self.get_group(group_id)
        
        return self.group_repo.update_group(group_id, group_name, description)
    
    def delete_group(self, group_id: int) -> bool:
        """
        Delete a device group.
        
        Args:
            group_id: Group ID
        
        Returns:
            True if deleted
        
        Raises:
            NotFoundError: If group not found
        """
        # Verify group exists
        self.get_group(group_id)
        
        return self.group_repo.delete_group(group_id)
    
    def add_device(self, group_id: int, ip_address: str) -> bool:
        """
        Add a device to a group.
        
        Args:
            group_id: Group ID
            ip_address: Device IP address
        
        Returns:
            True if added
        
        Raises:
            NotFoundError: If group not found
            ValidationError: If IP address is invalid
        """
        # Verify group exists
        self.get_group(group_id)
        validate_ip_address(ip_address)
        
        return self.group_repo.add_device_to_group(group_id, ip_address)
    
    def add_devices(self, group_id: int, ip_addresses: List[str]) -> Dict:
        """
        Add multiple devices to a group.
        
        Args:
            group_id: Group ID
            ip_addresses: List of device IP addresses
        
        Returns:
            Result with count of added devices
        
        Raises:
            NotFoundError: If group not found
        """
        # Verify group exists
        self.get_group(group_id)
        
        added = 0
        failed = []
        
        for ip in ip_addresses:
            try:
                validate_ip_address(ip)
                if self.group_repo.add_device_to_group(group_id, ip):
                    added += 1
            except Exception as e:
                failed.append({'ip': ip, 'error': str(e)})
        
        return {
            'added': added,
            'failed': failed,
            'total_requested': len(ip_addresses)
        }
    
    def remove_device(self, group_id: int, ip_address: str) -> bool:
        """
        Remove a device from a group.
        
        Args:
            group_id: Group ID
            ip_address: Device IP address
        
        Returns:
            True if removed
        
        Raises:
            NotFoundError: If group not found
        """
        # Verify group exists
        self.get_group(group_id)
        
        return self.group_repo.remove_device_from_group(group_id, ip_address)
    
    def get_device_groups(self, ip_address: str) -> List[Dict]:
        """
        Get all groups a device belongs to.
        
        Args:
            ip_address: Device IP address
        
        Returns:
            List of groups
        """
        validate_ip_address(ip_address)
        return self.group_repo.get_groups_for_device(ip_address)
