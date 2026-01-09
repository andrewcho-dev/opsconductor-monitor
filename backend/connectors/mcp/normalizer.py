"""
MCP (Ciena) Alert Normalizer

Transforms MCP alarm data to standard NormalizedAlert format.
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


class MCPNormalizer:
    """
    Database-driven normalizer for Ciena MCP alarms.
    
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
                ("mcp",)
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
                ("mcp",)
            )
            for row in category_rows:
                self._category_cache[row["source_value"]] = {
                    "category": row["target_category"],
                    "enabled": row["enabled"],
                    "description": row.get("description", "")
                }
            
            self._cache_loaded = True
            logger.info(f"Loaded {len(self._severity_cache)} severity and {len(self._category_cache)} category mappings for mcp")
            
        except Exception as e:
            logger.error(f"Failed to load mcp mappings: {e}")
            self._cache_loaded = True
    
    def is_event_enabled(self, alarm_type: str) -> bool:
        """Check if this alarm type is enabled in mappings.
        
        Returns False if:
        - Alarm type is not in any mapping (unknown events are ignored)
        - Alarm type is explicitly disabled in mappings
        """
        self._load_mappings()
        
        severity_mapping = self._severity_cache.get(alarm_type)
        category_mapping = self._category_cache.get(alarm_type)
        
        # If not in ANY mapping, treat as disabled (unknown event type)
        if not severity_mapping and not category_mapping:
            logger.debug(f"Alarm type '{alarm_type}' not in mappings - ignoring")
            return False
        
        # Check if explicitly disabled
        if severity_mapping and not severity_mapping.get("enabled", True):
            return False
        if category_mapping and not category_mapping.get("enabled", True):
            return False
        
        return True
    
    def _get_severity(self, alarm_type: str) -> Severity:
        """Get severity from database mapping."""
        self._load_mappings()
        
        mapping = self._severity_cache.get(alarm_type)
        if mapping:
            try:
                return Severity(mapping["severity"])
            except ValueError:
                pass
        
        return Severity.WARNING
    
    def _get_category(self, alarm_type: str) -> Category:
        """Get category from database mapping."""
        self._load_mappings()
        
        mapping = self._category_cache.get(alarm_type)
        if mapping:
            try:
                return Category(mapping["category"])
            except ValueError:
                pass
        
        return Category.NETWORK
    
    @property
    def source_system(self) -> str:
        return "mcp"
    
    def normalize(self, raw_data: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """
        Transform MCP alarm to NormalizedAlert.
        
        Returns None if the alarm type is disabled or not in mappings.
        """
        # Extract fields
        alarm_id = str(raw_data.get("id", "") or raw_data.get("alarmId", ""))
        severity_str = str(raw_data.get("severity", "") or raw_data.get("perceivedSeverity", "")).upper()
        
        # Device info
        device_name = raw_data.get("sourceName") or raw_data.get("networkConstructName", "")
        device_ip = raw_data.get("sourceIp") or raw_data.get("managementIp", "")
        
        # Alarm details
        alarm_type = raw_data.get("alarmType") or raw_data.get("probableCause", "unknown")
        alarm_type_normalized = alarm_type.lower().replace(' ', '_')
        description = raw_data.get("description") or raw_data.get("additionalText", "")
        
        # Check if alarm type is enabled in mappings
        if not self.is_event_enabled(alarm_type_normalized):
            logger.debug(f"Skipping disabled MCP alarm type: {alarm_type}")
            return None
        
        # Validate device_ip
        try:
            validated_ip = validate_device_ip(device_ip, device_name)
        except ValueError as e:
            logger.warning(f"Skipping MCP alert - no valid device_ip: {e}")
            return None
        
        # Timestamps
        raised_time = raw_data.get("raisedTime") or raw_data.get("eventTime")
        occurred_at = self._parse_datetime(raised_time)
        
        # Get severity and category from database mappings
        severity = self._get_severity(alarm_type_normalized)
        category = self._get_category(alarm_type_normalized)
        
        # Build title
        title = f"{alarm_type} - {device_name}" if device_name else alarm_type
        
        # Build message - ensure it's never empty
        message = self._build_message(description, alarm_type, device_name, validated_ip)
        
        # Is this a clear event?
        is_clear = severity_str in ("CLEARED", "CLEAR") or severity == Severity.CLEAR
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=alarm_id,
            device_ip=validated_ip,
            device_name=device_name or None,
            severity=severity,
            category=category,
            alert_type=f"mcp_{alarm_type_normalized}",
            title=title,
            message=message,
            occurred_at=occurred_at,
            is_clear=is_clear,
            raw_data=raw_data,
        )
    
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        """Determine severity from database mapping."""
        alarm_type = raw_data.get("alarmType") or raw_data.get("probableCause", "unknown")
        return self._get_severity(alarm_type.lower().replace(' ', '_'))
    
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        """Determine category from database mapping."""
        alarm_type = raw_data.get("alarmType") or raw_data.get("probableCause", "unknown")
        return self._get_category(alarm_type.lower().replace(' ', '_'))
    
    def get_fingerprint(self, raw_data: Dict[str, Any]) -> str:
        """Generate deduplication fingerprint."""
        alarm_id = str(raw_data.get("id", "") or raw_data.get("alarmId", ""))
        device = raw_data.get("sourceName") or raw_data.get("sourceIp", "")
        
        fingerprint_str = f"mcp:{alarm_id}:{device}"
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()
    
    def is_clear_event(self, raw_data: Dict[str, Any]) -> bool:
        """Check if this is a clear event."""
        severity_str = str(raw_data.get("severity", "") or raw_data.get("perceivedSeverity", "")).upper()
        return severity_str in ("CLEARED", "CLEAR")
    
    def _build_message(self, description: str, alarm_type: str, device_name: str, device_ip: str) -> str:
        """Build message - ensure it's never empty."""
        lines = []
        
        # Always include device info
        if device_name:
            lines.append(f"Device: {device_name}")
        elif device_ip:
            lines.append(f"Device: {device_ip}")
        
        # Alarm type
        if alarm_type:
            lines.append(f"Alarm: {alarm_type}")
        
        # Description
        if description:
            lines.append(description)
        
        return " | ".join(lines) if lines else f"MCP alarm {alarm_type} on {device_ip}"
    
    def _parse_datetime(self, datetime_str: str) -> datetime:
        """Parse MCP datetime string."""
        if not datetime_str:
            return datetime.utcnow()
        
        # MCP typically uses ISO format
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue
        
        return datetime.utcnow()
