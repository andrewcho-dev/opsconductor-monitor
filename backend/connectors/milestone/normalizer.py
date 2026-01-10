"""
Milestone VMS Alert Normalizer

Transforms Milestone XProtect event data to standard NormalizedAlert format.
Uses database mappings for severity and category via BaseNormalizer.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from backend.connectors.base import BaseNormalizer
from backend.core.models import NormalizedAlert, Severity, Category
from backend.utils.ip_utils import validate_device_ip

logger = logging.getLogger(__name__)


class MilestoneNormalizer(BaseNormalizer):
    """
    Database-driven normalizer for Milestone XProtect VMS events.
    
    Extends BaseNormalizer for standard mapping methods.
    """
    
    connector_type = "milestone"
    default_category = Category.VIDEO
    
    def normalize(self, raw_data: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """
        Transform Milestone event to NormalizedAlert.
        
        Returns None if the event type is disabled in mappings or no valid device_ip.
        """
        device_ip = raw_data.get("device_ip") or raw_data.get("camera_ip", "")
        device_name = raw_data.get("device_name") or raw_data.get("camera_name", "")
        event_type = raw_data.get("event_type", "unknown").lower().replace(" ", "_")
        event_data = raw_data.get("event_data", {})
        timestamp = raw_data.get("timestamp")
        
        # Check if this event type is enabled - skip if disabled
        if not self.is_event_enabled(event_type):
            logger.debug(f"Skipping disabled event type: {event_type}")
            return None
        
        # Validate device_ip - skip if we can't determine IP
        try:
            validated_ip = validate_device_ip(device_ip, device_name)
        except ValueError as e:
            logger.warning(f"Skipping Milestone alert - no valid device_ip: {e}")
            return None
        
        # Get severity and category from database mappings
        severity = self._get_severity(event_type)
        category = self._get_category(event_type)
        
        # Build title
        title = f"Milestone {event_type.replace('_', ' ').title()} - {device_name}" if device_name else f"Milestone {event_type.replace('_', ' ').title()}"
        
        # Build meaningful message from event data
        message = event_data.get("message", "")
        if not message:
            # Construct message from available data
            parts = []
            if device_name:
                parts.append(f"Camera: {device_name}")
            if event_type:
                parts.append(f"Event: {event_type.replace('_', ' ')}")
            if event_data.get("reason"):
                parts.append(f"Reason: {event_data['reason']}")
            if event_data.get("details"):
                parts.append(f"Details: {event_data['details']}")
            message = " | ".join(parts) if parts else f"{event_type.replace('_', ' ')} on {device_name or validated_ip}"
        
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
            alert_type=f"milestone_{event_type}",
            title=title,
            message=message,
            occurred_at=occurred_at,
            is_clear=is_clear,
            raw_data=raw_data,
        )
    
    def _parse_timestamp(self, timestamp: Any) -> datetime:
        if not timestamp:
            return datetime.utcnow()
        if isinstance(timestamp, datetime):
            return timestamp
        try:
            return datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except ValueError:
            return datetime.utcnow()
