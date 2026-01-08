"""
Cradlepoint Alert Normalizer

Transforms Cradlepoint NCOS data to standard NormalizedAlert format.
Uses database mappings for severity and category - NO HARDCODED VALUES.
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

from backend.core.models import NormalizedAlert, Severity, Category
from backend.utils.ip_utils import validate_device_ip
from backend.utils.db import db_query

logger = logging.getLogger(__name__)


class CradlepointNormalizer:
    """
    Database-driven normalizer for Cradlepoint router alerts.
    
    All mappings come from severity_mappings and category_mappings tables.
    """
    
    # Clear event types (events that resolve previous alerts)
    CLEAR_EVENTS = {
        "signal_normal", "connection_restored", "wan_restored", 
        "device_online", "temperature_normal", "gps_fix_acquired",
        "ethernet_link_up"
    }
    
    # Event type to title mapping
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
    
    def __init__(self):
        self._severity_cache: Dict[str, Dict] = {}
        self._category_cache: Dict[str, Dict] = {}
        self._cache_loaded = False
    
    def _load_mappings(self):
        """Load mappings from database."""
        if self._cache_loaded:
            return
        
        try:
            # Load severity mappings
            severity_rows = db_query(
                "SELECT source_value, target_severity, enabled, description FROM severity_mappings WHERE connector_type = %s",
                ("cradlepoint",)
            )
            for row in severity_rows:
                self._severity_cache[row["source_value"]] = {
                    "severity": row["target_severity"],
                    "enabled": row["enabled"],
                    "description": row.get("description", "")
                }
            
            # Load category mappings
            category_rows = db_query(
                "SELECT source_value, target_category, enabled, description FROM category_mappings WHERE connector_type = %s",
                ("cradlepoint",)
            )
            for row in category_rows:
                self._category_cache[row["source_value"]] = {
                    "category": row["target_category"],
                    "enabled": row["enabled"],
                    "description": row.get("description", "")
                }
            
            self._cache_loaded = True
            logger.info(f"Loaded {len(self._severity_cache)} severity and {len(self._category_cache)} category mappings for cradlepoint")
            
        except Exception as e:
            logger.error(f"Failed to load cradlepoint mappings: {e}")
            self._cache_loaded = True  # Don't retry on every call
    
    def is_event_enabled(self, event_type: str) -> bool:
        """Check if this event type is enabled in mappings."""
        self._load_mappings()
        
        severity_mapping = self._severity_cache.get(event_type)
        if severity_mapping and not severity_mapping.get("enabled", True):
            return False
        
        category_mapping = self._category_cache.get(event_type)
        if category_mapping and not category_mapping.get("enabled", True):
            return False
        
        return True
    
    def _get_severity(self, event_type: str) -> Severity:
        """Get severity from database mapping."""
        self._load_mappings()
        
        mapping = self._severity_cache.get(event_type)
        if mapping:
            try:
                return Severity(mapping["severity"])
            except ValueError:
                pass
        
        # Default fallback
        return Severity.WARNING
    
    def _get_category(self, event_type: str) -> Category:
        """Get category from database mapping."""
        self._load_mappings()
        
        mapping = self._category_cache.get(event_type)
        if mapping:
            try:
                return Category(mapping["category"])
            except ValueError:
                pass
        
        # Default fallback
        return Category.WIRELESS
    
    @property
    def source_system(self) -> str:
        return "cradlepoint"
    
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
        message = self._build_message(event_type, metrics)
        occurred_at = self._parse_timestamp(timestamp)
        
        # Is this a clear event?
        is_clear = event_type in self.CLEAR_EVENTS
        
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
    
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        event_type = raw_data.get("alert_type", "")
        return self._get_severity(event_type)
    
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        event_type = raw_data.get("alert_type", "")
        return self._get_category(event_type)
    
    def get_fingerprint(self, raw_data: Dict[str, Any]) -> str:
        device_ip = raw_data.get("device_ip", "")
        event_type = raw_data.get("alert_type", "")
        return hashlib.sha256(f"cradlepoint:{device_ip}:{event_type}".encode()).hexdigest()
    
    def _build_message(self, alert_type: str, metrics: Dict) -> str:
        lines = []
        
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
        
        return "\n".join(lines)
    
    def _parse_timestamp(self, timestamp: Any) -> datetime:
        if not timestamp:
            return datetime.utcnow()
        if isinstance(timestamp, datetime):
            return timestamp
        try:
            return datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except ValueError:
            return datetime.utcnow()
