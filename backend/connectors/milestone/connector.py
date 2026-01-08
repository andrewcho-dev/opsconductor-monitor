"""
Milestone VMS Connector

Polls Milestone XProtect for camera status and events.
Uses NTLM authentication for Windows domain credentials.
"""

import logging
import asyncio
import requests
from requests_ntlm import HttpNtlmAuth
from datetime import datetime
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

from backend.connectors.base import PollingConnector, BaseNormalizer
from backend.core.models import NormalizedAlert, ConnectorStatus
from backend.core.alert_manager import get_alert_manager

from .normalizer import MilestoneNormalizer

logger = logging.getLogger(__name__)

# Thread pool for sync requests
_executor = ThreadPoolExecutor(max_workers=4)


class MilestoneConnector(PollingConnector):
    """
    Milestone XProtect VMS connector.
    
    Polls Milestone management server for camera status and events.
    Uses NTLM authentication for Windows domain credentials.
    
    Username formats supported:
    - DOMAIN\\username (Windows style)
    - username@domain.local (UPN style)
    - username (local account)
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url = config.get("url", "").rstrip("/")
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.verify_ssl = config.get("verify_ssl", False)
        self._session: Optional[requests.Session] = None
        self._authenticated = False
        self._access_token: Optional[str] = None
    
    @property
    def connector_type(self) -> str:
        return "milestone"
    
    def _create_normalizer(self) -> BaseNormalizer:
        return MilestoneNormalizer()
    
    def _get_session(self) -> requests.Session:
        """Get or create requests session."""
        if self._session is None:
            self._session = requests.Session()
            self._session.verify = self.verify_ssl
        return self._session
    
    def _authenticate_sync(self) -> bool:
        """
        Authenticate with Milestone server using IDP token flow.
        
        Milestone API Gateway uses:
        1. NTLM auth to get Bearer token from /IDP/connect/token
        2. Bearer token for all subsequent API calls
        """
        if self._authenticated and self._access_token:
            return True
        
        session = self._get_session()
        
        try:
            # Get Bearer token via IDP with Windows credentials
            token_url = f"{self.url}/IDP/connect/token"
            logger.debug(f"Getting Milestone token from: {token_url}")
            
            response = session.post(
                token_url,
                data={
                    "grant_type": "windows_credentials",
                    "client_id": "GrantValidatorClient"
                },
                auth=HttpNtlmAuth(self.username, self.password),
                timeout=30
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self._access_token = token_data.get("access_token")
                if self._access_token:
                    self._authenticated = True
                    logger.info(f"Milestone authentication successful, got Bearer token")
                    return True
                else:
                    raise ValueError("No access_token in response")
            else:
                raise ValueError(f"Token request failed: {response.status_code} - {response.text[:200]}")
                
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Milestone authentication failed: {e}")
        
        raise ValueError(f"Milestone authentication failed. Check URL ({self.url}), username ({self.username}), and password.")
    
    async def _authenticate(self) -> bool:
        """Async wrapper for NTLM authentication."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._authenticate_sync)
    
    async def start(self) -> None:
        await super().start()
        logger.info(f"Milestone connector started (poll interval: {self.poll_interval}s)")
    
    async def stop(self) -> None:
        if self._session:
            self._session.close()
        self._session = None
        self._authenticated = False
        await super().stop()
        logger.info("Milestone connector stopped")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connectivity to Milestone server."""
        try:
            # Reset session to force fresh auth
            self._session = None
            self._authenticated = False
            await self._authenticate()
            return {
                "success": True,
                "message": f"Connected to Milestone XProtect at {self.url}",
                "details": {"url": self.url, "username": self.username}
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "details": {"url": self.url, "username": self.username}
            }
    
    def _poll_sync(self) -> List[NormalizedAlert]:
        """Synchronous poll implementation."""
        alerts = []
        
        try:
            # Ensure authenticated
            self._authenticate_sync()
            
            # Get camera status
            cameras = self._get_cameras_sync()
            hardware = self._get_hardware_sync()
            
            # Build hardware lookup for IP addresses
            hardware_ips = {}
            for hw in hardware:
                hw_id = hw.get("id", "")
                hw_ip = hw.get("address", "") or hw.get("ip", "")
                if hw_id and hw_ip:
                    hardware_ips[hw_id] = hw_ip
            
            for camera in cameras:
                # Get camera's hardware parent for IP
                parent = camera.get("relations", {}).get("parent", {})
                parent_id = parent.get("id", "")
                camera_ip = hardware_ips.get(parent_id, "")
                
                # Check if camera is enabled but not recording
                if camera.get("enabled", True) and not camera.get("recordingEnabled", True):
                    alert = self._create_alert_with_ip(camera, camera_ip, "recording_stopped", {
                        "message": f"Recording disabled for {camera.get('name', 'Unknown')}"
                    })
                    if alert:
                        alerts.append(alert)
            
            # Get hardware status - check for offline devices
            for hw in hardware:
                hw_enabled = hw.get("enabled", True)
                # Hardware items that are disabled or have connection issues
                if not hw_enabled:
                    hw_ip = hw.get("address", "") or hw.get("ip", "")
                    alert = self._create_alert_with_ip(hw, hw_ip, "camera_offline", {
                        "message": f"Hardware device {hw.get('name', 'Unknown')} is disabled"
                    })
                    if alert:
                        alerts.append(alert)
            
            # Get system alarms
            alarms = self._get_events_sync()
            for alarm in alarms:
                alert = self._create_event_alert(alarm)
                if alert:
                    alerts.append(alert)
            
            self.set_status(ConnectorStatus.CONNECTED)
            
        except Exception as e:
            logger.error(f"Milestone poll failed: {e}")
            self.set_status(ConnectorStatus.ERROR, str(e))
        
        logger.info(f"Milestone poll: {len(cameras) if 'cameras' in dir() else 0} cameras, {len(alerts)} alerts")
        return alerts
    
    async def poll(self) -> List[NormalizedAlert]:
        """Poll Milestone for alerts (async wrapper)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._poll_sync)
    
    def _api_get(self, endpoint: str) -> Optional[Dict]:
        """Make authenticated GET request to Milestone API."""
        session = self._get_session()
        headers = {"Authorization": f"Bearer {self._access_token}"}
        
        try:
            response = session.get(f"{self.url}{endpoint}", headers=headers, timeout=30)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                # Token expired, re-authenticate
                self._authenticated = False
                self._access_token = None
                self._authenticate_sync()
                headers = {"Authorization": f"Bearer {self._access_token}"}
                response = session.get(f"{self.url}{endpoint}", headers=headers, timeout=30)
                if response.status_code == 200:
                    return response.json()
            logger.debug(f"API {endpoint} returned {response.status_code}")
        except Exception as e:
            logger.debug(f"API {endpoint} failed: {e}")
        
        return None
    
    def _get_cameras_sync(self) -> List[Dict]:
        """Get camera list and status from Milestone REST API."""
        data = self._api_get("/API/rest/v1/cameras")
        if data:
            cameras = data.get("array", [])
            logger.info(f"Got {len(cameras)} cameras from Milestone")
            return cameras
        
        logger.warning("Could not get camera list from Milestone API")
        return []
    
    def _get_hardware_sync(self) -> List[Dict]:
        """Get hardware (recording servers, devices) from Milestone REST API."""
        data = self._api_get("/API/rest/v1/hardware")
        if data:
            hardware = data.get("array", [])
            logger.debug(f"Got {len(hardware)} hardware items from Milestone")
            return hardware
        return []
    
    def _get_recorders_sync(self) -> List[Dict]:
        """Get recording servers from Milestone REST API."""
        data = self._api_get("/API/rest/v1/recorders")
        if data:
            recorders = data.get("array", [])
            logger.debug(f"Got {len(recorders)} recorders from Milestone")
            return recorders
        return []
    
    def _get_events_sync(self) -> List[Dict]:
        """Get recent events/alarms from Milestone REST API."""
        # Milestone REST API doesn't have a direct events endpoint
        # Events come from the Event Server or via alarms
        data = self._api_get("/API/rest/v1/alarms")
        if data:
            alarms = data.get("array", [])
            logger.debug(f"Got {len(alarms)} alarms from Milestone")
            return alarms
        return []
    
    def _create_alert_with_ip(self, device: Dict, device_ip: str, event_type: str, event_data: Dict) -> Optional[NormalizedAlert]:
        """Create alert with explicit IP address."""
        raw_data = {
            "device_ip": device_ip,
            "device_name": device.get("name") or device.get("displayName", ""),
            "camera_id": device.get("id", ""),
            "event_type": event_type,
            "event_data": event_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return self.normalizer.normalize(raw_data)
    
    def _create_alert(self, camera: Dict, event_type: str, event_data: Dict) -> Optional[NormalizedAlert]:
        """Create alert from camera data. Returns None if event type is disabled or no valid IP."""
        raw_data = {
            "device_ip": camera.get("ip") or camera.get("address", ""),
            "device_name": camera.get("name") or camera.get("Name", ""),
            "camera_id": camera.get("id") or camera.get("Id", ""),
            "event_type": event_type,
            "event_data": event_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return self.normalizer.normalize(raw_data)
    
    def _create_event_alert(self, event: Dict) -> Optional[NormalizedAlert]:
        """Create alert from event data. Returns None if event type is disabled or no valid IP."""
        event_type = event.get("type") or event.get("Type", "")
        if not event_type:
            return None
        
        raw_data = {
            "device_ip": event.get("cameraIp") or event.get("sourceIp", ""),
            "device_name": event.get("cameraName") or event.get("sourceName", ""),
            "event_type": event_type.lower().replace(" ", "_"),
            "event_data": {"message": event.get("message") or event.get("Message", "")},
            "timestamp": event.get("timestamp") or event.get("Timestamp"),
        }
        return self.normalizer.normalize(raw_data)
    
    async def _process_alerts(self, alerts: List[Optional[NormalizedAlert]]) -> None:
        """Process alerts, skipping None (disabled events or no valid IP)."""
        alert_manager = get_alert_manager()
        for normalized in alerts:
            if normalized is None:
                continue
            try:
                await alert_manager.process_alert(normalized)
            except Exception as e:
                logger.warning(f"Failed to process Milestone alert: {e}")
