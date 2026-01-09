"""
Ubiquiti UISP Alert Normalizer

Transforms Ubiquiti UISP data to standard NormalizedAlert format.
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


class UbiquitiNormalizer:
    """
    Database-driven normalizer for Ubiquiti UISP alerts.
    
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
                ("ubiquiti",)
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
                ("ubiquiti",)
            )
            for row in category_rows:
                self._category_cache[row["source_value"]] = {
                    "category": row["target_category"],
                    "enabled": row["enabled"],
                    "description": row.get("description", "")
                }
            
            self._cache_loaded = True
            logger.info(f"Loaded {len(self._severity_cache)} severity and {len(self._category_cache)} category mappings for ubiquiti")
            
        except Exception as e:
            logger.error(f"Failed to load ubiquiti mappings: {e}")
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
        
        return Category.NETWORK
    
    @property
    def source_system(self) -> str:
        return "ubiquiti"
    
    def normalize(self, raw_data: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """Transform Ubiquiti UISP data to NormalizedAlert.
        
        Returns None if the event type is disabled or not in mappings.
        """
        device_ip = raw_data.get("device_ip", "")
        device_name = raw_data.get("device_name", "")
        alert_type = raw_data.get("alert_type", "unknown")
        metrics = raw_data.get("metrics", {})
        timestamp = raw_data.get("timestamp")
        
        # Check if event type is enabled in mappings
        if not self.is_event_enabled(alert_type):
            logger.debug(f"Skipping disabled Ubiquiti event type: {alert_type}")
            return None
        
        # Validate device_ip
        try:
            validated_ip = validate_device_ip(device_ip, device_name)
        except ValueError as e:
            logger.warning(f"Skipping Ubiquiti alert - no valid device_ip: {e}")
            return None
        
        # Get severity and category from database mappings
        severity = self._get_severity(alert_type)
        category = self._get_category(alert_type)
        
        # Get description from mapping
        mapping = self._severity_cache.get(alert_type, {})
        description = mapping.get("description", "")
        
        # Build title
        title = f"Ubiquiti {alert_type.replace('_', ' ').title()} - {device_name}" if device_name else f"Ubiquiti {alert_type.replace('_', ' ').title()}"
        
        message = self._build_message(alert_type, metrics, device_name, validated_ip)
        occurred_at = self._parse_timestamp(timestamp)
        
        # Is this a clear event?
        is_clear = severity == Severity.CLEAR or alert_type in ("device_online", "interface_up", "outage_ended")
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=f"{validated_ip}:{alert_type}",
            device_ip=validated_ip,
            device_name=device_name or None,
            severity=severity,
            category=category,
            alert_type=f"ubiquiti_{alert_type}",
            title=title,
            message=message,
            occurred_at=occurred_at,
            is_clear=is_clear,
            raw_data=raw_data,
        )
    
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        alert_type = raw_data.get("alert_type", "")
        return self.ALERT_TYPES.get(alert_type, {}).get("severity", Severity.WARNING)
    
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        alert_type = raw_data.get("alert_type", "")
        return self.ALERT_TYPES.get(alert_type, {}).get("category", Category.NETWORK)
    
    def get_fingerprint(self, raw_data: Dict[str, Any]) -> str:
        device_ip = raw_data.get("device_ip", "")
        alert_type = raw_data.get("alert_type", "")
        return hashlib.sha256(f"ubiquiti:{device_ip}:{alert_type}".encode()).hexdigest()
    
    def _build_message(self, alert_type: str, metrics: Dict, device_name: str = "", device_ip: str = "") -> str:
        lines = []
        
        # Always include device info
        if device_name:
            lines.append(f"Device: {device_name}")
        elif device_ip:
            lines.append(f"Device: {device_ip}")
        
        # Alert type
        if alert_type:
            lines.append(f"Alert: {alert_type.replace('_', ' ')}")
        
        if metrics.get("cpu_percent") is not None:
            lines.append(f"CPU: {metrics['cpu_percent']}%")
        if metrics.get("memory_percent") is not None:
            lines.append(f"Memory: {metrics['memory_percent']}%")
        if metrics.get("uptime") is not None:
            lines.append(f"Uptime: {metrics['uptime']}")
        if metrics.get("signal") is not None:
            lines.append(f"Signal: {metrics['signal']} dBm")
        if metrics.get("interface"):
            lines.append(f"Interface: {metrics['interface']}")
        if metrics.get("firmware"):
            lines.append(f"Firmware: {metrics['firmware']}")
        
        return " | ".join(lines) if lines else f"Ubiquiti {alert_type} on {device_ip}"
    
    def _parse_timestamp(self, timestamp: Any) -> datetime:
        if not timestamp:
            return datetime.utcnow()
        if isinstance(timestamp, datetime):
            return timestamp
        try:
            return datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except ValueError:
            return datetime.utcnow()
