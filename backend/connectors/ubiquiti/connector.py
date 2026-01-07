"""
Ubiquiti UISP Connector

Polls Ubiquiti UISP for device status and alerts.
"""

import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional, List

from connectors.base import PollingConnector, BaseNormalizer
from core.models import NormalizedAlert, ConnectorStatus
from core.alert_manager import get_alert_manager

from .normalizer import UbiquitiNormalizer

logger = logging.getLogger(__name__)


class UbiquitiConnector(PollingConnector):
    """
    Ubiquiti UISP connector.
    
    Polls UISP API for device status, outages, and alerts.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url = config.get("url", "").rstrip("/")
        self.api_token = config.get("api_token", "")
        self.include_device_types = config.get("include_device_types", [])
        self.thresholds = config.get("thresholds", {
            "cpu_warning": 80,
            "memory_warning": 80,
        })
        self._session: Optional[aiohttp.ClientSession] = None
    
    @property
    def connector_type(self) -> str:
        return "ubiquiti"
    
    def _create_normalizer(self) -> BaseNormalizer:
        return UbiquitiNormalizer()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "x-auth-token": self.api_token,
                    "Content-Type": "application/json",
                },
                connector=aiohttp.TCPConnector(ssl=True)
            )
        return self._session
    
    async def start(self) -> None:
        if not self.url or not self.api_token:
            logger.warning("Ubiquiti UISP not configured (missing URL or API token)")
        await super().start()
        logger.info(f"Ubiquiti connector started (poll interval: {self.poll_interval}s)")
    
    async def stop(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
        await super().stop()
        logger.info("Ubiquiti connector stopped")
    
    async def test_connection(self) -> Dict[str, Any]:
        if not self.url or not self.api_token:
            return {"success": False, "message": "UISP not configured", "details": None}
        
        try:
            session = await self._get_session()
            async with session.get(f"{self.url}/nms/api/v2.1/devices?count=1", timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "message": "Connected to UISP",
                        "details": {"device_count": len(data)}
                    }
                elif response.status == 401:
                    return {"success": False, "message": "Invalid API token", "details": None}
                else:
                    return {"success": False, "message": f"HTTP {response.status}", "details": None}
        except Exception as e:
            return {"success": False, "message": str(e), "details": None}
    
    async def poll(self) -> List[NormalizedAlert]:
        alerts = []
        
        try:
            # Get devices and check status
            devices = await self._get_devices()
            for device in devices:
                device_alerts = self._check_device(device)
                alerts.extend(device_alerts)
            
            # Get outages
            outages = await self._get_outages()
            for outage in outages:
                alert = self._create_outage_alert(outage)
                if alert:
                    alerts.append(alert)
            
            # Get system alerts
            system_alerts = await self._get_alerts()
            for sys_alert in system_alerts:
                alert = self._create_system_alert(sys_alert)
                if alert:
                    alerts.append(alert)
            
        except Exception as e:
            logger.error(f"Ubiquiti poll failed: {e}")
            self.set_status(ConnectorStatus.ERROR, str(e))
        
        logger.debug(f"Ubiquiti poll: {len(alerts)} alerts")
        return alerts
    
    async def _get_devices(self) -> List[Dict]:
        session = await self._get_session()
        
        async with session.get(f"{self.url}/nms/api/v2.1/devices", timeout=30) as response:
            response.raise_for_status()
            devices = await response.json()
            
            # Filter by device type if specified
            if self.include_device_types:
                devices = [d for d in devices if d.get("type") in self.include_device_types]
            
            return devices
    
    async def _get_outages(self) -> List[Dict]:
        session = await self._get_session()
        
        try:
            async with session.get(f"{self.url}/nms/api/v2.1/outages?type=ongoing", timeout=15) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.debug(f"Could not get outages: {e}")
        
        return []
    
    async def _get_alerts(self) -> List[Dict]:
        session = await self._get_session()
        
        try:
            async with session.get(f"{self.url}/nms/api/v2.1/alerts", timeout=15) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.debug(f"Could not get alerts: {e}")
        
        return []
    
    def _check_device(self, device: Dict) -> List[NormalizedAlert]:
        alerts = []
        
        device_ip = device.get("ipAddress") or device.get("ip", "")
        device_name = device.get("name", "")
        
        # Check if device is offline
        status = device.get("overview", {}).get("status", "")
        if status.lower() in ("offline", "disconnected"):
            alerts.append(self._create_alert(device, "device_offline", {"status": status}))
            return alerts  # Skip other checks if offline
        
        # Check CPU
        cpu = device.get("overview", {}).get("cpu")
        if cpu is not None and cpu > self.thresholds.get("cpu_warning", 80):
            alerts.append(self._create_alert(device, "high_cpu", {"cpu_percent": cpu}))
        
        # Check memory
        memory = device.get("overview", {}).get("ram")
        if memory is not None and memory > self.thresholds.get("memory_warning", 80):
            alerts.append(self._create_alert(device, "high_memory", {"memory_percent": memory}))
        
        # Check signal (for wireless devices)
        signal = device.get("overview", {}).get("signal")
        if signal is not None and signal < -70:
            alerts.append(self._create_alert(device, "signal_degraded", {"signal": signal}))
        
        return alerts
    
    def _create_alert(self, device: Dict, alert_type: str, metrics: Dict) -> NormalizedAlert:
        raw_data = {
            "device_ip": device.get("ipAddress") or device.get("ip", ""),
            "device_name": device.get("name", ""),
            "device_id": device.get("id", ""),
            "device_type": device.get("type", ""),
            "alert_type": alert_type,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return self.normalizer.normalize(raw_data)
    
    def _create_outage_alert(self, outage: Dict) -> Optional[NormalizedAlert]:
        device = outage.get("device", {})
        if not device:
            return None
        
        raw_data = {
            "device_ip": device.get("ipAddress") or device.get("ip", ""),
            "device_name": device.get("name", ""),
            "alert_type": "outage",
            "metrics": {
                "start_time": outage.get("startTimestamp"),
                "duration": outage.get("duration"),
            },
            "timestamp": outage.get("startTimestamp"),
        }
        return self.normalizer.normalize(raw_data)
    
    def _create_system_alert(self, alert: Dict) -> Optional[NormalizedAlert]:
        device = alert.get("device", {})
        alert_type = alert.get("type", "").lower().replace(" ", "_")
        
        if not alert_type:
            return None
        
        raw_data = {
            "device_ip": device.get("ipAddress") or device.get("ip", "") if device else "",
            "device_name": device.get("name", "") if device else "",
            "alert_type": alert_type,
            "metrics": {"message": alert.get("message", "")},
            "timestamp": alert.get("timestamp"),
        }
        return self.normalizer.normalize(raw_data)
    
    async def _process_alerts(self, alerts: List[NormalizedAlert]) -> None:
        alert_manager = get_alert_manager()
        for normalized in alerts:
            try:
                await alert_manager.process_alert(normalized)
            except Exception as e:
                logger.warning(f"Failed to process Ubiquiti alert: {e}")


from connectors.registry import register_connector
register_connector("ubiquiti", UbiquitiConnector)
