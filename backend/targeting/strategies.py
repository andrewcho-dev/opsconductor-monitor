"""
Targeting strategies for resolving job targets.

Each strategy resolves a targeting configuration to a list of IP addresses.
"""

from typing import Dict, List
from .base import BaseTargeting
from .registry import register_targeting


@register_targeting
class StaticTargeting(BaseTargeting):
    """Targeting strategy for static IP lists."""
    
    @property
    def targeting_type(self) -> str:
        return 'static'
    
    def get_required_fields(self) -> List[str]:
        return ['targets']
    
    def resolve(self, config: Dict) -> List[str]:
        """
        Resolve static target list.
        
        Config:
            targets: List of IP addresses
        
        Returns:
            List of IP addresses
        """
        targets = config.get('targets', [])
        
        if isinstance(targets, str):
            # Handle comma-separated string
            targets = [t.strip() for t in targets.split(',') if t.strip()]
        
        return targets


@register_targeting
class DatabaseQueryTargeting(BaseTargeting):
    """Targeting strategy for database query results."""
    
    @property
    def targeting_type(self) -> str:
        return 'database_query'
    
    def get_required_fields(self) -> List[str]:
        return ['query']
    
    def resolve(self, config: Dict) -> List[str]:
        """
        Resolve targets from database query.
        
        Config:
            query: SQL query that returns ip_address column
            filters: Optional filters to apply
        
        Returns:
            List of IP addresses from query results
        """
        from database import DatabaseManager
        
        query = config.get('query', '')
        filters = config.get('filters', {})
        
        # Handle predefined query types
        if query == 'all_devices':
            return self._get_all_devices(filters)
        elif query == 'devices_with_ssh':
            return self._get_devices_with_ssh(filters)
        elif query == 'devices_with_snmp':
            return self._get_devices_with_snmp(filters)
        elif query == 'optical_interfaces':
            return self._get_optical_interface_devices(filters)
        else:
            # Custom query (be careful with SQL injection)
            return self._execute_custom_query(query)
    
    def _get_all_devices(self, filters: Dict) -> List[str]:
        """Get all devices from scan_results."""
        from database import DatabaseManager
        db = DatabaseManager()
        
        query = "SELECT ip_address::text FROM scan_results"
        conditions = []
        params = []
        
        if filters.get('network_range'):
            conditions.append("network_range = %s")
            params.append(filters['network_range'])
        
        if filters.get('ping_status'):
            conditions.append("ping_status ILIKE %s")
            params.append(f"%{filters['ping_status']}%")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY ip_address"
        
        results = db.execute_query(query, tuple(params) if params else None)
        return [row['ip_address'] for row in results] if results else []
    
    def _get_devices_with_ssh(self, filters: Dict) -> List[str]:
        """Get devices with SSH enabled."""
        from database import DatabaseManager
        db = DatabaseManager()
        
        query = "SELECT ip_address::text FROM scan_results WHERE ssh_status = 'YES' ORDER BY ip_address"
        results = db.execute_query(query)
        return [row['ip_address'] for row in results] if results else []
    
    def _get_devices_with_snmp(self, filters: Dict) -> List[str]:
        """Get devices with SNMP enabled."""
        from database import DatabaseManager
        db = DatabaseManager()
        
        query = "SELECT ip_address::text FROM scan_results WHERE snmp_status = 'YES' ORDER BY ip_address"
        results = db.execute_query(query)
        return [row['ip_address'] for row in results] if results else []
    
    def _get_optical_interface_devices(self, filters: Dict) -> List[str]:
        """Get devices with optical interfaces."""
        from database import DatabaseManager
        db = DatabaseManager()
        
        query = """
            SELECT DISTINCT ip_address::text 
            FROM ssh_cli_scans 
            WHERE is_optical = true 
            ORDER BY ip_address
        """
        results = db.execute_query(query)
        return [row['ip_address'] for row in results] if results else []
    
    def _execute_custom_query(self, query: str) -> List[str]:
        """Execute a custom query (use with caution)."""
        from database import DatabaseManager
        db = DatabaseManager()
        
        # Basic safety check - query must select ip_address
        if 'ip_address' not in query.lower():
            return []
        
        results = db.execute_query(query)
        
        if not results:
            return []
        
        # Try to extract ip_address from results
        targets = []
        for row in results:
            if 'ip_address' in row:
                ip = row['ip_address']
                if isinstance(ip, str):
                    targets.append(ip)
                else:
                    targets.append(str(ip))
        
        return targets


@register_targeting
class GroupTargeting(BaseTargeting):
    """Targeting strategy for device groups."""
    
    @property
    def targeting_type(self) -> str:
        return 'group'
    
    def get_required_fields(self) -> List[str]:
        return ['group_id']
    
    def resolve(self, config: Dict) -> List[str]:
        """
        Resolve targets from a device group.
        
        Config:
            group_id: Device group ID
        
        Returns:
            List of IP addresses in the group
        """
        from database import DatabaseManager
        
        group_id = config.get('group_id')
        if not group_id:
            return []
        
        db = DatabaseManager()
        query = """
            SELECT gd.ip_address::text 
            FROM group_devices gd
            WHERE gd.group_id = %s
            ORDER BY gd.ip_address
        """
        results = db.execute_query(query, (group_id,))
        return [row['ip_address'] for row in results] if results else []


@register_targeting
class NetworkRangeTargeting(BaseTargeting):
    """Targeting strategy for network CIDR ranges."""
    
    @property
    def targeting_type(self) -> str:
        return 'network_range'
    
    def get_required_fields(self) -> List[str]:
        return ['cidr']
    
    def resolve(self, config: Dict) -> List[str]:
        """
        Resolve targets from a network CIDR range.
        
        Config:
            cidr: Network CIDR (e.g., '10.0.0.0/24')
            exclude: Optional list of IPs to exclude
        
        Returns:
            List of IP addresses in the range
        """
        from ..utils.ip import expand_cidr, is_valid_cidr
        
        cidr = config.get('cidr', '')
        exclude = set(config.get('exclude', []))
        
        if not is_valid_cidr(cidr):
            return []
        
        # Expand CIDR to list of IPs
        all_ips = expand_cidr(cidr)
        
        # Apply exclusions
        if exclude:
            all_ips = [ip for ip in all_ips if ip not in exclude]
        
        return all_ips


@register_targeting
class PreviousResultTargeting(BaseTargeting):
    """Targeting strategy that uses results from a previous action."""
    
    @property
    def targeting_type(self) -> str:
        return 'previous_result'
    
    def get_required_fields(self) -> List[str]:
        return ['field']
    
    def resolve(self, config: Dict) -> List[str]:
        """
        Resolve targets from previous action results.
        
        This is typically used in multi-step jobs where one action
        discovers targets for subsequent actions.
        
        Config:
            field: Field name containing IP addresses in previous results
            previous_results: Results from previous action (injected at runtime)
        
        Returns:
            List of IP addresses from previous results
        """
        field = config.get('field', 'ip_address')
        previous_results = config.get('previous_results', [])
        
        targets = []
        for result in previous_results:
            if isinstance(result, dict) and field in result:
                value = result[field]
                if isinstance(value, str):
                    targets.append(value)
                elif isinstance(value, list):
                    targets.extend(value)
        
        return targets
