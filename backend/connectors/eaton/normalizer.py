"""
Eaton UPS Alert Normalizer

Transforms Eaton UPS SNMP data to standard NormalizedAlert format.
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

from core.models import NormalizedAlert, Severity, Category

logger = logging.getLogger(__name__)


class EatonNormalizer:
    """
    Normalizer for Eaton UPS alerts.
    
    Based on XUPS-MIB (Eaton PowerMIB).
    """
    
    # Eaton alarm types and their severities
    ALARM_TYPES = {
        "on_battery": {
            "severity": Severity.WARNING,
            "title": "UPS On Battery",
            "description": "UPS is running on battery power"
        },
        "low_battery": {
            "severity": Severity.CRITICAL,
            "title": "UPS Low Battery",
            "description": "UPS battery is critically low"
        },
        "utility_restored": {
            "severity": Severity.CLEAR,
            "title": "UPS Utility Restored",
            "description": "AC power restored to UPS",
            "is_clear": True
        },
        "battery_bad": {
            "severity": Severity.MAJOR,
            "title": "UPS Battery Bad",
            "description": "UPS battery needs replacement"
        },
        "output_overload": {
            "severity": Severity.CRITICAL,
            "title": "UPS Output Overload",
            "description": "UPS load exceeds capacity"
        },
        "on_bypass": {
            "severity": Severity.WARNING,
            "title": "UPS On Bypass",
            "description": "UPS is operating in bypass mode"
        },
        "charger_failure": {
            "severity": Severity.MAJOR,
            "title": "UPS Charger Failure",
            "description": "UPS battery charger has failed"
        },
        "fan_failure": {
            "severity": Severity.MAJOR,
            "title": "UPS Fan Failure",
            "description": "UPS cooling fan has failed"
        },
        "temperature_high": {
            "severity": Severity.WARNING,
            "title": "UPS Temperature High",
            "description": "UPS temperature is above threshold"
        },
        "shutdown_imminent": {
            "severity": Severity.CRITICAL,
            "title": "UPS Shutdown Imminent",
            "description": "UPS will shut down soon due to low battery"
        },
        "communication_lost": {
            "severity": Severity.MAJOR,
            "title": "UPS Communication Lost",
            "description": "Lost SNMP communication with UPS"
        },
        "battery_capacity_low": {
            "severity": Severity.WARNING,
            "title": "UPS Battery Capacity Low",
            "description": "UPS battery capacity below threshold"
        },
        "load_high": {
            "severity": Severity.WARNING,
            "title": "UPS Load High",
            "description": "UPS load above warning threshold"
        },
    }
    
    # Eaton output source values
    OUTPUT_SOURCE = {
        1: "other",
        2: "none",
        3: "normal",      # AC power
        4: "bypass",
        5: "battery",
        6: "booster",
        7: "reducer",
    }
    
    # Battery status values
    BATTERY_STATUS = {
        1: "unknown",
        2: "batteryNormal",
        3: "batteryLow",
        4: "batteryDepleted",
    }
    
    @property
    def source_system(self) -> str:
        return "eaton"
    
    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedAlert:
        """
        Transform Eaton UPS data to NormalizedAlert.
        
        Expected raw_data format:
        {
            "device_ip": "10.1.2.1",
            "device_name": "UPS-Main",
            "alarm_type": "on_battery",
            "metrics": {"battery_capacity": 85, "load_percent": 45, ...},
            "timestamp": "2026-01-06T21:00:00Z"
        }
        """
        device_ip = raw_data.get("device_ip", "")
        device_name = raw_data.get("device_name", "")
        alarm_type = raw_data.get("alarm_type", "unknown")
        metrics = raw_data.get("metrics", {})
        timestamp = raw_data.get("timestamp")
        
        # Get alarm definition
        alarm_def = self.ALARM_TYPES.get(alarm_type, {
            "severity": Severity.WARNING,
            "title": f"UPS Alert - {alarm_type}",
            "description": ""
        })
        
        # Build title with device name
        title = f"{alarm_def['title']} - {device_name}" if device_name else alarm_def['title']
        
        # Build message with metrics
        message = self._build_message(alarm_def.get("description", ""), metrics)
        
        # Parse timestamp
        occurred_at = self._parse_timestamp(timestamp)
        
        # Is this a clear event?
        is_clear = alarm_def.get("is_clear", False)
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=f"{device_ip}:{alarm_type}",
            device_ip=device_ip,
            device_name=device_name,
            severity=alarm_def["severity"],
            category=Category.POWER,
            alert_type=f"eaton_{alarm_type}",
            title=title,
            message=message,
            occurred_at=occurred_at,
            is_clear=is_clear,
            raw_data=raw_data,
        )
    
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        """Determine severity from alarm type."""
        alarm_type = raw_data.get("alarm_type", "unknown")
        alarm_def = self.ALARM_TYPES.get(alarm_type, {})
        return alarm_def.get("severity", Severity.WARNING)
    
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        """All Eaton alerts are power category."""
        return Category.POWER
    
    def get_fingerprint(self, raw_data: Dict[str, Any]) -> str:
        """Generate deduplication fingerprint."""
        device_ip = raw_data.get("device_ip", "")
        alarm_type = raw_data.get("alarm_type", "")
        
        fingerprint_str = f"eaton:{device_ip}:{alarm_type}"
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()
    
    def is_clear_event(self, raw_data: Dict[str, Any]) -> bool:
        """Check if this is a clear event."""
        alarm_type = raw_data.get("alarm_type", "")
        alarm_def = self.ALARM_TYPES.get(alarm_type, {})
        return alarm_def.get("is_clear", False)
    
    def _build_message(self, description: str, metrics: Dict) -> str:
        """Build message with metrics."""
        lines = [description] if description else []
        
        if metrics.get("battery_capacity") is not None:
            lines.append(f"Battery: {metrics['battery_capacity']}%")
        
        if metrics.get("load_percent") is not None:
            lines.append(f"Load: {metrics['load_percent']}%")
        
        if metrics.get("runtime_remaining") is not None:
            mins = metrics['runtime_remaining']
            lines.append(f"Runtime: {mins} minutes")
        
        if metrics.get("output_source") is not None:
            source = self.OUTPUT_SOURCE.get(metrics['output_source'], "unknown")
            lines.append(f"Output Source: {source}")
        
        if metrics.get("temperature") is not None:
            lines.append(f"Temperature: {metrics['temperature']}°C")
        
        return "\n".join(lines)
    
    def _parse_timestamp(self, timestamp: Any) -> datetime:
        """Parse timestamp."""
        if not timestamp:
            return datetime.utcnow()
        
        if isinstance(timestamp, datetime):
            return timestamp
        
        try:
            return datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except ValueError:
            return datetime.utcnow()
