"""
Cisco ASA Normalizer

Converts Cisco ASA events to normalized alerts.
Uses database mappings for severity and category via BaseNormalizer.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from backend.connectors.base import BaseNormalizer
from backend.core.models import NormalizedAlert, Severity, Category
from backend.utils.ip_utils import validate_device_ip

logger = logging.getLogger(__name__)


class CiscoASANormalizer(BaseNormalizer):
    """
    Database-driven normalizer for Cisco ASA events.
    
    Extends BaseNormalizer for standard mapping methods.
    """
    
    connector_type = "cisco_asa"
    default_category = Category.SECURITY
    
    def normalize(self, raw_event: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """Convert raw ASA event to normalized alert.
        
        Returns None if the event type is disabled or not in mappings.
        """
        event_type = raw_event.get("event_type", "")
        
        # Check if event type is enabled in mappings
        if not self.is_event_enabled(event_type):
            logger.debug(f"Skipping disabled Cisco ASA event type: {event_type}")
            return None
        
        # Validate device IP
        try:
            device_ip = validate_device_ip(
                raw_event.get("device_ip"),
                raw_event.get("device_name")
            )
        except ValueError as e:
            logger.warning(f"Invalid device IP for Cisco ASA alert: {e}")
            return None
        
        # Get severity and category from database mappings
        severity = self._get_severity(event_type)
        category = self._get_category(event_type)
        
        # Get description from mapping for title
        mapping = self._severity_cache.get(event_type, {})
        title = mapping.get("description", f"Cisco ASA {event_type.replace('_', ' ').title()}")
        
        # Build message
        message = f"Device: {device_ip} | Event: {event_type.replace('_', ' ')}"
        if raw_event.get("peer_ip"):
            message += f" | Peer: {raw_event['peer_ip']}"
        if raw_event.get("interface"):
            message += f" | Interface: {raw_event['interface']}"
        
        # Generate unique source alert ID
        source_alert_id = f"cisco_asa_{event_type}_{device_ip}"
        if "peer_ip" in raw_event:
            source_alert_id += f"_{raw_event['peer_ip']}"
        if "interface" in raw_event:
            source_alert_id += f"_{raw_event['interface']}"
        
        # Parse timestamp
        timestamp = raw_event.get("timestamp")
        if isinstance(timestamp, str):
            try:
                occurred_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                occurred_at = datetime.utcnow()
        else:
            occurred_at = datetime.utcnow()
        
        return NormalizedAlert(
            source_system="cisco_asa",
            source_alert_id=source_alert_id,
            device_ip=device_ip,
            device_name=raw_event.get("device_name", device_ip),
            severity=severity,
            category=category,
            alert_type=f"cisco_asa_{event_type}",
            title=title,
            message=message,
            occurred_at=occurred_at,
            raw_data=raw_event,
        )
