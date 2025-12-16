"""
NetBox API Client Service.

Provides integration with an external NetBox instance for device inventory management.
NetBox serves as the source of truth for device inventory.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
import requests

logger = logging.getLogger(__name__)


class NetBoxService:
    """Service for interacting with NetBox API."""
    
    def __init__(self, url: str = None, token: str = None, verify_ssl: bool = True):
        """
        Initialize NetBox client.
        
        Args:
            url: NetBox base URL (e.g., https://netbox.example.com)
            token: NetBox API token
            verify_ssl: Whether to verify SSL certificates
        """
        self.url = (url or os.getenv('NETBOX_URL', '')).rstrip('/')
        self.token = token or os.getenv('NETBOX_TOKEN', '')
        self.verify_ssl = verify_ssl
        self._session = None
    
    @property
    def session(self) -> requests.Session:
        """Get or create requests session with auth headers."""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                'Authorization': f'Token {self.token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            })
            self._session.verify = self.verify_ssl
        return self._session
    
    @property
    def is_configured(self) -> bool:
        """Check if NetBox is configured."""
        return bool(self.url and self.token)
    
    def _api_url(self, endpoint: str) -> str:
        """Build full API URL."""
        return urljoin(f"{self.url}/api/", endpoint.lstrip('/'))
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Make API request to NetBox.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (e.g., 'dcim/devices/')
            **kwargs: Additional request arguments
        
        Returns:
            Response JSON
        
        Raises:
            NetBoxError: On API errors
        """
        if not self.is_configured:
            raise NetBoxError('NetBox is not configured. Set URL and API token in settings.')
        
        url = self._api_url(endpoint)
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            if response.status_code == 204:
                return {}
            
            return response.json()
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"NetBox connection error: {e}")
            raise NetBoxError(f"Cannot connect to NetBox at {self.url}")
        
        except requests.exceptions.HTTPError as e:
            error_detail = ''
            try:
                error_detail = response.json()
            except:
                error_detail = response.text
            
            logger.error(f"NetBox API error: {e} - {error_detail}")
            raise NetBoxError(f"NetBox API error: {e}", details=error_detail)
    
    def test_connection(self) -> Dict:
        """
        Test connection to NetBox.
        
        Returns:
            NetBox status info
        """
        try:
            result = self._request('GET', 'status/')
            return {
                'connected': True,
                'netbox_version': result.get('netbox-version'),
                'python_version': result.get('python-version'),
                'plugins': result.get('plugins', {}),
            }
        except NetBoxError as e:
            return {
                'connected': False,
                'error': str(e),
            }
    
    # ==================== DEVICES ====================
    
    def get_devices(
        self,
        site: str = None,
        role: str = None,
        manufacturer: str = None,
        status: str = None,
        tag: str = None,
        q: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict:
        """
        Get devices from NetBox.
        
        Args:
            site: Filter by site slug
            role: Filter by device role slug
            manufacturer: Filter by manufacturer slug
            status: Filter by status (active, planned, staged, failed, etc.)
            tag: Filter by tag
            q: Search query
            limit: Results per page
            offset: Pagination offset
        
        Returns:
            Paginated device list
        """
        params = {'limit': limit, 'offset': offset}
        
        if site:
            params['site'] = site
        if role:
            params['role'] = role
        if manufacturer:
            params['manufacturer'] = manufacturer
        if status:
            params['status'] = status
        if tag:
            params['tag'] = tag
        if q:
            params['q'] = q
        
        return self._request('GET', 'dcim/devices/', params=params)
    
    def get_device(self, device_id: int) -> Dict:
        """Get a single device by ID."""
        return self._request('GET', f'dcim/devices/{device_id}/')
    
    def get_device_by_name(self, name: str) -> Optional[Dict]:
        """Get a device by name."""
        result = self._request('GET', 'dcim/devices/', params={'name': name})
        devices = result.get('results', [])
        return devices[0] if devices else None
    
    def create_device(
        self,
        name: str,
        device_type_id: int,
        role_id: int,
        site_id: int,
        status: str = 'active',
        serial: str = None,
        asset_tag: str = None,
        description: str = None,
        comments: str = None,
        tags: List[str] = None,
        custom_fields: Dict = None,
    ) -> Dict:
        """
        Create a new device in NetBox.
        
        Args:
            name: Device name/hostname
            device_type_id: Device type ID
            role_id: Device role ID
            site_id: Site ID
            status: Device status
            serial: Serial number
            asset_tag: Asset tag
            description: Short description
            comments: Longer comments
            tags: List of tag names
            custom_fields: Custom field values
        
        Returns:
            Created device
        """
        data = {
            'name': name,
            'device_type': device_type_id,
            'role': role_id,
            'site': site_id,
            'status': status,
        }
        
        if serial:
            data['serial'] = serial
        if asset_tag:
            data['asset_tag'] = asset_tag
        if description:
            data['description'] = description
        if comments:
            data['comments'] = comments
        if tags:
            data['tags'] = [{'name': t} for t in tags]
        if custom_fields:
            data['custom_fields'] = custom_fields
        
        return self._request('POST', 'dcim/devices/', json=data)
    
    def update_device(self, device_id: int, **kwargs) -> Dict:
        """Update an existing device."""
        return self._request('PATCH', f'dcim/devices/{device_id}/', json=kwargs)
    
    def delete_device(self, device_id: int) -> None:
        """Delete a device."""
        self._request('DELETE', f'dcim/devices/{device_id}/')
    
    # ==================== IP ADDRESSES ====================
    
    def get_ip_addresses(
        self,
        address: str = None,
        device: str = None,
        interface: str = None,
        status: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict:
        """Get IP addresses from NetBox."""
        params = {'limit': limit, 'offset': offset}
        
        if address:
            params['address'] = address
        if device:
            params['device'] = device
        if interface:
            params['interface'] = interface
        if status:
            params['status'] = status
        
        return self._request('GET', 'ipam/ip-addresses/', params=params)
    
    def get_ip_address_by_address(self, address: str) -> Optional[Dict]:
        """Get IP address record by address (e.g., '192.168.1.1/24' or '192.168.1.1')."""
        # NetBox stores IPs with prefix length, try both formats
        result = self._request('GET', 'ipam/ip-addresses/', params={'address': address})
        ips = result.get('results', [])
        return ips[0] if ips else None
    
    def create_ip_address(
        self,
        address: str,
        status: str = 'active',
        description: str = None,
        assigned_object_type: str = None,
        assigned_object_id: int = None,
        dns_name: str = None,
        tags: List[str] = None,
    ) -> Dict:
        """
        Create an IP address in NetBox.
        
        Args:
            address: IP address with prefix (e.g., '192.168.1.1/24')
            status: IP status (active, reserved, deprecated, dhcp, slaac)
            description: Description
            assigned_object_type: Object type (e.g., 'dcim.interface')
            assigned_object_id: Object ID to assign to
            dns_name: DNS hostname
            tags: List of tag names
        
        Returns:
            Created IP address
        """
        data = {
            'address': address,
            'status': status,
        }
        
        if description:
            data['description'] = description
        if dns_name:
            data['dns_name'] = dns_name
        if assigned_object_type and assigned_object_id:
            data['assigned_object_type'] = assigned_object_type
            data['assigned_object_id'] = assigned_object_id
        if tags:
            data['tags'] = [{'name': t} for t in tags]
        
        return self._request('POST', 'ipam/ip-addresses/', json=data)
    
    def update_ip_address(self, ip_id: int, **kwargs) -> Dict:
        """Update an IP address."""
        return self._request('PATCH', f'ipam/ip-addresses/{ip_id}/', json=kwargs)
    
    # ==================== PREFIXES ====================
    
    def get_prefixes(
        self,
        prefix: str = None,
        site: str = None,
        vlan_id: int = None,
        status: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict:
        """Get prefixes/subnets from NetBox."""
        params = {'limit': limit, 'offset': offset}
        
        if prefix:
            params['prefix'] = prefix
        if site:
            params['site'] = site
        if vlan_id:
            params['vlan_id'] = vlan_id
        if status:
            params['status'] = status
        
        return self._request('GET', 'ipam/prefixes/', params=params)
    
    # ==================== SITES ====================
    
    def get_sites(self, limit: int = 100, offset: int = 0) -> Dict:
        """Get all sites."""
        return self._request('GET', 'dcim/sites/', params={'limit': limit, 'offset': offset})
    
    def get_site(self, site_id: int) -> Dict:
        """Get a single site."""
        return self._request('GET', f'dcim/sites/{site_id}/')
    
    def create_site(self, name: str, slug: str, status: str = 'active', **kwargs) -> Dict:
        """Create a new site."""
        data = {'name': name, 'slug': slug, 'status': status, **kwargs}
        return self._request('POST', 'dcim/sites/', json=data)
    
    # ==================== DEVICE TYPES ====================
    
    def get_device_types(self, manufacturer: str = None, limit: int = 100, offset: int = 0) -> Dict:
        """Get device types."""
        params = {'limit': limit, 'offset': offset}
        if manufacturer:
            params['manufacturer'] = manufacturer
        return self._request('GET', 'dcim/device-types/', params=params)
    
    def get_device_type(self, type_id: int) -> Dict:
        """Get a single device type."""
        return self._request('GET', f'dcim/device-types/{type_id}/')
    
    def create_device_type(
        self,
        manufacturer_id: int,
        model: str,
        slug: str,
        **kwargs
    ) -> Dict:
        """Create a new device type."""
        data = {
            'manufacturer': manufacturer_id,
            'model': model,
            'slug': slug,
            **kwargs
        }
        return self._request('POST', 'dcim/device-types/', json=data)
    
    # ==================== DEVICE ROLES ====================
    
    def get_device_roles(self, limit: int = 100, offset: int = 0) -> Dict:
        """Get device roles."""
        return self._request('GET', 'dcim/device-roles/', params={'limit': limit, 'offset': offset})
    
    def create_device_role(self, name: str, slug: str, color: str = '9e9e9e', **kwargs) -> Dict:
        """Create a new device role."""
        data = {'name': name, 'slug': slug, 'color': color, **kwargs}
        return self._request('POST', 'dcim/device-roles/', json=data)
    
    # ==================== MANUFACTURERS ====================
    
    def get_manufacturers(self, limit: int = 100, offset: int = 0) -> Dict:
        """Get manufacturers."""
        return self._request('GET', 'dcim/manufacturers/', params={'limit': limit, 'offset': offset})
    
    def create_manufacturer(self, name: str, slug: str, **kwargs) -> Dict:
        """Create a new manufacturer."""
        data = {'name': name, 'slug': slug, **kwargs}
        return self._request('POST', 'dcim/manufacturers/', json=data)
    
    # ==================== INTERFACES ====================
    
    def get_interfaces(
        self,
        device_id: int = None,
        device: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict:
        """Get interfaces."""
        params = {'limit': limit, 'offset': offset}
        if device_id:
            params['device_id'] = device_id
        if device:
            params['device'] = device
        return self._request('GET', 'dcim/interfaces/', params=params)
    
    def create_interface(
        self,
        device_id: int,
        name: str,
        type: str = '1000base-t',
        **kwargs
    ) -> Dict:
        """Create an interface on a device."""
        data = {
            'device': device_id,
            'name': name,
            'type': type,
            **kwargs
        }
        return self._request('POST', 'dcim/interfaces/', json=data)
    
    # ==================== DISCOVERY HELPERS ====================
    
    def upsert_discovered_device(
        self,
        ip_address: str,
        hostname: str = None,
        description: str = None,
        vendor: str = None,
        model: str = None,
        serial: str = None,
        site_id: int = None,
        role_id: int = None,
        device_type_id: int = None,
        status: str = 'active',
        tags: List[str] = None,
        custom_fields: Dict = None,
    ) -> Dict:
        """
        Create or update a device discovered by network scan.
        
        This is a high-level helper that handles the common discovery workflow:
        1. Check if device exists (by name or primary IP)
        2. Create or update device
        3. Create or update IP address
        4. Link IP to device
        
        Args:
            ip_address: Discovered IP address
            hostname: Discovered hostname (used as device name)
            description: Device description (e.g., from SNMP sysDescr)
            vendor: Vendor/manufacturer name
            model: Device model
            serial: Serial number
            site_id: Site to assign device to
            role_id: Device role ID
            device_type_id: Device type ID
            status: Device status
            tags: Tags to apply
            custom_fields: Custom field values
        
        Returns:
            Device record with IP info
        """
        # Use hostname as device name, or generate from IP
        device_name = hostname or f"device-{ip_address.replace('.', '-')}"
        
        # Check if device already exists
        existing = self.get_device_by_name(device_name)
        
        if existing:
            # Update existing device
            update_data = {}
            if description:
                update_data['description'] = description
            if serial:
                update_data['serial'] = serial
            if custom_fields:
                update_data['custom_fields'] = custom_fields
            
            if update_data:
                device = self.update_device(existing['id'], **update_data)
            else:
                device = existing
        else:
            # Create new device
            if not all([site_id, role_id, device_type_id]):
                raise NetBoxError(
                    "site_id, role_id, and device_type_id are required to create new devices. "
                    "Configure default values in NetBox settings."
                )
            
            device = self.create_device(
                name=device_name,
                device_type_id=device_type_id,
                role_id=role_id,
                site_id=site_id,
                status=status,
                serial=serial,
                description=description,
                tags=tags or ['discovered'],
                custom_fields=custom_fields,
            )
        
        # Handle IP address
        ip_with_prefix = ip_address if '/' in ip_address else f"{ip_address}/32"
        existing_ip = self.get_ip_address_by_address(ip_address)
        
        if existing_ip:
            # Update IP if needed
            ip_record = existing_ip
        else:
            # Create IP address
            ip_record = self.create_ip_address(
                address=ip_with_prefix,
                status='active',
                dns_name=hostname,
                tags=tags or ['discovered'],
            )
        
        # Set as primary IP if device doesn't have one
        if device and not device.get('primary_ip4'):
            self.update_device(device['id'], primary_ip4=ip_record['id'])
            device['primary_ip4'] = ip_record
        
        return {
            'device': device,
            'ip_address': ip_record,
            'created': not existing,
        }


class NetBoxError(Exception):
    """NetBox API error."""
    
    def __init__(self, message: str, details: Any = None):
        super().__init__(message)
        self.message = message
        self.details = details
