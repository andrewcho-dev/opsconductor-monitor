# 03 - Data Models

**OpsConductor MVP - Database Schema & Entity Relationships**

---

## 1. Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     devices     │       │     alerts      │       │  alert_history  │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │       │ id (PK)         │
│ ip_address (UK) │◄──────│ device_ip (FK)  │       │ alert_id (FK)   │──┐
│ name            │       │ device_name     │       │ action          │  │
│ netbox_id       │       │ source_system   │       │ user_id         │  │
│ device_type     │       │ source_alert_id │       │ notes           │  │
│ site            │       │ severity        │       │ old_status      │  │
│ status          │       │ category        │       │ new_status      │  │
│ created_at      │       │ alert_type      │       │ created_at      │  │
│ updated_at      │       │ title           │       └─────────────────┘  │
└────────┬────────┘       │ message         │                            │
         │                │ status          │◄───────────────────────────┘
         │                │ priority        │
         │                │ impact          │
         │                │ urgency         │
         │                │ is_clear        │
         │                │ correlated_to_id│──┐ (self-reference)
         │                │ occurred_at     │  │
         │                │ received_at     │  │
         │                │ acknowledged_at │  │
         │                │ resolved_at     │  │
         │                │ raw_data (JSONB)│◄─┘
         │                └─────────────────┘
         │
         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  dependencies   │       │   connectors    │       │ oid_mappings    │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │       │ id (PK)         │
│ device_ip (FK)  │       │ name (UK)       │       │ oid_pattern     │
│ depends_on_ip   │       │ type            │       │ vendor          │
│ dependency_type │       │ enabled         │       │ alert_type      │
│ description     │       │ config (JSONB)  │       │ category        │
│ created_at      │       │ last_poll       │       │ default_severity│
│ created_by      │       │ status          │       │ title_template  │
└─────────────────┘       │ error_message   │       │ description     │
                          │ created_at      │       │ is_clear_event  │
                          │ updated_at      │       │ mib_name        │
                          └─────────────────┘       │ created_at      │
                                                    └─────────────────┘

┌─────────────────┐       ┌─────────────────┐
│notification_rules│      │ notification_log│
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ name            │       │ alert_id (FK)   │
│ enabled         │       │ rule_id (FK)    │
│ conditions (JSON)│      │ channel         │
│ channels (JSON) │       │ recipient       │
│ priority        │       │ status          │
│ created_at      │       │ error_message   │
│ updated_at      │       │ sent_at         │
└─────────────────┘       └─────────────────┘
```

---

## 2. Table Definitions

### 2.1 alerts (Core Table)

Primary table for all normalized alerts.

```sql
CREATE TABLE alerts (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_system VARCHAR(50) NOT NULL,
    source_alert_id VARCHAR(255) NOT NULL,
    
    -- Device
    device_ip VARCHAR(45),  -- IPv4 or IPv6
    device_name VARCHAR(255),
    
    -- Classification (per standard)
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('critical', 'major', 'minor', 'warning', 'info', 'clear')),
    category VARCHAR(50) NOT NULL CHECK (category IN ('network', 'power', 'video', 'wireless', 'security', 'environment', 'compute', 'storage', 'application', 'unknown')),
    alert_type VARCHAR(100) NOT NULL,
    
    -- Priority (ITIL)
    impact VARCHAR(20) CHECK (impact IN ('high', 'medium', 'low')),
    urgency VARCHAR(20) CHECK (urgency IN ('high', 'medium', 'low')),
    priority VARCHAR(5) CHECK (priority IN ('P1', 'P2', 'P3', 'P4', 'P5')),
    
    -- Content
    title VARCHAR(255) NOT NULL,
    message TEXT,
    
    -- State
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'acknowledged', 'suppressed', 'resolved', 'expired')),
    is_clear BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by VARCHAR(100),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(100),
    
    -- Correlation
    correlated_to_id UUID REFERENCES alerts(id),
    correlation_rule VARCHAR(100),
    
    -- Additional data
    tags TEXT[],
    custom_fields JSONB DEFAULT '{}',
    raw_data JSONB NOT NULL DEFAULT '{}',
    
    -- Deduplication
    fingerprint VARCHAR(64),  -- SHA256 hash for dedup
    occurrence_count INTEGER DEFAULT 1,
    last_occurrence_at TIMESTAMP WITH TIME ZONE,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT alerts_device_required CHECK (device_ip IS NOT NULL OR device_name IS NOT NULL),
    CONSTRAINT alerts_unique_fingerprint UNIQUE (fingerprint, status) WHERE status = 'active'
);

