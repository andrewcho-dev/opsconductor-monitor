"""
Cradlepoint Connector

Polls Cradlepoint routers via NCOS API for status and signal metrics.
"""

import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from base64 import b64encode

from backend.connectors.base import PollingConnector, BaseNormalizer
from backend.core.models import NormalizedAlert, ConnectorStatus
from backend.core.alert_manager import get_alert_manager

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
                # Filter out None alerts (disabled event types)
                alerts.extend([a for a in target_alerts if a is not None])
            except Exception as e:
                logger.error(f"Error polling router {target.get('ip')}: {e}")
                alert = self._create_alert(target, "device_offline", {"error": str(e)})
                if alert:
                    alerts.append(alert)
        
        logger.debug(f"Cradlepoint poll: {len(alerts)} alerts from {len(self.targets)} routers")
        return alerts
    
    def _safe_float(self, value) -> Optional[float]:
        """Safely convert value to float for comparison."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    async def _poll_router(self, target: Dict) -> List[Optional[NormalizedAlert]]:
        alerts: List[Optional[NormalizedAlert]] = []
        
        try:
            # Get WAN/modem status
            diagnostics = await self._get_diagnostics(target)
            
            if diagnostics:
                # Check signal levels - convert to float for comparison
                rssi = self._safe_float(diagnostics.get("rssi"))
                rsrp = self._safe_float(diagnostics.get("rsrp"))
                sinr = self._safe_float(diagnostics.get("sinr"))
                
                # RSRP thresholds (prefer for LTE)
                if rsrp is not None:
                    if rsrp <= self.thresholds.get("rsrp_critical", -110):
                        alerts.append(self._create_alert(target, "signal_critical", diagnostics))
                    elif rsrp <= self.thresholds.get("rsrp_warning", -100):
                        alerts.append(self._create_alert(target, "signal_low", diagnostics))
                # RSSI thresholds (fallback)
                elif rssi is not None:
                    if rssi <= self.thresholds.get("rssi_critical", -95):
                        alerts.append(self._create_alert(target, "signal_critical", diagnostics))
                    elif rssi <= self.thresholds.get("rssi_warning", -85):
                        alerts.append(self._create_alert(target, "signal_low", diagnostics))
                
                # SINR thresholds
                if sinr is not None:
                    if sinr <= self.thresholds.get("sinr_critical", 0):
                        alerts.append(self._create_alert(target, "sinr_critical", diagnostics))
                    elif sinr <= self.thresholds.get("sinr_warning", 5):
                        alerts.append(self._create_alert(target, "sinr_low", diagnostics))
                
                # Connection state - only alert if NO modem is connected
                # (don't alert on disconnected secondary/backup modems)
                connection_state = diagnostics.get("connection_state", "").lower()
                has_connected_modem = diagnostics.get("has_connected_modem", False)
                
                if connection_state in ("disconnected", "error", "none") and not has_connected_modem:
                    # Only alert if there's no connected modem at all
                    alerts.append(self._create_alert(target, "connection_lost", diagnostics))
                elif connection_state == "connecting":
                    alerts.append(self._create_alert(target, "connection_connecting", diagnostics))
            
            # Get system status (temperature, uptime)
            system_status = await self._get_system_status(target)
            if system_status:
                temp = self._safe_float(system_status.get("temperature"))
                if temp is not None:
                    if temp >= self.thresholds.get("temp_critical", 70):
                        alerts.append(self._create_alert(target, "temperature_critical", system_status))
                    elif temp >= self.thresholds.get("temp_warning", 60):
                        alerts.append(self._create_alert(target, "temperature_high", system_status))
            
            # Get GPS status
            gps_status = await self._get_gps_status(target)
            if gps_status:
                gps_fix = gps_status.get("fix_type", "").lower()
                if gps_fix in ("none", "no fix", ""):
                    alerts.append(self._create_alert(target, "gps_fix_lost", gps_status))
            
            # Get ethernet port status (only if enabled in config)
            if self.config.get("monitor_ethernet", False):
                ethernet_status = await self._get_ethernet_status(target)
                for port_info in ethernet_status:
                    port_num = port_info.get("port")
                    link_state = port_info.get("link", "").lower()
                    # Alert on ports that are down
                    if link_state == "down":
                        alerts.append(self._create_alert(target, "ethernet_link_down", {
                            "port": port_num,
                            "link_state": link_state,
                            "speed": port_info.get("link_speed", "Unknown")
                        }))
            
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
                    resp_data = await response.json()
                    # NCOS API wraps response in {"success": true, "data": {...}}
                    data = resp_data.get("data", resp_data)
                    
                    # Find the CONNECTED modem (primary active connection)
                    # IBR routers can have multiple modems - we want the active one
                    connected_modem = None
                    any_modem = None
                    
                    for key, device in data.items():
                        if "mdm" in key.lower() and isinstance(device, dict):
                            status = device.get("status", {})
                            conn_state = status.get("connection_state", "")
                            
                            # Track any modem we find
                            if any_modem is None:
                                any_modem = (key, device, conn_state)
                            
                            # Prefer the connected modem
                            if conn_state == "connected":
                                connected_modem = (key, device, conn_state)
                                break
                    
                    # Track if ANY modem is connected (for connection_lost alerting)
                    diagnostics["has_connected_modem"] = connected_modem is not None
                    
                    # Use connected modem if found, otherwise use any modem for signal data
                    modem_info = connected_modem or any_modem
                    
                    if modem_info:
                        key, device, conn_state = modem_info
                        diagnostics["modem_id"] = key
                        diagnostics["connection_state"] = conn_state
                        
                        # Get signal info from diagnostics
                        # Signal data can be in diagnostics directly OR in diagnostics.MODEMINFO
                        diag = device.get("diagnostics", {})
                        info = diag.get("MODEMINFO", diag)  # Fall back to diag itself
                        
                        diagnostics["rssi"] = info.get("DBM")
                        diagnostics["rsrp"] = info.get("RSRP")
                        diagnostics["rsrq"] = info.get("RSRQ")
                        diagnostics["sinr"] = info.get("SINR")
                        diagnostics["carrier"] = info.get("HOMECARRID") or info.get("CARRID")
                        diagnostics["modem_temp"] = info.get("MODEMTEMP")
                        
        except Exception as e:
            logger.debug(f"Could not get modem diagnostics: {e}")
        
        return diagnostics
    
    async def _get_system_status(self, target: Dict) -> Dict[str, Any]:
        """Get system status including temperature and uptime."""
        ip = target.get("ip")
        session = await self._get_session(target)
        
        status = {}
        
        try:
            async with session.get(f"http://{ip}/api/status/system/", timeout=10) as response:
                if response.status == 200:
                    resp_data = await response.json()
                    # NCOS API wraps response in {"success": true, "data": {...}}
                    data = resp_data.get("data", resp_data)
                    status["uptime"] = data.get("uptime")
                    status["product_name"] = data.get("product_name")
                    status["serial_number"] = data.get("serial_number")
                    # Temperature may be in modem_temperature for IBR models
                    status["temperature"] = data.get("modem_temperature") or data.get("temperature") or data.get("cpu_temp")
        except Exception as e:
            logger.debug(f"Could not get system status: {e}")
        
        return status
    
    async def _get_gps_status(self, target: Dict) -> Dict[str, Any]:
        """Get GPS status including fix type and coordinates."""
        ip = target.get("ip")
        session = await self._get_session(target)
        
        gps = {}
        
        try:
            async with session.get(f"http://{ip}/api/status/gps/", timeout=10) as response:
                if response.status == 200:
                    resp_data = await response.json()
                    # NCOS API wraps response in {"success": true, "data": {...}}
                    data = resp_data.get("data", resp_data)
                    fix = data.get("fix", {})
                    gps["fix_type"] = fix.get("type", "") or fix.get("lock_status", "")
                    gps["latitude"] = fix.get("latitude")
                    gps["longitude"] = fix.get("longitude")
                    gps["satellites"] = fix.get("satellites")
        except Exception as e:
            logger.debug(f"Could not get GPS status: {e}")
        
        return gps
    
    async def _get_ethernet_status(self, target: Dict) -> List[Dict[str, Any]]:
        """Get ethernet port status (link up/down, speed)."""
        ip = target.get("ip")
        session = await self._get_session(target)
        
        ports = []
        
        try:
            async with session.get(f"http://{ip}/api/status/ethernet/", timeout=10) as response:
                if response.status == 200:
                    resp_data = await response.json()
                    # NCOS API wraps response in {"success": true, "data": [...]}
                    data = resp_data.get("data", resp_data)
                    if isinstance(data, list):
                        ports = data
                    logger.debug(f"Got {len(ports)} ethernet ports from {ip}")
        except Exception as e:
            logger.debug(f"Could not get ethernet status: {e}")
        
        return ports
    
    def _create_alert(self, target: Dict, alert_type: str, metrics: Dict) -> Optional[NormalizedAlert]:
        """Create alert. Returns None if event type is disabled or no valid IP."""
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
