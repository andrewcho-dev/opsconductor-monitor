"""
Cradlepoint Alert Normalizer

Transforms Cradlepoint NCOS data to standard NormalizedAlert format.
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Any

from backend.core.models import NormalizedAlert, Severity, Category
from backend.utils.ip_utils import validate_device_ip

logger = logging.getLogger(__name__)


class CradlepointNormalizer:
    """Normalizer for Cradlepoint router alerts."""
    
    ALERT_TYPES = {
        "signal_low": {
            "category": Category.WIRELESS,
            "severity": Severity.WARNING,
            "title": "Cellular Signal Low",
        },
        "signal_critical": {
            "category": Category.WIRELESS,
            "severity": Severity.MAJOR,
            "title": "Cellular Signal Critical",
        },
        "connection_lost": {
            "category": Category.WIRELESS,
            "severity": Severity.CRITICAL,
            "title": "Cellular Connection Lost",
        },
        "connection_restored": {
            "category": Category.WIRELESS,
            "severity": Severity.CLEAR,
            "title": "Cellular Connection Restored",
            "is_clear": True,
        },
        "wan_failover": {
            "category": Category.NETWORK,
            "severity": Severity.WARNING,
            "title": "WAN Failover Active",
        },
        "wan_restored": {
            "category": Category.NETWORK,
            "severity": Severity.CLEAR,
            "title": "WAN Primary Restored",
            "is_clear": True,
        },
        "carrier_change": {
            "category": Category.WIRELESS,
            "severity": Severity.INFO,
            "title": "Carrier Changed",
        },
        "device_offline": {
            "category": Category.NETWORK,
            "severity": Severity.CRITICAL,
            "title": "Router Offline",
        },
        "device_online": {
            "category": Category.NETWORK,
            "severity": Severity.CLEAR,
            "title": "Router Online",
            "is_clear": True,
        },
        "high_temperature": {
            "category": Category.ENVIRONMENT,
            "severity": Severity.WARNING,
            "title": "High Temperature",
        },
    }
    
    # Signal thresholds
    RSSI_WARNING = -85
    RSSI_CRITICAL = -95
    RSRP_WARNING = -100
    RSRP_CRITICAL = -110
    
    @property
    def source_system(self) -> str:
        return "cradlepoint"
    
    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedAlert:
        """Transform Cradlepoint data to NormalizedAlert."""
        device_ip = raw_data.get("device_ip", "")
        device_name = raw_data.get("device_name", "")
        alert_type = raw_data.get("alert_type", "unknown")
        metrics = raw_data.get("metrics", {})
        timestamp = raw_data.get("timestamp")
        
        alert_def = self.ALERT_TYPES.get(alert_type, {
            "category": Category.WIRELESS,
            "severity": Severity.WARNING,
            "title": f"Cradlepoint Alert - {alert_type}",
        })
        
        title = f"{alert_def['title']} - {device_name}" if device_name else alert_def['title']
        message = self._build_message(alert_type, metrics)
        occurred_at = self._parse_timestamp(timestamp)
        is_clear = alert_def.get("is_clear", False)
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=f"{device_ip}:{alert_type}",
            device_ip=validate_device_ip(device_ip, device_name),
            device_name=device_name or None,
            severity=alert_def["severity"],
            category=alert_def["category"],
            alert_type=f"cradlepoint_{alert_type}",
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
        return self.ALERT_TYPES.get(alert_type, {}).get("category", Category.WIRELESS)
    
    def get_fingerprint(self, raw_data: Dict[str, Any]) -> str:
        device_ip = raw_data.get("device_ip", "")
        alert_type = raw_data.get("alert_type", "")
        return hashlib.sha256(f"cradlepoint:{device_ip}:{alert_type}".encode()).hexdigest()
    
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