-- Indexes for common queries
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_category ON alerts(category);
CREATE INDEX idx_alerts_device_ip ON alerts(device_ip);
CREATE INDEX idx_alerts_occurred_at ON alerts(occurred_at);
CREATE INDEX idx_alerts_source_system ON alerts(source_system);
CREATE INDEX idx_alerts_fingerprint ON alerts(fingerprint);
CREATE INDEX idx_alerts_active ON alerts(status) WHERE status = 'active';

-- Trigger for updated_at
CREATE TRIGGER alerts_updated_at
    BEFORE UPDATE ON alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 2.2 alert_history

Audit trail for alert state changes.

```sql
CREATE TABLE alert_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    
    -- Change details
    action VARCHAR(50) NOT NULL,  -- 'created', 'acknowledged', 'resolved', 'suppressed', 'updated', 'reopened'
    old_status VARCHAR(20),
    new_status VARCHAR(20),
    
    -- Actor
    user_id VARCHAR(100),
    user_name VARCHAR(255),
    
    -- Notes
    notes TEXT,
    
    -- Metadata
    changes JSONB,  -- What fields changed
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_alert_history_alert_id ON alert_history(alert_id);
CREATE INDEX idx_alert_history_created_at ON alert_history(created_at);
```

### 2.3 devices

Device registry (synced from NetBox).

```sql
CREATE TABLE devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identity
    ip_address VARCHAR(45) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    
    -- NetBox sync
    netbox_id INTEGER,
    netbox_url VARCHAR(500),
    
    -- Classification
    device_type VARCHAR(100),
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    
    -- Location
    site VARCHAR(100),
    location VARCHAR(255),
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',
    
    -- Metadata
    tags TEXT[],
    custom_fields JSONB DEFAULT '{}',
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_synced_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_devices_ip_address ON devices(ip_address);
CREATE INDEX idx_devices_name ON devices(name);
CREATE INDEX idx_devices_netbox_id ON devices(netbox_id);
CREATE INDEX idx_devices_site ON devices(site);
```

### 2.4 dependencies

Device dependency relationships.

```sql
CREATE TABLE dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Relationship
    device_ip VARCHAR(45) NOT NULL,       -- The dependent device
    depends_on_ip VARCHAR(45) NOT NULL,   -- The device it depends on
    
    -- Classification
    dependency_type VARCHAR(50) NOT NULL DEFAULT 'network',  -- 'network', 'power', 'service'
    
    -- Documentation
    description TEXT,
    
    -- Metadata
    auto_discovered BOOLEAN DEFAULT FALSE,
    confidence DECIMAL(3,2),  -- 0.00 - 1.00 for auto-discovered
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT dependencies_no_self_reference CHECK (device_ip != depends_on_ip),
    CONSTRAINT dependencies_unique UNIQUE (device_ip, depends_on_ip, dependency_type)
);

CREATE INDEX idx_dependencies_device_ip ON dependencies(device_ip);
CREATE INDEX idx_dependencies_depends_on_ip ON dependencies(depends_on_ip);
```

### 2.5 connectors

Connector configuration and status.

```sql
CREATE TABLE connectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identity
    name VARCHAR(100) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL,  -- 'prtg', 'mcp', 'snmp', 'eaton', 'axis', etc.
    
    -- Status
    enabled BOOLEAN DEFAULT FALSE,
    status VARCHAR(50) DEFAULT 'unknown',  -- 'connected', 'disconnected', 'error', 'unknown'
    error_message TEXT,
    
    -- Configuration (encrypted sensitive fields)
    config JSONB NOT NULL DEFAULT '{}',
    -- Example config:
    -- {
    --   "url": "https://prtg.example.com",
    --   "username": "admin",
    --   "password_ref": "vault:prtg_password",  -- Reference to credential store
    --   "poll_interval": 60,
    --   "verify_ssl": true
    -- }
    
    -- Statistics
    last_poll_at TIMESTAMP WITH TIME ZONE,
    last_success_at TIMESTAMP WITH TIME ZONE,
    alerts_received INTEGER DEFAULT 0,
    alerts_today INTEGER DEFAULT 0,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_connectors_type ON connectors(type);
CREATE INDEX idx_connectors_enabled ON connectors(enabled);
```

