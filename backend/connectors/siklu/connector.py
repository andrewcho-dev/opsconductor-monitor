"""
Siklu Radio Connector

Polls Siklu EtherHaul radios via SNMP using enterprise OID 1.3.6.1.4.1.31926.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pysnmp.hlapi.asyncio import (
    get_cmd, SnmpEngine, CommunityData, UdpTransportTarget,
    ContextData, ObjectType, ObjectIdentity
)

from backend.connectors.base import PollingConnector, BaseNormalizer
from backend.core.models import NormalizedAlert, ConnectorStatus
from backend.core.alert_manager import get_alert_manager

from .normalizer import SikluNormalizer

logger = logging.getLogger(__name__)

# Siklu Enterprise OID: 1.3.6.1.4.1.31926
SIKLU_OID_BASE = "1.3.6.1.4.1.31926"
SIKLU_OIDS = {
    "temperature": f"{SIKLU_OID_BASE}.1.2.0",      # Temperature in Celsius
    "model": f"{SIKLU_OID_BASE}.1.30.0",           # Model name
    "sw_version": f"{SIKLU_OID_BASE}.1.6.0",       # Software version
    "link_state": f"{SIKLU_OID_BASE}.2.1.1.6.1",   # Link state (1=up, 2=down)
    "cinr": f"{SIKLU_OID_BASE}.2.1.1.18.1",        # CINR in dB
    "rssi": f"{SIKLU_OID_BASE}.2.1.1.19.1",        # RSSI/RSL in dBm
    "tx_power": f"{SIKLU_OID_BASE}.2.1.1.42.1",    # TX power in dBm
    "frequency": f"{SIKLU_OID_BASE}.2.1.1.4.1",    # TX frequency in MHz
}


class SikluConnector(PollingConnector):
    """
    Siklu EtherHaul radio connector.
    
    Polls radio link status and signal metrics via SNMP.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.targets = config.get("targets", [])
        self.thresholds = config.get("thresholds", {
            "rsl_warning": -55,
            "rsl_critical": -60,
        })
        self.snmp_community = config.get("snmp_community", "public")
        self._snmp_engine = SnmpEngine()
    
    @property
    def connector_type(self) -> str:
        return "siklu"
    
    def _create_normalizer(self) -> BaseNormalizer:
        return SikluNormalizer()
    
    async def start(self) -> None:
        if not self.targets:
            logger.warning("No Siklu targets configured")
        await super().start()
        logger.info(f"Siklu connector started (poll interval: {self.poll_interval}s, targets: {len(self.targets)})")
    
    async def stop(self) -> None:
        await super().stop()
        logger.info("Siklu connector stopped")
    
    async def _snmp_get(self, ip: str, oid: str) -> Any:
        """Get a single SNMP OID value."""
        try:
            errorIndication, errorStatus, errorIndex, varBinds = await get_cmd(
                self._snmp_engine,
                CommunityData(self.snmp_community),
                UdpTransportTarget((ip, 161), timeout=5, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
            
            if errorIndication or errorStatus:
                return None
            
            for varBind in varBinds:
                return varBind[1].prettyPrint()
        except Exception as e:
            logger.debug(f"SNMP get failed for {ip} OID {oid}: {e}")
        return None
    
    async def _get_snmp_data(self, ip: str) -> Dict[str, Any]:
        """Get all Siklu SNMP data for a radio."""
        data = {}
        
        for name, oid in SIKLU_OIDS.items():
            value = await self._snmp_get(ip, oid)
            if value is not None:
                # Convert numeric values
                if name in ("temperature", "cinr", "rssi", "tx_power", "frequency", "link_state"):
                    try:
                        data[name] = int(value)
                    except (ValueError, TypeError):
                        data[name] = value
                else:
                    data[name] = value
        
        return data
    
    async def test_connection(self) -> Dict[str, Any]:
        if not self.targets:
            return {"success": False, "message": "No targets configured", "details": None}
        
        results = []
        for target in self.targets:
            ip = target.get("ip")
            try:
                data = await self._get_snmp_data(ip)
                if data.get("model") or data.get("rssi") is not None:
                    results.append({
                        "ip": ip,
                        "name": target.get("name"),
                        "success": True,
                        "model": data.get("model", "Siklu Radio"),
                        "rssi": data.get("rssi"),
                        "temperature": data.get("temperature"),
                    })
                else:
                    results.append({
                        "ip": ip,
                        "name": target.get("name"),
                        "success": False,
                        "error": "No SNMP response",
                    })
            except Exception as e:
                results.append({
                    "ip": ip,
                    "name": target.get("name"),
                    "success": False,
                    "error": str(e),
                })
        
        success_count = sum(1 for r in results if r.get("success"))
        return {
            "success": success_count > 0,
            "message": f"Connected to {success_count}/{len(self.targets)} radios via SNMP",
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
                alert = self._create_alert(target, "device_offline", {"error": str(e)})
                if alert:
                    alerts.append(alert)
        
        logger.info(f"Siklu poll: {len(alerts)} alerts from {len(self.targets)} radios")
        return alerts
    
    async def _poll_radio(self, target: Dict) -> List[NormalizedAlert]:
        alerts = []
        ip = target.get("ip")
        
        try:
            data = await self._get_snmp_data(ip)
            
            if not data:
                alert = self._create_alert(target, "device_offline", {"error": "No SNMP response"})
                if alert:
                    alerts.append(alert)
                return alerts
            
            # Build metrics dict
            metrics = {
                "model": data.get("model", "Siklu Radio"),
                "rsl": data.get("rssi"),
                "cinr": data.get("cinr"),
                "tx_power": data.get("tx_power"),
                "temperature": data.get("temperature"),
                "frequency": data.get("frequency"),
            }
            
            # Check link state (1=up, 2=down)
            link_state = data.get("link_state")
            if link_state is not None and link_state != 1:
                alert = self._create_alert(target, "link_down", metrics)
                if alert:
                    alerts.append(alert)
            
            # Check RSL/RSSI
            rsl = data.get("rssi")
            if rsl is not None:
                if rsl <= self.thresholds.get("rsl_critical", -60):
                    alert = self._create_alert(target, "rsl_critical", metrics)
                    if alert:
                        alerts.append(alert)
                elif rsl <= self.thresholds.get("rsl_warning", -55):
                    alert = self._create_alert(target, "rsl_low", metrics)
                    if alert:
                        alerts.append(alert)
            
            # Check temperature
            temp = data.get("temperature")
            if temp is not None and temp > 70:
                alert = self._create_alert(target, "high_temperature", metrics)
                if alert:
                    alerts.append(alert)
            
            logger.debug(f"Siklu {ip}: RSL={rsl}dBm, CINR={data.get('cinr')}dB, Temp={temp}°C, Link={link_state}")
            
        except Exception as e:
            logger.warning(f"Radio {ip} appears offline: {e}")
            alert = self._create_alert(target, "device_offline", {"error": str(e)})
            if alert:
                alerts.append(alert)
        
        return alerts
    
    def _create_alert(self, target: Dict, alert_type: str, metrics: Dict) -> Optional[NormalizedAlert]:
        raw_data = {
            "device_ip": target.get("ip"),
            "device_name": target.get("name") or target.get("ip"),
            "peer_ip": target.get("peer_ip"),
            "alert_type": alert_type,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return self.normalizer.normalize(raw_data)
    
    async def _process_alerts(self, alerts: List[NormalizedAlert]) -> None:
        alert_manager = get_alert_manager()
        for normalized in alerts:
            if normalized is None:
                continue
            try:
                await alert_manager.process_alert(normalized)
            except Exception as e:
                logger.warning(f"Failed to process Siklu alert: {e}")
