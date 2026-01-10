"""
Siklu Radio Alert Normalizer

Database-driven normalizer for Siklu EtherHaul radio alerts.
Uses database mappings for severity and category via BaseNormalizer.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from backend.connectors.base import BaseNormalizer
from backend.core.models import NormalizedAlert, Severity, Category
from backend.utils.ip_utils import validate_device_ip

logger = logging.getLogger(__name__)


class SikluNormalizer(BaseNormalizer):
    """
    Database-driven normalizer for Siklu radio link alerts.
    
    Extends BaseNormalizer for standard mapping methods.
    """
    
    connector_type = "siklu"
    default_category = Category.WIRELESS
    
    # Fallback alert type definitions for titles (connector-specific)
    ALERT_TYPE_DEFAULTS = {
        "link_down": {"title": "Radio Link Down"},
        "link_up": {"title": "Radio Link Up"},
        "rsl_low": {"title": "RSL Low"},
        "rsl_critical": {"title": "RSL Critical"},
        "modulation_drop": {"title": "Modulation Reduced"},
        "ethernet_down": {"title": "Ethernet Port Down"},
        "ethernet_up": {"title": "Ethernet Port Up"},
        "high_temperature": {"title": "High Temperature"},
        "device_offline": {"title": "Radio Offline"},
        "device_online": {"title": "Radio Online"},
    }
    
    def normalize(self, raw_data: Dict[str, Any]) -> Optional[NormalizedAlert]:
        device_ip = raw_data.get("device_ip", "")
        device_name = raw_data.get("device_name", "")
        alert_type = raw_data.get("alert_type", "unknown")
        metrics = raw_data.get("metrics", {})
        timestamp = raw_data.get("timestamp")
        
        # Check if this alert type is enabled in mappings
        if not self.is_event_enabled(alert_type):
            logger.debug(f"Skipping disabled Siklu alert type: {alert_type}")
            return None
        
        # Get severity and category from database mappings (via BaseNormalizer)
        severity = self._get_severity(alert_type)
        category = self._get_category(alert_type)
        
        # Get title from defaults
        alert_defaults = self.ALERT_TYPE_DEFAULTS.get(alert_type, {})
        base_title = alert_defaults.get("title", f"Siklu Alert - {alert_type}")
        title = f"{base_title} - {device_name}" if device_name else base_title
        message = self._build_message(alert_type, metrics, device_name, device_ip)
        occurred_at = self._parse_timestamp(timestamp)
        
        # Use standard clear event detection from BaseNormalizer
        is_clear = self.is_clear_event(alert_type, raw_data)
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=f"{device_ip}:{alert_type}",
            device_ip=validate_device_ip(device_ip, device_name),
            device_name=device_name or None,
            severity=severity,
            category=category,
            alert_type=f"siklu_{alert_type}",
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
        
        return " | ".join(lines) if lines else f"Siklu {alert_type} on {device_ip}"
    
    def _parse_timestamp(self, timestamp: Any) -> datetime:
        if not timestamp:
            return datetime.utcnow()
        if isinstance(timestamp, datetime):
            return timestamp
        try:
            return datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except ValueError:
            return datetime.utcnow()