### 2.6 oid_mappings

SNMP OID to alert type mappings.

```sql
CREATE TABLE oid_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Match criteria
    oid_pattern VARCHAR(255) NOT NULL,  -- Supports wildcards: "1.3.6.1.4.1.6141.*"
    vendor VARCHAR(50),  -- 'ciena', 'eaton', 'cisco', NULL for generic
    
    -- Classification
    alert_type VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    default_severity VARCHAR(20) NOT NULL,
    
    -- Display
    title_template VARCHAR(255),  -- "Optical Power Alarm on {interface}"
    description TEXT,
    
    -- State handling
    is_clear_event BOOLEAN DEFAULT FALSE,
    clear_oid_pattern VARCHAR(255),  -- OID that clears this alarm
    
    -- Documentation
    mib_name VARCHAR(100),
    mib_object VARCHAR(100),
    notes TEXT,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT oid_mappings_unique UNIQUE (oid_pattern, vendor)
);

CREATE INDEX idx_oid_mappings_oid_pattern ON oid_mappings(oid_pattern);
CREATE INDEX idx_oid_mappings_vendor ON oid_mappings(vendor);
```

### 2.7 notification_rules

Notification routing rules.

```sql
CREATE TABLE notification_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identity
    name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Status
    enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 100,  -- Lower = higher priority
    
    -- Conditions (JSON query format)
    conditions JSONB NOT NULL DEFAULT '{}',
    -- Example:
    -- {
    --   "severity": ["critical", "major"],
    --   "category": ["network", "power"],
    --   "device_ip_pattern": "10.1.*"
    -- }
    
    -- Actions
    channels JSONB NOT NULL DEFAULT '[]',
    -- Example:
    -- [
    --   {"type": "email", "recipients": ["noc@example.com"]},
    --   {"type": "webhook", "url": "https://slack.com/webhook/xxx"}
    -- ]
    
    -- Throttling
    throttle_minutes INTEGER DEFAULT 0,  -- 0 = no throttle
    last_triggered_at TIMESTAMP WITH TIME ZONE,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100)
);

CREATE INDEX idx_notification_rules_enabled ON notification_rules(enabled);
CREATE INDEX idx_notification_rules_priority ON notification_rules(priority);
```

### 2.8 notification_log

Record of sent notifications.

```sql
CREATE TABLE notification_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- References
    alert_id UUID REFERENCES alerts(id),
    rule_id UUID REFERENCES notification_rules(id),
    
    -- Delivery details
    channel VARCHAR(50) NOT NULL,  -- 'email', 'webhook', 'sms'
    recipient VARCHAR(255) NOT NULL,
    
    -- Status
    status VARCHAR(50) NOT NULL,  -- 'sent', 'failed', 'pending'
    error_message TEXT,
    
    -- Content (for debugging)
    payload JSONB,
    
    -- Timing
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    response_time_ms INTEGER
);

CREATE INDEX idx_notification_log_alert_id ON notification_log(alert_id);
CREATE INDEX idx_notification_log_sent_at ON notification_log(sent_at);
CREATE INDEX idx_notification_log_status ON notification_log(status);
```

---

## 3. Supporting Tables

### 3.1 Existing Tables to Keep

These tables from the current system will be retained:

| Table | Purpose | Changes |
|-------|---------|---------|
| `users` | User accounts | No change |
| `roles` | Role definitions | No change |
| `user_roles` | User-role mapping | No change |
| `sessions` | Session management | No change |
| `credentials` | Encrypted credential store | No change |
| `system_settings` | Configuration key-values | No change |
| `audit_log` | System audit trail | No change |

### 3.2 Tables to Remove

These tables will be removed as they're out of MVP scope:

| Table | Reason |
|-------|--------|
| `workflows` | Workflow builder out of scope |
| `workflow_nodes` | Workflow builder out of scope |
| `workflow_executions` | Workflow builder out of scope |
| `jobs` | Job scheduler out of scope |
| `job_schedules` | Job scheduler out of scope |

---

## 4. Migration Script

