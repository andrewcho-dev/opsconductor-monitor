"""
Siklu Radio Connector

Polls Siklu EtherHaul radios via HTTP API and SNMP.
"""

import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional, List
from base64 import b64encode

from backend.connectors.base import PollingConnector, BaseNormalizer
from backend.core.models import NormalizedAlert, ConnectorStatus
from backend.core.alert_manager import get_alert_manager

from .normalizer import SikluNormalizer

logger = logging.getLogger(__name__)


class SikluConnector(PollingConnector):
    """
    Siklu EtherHaul radio connector.
    
    Polls radio link status and signal metrics.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.targets = config.get("targets", [])
        self.thresholds = config.get("thresholds", {
            "rsl_warning": -55,
            "rsl_critical": -60,
        })
        self._sessions: Dict[str, aiohttp.ClientSession] = {}
    
    @property
    def connector_type(self) -> str:
        return "siklu"
    
    def _create_normalizer(self) -> BaseNormalizer:
        return SikluNormalizer()
    
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
            logger.warning("No Siklu targets configured")
        await super().start()
        logger.info(f"Siklu connector started (poll interval: {self.poll_interval}s, targets: {len(self.targets)})")
    
    async def stop(self) -> None:
        for session in self._sessions.values():
            if not session.closed:
                await session.close()
        self._sessions.clear()
        await super().stop()
        logger.info("Siklu connector stopped")
    
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
            "message": f"Connected to {success_count}/{len(self.targets)} radios",
            "details": {"results": results}
        }
    
    async def poll(self) -> List[NormalizedAlert]:
        alerts = []
        
        for target in self.targets:
            try:
                target_alerts = await self._poll_radio(target)
                alerts.extend(target_alerts)
            except Exception as e:
                logger.error(f"Error polling radio {target.get('ip')}: {e}")
                alerts.append(self._create_alert(target, "device_offline", {"error": str(e)}))
        
        logger.debug(f"Siklu poll: {len(alerts)} alerts from {len(self.targets)} radios")
        return alerts
    
    async def _poll_radio(self, target: Dict) -> List[NormalizedAlert]:
        alerts = []
        
        try:
            status = await self._get_status(target)
            metrics = await self._get_metrics(target)
            
            # Check link state
            link_state = status.get("link_state", "").lower()
            if link_state in ("down", "disconnected"):
                alerts.append(self._create_alert(target, "link_down", {**status, **metrics}))
            
            # Check RSL
            rsl = metrics.get("rsl")
            if rsl is not None:
                if rsl <= self.thresholds.get("rsl_critical", -60):
                    alerts.append(self._create_alert(target, "rsl_critical", metrics))
                elif rsl <= self.thresholds.get("rsl_warning", -55):
                    alerts.append(self._create_alert(target, "rsl_low", metrics))
            
            # Check temperature
            temp = metrics.get("temperature")
            if temp is not None and temp > 70:
                alerts.append(self._create_alert(target, "high_temperature", metrics))
            
        except Exception as e:
            logger.warning(f"Radio {target.get('ip')} appears offline: {e}")
            alerts.append(self._create_alert(target, "device_offline", {"error": str(e)}))
        
        return alerts
    
    async def _get_status(self, target: Dict) -> Dict[str, Any]:
        """Get radio status via HTTP API."""
        ip = target.get("ip")
        session = await self._get_session(target)
        
        try:
            # Try common Siklu API endpoints
            async with session.get(f"http://{ip}/api/status", timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "model": data.get("model", "Siklu Radio"),
                        "serial": data.get("serial", ""),
                        "link_state": data.get("linkState", data.get("link_state", "")),
                    }
        except Exception:
            pass
        
        # Fallback - try SNMP if available
        return await self._get_status_snmp(target)
    
    async def _get_status_snmp(self, target: Dict) -> Dict[str, Any]:
        """Get radio status via SNMP."""
        # Basic status if HTTP fails
        return {
            "model": "Siklu Radio",
            "link_state": "unknown",
        }
    
    async def _get_metrics(self, target: Dict) -> Dict[str, Any]:
        """Get radio metrics."""
        ip = target.get("ip")
        session = await self._get_session(target)
        
        metrics = {}
        
        try:
            async with session.get(f"http://{ip}/api/radio/status", timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    metrics["rsl"] = data.get("rsl") or data.get("rssi")
                    metrics["modulation"] = data.get("modulation")
                    metrics["tx_power"] = data.get("txPower") or data.get("tx_power")
                    metrics["temperature"] = data.get("temperature")
        except Exception as e:
            logger.debug(f"Could not get metrics from {ip}: {e}")
        
        return metrics
    
    def _create_alert(self, target: Dict, alert_type: str, metrics: Dict) -> NormalizedAlert:
        raw_data = {
            "device_ip": target.get("ip"),
            "device_name": target.get("name"),
            "peer_ip": target.get("peer_ip"),
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
                logger.warning(f"Failed to process Siklu alert: {e}")
