"""
OpsConductor Core Models

Standard data models conforming to Alert Classification Standard.
See: docs/standards/ALERT_CLASSIFICATION_STANDARD.md
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from enum import Enum


# =============================================================================
# Enumerations (per Alert Classification Standard)
# =============================================================================

class Severity(str, Enum):
    """Alert severity levels (RFC 5424 based)."""
    CRITICAL = "critical"  # Immediate action required
    MAJOR = "major"        # Significant impact, urgent
    MINOR = "minor"        # Limited impact, business hours
    WARNING = "warning"    # Potential issue, monitor
    INFO = "info"          # Informational, no action
    CLEAR = "clear"        # Recovery event


class Category(str, Enum):
    """Alert categories (ITIL/MOF based)."""
    NETWORK = "network"
    POWER = "power"
    VIDEO = "video"
    WIRELESS = "wireless"
    SECURITY = "security"
    ENVIRONMENT = "environment"
    COMPUTE = "compute"
    STORAGE = "storage"
    APPLICATION = "application"
    UNKNOWN = "unknown"


class AlertStatus(str, Enum):
    """
    Alert status reflecting source system state.
    
    OpsConductor mirrors the originating system's status - it does not
    manage its own lifecycle. Status changes come from source systems.
    """
    ACTIVE = "active"           # Source reports problem state (down, warning, error)
    ACKNOWLEDGED = "acknowledged"  # Source reports alert is ack'd but issue persists
    SUPPRESSED = "suppressed"   # Source has paused, muted, or suppressed the alert
    RESOLVED = "resolved"       # Source reports OK/clear, or alert no longer in poll


class Priority(str, Enum):
    """ITIL priority levels."""
    P1 = "P1"  # Critical - Immediate
    P2 = "P2"  # High - 15 min response
    P3 = "P3"  # Medium - 1 hour response
    P4 = "P4"  # Low - 4 hour response
    P5 = "P5"  # Planning - Next business day


class Impact(str, Enum):
    """Business impact levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Urgency(str, Enum):
    """Time sensitivity levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ConnectorStatus(str, Enum):
    """Connector connection states."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    UNKNOWN = "unknown"


class DependencyType(str, Enum):
    """Types of device dependencies."""
    NETWORK = "network"  # Network connectivity dependency
    POWER = "power"      # Power supply dependency
    SERVICE = "service"  # Service/application dependency


# =============================================================================
# Priority Calculation
# =============================================================================

PRIORITY_MATRIX = {
    (Impact.HIGH, Urgency.HIGH): Priority.P1,
    (Impact.HIGH, Urgency.MEDIUM): Priority.P2,
    (Impact.HIGH, Urgency.LOW): Priority.P3,
    (Impact.MEDIUM, Urgency.HIGH): Priority.P2,
    (Impact.MEDIUM, Urgency.MEDIUM): Priority.P3,
    (Impact.MEDIUM, Urgency.LOW): Priority.P4,
    (Impact.LOW, Urgency.HIGH): Priority.P3,
    (Impact.LOW, Urgency.MEDIUM): Priority.P4,
    (Impact.LOW, Urgency.LOW): Priority.P5,
}


def calculate_priority(impact: Impact, urgency: Urgency) -> Priority:
    """Calculate priority from impact and urgency using ITIL matrix."""
    return PRIORITY_MATRIX.get((impact, urgency), Priority.P3)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class NormalizedAlert:
    """
    Alert after normalization from connector, before storage.
    
    This is the output of every normalizer - a standard format
    regardless of source system.
    """
    # Required fields
    source_system: str
    source_alert_id: str
    severity: Severity
    category: Category
    alert_type: str
    title: str
    occurred_at: datetime
    
    # Device identification (at least one required)
    device_ip: Optional[str] = None
    device_name: Optional[str] = None
    
    # Content
    message: Optional[str] = None
    
    # State
    is_clear: bool = False
    source_status: Optional[str] = None  # Raw status from source system
    status: Optional[str] = None  # OpsConductor status (active, acknowledged, suppressed, resolved)
    
    # Raw data for debugging
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    # Generated fields
    id: UUID = field(default_factory=uuid4)
    received_at: datetime = field(default_factory=lambda: datetime.utcnow())
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.device_ip and not self.device_name:
            raise ValueError("At least one of device_ip or device_name is required")
        
        # Convert string enums if needed
        if isinstance(self.severity, str):
            self.severity = Severity(self.severity)
        if isinstance(self.category, str):
            self.category = Category(self.category)


