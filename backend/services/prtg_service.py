"""
PRTG Service

Handles communication with PRTG Network Monitor API for:
- Fetching devices, sensors, and groups
- Getting sensor data and alerts
- Syncing devices to NetBox
"""

import os
import logging
import requests
from typing import Optional, Dict, List, Any
from urllib.parse import urljoin
from datetime import datetime

from backend.database import DatabaseConnection

logger = logging.getLogger(__name__)


class PRTGService:
    """Service for interacting with PRTG Network Monitor API."""
    
    # PRTG status codes
    STATUS_CODES = {
        1: 'Unknown',
        2: 'Scanning',
        3: 'Up',
        4: 'Warning',
        5: 'Down',
        6: 'No Probe',
        7: 'Paused by User',
        8: 'Paused by Dependency',
        9: 'Paused by Schedule',
        10: 'Unusual',
        11: 'Not Licensed',
        12: 'Paused Until',
        13: 'Down (Acknowledged)',
        14: 'Down (Partial)'
    }
    
    def __init__(self, url: str = None, api_token: str = None, 
                 username: str = None, passhash: str = None):
        """
        Initialize PRTG service.
        
        Args:
            url: PRTG server URL (e.g., https://prtg.example.com)
            api_token: API token for authentication (preferred)
            username: Username for passhash authentication
            passhash: Passhash for authentication
        """
        self.url = url or self._get_setting('url')
        self.api_token = api_token or self._get_setting('api_token')
        self.username = username or self._get_setting('username')
        self.passhash = passhash or self._get_setting('passhash')
        self.verify_ssl = self._get_setting('verify_ssl', 'true').lower() == 'true'
        
        # Ensure URL has no trailing slash
        if self.url:
            self.url = self.url.rstrip('/')
    
    def _get_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get PRTG setting from database."""
        try:
            db = DatabaseConnection()
            with db.cursor() as cur:
                cur.execute(
                    "SELECT value FROM system_settings WHERE key = %s",
                    (f'prtg_{key}',)
                )
                row = cur.fetchone()
                return row['value'] if row else default
        except Exception:
            return default
    
    def _get_auth_params(self) -> Dict[str, str]:
        """Get authentication parameters for API requests."""
        if self.api_token:
            return {'apitoken': self.api_token}
        elif self.username and self.passhash:
            return {'username': self.username, 'passhash': self.passhash}
        else:
            raise ValueError("PRTG authentication not configured. Set API token or username/passhash.")
    
    def _request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make authenticated request to PRTG API."""
        if not self.url:
            raise ValueError("PRTG URL not configured")
        
        url = f"{self.url}{endpoint}"
        request_params = self._get_auth_params()
        if params:
            request_params.update(params)
        
        logger.debug(f"PRTG API request: {endpoint}")
        
        response = requests.get(
            url,
            params=request_params,
            verify=self.verify_ssl,
            timeout=30
        )
        response.raise_for_status()
        
        # PRTG returns JSON for .json endpoints
        if endpoint.endswith('.json'):
            return response.json()
        else:
            return {'raw': response.text}
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to PRTG server."""
        try:
            # Try getstatus.json first (older PRTG versions)
            try:
                status = self._request('/api/getstatus.json')
                return {
                    'connected': True,
                    'version': status.get('Version'),
                    'clock': status.get('Clock'),
                    'is_cluster': status.get('IsCluster'),
                    'new_messages': status.get('NewMessages'),
                    'new_alarms': status.get('NewAlarms'),
                    'alarms': status.get('Alarms'),
                    'ack_alarms': status.get('AckAlarms'),
                    'new_todos': status.get('NewToDos'),
                    'background_tasks': status.get('BackgroundTasks')
                }
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    # Fallback: use table.json to verify connection works
                    # This works on newer PRTG versions where getstatus.json may not exist
                    result = self._request('/api/table.json', {'content': 'sensors', 'count': 1})
                    sensor_count = result.get('treesize', 0)
                    return {
                        'connected': True,
                        'version': 'PRTG',  # Version not available via table.json
                        'sensor_count': sensor_count
                    }
                raise
        except requests.exceptions.RequestException as e:
            logger.error(f"PRTG connection test failed: {e}")
            return {
                'connected': False,
                'error': str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get PRTG system status."""
        return self.test_connection()
    
    def get_devices(self, group: str = None, status: str = None, 
                    search: str = None) -> List[Dict]:
        """
        Get devices from PRTG.
        
        Args:
            group: Filter by group name
            status: Filter by status (up, down, warning, paused)
            search: Search term for device name
        """
        params = {
            'content': 'devices',
            'columns': 'objid,device,host,group,probe,status,message,priority,tags,active,type'
        }
        
        # Add filters
        if status:
            status_map = {
                'up': 3,
                'warning': 4,
                'down': 5,
                'paused': 7
            }
            if status.lower() in status_map:
                params['filter_status'] = status_map[status.lower()]
        
        result = self._request('/api/table.json', params)
        devices = result.get('devices', [])
        
        # Apply additional filters
        if group:
            devices = [d for d in devices if group.lower() in (d.get('group', '') or '').lower()]
        if search:
            devices = [d for d in devices if search.lower() in (d.get('device', '') or '').lower() 
                      or search.lower() in (d.get('host', '') or '').lower()]
        
        # Enrich with status text
        for device in devices:
            status_id = device.get('status_raw') or device.get('status')
            if isinstance(status_id, int):
                device['status_text'] = self.STATUS_CODES.get(status_id, 'Unknown')
        
        return devices
    
    def get_device_details(self, device_id: int) -> Dict:
        """Get detailed information for a specific device."""
        params = {
            'id': device_id,
            'content': 'devices',
            'columns': 'objid,device,host,group,probe,status,message,priority,tags,active,type,location,comments'
        }
        
        result = self._request('/api/table.json', params)
        devices = result.get('devices', [])
        
        if devices:
            device = devices[0]
            # Get additional properties
            try:
                props = self._request('/api/getobjectproperty.htm', {
                    'id': device_id,
                    'name': 'location,comments,serviceurl'
                })
                device.update(props)
            except Exception:
                pass
            return device
        
        return None
    
    def get_sensors(self, device_id: int = None, status: str = None,
                    sensor_type: str = None) -> List[Dict]:
        """
        Get sensors from PRTG.
        
        Args:
            device_id: Filter by device ID
            status: Filter by status
            sensor_type: Filter by sensor type
        """
        params = {
            'content': 'sensors',
            'columns': 'objid,sensor,device,group,probe,status,message,lastvalue,priority,tags,type,active,parentid'
        }
        
        if device_id:
            params['id'] = device_id
        
        if status:
            status_map = {
                'up': 3,
                'warning': 4,
                'down': 5,
                'paused': 7,
                'unusual': 10
            }
            if status.lower() in status_map:
                params['filter_status'] = status_map[status.lower()]
        
        result = self._request('/api/table.json', params)
        sensors = result.get('sensors', [])
        
        # Apply type filter
        if sensor_type:
            sensors = [s for s in sensors if sensor_type.lower() in (s.get('type', '') or '').lower()]
        
        return sensors
    
    def get_sensor_details(self, sensor_id: int) -> Dict:
        """Get detailed information for a specific sensor."""
        result = self._request('/api/getsensordetails.json', {'id': sensor_id})
        return result.get('sensordata', {})
    
    def get_sensor_history(self, sensor_id: int, start_date: str = None,
                          end_date: str = None, avg: int = 0) -> Dict:
        """
        Get historical data for a sensor.
        
        Args:
            sensor_id: Sensor ID
            start_date: Start date (YYYY-MM-DD-HH-MM-SS)
            end_date: End date (YYYY-MM-DD-HH-MM-SS)
            avg: Averaging interval in seconds (0 = no averaging)
        """
        params = {
            'id': sensor_id,
            'avg': avg
        }
        
        if start_date:
            params['sdate'] = start_date
        if end_date:
            params['edate'] = end_date
        
        return self._request('/api/historicdata.json', params)
    
    def get_groups(self) -> List[Dict]:
        """Get device groups from PRTG."""
        params = {
            'content': 'groups',
            'columns': 'objid,group,probe,status,message,priority,tags,active'
        }
        
        result = self._request('/api/table.json', params)
        return result.get('groups', [])
    
    def get_probes(self) -> List[Dict]:
        """Get probes from PRTG."""
        params = {
            'content': 'probes',
            'columns': 'objid,probe,status,message,active'
        }
        
        result = self._request('/api/table.json', params)
        return result.get('probes', [])
    
    def get_alerts(self, status: str = None) -> List[Dict]:
        """
        Get current alerts from PRTG.
        
        Args:
            status: Filter by status (down, warning, unusual)
        """
        # Get sensors in alert state
        params = {
            'content': 'sensors',
            'columns': 'objid,sensor,device,group,probe,status,message,lastvalue,priority,downtimesince,lastdown'
        }
        
        # Filter for alert states
        if status == 'down':
            params['filter_status'] = 5
        elif status == 'warning':
            params['filter_status'] = 4
        elif status == 'unusual':
            params['filter_status'] = 10
        else:
            # All alert states
            params['filter_status'] = [4, 5, 10, 13, 14]
        
        result = self._request('/api/table.json', params)
        return result.get('sensors', [])
    
    def acknowledge_alarm(self, sensor_id: int, message: str = '') -> bool:
        """Acknowledge an alarm in PRTG."""
        try:
            self._request('/api/acknowledgealarm.htm', {
                'id': sensor_id,
                'ackmsg': message
            })
            return True
        except Exception as e:
            logger.error(f"Error acknowledging alarm: {e}")
            return False
    
    def pause_object(self, object_id: int, duration: int = None, 
                     message: str = '') -> bool:
        """
        Pause a sensor, device, or group.
        
        Args:
            object_id: Object ID to pause
            duration: Duration in minutes (None = indefinite)
            message: Pause message
        """
        try:
            params = {
                'id': object_id,
                'action': 0,  # 0 = pause, 1 = resume
                'pausemsg': message
            }
            if duration:
                params['duration'] = duration
            
            self._request('/api/pause.htm', params)
            return True
        except Exception as e:
            logger.error(f"Error pausing object: {e}")
            return False
    
    def resume_object(self, object_id: int) -> bool:
        """Resume a paused sensor, device, or group."""
        try:
            self._request('/api/pause.htm', {
                'id': object_id,
                'action': 1  # Resume
            })
            return True
        except Exception as e:
            logger.error(f"Error resuming object: {e}")
            return False
    
    # ========================================================================
    # NetBox Sync Methods
    # ========================================================================
    
    def preview_netbox_sync(self) -> Dict[str, Any]:
        """Preview what would be synced to NetBox."""
        from backend.services.netbox_service import NetBoxService
        
        prtg_devices = self.get_devices()
        netbox_service = NetBoxService()
        
        # Get existing NetBox devices
        try:
            netbox_devices = netbox_service.get_devices()
            netbox_ips = {d.get('primary_ip4', {}).get('address', '').split('/')[0] 
                         for d in netbox_devices if d.get('primary_ip4')}
            netbox_names = {d.get('name', '').lower() for d in netbox_devices}
        except Exception:
            netbox_ips = set()
            netbox_names = set()
        
        # Categorize devices
        to_create = []
        existing = []
        
        for device in prtg_devices:
            host = device.get('host', '')
            name = device.get('device', '').lower()
            
            if host in netbox_ips or name in netbox_names:
                existing.append({
                    'prtg_id': device.get('objid'),
                    'name': device.get('device'),
                    'host': host,
                    'group': device.get('group'),
                    'status': 'exists_in_netbox'
                })
            else:
                to_create.append({
                    'prtg_id': device.get('objid'),
                    'name': device.get('device'),
                    'host': host,
                    'group': device.get('group'),
                    'type': device.get('type'),
                    'tags': device.get('tags'),
                    'status': 'will_create'
                })
        
        return {
            'total_prtg_devices': len(prtg_devices),
            'existing_in_netbox': len(existing),
            'to_create': len(to_create),
            'devices_to_create': to_create,
            'devices_existing': existing
        }
    
    def sync_to_netbox(self, dry_run: bool = False, device_ids: List[int] = None,
                       default_site: int = None, default_role: int = None,
                       update_existing: bool = False, 
                       create_missing: bool = True) -> Dict[str, Any]:
        """
        Sync PRTG devices to NetBox.
        
        Args:
            dry_run: If True, don't make changes, just report what would happen
            device_ids: Specific device IDs to sync (None = all)
            default_site: Default NetBox site ID for new devices
            default_role: Default NetBox device role ID
            update_existing: Update devices that already exist in NetBox
            create_missing: Create devices that don't exist in NetBox
        """
        from backend.services.netbox_service import NetBoxService
        
        netbox_service = NetBoxService()
        
        # Get PRTG devices
        prtg_devices = self.get_devices()
        if device_ids:
            prtg_devices = [d for d in prtg_devices if d.get('objid') in device_ids]
        
        results = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': [],
            'details': []
        }
        
        def sync_single_device(device):
            detail = {'processed': 1, 'created': 0, 'updated': 0, 'skipped': 0, 'error': None, 'detail': None}
            try:
                host = device.get('host', '')
                name = device.get('device', '')
                
                # Check if device exists in NetBox
                existing = netbox_service.find_device_by_ip(host) or \
                          netbox_service.find_device_by_name(name)
                
                if existing:
                    if update_existing and not dry_run:
                        netbox_service.update_device(existing['id'], {
                            'comments': f"Synced from PRTG. Group: {device.get('group')}"
                        })
                        detail['updated'] = 1
                        detail['detail'] = {'action': 'updated', 'name': name, 'host': host, 'netbox_id': existing['id']}
                    else:
                        detail['skipped'] = 1
                        detail['detail'] = {'action': 'skipped', 'name': name, 'host': host, 'reason': 'exists_in_netbox'}
                elif create_missing:
                    if not dry_run:
                        new_device = netbox_service.create_device({
                            'name': name,
                            'site': default_site,
                            'device_role': default_role,
                            'device_type': 1,
                            'status': 'active',
                            'primary_ip4': host,
                            'comments': f"Imported from PRTG. Group: {device.get('group')}, Tags: {device.get('tags')}"
                        })
                        detail['created'] = 1
                        detail['detail'] = {'action': 'created', 'name': name, 'host': host, 'netbox_id': new_device.get('id')}
                    else:
                        detail['created'] = 1
                        detail['detail'] = {'action': 'would_create', 'name': name, 'host': host}
                        
            except Exception as e:
                logger.error(f"Error syncing device {device.get('device')}: {e}")
                detail['error'] = {'device': device.get('device'), 'error': str(e)}
            
            return detail
        
        # Process devices in parallel
        from concurrent.futures import ThreadPoolExecutor
        import os
        cpu_count = os.cpu_count() or 4
        max_workers = min(cpu_count * 5, len(prtg_devices), 100)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            sync_results = list(executor.map(sync_single_device, prtg_devices))
        
        for detail in sync_results:
            results['processed'] += detail['processed']
            results['created'] += detail['created']
            results['updated'] += detail['updated']
            results['skipped'] += detail['skipped']
            if detail['detail']:
                results['details'].append(detail['detail'])
            if detail['error']:
                results['errors'].append(detail['error'])
        
        return results
