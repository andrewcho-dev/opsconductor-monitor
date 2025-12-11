"""
Device repository for scan_results table operations.

Handles all database operations related to network devices.
"""

from typing import Dict, List, Optional, Any
from .base import BaseRepository
from ..utils.serialization import serialize_row, serialize_rows


class DeviceRepository(BaseRepository):
    """Repository for device (scan_results) operations."""
    
    table_name = 'scan_results'
    primary_key = 'id'
    resource_name = 'Device'
    
    def get_by_ip(self, ip_address: str, serialize: bool = True) -> Optional[Dict]:
        """
        Get a device by IP address.
        
        Args:
            ip_address: Device IP address
            serialize: Whether to serialize the result
        
        Returns:
            Device record or None
        """
        query = "SELECT * FROM scan_results WHERE ip_address = %s"
        results = self.execute_query(query, (ip_address,))
        
        if not results:
            return None
        
        return serialize_row(results[0]) if serialize else results[0]
    
    def get_all_devices(self, serialize: bool = True) -> List[Dict]:
        """
        Get all devices with full details.
        
        Returns:
            List of device records
        """
        query = """
            SELECT 
                id,
                ip_address::text as ip_address,
                network_range,
                ping_status,
                snmp_status,
                ssh_status,
                rdp_status,
                scan_timestamp,
                snmp_description,
                snmp_hostname,
                snmp_location,
                snmp_contact,
                snmp_uptime,
                snmp_vendor_oid,
                snmp_vendor_name,
                snmp_model,
                snmp_chassis_mac,
                snmp_serial
            FROM scan_results 
            ORDER BY ip_address
        """
        results = self.execute_query(query)
        
        return serialize_rows(results) if serialize else results
    
    def get_devices_by_network(self, network_range: str) -> List[Dict]:
        """
        Get all devices in a specific network range.
        
        Args:
            network_range: Network CIDR (e.g., '10.0.0.0/24')
        
        Returns:
            List of devices in the network
        """
        return self.get_all(filters={'network_range': network_range})
    
    def get_devices_by_status(self, status_field: str, status_value: str) -> List[Dict]:
        """
        Get devices by status field value.
        
        Args:
            status_field: Status field name (ping_status, snmp_status, etc.)
            status_value: Status value to match
        
        Returns:
            List of matching devices
        """
        valid_fields = ['ping_status', 'snmp_status', 'ssh_status', 'rdp_status']
        if status_field not in valid_fields:
            raise ValueError(f"Invalid status field: {status_field}")
        
        return self.get_all(filters={status_field: status_value})
    
    def upsert_device(
        self,
        ip_address: str,
        ping_status: str = None,
        scan_timestamp: str = None,
        network_range: str = None,
        snmp_status: str = None,
        ssh_status: str = None,
        rdp_status: str = None,
        snmp_data: Dict = None
    ) -> Optional[Dict]:
        """
        Insert or update a device record.
        
        Args:
            ip_address: Device IP address
            ping_status: Ping status
            scan_timestamp: Scan timestamp
            network_range: Network CIDR
            snmp_status: SNMP status
            ssh_status: SSH status
            rdp_status: RDP status
            snmp_data: Dictionary of SNMP fields
        
        Returns:
            Upserted device record
        """
        data = {'ip_address': ip_address}
        
        if ping_status is not None:
            data['ping_status'] = ping_status
        if scan_timestamp is not None:
            data['scan_timestamp'] = scan_timestamp
        if network_range is not None:
            data['network_range'] = network_range
        if snmp_status is not None:
            data['snmp_status'] = snmp_status
        if ssh_status is not None:
            data['ssh_status'] = ssh_status
        if rdp_status is not None:
            data['rdp_status'] = rdp_status
        
        # Add SNMP data fields
        if snmp_data:
            snmp_fields = [
                'snmp_description', 'snmp_hostname', 'snmp_location',
                'snmp_contact', 'snmp_uptime', 'snmp_vendor_oid',
                'snmp_vendor_name', 'snmp_model', 'snmp_chassis_mac', 'snmp_serial'
            ]
            for field in snmp_fields:
                if field in snmp_data:
                    data[field] = snmp_data[field]
        
        return self.upsert(
            data=data,
            conflict_columns=['ip_address'],
            update_columns=[k for k in data.keys() if k != 'ip_address']
        )
    
    def delete_by_ip(self, ip_address: str) -> bool:
        """
        Delete a device by IP address.
        
        Args:
            ip_address: Device IP address
        
        Returns:
            True if device was deleted
        """
        query = "DELETE FROM scan_results WHERE ip_address = %s RETURNING id"
        results = self.execute_query(query, (ip_address,))
        return bool(results)
    
    def get_network_summary(self) -> List[Dict]:
        """
        Get summary of devices grouped by network range.
        
        Returns:
            List of network summaries with device counts
        """
        query = """
            SELECT 
                network_range,
                COUNT(*) as device_count,
                COUNT(*) FILTER (WHERE ping_status ILIKE '%online%' OR ping_status ILIKE '%responds%') as online_count,
                COUNT(*) FILTER (WHERE snmp_status = 'YES') as snmp_count,
                COUNT(*) FILTER (WHERE ssh_status = 'YES') as ssh_count
            FROM scan_results
            GROUP BY network_range
            ORDER BY network_range
        """
        results = self.execute_query(query)
        
        from backend.utils.serialization import serialize_rows
        return serialize_rows(results)
    
    def search_devices(self, search_term: str, limit: int = 100) -> List[Dict]:
        """
        Search devices by IP, hostname, or description.
        
        Args:
            search_term: Search string
            limit: Maximum results
        
        Returns:
            List of matching devices
        """
        query = """
            SELECT * FROM scan_results
            WHERE ip_address::text ILIKE %s
               OR snmp_hostname ILIKE %s
               OR snmp_description ILIKE %s
            ORDER BY ip_address
            LIMIT %s
        """
        search_pattern = f'%{search_term}%'
        results = self.execute_query(query, (search_pattern, search_pattern, search_pattern, limit))
        
        from backend.utils.serialization import serialize_rows
        return serialize_rows(results)
