"""
Cradlepoint Connector

Polls Cradlepoint routers via NCOS API for status and signal metrics.
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

from .normalizer import CradlepointNormalizer

logger = logging.getLogger(__name__)


class CradlepointConnector(PollingConnector):
    """
    Cradlepoint router connector using NCOS API.
    
    Polls router status and cellular signal metrics.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.targets = config.get("targets", [])
        self.thresholds = config.get("thresholds", {
            "rssi_warning": -85,
            "rssi_critical": -95,
            "rsrp_warning": -100,
            "rsrp_critical": -110,
            "sinr_warning": 5,
            "sinr_critical": 0,
        })
        self._sessions: Dict[str, aiohttp.ClientSession] = {}
    
    @property
    def connector_type(self) -> str:
        return "cradlepoint"
    
    def _create_normalizer(self) -> BaseNormalizer:
        return CradlepointNormalizer()
    
    async def _get_session(self, target: Dict) -> aiohttp.ClientSession:
        ip = target.get("ip")
        if ip not in self._sessions or self._sessions[ip].closed:
            auth = b64encode(f"{target.get('username', 'admin')}:{target.get('password', '')}".encode()).decode()
            self._sessions[ip] = aiohttp.ClientSession(
                headers={"Authorization": f"Basic {auth}"},
                connector=aiohttp.TCPConnector(ssl=False)
            )
        return self._sessions[ip]
    
    async def start(self) -> None:
        if not self.targets:
            logger.warning("No Cradlepoint targets configured")
        await super().start()
        logger.info(f"Cradlepoint connector started (poll interval: {self.poll_interval}s, targets: {len(self.targets)})")
    
    async def stop(self) -> None:
        for session in self._sessions.values():
            if not session.closed:
                await session.close()
        self._sessions.clear()
        await super().stop()
        logger.info("Cradlepoint connector stopped")
    
    async def test_connection(self) -> Dict[str, Any]:
        if not self.targets:
            return {"success": False, "message": "No targets configured", "details": None}
        
        results = []
        for target in self.targets:
            try:
                status = await self._get_status(target)
                results.append({
                    "ip": target.get("ip"),
                    "name": target.get("name"),
                    "success": True,
                    "model": status.get("model"),
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
            "message": f"Connected to {success_count}/{len(self.targets)} routers",
            "details": {"results": results}
        }
    
    async def poll(self) -> List[NormalizedAlert]:
        alerts = []
        
        for target in self.targets:
            try:
                target_alerts = await self._poll_router(target)
                alerts.extend(target_alerts)
            except Exception as e:
                logger.error(f"Error polling router {target.get('ip')}: {e}")
                alerts.append(self._create_alert(target, "device_offline", {"error": str(e)}))
        
        logger.debug(f"Cradlepoint poll: {len(alerts)} alerts from {len(self.targets)} routers")
        return alerts
    
    async def _poll_router(self, target: Dict) -> List[NormalizedAlert]:
        alerts = []
        
        try:
            # Get WAN/modem status
            diagnostics = await self._get_diagnostics(target)
            
            if diagnostics:
                # Check signal levels
                rssi = diagnostics.get("rssi")
                rsrp = diagnostics.get("rsrp")
                sinr = diagnostics.get("sinr")
                
                # RSSI thresholds
                if rssi is not None:
                    if rssi <= self.thresholds.get("rssi_critical", -95):
                        alerts.append(self._create_alert(target, "signal_critical", diagnostics))
                    elif rssi <= self.thresholds.get("rssi_warning", -85):
                        alerts.append(self._create_alert(target, "signal_low", diagnostics))
                
                # RSRP thresholds (prefer over RSSI for LTE)
                elif rsrp is not None:
                    if rsrp <= self.thresholds.get("rsrp_critical", -110):
                        alerts.append(self._create_alert(target, "signal_critical", diagnostics))
                    elif rsrp <= self.thresholds.get("rsrp_warning", -100):
                        alerts.append(self._create_alert(target, "signal_low", diagnostics))
                
                # Connection state
                connection_state = diagnostics.get("connection_state", "").lower()
                if connection_state in ("disconnected", "error", "none"):
                    alerts.append(self._create_alert(target, "connection_lost", diagnostics))
            
        except Exception as e:
            logger.warning(f"Router {target.get('ip')} appears offline: {e}")
            alerts.append(self._create_alert(target, "device_offline", {"error": str(e)}))
        
        return alerts
    
    async def _get_status(self, target: Dict) -> Dict[str, Any]:
        ip = target.get("ip")
        session = await self._get_session(target)
        
        async with session.get(f"http://{ip}/api/status/system/", timeout=10) as response:
            response.raise_for_status()
            data = await response.json()
            return {
                "model": data.get("product_name", "Cradlepoint"),
                "serial": data.get("serial_number", ""),
                "firmware": data.get("fw_info", {}).get("major_version", ""),
            }
    
    async def _get_diagnostics(self, target: Dict) -> Dict[str, Any]:
        ip = target.get("ip")
        session = await self._get_session(target)
        
        diagnostics = {}
        
        # Get modem diagnostics
        try:
            async with session.get(f"http://{ip}/api/status/wan/devices/", timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    # Find first modem
                    for key, device in data.items():
                        if "mdm" in key.lower():
                            diagnostics["modem_id"] = key
                            diagnostics["connection_state"] = device.get("status", {}).get("connection_state", "")
                            
                            # Get signal info
                            info = device.get("diagnostics", {}).get("MODEMINFO", {})
                            diagnostics["rssi"] = info.get("DBM")
                            diagnostics["rsrp"] = info.get("RSRP")
                            diagnostics["rsrq"] = info.get("RSRQ")
                            diagnostics["sinr"] = info.get("SINR")
                            diagnostics["carrier"] = info.get("HOMECARRID")
                            break
        except Exception as e:
            logger.debug(f"Could not get modem diagnostics: {e}")
        
        return diagnostics
    
    def _create_alert(self, target: Dict, alert_type: str, metrics: Dict) -> NormalizedAlert:
        raw_data = {
            "device_ip": target.get("ip"),
            "device_name": target.get("name"),
            "alert_type": alert_type,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return self.normalizer.normalize(raw_data)
    
    async def _process_alerts(self, alerts: List[NormalizedAlert]) -> None:
        alert_manager = get_alert_manager()
        for normalized in alerts:
            try:
                await alert_manager.process_alert(normalized)
            except Exception as e:
                logger.warning(f"Failed to process Cradlepoint alert: {e}")


from connectors.registry import register_connector
register_connector("cradlepoint", CradlepointConnector)
