"""
Siklu Radio Alert Normalizer

Database-driven normalizer for Siklu EtherHaul radio alerts.
All mappings come from severity_mappings and category_mappings tables.
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

from backend.core.models import NormalizedAlert, Severity, Category
from backend.utils.ip_utils import validate_device_ip
from backend.utils.db import db_query

logger = logging.getLogger(__name__)


# Fallback alert type definitions (used when no database mapping exists)
ALERT_TYPE_DEFAULTS = {
    "link_down": {"title": "Radio Link Down", "is_clear": False},
    "link_up": {"title": "Radio Link Up", "is_clear": True},
    "rsl_low": {"title": "RSL Low", "is_clear": False},
    "rsl_critical": {"title": "RSL Critical", "is_clear": False},
    "modulation_drop": {"title": "Modulation Reduced", "is_clear": False},
    "ethernet_down": {"title": "Ethernet Port Down", "is_clear": False},
    "ethernet_up": {"title": "Ethernet Port Up", "is_clear": True},
    "high_temperature": {"title": "High Temperature", "is_clear": False},
    "device_offline": {"title": "Radio Offline", "is_clear": False},
    "device_online": {"title": "Radio Online", "is_clear": True},
}


class SikluNormalizer:
    """
    Database-driven normalizer for Siklu radio link alerts.
    
    All mappings come from severity_mappings and category_mappings tables.
    """
    
    def __init__(self):
        self._severity_cache = {}
        self._category_cache = {}
        self._cache_loaded = False
    
    def _load_mappings(self):
        """Load mappings from database."""
        if self._cache_loaded:
            return
        
        try:
            # Load severity mappings
            severity_rows = db_query(
                "SELECT source_value, target_severity, enabled, description FROM severity_mappings WHERE connector_type = %s",
                ("siklu",)
            )
            for row in severity_rows:
                self._severity_cache[row['source_value']] = {
                    'severity': row['target_severity'],
                    'enabled': row['enabled'],
                    'description': row.get('description', '')
                }
            
            # Load category mappings
            category_rows = db_query(
                "SELECT source_value, target_category, enabled, description FROM category_mappings WHERE connector_type = %s",
                ("siklu",)
            )
            for row in category_rows:
                self._category_cache[row['source_value']] = {
                    'category': row['target_category'],
                    'enabled': row['enabled'],
                    'description': row.get('description', '')
                }
            
            logger.info(f"Loaded siklu mappings: {len(self._severity_cache)} severity, {len(self._category_cache)} category")
            self._cache_loaded = True
            
        except Exception as e:
            logger.error(f"Failed to load siklu mappings: {e}")
            self._cache_loaded = True  # Don't retry on every call
    
    def is_alert_enabled(self, alert_type: str) -> bool:
        """Check if this alert type is enabled in mappings."""
        self._load_mappings()
        
        severity_mapping = self._severity_cache.get(alert_type)
        if severity_mapping and not severity_mapping.get('enabled', True):
            return False
        
        return True
    
    @property
    def source_system(self) -> str:
        return "siklu"
    
    def normalize(self, raw_data: Dict[str, Any]) -> Optional[NormalizedAlert]:
        device_ip = raw_data.get("device_ip", "")
        device_name = raw_data.get("device_name", "")
        alert_type = raw_data.get("alert_type", "unknown")
        metrics = raw_data.get("metrics", {})
        timestamp = raw_data.get("timestamp")
        
        # Check if this alert type is enabled in mappings
        if not self.is_alert_enabled(alert_type):
            logger.debug(f"Skipping disabled Siklu alert type: {alert_type}")
            return None
        
        # Load mappings
        self._load_mappings()
        
        # Get severity from database mapping, fallback to warning
        severity_mapping = self._severity_cache.get(alert_type)
        if severity_mapping:
            severity = Severity(severity_mapping['severity'])
        else:
            severity = Severity.WARNING
        
        # Get category from database mapping, fallback to wireless
        category_mapping = self._category_cache.get(alert_type)
        if category_mapping:
            category = Category(category_mapping['category'])
        else:
            category = Category.WIRELESS
        
        # Get title and is_clear from defaults
        alert_defaults = ALERT_TYPE_DEFAULTS.get(alert_type, {
            "title": f"Siklu Alert - {alert_type}",
            "is_clear": False
        })
        
        base_title = alert_defaults.get("title", f"Siklu Alert - {alert_type}")
        title = f"{base_title} - {device_name}" if device_name else base_title
        message = self._build_message(alert_type, metrics, device_name, device_ip)
        occurred_at = self._parse_timestamp(timestamp)
        is_clear = alert_defaults.get("is_clear", False)
        
        # Clear events always have CLEAR severity
        if is_clear:
            severity = Severity.CLEAR
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=f"{device_ip}:{alert_type}",
            device_ip=validate_device_ip(device_ip, device_name),
            device_name=device_name or None,
            severity=severity,
            category=category,
            alert_type=f"siklu_{alert_type}",
            title=title,
            message=message,
            occurred_at=occurred_at,
            is_clear=is_clear,
            raw_data=raw_data,
        )
    
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        alert_type = raw_data.get("alert_type", "")
        self._load_mappings()
        severity_mapping = self._severity_cache.get(alert_type)
        if severity_mapping:
            return Severity(severity_mapping['severity'])
        return Severity.WARNING
    
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        alert_type = raw_data.get("alert_type", "")
        self._load_mappings()
        category_mapping = self._category_cache.get(alert_type)
        if category_mapping:
            return Category(category_mapping['category'])
        return Category.WIRELESS
    
    def get_fingerprint(self, raw_data: Dict[str, Any]) -> str:
        device_ip = raw_data.get("device_ip", "")
        alert_type = raw_data.get("alert_type", "")
        return hashlib.sha256(f"siklu:{device_ip}:{alert_type}".encode()).hexdigest()
    
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
        
        if metrics.get("rsl") is not None:
            lines.append(f"RSL: {metrics['rsl']} dBm")
        if metrics.get("modulation"):
            lines.append(f"Modulation: {metrics['modulation']}")
        if metrics.get("link_state"):
            lines.append(f"Link State: {metrics['link_state']}")
        if metrics.get("temperature") is not None:
            lines.append(f"Temperature: {metrics['temperature']}°C")
        if metrics.get("tx_power") is not None:
            lines.append(f"TX Power: {metrics['tx_power']} dBm")
        if metrics.get("peer_ip"):
            lines.append(f"Peer: {metrics['peer_ip']}")
        
        return " | ".join(lines) if lines else f"Siklu {alert_type} on {device_ip}"
    
    def _parse_timestamp(self, timestamp: Any) -> datetime:
        if not timestamp:
            return datetime.utcnow()
        if isinstance(timestamp, datetime):
            return timestamp
        try:
            return datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except ValueError:
            return datetime.utcnow()
