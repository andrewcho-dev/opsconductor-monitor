"""
Cradlepoint Alert Normalizer

Transforms Cradlepoint NCOS data to standard NormalizedAlert format.
Uses database mappings for severity and category via BaseNormalizer.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from backend.connectors.base import BaseNormalizer
from backend.core.models import NormalizedAlert, Severity, Category
from backend.utils.ip_utils import validate_device_ip

logger = logging.getLogger(__name__)


class CradlepointNormalizer(BaseNormalizer):
    """
    Database-driven normalizer for Cradlepoint router alerts.
    
    Extends BaseNormalizer for standard mapping methods.
    """
    
    connector_type = "cradlepoint"
    default_category = Category.WIRELESS
    
    # Event type to title mapping (connector-specific)
    EVENT_TITLES = {
        "signal_critical": "Cellular Signal Critical",
        "signal_low": "Cellular Signal Low",
        "signal_normal": "Cellular Signal Normal",
        "sinr_critical": "SINR Critical",
        "sinr_low": "SINR Low",
        "connection_lost": "Cellular Connection Lost",
        "connection_restored": "Cellular Connection Restored",
        "connection_error": "Cellular Connection Error",
        "connection_connecting": "Cellular Connecting",
        "wan_failover": "WAN Failover Active",
        "wan_restored": "WAN Primary Restored",
        "wan_primary_down": "Primary WAN Down",
        "wan_all_down": "All WAN Connections Down",
        "device_offline": "Router Offline",
        "device_online": "Router Online",
        "device_rebooting": "Router Rebooting",
        "device_uptime_reset": "Router Uptime Reset",
        "temperature_critical": "Temperature Critical",
        "temperature_high": "Temperature High",
        "temperature_normal": "Temperature Normal",
        "gps_fix_lost": "GPS Fix Lost",
        "gps_fix_acquired": "GPS Fix Acquired",
        "gps_antenna_fault": "GPS Antenna Fault",
        "ethernet_link_down": "Ethernet Link Down",
        "ethernet_link_up": "Ethernet Link Up",
        "carrier_change": "Carrier Changed",
        "sim_error": "SIM Card Error",
        "sim_not_present": "SIM Card Not Present",
        "modem_error": "Modem Error",
        "modem_reset": "Modem Reset",
        "modem_firmware_mismatch": "Modem Firmware Mismatch",
    }
    
    def normalize(self, raw_data: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """
        Transform Cradlepoint data to NormalizedAlert.
        
        Returns None if the event type is disabled in mappings or no valid IP.
        """
        device_ip = raw_data.get("device_ip", "")
        device_name = raw_data.get("device_name", "")
        event_type = raw_data.get("alert_type", "unknown")
        metrics = raw_data.get("metrics", {})
        timestamp = raw_data.get("timestamp")
        
        # Check if event type is enabled
        if not self.is_event_enabled(event_type):
            logger.debug(f"Skipping disabled Cradlepoint event type: {event_type}")
            return None
        
        # Validate device IP
        try:
            validated_ip = validate_device_ip(device_ip, device_name)
        except ValueError as e:
            logger.warning(f"Skipping Cradlepoint alert - no valid device_ip: {e}")
            return None
        
        # Get severity and category from database mappings
        severity = self._get_severity(event_type)
        category = self._get_category(event_type)
        
        # Build title
        base_title = self.EVENT_TITLES.get(event_type, f"Cradlepoint {event_type.replace('_', ' ').title()}")
        title = f"{base_title} - {device_name}" if device_name else base_title
        message = self._build_message(event_type, metrics, device_name, validated_ip)
        occurred_at = self._parse_timestamp(timestamp)
        
        # Use standard clear event detection from BaseNormalizer
        is_clear = self.is_clear_event(event_type, raw_data)
        
        # source_alert_id must be STABLE for deduplication - no timestamps!
        source_alert_id = f"{validated_ip}:{event_type}"
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=source_alert_id,
            device_ip=validated_ip,
            device_name=device_name or None,
            severity=severity,
            category=category,
            alert_type=f"cradlepoint_{event_type}",
            title=title,
            message=message,
            occurred_at=occurred_at,
            is_clear=is_clear,
            raw_data=raw_data,
        )
    
    def _build_message(self, alert_type: str, metrics: Dict, device_name: str = "", device_ip: str = "") -> str:
        lines = []
        
        # Always include device info
        if device_name:
            lines.append(f"Device: {device_name}")
        elif device_ip:
            lines.append(f"Device: {device_ip}")
        
        # Alert type
        if alert_type:
            lines.append(f"Alert: {alert_type.replace('_', ' ')}")
        
        if metrics.get("rssi") is not None:
            lines.append(f"RSSI: {metrics['rssi']} dBm")
        if metrics.get("rsrp") is not None:
            lines.append(f"RSRP: {metrics['rsrp']} dBm")
        if metrics.get("rsrq") is not None:
            lines.append(f"RSRQ: {metrics['rsrq']} dB")
        if metrics.get("sinr") is not None:
            lines.append(f"SINR: {metrics['sinr']} dB")
        if metrics.get("carrier"):
            lines.append(f"Carrier: {metrics['carrier']}")
        if metrics.get("connection_state"):
            lines.append(f"State: {metrics['connection_state']}")
        
        return " | ".join(lines) if lines else f"Cradlepoint {alert_type} on {device_ip}"
    
    def _parse_timestamp(self, timestamp: Any) -> datetime:
        if not timestamp:
            return datetime.utcnow()
        if isinstance(timestamp, datetime):
            return timestamp
        try:
            return datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except ValueError:
            return datetime.utcnow()
