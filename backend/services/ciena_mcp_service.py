"""
Ciena MCP API Service.

Provides integration with Ciena MCP (Management Control Plane) for device inventory,
equipment tracking, and network topology synchronization.
"""

import logging
import requests
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class CienaMCPError(Exception):
    """Exception for Ciena MCP API errors."""
    def __init__(self, message: str, status_code: int = None, details: Any = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class CienaMCPService:
    """Service for interacting with Ciena MCP REST API."""
    
    def __init__(self, url: str = None, username: str = None, password: str = None, verify_ssl: bool = False):
        """
        Initialize Ciena MCP client.
        
        Args:
            url: MCP base URL (e.g., https://10.127.0.15)
            username: MCP username
            password: MCP password
            verify_ssl: Whether to verify SSL certificates (default False for self-signed)
        """
        self.url = (url or '').rstrip('/')
        self.username = username or ''
        self.password = password or ''
        self.verify_ssl = verify_ssl
        self._token = None
        self._session = None
    
    @property
    def session(self) -> requests.Session:
        """Get or create requests session with connection pooling."""
        if self._session is None:
            self._session = requests.Session()
            self._session.verify = self.verify_ssl
            
            # Configure connection pooling
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            retry_strategy = Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[502, 503, 504],
            )
            adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=retry_strategy)
            self._session.mount('http://', adapter)
            self._session.mount('https://', adapter)
        return self._session
    
    @property
    def is_configured(self) -> bool:
        """Check if MCP is configured."""
        return bool(self.url and self.username and self.password)
    
    def _get_token(self) -> str:
        """Authenticate and get bearer token."""
        if self._token:
            return self._token
        
        if not self.is_configured:
            raise CienaMCPError('Ciena MCP is not configured. Set URL, username, and password.')
        
        url = f"{self.url}/tron/api/v1/tokens"
        payload = {
            'username': self.username,
            'password': self.password
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('isSuccessful'):
                raise CienaMCPError(f"Authentication failed: {data.get('message', 'Unknown error')}")
            
            self._token = data.get('token')
            logger.info(f"Ciena MCP authentication successful for user {self.username}")
            return self._token
            
        except requests.exceptions.RequestException as e:
            raise CienaMCPError(f"Failed to authenticate with MCP: {e}")
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Make authenticated API request to MCP.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (e.g., '/nsi/api/search/networkConstructs')
            **kwargs: Additional request arguments
        
        Returns:
            Response JSON
        """
        token = self._get_token()
        
        url = f"{self.url}{endpoint}"
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f'Bearer {token}'
        headers['Content-Type'] = 'application/json'
        headers['Accept'] = 'application/json'
        
        try:
            response = self.session.request(method, url, headers=headers, timeout=60, **kwargs)
            
            # Handle token expiration
            if response.status_code == 401:
                self._token = None
                token = self._get_token()
                headers['Authorization'] = f'Bearer {token}'
                response = self.session.request(method, url, headers=headers, timeout=60, **kwargs)
            
            response.raise_for_status()
            
            if response.status_code == 204:
                return {}
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            try:
                error_data = response.json() if response else {}
                error_msg = error_data.get('errorMessage', error_msg)
            except:
                pass
            raise CienaMCPError(f"MCP API error: {error_msg}", 
                              status_code=getattr(response, 'status_code', None))
    
    def test_connection(self) -> Dict:
        """Test MCP connection and return status."""
        try:
            token = self._get_token()
            return {
                'success': True,
                'message': 'Connected to Ciena MCP',
                'authenticated': True
            }
        except CienaMCPError as e:
            return {
                'success': False,
                'message': str(e),
                'authenticated': False
            }
    
    # ==================== DEVICES (Network Constructs) ====================
    
    def get_devices(self, limit: int = 100, offset: int = 0, filters: Dict = None) -> Dict:
        """
        Get network devices (network constructs) from MCP.
        
        Args:
            limit: Maximum results per page
            offset: Offset for pagination
            filters: Optional filters (e.g., {'name': 'switch1'})
        
        Returns:
            Dict with 'data' list and 'meta' pagination info
        """
        params = f"?limit={limit}&offset={offset}"
        if filters:
            for key, value in filters.items():
                params += f"&{key}={value}"
        
        return self._request('GET', f'/nsi/api/search/networkConstructs{params}')
    
    def get_all_devices(self) -> List[Dict]:
        """Get all devices with pagination handling."""
        all_devices = []
        offset = 0
        limit = 100
        
        while True:
            result = self.get_devices(limit=limit, offset=offset)
            devices = result.get('data', [])
            all_devices.extend(devices)
            
            total = result.get('meta', {}).get('total', 0)
            if offset + limit >= total or not devices:
                break
            offset += limit
        
        logger.info(f"Retrieved {len(all_devices)} devices from MCP")
        return all_devices
    
    def get_device(self, device_id: str) -> Dict:
        """Get single device by ID."""
        result = self._request('GET', f'/nsi/api/search/networkConstructs?filter=id=={device_id}')
        devices = result.get('data', [])
        return devices[0] if devices else None
    
    # ==================== PORTS/TPs (Termination Points) ====================
    
    def get_ports(self, device_id: str, limit: int = 200, offset: int = 0) -> Dict:
        """
        Get ports (termination points) for a device from MCP.
        
        Args:
            device_id: Network construct ID
            limit: Maximum results per page
            offset: Offset for pagination
        
        Returns:
            Dict with 'data' list and 'meta' pagination info
        """
        params = f"?limit={limit}&offset={offset}"
        return self._request('GET', f'/nsi/api/networkConstructs/{device_id}/tps{params}')
    
    def get_all_ports(self, device_id: str) -> List[Dict]:
        """Get all ports for a device with pagination handling."""
        all_ports = []
        offset = 0
        limit = 200
        
        while True:
            try:
                result = self.get_ports(device_id, limit=limit, offset=offset)
                ports = result.get('data', [])
                all_ports.extend(ports)
                
                total = result.get('meta', {}).get('total', 0)
                if offset + limit >= total or not ports:
                    break
                offset += limit
            except CienaMCPError as e:
                logger.warning(f"Failed to get ports for device {device_id}: {e}")
                break
        
        logger.info(f"Retrieved {len(all_ports)} ports for device {device_id}")
        return all_ports
    
    # ==================== EQUIPMENT (SFPs, Cards) ====================
    
    def get_equipment(self, limit: int = 100, offset: int = 0, device_id: str = None) -> Dict:
        """
        Get equipment (SFPs, cards, modules) from MCP.
        
        Args:
            limit: Maximum results per page
            offset: Offset for pagination
            device_id: Optional filter by device (networkConstruct) ID
        
        Returns:
            Dict with 'data' list and 'meta' pagination info
        """
        params = f"?limit={limit}&offset={offset}"
        if device_id:
            params += f"&filter=networkConstruct.id=={device_id}"
        
        return self._request('GET', f'/nsi/api/search/equipment{params}')
    
    def get_all_equipment(self, device_id: str = None) -> List[Dict]:
        """Get all equipment with pagination handling."""
        all_equipment = []
        offset = 0
        limit = 100
        
        while True:
            result = self.get_equipment(limit=limit, offset=offset, device_id=device_id)
            equipment = result.get('data', [])
            all_equipment.extend(equipment)
            
            total = result.get('meta', {}).get('total', 0)
            if offset + limit >= total or not equipment:
                break
            offset += limit
        
        logger.info(f"Retrieved {len(all_equipment)} equipment items from MCP")
        return all_equipment
    
    # ==================== LINKS (Physical connections) ====================
    
    def get_links(self, limit: int = 100, offset: int = 0) -> Dict:
        """
        Get physical network links from MCP.
        
        Returns:
            Dict with 'data' list and 'meta' pagination info
        """
        params = f"?limit={limit}&offset={offset}"
        return self._request('GET', f'/nsi/api/search/links{params}')
    
    def get_all_links(self) -> List[Dict]:
        """Get all physical links with pagination handling."""
        all_links = []
        offset = 0
        limit = 100
        
        while True:
            result = self.get_links(limit=limit, offset=offset)
            links = result.get('data', [])
            all_links.extend(links)
            
            total = result.get('meta', {}).get('total', 0)
            if offset + limit >= total or not links:
                break
            offset += limit
        
        logger.info(f"Retrieved {len(all_links)} physical links from MCP")
        return all_links
    
    # ==================== SERVICES (FREs - Forwarding Resource Elements) ====================
    
    def get_services(self, limit: int = 100, offset: int = 0) -> Dict:
        """
        Get services/circuits (FREs) from MCP.
        
        Args:
            limit: Maximum results per page
            offset: Offset for pagination
        
        Returns:
            Dict with 'data' list and 'meta' pagination info
        """
        params = f"?limit={limit}&offset={offset}"
        return self._request('GET', f'/nsi/api/search/fres{params}')
    
    def get_all_services(self, service_class: str = None) -> List[Dict]:
        """Get all services with pagination handling and optional client-side filtering."""
        all_services = []
        offset = 0
        limit = 200
        
        while True:
            result = self.get_services(limit=limit, offset=offset)
            services = result.get('data', [])
            all_services.extend(services)
            
            total = result.get('meta', {}).get('total', 0)
            if offset + limit >= total or not services:
                break
            offset += limit
        
        # Apply client-side filter if specified
        if service_class:
            all_services = [s for s in all_services if s.get('attributes', {}).get('serviceClass') == service_class]
        
        filter_msg = f" (class={service_class})" if service_class else ""
        logger.info(f"Retrieved {len(all_services)} services{filter_msg} from MCP")
        return all_services
    
    def get_service(self, service_id: str) -> Dict:
        """Get a single service by ID."""
        result = self._request('GET', f'/nsi/api/search/fres?filter=id=={service_id}')
        services = result.get('data', [])
        return services[0] if services else None
    
    def get_rings(self) -> List[Dict]:
        """Get all G.8032 ring services."""
        # Filter client-side since API filter doesn't work for serviceClass
        all_services = self.get_all_services()
        return [s for s in all_services if s.get('attributes', {}).get('serviceClass') == 'Ring']
    
    def get_evcs(self) -> List[Dict]:
        """Get all EVC services."""
        # Filter client-side since API filter doesn't work for serviceClass
        all_services = self.get_all_services()
        return [s for s in all_services if s.get('attributes', {}).get('serviceClass') == 'EVC']
    
    def get_service_summary(self) -> Dict:
        """Get summary of all services by class."""
        all_services = self.get_all_services()
        
        summary = {
            'total': len(all_services),
            'by_class': {},
            'by_state': {'up': 0, 'down': 0, 'unknown': 0},
            'rings': [],
            'down_services': []
        }
        
        for svc in all_services:
            attrs = svc.get('attributes', {})
            display = attrs.get('displayData', {})
            
            # Count by class
            svc_class = attrs.get('serviceClass', 'Unknown')
            summary['by_class'][svc_class] = summary['by_class'].get(svc_class, 0) + 1
            
            # Count by state
            op_state = (display.get('operationState') or attrs.get('operationState') or '').lower()
            if op_state == 'up':
                summary['by_state']['up'] += 1
            elif op_state == 'down':
                summary['by_state']['down'] += 1
                # Track down services
                summary['down_services'].append({
                    'id': svc.get('id'),
                    'name': attrs.get('userLabel') or attrs.get('mgmtName') or svc.get('id'),
                    'class': svc_class,
                    'state': op_state
                })
            else:
                summary['by_state']['unknown'] += 1
            
            # Track rings with their status
            if svc_class == 'Ring':
                add_attrs = attrs.get('additionalAttributes', {})
                summary['rings'].append({
                    'id': svc.get('id'),
                    'name': attrs.get('mgmtName') or attrs.get('userLabel') or svc.get('id'),
                    'ring_id': add_attrs.get('ringId'),
                    'ring_state': add_attrs.get('ringState'),
                    'ring_status': add_attrs.get('ringStatus'),
                    'ring_type': add_attrs.get('ringType'),
                    'members': add_attrs.get('ringMembers'),
                    'logical_ring': add_attrs.get('logicalRingName'),
                    'virtual_ring': add_attrs.get('virtualRingName'),
                })
        
        return summary
    
    # ==================== WATCHERS (Monitoring) ====================
    
    def get_watchers(self) -> List[Dict]:
        """Get all monitoring watchers."""
        result = self._request('GET', '/watcher/api/v1/watchers')
        return result if isinstance(result, list) else result.get('items', [])
    
    # ==================== SYNC TO NETBOX ====================
    
    def sync_devices_to_netbox(self, netbox_service, site_id: int = None, 
                                device_role_id: int = None, create_missing: bool = True) -> Dict:
        """
        Sync MCP devices to NetBox.
        
        Args:
            netbox_service: NetBox service instance
            site_id: Default site ID for new devices
            device_role_id: Default device role ID for new devices
            create_missing: Whether to create devices that don't exist in NetBox
        
        Returns:
            Dict with sync statistics
        """
        stats = {
            'total': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': []
        }
        
        devices = self.get_all_devices()
        stats['total'] = len(devices)
        
        for device in devices:
            try:
                attrs = device.get('attributes', {})
                display = attrs.get('displayData', {})
                
                name = attrs.get('name') or display.get('displayName')
                ip_address = attrs.get('ipAddress') or display.get('displayIpAddress')
                serial = attrs.get('serialNumber', '')
                mac = attrs.get('macAddress') or display.get('displayMACAddress', '')
                software = attrs.get('softwareVersion', '')
                device_type = attrs.get('deviceType', '')
                vendor = attrs.get('vendor', 'Ciena')
                
                if not name:
                    stats['skipped'] += 1
                    continue
                
                # Check if device exists in NetBox by name or serial
                existing = None
                try:
                    search = netbox_service._request('GET', f'dcim/devices/?name={name}')
                    if search.get('results'):
                        existing = search['results'][0]
                except:
                    pass
                
                if not existing and serial:
                    try:
                        search = netbox_service._request('GET', f'dcim/devices/?serial={serial}')
                        if search.get('results'):
                            existing = search['results'][0]
                    except:
                        pass
                
                # Build device data
                device_data = {
                    'name': name,
                    'serial': serial,
                    'comments': f"Software: {software}\nDevice Type: {device_type}\nManaged by Ciena MCP",
                }
                
                if existing:
                    # Update existing device
                    try:
                        netbox_service._request('PATCH', f'dcim/devices/{existing["id"]}/', json=device_data)
                        stats['updated'] += 1
                        logger.debug(f"Updated device {name} in NetBox")
                    except Exception as e:
                        stats['errors'].append({'device': name, 'error': str(e)})
                elif create_missing:
                    # Create new device
                    if site_id:
                        device_data['site'] = site_id
                    if device_role_id:
                        device_data['role'] = device_role_id
                    
                    # Need device type - try to find or create
                    try:
                        # Look for existing device type
                        dt_search = netbox_service._request('GET', f'dcim/device-types/?model__ic={device_type[:50]}')
                        if dt_search.get('results'):
                            device_data['device_type'] = dt_search['results'][0]['id']
                        else:
                            # Skip if no matching device type
                            logger.warning(f"No device type found for {device_type}, skipping {name}")
                            stats['skipped'] += 1
                            continue
                        
                        netbox_service._request('POST', 'dcim/devices/', json=device_data)
                        stats['created'] += 1
                        logger.debug(f"Created device {name} in NetBox")
                    except Exception as e:
                        stats['errors'].append({'device': name, 'error': str(e)})
                else:
                    stats['skipped'] += 1
                    
            except Exception as e:
                stats['errors'].append({'device': device.get('id', 'unknown'), 'error': str(e)})
        
        logger.info(f"MCP to NetBox sync: {stats['created']} created, {stats['updated']} updated, "
                   f"{stats['skipped']} skipped, {len(stats['errors'])} errors")
        return stats
    
    def sync_equipment_to_netbox(self, netbox_service) -> Dict:
        """
        Sync MCP equipment (SFPs, cards) to NetBox as inventory items.
        
        Args:
            netbox_service: NetBox service instance
        
        Returns:
            Dict with sync statistics
        """
        stats = {
            'total': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': []
        }
        
        # Get all equipment from MCP
        equipment_list = self.get_all_equipment()
        stats['total'] = len(equipment_list)
        
        # Build device name to ID mapping from NetBox
        device_map = {}
        try:
            nb_devices = netbox_service._request('GET', 'dcim/devices/?limit=1000')
            for dev in nb_devices.get('results', []):
                device_map[dev['name'].lower()] = dev['id']
        except Exception as e:
            logger.warning(f"Failed to get NetBox devices for mapping: {e}")
        
        # Get or create manufacturer
        manufacturer_id = None
        try:
            mfr_search = netbox_service._request('GET', 'dcim/manufacturers/?name=Ciena')
            if mfr_search.get('results'):
                manufacturer_id = mfr_search['results'][0]['id']
            else:
                # Try common SFP manufacturers
                for mfr_name in ['FS', 'Finisar', 'Generic']:
                    mfr_search = netbox_service._request('GET', f'dcim/manufacturers/?name__ic={mfr_name}')
                    if mfr_search.get('results'):
                        manufacturer_id = mfr_search['results'][0]['id']
                        break
        except:
            pass
        
        for item in equipment_list:
            try:
                attrs = item.get('attributes', {})
                display = attrs.get('displayData', {})
                installed = attrs.get('installedSpec', {})
                locations = attrs.get('locations', [{}])
                location = locations[0] if locations else {}
                
                serial = installed.get('serialNumber', '')
                part_number = installed.get('partNumber', '').strip()
                item_type = installed.get('type') or attrs.get('cardType', '')
                device_name = location.get('neName', '')
                slot = location.get('subslot', '')
                manufacturer = installed.get('manufacturer', '')
                
                if not serial or not device_name:
                    stats['skipped'] += 1
                    continue
                
                # Find device ID in NetBox
                device_id = device_map.get(device_name.lower())
                if not device_id:
                    stats['skipped'] += 1
                    continue
                
                # Check if inventory item exists
                existing = None
                try:
                    search = netbox_service._request('GET', f'dcim/inventory-items/?serial={serial}')
                    if search.get('results'):
                        existing = search['results'][0]
                except:
                    pass
                
                # Build inventory item data
                item_data = {
                    'device': device_id,
                    'name': f"{item_type}-{slot}" if slot else item_type,
                    'serial': serial,
                    'part_id': part_number,
                    'description': f"MCP Equipment: {manufacturer} {item_type}",
                }
                
                if manufacturer_id:
                    item_data['manufacturer'] = manufacturer_id
                
                if existing:
                    # Update existing
                    try:
                        netbox_service._request('PATCH', f'dcim/inventory-items/{existing["id"]}/', json=item_data)
                        stats['updated'] += 1
                    except Exception as e:
                        stats['errors'].append({'serial': serial, 'error': str(e)})
                else:
                    # Create new
                    try:
                        netbox_service._request('POST', 'dcim/inventory-items/', json=item_data)
                        stats['created'] += 1
                    except Exception as e:
                        stats['errors'].append({'serial': serial, 'error': str(e)})
                        
            except Exception as e:
                stats['errors'].append({'item': item.get('id', 'unknown'), 'error': str(e)})
        
        logger.info(f"MCP equipment to NetBox sync: {stats['created']} created, {stats['updated']} updated, "
                   f"{stats['skipped']} skipped, {len(stats['errors'])} errors")
        return stats
    
    def get_device_summary(self) -> Dict:
        """Get summary of MCP inventory."""
        try:
            devices = self.get_devices(limit=1)
            equipment = self.get_equipment(limit=1)
            links = self.get_links(limit=1)
            
            return {
                'devices': devices.get('meta', {}).get('total', 0),
                'equipment': equipment.get('meta', {}).get('total', 0),
                'links': links.get('meta', {}).get('total', 0),
            }
        except Exception as e:
            logger.error(f"Failed to get MCP summary: {e}")
            return {'error': str(e)}


# Global instance for easy access
_mcp_service = None


def get_mcp_service() -> CienaMCPService:
    """Get configured MCP service instance."""
    global _mcp_service
    if _mcp_service is None:
        from database import DatabaseManager
        db = DatabaseManager()
        
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT key, value FROM system_settings 
                WHERE key LIKE 'mcp_%'
            """)
            rows = cursor.fetchall()
        
        settings = {}
        for row in rows:
            key = row['key'].replace('mcp_', '')
            settings[key] = row['value']
        
        _mcp_service = CienaMCPService(
            url=settings.get('url', ''),
            username=settings.get('username', ''),
            password=settings.get('password', ''),
            verify_ssl=settings.get('verify_ssl', 'false').lower() == 'true'
        )
    return _mcp_service


def reset_mcp_service():
    """Reset the global MCP service instance (for config changes)."""
    global _mcp_service
    _mcp_service = None
