"""
Milestone VMS Alert Normalizer

Transforms Milestone XProtect event data to standard NormalizedAlert format.
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


class MilestoneNormalizer:
    """
    Database-driven normalizer for Milestone XProtect VMS events.
    
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
                ("milestone",)
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
                ("milestone",)
            )
            for row in category_rows:
                self._category_cache[row["source_value"]] = {
                    "category": row["target_category"],
                    "enabled": row["enabled"],
                    "description": row.get("description", "")
                }
            
            self._cache_loaded = True
            logger.info(f"Loaded {len(self._severity_cache)} severity and {len(self._category_cache)} category mappings for milestone")
            
        except Exception as e:
            logger.error(f"Failed to load milestone mappings: {e}")
            self._cache_loaded = True
    
    def is_event_enabled(self, event_type: str) -> bool:
        """Check if this event type is enabled in mappings.
        
        Returns False if:
        - Event type is not in any mapping (unknown events are ignored)
        - Event type is explicitly disabled in mappings
        """
        self._load_mappings()
        
        severity_mapping = self._severity_cache.get(event_type)
        category_mapping = self._category_cache.get(event_type)
        
        # If not in ANY mapping, treat as disabled (unknown event type)
        if not severity_mapping and not category_mapping:
            logger.debug(f"Event type '{event_type}' not in mappings - ignoring")
            return False
        
        # Check if explicitly disabled
        if severity_mapping and not severity_mapping.get("enabled", True):
            return False
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
        
        return Category.VIDEO
    
    @property
    def source_system(self) -> str:
        return "milestone"
    
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
        
        # Is this a clear event? (events that resolve previous alerts)
        # Note: recording_stopped is NOT a clear - it's an alert that recording has stopped
        # motion_stopped IS a clear - it clears motion_started
        is_clear = event_type in (
            "camera_online", "server_started", "backup_completed", 
            "failover_deactivated", "motion_stopped"
        )
        
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
    
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        """Determine severity from database mapping."""
        event_type = raw_data.get("event_type", "").lower().replace(" ", "_")
        return self._get_severity(event_type)
    
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        """Determine category from database mapping."""
        event_type = raw_data.get("event_type", "").lower().replace(" ", "_")
        return self._get_category(event_type)
    
    def get_fingerprint(self, raw_data: Dict[str, Any]) -> str:
        """Generate deduplication fingerprint."""
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
