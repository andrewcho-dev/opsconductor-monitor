"""
MCP (Ciena) Alert Normalizer

Transforms MCP alarm data to standard NormalizedAlert format.
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

from backend.core.models import NormalizedAlert, Severity, Category

logger = logging.getLogger(__name__)


class MCPNormalizer:
    """
    Normalizer for Ciena MCP alarms.
    """
    
    # MCP severity mapping
    SEVERITY_MAP = {
        "CRITICAL": Severity.CRITICAL,
        "MAJOR": Severity.MAJOR,
        "MINOR": Severity.MINOR,
        "WARNING": Severity.WARNING,
        "INFO": Severity.INFO,
        "CLEARED": Severity.CLEAR,
        "CLEAR": Severity.CLEAR,
    }
    
    # MCP alarm category mapping
    CATEGORY_MAP = {
        "equipment": Category.NETWORK,
        "communication": Category.NETWORK,
        "processing": Category.COMPUTE,
        "environment": Category.ENVIRONMENT,
        "power": Category.POWER,
        "security": Category.SECURITY,
        "qos": Category.NETWORK,
    }
    
    @property
    def source_system(self) -> str:
        return "mcp"
    
    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedAlert:
        """
        Transform MCP alarm to NormalizedAlert.
        """
        # Extract fields
        alarm_id = str(raw_data.get("id", "") or raw_data.get("alarmId", ""))
        severity_str = str(raw_data.get("severity", "") or raw_data.get("perceivedSeverity", "")).upper()
        
        # Device info
        device_name = raw_data.get("sourceName") or raw_data.get("networkConstructName", "")
        device_ip = raw_data.get("sourceIp") or raw_data.get("managementIp", "")
        
        # Alarm details
        alarm_type = raw_data.get("alarmType") or raw_data.get("probableCause", "unknown")
        description = raw_data.get("description") or raw_data.get("additionalText", "")
        
        # Timestamps
        raised_time = raw_data.get("raisedTime") or raw_data.get("eventTime")
        occurred_at = self._parse_datetime(raised_time)
        
        # Determine severity
        severity = self.get_severity(raw_data)
        
        # Determine category
        category = self.get_category(raw_data)
        
        # Build title
        title = f"{alarm_type} - {device_name}" if device_name else alarm_type
        
        # Is this a clear event?
        is_clear = severity_str in ("CLEARED", "CLEAR") or severity == Severity.CLEAR
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=alarm_id,
            device_ip=device_ip if device_ip else None,
            device_name=device_name if device_name else None,
            severity=severity,
            category=category,
            alert_type=f"mcp_{alarm_type.lower().replace(' ', '_')}",
            title=title,
            message=description,
            occurred_at=occurred_at,
            is_clear=is_clear,
            raw_data=raw_data,
        )
    
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        """Determine severity from MCP alarm."""
        severity_str = str(raw_data.get("severity", "") or raw_data.get("perceivedSeverity", "")).upper()
        return self.SEVERITY_MAP.get(severity_str, Severity.WARNING)
    
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        """Determine category from MCP alarm type."""
        alarm_category = str(raw_data.get("category", "") or raw_data.get("alarmCategory", "")).lower()
        alarm_type = str(raw_data.get("alarmType", "") or raw_data.get("probableCause", "")).lower()
        
        # Check category first
        for keyword, category in self.CATEGORY_MAP.items():
            if keyword in alarm_category:
                return category
        
        # Check alarm type
        for keyword, category in self.CATEGORY_MAP.items():
            if keyword in alarm_type:
                return category
        
        # Default to network for MCP
        return Category.NETWORK
    
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
