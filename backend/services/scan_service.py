"""
Scan service for business logic related to interface scans and optical power.

Handles scan data retrieval and optical power history.
"""

from typing import Dict, List, Optional, Any
from .base import BaseService
from ..repositories.scan_repo import ScanRepository, OpticalPowerRepository
from ..repositories.device_repo import DeviceRepository
from ..utils.errors import NotFoundError, ValidationError
from ..utils.validation import validate_ip_address, validate_positive_int


class ScanService(BaseService):
    """Service for scan-related business logic."""
    
    def __init__(
        self,
        scan_repo: ScanRepository,
        optical_repo: OpticalPowerRepository,
        device_repo: DeviceRepository = None
    ):
        """
        Initialize scan service.
        
        Args:
            scan_repo: Scan repository
            optical_repo: Optical power repository
            device_repo: Optional device repository
        """
        super().__init__(scan_repo)
        self.scan_repo = scan_repo
        self.optical_repo = optical_repo
        self.device_repo = device_repo
    
    def get_device_interfaces(self, ip_address: str) -> List[Dict]:
        """
        Get latest interface scan data for a device.
        
        Args:
            ip_address: Device IP address
        
        Returns:
            List of interface records
        """
        validate_ip_address(ip_address)
        return self.scan_repo.get_latest_scans_for_device(ip_address)
    
    def get_optical_interfaces(self, ip_address: str = None) -> List[Dict]:
        """
        Get all optical interfaces.
        
        Args:
            ip_address: Optional device filter
        
        Returns:
            List of optical interfaces
        """
        if ip_address:
            validate_ip_address(ip_address)
        return self.scan_repo.get_optical_interfaces(ip_address)
    
    def get_optical_power_history(
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
        validate_ip_address(ip_address)
        return self.optical_repo.get_power_history(ip_address, interface_index, hours)
    
    def get_optical_power_trends(
        self,
        ip_address: str,
        interface_index: int,
        days: int = 7
    ) -> Dict:
        """
        Get optical power trend statistics.
        
        Args:
            ip_address: Device IP address
            interface_index: Interface index
            days: Time window in days
        
        Returns:
            Trend statistics
        """
        validate_ip_address(ip_address)
        return self.optical_repo.get_power_trends(ip_address, interface_index, days)
    
    def save_interface_scan(
        self,
        ip_address: str,
        interface_index: int,
        interface_name: str,
        cli_port: int,
        is_optical: bool = False,
        **kwargs
    ) -> Dict:
        """
        Save an interface scan result.
        
        Args:
            ip_address: Device IP address
            interface_index: Interface index
            interface_name: Interface name
            cli_port: CLI port number
            is_optical: Whether interface is optical
            **kwargs: Additional interface data
        
        Returns:
            Saved record
        """
        validate_ip_address(ip_address)
        
        return self.scan_repo.upsert_interface_scan(
            ip_address=ip_address,
            interface_index=interface_index,
            interface_name=interface_name,
            cli_port=cli_port,
            is_optical=is_optical,
            **kwargs
        )
    
    def save_optical_power_reading(
        self,
        ip_address: str,
        interface_index: int,
        interface_name: str,
        cli_port: int,
        tx_power: float = None,
        rx_power: float = None,
        temperature: float = None
    ) -> Dict:
        """
        Save an optical power reading.
        
        Args:
            ip_address: Device IP address
            interface_index: Interface index
            interface_name: Interface name
            cli_port: CLI port number
            tx_power: TX power value
            rx_power: RX power value
            temperature: Temperature value
        
        Returns:
            Saved record
        """
        validate_ip_address(ip_address)
        
        return self.optical_repo.insert_reading(
            ip_address=ip_address,
            interface_index=interface_index,
            interface_name=interface_name,
            cli_port=cli_port,
            tx_power=tx_power,
            rx_power=rx_power,
            temperature=temperature
        )
    
    def get_power_history_for_devices(
        self,
        ip_addresses: List[str],
        interface_index: int = None,
        hours: int = 24
    ) -> Dict[str, List[Dict]]:
        """
        Get optical power history for multiple devices.
        
        Args:
            ip_addresses: List of device IP addresses
            interface_index: Optional interface filter
            hours: Time window in hours
        
        Returns:
            Dictionary mapping IP to power readings
        """
        result = {}
        for ip in ip_addresses:
            try:
                validate_ip_address(ip)
                result[ip] = self.optical_repo.get_power_history(ip, interface_index, hours)
            except Exception:
                result[ip] = []
        return result
    
    def cleanup_old_data(self, optical_days: int = 90) -> Dict:
        """
        Clean up old scan and power data.
        
        Args:
            optical_days: Age threshold for optical data
        
        Returns:
            Cleanup statistics
        """
        optical_deleted = self.optical_repo.cleanup_old_readings(optical_days)
        
        return {
            'optical_readings_deleted': optical_deleted
        }
