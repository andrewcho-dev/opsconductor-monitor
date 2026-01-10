"""
Eaton UPS Alert Normalizer

Transforms Eaton UPS SNMP data to standard NormalizedAlert format.
Uses database mappings for severity and category via BaseNormalizer.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from backend.connectors.base import BaseNormalizer
from backend.core.models import NormalizedAlert, Severity, Category
from backend.utils.ip_utils import validate_device_ip

logger = logging.getLogger(__name__)


class EatonNormalizer(BaseNormalizer):
    """
    Database-driven normalizer for Eaton UPS alerts.
    
    Extends BaseNormalizer for standard mapping methods.
    """
    
    connector_type = "eaton"
    default_category = Category.POWER
    
    # Eaton output source values (for message building only)
    OUTPUT_SOURCE = {
        1: "other",
        2: "none",
        3: "normal",
        4: "bypass",
        5: "battery",
        6: "booster",
        7: "reducer",
    }
    
    def normalize(self, raw_data: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """
        Transform Eaton UPS data to NormalizedAlert.
        
        Returns None if the event type is disabled or not in mappings.
        """
        device_ip = raw_data.get("device_ip", "")
        device_name = raw_data.get("device_name", "")
        alarm_type = raw_data.get("alarm_type", "unknown")
        metrics = raw_data.get("metrics", {})
        timestamp = raw_data.get("timestamp")
        
        # Check if event type is enabled in mappings
        if not self.is_event_enabled(alarm_type):
            logger.debug(f"Skipping disabled Eaton event type: {alarm_type}")
            return None
        
        # Validate device_ip
        try:
            validated_ip = validate_device_ip(device_ip, device_name)
        except ValueError as e:
            logger.warning(f"Skipping Eaton alert - no valid device_ip: {e}")
            return None
        
        # Get severity and category from database mappings
        severity = self._get_severity(alarm_type)
        category = self._get_category(alarm_type)
        
        # Get description from mapping
        mapping = self._severity_cache.get(alarm_type, {})
        description = mapping.get("description", "")
        
        # Build title
        title = f"Eaton {alarm_type.replace('_', ' ').title()} - {device_name}" if device_name else f"Eaton {alarm_type.replace('_', ' ').title()}"
        
        # Build message with metrics
        message = self._build_message(description, metrics, alarm_type, device_name, validated_ip)
        
        # Parse timestamp
        occurred_at = self._parse_timestamp(timestamp)
        
        # Use standard clear event detection from BaseNormalizer
        is_clear = self.is_clear_event(alarm_type, raw_data)
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=f"{validated_ip}:{alarm_type}",
            device_ip=validated_ip,
            device_name=device_name or None,
            severity=severity,
            category=category,
            alert_type=f"eaton_{alarm_type}",
            title=title,
            message=message,
            occurred_at=occurred_at,
            is_clear=is_clear,
            raw_data=raw_data,
        )
    
    def _build_message(self, description: str, metrics: Dict, alarm_type: str = "", device_name: str = "", device_ip: str = "") -> str:
        """Build message with metrics."""
        lines = []
        
        if device_name:
            lines.append(f"UPS: {device_name}")
        elif device_ip:
            lines.append(f"UPS: {device_ip}")
        
        if alarm_type:
            lines.append(f"Alarm: {alarm_type.replace('_', ' ')}")
        
        if description:
            lines.append(description)
        
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
        
        return " | ".join(lines) if lines else f"Eaton UPS {alarm_type} on {device_ip}"
    
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
