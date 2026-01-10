"""
MCP (Ciena) Connector

Polls Ciena MCP for alarms and events.
"""

import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional, List

from backend.connectors.base import PollingConnector, BaseNormalizer
from backend.core.models import NormalizedAlert, ConnectorStatus
from backend.core.alert_manager import get_alert_manager

from .normalizer import MCPNormalizer

logger = logging.getLogger(__name__)


class MCPConnector(PollingConnector):
    """
    Ciena MCP (Management Control Plane) connector.
    
    Polls MCP for active alarms and events.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url = config.get("url", "").rstrip("/")
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.verify_ssl = config.get("verify_ssl", False)
        self._token: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None
    
    @property
    def connector_type(self) -> str:
        return "mcp"
    
    def _create_normalizer(self) -> BaseNormalizer:
        return MCPNormalizer()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session
    
    async def _authenticate(self) -> str:
        """Authenticate and get bearer token."""
        if self._token:
            return self._token
        
        if not self.url or not self.username or not self.password:
            raise ValueError("MCP not configured (URL, username, password required)")
        
        url = f"{self.url}/tron/api/v1/tokens"
        payload = {
            "username": self.username,
            "password": self.password
        }
        
        session = await self._get_session()
        
        async with session.post(url, json=payload, timeout=30) as response:
            response.raise_for_status()
            data = await response.json()
            
            if not data.get("isSuccessful"):
                raise ValueError(f"MCP auth failed: {data.get('message', 'Unknown error')}")
            
            self._token = data.get("token")
            logger.info(f"MCP authenticated as {self.username}")
            return self._token
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make authenticated request to MCP API."""
        token = await self._authenticate()
        
        url = f"{self.url}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
        
        session = await self._get_session()
        
        async with session.request(method, url, headers=headers, timeout=60, **kwargs) as response:
            # Handle token expiration
            if response.status == 401:
                self._token = None
                token = await self._authenticate()
                headers["Authorization"] = f"Bearer {token}"
                async with session.request(method, url, headers=headers, timeout=60, **kwargs) as retry_response:
                    retry_response.raise_for_status()
                    if retry_response.status == 204:
                        return {}
                    return await retry_response.json()
            
            response.raise_for_status()
            
            if response.status == 204:
                return {}
            
            return await response.json()
    
    async def start(self) -> None:
        """Start the connector."""
        await super().start()
        logger.info(f"MCP connector started (poll interval: {self.poll_interval}s)")
    
    async def stop(self) -> None:
        """Stop the connector."""
        if self._session and not self._session.closed:
            await self._session.close()
        
        self._token = None
        await super().stop()
        logger.info("MCP connector stopped")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connectivity to MCP."""
        try:
            await self._authenticate()
            return {
                "success": True,
                "message": "Connected to Ciena MCP",
                "details": {
                    "url": self.url,
                    "user": self.username
                }
            }
        except Exception as e:
            logger.error(f"MCP connection test failed: {e}")
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "details": None
            }
    
    async def poll(self) -> List[NormalizedAlert]:
        """Poll MCP for active alarms."""
        alerts = []
        
        try:
            # Get active alarms
            result = await self._request("GET", "/nsi/api/search/alarms?limit=500&filter=status==ACTIVE")
            alarms = result.get("data", [])
            
            for alarm in alarms:
                try:
                    normalized = self.normalizer.normalize(alarm)
                    alerts.append(normalized)
                except Exception as e:
                    logger.warning(f"Failed to normalize MCP alarm {alarm.get('id')}: {e}")
            
            logger.debug(f"MCP poll: {len(alerts)} active alarms")
            
        except Exception as e:
            logger.error(f"MCP poll failed: {e}")
            self.set_status(ConnectorStatus.ERROR, str(e))
        
        return alerts
    
    async def _process_alerts(self, alerts: List[NormalizedAlert]) -> None:
        """Process polled alerts."""
        alert_manager = get_alert_manager()
        
        for normalized in alerts:
            try:
                await alert_manager.process_alert(normalized)
            except Exception as e:
                logger.warning(f"Failed to process MCP alert: {e}")
    
    async def get_devices(self) -> List[Dict]:
        """Get network devices from MCP."""
        all_devices = []
        offset = 0
        limit = 100
        
        while True:
            result = await self._request("GET", f"/nsi/api/search/networkConstructs?limit={limit}&offset={offset}")
            devices = result.get("data", [])
            all_devices.extend(devices)
            
            total = result.get("meta", {}).get("total", 0)
            if offset + limit >= total or not devices:
                break
            offset += limit
        
        return all_devices
    
    async def get_alarms(self, status: str = None) -> List[Dict]:
        """Get alarms from MCP."""
        filter_param = f"&filter=status=={status}" if status else ""
        result = await self._request("GET", f"/nsi/api/search/alarms?limit=500{filter_param}")
        return result.get("data", [])
