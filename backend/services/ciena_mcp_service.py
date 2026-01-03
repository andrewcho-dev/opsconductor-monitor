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
            
            # Count by class - use layerRate as fallback when serviceClass is missing
            svc_class = attrs.get('serviceClass')
            if not svc_class:
                # Derive class from layerRate
                layer_rate = (attrs.get('layerRate') or '').upper()
                if layer_rate == 'G8032':
                    svc_class = 'Ring'
                elif layer_rate == 'ETHERNET':
                    svc_class = 'Ethernet'
                elif layer_rate:
                    svc_class = layer_rate.title()
                else:
                    svc_class = 'Unknown'
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
    
    # ==================== PERFORMANCE METRICS (Real-time PM via nmserver) ====================
    
    def get_management_session(self, device_id: str) -> Optional[Dict]:
        """
        Get management session for a device (needed for PM queries).
        
        Args:
            device_id: Network construct ID
        
        Returns:
            Management session data or None
        """
        try:
            # First get the device to find its IP
            device = self._request('GET', f'/nsi/api/v4/networkConstructs/{device_id}')
            if not device or 'data' not in device:
                return None
            
            attrs = device['data'].get('attributes', {})
            ip_address = attrs.get('ipAddress')
            
            if not ip_address:
                return None
            
            # Search for management session by IP
            sessions = self._request('GET', f'/discovery/api/v3/managementSessions?limit=500')
            for session in sessions.get('data', []):
                session_attrs = session.get('attributes', {})
                if session_attrs.get('ipAddress') == ip_address:
                    return {
                        'session_id': session.get('id'),
                        'device_name': session_attrs.get('name'),
                        'ip_address': ip_address,
                        'type_group': session_attrs.get('typeGroup'),
                        'resource_type': session_attrs.get('resourceType'),
                        'software_version': attrs.get('softwareVersion'),
                        'device_type': attrs.get('deviceType'),
                        'nc_id': device_id,
                    }
            
            return None
            
        except CienaMCPError as e:
            logger.warning(f"Failed to get management session for {device_id}: {e}")
            return None
    
    def get_realtime_pm(self, device_id: str, port_number: str) -> Optional[Dict]:
        """
        Get real-time performance metrics for a specific port.
        
        Args:
            device_id: Network construct ID (e.g., 'cebcc6a3-7232-3556-8e75-0c68d82f6b05')
            port_number: Port number (e.g., '21', '22')
        
        Returns:
            Dict with traffic statistics or None
        """
        try:
            # Get management session info
            session = self.get_management_session(device_id)
            if not session:
                logger.warning(f"No management session found for device {device_id}")
                return None
            
            # Build the PM query URL
            from urllib.parse import quote
            params = {
                'instanceName': port_number,
                'typegroup': session['type_group'],
                'sessionid': session['session_id'],
                'softwareVersion': session['software_version'],
                'ncid': device_id,
                'deviceType': session['device_type'],
                'neName': session['device_name'],
                'resourceType': session['resource_type'],
            }
            
            query = '&'.join(f"{k}={quote(str(v))}" for k, v in params.items())
            result = self._request('GET', f'/nmserver/api/v1/nes/pm/realtimepm/values?{query}')
            
            # Parse the response
            pm_data = result.get('realtimepmfixedtablevalues', {}).get('data', [])
            if not pm_data:
                return None
            
            json_data = pm_data[0].get('attributes', {}).get('jsondata', [])
            if not json_data:
                return None
            
            # Return both current bin and 24hr bin data
            stats = {
                'port': port_number,
                'device_name': session['device_name'],
                'device_ip': session['ip_address'],
            }
            
            for entry in json_data:
                bin_type = entry.get('bin', '')
                prefix = 'current_' if 'Current bin' == bin_type else '24hr_' if '24 hour' in bin_type else ''
                
                if prefix:
                    # Parse numeric values (remove commas)
                    def parse_num(val):
                        if val is None:
                            return 0
                        return int(str(val).replace(',', '')) if val else 0
                    
                    stats[f'{prefix}rx_bytes'] = parse_num(entry.get('rxBytes'))
                    stats[f'{prefix}tx_bytes'] = parse_num(entry.get('txBytes'))
                    stats[f'{prefix}rx_pkts'] = parse_num(entry.get('rxPkts'))
                    stats[f'{prefix}tx_pkts'] = parse_num(entry.get('txPkts'))
                    stats[f'{prefix}rx_errors'] = parse_num(entry.get('rxInErrorPkts'))
                    stats[f'{prefix}tx_errors'] = parse_num(entry.get('txLCheckErrorPkts'))
                    stats[f'{prefix}rx_drops'] = parse_num(entry.get('rxDropPkts'))
                    stats[f'{prefix}rx_discards'] = parse_num(entry.get('rxDiscardPkts'))
                    stats[f'{prefix}collection_time'] = entry.get('collectionStartDateTime')
                    stats[f'{prefix}datetime'] = entry.get('datetime')
            
            return stats
            
        except CienaMCPError as e:
            logger.error(f"Failed to get real-time PM for {device_id} port {port_number}: {e}")
            return None
    
    def get_all_port_stats(self, device_id: str, port_numbers: List[str] = None) -> List[Dict]:
        """
        Get real-time PM stats for multiple ports on a device.
        
        Args:
            device_id: Network construct ID
            port_numbers: List of port numbers to query (default: 1-24)
        
        Returns:
            List of port statistics
        """
        if port_numbers is None:
            port_numbers = [str(i) for i in range(1, 25)]
        
        stats = []
        for port in port_numbers:
            pm = self.get_realtime_pm(device_id, port)
            if pm and (pm.get('current_rx_bytes', 0) > 0 or pm.get('current_tx_bytes', 0) > 0):
                stats.append(pm)
        
        return stats
    
    def get_ethernet_port_status(self, device_id: str) -> List[Dict]:
        """
        Get real-time Ethernet port operational status from MCP.
        
        Args:
            device_id: Network construct ID
        
        Returns:
            List of port status records with operLink, operMode, adminLink, etc.
        """
        try:
            # Get management session info
            session = self.get_management_session(device_id)
            if not session:
                logger.warning(f"No management session found for device {device_id}")
                return []
            
            # Build the query URL
            from urllib.parse import quote
            params = {
                'typegroup': session['type_group'],
                'sessionid': session['session_id'],
                'softwareVersion': session['software_version'],
                'ncid': device_id,
                'deviceType': session['device_type'],
                'neName': session['device_name'],
                'resourceType': session['resource_type'],
                'uiAction': 'refresh',
            }
            
            query = '&'.join(f"{k}={quote(str(v))}" for k, v in params.items())
            result = self._request('GET', f'/nmserver/api/v1/nes/ethernetPortMgmt/ettp/values?{query}')
            
            # Parse the response
            ettp_data = result.get('ettpfixedtablevalues', {}).get('data', [])
            if not ettp_data:
                return []
            
            json_data = ettp_data[0].get('attributes', {}).get('jsondata', [])
            
            ports = []
            for entry in json_data:
                ports.append({
                    'port': entry.get('port'),
                    'port_type': entry.get('portType'),
                    'oper_link': entry.get('operLink'),
                    'oper_link_duration': entry.get('operLinkStateDuration'),
                    'oper_xcvr': entry.get('operXCVR'),
                    'oper_stp': entry.get('operSTP'),
                    'oper_mode': entry.get('operMode'),
                    'oper_auto_neg': entry.get('operAutoNeg'),
                    'admin_link': entry.get('adminLink'),
                    'admin_mode': entry.get('adminMode'),
                    'admin_auto_neg': entry.get('adminAutoNeg'),
                    'admin_max_frame_size': entry.get('adminMaxFrameSize'),
                    'port_descr': entry.get('portDescr'),
                })
            
            return ports
            
        except CienaMCPError as e:
            logger.error(f"Failed to get Ethernet port status for {device_id}: {e}")
            return []
    
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