```sql
-- Migration: Create MVP Alert Tables
-- Version: 001
-- Date: 2026-01-06

BEGIN;

-- Create updated_at trigger function if not exists
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create alerts table
CREATE TABLE IF NOT EXISTS alerts (
    -- [Full definition from above]
);

-- Create alert_history table
CREATE TABLE IF NOT EXISTS alert_history (
    -- [Full definition from above]
);

-- Create devices table (or migrate from existing)
CREATE TABLE IF NOT EXISTS devices (
    -- [Full definition from above]
);

-- Create dependencies table
CREATE TABLE IF NOT EXISTS dependencies (
    -- [Full definition from above]
);

-- Create connectors table
CREATE TABLE IF NOT EXISTS connectors (
    -- [Full definition from above]
);

-- Create oid_mappings table
CREATE TABLE IF NOT EXISTS oid_mappings (
    -- [Full definition from above]
);

-- Create notification_rules table
CREATE TABLE IF NOT EXISTS notification_rules (
    -- [Full definition from above]
);

-- Create notification_log table
CREATE TABLE IF NOT EXISTS notification_log (
    -- [Full definition from above]
);

-- Seed default OID mappings
INSERT INTO oid_mappings (oid_pattern, vendor, alert_type, category, default_severity, title_template, description) VALUES
('1.3.6.1.6.3.1.1.5.1', NULL, 'cold_start', 'network', 'warning', 'Device Cold Start - {device_name}', 'Device has rebooted (cold start)'),
('1.3.6.1.6.3.1.1.5.2', NULL, 'warm_start', 'network', 'info', 'Device Warm Start - {device_name}', 'Device has rebooted (warm start)'),
('1.3.6.1.6.3.1.1.5.3', NULL, 'link_down', 'network', 'major', 'Interface Down - {device_name}', 'Network interface has gone down'),
('1.3.6.1.6.3.1.1.5.4', NULL, 'link_up', 'network', 'clear', 'Interface Up - {device_name}', 'Network interface has come up'),
('1.3.6.1.6.3.1.1.5.5', NULL, 'auth_failure', 'security', 'warning', 'Authentication Failure - {device_name}', 'SNMP authentication failure')
ON CONFLICT DO NOTHING;

COMMIT;
```

---

## 5. Data Types (Python Models)

```python
# backend/core/models.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from enum import Enum

class Severity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    WARNING = "warning"
    INFO = "info"
    CLEAR = "clear"

class Category(str, Enum):
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
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"
    RESOLVED = "resolved"
    EXPIRED = "expired"

class Priority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"
    P5 = "P5"

class Impact(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Urgency(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class NormalizedAlert:
    """Alert after normalization, before storage."""
    source_system: str
    source_alert_id: str
    severity: Severity
    category: Category
    alert_type: str
    title: str
    occurred_at: datetime
    
    device_ip: Optional[str] = None
    device_name: Optional[str] = None
    message: Optional[str] = None
    is_clear: bool = False
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    id: UUID = field(default_factory=uuid4)
    received_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Alert:
    """Full alert entity from database."""
    id: UUID
    source_system: str
    source_alert_id: str
    device_ip: Optional[str]
    device_name: Optional[str]
    severity: Severity
    category: Category
    alert_type: str
    title: str
    message: Optional[str]
    status: AlertStatus
    is_clear: bool
    occurred_at: datetime
    received_at: datetime
    raw_data: Dict[str, Any]
    
    # Optional fields
    impact: Optional[Impact] = None
    urgency: Optional[Urgency] = None
    priority: Optional[Priority] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    correlated_to_id: Optional[UUID] = None
    correlation_rule: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    fingerprint: Optional[str] = None
    occurrence_count: int = 1


@dataclass
class Dependency:
    """Device dependency relationship."""
    id: UUID
    device_ip: str
    depends_on_ip: str
    dependency_type: str
    description: Optional[str] = None
    auto_discovered: bool = False
    confidence: Optional[float] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None


@dataclass
class Connector:
    """Connector configuration."""
    id: UUID
    name: str
    type: str
    enabled: bool
    status: str
    config: Dict[str, Any]
    error_message: Optional[str] = None
    last_poll_at: Optional[datetime] = None
    alerts_received: int = 0
```

---

*Next: [05_API_SPECIFICATION.md](./05_API_SPECIFICATION.md)*
