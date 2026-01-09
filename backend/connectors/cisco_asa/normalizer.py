"""
Cisco ASA Normalizer

Converts Cisco ASA events to normalized alerts.
Uses database mappings for severity and category - NO HARDCODED VALUES.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from backend.connectors.base import BaseNormalizer
from backend.core.models import NormalizedAlert, Severity, Category
from backend.utils.ip_utils import validate_device_ip
from backend.utils.db import db_query

logger = logging.getLogger(__name__)


class CiscoASANormalizer(BaseNormalizer):
    """
    Database-driven normalizer for Cisco ASA events.
    
    All mappings come from severity_mappings and category_mappings tables.
    """
    
    def __init__(self):
        super().__init__()
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
                ("cisco_asa",)
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
                ("cisco_asa",)
            )
            for row in category_rows:
                self._category_cache[row["source_value"]] = {
                    "category": row["target_category"],
                    "enabled": row["enabled"],
                    "description": row.get("description", "")
                }
            
            self._cache_loaded = True
            logger.info(f"Loaded {len(self._severity_cache)} severity and {len(self._category_cache)} category mappings for cisco_asa")
            
        except Exception as e:
            logger.error(f"Failed to load cisco_asa mappings: {e}")
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
        return "cisco_asa"
    
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        event_type = raw_data.get("event_type", "")
        return self._get_severity(event_type)
    
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        event_type = raw_data.get("event_type", "")
        return self._get_category(event_type)
    
    def normalize(self, raw_event: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """Convert raw ASA event to normalized alert.
        
        Returns None if the event type is disabled or not in mappings.
        """
        event_type = raw_event.get("event_type", "")
        
        # Check if event type is enabled in mappings
        if not self.is_event_enabled(event_type):
            logger.debug(f"Skipping disabled Cisco ASA event type: {event_type}")
            return None
        
        # Validate device IP
        try:
            device_ip = validate_device_ip(
                raw_event.get("device_ip"),
                raw_event.get("device_name")
            )
        except ValueError as e:
            logger.warning(f"Invalid device IP for Cisco ASA alert: {e}")
            return None
        
        # Get severity and category from database mappings
        severity = self._get_severity(event_type)
        category = self._get_category(event_type)
        
        # Get description from mapping for title
        mapping = self._severity_cache.get(event_type, {})
        title = mapping.get("description", f"Cisco ASA {event_type.replace('_', ' ').title()}")
        
        # Build message
        message = f"Device: {device_ip} | Event: {event_type.replace('_', ' ')}"
        if raw_event.get("peer_ip"):
            message += f" | Peer: {raw_event['peer_ip']}"
        if raw_event.get("interface"):
            message += f" | Interface: {raw_event['interface']}"
        
        # Generate unique source alert ID
        source_alert_id = f"cisco_asa_{event_type}_{device_ip}"
        if "peer_ip" in raw_event:
            source_alert_id += f"_{raw_event['peer_ip']}"
        if "interface" in raw_event:
            source_alert_id += f"_{raw_event['interface']}"
        
        # Parse timestamp
        timestamp = raw_event.get("timestamp")
        if isinstance(timestamp, str):
            try:
                occurred_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                occurred_at = datetime.utcnow()
        else:
            occurred_at = datetime.utcnow()
        
        return NormalizedAlert(
            source_system="cisco_asa",
            source_alert_id=source_alert_id,
            device_ip=device_ip,
            device_name=raw_event.get("device_name", device_ip),
            severity=severity,
            category=category,
            alert_type=f"cisco_asa_{event_type}",
            title=title,
            message=message,
            occurred_at=occurred_at,
            raw_data=raw_event,
        )
