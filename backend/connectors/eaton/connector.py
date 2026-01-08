"""
Eaton UPS Connector

Polls Eaton UPS devices via SNMP for status and alarms.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List

from backend.connectors.base import PollingConnector, BaseNormalizer
from backend.core.models import NormalizedAlert, ConnectorStatus
from backend.core.alert_manager import get_alert_manager

from .normalizer import EatonNormalizer

logger = logging.getLogger(__name__)


# XUPS-MIB OIDs
class EatonOIDs:
    """Eaton UPS SNMP OIDs (XUPS-MIB)."""
    # Identity
    IDENT_MODEL = "1.3.6.1.4.1.534.1.1.2.0"
    IDENT_SERIAL = "1.3.6.1.4.1.534.1.1.3.0"
    
    # Battery
    BATTERY_STATUS = "1.3.6.1.4.1.534.1.2.5.0"
    BATTERY_CAPACITY = "1.3.6.1.4.1.534.1.2.4.0"
    BATTERY_VOLTAGE = "1.3.6.1.4.1.534.1.2.2.0"
    BATTERY_RUNTIME = "1.3.6.1.4.1.534.1.2.1.0"  # Seconds remaining
    
    # Input
    INPUT_VOLTAGE = "1.3.6.1.4.1.534.1.3.4.1.2.1"
    INPUT_FREQUENCY = "1.3.6.1.4.1.534.1.3.1.0"
    
    # Output
    OUTPUT_SOURCE = "1.3.6.1.4.1.534.1.4.5.0"
    OUTPUT_VOLTAGE = "1.3.6.1.4.1.534.1.4.4.1.2.1"
    OUTPUT_LOAD = "1.3.6.1.4.1.534.1.4.1.0"
    OUTPUT_FREQUENCY = "1.3.6.1.4.1.534.1.4.2.0"
    
    # Environment
    ENVIRONMENT_TEMP = "1.3.6.1.4.1.534.1.6.1.0"
    
    # Alarms
    ALARMS_PRESENT = "1.3.6.1.4.1.534.1.7.1.0"


class EatonConnector(PollingConnector):
    """
    Eaton UPS connector using SNMP polling.
    
    Monitors UPS status and generates alerts based on thresholds.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.targets = config.get("targets", [])
        self.thresholds = config.get("thresholds", {
            "battery_capacity_low": 30,
            "battery_capacity_critical": 10,
            "load_warning": 80,
            "load_critical": 95,
            "temp_high": 40,
        })
        self._snmp_available = False
        self._check_snmp()
    
    def _check_snmp(self):
        """Check if pysnmp is available."""
        try:
            import pysnmp
            self._snmp_available = True
        except ImportError:
            logger.warning("pysnmp not available - Eaton connector will be limited")
            self._snmp_available = False
    
    @property
    def connector_type(self) -> str:
        return "eaton"
    
    def _create_normalizer(self) -> BaseNormalizer:
        return EatonNormalizer()
    
    async def start(self) -> None:
        """Start the connector."""
        if not self.targets:
            logger.warning("No Eaton UPS targets configured")
        
        await super().start()
        logger.info(f"Eaton connector started (poll interval: {self.poll_interval}s, targets: {len(self.targets)})")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connectivity to configured UPS targets."""
        if not self.targets:
            return {
                "success": False,
                "message": "No targets configured",
                "details": None
            }
        
        results = []
        for target in self.targets:
            try:
                status = await self._poll_ups(target)
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
            "message": f"Connected to {success_count}/{len(self.targets)} UPS devices",
            "details": {"results": results}
        }
    
    async def poll(self) -> List[NormalizedAlert]:
        """Poll all UPS targets for alerts."""
        alerts = []
        
        for target in self.targets:
            try:
                target_alerts = await self._poll_ups_alerts(target)
                alerts.extend(target_alerts)
            except Exception as e:
                logger.error(f"Error polling UPS {target.get('ip')}: {e}")
                
                # Generate communication lost alert
                alerts.append(self._create_alert(
                    target,
                    "communication_lost",
                    {"error": str(e)}
                ))
        
        logger.debug(f"Eaton poll: {len(alerts)} alerts from {len(self.targets)} targets")
        return alerts
    
    async def _poll_ups_alerts(self, target: Dict) -> List[NormalizedAlert]:
        """Poll single UPS and generate alerts based on status."""
        alerts = []
        
        try:
            status = await self._poll_ups(target)
            metrics = status.get("metrics", {})
            
            # Check output source
            output_source = metrics.get("output_source")
            if output_source == 5:  # Battery
                alerts.append(self._create_alert(target, "on_battery", metrics))
            elif output_source == 4:  # Bypass
                alerts.append(self._create_alert(target, "on_bypass", metrics))
            
            # Check battery capacity
            capacity = metrics.get("battery_capacity")
            if capacity is not None:
                if capacity <= self.thresholds.get("battery_capacity_critical", 10):
                    alerts.append(self._create_alert(target, "low_battery", metrics))
                elif capacity <= self.thresholds.get("battery_capacity_low", 30):
                    alerts.append(self._create_alert(target, "battery_capacity_low", metrics))
            
            # Check load
            load = metrics.get("load_percent")
            if load is not None:
                if load >= self.thresholds.get("load_critical", 95):
                    alerts.append(self._create_alert(target, "output_overload", metrics))
                elif load >= self.thresholds.get("load_warning", 80):
                    alerts.append(self._create_alert(target, "load_high", metrics))
            
            # Check temperature
            temp = metrics.get("temperature")
            if temp is not None:
                if temp >= self.thresholds.get("temp_high", 40):
                    alerts.append(self._create_alert(target, "temperature_high", metrics))
            
            # Check battery status
            battery_status = metrics.get("battery_status")
            if battery_status == 3:  # Low
                if not any(a.raw_data.get("alarm_type") == "low_battery" for a in alerts):
                    alerts.append(self._create_alert(target, "low_battery", metrics))
            elif battery_status == 4:  # Depleted
                alerts.append(self._create_alert(target, "shutdown_imminent", metrics))
            
        except Exception as e:
            logger.error(f"Error checking UPS {target.get('ip')}: {e}")
        
        return alerts
    
    async def _poll_ups(self, target: Dict) -> Dict[str, Any]:
        """Poll UPS via SNMP and return status."""
        ip = target.get("ip")
        community = target.get("community", "public")
        
        if not self._snmp_available:
            # Return mock data if SNMP not available
            return {
                "ip": ip,
                "name": target.get("name"),
                "model": "Unknown (pysnmp not installed)",
                "metrics": {}
            }
        
        # Use pysnmp for actual polling
        metrics = await self._snmp_get_metrics(ip, community)
        
        return {
            "ip": ip,
            "name": target.get("name"),
            "model": metrics.get("model", "Eaton UPS"),
            "metrics": metrics
        }
    
    async def _snmp_get_metrics(self, ip: str, community: str) -> Dict[str, Any]:
        """Get UPS metrics via SNMP."""
        from pysnmp.hlapi.asyncio import (
            getCmd, SnmpEngine, CommunityData, UdpTransportTarget,
            ContextData, ObjectType, ObjectIdentity
        )
        
        metrics = {}
        
        oids = [
            (EatonOIDs.BATTERY_CAPACITY, "battery_capacity"),
            (EatonOIDs.BATTERY_STATUS, "battery_status"),
            (EatonOIDs.BATTERY_RUNTIME, "runtime_remaining"),
            (EatonOIDs.OUTPUT_SOURCE, "output_source"),
            (EatonOIDs.OUTPUT_LOAD, "load_percent"),
            (EatonOIDs.ENVIRONMENT_TEMP, "temperature"),
            (EatonOIDs.IDENT_MODEL, "model"),
        ]
        
        for oid, key in oids:
            try:
                errorIndication, errorStatus, errorIndex, varBinds = await getCmd(
                    SnmpEngine(),
                    CommunityData(community),
                    UdpTransportTarget((ip, 161), timeout=5, retries=1),
                    ContextData(),
                    ObjectType(ObjectIdentity(oid))
                )
                
                if not errorIndication and not errorStatus:
                    for varBind in varBinds:
                        value = varBind[1]
                        if key == "model":
                            metrics[key] = str(value)
                        elif key == "runtime_remaining":
                            # Convert seconds to minutes
                            metrics[key] = int(value) // 60 if value else None
                        else:
                            metrics[key] = int(value) if value else None
                            
            except Exception as e:
                logger.debug(f"Failed to get {key} from {ip}: {e}")
        
        return metrics
    
    def _create_alert(self, target: Dict, alarm_type: str, metrics: Dict) -> NormalizedAlert:
        """Create normalized alert from UPS data."""
        raw_data = {
            "device_ip": target.get("ip"),
            "device_name": target.get("name"),
            "alarm_type": alarm_type,
            "metrics": metrics,
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
                logger.warning(f"Failed to process Eaton alert: {e}")
