"""
Ubiquiti Alert Normalizer

Transforms Ubiquiti device data to standard NormalizedAlert format.
Uses database mappings for severity and category via BaseNormalizer.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from backend.connectors.base import BaseNormalizer
from backend.core.models import NormalizedAlert, Severity, Category
from backend.utils.ip_utils import validate_device_ip

logger = logging.getLogger(__name__)


class UbiquitiNormalizer(BaseNormalizer):
    """
    Database-driven normalizer for Ubiquiti device alerts.
    
    Extends BaseNormalizer for standard mapping methods.
    """
    
    connector_type = "ubiquiti"
    default_category = Category.WIRELESS
    
    def normalize(self, raw_data: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """Transform Ubiquiti UISP data to NormalizedAlert.
        
        Returns None if the event type is disabled or not in mappings.
        """
        device_ip = raw_data.get("device_ip", "")
        device_name = raw_data.get("device_name", "")
        alert_type = raw_data.get("alert_type", "unknown")
        metrics = raw_data.get("metrics", {})
        timestamp = raw_data.get("timestamp")
        
        # Check if event type is enabled in mappings
        if not self.is_event_enabled(alert_type):
            logger.debug(f"Skipping disabled Ubiquiti event type: {alert_type}")
            return None
        
        # Validate device_ip
        try:
            validated_ip = validate_device_ip(device_ip, device_name)
        except ValueError as e:
            logger.warning(f"Skipping Ubiquiti alert - no valid device_ip: {e}")
            return None
        
        # Get severity and category from database mappings
        severity = self._get_severity(alert_type)
        category = self._get_category(alert_type)
        
        # Get description from mapping
        mapping = self._severity_cache.get(alert_type, {})
        description = mapping.get("description", "")
        
        # Build title
        title = f"Ubiquiti {alert_type.replace('_', ' ').title()} - {device_name}" if device_name else f"Ubiquiti {alert_type.replace('_', ' ').title()}"
        
        message = self._build_message(alert_type, metrics, device_name, validated_ip)
        occurred_at = self._parse_timestamp(timestamp)
        
        # Use standard clear event detection from BaseNormalizer
        is_clear = self.is_clear_event(alert_type, raw_data)
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=f"{validated_ip}:{alert_type}",
            device_ip=validated_ip,
            device_name=device_name or None,
            severity=severity,
            category=category,
            alert_type=f"ubiquiti_{alert_type}",
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
