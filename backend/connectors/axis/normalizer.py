"""
Axis Camera Alert Normalizer

Transforms Axis VAPIX event data to standard NormalizedAlert format.
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

from core.models import NormalizedAlert, Severity, Category

logger = logging.getLogger(__name__)


class AxisNormalizer:
    """
    Normalizer for Axis camera events.
    
    Based on Axis VAPIX API event types.
    """
    
    # Axis event type to alert mapping
    EVENT_TYPES = {
        # Video Analytics
        "motion": {
            "category": Category.VIDEO,
            "severity": Severity.INFO,
            "title": "Motion Detected",
        },
        "vmd3": {
            "category": Category.VIDEO,
            "severity": Severity.INFO,
            "title": "Video Motion Detection",
        },
        "objectanalytics": {
            "category": Category.VIDEO,
            "severity": Severity.INFO,
            "title": "Object Analytics Event",
        },
        "crosslinedetection": {
            "category": Category.VIDEO,
            "severity": Severity.WARNING,
            "title": "Crossline Detection",
        },
        
        # Security
        "tampering": {
            "category": Category.SECURITY,
            "severity": Severity.MAJOR,
            "title": "Camera Tampering Detected",
        },
        "casing_open": {
            "category": Category.SECURITY,
            "severity": Severity.MAJOR,
            "title": "Camera Casing Opened",
        },
        
        # Storage
        "storage_failure": {
            "category": Category.STORAGE,
            "severity": Severity.CRITICAL,
            "title": "Storage Failure",
        },
        "storage_full": {
            "category": Category.STORAGE,
            "severity": Severity.MAJOR,
            "title": "Storage Full",
        },
        "storage_disruption": {
            "category": Category.STORAGE,
            "severity": Severity.MAJOR,
            "title": "Storage Disruption",
        },
        "recording_error": {
            "category": Category.VIDEO,
            "severity": Severity.MAJOR,
            "title": "Recording Error",
        },
        
        # Network
        "network_lost": {
            "category": Category.NETWORK,
            "severity": Severity.CRITICAL,
            "title": "Network Connection Lost",
        },
        "network_restored": {
            "category": Category.NETWORK,
            "severity": Severity.CLEAR,
            "title": "Network Connection Restored",
            "is_clear": True,
        },
        
        # Hardware
        "temperature_high": {
            "category": Category.ENVIRONMENT,
            "severity": Severity.WARNING,
            "title": "High Temperature",
        },
        "fan_failure": {
            "category": Category.ENVIRONMENT,
            "severity": Severity.MAJOR,
            "title": "Fan Failure",
        },
        
        # System
        "system_ready": {
            "category": Category.APPLICATION,
            "severity": Severity.CLEAR,
            "title": "System Ready",
            "is_clear": True,
        },
        "device_offline": {
            "category": Category.NETWORK,
            "severity": Severity.CRITICAL,
            "title": "Camera Offline",
        },
        "device_online": {
            "category": Category.NETWORK,
            "severity": Severity.CLEAR,
            "title": "Camera Online",
            "is_clear": True,
        },
    }
    
    @property
    def source_system(self) -> str:
        return "axis"
    
    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedAlert:
        """
        Transform Axis event to NormalizedAlert.
        
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
        
        # Get event definition
        event_def = self.EVENT_TYPES.get(event_type, {
            "category": Category.VIDEO,
            "severity": Severity.INFO,
            "title": f"Axis Event - {event_type}",
        })
        
        # Build title with device name
        title = f"{event_def['title']} - {device_name}" if device_name else event_def['title']
        
        # Build message from event data
        message = self._build_message(event_type, event_data)
        
        # Parse timestamp
        occurred_at = self._parse_timestamp(timestamp)
        
        # Is this a clear event?
        is_clear = event_def.get("is_clear", False)
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=f"{device_ip}:{event_type}:{occurred_at.timestamp()}",
            device_ip=device_ip,
            device_name=device_name,
            severity=event_def["severity"],
            category=event_def["category"],
            alert_type=f"axis_{event_type}",
            title=title,
            message=message,
            occurred_at=occurred_at,
            is_clear=is_clear,
            raw_data=raw_data,
        )
    
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        """Determine severity from event type."""
        event_type = raw_data.get("event_type", "").lower()
        event_def = self.EVENT_TYPES.get(event_type, {})
        return event_def.get("severity", Severity.INFO)
    
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        """Determine category from event type."""
        event_type = raw_data.get("event_type", "").lower()
        event_def = self.EVENT_TYPES.get(event_type, {})
        return event_def.get("category", Category.VIDEO)
    
    def get_fingerprint(self, raw_data: Dict[str, Any]) -> str:
        """Generate deduplication fingerprint."""
        device_ip = raw_data.get("device_ip", "")
        event_type = raw_data.get("event_type", "")
        
        fingerprint_str = f"axis:{device_ip}:{event_type}"
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()
    
    def is_clear_event(self, raw_data: Dict[str, Any]) -> bool:
        """Check if this is a clear event."""
        event_type = raw_data.get("event_type", "").lower()
        event_def = self.EVENT_TYPES.get(event_type, {})
        return event_def.get("is_clear", False)
    
    def _build_message(self, event_type: str, event_data: Dict) -> str:
        """Build message from event data."""
        if not event_data:
            return ""
        
        lines = []
        
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