def sync_ciena_interfaces_to_netbox(mcp_service, netbox_service, device_ip: str = None) -> Dict:
    """
    Sync Ciena switch interfaces to NetBox with correct types, speeds, and SFP modules.
    
    This function:
    1. Gets port status from MCP to determine actual port types
    2. Gets equipment (SFPs) from MCP
    3. Updates NetBox interfaces with correct types and speeds
    4. Creates/updates SFP modules in NetBox module bays
    
    Args:
        mcp_service: CienaMCPService instance
        netbox_service: NetBox service instance
        device_ip: Optional - sync only this device, otherwise sync all Ciena devices
    
    Returns:
        Dict with sync statistics
    """
    stats = {
        'devices_processed': 0,
        'interfaces_updated': 0,
        'modules_created': 0,
        'modules_updated': 0,
        'errors': []
    }
    
    # Map MCP port types to NetBox interface types
    PORT_TYPE_MAP = {
        '10/100/G': '1000base-t',      # Copper 1G
        '10Gig': '10gbase-x-sfpp',      # SFP+ 10G
        'G/10Gig': '10gbase-x-sfpp',    # Combo SFP (1G/10G)
        '1Gig': '1000base-x-sfp',       # SFP 1G
        '100G': '100gbase-x-qsfp28',    # QSFP28 100G
    }
    
    # Map MCP oper_mode to speed in Kbps
    SPEED_MAP = {
        '10/FD': 10000,
        '10/HD': 10000,
        '100/FD': 100000,
        '100/HD': 100000,
        '1000/FD': 1000000,
        '10G/FD': 10000000,
        '100G/FD': 100000000,
    }
    
    try:
        # Get all Ciena devices from MCP
        all_mcp_devices = mcp_service.get_all_devices()
        
        # Filter to specific device if requested
        if device_ip:
            all_mcp_devices = [d for d in all_mcp_devices 
                              if d.get('attributes', {}).get('ipAddress') == device_ip]
        
        for mcp_device in all_mcp_devices:
            attrs = mcp_device.get('attributes', {})
            ip = attrs.get('ipAddress')
            name = attrs.get('name') or attrs.get('displayData', {}).get('displayName')
            device_id = mcp_device.get('id')
            
            if not ip or not name:
                continue
            
            # Find device in NetBox
            try:
                nb_search = netbox_service._request('GET', f'dcim/devices/?name={name}')
                if not nb_search.get('results'):
                    # Try by primary IP
                    nb_search = netbox_service._request('GET', f'dcim/devices/?primary_ip4={ip}')
                
                if not nb_search.get('results'):
                    logger.debug(f"Device {name} ({ip}) not found in NetBox, skipping")
                    continue
                
                nb_device = nb_search['results'][0]
                nb_device_id = nb_device['id']
            except Exception as e:
                stats['errors'].append({'device': name, 'error': f'NetBox lookup failed: {e}'})
                continue
            
            stats['devices_processed'] += 1
            
            # Get port status from MCP
            try:
                port_status = mcp_service.get_ethernet_port_status(device_id)
            except Exception as e:
                logger.warning(f"Failed to get port status for {name}: {e}")
                port_status = []
            
            # Get equipment (SFPs) from MCP
            try:
                # Get all equipment and filter by device name
                all_equipment = mcp_service.get_all_equipment()
                device_equipment = [e for e in all_equipment 
                                   if e.get('attributes', {}).get('locations', [{}])[0].get('neName') == name]
                
                # Extract SFPs with simplified format
                sfps = []
                for item in device_equipment:
                    attrs = item.get('attributes', {})
                    installed = attrs.get('installedSpec', {})
                    locations = attrs.get('locations', [{}])
                    location = locations[0] if locations else {}
                    
                    eq_type = installed.get('type') or attrs.get('cardType')
                    slot = location.get('subslot')
                    
                    if eq_type == 'SFP' and slot:
                        sfps.append({
                            'slot': slot,
                            'serial_number': installed.get('serialNumber', ''),
                            'part_number': installed.get('partNumber', ''),
                            'manufacturer': installed.get('manufacturer', 'Unknown'),
                        })
                logger.debug(f"Found {len(sfps)} SFPs for {name}: {[s['slot'] for s in sfps]}")
            except Exception as e:
                logger.warning(f"Failed to get equipment for {name}: {e}")
                sfps = []
            
            # Get existing interfaces from NetBox
            try:
                nb_interfaces = netbox_service._request('GET', f'dcim/interfaces/?device_id={nb_device_id}&limit=100')
                interface_map = {str(iface['name']): iface for iface in nb_interfaces.get('results', [])}
            except Exception as e:
                stats['errors'].append({'device': name, 'error': f'Failed to get interfaces: {e}'})
                continue
            
            # Update interfaces based on MCP port status
            for port in port_status:
                port_num = port.get('port')
                port_type = port.get('port_type')
                oper_mode = port.get('oper_mode')
                oper_link = port.get('oper_link')
                
                if not port_num:
                    continue
                
                # Find matching interface in NetBox
                nb_iface = interface_map.get(port_num)
                if not nb_iface:
                    continue
                
                # Determine correct interface type
                nb_type = PORT_TYPE_MAP.get(port_type, '1000base-t')
                
                # Determine speed
                speed = SPEED_MAP.get(oper_mode) if oper_mode else None
                
                # Build update data
                update_data = {}
                
                if nb_iface.get('type', {}).get('value') != nb_type:
                    update_data['type'] = nb_type
                
                if speed and nb_iface.get('speed') != speed:
                    update_data['speed'] = speed
                
                # Update enabled status based on admin_link
                admin_enabled = port.get('admin_link') == 'Enabled'
                if nb_iface.get('enabled') != admin_enabled:
                    update_data['enabled'] = admin_enabled
                
                if update_data:
                    try:
                        netbox_service._request('PATCH', f'dcim/interfaces/{nb_iface["id"]}/', json=update_data)
                        stats['interfaces_updated'] += 1
                        logger.debug(f"Updated interface {name}/{port_num}: {update_data}")
                    except Exception as e:
                        stats['errors'].append({'device': name, 'interface': port_num, 'error': str(e)})
            
            # Handle SFP modules
            # Get module bays for this device
            try:
                nb_module_bays = netbox_service._request('GET', f'dcim/module-bays/?device_id={nb_device_id}')
                module_bay_map = {}
                for bay in nb_module_bays.get('results', []):
                    bay_name = bay['name']
                    # Map bay names to MCP slot numbers
                    # SFP+1 -> slot 21, SFP+2 -> slot 22, etc.
                    if 'SFP+' in bay_name:
                        bay_num = int(bay_name.replace('SFP+', ''))
                        mcp_slot = str(20 + bay_num)  # SFP+1 = slot 21
                        module_bay_map[mcp_slot] = bay
                    elif bay_name.isdigit():
                        # Direct slot number
                        module_bay_map[bay_name] = bay
                logger.debug(f"Module bay map for {name}: {list(module_bay_map.keys())}")
            except Exception as e:
                logger.warning(f"Failed to get module bays for {name}: {e}")
                module_bay_map = {}
            
            # Get existing modules
            try:
                nb_modules = netbox_service._request('GET', f'dcim/modules/?device_id={nb_device_id}')
                existing_modules = {m['module_bay']['id']: m for m in nb_modules.get('results', [])}
            except Exception as e:
                logger.warning(f"Failed to get modules for {name}: {e}")
                existing_modules = {}
            
            # Process SFPs from MCP
            for sfp in sfps:
                # Equipment data is already simplified from get_equipment()
                slot = sfp.get('slot')
                
                if not slot:
                    continue
                
                serial = sfp.get('serial_number', '')
                part_number = sfp.get('part_number', '')
                manufacturer = sfp.get('manufacturer', 'Unknown')
                
                # Find matching module bay
                module_bay = module_bay_map.get(slot)
                if not module_bay:
                    continue
                
                # Check if module already exists
                existing_module = existing_modules.get(module_bay['id'])
                
                # Get or create module type
                module_type_id = None
                try:
                    # Search for existing module type
                    mt_search = netbox_service._request('GET', f'dcim/module-types/?model__ic={part_number[:30]}')
                    if mt_search.get('results'):
                        module_type_id = mt_search['results'][0]['id']
                    else:
                        # Create module type
                        # First get/create manufacturer
                        mfr_search = netbox_service._request('GET', f'dcim/manufacturers/?name__ic={manufacturer}')
                        if mfr_search.get('results'):
                            mfr_id = mfr_search['results'][0]['id']
                        else:
                            # Create manufacturer
                            mfr_data = {'name': manufacturer, 'slug': manufacturer.lower().replace(' ', '-')}
                            mfr_result = netbox_service._request('POST', 'dcim/manufacturers/', json=mfr_data)
                            mfr_id = mfr_result['id']
                        
                        # Create module type
                        mt_data = {
                            'manufacturer': mfr_id,
                            'model': part_number or 'SFP',
                        }
                        mt_result = netbox_service._request('POST', 'dcim/module-types/', json=mt_data)
                        module_type_id = mt_result['id']
                except Exception as e:
                    logger.warning(f"Failed to get/create module type for {part_number}: {e}")
                    continue
                
                if existing_module:
                    # Update existing module
                    update_data = {'serial': serial}
                    if existing_module.get('module_type', {}).get('id') != module_type_id:
                        update_data['module_type'] = module_type_id
                    try:
                        netbox_service._request('PATCH', f'dcim/modules/{existing_module["id"]}/', json=update_data)
                        stats['modules_updated'] += 1
                    except Exception as e:
                        stats['errors'].append({'device': name, 'slot': slot, 'error': str(e)})
                else:
                    # Create new module
                    module_data = {
                        'device': nb_device_id,
                        'module_bay': module_bay['id'],
                        'module_type': module_type_id,
                        'serial': serial,
                    }
                    try:
                        netbox_service._request('POST', 'dcim/modules/', json=module_data)
                        stats['modules_created'] += 1
                    except Exception as e:
                        stats['errors'].append({'device': name, 'slot': slot, 'error': str(e)})
        
        logger.info(f"Ciena sync complete: {stats['devices_processed']} devices, "
                   f"{stats['interfaces_updated']} interfaces updated, "
                   f"{stats['modules_created']} modules created, "
                   f"{stats['modules_updated']} modules updated")
        
    except Exception as e:
        stats['errors'].append({'error': f'Sync failed: {e}'})
        logger.error(f"Ciena sync failed: {e}")
    
    return stats
