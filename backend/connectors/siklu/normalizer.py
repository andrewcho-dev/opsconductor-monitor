"""
Siklu Radio Alert Normalizer

Transforms Siklu EtherHaul data to standard NormalizedAlert format.
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Any

from backend.core.models import NormalizedAlert, Severity, Category

logger = logging.getLogger(__name__)


class SikluNormalizer:
    """Normalizer for Siklu radio link alerts."""
    
    ALERT_TYPES = {
        "link_down": {
            "category": Category.WIRELESS,
            "severity": Severity.CRITICAL,
            "title": "Radio Link Down",
        },
        "link_up": {
            "category": Category.WIRELESS,
            "severity": Severity.CLEAR,
            "title": "Radio Link Up",
            "is_clear": True,
        },
        "rsl_low": {
            "category": Category.WIRELESS,
            "severity": Severity.WARNING,
            "title": "RSL Low",
        },
        "rsl_critical": {
            "category": Category.WIRELESS,
            "severity": Severity.MAJOR,
            "title": "RSL Critical",
        },
        "modulation_drop": {
            "category": Category.WIRELESS,
            "severity": Severity.WARNING,
            "title": "Modulation Reduced",
        },
        "ethernet_down": {
            "category": Category.NETWORK,
            "severity": Severity.MAJOR,
            "title": "Ethernet Port Down",
        },
        "ethernet_up": {
            "category": Category.NETWORK,
            "severity": Severity.CLEAR,
            "title": "Ethernet Port Up",
            "is_clear": True,
        },
        "high_temperature": {
            "category": Category.ENVIRONMENT,
            "severity": Severity.WARNING,
            "title": "High Temperature",
        },
        "device_offline": {
            "category": Category.NETWORK,
            "severity": Severity.CRITICAL,
            "title": "Radio Offline",
        },
        "device_online": {
            "category": Category.NETWORK,
            "severity": Severity.CLEAR,
            "title": "Radio Online",
            "is_clear": True,
        },
    }
    
    @property
    def source_system(self) -> str:
        return "siklu"
    
    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedAlert:
        device_ip = raw_data.get("device_ip", "")
        device_name = raw_data.get("device_name", "")
        alert_type = raw_data.get("alert_type", "unknown")
        metrics = raw_data.get("metrics", {})
        timestamp = raw_data.get("timestamp")
        
        alert_def = self.ALERT_TYPES.get(alert_type, {
            "category": Category.WIRELESS,
            "severity": Severity.WARNING,
            "title": f"Siklu Alert - {alert_type}",
        })
        
        title = f"{alert_def['title']} - {device_name}" if device_name else alert_def['title']
        message = self._build_message(alert_type, metrics)
        occurred_at = self._parse_timestamp(timestamp)
        is_clear = alert_def.get("is_clear", False)
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=f"{device_ip}:{alert_type}",
            device_ip=device_ip,
            device_name=device_name,
            severity=alert_def["severity"],
            category=alert_def["category"],
            alert_type=f"siklu_{alert_type}",
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
        return hashlib.sha256(f"siklu:{device_ip}:{alert_type}".encode()).hexdigest()
    
    def _build_message(self, alert_type: str, metrics: Dict) -> str:
        lines = []
        
        if metrics.get("rsl") is not None:
            lines.append(f"RSL: {metrics['rsl']} dBm")
        if metrics.get("modulation"):
            lines.append(f"Modulation: {metrics['modulation']}")
        if metrics.get("link_state"):
            lines.append(f"Link State: {metrics['link_state']}")
        if metrics.get("temperature") is not None:
            lines.append(f"Temperature: {metrics['temperature']}°C")
        if metrics.get("tx_power") is not None:
            lines.append(f"TX Power: {metrics['tx_power']} dBm")
        if metrics.get("peer_ip"):
            lines.append(f"Peer: {metrics['peer_ip']}")
        
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
