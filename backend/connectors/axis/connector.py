"""
Axis Camera Connector

Polls Axis cameras via VAPIX API for status and events.
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

from .normalizer import AxisNormalizer

logger = logging.getLogger(__name__)


class AxisConnector(PollingConnector):
    """
    Axis camera connector using VAPIX API.
    
    Monitors camera status and events via HTTP polling.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.targets = config.get("targets", [])
        self.event_types = config.get("event_types", ["motion", "tampering", "storage_failure"])
        self._sessions: Dict[str, aiohttp.ClientSession] = {}
    
    @property
    def connector_type(self) -> str:
        return "axis"
    
    def _create_normalizer(self) -> BaseNormalizer:
        return AxisNormalizer()
    
    def _get_auth_header(self, username: str, password: str) -> str:
        """Create Basic auth header."""
        credentials = b64encode(f"{username}:{password}".encode()).decode()
        return f"Basic {credentials}"
    
    async def _get_session(self, target: Dict) -> aiohttp.ClientSession:
        """Get or create HTTP session for a target."""
        ip = target.get("ip")
        
        if ip not in self._sessions or self._sessions[ip].closed:
            auth_header = self._get_auth_header(
                target.get("username", "root"),
                target.get("password", "")
            )
            
            connector = aiohttp.TCPConnector(ssl=False)
            self._sessions[ip] = aiohttp.ClientSession(
                connector=connector,
                headers={"Authorization": auth_header}
            )
        
        return self._sessions[ip]
    
    async def start(self) -> None:
        """Start the connector."""
        if not self.targets:
            logger.warning("No Axis camera targets configured")
        
        await super().start()
        logger.info(f"Axis connector started (poll interval: {self.poll_interval}s, targets: {len(self.targets)})")
    
    async def stop(self) -> None:
        """Stop the connector."""
        # Close all sessions
        for session in self._sessions.values():
            if not session.closed:
                await session.close()
        self._sessions.clear()
        
        await super().stop()
        logger.info("Axis connector stopped")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connectivity to configured camera targets."""
        if not self.targets:
            return {
                "success": False,
                "message": "No targets configured",
                "details": None
            }
        
        results = []
        for target in self.targets:
            try:
                info = await self._get_device_info(target)
                results.append({
                    "ip": target.get("ip"),
                    "name": target.get("name"),
                    "success": True,
                    "model": info.get("model"),
                    "serial": info.get("serial"),
                })
            except Exception as e:
                results.append({
                    "ip": target.get("ip"),
                    "name": target.get("name"),
                    "success": False,
                    "error": str(e),
                })
        
        success_count = sum(1 for r in results if r.get("success"))
        
        return {
            "success": success_count > 0,
            "message": f"Connected to {success_count}/{len(self.targets)} cameras",
            "details": {"results": results}
        }
    
    async def poll(self) -> List[NormalizedAlert]:
        """Poll all camera targets for alerts."""
        alerts = []
        
        for target in self.targets:
            try:
                target_alerts = await self._poll_camera(target)
                alerts.extend(target_alerts)
            except Exception as e:
                logger.error(f"Error polling camera {target.get('ip')}: {e}")
                
                # Generate offline alert
                alerts.append(self._create_alert(
                    target,
                    "device_offline",
                    {"error": str(e)}
                ))
        
        logger.debug(f"Axis poll: {len(alerts)} alerts from {len(self.targets)} cameras")
        return alerts
    
    async def _poll_camera(self, target: Dict) -> List[NormalizedAlert]:
        """Poll single camera for status and events."""
        alerts = []
        ip = target.get("ip")
        
        try:
            # Check camera is reachable
            info = await self._get_device_info(target)
            
            # Check storage status
            try:
                storage = await self._get_storage_status(target)
                if storage:
                    storage_alerts = self._check_storage(target, storage)
                    alerts.extend(storage_alerts)
            except Exception as e:
                logger.debug(f"Could not get storage status for {ip}: {e}")
            
            # Check recording status
            try:
                recording = await self._get_recording_status(target)
                if recording and not recording.get("active"):
                    alerts.append(self._create_alert(target, "recording_error", recording))
            except Exception as e:
                logger.debug(f"Could not get recording status for {ip}: {e}")
            
        except Exception as e:
            logger.warning(f"Camera {ip} appears offline: {e}")
            alerts.append(self._create_alert(target, "device_offline", {"error": str(e)}))
        
        return alerts
    
    async def _get_device_info(self, target: Dict) -> Dict[str, Any]:
        """Get basic device info via VAPIX."""
        ip = target.get("ip")
        session = await self._get_session(target)
        
        async with session.get(
            f"http://{ip}/axis-cgi/basicdeviceinfo.cgi",
            timeout=10
        ) as response:
            response.raise_for_status()
            text = await response.text()
            
            # Parse response (varies by firmware version)
            info = {}
            for line in text.strip().split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    info[key.strip().lower()] = value.strip()
            
            return {
                "model": info.get("prodshortname", info.get("brand", "Axis Camera")),
                "serial": info.get("serialnumber", ""),
                "firmware": info.get("version", ""),
            }
    
    async def _get_storage_status(self, target: Dict) -> Optional[Dict]:
        """Get storage/disk status."""
        ip = target.get("ip")
        session = await self._get_session(target)
        
        try:
            async with session.get(
                f"http://{ip}/axis-cgi/disks/list.cgi",
                timeout=10
            ) as response:
                if response.status == 200:
                    text = await response.text()
                    # Parse disk info (simplified)
                    return {"raw": text, "available": True}
        except Exception:
            pass
        
        return None
    
    async def _get_recording_status(self, target: Dict) -> Optional[Dict]:
        """Get recording status."""
        # This varies by camera model
        return None
    
    def _check_storage(self, target: Dict, storage: Dict) -> List[NormalizedAlert]:
        """Check storage status and generate alerts if needed."""
        alerts = []
        
        raw = storage.get("raw", "")
        
        # Check for disk errors
        if "error" in raw.lower() or "fail" in raw.lower():
            alerts.append(self._create_alert(target, "storage_failure", storage))
        
        # Check for full disk
        if "full" in raw.lower() or "100%" in raw:
            alerts.append(self._create_alert(target, "storage_full", storage))
        
        return alerts
    
    def _create_alert(self, target: Dict, event_type: str, event_data: Dict) -> NormalizedAlert:
        """Create normalized alert from camera event."""
        raw_data = {
            "device_ip": target.get("ip"),
            "device_name": target.get("name"),
            "event_type": event_type,
            "event_data": event_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        return self.normalizer.normalize(raw_data)
    
    async def _process_alerts(self, alerts: List[NormalizedAlert]) -> None:
        """Process polled alerts."""
        alert_manager = get_alert_manager()
        
        for normalized in alerts:
            try:
                await alert_manager.process_alert(normalized)
            except Exception as e:
                logger.warning(f"Failed to process Axis alert: {e}")


# Register the connector
from connectors.registry import register_connector
register_connector("axis", AxisConnector)
