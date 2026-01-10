"""
SNMP Alert Normalizer

Transforms SNMP trap data to standard NormalizedAlert format.
Uses database mappings (severity_mappings, category_mappings, snmp_trap_mappings)
for CONSISTENT classification with all other connectors.
"""

import logging
import hashlib
import re
from datetime import datetime
from typing import Dict, Any, Optional, List

from backend.utils.db import db_query, db_query_one
from backend.core.models import NormalizedAlert, Severity, Category
from backend.utils.ip_utils import validate_device_ip

logger = logging.getLogger(__name__)


class SNMPNormalizer:
    """
    Normalizer for SNMP traps.
    
    Uses database mappings for CONSISTENT classification:
    - severity_mappings: trap_oid -> severity
    - category_mappings: trap_oid -> category  
    - snmp_trap_mappings: trap_oid -> alert_type, is_clear, correlation_key
    
    Falls back to generic classification for unknown OIDs.
    """
    
    # Standard trap OID prefixes (fallback only)
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
        "31926": "siklu",    # Siklu
    }
    
    def __init__(self):
        self._severity_cache: Dict[str, str] = {}
        self._category_cache: Dict[str, str] = {}
        self._trap_cache: Dict[str, Dict] = {}
        self._cache_loaded = False
    
    @property
    def source_system(self) -> str:
        return "snmp"
    
    def is_trap_enabled(self, trap_oid: str) -> bool:
        """Check if this trap OID is enabled in mappings.
        
        Returns False if:
        - Trap OID is not in any mapping (unknown traps are ignored)
        - Trap OID is explicitly disabled in mappings
        """
        if not self._cache_loaded:
            self._load_mapping_cache()
        
        severity_mapping = self._severity_cache.get(trap_oid)
        trap_mapping = self._trap_cache.get(trap_oid)
        
        # If not in ANY mapping, treat as disabled (unknown trap)
        if not severity_mapping and not trap_mapping:
            logger.debug(f"Trap OID '{trap_oid}' not in mappings - ignoring")
            return False
        
        # Check if explicitly disabled in severity mapping
        # Note: We check the raw database value, not the cached string
        # For now, if it's in the cache, it's enabled
        return True
    
    def normalize(self, raw_data: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """
        Transform SNMP trap to NormalizedAlert.
        
        Returns None if the trap OID is not in mappings.
        
        Uses database mappings for CONSISTENT classification:
        - severity_mappings table (connector_type='snmp_trap')
        - category_mappings table (connector_type='snmp_trap')
        - snmp_trap_mappings table (for alert_type, is_clear, correlation)
        
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
        # Load cache if needed
        if not self._cache_loaded:
            self._load_mapping_cache()
        
        source_ip = raw_data.get("source_ip", "")
        trap_oid = raw_data.get("trap_oid", "")
        enterprise_oid = raw_data.get("enterprise_oid", "")
        varbinds = raw_data.get("varbinds", {})
        timestamp = raw_data.get("timestamp")
        
        # Check if trap OID is enabled in mappings
        if not self.is_trap_enabled(trap_oid):
            logger.debug(f"Skipping unmapped SNMP trap OID: {trap_oid}")
            return None
        
        # Look up from database mappings
        trap_mapping = self._trap_cache.get(trap_oid)
        severity_str = self._severity_cache.get(trap_oid)
        category_str = self._category_cache.get(trap_oid)
        
        if trap_mapping:
            # Use database mapping
            alert_type = trap_mapping.get("alert_type", "snmp_trap")
            is_clear = trap_mapping.get("is_clear", False)
            title = f"SNMP Trap - {trap_mapping.get('description', alert_type)}"
        else:
            # Use severity mapping description if available
            alert_type = f"snmp_{trap_oid.replace('.', '_')}"
            is_clear = False
            title = f"SNMP Trap - {trap_oid}"
        
        # Get severity from database
        if severity_str:
            severity = Severity(severity_str)
        else:
            severity = Severity.WARNING
        
        # Get category from database
        if category_str:
            category = Category(category_str)
        else:
            category = Category.NETWORK
        
        # Build message from varbinds
        message = self._format_varbinds(varbinds, source_ip, trap_oid)
        
        # Parse timestamp
        occurred_at = self._parse_timestamp(timestamp)
        
        # Generate fingerprint for raise/clear correlation
        fingerprint = self.get_fingerprint(raw_data)
        
        return NormalizedAlert(
            source_system=self.source_system,
            source_alert_id=f"{source_ip}:{trap_oid}:{occurred_at.timestamp()}",
            device_ip=validate_device_ip(source_ip, None),
            device_name=None,
            severity=severity,
            category=category,
            alert_type=alert_type,
            title=title,
            message=message,
            occurred_at=occurred_at,
            is_clear=is_clear,
            raw_data=raw_data,
            fingerprint=fingerprint,
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
        """Generate deduplication fingerprint.
        
        Uses correlation_key from database so raise/clear traps match.
        Falls back to alert_type if no correlation_key defined.
        """
        # Load cache if needed
        if not self._cache_loaded:
            self._load_mapping_cache()
        
        source_ip = raw_data.get("source_ip", "")
        trap_oid = raw_data.get("trap_oid", "")
        
        # Check database mapping for correlation_key
        trap_mapping = self._trap_cache.get(trap_oid)
        if trap_mapping:
            # Use correlation_key if available, otherwise alert_type
            correlation_key = trap_mapping.get("correlation_key") or trap_mapping.get("alert_type")
            fingerprint_str = f"snmp:{source_ip}:{correlation_key}"
        else:
            # Fallback to trap_oid
            fingerprint_str = f"snmp:{source_ip}:{trap_oid}"
        
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()
    
    def is_clear_event(self, raw_data: Dict[str, Any]) -> bool:
        """Check if this is a clear/recovery trap using database mapping."""
        # Load cache if needed
        if not self._cache_loaded:
            self._load_mapping_cache()
        
        trap_oid = raw_data.get("trap_oid", "")
        
        # Check database mapping first
        trap_mapping = self._trap_cache.get(trap_oid)
        if trap_mapping:
            return trap_mapping.get("is_clear", False)
        
        # Fallback: Link up is a clear event
        if trap_oid.startswith("1.3.6.1.6.3.1.1.5.4"):
            return True
        
        return False
    
    def _load_mapping_cache(self) -> None:
        """
        Load all mappings from database into cache.
        
        Loads from:
        - severity_mappings (connector_type='snmp_trap', source_field='trap_oid')
        - category_mappings (connector_type='snmp_trap', source_field='trap_oid')
        - snmp_trap_mappings (trap_oid -> alert_type, is_clear, correlation_key)
        """
        try:
            # Load severity mappings
            severity_rows = db_query("""
                SELECT source_value, target_severity 
                FROM severity_mappings 
                WHERE connector_type = 'snmp_trap' 
                AND source_field = 'trap_oid'
                AND enabled = true
                ORDER BY priority DESC
            """)
            for row in severity_rows:
                self._severity_cache[row["source_value"]] = row["target_severity"]
            
            # Load category mappings
            category_rows = db_query("""
                SELECT source_value, target_category 
                FROM category_mappings 
                WHERE connector_type = 'snmp_trap' 
                AND source_field = 'trap_oid'
                AND enabled = true
                ORDER BY priority DESC
            """)
            for row in category_rows:
                self._category_cache[row["source_value"]] = row["target_category"]
            
            # Load trap-specific mappings (alert_type, is_clear, correlation_key)
            trap_rows = db_query("""
                SELECT trap_oid, alert_type, is_clear, correlation_key, vendor, description
                FROM snmp_trap_mappings
                WHERE enabled = true
            """)
            for row in trap_rows:
                self._trap_cache[row["trap_oid"]] = dict(row)
            
            logger.info(f"Loaded SNMP trap mappings: {len(self._severity_cache)} severity, "
                       f"{len(self._category_cache)} category, {len(self._trap_cache)} trap")
            self._cache_loaded = True
            
        except Exception as e:
            logger.warning(f"Failed to load SNMP trap mappings: {e}")
            self._cache_loaded = True  # Don't retry on error
    
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
        """Classify unknown trap OID (fallback when not in database)."""
        # Check standard traps
        for oid, (alert_type, severity, category) in self.STANDARD_TRAPS.items():
            if trap_oid.startswith(oid):
                is_clear = trap_oid.startswith("1.3.6.1.6.3.1.1.5.4")
                return severity, category, alert_type, is_clear
        
        # Check if it's a Siklu trap by prefix (for unknown specific traps)
        if trap_oid.startswith("1.3.6.1.4.1.31926"):
            return Severity.WARNING, Category.WIRELESS, "siklu_unknown_trap", False
        
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
    
    def _format_varbinds(self, varbinds: Dict, source_ip: str = "", trap_oid: str = "") -> str:
        """Format varbinds into readable message."""
        lines = []
        
        # Always include device info
        if source_ip:
            lines.append(f"Device: {source_ip}")
        
        # Trap OID
        if trap_oid:
            lines.append(f"Trap: {trap_oid}")
        
        if varbinds:
            for oid, value in list(varbinds.items())[:10]:  # Limit to 10 varbinds
                # Truncate OID for readability
                short_oid = oid.split(".")[-3:] if "." in oid else oid
                lines.append(f"{'.'.join(short_oid)}: {value}")
        
        return " | ".join(lines) if lines else f"SNMP trap from {source_ip}"
    
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
