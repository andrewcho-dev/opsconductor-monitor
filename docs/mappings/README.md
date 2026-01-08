# Alert Mapping Documentation

This directory contains the complete mapping documentation for each connector's alerts to OpsConductor's normalized alert structure.

## Purpose

These documents serve as the **authoritative reference** for how each external system's alerts are translated into OpsConductor's normalized format. They must be kept accurate and up-to-date as connectors are modified.

## Connector Mappings

| Connector | Document | Status | Last Updated |
|-----------|----------|--------|--------------|
| **PRTG** | [PRTG_ALERT_MAPPING.md](PRTG_ALERT_MAPPING.md) | ✅ Complete | 2026-01-07 |
| **Axis Cameras** | [AXIS_ALERT_MAPPING.md](AXIS_ALERT_MAPPING.md) | ✅ Complete | 2026-01-07 |
| **Eaton UPS** | EATON_ALERT_MAPPING.md | 🔲 Pending | - |
| **Cradlepoint** | CRADLEPOINT_ALERT_MAPPING.md | 🔲 Pending | - |
| **Milestone VMS** | MILESTONE_ALERT_MAPPING.md | 🔲 Pending | - |
| **MCP** | MCP_ALERT_MAPPING.md | 🔲 Pending | - |

## Normalized Alert Structure

All connectors normalize alerts to this common structure:

```python
NormalizedAlert(
    source_system: str,        # Connector identifier (e.g., "prtg", "axis")
    source_alert_id: str,      # Unique ID from source system
    severity: str,             # critical, major, minor, warning, info
    category: str,             # availability, hardware, application, etc.
    status: str,               # active, acknowledged, suppressed, resolved
    title: str,                # Human-readable alert title
    description: str,          # Detailed description
    device_ip: str,            # Device IP address
    device_name: str,          # Device display name
    alert_type: str,           # Specific alert type code
    occurred_at: datetime,     # When alert occurred
    raw_data: dict,            # Original data from source system
)
```

## Severity Levels

| Severity | Code | Description |
|----------|------|-------------|
| Critical | `critical` | Immediate action required |
| Major | `major` | Significant issue requiring attention |
| Minor | `minor` | Notable issue |
| Warning | `warning` | Potential issue or threshold exceeded |
| Info | `info` | Informational |

## Status Values

| Status | Code | Description |
|--------|------|-------------|
| Active | `active` | Alert condition currently exists |
| Acknowledged | `acknowledged` | Operator has acknowledged |
| Suppressed | `suppressed` | Temporarily suppressed |
| Resolved | `resolved` | Condition no longer exists |

## Categories

| Category | Code | Description |
|----------|------|-------------|
| Availability | `availability` | Reachability, connectivity |
| Hardware | `hardware` | Physical components |
| Application | `application` | Software, services |
| Network | `network` | Network infrastructure |
| Environmental | `environmental` | Temperature, humidity |
| Security | `security` | Tampering, unauthorized access |
| Performance | `performance` | Response times, load |
| Maintenance | `maintenance` | Updates, configuration |

## Updating Documentation

When modifying a connector:

1. **Update the mapping document** with any new alert types
2. **Update the version** and last updated date
3. **Add to revision history** at bottom of document
4. **Test the mapping** to ensure alerts normalize correctly

## Document Template

Each mapping document should include:

1. Normalized Alert Structure
2. Severity Definitions
3. Category Definitions  
4. Status Definitions
5. Source System Specific Mappings
6. Fingerprint Generation Logic
7. Reconciliation Logic
8. Example Normalized Alerts
9. Revision History
