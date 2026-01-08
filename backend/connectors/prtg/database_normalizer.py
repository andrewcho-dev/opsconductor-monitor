"""
PRTG Database-Driven Normalizer

Uses database mappings for configurable alert normalization.
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

from backend.core.models import NormalizedAlert, Severity, Category
from backend.utils.db import db_query
from backend.utils.ip_utils import validate_device_ip

logger = logging.getLogger(__name__)


class PRTGDatabaseNormalizer:
    """
    Database-driven normalizer for PRTG alerts.
    
    All mappings (severity, category, priority) are read from database tables
    for full configurability.
    """
    
    def __init__(self):
        # Cache mappings in memory for performance
        self._severity_mappings = {}
        self._category_mappings = {}
        self._priority_rules = {}
        self._alert_type_templates = {}
        self._deduplication_rules = {}
        self._last_cache_update = None
        
        # Load initial mappings
        self._load_mappings()
    
    @property
    def source_system(self) -> str:
        return "prtg"
    
    def _load_mappings(self) -> None:
        """Load all mappings from database."""
        try:
            # Load severity mappings
            self._severity_mappings = {}
            rows = db_query("""
                SELECT source_value, source_field, target_severity, priority
                FROM severity_mappings
                WHERE connector_type = 'prtg' AND enabled = true
                ORDER BY priority DESC
            """)
            for row in rows:
                key = f"{row['source_field']}:{row['source_value']}"
                self._severity_mappings[key] = row['target_severity']
            
            # Load category mappings
            self._category_mappings = {}
            rows = db_query("""
                SELECT source_value, source_field, target_category, priority
                FROM category_mappings
                WHERE connector_type = 'prtg' AND enabled = true
                ORDER BY priority DESC
            """)
            for row in rows:
                key = f"{row['source_field']}:{row['source_value']}"
                self._category_mappings[key] = row['target_category']
            
            # Load priority rules
            self._priority_rules = {}
            rows = db_query("""
                SELECT category, severity, impact, urgency, priority
                FROM priority_rules
                WHERE connector_type = 'prtg' AND enabled = true
            """)
            for row in rows:
                key = f"{row['category']}:{row['severity']}"
                self._priority_rules[key] = {
                    'impact': row['impact'],
                    'urgency': row['urgency'],
                    'priority': row['priority']
                }
            
            # Load alert type templates
            self._alert_type_templates = {}
            rows = db_query("""
                SELECT pattern, template
                FROM alert_type_templates
                WHERE connector_type = 'prtg' AND enabled = true
            """)
            for row in rows:
                self._alert_type_templates[row['pattern']] = row['template']
            
            # Load deduplication rules
            rows = db_query("""
                SELECT fingerprint_fields, dedup_window_minutes
                FROM deduplication_rules
                WHERE connector_type = 'prtg' AND enabled = true
                LIMIT 1
            """)
            if rows:
                self._deduplication_rules = {
                    'fields': rows[0]['fingerprint_fields'],
                    'window_minutes': rows[0]['dedup_window_minutes']
                }
            
            self._last_cache_update = datetime.utcnow()
            logger.info(f"Loaded PRTG mappings: {len(self._severity_mappings)} severity, "
                       f"{len(self._category_mappings)} category, {len(self._priority_rules)} priority")
            
        except Exception as e:
            logger.error(f"Failed to load PRTG mappings: {e}")
            # Set fallback defaults
            self._set_fallback_mappings()
    
    def _set_fallback_mappings(self) -> None:
        """Set hardcoded fallback mappings if database fails."""
        logger.warning("Using fallback PRTG mappings")
        
        # Basic severity mappings
        self._severity_mappings = {
            "status:down": "critical",
            "status:warning": "warning",
            "status:up": "clear",
            "status:5": "critical",  # Down status ID
            "status:4": "warning",  # Warning status ID
            "status:3": "clear",    # Up status ID
        }
        
        # Basic category mappings
        self._category_mappings = {
            "type:ping": "network",
            "type:cpu": "compute",
            "type:memory": "compute",
            "type:disk": "storage",
        }
        
        # Default deduplication
        self._deduplication_rules = {
            'fields': ['sensorid', 'device'],
            'window_minutes': 300
        }
    
    def normalize(self, raw_data: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """
        Transform PRTG data to NormalizedAlert using database mappings.
        
        Returns None for paused sensors (they shouldn't create new alerts).
        """
        # Check if cache needs refresh (every 5 minutes)
        if (not self._last_cache_update or 
            (datetime.utcnow() - self._last_cache_update).total_seconds() > 300):
            self._load_mappings()
        
        # Determine if this is webhook or poll data
        if "sensorid" in raw_data:
            return self._normalize_webhook(raw_data)
        elif "objid" in raw_data:
            return self._normalize_poll(raw_data)
        else:
            raise ValueError("Unknown PRTG data format")
    
    def _normalize_webhook(self, raw: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """Normalize webhook payload using database mappings. Returns None if no valid device_ip."""
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
        
        # Validate device_ip early - skip if we can't determine IP
        try:
            device_ip = validate_device_ip(host, device_name)
        except ValueError as e:
            logger.warning(f"Skipping PRTG alert - no valid device_ip: {e}")
            return None
        
        # Parse occurred_at
        occurred_at = self._parse_datetime(datetime_str)
        
        # Determine severity from database mappings
        severity = self.get_severity(raw)
        
        # Determine category from database mappings
        category = self.get_category(raw)
        
        # Build alert type (without status for consistent fingerprinting)
        alert_type = self._build_alert_type(sensor_name, "")
        
        # Build title (without status - status is tracked separately)
        title = sensor_name if sensor_name else "PRTG Alert"
        
        # Is this a clear event?
        is_clear = status == "up" or severity == Severity.CLEAR
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=sensor_id,
            device_ip=device_ip,
            device_name=device_name or None,
            severity=severity,
            category=category,
            alert_type=alert_type,
            title=title,
            message=message,
            occurred_at=occurred_at,
            is_clear=is_clear,
            raw_data=raw,
        )
    
    def _normalize_poll(self, raw: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """Normalize polled sensor data using database mappings. Returns None if no valid device_ip."""
        # Extract fields
        sensor_id = str(raw.get("objid", ""))
        device_name = raw.get("device", "")
        sensor_name = raw.get("sensor", "")
        status_raw = raw.get("status_raw") or raw.get("status")
        message = raw.get("message", "")
        host = raw.get("host", "")
        
        # Validate device_ip early - skip if we can't determine IP
        try:
            device_ip = validate_device_ip(host, device_name)
        except ValueError as e:
            logger.warning(f"Skipping PRTG poll alert - no valid device_ip: {e}")
            return None
        
        # Status could be int or string
        if isinstance(status_raw, int):
            status_text = self._status_code_to_text(status_raw)
            status_id = status_raw
        else:
            status_text = str(status_raw).lower()
            status_id = None
        
        # Get source status for display (human-readable)
        source_status = self._get_source_status_display(status_id, status_text)
        
        # Determine OpsConductor status based on PRTG status
        ops_status = self._get_opsconductor_status(status_id, status_text)
        
        # Determine severity
        severity = self.get_severity(raw)
        
        # Determine category
        category = self.get_category(raw)
        
        # Build alert type (without status for consistent fingerprinting)
        alert_type = self._build_alert_type(sensor_name, "")
        
        # Build title (without status - status is tracked separately)
        title = sensor_name if sensor_name else "PRTG Alert"
        
        # Is this a clear event?
        is_clear = status_text == "up" or severity == Severity.CLEAR
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=sensor_id,
            device_ip=device_ip,
            device_name=device_name or None,
            severity=severity,
            category=category,
            alert_type=alert_type,
            title=title,
            message=message,
            occurred_at=datetime.utcnow(),
            is_clear=is_clear,
            source_status=source_status,
            status=ops_status,
            raw_data=raw,
        )
    
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        """Determine severity from database mappings."""
        # Try status ID first
        status_id = raw_data.get("statusid") or raw_data.get("status_raw")
        if isinstance(status_id, int):
            key = f"status:{status_id}"
            if key in self._severity_mappings:
                return Severity(self._severity_mappings[key])
        
        # Try status text
        status_text = str(raw_data.get("status", "")).lower()
        key = f"status:{status_text}"
        if key in self._severity_mappings:
            return Severity(self._severity_mappings[key])
        
        # Default
        return Severity.WARNING
    
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        """Determine category from database mappings."""
        sensor_type = str(raw_data.get("type", "") or raw_data.get("sensor", "")).lower()
        
        # Try exact match
        key = f"type:{sensor_type}"
        if key in self._category_mappings:
            return Category(self._category_mappings[key])
        
        # Try keyword match
        for mapping_key, category in self._category_mappings.items():
            field, value = mapping_key.split(":", 1)
            if field == "type" and value in sensor_type:
                return Category(category)
        
        # Default to network for PRTG
        return Category.NETWORK
    
    def get_fingerprint(self, raw_data: Dict[str, Any]) -> str:
        """Generate deduplication fingerprint using database rules."""
        fields = self._deduplication_rules.get('fields', ['sensorid', 'device'])
        
        parts = ["prtg"]
        for field in fields:
            value = raw_data.get(field, "")
            if value:
                parts.append(str(value))
        
        fingerprint_str = ":".join(parts)
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
        """Convert status ID to text for internal processing."""
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
            11: "paused",
            12: "paused",
            13: "down_acknowledged",
            14: "down_partial",
        }
        return status_map.get(status_id, "unknown")
    
    def _get_source_status_display(self, status_id: Optional[int], status_text: str) -> str:
        """Get human-readable source status for display."""
        if status_id is not None:
            display_map = {
                1: "Unknown",
                2: "Scanning",
                3: "Up",
                4: "Warning",
                5: "Down",
                6: "No Probe",
                7: "Paused (User)",
                8: "Paused (Dependency)",
                9: "Paused (Schedule)",
                10: "Unusual",
                11: "Paused (Until)",
                12: "Paused (License)",
                13: "Down (Acknowledged)",
                14: "Down (Partial)",
            }
            return display_map.get(status_id, status_text.title())
        return status_text.title()
    
    def _get_opsconductor_status(self, status_id: Optional[int], status_text: str) -> str:
        """
        Map PRTG status to OpsConductor status.
        
        PRTG Status -> OpsConductor Status:
        - Down, Warning, Unusual, Down Partial -> active
        - Down Acknowledged -> acknowledged  
        - Paused variants -> suppressed (user intentionally paused monitoring)
        - Up -> resolved (but we don't poll Up sensors)
        """
        if status_id is not None:
            # Paused variants -> suppressed
            if status_id in (7, 8, 9, 11, 12):
                return "suppressed"
            # Down Acknowledged -> acknowledged
            if status_id == 13:
                return "acknowledged"
            # Up -> resolved
            if status_id == 3:
                return "resolved"
        
        # Check text for paused
        if "paused" in status_text.lower():
            return "suppressed"
        if "acknowledged" in status_text.lower():
            return "acknowledged"
        if status_text.lower() == "up":
            return "resolved"
        
        # Default: active
        return "active"
    
    def _build_alert_type(self, sensor_name: str, status: str) -> str:
        """Build alert type using database template."""
        # Try to find matching template
        for pattern, template in self._alert_type_templates.items():
            if pattern == "default" or pattern in sensor_name.lower():
                # Replace placeholders
                alert_type = template.replace("{sensor_type}", sensor_name.lower().replace(" ", "_"))
                alert_type = alert_type.replace("{status}", status)
                return alert_type
        
        # Fallback
        sensor_type = sensor_name.lower().replace(" ", "_") if sensor_name else "sensor"
        return f"prtg_{sensor_type}_{status}"
    
