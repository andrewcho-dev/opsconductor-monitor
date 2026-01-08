"""
Ubiquiti UISP Alert Normalizer

Transforms Ubiquiti UISP data to standard NormalizedAlert format.
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Any

from backend.core.models import NormalizedAlert, Severity, Category
from backend.utils.ip_utils import validate_device_ip

logger = logging.getLogger(__name__)


class UbiquitiNormalizer:
    """Normalizer for Ubiquiti UISP alerts."""
    
    ALERT_TYPES = {
        "device_offline": {
            "category": Category.NETWORK,
            "severity": Severity.CRITICAL,
            "title": "Device Offline",
        },
        "device_online": {
            "category": Category.NETWORK,
            "severity": Severity.CLEAR,
            "title": "Device Online",
            "is_clear": True,
        },
        "high_cpu": {
            "category": Category.COMPUTE,
            "severity": Severity.WARNING,
            "title": "High CPU Usage",
        },
        "high_memory": {
            "category": Category.COMPUTE,
            "severity": Severity.WARNING,
            "title": "High Memory Usage",
        },
        "interface_down": {
            "category": Category.NETWORK,
            "severity": Severity.MAJOR,
            "title": "Interface Down",
        },
        "interface_up": {
            "category": Category.NETWORK,
            "severity": Severity.CLEAR,
            "title": "Interface Up",
            "is_clear": True,
        },
        "signal_degraded": {
            "category": Category.WIRELESS,
            "severity": Severity.WARNING,
            "title": "Signal Degraded",
        },
        "reboot_detected": {
            "category": Category.NETWORK,
            "severity": Severity.INFO,
            "title": "Device Rebooted",
        },
        "config_changed": {
            "category": Category.SECURITY,
            "severity": Severity.INFO,
            "title": "Configuration Changed",
        },
        "firmware_update": {
            "category": Category.APPLICATION,
            "severity": Severity.INFO,
            "title": "Firmware Update Available",
        },
        "outage": {
            "category": Category.NETWORK,
            "severity": Severity.CRITICAL,
            "title": "Service Outage",
        },
        "outage_ended": {
            "category": Category.NETWORK,
            "severity": Severity.CLEAR,
            "title": "Outage Ended",
            "is_clear": True,
        },
    }
    
    @property
    def source_system(self) -> str:
        return "ubiquiti"
    
    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedAlert:
        device_ip = raw_data.get("device_ip", "")
        device_name = raw_data.get("device_name", "")
        alert_type = raw_data.get("alert_type", "unknown")
        metrics = raw_data.get("metrics", {})
        timestamp = raw_data.get("timestamp")
        
        alert_def = self.ALERT_TYPES.get(alert_type, {
            "category": Category.NETWORK,
            "severity": Severity.WARNING,
            "title": f"UISP Alert - {alert_type}",
        })
        
        title = f"{alert_def['title']} - {device_name}" if device_name else alert_def['title']
        message = self._build_message(alert_type, metrics, device_name, device_ip)
        occurred_at = self._parse_timestamp(timestamp)
        is_clear = alert_def.get("is_clear", False)
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=f"{device_ip}:{alert_type}",
            device_ip=validate_device_ip(device_ip, device_name),
            device_name=device_name or None,
            severity=alert_def["severity"],
            category=alert_def["category"],
            alert_type=f"ubiquiti_{alert_type}",
            title=title,
            message=message,
            occurred_at=occurred_at,
            is_clear=is_clear,
            raw_data=raw_data,
        )
    
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        alert_type = raw_data.get("alert_type", "")
        return self.ALERT_TYPES.get(alert_type, {}).get("severity", Severity.WARNING)
    
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        alert_type = raw_data.get("alert_type", "")
        return self.ALERT_TYPES.get(alert_type, {}).get("category", Category.NETWORK)
    
    def get_fingerprint(self, raw_data: Dict[str, Any]) -> str:
        device_ip = raw_data.get("device_ip", "")
        alert_type = raw_data.get("alert_type", "")
        return hashlib.sha256(f"ubiquiti:{device_ip}:{alert_type}".encode()).hexdigest()
    
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
        
        if metrics.get("cpu_percent") is not None:
            lines.append(f"CPU: {metrics['cpu_percent']}%")
        if metrics.get("memory_percent") is not None:
            lines.append(f"Memory: {metrics['memory_percent']}%")
        if metrics.get("uptime") is not None:
            lines.append(f"Uptime: {metrics['uptime']}")
        if metrics.get("signal") is not None:
            lines.append(f"Signal: {metrics['signal']} dBm")
        if metrics.get("interface"):
            lines.append(f"Interface: {metrics['interface']}")
        if metrics.get("firmware"):
            lines.append(f"Firmware: {metrics['firmware']}")
        
        return " | ".join(lines) if lines else f"Ubiquiti {alert_type} on {device_ip}"
    
    def _parse_timestamp(self, timestamp: Any) -> datetime:
        if not timestamp:
            return datetime.utcnow()
        if isinstance(timestamp, datetime):
            return timestamp
        try:
            return datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except ValueError:
            return datetime.utcnow()
