"""
MCP (Ciena) Alert Normalizer

Transforms MCP alarm data to standard NormalizedAlert format.
Uses database mappings for severity and category via BaseNormalizer.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from backend.connectors.base import BaseNormalizer
from backend.core.models import NormalizedAlert, Severity, Category
from backend.utils.ip_utils import validate_device_ip

logger = logging.getLogger(__name__)


class MCPNormalizer(BaseNormalizer):
    """
    Database-driven normalizer for Ciena MCP alarms.
    
    Extends BaseNormalizer for standard mapping methods.
    """
    
    connector_type = "mcp"
    default_category = Category.NETWORK
    
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
