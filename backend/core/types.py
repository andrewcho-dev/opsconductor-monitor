"""
Shared Types for Addon Module System

Dataclasses used by core system and addon modules for communication.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class Target:
    """Target device information passed to addon poll functions."""
    id: str
    ip_address: str
    name: str
    addon_id: str
    port: int = None
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    last_poll_at: datetime = None


@dataclass
class Credentials:
    """Resolved credentials for a target."""
    username: str = None
    password: str = None
    api_key: str = None
    community: str = None      # SNMP community string
    key_file: str = None       # SSH key path
    
    def has_auth(self) -> bool:
        """Check if any authentication is configured."""
        return bool(self.username or self.api_key or self.community or self.key_file)


@dataclass
class HttpResponse:
    """Response from HTTP client."""
    success: bool
    status_code: int
    data: Any = None           # Parsed JSON or raw text
    text: str = None           # Raw response text
    error: str = None
    headers: Dict[str, str] = field(default_factory=dict)
    duration: float = 0.0


@dataclass
class SnmpResponse:
    """Response from SNMP client."""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)  # OID -> value mapping
    error: str = None
    duration: float = 0.0


@dataclass
class SshResponse:
    """Response from SSH client."""
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    error: str = None
    duration: float = 0.0


@dataclass
class PollResult:
    """
    Result from addon poll function.
    
    This is returned by addon poll.py modules to tell the core
    what alerts to create and which alert types to auto-resolve.
    """
    success: bool                                        # Overall poll success
    reachable: bool                                      # Device responded (even if errors)
    alerts: List[Dict[str, Any]] = field(default_factory=list)      # Alerts to create
    clear_types: List[str] = field(default_factory=list)            # Alert types to auto-resolve
    error: str = None                                    # Error message if failed
    metrics: Dict[str, Any] = None                       # Optional metrics data


@dataclass 
class ParsedAlert:
    """
    Normalized alert from addon parse function.
    
    Used by both addon parse.py modules and webhook/trap handlers.
    """
    alert_type: str
    device_ip: str
    message: str = None
    device_name: str = None
    timestamp: datetime = None
    is_clear: bool = False
    fields: Dict[str, Any] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)