@dataclass
class Alert:
    """
    Full alert entity as stored in database.
    
    Extends NormalizedAlert with database fields, timestamps,
    and correlation data.
    """
    # Identity
    id: UUID
    source_system: str
    source_alert_id: str
    
    # Device
    device_ip: Optional[str]
    device_name: Optional[str]
    
    # Classification
    severity: Severity
    category: Category
    alert_type: str
    
    # Content
    title: str
    message: Optional[str]
    
    # State
    status: AlertStatus
    is_clear: bool
    
    # Timestamps
    occurred_at: datetime
    received_at: datetime
    
    # Raw data
    raw_data: Dict[str, Any]
    
    # Priority (ITIL)
    impact: Optional[Impact] = None
    urgency: Optional[Urgency] = None
    priority: Optional[Priority] = None
    
    # Source system status (raw value from source)
    source_status: Optional[str] = None
    
    # Resolution
    resolved_at: Optional[datetime] = None
    
    # Correlation
    correlated_to_id: Optional[UUID] = None
    correlation_rule: Optional[str] = None
    
    # Deduplication
    fingerprint: Optional[str] = None
    occurrence_count: int = 1
    last_occurrence_at: Optional[datetime] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    # Audit
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_normalized(cls, normalized: NormalizedAlert, **kwargs) -> "Alert":
        """Create Alert from NormalizedAlert."""
        # Use status from normalized alert if provided, otherwise default to ACTIVE
        if normalized.status:
            status = AlertStatus(normalized.status)
        else:
            status = AlertStatus.ACTIVE
        
        return cls(
            id=normalized.id,
            source_system=normalized.source_system,
            source_alert_id=normalized.source_alert_id,
            device_ip=normalized.device_ip,
            device_name=normalized.device_name,
            severity=normalized.severity,
            category=normalized.category,
            alert_type=normalized.alert_type,
            title=normalized.title,
            message=normalized.message,
            status=status,
            is_clear=normalized.is_clear,
            occurred_at=normalized.occurred_at,
            received_at=normalized.received_at,
            raw_data=normalized.raw_data,
            source_status=normalized.source_status,
            **kwargs
        )
    
    def calculate_priority(self) -> Optional[Priority]:
        """Calculate priority from impact and urgency."""
        if self.impact and self.urgency:
            self.priority = calculate_priority(self.impact, self.urgency)
        return self.priority


@dataclass
class AlertHistoryEntry:
    """Record of an alert state change."""
    id: UUID
    alert_id: UUID
    action: str  # created, acknowledged, resolved, suppressed, updated, reopened
    old_status: Optional[AlertStatus]
    new_status: Optional[AlertStatus]
    user_id: Optional[str]
    user_name: Optional[str]
    notes: Optional[str]
    changes: Optional[Dict[str, Any]]
    created_at: datetime


@dataclass
class Dependency:
    """Device dependency relationship."""
    id: UUID
    device_ip: str
    depends_on_ip: str
    dependency_type: DependencyType
    description: Optional[str] = None
    auto_discovered: bool = False
    confidence: Optional[float] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    
    # Joined fields (not stored, populated by queries)
    device_name: Optional[str] = None
    depends_on_name: Optional[str] = None


@dataclass
class Connector:
    """Connector configuration and status."""
    id: UUID
    name: str
    type: str  # prtg, mcp, snmp_trap, snmp_poll, eaton, axis, etc.
    enabled: bool
    status: ConnectorStatus
    config: Dict[str, Any]
    error_message: Optional[str] = None
    last_poll_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    alerts_received: int = 0
    alerts_today: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class OIDMapping:
    """SNMP OID to alert type mapping."""
    id: UUID
    oid_pattern: str
    vendor: Optional[str]
    alert_type: str
    category: Category
    default_severity: Severity
    title_template: Optional[str]
    description: Optional[str]
    is_clear_event: bool = False
    clear_oid_pattern: Optional[str] = None
    mib_name: Optional[str] = None
    mib_object: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class NotificationRule:
    """Notification routing rule."""
    id: UUID
    name: str
    enabled: bool
    priority: int  # Lower = higher priority
    conditions: Dict[str, Any]  # Matching conditions
    channels: List[Dict[str, Any]]  # Delivery channels
    throttle_minutes: int = 0
    last_triggered_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None


@dataclass
class NotificationLog:
    """Record of sent notification."""
    id: UUID
    alert_id: Optional[UUID]
    rule_id: Optional[UUID]
    channel: str
    recipient: str
    status: str  # sent, failed, pending
    error_message: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    sent_at: Optional[datetime] = None
    response_time_ms: Optional[int] = None
