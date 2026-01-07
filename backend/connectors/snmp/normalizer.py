"""
SNMP Alert Normalizer

Transforms SNMP trap data to standard NormalizedAlert format.
Uses OID mappings from database for classification.
"""

import logging
import hashlib
import re
from datetime import datetime
from typing import Dict, Any, Optional, List

from utils.db import db_query, db_query_one
from core.models import NormalizedAlert, Severity, Category

logger = logging.getLogger(__name__)


class SNMPNormalizer:
    """
    Normalizer for SNMP traps.
    
    Uses oid_mappings table to classify traps.
    Falls back to generic classification for unknown OIDs.
    """
    
    # Standard trap OID prefixes
    STANDARD_TRAPS = {
        "1.3.6.1.6.3.1.1.5.1": ("cold_start", Severity.WARNING, Category.NETWORK),
        "1.3.6.1.6.3.1.1.5.2": ("warm_start", Severity.INFO, Category.NETWORK),
        "1.3.6.1.6.3.1.1.5.3": ("link_down", Severity.MAJOR, Category.NETWORK),
        "1.3.6.1.6.3.1.1.5.4": ("link_up", Severity.CLEAR, Category.NETWORK),
        "1.3.6.1.6.3.1.1.5.5": ("auth_failure", Severity.WARNING, Category.SECURITY),
    }
    
    # Enterprise OID vendor mapping
    VENDOR_MAP = {
        "6141": "ciena",     # Ciena WWP
        "534": "eaton",      # Eaton
        "9": "cisco",        # Cisco
        "2636": "juniper",   # Juniper
        "8072": "net-snmp",  # Net-SNMP
    }
    
    def __init__(self):
        self._oid_cache: Dict[str, Dict] = {}
        self._cache_loaded = False
    
    @property
    def source_system(self) -> str:
        return "snmp"
    
    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedAlert:
        """
        Transform SNMP trap to NormalizedAlert.
        
        Expected raw_data format:
        {
            "source_ip": "10.1.1.1",
            "trap_oid": "1.3.6.1.6.3.1.1.5.3",
            "enterprise_oid": "1.3.6.1.4.1.6141",
            "varbinds": {"1.3.6.1.2.1.2.2.1.1": "3", ...},
            "timestamp": "2026-01-06T21:00:00Z",
            "community": "public"
        }
        """
        source_ip = raw_data.get("source_ip", "")
        trap_oid = raw_data.get("trap_oid", "")
        enterprise_oid = raw_data.get("enterprise_oid", "")
        varbinds = raw_data.get("varbinds", {})
        timestamp = raw_data.get("timestamp")
        
        # Look up OID mapping
        mapping = self._lookup_oid_mapping(trap_oid, enterprise_oid)
        
        if mapping:
            # Use mapped classification
            severity = Severity(mapping["default_severity"])
            category = Category(mapping["category"])
            alert_type = mapping["alert_type"]
            title = self._format_title(mapping.get("title_template"), raw_data)
            is_clear = mapping.get("is_clear_event", False)
        else:
            # Fallback to standard traps or generic
            severity, category, alert_type, is_clear = self._classify_unknown(trap_oid, enterprise_oid)
            title = f"SNMP Trap - {alert_type}"
        
        # Build message from varbinds
        message = self._format_varbinds(varbinds)
        
        # Parse timestamp
        occurred_at = self._parse_timestamp(timestamp)
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=f"{source_ip}:{trap_oid}:{occurred_at.timestamp()}",
            device_ip=source_ip,
            device_name=None,  # Could be resolved later from device registry
            severity=severity,
            category=category,
            alert_type=alert_type,
            title=title,
            message=message,
            occurred_at=occurred_at,
            is_clear=is_clear,
            raw_data=raw_data,
        )
    
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        """Determine severity from trap data."""
        trap_oid = raw_data.get("trap_oid", "")
        enterprise_oid = raw_data.get("enterprise_oid", "")
        
        mapping = self._lookup_oid_mapping(trap_oid, enterprise_oid)
        if mapping:
            return Severity(mapping["default_severity"])
        
        # Check standard traps
        for oid, (_, severity, _) in self.STANDARD_TRAPS.items():
            if trap_oid.startswith(oid):
                return severity
        
        return Severity.WARNING
    
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        """Determine category from trap data."""
        trap_oid = raw_data.get("trap_oid", "")
        enterprise_oid = raw_data.get("enterprise_oid", "")
        
        mapping = self._lookup_oid_mapping(trap_oid, enterprise_oid)
        if mapping:
            return Category(mapping["category"])
        
        # Check standard traps
        for oid, (_, _, category) in self.STANDARD_TRAPS.items():
            if trap_oid.startswith(oid):
                return category
        
        return Category.NETWORK
    
    def get_fingerprint(self, raw_data: Dict[str, Any]) -> str:
        """Generate deduplication fingerprint."""
        source_ip = raw_data.get("source_ip", "")
        trap_oid = raw_data.get("trap_oid", "")
        
        fingerprint_str = f"snmp:{source_ip}:{trap_oid}"
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()
    
    def is_clear_event(self, raw_data: Dict[str, Any]) -> bool:
        """Check if this is a clear/recovery trap."""
        trap_oid = raw_data.get("trap_oid", "")
        
        # Link up is a clear event
        if trap_oid.startswith("1.3.6.1.6.3.1.1.5.4"):
            return True
        
        mapping = self._lookup_oid_mapping(trap_oid, raw_data.get("enterprise_oid", ""))
        if mapping:
            return mapping.get("is_clear_event", False)
        
        return False
    
    def _lookup_oid_mapping(self, trap_oid: str, enterprise_oid: str = "") -> Optional[Dict]:
        """
        Look up OID mapping from database.
        
        Supports wildcards in oid_pattern (e.g., "1.3.6.1.4.1.6141.*")
        """
        # Load cache if needed
        if not self._cache_loaded:
            self._load_oid_cache()
        
        # Determine vendor from enterprise OID
        vendor = self._get_vendor(enterprise_oid)
        
        # Exact match first
        cache_key = f"{trap_oid}:{vendor}"
        if cache_key in self._oid_cache:
            return self._oid_cache[cache_key]
        
        cache_key_generic = f"{trap_oid}:"
        if cache_key_generic in self._oid_cache:
            return self._oid_cache[cache_key_generic]
        
        # Try wildcard match
        for pattern_key, mapping in self._oid_cache.items():
            pattern = pattern_key.split(":")[0]
            if "*" in pattern:
                regex_pattern = pattern.replace(".", r"\.").replace("*", ".*")
                if re.match(f"^{regex_pattern}$", trap_oid):
                    return mapping
        
        return None
    
    def _load_oid_cache(self) -> None:
        """Load OID mappings from database into cache."""
        try:
            rows = db_query("SELECT * FROM oid_mappings")
            
            for row in rows:
                oid_pattern = row["oid_pattern"]
                vendor = row.get("vendor") or ""
                cache_key = f"{oid_pattern}:{vendor}"
                self._oid_cache[cache_key] = dict(row)
            
            logger.info(f"Loaded {len(self._oid_cache)} OID mappings into cache")
            self._cache_loaded = True
            
        except Exception as e:
            logger.warning(f"Failed to load OID mappings: {e}")
            self._cache_loaded = True  # Don't retry
    
    def _get_vendor(self, enterprise_oid: str) -> Optional[str]:
        """Extract vendor from enterprise OID."""
        if not enterprise_oid:
            return None
        
        # Enterprise OID format: 1.3.6.1.4.1.<enterprise_id>...
        parts = enterprise_oid.split(".")
        if len(parts) > 6:
            enterprise_id = parts[6]
            return self.VENDOR_MAP.get(enterprise_id)
        
        return None
    
    def _classify_unknown(self, trap_oid: str, enterprise_oid: str):
        """Classify unknown trap OID."""
        # Check standard traps
        for oid, (alert_type, severity, category) in self.STANDARD_TRAPS.items():
            if trap_oid.startswith(oid):
                is_clear = trap_oid.startswith("1.3.6.1.6.3.1.1.5.4")
                return severity, category, alert_type, is_clear
        
        # Generic enterprise trap
        vendor = self._get_vendor(enterprise_oid) or "generic"
        return Severity.WARNING, Category.UNKNOWN, f"snmp_{vendor}_trap", False
    
    def _format_title(self, template: Optional[str], raw_data: Dict) -> str:
        """Format title template with raw data."""
        if not template:
            return "SNMP Trap"
        
        # Replace placeholders
        title = template
        title = title.replace("{device_ip}", raw_data.get("source_ip", ""))
        title = title.replace("{device_name}", raw_data.get("source_ip", ""))  # Use IP if no name
        
        return title
    
    def _format_varbinds(self, varbinds: Dict) -> str:
        """Format varbinds into readable message."""
        if not varbinds:
            return ""
        
        lines = []
        for oid, value in varbinds.items():
            # Truncate OID for readability
            short_oid = oid.split(".")[-3:] if "." in oid else oid
            lines.append(f"{'.'.join(short_oid)}: {value}")
        
        return "\n".join(lines[:10])  # Limit to 10 varbinds
    
    def _parse_timestamp(self, timestamp: Any) -> datetime:
        """Parse timestamp from trap."""
        if not timestamp:
            return datetime.utcnow()
        
        if isinstance(timestamp, datetime):
            return timestamp
        
        if isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(timestamp)
        
        # Try ISO format
        try:
            return datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except ValueError:
            return datetime.utcnow()
