"""
Axis Camera Alert Normalizer

Transforms Axis VAPIX event data to standard NormalizedAlert format.
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

from backend.core.models import NormalizedAlert, Severity, Category

logger = logging.getLogger(__name__)


class AxisNormalizer:
    """
    Normalizer for Axis camera events.
    
    Based on Axis VAPIX API event types.
    """
    
    # Axis event type to alert mapping - see docs/mappings/AXIS_ALERT_MAPPING.md
    EVENT_TYPES = {
        # Availability
        "camera_offline": {"category": Category.AVAILABILITY, "severity": Severity.CRITICAL, "title": "Camera Offline"},
        "camera_auth_failed": {"category": Category.AVAILABILITY, "severity": Severity.MAJOR, "title": "Camera Auth Failed"},
        "camera_unreachable": {"category": Category.AVAILABILITY, "severity": Severity.CRITICAL, "title": "Camera Unreachable"},
        
        # Storage
        "storage_failure": {"category": Category.HARDWARE, "severity": Severity.CRITICAL, "title": "Storage Failure"},
        "storage_full": {"category": Category.HARDWARE, "severity": Severity.CRITICAL, "title": "Storage Full"},
        "storage_warning": {"category": Category.HARDWARE, "severity": Severity.WARNING, "title": "Storage Warning"},
        "storage_missing": {"category": Category.HARDWARE, "severity": Severity.MAJOR, "title": "No Storage Detected"},
        "storage_readonly": {"category": Category.HARDWARE, "severity": Severity.MAJOR, "title": "Storage Read-Only"},
        
        # Recording
        "recording_stopped": {"category": Category.APPLICATION, "severity": Severity.CRITICAL, "title": "Recording Stopped"},
        "recording_error": {"category": Category.APPLICATION, "severity": Severity.MAJOR, "title": "Recording Error"},
        
        # Video
        "video_loss": {"category": Category.HARDWARE, "severity": Severity.CRITICAL, "title": "Video Loss"},
        "stream_timeout": {"category": Category.APPLICATION, "severity": Severity.MAJOR, "title": "Stream Timeout"},
        
        # Security/Tampering
        "tampering_detected": {"category": Category.SECURITY, "severity": Severity.CRITICAL, "title": "Camera Tampering"},
        "tampering_physical": {"category": Category.SECURITY, "severity": Severity.CRITICAL, "title": "Physical Tampering"},
        "camera_moved": {"category": Category.SECURITY, "severity": Severity.MAJOR, "title": "Camera Position Changed"},
        "unauthorized_access": {"category": Category.SECURITY, "severity": Severity.MAJOR, "title": "Unauthorized Access Attempt"},
        
        # Power
        "power_insufficient": {"category": Category.HARDWARE, "severity": Severity.MAJOR, "title": "Insufficient Power"},
        "poe_warning": {"category": Category.HARDWARE, "severity": Severity.WARNING, "title": "PoE Power Warning"},
        "power_supply_error": {"category": Category.HARDWARE, "severity": Severity.CRITICAL, "title": "Power Supply Error"},
        
        # PTZ
        "ptz_error": {"category": Category.HARDWARE, "severity": Severity.MAJOR, "title": "PTZ Error"},
        "ptz_power_insufficient": {"category": Category.HARDWARE, "severity": Severity.MAJOR, "title": "PTZ Power Insufficient"},
        "ptz_motor_failure": {"category": Category.HARDWARE, "severity": Severity.CRITICAL, "title": "PTZ Motor Failure"},
        "ptz_preset_failure": {"category": Category.HARDWARE, "severity": Severity.WARNING, "title": "PTZ Preset Failure"},
        
        # Environmental
        "temperature_critical": {"category": Category.ENVIRONMENTAL, "severity": Severity.CRITICAL, "title": "Camera Overheating"},
        "temperature_warning": {"category": Category.ENVIRONMENTAL, "severity": Severity.WARNING, "title": "Camera Temperature Warning"},
        "temperature_low": {"category": Category.ENVIRONMENTAL, "severity": Severity.WARNING, "title": "Camera Temperature Low"},
        "heater_failure": {"category": Category.ENVIRONMENTAL, "severity": Severity.MAJOR, "title": "Heater Failure"},
        "fan_failure": {"category": Category.ENVIRONMENTAL, "severity": Severity.CRITICAL, "title": "Fan Failure"},
        "housing_open": {"category": Category.ENVIRONMENTAL, "severity": Severity.MAJOR, "title": "Housing Open"},
        
        # Hardware
        "lens_error": {"category": Category.HARDWARE, "severity": Severity.MAJOR, "title": "Lens Error"},
        "focus_failure": {"category": Category.HARDWARE, "severity": Severity.WARNING, "title": "Auto-Focus Failed"},
        "ir_failure": {"category": Category.HARDWARE, "severity": Severity.WARNING, "title": "IR Illuminator Failure"},
        "sensor_failure": {"category": Category.HARDWARE, "severity": Severity.CRITICAL, "title": "Image Sensor Failure"},
        "audio_failure": {"category": Category.HARDWARE, "severity": Severity.WARNING, "title": "Audio System Failure"},
        "io_error": {"category": Category.HARDWARE, "severity": Severity.WARNING, "title": "I/O Port Error"},
        
        # Network
        "network_config_error": {"category": Category.NETWORK, "severity": Severity.MAJOR, "title": "Network Config Error"},
        "network_degraded": {"category": Category.NETWORK, "severity": Severity.WARNING, "title": "Network Degraded"},
        "ip_conflict": {"category": Category.NETWORK, "severity": Severity.MAJOR, "title": "IP Address Conflict"},
        "dns_failure": {"category": Category.NETWORK, "severity": Severity.WARNING, "title": "DNS Resolution Failure"},
        
        # Firmware/System
        "firmware_outdated": {"category": Category.MAINTENANCE, "severity": Severity.INFO, "title": "Firmware Outdated"},
        "camera_rebooted": {"category": Category.MAINTENANCE, "severity": Severity.INFO, "title": "Camera Rebooted"},
        "config_changed": {"category": Category.MAINTENANCE, "severity": Severity.INFO, "title": "Configuration Changed"},
        "certificate_expiring": {"category": Category.MAINTENANCE, "severity": Severity.WARNING, "title": "Certificate Expiring"},
        "certificate_expired": {"category": Category.MAINTENANCE, "severity": Severity.MAJOR, "title": "Certificate Expired"},
        "system_error": {"category": Category.MAINTENANCE, "severity": Severity.MAJOR, "title": "System Error"},
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
