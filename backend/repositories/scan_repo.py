"""
Scan repository for ssh_cli_scans and optical_power_history table operations.

Handles all database operations related to interface scans and optical power data.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import BaseRepository
from ..utils.serialization import serialize_rows


class ScanRepository(BaseRepository):
    """Repository for ssh_cli_scans and related operations."""
    
    table_name = 'ssh_cli_scans'
    primary_key = 'id'
    resource_name = 'Scan Result'
    
    def get_scans_for_device(
        self, 
        ip_address: str, 
        limit: int = 100
    ) -> List[Dict]:
        """
        Get scan results for a specific device.
        
        Args:
            ip_address: Device IP address
            limit: Maximum results
        
        Returns:
            List of scan records
        """
        query = """
            SELECT * FROM ssh_cli_scans
            WHERE ip_address = %s
            ORDER BY scan_timestamp DESC
            LIMIT %s
        """
        results = self.execute_query(query, (ip_address, limit))
        
        return serialize_rows(results)
    
    def get_latest_scans_for_device(self, ip_address: str) -> List[Dict]:
        """
        Get the most recent scan for each interface on a device.
        
        Args:
            ip_address: Device IP address
        
        Returns:
            List of latest scan records per interface
        """
        query = """
            SELECT DISTINCT ON (interface_index) *
            FROM ssh_cli_scans
            WHERE ip_address = %s
            ORDER BY interface_index, scan_timestamp DESC
        """
        results = self.execute_query(query, (ip_address,))
        
        return serialize_rows(results)
    
    def upsert_interface_scan(
        self,
        ip_address: str,
        interface_index: int,
        interface_name: str,
        cli_port: int,
        is_optical: bool = False,
        medium: str = None,
        connector: str = None,
        speed: str = None,
        tx_power: float = None,
        rx_power: float = None,
        temperature: float = None,
        status: str = None,
        raw_output: str = None,
        lldp_data: Dict = None
    ) -> Optional[Dict]:
        """
        Insert or update an interface scan record.
        
        Args:
            ip_address: Device IP address
            interface_index: Interface index
            interface_name: Interface name
            cli_port: CLI port number
            is_optical: Whether interface is optical
            medium: Medium type
            connector: Connector type
            speed: Interface speed
            tx_power: TX power reading
            rx_power: RX power reading
            temperature: Temperature reading
            status: Interface status
            raw_output: Raw command output
            lldp_data: LLDP neighbor data
        
        Returns:
            Upserted record
        """
        data = {
            'ip_address': ip_address,
            'interface_index': interface_index,
            'interface_name': interface_name,
            'cli_port': cli_port,
            'scan_timestamp': datetime.utcnow(),
            'is_optical': is_optical
        }
        
        if medium is not None:
            data['medium'] = medium
        if connector is not None:
            data['connector'] = connector
        if speed is not None:
            data['speed'] = speed
        if tx_power is not None:
            data['tx_power'] = tx_power
        if rx_power is not None:
            data['rx_power'] = rx_power
        if temperature is not None:
            data['temperature'] = temperature
        if status is not None:
            data['status'] = status
        if raw_output is not None:
            data['raw_output'] = raw_output
        
        if lldp_data:
            data['lldp_remote_port'] = lldp_data.get('remote_port')
            data['lldp_remote_mgmt_addr'] = lldp_data.get('remote_mgmt_addr')
            data['lldp_remote_chassis_id'] = lldp_data.get('remote_chassis_id')
            data['lldp_remote_system_name'] = lldp_data.get('remote_system_name')
            data['lldp_raw_info'] = lldp_data.get('raw_info')
        
        return self.upsert(
            data=data,
            conflict_columns=['ip_address', 'interface_index'],
            update_columns=[k for k in data.keys() if k not in ['ip_address', 'interface_index']]
        )
    
    def get_optical_interfaces(self, ip_address: str = None) -> List[Dict]:
        """
        Get all optical interfaces.
        
        Args:
            ip_address: Optional device filter
        
        Returns:
            List of optical interfaces
        """
        if ip_address:
            query = """
                SELECT DISTINCT ON (ip_address, interface_index) *
                FROM ssh_cli_scans
                WHERE ip_address = %s AND is_optical = true
                ORDER BY ip_address, interface_index, scan_timestamp DESC
            """
            results = self.execute_query(query, (ip_address,))
        else:
            query = """
                SELECT DISTINCT ON (ip_address, interface_index) *
                FROM ssh_cli_scans
                WHERE is_optical = true
                ORDER BY ip_address, interface_index, scan_timestamp DESC
            """
            results = self.execute_query(query)
        
        return serialize_rows(results)


class OpticalPowerRepository(BaseRepository):
    """Repository for optical_power_history operations."""
    
    table_name = 'optical_power_history'
    primary_key = 'id'
    resource_name = 'Optical Power Reading'
    
    def insert_reading(
        self,
        ip_address: str,
        interface_index: int,
        interface_name: str,
        cli_port: int,
        tx_power: float = None,
        rx_power: float = None,
        temperature: float = None,
        tx_power_unit: str = 'dBm',
        rx_power_unit: str = 'dBm',
        temperature_unit: str = 'C'
    ) -> Optional[Dict]:
        """
        Insert an optical power reading.
        
        Args:
            ip_address: Device IP address
            interface_index: Interface index
            interface_name: Interface name
            cli_port: CLI port number
            tx_power: TX power value
            rx_power: RX power value
            temperature: Temperature value
            tx_power_unit: TX power unit
            rx_power_unit: RX power unit
            temperature_unit: Temperature unit
        
        Returns:
            Created record
        """
        data = {
            'ip_address': ip_address,
            'interface_index': interface_index,
            'interface_name': interface_name,
            'cli_port': cli_port,
            'measurement_timestamp': datetime.utcnow(),
            'tx_power': tx_power,
            'rx_power': rx_power,
            'temperature': temperature,
            'tx_power_unit': tx_power_unit,
            'rx_power_unit': rx_power_unit,
            'temperature_unit': temperature_unit
        }
        
        return self.create(data)
    
    def get_power_history(
        self,
        ip_address: str,
        interface_index: int = None,
        hours: int = 24
    ) -> List[Dict]:
        """
        Get optical power history for a device/interface.
        
        Args:
            ip_address: Device IP address
            interface_index: Optional interface filter
            hours: Time window in hours
        
        Returns:
            List of power readings
        """
        if interface_index is not None:
            query = """
                SELECT * FROM optical_power_history
                WHERE ip_address = %s 
                  AND interface_index = %s
                  AND measurement_timestamp >= NOW() - INTERVAL '%s hours'
                ORDER BY measurement_timestamp DESC
            """
            results = self.execute_query(query, (ip_address, interface_index, hours))
        else:
            query = """
                SELECT * FROM optical_power_history
                WHERE ip_address = %s 
                  AND measurement_timestamp >= NOW() - INTERVAL '%s hours'
                ORDER BY measurement_timestamp DESC
            """
            results = self.execute_query(query, (ip_address, hours))
        
        return serialize_rows(results)
    
    def get_power_trends(
        self,
        ip_address: str,
        interface_index: int,
        days: int = 7
    ) -> Dict:
        """
        Get power trend statistics for an interface.
        
        Args:
            ip_address: Device IP address
            interface_index: Interface index
            days: Time window in days
        
        Returns:
            Trend statistics
        """
        query = """
            SELECT 
                MIN(tx_power) as tx_min,
                MAX(tx_power) as tx_max,
                AVG(tx_power) as tx_avg,
                MIN(rx_power) as rx_min,
                MAX(rx_power) as rx_max,
                AVG(rx_power) as rx_avg,
                MIN(temperature) as temp_min,
                MAX(temperature) as temp_max,
                AVG(temperature) as temp_avg,
                COUNT(*) as reading_count
            FROM optical_power_history
            WHERE ip_address = %s 
              AND interface_index = %s
              AND measurement_timestamp >= NOW() - INTERVAL '%s days'
        """
        results = self.execute_query(query, (ip_address, interface_index, days))
        
        if results:
            row = results[0]
            return {
                'tx_power': {
                    'min': float(row['tx_min']) if row['tx_min'] else None,
                    'max': float(row['tx_max']) if row['tx_max'] else None,
                    'avg': float(row['tx_avg']) if row['tx_avg'] else None
                },
                'rx_power': {
                    'min': float(row['rx_min']) if row['rx_min'] else None,
                    'max': float(row['rx_max']) if row['rx_max'] else None,
                    'avg': float(row['rx_avg']) if row['rx_avg'] else None
                },
                'temperature': {
                    'min': float(row['temp_min']) if row['temp_min'] else None,
                    'max': float(row['temp_max']) if row['temp_max'] else None,
                    'avg': float(row['temp_avg']) if row['temp_avg'] else None
                },
                'reading_count': row['reading_count'] or 0
            }
        
        return {
            'tx_power': {'min': None, 'max': None, 'avg': None},
            'rx_power': {'min': None, 'max': None, 'avg': None},
            'temperature': {'min': None, 'max': None, 'avg': None},
            'reading_count': 0
        }
    
    def cleanup_old_readings(self, days: int = 90) -> int:
        """
        Delete readings older than specified days.
        
        Args:
            days: Age threshold in days
        
        Returns:
            Number of deleted records
        """
        query = """
            DELETE FROM optical_power_history
            WHERE measurement_timestamp < NOW() - INTERVAL '%s days'
            RETURNING id
        """
        results = self.execute_query(query, (days,))
        return len(results) if results else 0
