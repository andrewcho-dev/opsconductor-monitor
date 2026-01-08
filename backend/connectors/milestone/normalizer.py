"""
Milestone VMS Alert Normalizer

Transforms Milestone XProtect event data to standard NormalizedAlert format.
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Any

from backend.core.models import NormalizedAlert, Severity, Category

logger = logging.getLogger(__name__)


class MilestoneNormalizer:
    """Normalizer for Milestone XProtect VMS events."""
    
    EVENT_TYPES = {
        # Camera events
        "camera_connection_error": {
            "category": Category.VIDEO,
            "severity": Severity.MAJOR,
            "title": "Camera Connection Error",
        },
        "camera_offline": {
            "category": Category.VIDEO,
            "severity": Severity.CRITICAL,
            "title": "Camera Offline",
        },
        "camera_online": {
            "category": Category.VIDEO,
            "severity": Severity.CLEAR,
            "title": "Camera Online",
            "is_clear": True,
        },
        
        # Recording events
        "recording_started": {
            "category": Category.VIDEO,
            "severity": Severity.INFO,
            "title": "Recording Started",
        },
        "recording_stopped": {
            "category": Category.VIDEO,
            "severity": Severity.WARNING,
            "title": "Recording Stopped",
        },
        "recording_error": {
            "category": Category.VIDEO,
            "severity": Severity.MAJOR,
            "title": "Recording Error",
        },
        
        # Motion events
        "motion_started": {
            "category": Category.VIDEO,
            "severity": Severity.INFO,
            "title": "Motion Detected",
        },
        "motion_stopped": {
            "category": Category.VIDEO,
            "severity": Severity.CLEAR,
            "title": "Motion Ended",
            "is_clear": True,
        },
        
        # Analytics
        "analytics_event": {
            "category": Category.VIDEO,
            "severity": Severity.WARNING,
            "title": "Analytics Event",
        },
        
        # Storage
        "storage_alert": {
            "category": Category.STORAGE,
            "severity": Severity.MAJOR,
            "title": "Storage Alert",
        },
        "archive_full": {
            "category": Category.STORAGE,
            "severity": Severity.CRITICAL,
            "title": "Archive Storage Full",
        },
        
        # Server
        "server_error": {
            "category": Category.COMPUTE,
            "severity": Severity.CRITICAL,
            "title": "Server Error",
        },
        "license_warning": {
            "category": Category.APPLICATION,
            "severity": Severity.WARNING,
            "title": "License Warning",
        },
        "failover_activated": {
            "category": Category.APPLICATION,
            "severity": Severity.MAJOR,
            "title": "Failover Activated",
        },
    }
    
    @property
    def source_system(self) -> str:
        return "milestone"
    
    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedAlert:
        """Transform Milestone event to NormalizedAlert."""
        device_ip = raw_data.get("device_ip") or raw_data.get("camera_ip", "")
        device_name = raw_data.get("device_name") or raw_data.get("camera_name", "")
        event_type = raw_data.get("event_type", "unknown").lower().replace(" ", "_")
        event_data = raw_data.get("event_data", {})
        timestamp = raw_data.get("timestamp")
        
        event_def = self.EVENT_TYPES.get(event_type, {
            "category": Category.VIDEO,
            "severity": Severity.WARNING,
            "title": f"Milestone Event - {event_type}",
        })
        
        title = f"{event_def['title']} - {device_name}" if device_name else event_def['title']
        message = event_data.get("message", "")
        occurred_at = self._parse_timestamp(timestamp)
        is_clear = event_def.get("is_clear", False)
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=f"{device_ip}:{event_type}:{occurred_at.timestamp()}",
            device_ip=device_ip if device_ip else None,
            device_name=device_name if device_name else None,
            severity=event_def["severity"],
            category=event_def["category"],
            alert_type=f"milestone_{event_type}",
            title=title,
            message=message,
            occurred_at=occurred_at,
            is_clear=is_clear,
            raw_data=raw_data,
        )
    
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        event_type = raw_data.get("event_type", "").lower().replace(" ", "_")
        return self.EVENT_TYPES.get(event_type, {}).get("severity", Severity.WARNING)
    
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        event_type = raw_data.get("event_type", "").lower().replace(" ", "_")
        return self.EVENT_TYPES.get(event_type, {}).get("category", Category.VIDEO)
    
    def get_fingerprint(self, raw_data: Dict[str, Any]) -> str:
        device_ip = raw_data.get("device_ip") or raw_data.get("camera_ip", "")
        event_type = raw_data.get("event_type", "")
        return hashlib.sha256(f"milestone:{device_ip}:{event_type}".encode()).hexdigest()
    
    def _parse_timestamp(self, timestamp: Any) -> datetime:
        if not timestamp:
            return datetime.utcnow()
        if isinstance(timestamp, datetime):
            return timestamp
        try:
            return datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except ValueError:
            return datetime.utcnow()
