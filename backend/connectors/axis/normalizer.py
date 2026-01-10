"""
Axis Camera Alert Normalizer

Transforms Axis VAPIX event data to standard NormalizedAlert format.
Uses database mappings for severity and category via BaseNormalizer.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from backend.connectors.base import BaseNormalizer
from backend.core.models import NormalizedAlert, Severity, Category
from backend.utils.ip_utils import validate_device_ip

logger = logging.getLogger(__name__)


class AxisNormalizer(BaseNormalizer):
    """
    Database-driven normalizer for Axis camera events.
    
    Extends BaseNormalizer for standard mapping methods.
    """
    
    connector_type = "axis"
    default_category = Category.VIDEO
    
    def normalize(self, raw_data: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """
        Transform Axis event to NormalizedAlert.
        
        Returns None if the event type is disabled in mappings.
        
        Expected raw_data format:
        {
            "device_ip": "10.1.3.1",
            "device_name": "Camera-Lobby",
            "event_type": "motion",
            "event_data": {...},
            "timestamp": "2026-01-06T21:00:00Z"
        }
        """
        device_ip = raw_data.get("device_ip", "")
        device_name = raw_data.get("device_name", "")
        event_type = raw_data.get("event_type", "unknown").lower()
        event_data = raw_data.get("event_data", {})
        timestamp = raw_data.get("timestamp")
        
        # Check if this event type is enabled - skip if disabled
        if not self.is_event_enabled(event_type):
            logger.debug(f"Skipping disabled event type: {event_type}")
            return None
        
        # Get severity and category from database mappings
        severity = self._get_severity(event_type)
        category = self._get_category(event_type)
        
        # Build title with device name
        title = f"Axis {event_type.replace('_', ' ').title()} - {device_name}" if device_name else f"Axis {event_type.replace('_', ' ').title()}"
        
        # Build message from event data
        message = self._build_message(event_type, event_data, device_ip, device_name)
        
        # Parse timestamp
        occurred_at = self._parse_timestamp(timestamp)
        
        # Use standard clear event detection from BaseNormalizer
        is_clear = self.is_clear_event(event_type, raw_data)
        
        # source_alert_id must be STABLE for deduplication - no timestamps!
        source_alert_id = f"{device_ip}:{event_type}"
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=source_alert_id,
            device_ip=validate_device_ip(device_ip, device_name),
            device_name=device_name or None,
            severity=severity,
            category=category,
            alert_type=f"axis_{event_type}",
            title=title,
            message=message,
            occurred_at=occurred_at,
            is_clear=is_clear,
            raw_data=raw_data,
        )
    
    def _build_message(self, event_type: str, event_data: Dict, device_ip: str = "", device_name: str = "") -> str:
        """Build message from event data."""
        lines = []
        
        # Always include device info
        if device_name:
            lines.append(f"Camera: {device_name}")
        elif device_ip:
            lines.append(f"Camera: {device_ip}")
        
        # Event type
        if event_type:
            lines.append(f"Event: {event_type.replace('_', ' ')}")
        
        if event_data:
            # Error info
            if event_data.get("error"):
                lines.append(f"Error: {event_data['error']}")
            
            # Common fields
            if event_data.get("source"):
                lines.append(f"Source: {event_data['source']}")
            if event_data.get("channel"):
                lines.append(f"Channel: {event_data['channel']}")
            if event_data.get("region"):
                lines.append(f"Region: {event_data['region']}")
            
            # Storage-specific
            if event_data.get("disk_id"):
                lines.append(f"Disk: {event_data['disk_id']}")
            if event_data.get("used_percent"):
                lines.append(f"Usage: {event_data['used_percent']}%")
            
            # Temperature-specific
            if event_data.get("temperature"):
                lines.append(f"Temperature: {event_data['temperature']}°C")
        
        return " | ".join(lines) if lines else f"{event_type} on {device_ip}"
    
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
