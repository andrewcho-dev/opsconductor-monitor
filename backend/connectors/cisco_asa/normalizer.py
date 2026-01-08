"""
Cisco ASA Normalizer

Converts Cisco ASA events to normalized alerts.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from backend.connectors.base import BaseNormalizer
from backend.core.models import NormalizedAlert, Severity, Category
from backend.utils.ip_utils import validate_device_ip

logger = logging.getLogger(__name__)

# Alert type mappings
ALERT_TYPES = {
    "ipsec_tunnel_down": {
        "severity": Severity.CRITICAL,
        "category": Category.NETWORK,
        "title": "IPSec Tunnel Down",
        "message_template": "IPSec VPN tunnel to {peer_ip} is down"
    },
    "ike_tunnel_down": {
        "severity": Severity.CRITICAL,
        "category": Category.NETWORK,
        "title": "IKE Tunnel Down",
        "message_template": "IKE SA to {peer_ip} not established"
    },
    "vpn_peer_down": {
        "severity": Severity.CRITICAL,
        "category": Category.NETWORK,
        "title": "VPN Peer Unreachable",
        "message_template": "VPN peer {peer_ip} is not responding"
    },
    "cpu_critical": {
        "severity": Severity.CRITICAL,
        "category": Category.PERFORMANCE,
        "title": "CPU Critical",
        "message_template": "CPU usage at {cpu_percent}% (threshold: {threshold}%)"
    },
    "cpu_high": {
        "severity": Severity.WARNING,
        "category": Category.PERFORMANCE,
        "title": "CPU High",
        "message_template": "CPU usage at {cpu_percent}% (threshold: {threshold}%)"
    },
    "memory_critical": {
        "severity": Severity.CRITICAL,
        "category": Category.PERFORMANCE,
        "title": "Memory Critical",
        "message_template": "Memory usage at {memory_percent:.1f}% (threshold: {threshold}%)"
    },
    "memory_high": {
        "severity": Severity.WARNING,
        "category": Category.PERFORMANCE,
        "title": "Memory High",
        "message_template": "Memory usage at {memory_percent:.1f}% (threshold: {threshold}%)"
    },
    "interface_down": {
        "severity": Severity.CRITICAL,
        "category": Category.NETWORK,
        "title": "Interface Down",
        "message_template": "Interface {interface} is down"
    },
    "failover_issue": {
        "severity": Severity.WARNING,
        "category": Category.AVAILABILITY,
        "title": "Failover Issue",
        "message_template": "Failover state abnormal"
    },
    "failover_failed": {
        "severity": Severity.CRITICAL,
        "category": Category.AVAILABILITY,
        "title": "Failover Failed",
        "message_template": "Failover unit in Failed state"
    },
    "device_offline": {
        "severity": Severity.CRITICAL,
        "category": Category.AVAILABILITY,
        "title": "Device Offline",
        "message_template": "Cannot connect to ASA: {error}"
    },
}


class CiscoASANormalizer(BaseNormalizer):
    """Normalizes Cisco ASA events to standard alert format."""
    
    def __init__(self):
        super().__init__()
        self._enabled_events = set(ALERT_TYPES.keys())
    
    @property
    def source_system(self) -> str:
        return "cisco_asa"
    
    def get_severity(self, raw_data: Dict[str, Any]) -> Severity:
        event_type = raw_data.get("event_type", "")
        return ALERT_TYPES.get(event_type, {}).get("severity", Severity.WARNING)
    
    def get_category(self, raw_data: Dict[str, Any]) -> Category:
        event_type = raw_data.get("event_type", "")
        return ALERT_TYPES.get(event_type, {}).get("category", Category.NETWORK)
    
    def normalize(self, raw_event: Dict[str, Any]) -> Optional[NormalizedAlert]:
        """Convert raw ASA event to normalized alert."""
        event_type = raw_event.get("event_type", "")
        
        if event_type not in ALERT_TYPES:
            logger.warning(f"Unknown Cisco ASA event type: {event_type}")
            return None
        
        if event_type not in self._enabled_events:
            return None
        
        alert_config = ALERT_TYPES[event_type]
        
        # Validate device IP
        try:
            device_ip = validate_device_ip(
                raw_event.get("device_ip"),
                raw_event.get("device_name")
            )
        except ValueError as e:
            logger.warning(f"Invalid device IP for Cisco ASA alert: {e}")
            return None
        
        # Build message from template
        try:
            message = alert_config["message_template"].format(**raw_event)
        except KeyError:
            message = alert_config["message_template"]
        
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
            severity=alert_config["severity"],
            category=alert_config["category"],
            alert_type=f"cisco_asa_{event_type}",
            title=alert_config["title"],
            message=message,
            occurred_at=occurred_at,
            raw_data=raw_event,
        )
    
    def set_enabled_events(self, events: set):
        """Set which event types are enabled."""
        self._enabled_events = events
