# OpsConductor Alert Classification Standard

**Version:** 1.0  
**Date:** January 6, 2026  
**Status:** APPROVED - Official Standard  
**Authors:** Architecture Team

---

## Purpose

This document defines the **official classification standard** for all alerts, alarms, and events processed by OpsConductor. All connectors, normalizers, and future integrations MUST conform to this standard.

---

## 1. Severity Levels

Based on **RFC 5424 (Syslog)** with simplification for operational use.

| Level | Code | Name | Description | Response Time | Notification |
|-------|------|------|-------------|---------------|--------------|
| 1 | `critical` | Critical | Service outage, immediate action required | Immediate | Page on-call |
| 2 | `major` | Major | Significant degradation, urgent response needed | < 15 minutes | Alert + escalation |
| 3 | `minor` | Minor | Limited impact, attention needed | < 1 hour | Alert |
| 4 | `warning` | Warning | Potential issue, may escalate | < 4 hours | Dashboard |
| 5 | `info` | Info | Informational, no action required | N/A | Log only |
| 6 | `clear` | Clear | Recovery event, closes prior alert | N/A | Auto-resolve |

### Severity Guidelines

**Critical (1):**
- Complete service outage
- Data loss imminent
- Safety system failure
- Multiple users/services affected
- Examples: Core switch down, UPS battery depleted, main link failure

**Major (2):**
- Significant degradation
- Single critical component failure
- Redundancy lost
- Examples: Single link down with redundancy, UPS on battery, camera recording failed

**Minor (3):**
- Limited impact
- Non-critical component issue
- Workaround available
- Examples: Secondary link down, single camera offline, high CPU on non-critical device

**Warning (4):**
- Potential future issue
- Threshold approaching
- Degraded performance
- Examples: Disk 80% full, signal strength declining, battery aging

**Info (5):**
- Awareness only
- Status change
- No action needed
- Examples: Scheduled maintenance, config change, firmware update available

**Clear (6):**
- Recovery notification
- Previous alert resolved
- Examples: Link up (after link down), UPS returned to AC power

---

## 2. Categories

Standard operational categories based on **ITIL/MOF** service classification.

| Category | Code | Description | Typical Sources |
|----------|------|-------------|-----------------|
| Network | `network` | Connectivity, switching, routing | SNMP, PRTG, MCP |
| Power | `power` | UPS, PDU, electrical | Eaton, SNMP |
| Video | `video` | Cameras, VMS, recording | Axis, Milestone |
| Wireless | `wireless` | WiFi, cellular, microwave | Cradlepoint, Siklu, Ubiquiti |
| Security | `security` | Authentication, access, intrusion | SNMP, Cameras, Access Control |
| Environment | `environment` | Temperature, humidity, physical | SNMP, Sensors |
| Compute | `compute` | Servers, VMs, containers | PRTG, SNMP |
| Storage | `storage` | Disk, SAN, NAS, backup | PRTG, SNMP |
| Application | `application` | Software, services, APIs | PRTG, Custom |
| Unknown | `unknown` | Unmapped or new alert types | Any (requires mapping) |

### Category Assignment Rules

1. Assign based on the **primary affected resource**
2. If multiple categories apply, use the **most specific**
3. New alert types start as `unknown` until mapped
4. Category determines default dashboard grouping

---

## 3. Alert Status

Alert status reflects the **source system's state**. OpsConductor does not manage its own lifecycle - it mirrors what the originating system reports.

| Status | Code | Description | Source System Meaning |
|--------|------|-------------|----------------------|
| Active | `active` | Alert is currently active | Source reports problem state (down, warning, error, etc.) |
| Acknowledged | `acknowledged` | Alert acknowledged at source | Source reports alert is ack'd but issue persists |
| Suppressed | `suppressed` | Alert paused/hidden at source | Source has paused, muted, or suppressed the alert |
| Resolved | `resolved` | Issue resolved | Source reports OK/clear, or alert no longer present in poll |

### Key Principles

