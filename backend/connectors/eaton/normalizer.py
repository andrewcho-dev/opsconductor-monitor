"""
Eaton UPS Alert Normalizer

Transforms Eaton UPS SNMP data to standard NormalizedAlert format.
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


class EatonNormalizer:
    """
    Database-driven normalizer for Eaton UPS alerts.
    
    All mappings come from severity_mappings and category_mappings tables.
    """
    
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
                ("eaton",)
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
                ("eaton",)
            )
            for row in category_rows:
                self._category_cache[row["source_value"]] = {
                    "category": row["target_category"],
                    "enabled": row["enabled"],
                    "description": row.get("description", "")
                }
            
            self._cache_loaded = True
            logger.info(f"Loaded {len(self._severity_cache)} severity and {len(self._category_cache)} category mappings for eaton")
            
        except Exception as e:
            logger.error(f"Failed to load eaton mappings: {e}")
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
        
        return Category.POWER
    
    @property
    def source_system(self) -> str:
        return "eaton"
    
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
        
        # Is this a clear event?
        is_clear = severity == Severity.CLEAR or alarm_type in ("utility_restored", "normal")
        
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
    
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        """Determine severity from database mapping."""
        alarm_type = raw_data.get("alarm_type", "unknown")
        return self._get_severity(alarm_type)
    
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        """Determine category from database mapping."""
        alarm_type = raw_data.get("alarm_type", "unknown")
        return self._get_category(alarm_type)
    
    def get_fingerprint(self, raw_data: Dict[str, Any]) -> str:
        """Generate deduplication fingerprint."""
        device_ip = raw_data.get("device_ip", "")
        alarm_type = raw_data.get("alarm_type", "")
        
        fingerprint_str = f"eaton:{device_ip}:{alarm_type}"
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()
    
    def is_clear_event(self, raw_data: Dict[str, Any]) -> bool:
        """Check if this is a clear event."""
        alarm_type = raw_data.get("alarm_type", "")
        severity = self._get_severity(alarm_type)
        return severity == Severity.CLEAR or alarm_type in ("utility_restored", "normal")
    
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
