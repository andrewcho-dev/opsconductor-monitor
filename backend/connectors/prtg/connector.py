"""
PRTG Connector

Receives alerts from PRTG via webhook and polling.
"""

import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional, List

from connectors.base import WebhookConnector, PollingConnector, BaseNormalizer
from core.models import NormalizedAlert, ConnectorStatus
from core.alert_manager import get_alert_manager

from .normalizer import PRTGNormalizer

logger = logging.getLogger(__name__)


class PRTGConnector(WebhookConnector):
    """
    PRTG Network Monitor connector.
    
    Supports both:
    - Webhook: Receives real-time alerts via HTTP POST
    - Polling: Periodically fetches sensors in alert state
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url = config.get("url", "").rstrip("/")
        self.api_token = config.get("api_token", "")
        self.username = config.get("username", "")
        self.passhash = config.get("passhash", "")
        self.verify_ssl = config.get("verify_ssl", True)
        self.poll_interval = config.get("poll_interval", 60)
        self._session: Optional[aiohttp.ClientSession] = None
        self._polling = False
        self._poll_task = None
    
    @property
    def connector_type(self) -> str:
        return "prtg"
    
    def _create_normalizer(self) -> BaseNormalizer:
        return PRTGNormalizer()
    
    def _get_auth_params(self) -> Dict[str, str]:
        """Get authentication parameters."""
        if self.api_token:
            return {"apitoken": self.api_token}
        elif self.username and self.passhash:
            return {"username": self.username, "passhash": self.passhash}
        else:
            raise ValueError("PRTG authentication not configured")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session
    
    async def _request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make authenticated request to PRTG API."""
        if not self.url:
            raise ValueError("PRTG URL not configured")
        
        url = f"{self.url}{endpoint}"
        request_params = self._get_auth_params()
        if params:
            request_params.update(params)
        
        session = await self._get_session()
        
        async with session.get(url, params=request_params, timeout=30) as response:
            response.raise_for_status()
            
            if endpoint.endswith(".json"):
                return await response.json()
            else:
                return {"raw": await response.text()}
    
    async def start(self) -> None:
        """Start the connector (webhook + optional polling)."""
        await super().start()
        
        # Start polling if enabled
        if self.poll_interval > 0:
            self._polling = True
            self._poll_task = asyncio.create_task(self._poll_loop())
            logger.info(f"PRTG polling started (interval: {self.poll_interval}s)")
    
    async def stop(self) -> None:
        """Stop the connector."""
        self._polling = False
        
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None
        
        if self._session and not self._session.closed:
            await self._session.close()
        
        await super().stop()
        logger.info("PRTG connector stopped")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connectivity to PRTG server."""
        try:
            # Try getstatus.json first
            try:
                status = await self._request("/api/getstatus.json")
                return {
                    "success": True,
                    "message": "Connected to PRTG",
                    "details": {
                        "version": status.get("Version"),
                        "alarms": status.get("Alarms"),
                        "new_alarms": status.get("NewAlarms"),
                    }
                }
            except aiohttp.ClientResponseError as e:
                if e.status == 404:
                    # Fallback to table.json
                    result = await self._request("/api/table.json", {
                        "content": "sensors",
                        "count": 1
                    })
                    return {
                        "success": True,
                        "message": "Connected to PRTG",
                        "details": {
                            "sensor_count": result.get("treesize", 0)
                        }
                    }
                raise
        except Exception as e:
            logger.error(f"PRTG connection test failed: {e}")
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "details": None
            }
    
    async def handle_webhook(self, data: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """
        Handle incoming PRTG webhook.
        
        PRTG sends form-encoded data like:
        sensorid=123&deviceid=456&device=Switch1&status=Down&message=...
        """
        try:
            # Normalize the data
            normalized = self.normalizer.normalize(data)
            
            logger.info(f"PRTG webhook: {normalized.title} ({normalized.severity.value})")
            
            # Process through alert manager
            alert_manager = get_alert_manager()
            await alert_manager.process_alert(normalized)
            
            return normalized
            
        except Exception as e:
            logger.exception(f"Error processing PRTG webhook: {e}")
            raise
    
    async def poll(self) -> List[NormalizedAlert]:
        """Poll PRTG for sensors in alert state."""
        alerts = []
        
        try:
            # Get sensors in alert states (down, warning, unusual)
            params = {
                "content": "sensors",
                "columns": "objid,sensor,device,group,probe,status,status_raw,message,lastvalue,priority,type,host",
                "filter_status": [4, 5, 10, 13, 14],  # Warning, Down, Unusual, Down Ack, Down Partial
                "count": 5000,
            }
            
            result = await self._request("/api/table.json", params)
            sensors = result.get("sensors", [])
            
            for sensor in sensors:
                try:
                    normalized = self.normalizer.normalize(sensor)
                    alerts.append(normalized)
                except Exception as e:
                    logger.warning(f"Failed to normalize PRTG sensor {sensor.get('objid')}: {e}")
            
            logger.debug(f"PRTG poll: {len(alerts)} alerts found")
            
        except Exception as e:
            logger.error(f"PRTG poll failed: {e}")
            self.set_status(ConnectorStatus.ERROR, str(e))
        
        return alerts
    
    async def _poll_loop(self) -> None:
        """Polling loop for PRTG sensors."""
        alert_manager = get_alert_manager()
        
        while self._polling:
            try:
                alerts = await self.poll()
                self.last_poll_at = datetime.utcnow()
                
                # Process each alert
                for normalized in alerts:
                    try:
                        await alert_manager.process_alert(normalized)
                        self.increment_alerts()
                    except Exception as e:
                        logger.warning(f"Failed to process PRTG alert: {e}")
                
                self.set_status(ConnectorStatus.CONNECTED)
                
            except Exception as e:
                self.set_status(ConnectorStatus.ERROR, str(e))
                logger.exception("Error in PRTG poll loop")
            
            await asyncio.sleep(self.poll_interval)
    
    async def get_devices(self) -> List[Dict]:
        """Get devices from PRTG."""
        params = {
            "content": "devices",
            "columns": "objid,device,host,group,probe,status,message,priority,tags",
            "count": 50000,
        }
        
        result = await self._request("/api/table.json", params)
        return result.get("devices", [])
    
    async def get_sensors(self, device_id: int = None) -> List[Dict]:
        """Get sensors from PRTG."""
        params = {
            "content": "sensors",
            "columns": "objid,sensor,device,group,status,message,lastvalue,type",
            "count": 50000,
        }
        
        if device_id:
            params["id"] = device_id
        
        result = await self._request("/api/table.json", params)
        return result.get("sensors", [])
    
    async def acknowledge_alarm(self, sensor_id: int, message: str = "") -> bool:
        """Acknowledge an alarm in PRTG."""
        try:
            await self._request("/api/acknowledgealarm.htm", {
                "id": sensor_id,
                "ackmsg": message
            })
            return True
        except Exception as e:
            logger.error(f"Error acknowledging PRTG alarm: {e}")
            return False


# Register the connector
from connectors.registry import register_connector
register_connector("prtg", PRTGConnector)