1. **OpsConductor is read-only** - Status changes come from source systems, not user actions in OpsConductor
2. **Polling reconciliation** - For polled sources, alerts that disappear from poll results are marked `resolved`
3. **Explicit clears** - For event-based sources, `resolved` requires an explicit clear event (`is_clear=true`)
4. **Suppression visibility** - Suppressed alerts are still shown (not hidden) but marked as `suppressed`

### Source System Status Mappings

#### PRTG

| PRTG Status | Code | OpsConductor Status |
|-------------|------|--------------------|
| Up | 3 | `resolved` |
| Warning | 4 | `active` |
| Down | 5 | `active` |
| Paused by User | 7 | `suppressed` |
| Paused by Dependency | 8 | `suppressed` |
| Paused by Schedule | 9 | `suppressed` |
| Unusual | 10 | `active` |
| Paused Until | 11 | `suppressed` |
| Down (Acknowledged) | 13 | `acknowledged` |
| Down (Partial) | 14 | `active` |
| Not in poll results | - | `resolved` |

#### Eaton UPS

| Eaton State | OpsConductor Status |
|-------------|--------------------|
| Alarm active | `active` |
| Alarm cleared | `resolved` |

#### SNMP Traps

| Trap Type | OpsConductor Status |
|-----------|--------------------|
| Alert trap | `active` |
| Clear trap (`is_clear=true`) | `resolved` |

#### Axis Cameras

| Axis Event | OpsConductor Status |
|------------|--------------------|
| Event active | `active` |
| Event cleared | `resolved` |

#### Cradlepoint / Siklu / Ubiquiti

| State | OpsConductor Status |
|-------|--------------------|
| Alert active | `active` |
| Alert cleared | `resolved` |

### Status Workflow

```
    ┌─────────────────────────────────────────────────────────┐
    │                   SOURCE SYSTEM                         │
    │  (PRTG, Eaton, SNMP, Axis, Cradlepoint, etc.)          │
    └─────────────────────────┬───────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────┐
    │                   OPSCONDUCTOR                          │
    │                                                         │
    │   Source says alerting ──────────► ACTIVE               │
    │   Source says ack'd ─────────────► ACKNOWLEDGED         │
    │   Source says paused ────────────► SUPPRESSED           │
    │   Source says OK/clear ──────────► RESOLVED             │
    │   Alert disappears from poll ────► RESOLVED             │
    │                                                         │
    └─────────────────────────────────────────────────────────┘
```

### Reconciliation Logic (Polled Sources)

For connectors that poll for current state (PRTG, Eaton, etc.):

1. Before poll: Note all `active`/`acknowledged`/`suppressed` alerts from this source
2. After poll: Compare returned alerts against existing
3. Any existing alert NOT in poll results → mark as `resolved`
4. Only reconcile if connector poll was successful (no errors)

---

## 4. Priority (ITIL-Based)

Priority is **calculated** from Impact × Urgency.

### Impact Levels

| Impact | Code | Description |
|--------|------|-------------|
| High | `high` | Multiple users/services affected, revenue impact |
| Medium | `medium` | Single service or limited users affected |
| Low | `low` | Single user or non-critical function |

### Urgency Levels

| Urgency | Code | Description |
|---------|------|-------------|
| High | `high` | Immediate business need, no workaround |
| Medium | `medium` | Business need within hours, workaround exists |
| Low | `low` | Can wait for scheduled maintenance |

### Priority Matrix

|  | High Urgency | Medium Urgency | Low Urgency |
|---|---|---|---|
| **High Impact** | **P1** | **P2** | **P3** |
| **Medium Impact** | **P2** | **P3** | **P4** |
| **Low Impact** | **P3** | **P4** | **P5** |

### Priority Definitions

| Priority | Name | Target Response | Target Resolution |
|----------|------|-----------------|-------------------|
| P1 | Critical | Immediate | 1 hour |
| P2 | High | 15 minutes | 4 hours |
| P3 | Medium | 1 hour | 8 hours |
| P4 | Low | 4 hours | 24 hours |
| P5 | Planning | Next business day | Scheduled |

