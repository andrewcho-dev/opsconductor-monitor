"""
Axis Camera Alert Normalizer

Transforms Axis VAPIX event data to standard NormalizedAlert format.
Uses database mappings for severity and category - NO HARDCODED VALUES.
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

from backend.core.models import NormalizedAlert, Severity, Category
from backend.utils.ip_utils import validate_device_ip
from backend.utils.db import db_query

logger = logging.getLogger(__name__)


class AxisNormalizer:
    """
    Database-driven normalizer for Axis camera events.
    
    All mappings come from severity_mappings and category_mappings tables.
    """
    
    def __init__(self):
        self._severity_cache: Dict[str, Dict] = {}
        self._category_cache: Dict[str, Dict] = {}
        self._cache_loaded = False
    
    def _load_mappings(self):
        """Load mappings from database."""
        if self._cache_loaded:
            return
        
        try:
            # Load severity mappings
            severity_rows = db_query(
                "SELECT source_value, target_severity, enabled, description FROM severity_mappings WHERE connector_type = %s",
                ("axis",)
            )
            for row in severity_rows:
                self._severity_cache[row["source_value"]] = {
                    "severity": row["target_severity"],
                    "enabled": row["enabled"],
                    "description": row.get("description", "")
                }
            
            # Load category mappings
            category_rows = db_query(
                "SELECT source_value, target_category, enabled, description FROM category_mappings WHERE connector_type = %s",
                ("axis",)
            )
            for row in category_rows:
                self._category_cache[row["source_value"]] = {
                    "category": row["target_category"],
                    "enabled": row["enabled"],
                    "description": row.get("description", "")
                }
            
            self._cache_loaded = True
            logger.info(f"Loaded {len(self._severity_cache)} severity and {len(self._category_cache)} category mappings for axis")
            
        except Exception as e:
            logger.error(f"Failed to load axis mappings: {e}")
            self._cache_loaded = True  # Don't retry on every call
    
    def is_event_enabled(self, event_type: str) -> bool:
        """Check if this event type is enabled in mappings."""
        self._load_mappings()
        
        severity_mapping = self._severity_cache.get(event_type)
        if severity_mapping and not severity_mapping.get("enabled", True):
            return False
        
        category_mapping = self._category_cache.get(event_type)
        if category_mapping and not category_mapping.get("enabled", True):
            return False
        
        return True
    
    def _get_severity(self, event_type: str) -> Severity:
        """Get severity from database mapping."""
        self._load_mappings()
        
        mapping = self._severity_cache.get(event_type)
        if mapping:
            try:
                return Severity(mapping["severity"])
            except ValueError:
                pass
        
        # Default fallback
        return Severity.WARNING
    
    def _get_category(self, event_type: str) -> Category:
        """Get category from database mapping."""
        self._load_mappings()
        
        mapping = self._category_cache.get(event_type)
        if mapping:
            try:
                return Category(mapping["category"])
            except ValueError:
                pass
        
        # Default fallback
        return Category.VIDEO
    
    @property
    def source_system(self) -> str:
        return "axis"
    
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
        
        # Is this a clear event? (event types ending in _restored, _up, _online, etc.)
        is_clear = event_type.endswith(("_restored", "_up", "_online", "_ok", "_normal", "_cleared"))
        
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
    
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        """Determine severity from database mapping."""
        event_type = raw_data.get("event_type", "").lower()
        return self._get_severity(event_type)
    
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        """Determine category from database mapping."""
        event_type = raw_data.get("event_type", "").lower()
        return self._get_category(event_type)
    
    def get_fingerprint(self, raw_data: Dict[str, Any]) -> str:
        """Generate deduplication fingerprint."""
        device_ip = raw_data.get("device_ip", "")
        event_type = raw_data.get("event_type", "")
        
        fingerprint_str = f"axis:{device_ip}:{event_type}"
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()
    
    def is_clear_event(self, raw_data: Dict[str, Any]) -> bool:
        """Check if this is a clear event."""
        event_type = raw_data.get("event_type", "").lower()
        return event_type.endswith(("_restored", "_up", "_online", "_ok", "_normal", "_cleared"))
    
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
