"""
PRTG Alert Normalizer

Transforms raw PRTG alert data to standard NormalizedAlert format.
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

from core.models import NormalizedAlert, Severity, Category

logger = logging.getLogger(__name__)


class PRTGNormalizer:
    """
    Normalizer for PRTG alerts.
    
    Handles both webhook payloads and polled sensor data.
    """
    
    # PRTG status codes to severity mapping
    SEVERITY_MAP = {
        # Status ID -> Severity
        1: Severity.WARNING,    # Unknown
        2: Severity.INFO,       # Scanning
        3: Severity.CLEAR,      # Up
        4: Severity.WARNING,    # Warning
        5: Severity.CRITICAL,   # Down
        6: Severity.MAJOR,      # No Probe
        7: Severity.INFO,       # Paused by User
        8: Severity.INFO,       # Paused by Dependency
        9: Severity.INFO,       # Paused by Schedule
        10: Severity.WARNING,   # Unusual
        11: Severity.WARNING,   # Not Licensed
        12: Severity.INFO,      # Paused Until
        13: Severity.MAJOR,     # Down (Acknowledged)
        14: Severity.MAJOR,     # Down (Partial)
    }
    
    # PRTG status text to severity mapping (for webhooks)
    SEVERITY_TEXT_MAP = {
        "up": Severity.CLEAR,
        "down": Severity.CRITICAL,
        "warning": Severity.WARNING,
        "unusual": Severity.WARNING,
        "paused": Severity.INFO,
        "unknown": Severity.WARNING,
    }
    
    # Sensor type to category mapping
    CATEGORY_MAP = {
        "ping": Category.NETWORK,
        "snmp": Category.NETWORK,
        "bandwidth": Category.NETWORK,
        "traffic": Category.NETWORK,
        "port": Category.NETWORK,
        "cpu": Category.COMPUTE,
        "memory": Category.COMPUTE,
        "disk": Category.STORAGE,
        "http": Category.APPLICATION,
        "ssl": Category.SECURITY,
        "wmi": Category.COMPUTE,
        "vmware": Category.COMPUTE,
        "ups": Category.POWER,
        "temperature": Category.ENVIRONMENT,
        "humidity": Category.ENVIRONMENT,
    }
    
    @property
    def source_system(self) -> str:
        return "prtg"
    
    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedAlert:
        """
        Transform PRTG data to NormalizedAlert.
        
        Handles both webhook format and polled sensor format.
        """
        # Determine if this is webhook or poll data
        if "sensorid" in raw_data:
            return self._normalize_webhook(raw_data)
        elif "objid" in raw_data:
            return self._normalize_poll(raw_data)
        else:
            raise ValueError("Unknown PRTG data format")
    
    def _normalize_webhook(self, raw: Dict[str, Any]) -> NormalizedAlert:
        """Normalize webhook payload."""
        # Extract fields
        sensor_id = str(raw.get("sensorid", ""))
        device_id = str(raw.get("deviceid", ""))
        device_name = raw.get("device", "")
        sensor_name = raw.get("sensor") or raw.get("name", "")
        status = raw.get("status", "").lower()
        status_id = raw.get("statusid")
        message = raw.get("message", "")
        host = raw.get("host", "")
        datetime_str = raw.get("datetime", "")
        
        # Parse occurred_at
        occurred_at = self._parse_datetime(datetime_str)
        
        # Determine severity
        severity = self.get_severity(raw)
        
        # Determine category
        category = self.get_category(raw)
        
        # Build alert type
        alert_type = self._build_alert_type(sensor_name, status)
        
        # Build title
        title = f"{sensor_name} - {status.title()}" if sensor_name else f"PRTG Alert - {status.title()}"
        
        # Is this a clear event?
        is_clear = status == "up" or severity == Severity.CLEAR
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=sensor_id,
            device_ip=host if self._is_ip(host) else None,
            device_name=device_name or host,
            severity=severity,
            category=category,
            alert_type=alert_type,
            title=title,
            message=message,
            occurred_at=occurred_at,
            is_clear=is_clear,
            raw_data=raw,
        )
    
    def _normalize_poll(self, raw: Dict[str, Any]) -> NormalizedAlert:
        """Normalize polled sensor data."""
        # Extract fields
        sensor_id = str(raw.get("objid", ""))
        device_name = raw.get("device", "")
        sensor_name = raw.get("sensor", "")
        status_raw = raw.get("status_raw") or raw.get("status")
        message = raw.get("message", "")
        host = raw.get("host", "")
        
        # Status could be int or string
        if isinstance(status_raw, int):
            status_text = self._status_code_to_text(status_raw)
        else:
            status_text = str(status_raw).lower()
        
        # Determine severity
        severity = self.get_severity(raw)
        
        # Determine category
        category = self.get_category(raw)
        
        # Build alert type
        alert_type = self._build_alert_type(sensor_name, status_text)
        
        # Build title
        title = f"{sensor_name} - {status_text.title()}" if sensor_name else f"PRTG Alert"
        
        # Is this a clear event?
        is_clear = status_text == "up" or severity == Severity.CLEAR
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=sensor_id,
            device_ip=host if self._is_ip(host) else None,
            device_name=device_name or host,
            severity=severity,
            category=category,
            alert_type=alert_type,
            title=title,
            message=message,
            occurred_at=datetime.utcnow(),
            is_clear=is_clear,
            raw_data=raw,
        )
    
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        """Determine severity from PRTG data."""
        # Try status ID first
        status_id = raw_data.get("statusid") or raw_data.get("status_raw")
        if isinstance(status_id, int) and status_id in self.SEVERITY_MAP:
            return self.SEVERITY_MAP[status_id]
        
        # Try status text
        status_text = str(raw_data.get("status", "")).lower()
        if status_text in self.SEVERITY_TEXT_MAP:
            return self.SEVERITY_TEXT_MAP[status_text]
        
        # Default
        return Severity.WARNING
    
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        """Determine category from PRTG sensor type."""
        sensor_type = str(raw_data.get("type", "") or raw_data.get("sensor", "")).lower()
        
        for keyword, category in self.CATEGORY_MAP.items():
            if keyword in sensor_type:
                return category
        
        # Default to network for PRTG
        return Category.NETWORK
    
    def get_fingerprint(self, raw_data: Dict[str, Any]) -> str:
        """Generate deduplication fingerprint."""
        sensor_id = str(raw_data.get("sensorid") or raw_data.get("objid", ""))
        device = raw_data.get("device") or raw_data.get("host", "")
        
        fingerprint_str = f"prtg:{sensor_id}:{device}"
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()
    
    def is_clear_event(self, raw_data: Dict[str, Any]) -> bool:
        """Check if this is a recovery/clear event."""
        status = str(raw_data.get("status", "")).lower()
        status_id = raw_data.get("statusid") or raw_data.get("status_raw")
        
        return status == "up" or status_id == 3
    
    def _parse_datetime(self, datetime_str: str) -> datetime:
        """Parse PRTG datetime string."""
        if not datetime_str:
            return datetime.utcnow()
        
        # Try various PRTG formats
        formats = [
            "%m/%d/%Y %I:%M:%S %p",  # US format
            "%d/%m/%Y %H:%M:%S",     # EU format
            "%Y-%m-%d %H:%M:%S",     # ISO format
            "%Y/%m/%d %H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue
        
        return datetime.utcnow()
    
    def _status_code_to_text(self, status_id: int) -> str:
        """Convert status ID to text."""
        status_map = {
            1: "unknown",
            2: "scanning",
            3: "up",
            4: "warning",
            5: "down",
            6: "no_probe",
            7: "paused",
            8: "paused",
            9: "paused",
            10: "unusual",
            11: "not_licensed",
            12: "paused",
            13: "down_acknowledged",
            14: "down_partial",
        }
        return status_map.get(status_id, "unknown")
    
    def _build_alert_type(self, sensor_name: str, status: str) -> str:
        """Build alert type string."""
        # Normalize sensor name
        sensor_type = sensor_name.lower().replace(" ", "_") if sensor_name else "sensor"
        
        # Remove special characters
        sensor_type = "".join(c for c in sensor_type if c.isalnum() or c == "_")
        
        return f"prtg_{sensor_type}_{status}"
    
    def _is_ip(self, value: str) -> bool:
        """Check if value looks like an IP address."""
        if not value:
            return False
        
        parts = value.split(".")
        if len(parts) != 4:
            return False
        
        try:
            return all(0 <= int(p) <= 255 for p in parts)
        except ValueError:
            return False