---

## 5. Normalized Alert Schema

All alerts MUST conform to this schema after normalization.

```json
{
  "id": "uuid-v4",
  "source_system": "prtg|snmp|mcp|eaton|axis|milestone|cradlepoint|siklu|ubiquiti",
  "source_alert_id": "string",
  
  "device_ip": "10.1.1.5",
  "device_name": "Core-Switch-1",
  
  "severity": "critical|major|minor|warning|info|clear",
  "category": "network|power|video|wireless|security|environment|compute|storage|application|unknown",
  "alert_type": "string",
  
  "impact": "high|medium|low",
  "urgency": "high|medium|low",
  "priority": "P1|P2|P3|P4|P5",
  
  "title": "string (max 255 chars)",
  "message": "string (detailed description)",
  
  "status": "active|acknowledged|suppressed|resolved",
  "source_status": "string (raw status from source system)",
  "is_clear": false,
  
  "occurred_at": "ISO 8601 timestamp",
  "received_at": "ISO 8601 timestamp",
  "resolved_at": "ISO 8601 timestamp or null",
  
  "correlated_to_id": "uuid or null",
  "correlation_rule": "string or null",
  
  "tags": ["string"],
  "custom_fields": {},
  
  "raw_data": {}
}
```

### Required Fields

These fields MUST be present on every normalized alert:

- `id`
- `source_system`
- `source_alert_id`
- `device_ip` OR `device_name` (at least one)
- `severity`
- `category`
- `title`
- `status`
- `occurred_at`
- `received_at`

### Optional Fields

These fields may be null or omitted:

- `source_status` (raw status string from source)
- `impact`, `urgency`, `priority` (calculated later)
- `resolved_at`
- `correlated_to_id`, `correlation_rule`
- `tags`, `custom_fields`

---

## 6. Alert Type Naming Convention

Alert types are specific identifiers within a category.

### Format

```
{category}_{specific_type}
```

### Examples

| Category | Alert Type | Description |
|----------|------------|-------------|
| network | `network_link_down` | Interface/link went down |
| network | `network_link_up` | Interface/link came up |
| network | `network_high_utilization` | Bandwidth threshold exceeded |
| power | `power_on_battery` | UPS running on battery |
| power | `power_low_battery` | Battery critically low |
| power | `power_overload` | Load exceeds capacity |
| video | `video_camera_offline` | Camera not responding |
| video | `video_recording_failed` | Recording error |
| video | `video_motion_detected` | Motion event |
| wireless | `wireless_signal_low` | Signal strength below threshold |
| wireless | `wireless_link_down` | Radio link lost |

---

## 7. Implementation Requirements

### For Connector Developers

1. **Every connector MUST have a normalizer** that outputs this schema
2. **Severity mapping MUST be documented** for each source system
3. **Unknown alerts MUST be categorized as `unknown`** until mapped
4. **Raw data MUST be preserved** in `raw_data` field

### For Frontend Developers

1. **Use severity codes for styling** (colors, icons)
2. **Use priority for sorting/filtering** default views
3. **Display status transitions** in alert history

### For Database Design

1. **Index on**: `status`, `severity`, `category`, `device_ip`, `occurred_at`
2. **Partition by**: `occurred_at` (for performance on large datasets)
3. **Retain raw_data**: As JSONB for debugging

---

## 8. Future Extensions

This standard may be extended for:

- **AI Triage Module**: Additional fields for ML classification
- **Runbook Integration**: Links to remediation procedures
- **SLA Tracking**: Time-to-acknowledge, time-to-resolve metrics
- **Custom Categories**: Domain-specific categorizations

All extensions MUST maintain backward compatibility with this base schema.

---

## 9. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-06 | Initial standard approved |

---

## 10. Approval

This standard is **APPROVED** and **MANDATORY** for all OpsConductor alert processing.

All connectors, normalizers, and integrations MUST comply with this specification.
