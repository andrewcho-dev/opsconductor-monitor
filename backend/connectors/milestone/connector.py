"""
Milestone VMS Connector

Polls Milestone XProtect for camera status and events.
"""

import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional, List
from base64 import b64encode

from connectors.base import PollingConnector, BaseNormalizer
from core.models import NormalizedAlert, ConnectorStatus
from core.alert_manager import get_alert_manager

from .normalizer import MilestoneNormalizer

logger = logging.getLogger(__name__)


class MilestoneConnector(PollingConnector):
    """
    Milestone XProtect VMS connector.
    
    Polls Milestone management server for camera status and events.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url = config.get("url", "").rstrip("/")
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.verify_ssl = config.get("verify_ssl", False)
        self._session: Optional[aiohttp.ClientSession] = None
        self._token: Optional[str] = None
    
    @property
    def connector_type(self) -> str:
        return "milestone"
    
    def _create_normalizer(self) -> BaseNormalizer:
        return MilestoneNormalizer()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session
    
    async def _authenticate(self) -> str:
        """Authenticate with Milestone server."""
        if self._token:
            return self._token
        
        session = await self._get_session()
        
        # Milestone uses various auth methods depending on version
        # Try Basic auth first
        auth = b64encode(f"{self.username}:{self.password}".encode()).decode()
        
        try:
            async with session.get(
                f"{self.url}/IServerCommandService/GetConfiguration",
                headers={"Authorization": f"Basic {auth}"},
                timeout=30
            ) as response:
                if response.status == 200:
                    self._token = auth
                    return self._token
        except Exception as e:
            logger.debug(f"Basic auth failed: {e}")
        
        raise ValueError("Milestone authentication failed")
    
    async def start(self) -> None:
        await super().start()
        logger.info(f"Milestone connector started (poll interval: {self.poll_interval}s)")
    
    async def stop(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
        self._token = None
        await super().stop()
        logger.info("Milestone connector stopped")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connectivity to Milestone server."""
        try:
            await self._authenticate()
            return {
                "success": True,
                "message": "Connected to Milestone XProtect",
                "details": {"url": self.url}
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "details": None
            }
    
    async def poll(self) -> List[NormalizedAlert]:
        """Poll Milestone for alerts."""
        alerts = []
        
        try:
            # Get camera status
            cameras = await self._get_cameras()
            
            for camera in cameras:
                if not camera.get("connected", True):
                    alerts.append(self._create_alert(camera, "camera_offline", {}))
                
                if camera.get("recording_error"):
                    alerts.append(self._create_alert(camera, "recording_error", {
                        "message": camera.get("error_message", "")
                    }))
            
            # Get system events/alarms
            events = await self._get_events()
            for event in events:
                alert = self._create_event_alert(event)
                if alert:
                    alerts.append(alert)
            
        except Exception as e:
            logger.error(f"Milestone poll failed: {e}")
            self.set_status(ConnectorStatus.ERROR, str(e))
        
        logger.debug(f"Milestone poll: {len(alerts)} alerts")
        return alerts
    
    async def _get_cameras(self) -> List[Dict]:
        """Get camera list and status."""
        try:
            session = await self._get_session()
            auth = await self._authenticate()
            
            async with session.get(
                f"{self.url}/IRecorderCommandService/GetCameraStatus",
                headers={"Authorization": f"Basic {auth}"},
                timeout=30
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("cameras", data.get("Cameras", []))
        except Exception as e:
            logger.debug(f"Could not get cameras: {e}")
        
        return []
    
    async def _get_events(self) -> List[Dict]:
        """Get recent events/alarms."""
        try:
            session = await self._get_session()
            auth = await self._authenticate()
            
            async with session.get(
                f"{self.url}/IEventServerService/GetEvents",
                headers={"Authorization": f"Basic {auth}"},
                timeout=30
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("events", data.get("Events", []))
        except Exception as e:
            logger.debug(f"Could not get events: {e}")
        
        return []
    
    def _create_alert(self, camera: Dict, event_type: str, event_data: Dict) -> NormalizedAlert:
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
    
    async def _process_alerts(self, alerts: List[NormalizedAlert]) -> None:
        alert_manager = get_alert_manager()
        for normalized in alerts:
            try:
                await alert_manager.process_alert(normalized)
            except Exception as e:
                logger.warning(f"Failed to process Milestone alert: {e}")


from connectors.registry import register_connector
register_connector("milestone", MilestoneConnector)
