# OpsConductor Addon Architecture

## Overview

This document defines the interfaces between the Core System, Addons, and Frontend.

---

## 1. Core Infrastructure Methods

Each addon must specify which core method it uses. The core provides these infrastructure methods:

| Method | Direction | Description |
|--------|-----------|-------------|
| `snmp_trap` | Inbound | Receives SNMP traps on UDP 162 |
| `snmp_poll` | Outbound | Polls devices via SNMP GET/WALK |
| `ssh` | Outbound | Executes commands via SSH |
| `api_poll` | Outbound | Polls HTTP/REST endpoints |
| `webhook` | Inbound | Receives HTTP POST callbacks |

---

## 2. Addon Manifest Schema

Every addon MUST have a `manifest.json` with these sections:

### 2.1 Required Base Fields

```json
{
  "id": "string",           // Unique identifier (lowercase, no spaces)
  "name": "string",         // Display name
  "version": "string",      // Semantic version
  "description": "string",  // Brief description
  "author": "string",       // Author/organization
  "method": "string",       // One of: snmp_trap, snmp_poll, ssh, api_poll, webhook
  "category": "string"      // nms, device, security, etc.
}
```

### 2.2 Method-Specific Configuration

Each method type requires specific configuration:

---

#### METHOD: `snmp_trap` (Inbound)

```json
{
  "method": "snmp_trap",
  "snmp_trap": {
    "enterprise_oid": "1.3.6.1.4.1.XXXXX",    // Required: Enterprise OID prefix to match
    "trap_definitions": {
      "<full_trap_oid>": {
        "alert_type": "string",               // Internal alert type name
        "clear_oid": "string|null",           // OID that clears this alert (null if none)
        "description": "string"
      }
    },
    "varbind_mappings": {
      "<oid>": "field_name"                   // Map varbind OIDs to field names
    }
  }
}
```

**How Core Uses This:**
1. Trap Receiver receives trap with OID `1.3.6.1.4.1.31926.x.x.x`
2. Core matches `enterprise_oid` prefix → finds Siklu addon
3. Core looks up specific trap in `trap_definitions` → gets `alert_type`
4. Core extracts fields using `varbind_mappings`
5. Core applies `severity_mappings` and `category_mappings`
6. Core creates NormalizedAlert

---

#### METHOD: `snmp_poll` (Outbound)

```json
{
  "method": "snmp_poll",
  "snmp_poll": {
    "port": 161,
    "version": "v2c|v3",
    "default_community": "public",
    "poll_groups": [
      {
        "name": "interface_status",
        "interval_seconds": 60,
        "oids": [
          {
            "oid": "1.3.6.1.2.1.2.2.1.8",     // ifOperStatus
            "type": "walk",                    // get or walk
            "field": "oper_status"
          }
        ],
        "alert_condition": {
          "field": "oper_status",
          "operator": "equals",
          "value": 2,
          "alert_type": "interface_down"
        }
      }
    ]
  }
}
```

**How Core Uses This:**
1. Celery Beat schedules poll task based on `interval_seconds`
2. Core SNMP Poller connects to device using addon's config
3. Core executes OID queries defined in `poll_groups`
4. Core evaluates `alert_condition` rules
5. If condition met → creates alert using `alert_type`
6. Core applies mappings → NormalizedAlert

---

#### METHOD: `ssh` (Outbound)

```json
{
  "method": "ssh",
  "ssh": {
    "port": 22,
    "auth_methods": ["password", "key"],
    "commands": [
      {
        "name": "show_alarms",
        "command": "show alarms active",
        "interval_seconds": 300,
        "parser": "regex|json|csv|custom",
        "parse_rules": {
          "pattern": "^(\\S+)\\s+(\\S+)\\s+(.*)$",
          "fields": ["timestamp", "severity", "message"]
        },
        "alert_type_field": "severity"
      }
    ]
  }
}
```

**How Core Uses This:**
1. Celery Beat schedules SSH task
2. Core SSH Client connects to device
3. Core executes `command` string
4. Core parses output using `parse_rules`
5. Core creates alerts from parsed rows
6. Core applies mappings → NormalizedAlert

---

#### METHOD: `api_poll` (Outbound)

```json
{
  "method": "api_poll",
  "api_poll": {
    "base_url_template": "https://{host}:{port}/api/v1",
    "auth_type": "basic|bearer|api_key|none",
    "auth_header": "X-API-Key",
    "endpoints": [
      {
        "name": "get_alerts",
        "path": "/alerts",
        "method": "GET",
        "interval_seconds": 60,
        "response_type": "json",
        "alerts_path": "$.data.alerts",        // JSONPath to alerts array
        "field_mappings": {
          "alert_type": "$.type",
          "message": "$.description",
          "device_ip": "$.source.ip",
          "timestamp": "$.created_at"
        }
      }
    ]
  }
}
```

**How Core Uses This:**
1. Celery Beat schedules API poll task
2. Core API Client makes request to endpoint
3. Core extracts alerts using `alerts_path`
4. Core maps fields using `field_mappings`
5. Core applies severity/category mappings → NormalizedAlert

---

#### METHOD: `webhook` (Inbound)

```json
{
  "method": "webhook",
  "webhook": {
    "endpoint_path": "/webhooks/prtg",         // Core registers this route
    "auth_type": "none|header|query_param",
    "auth_key": "X-PRTG-Token",
    "request_type": "json|form|xml",
    "field_mappings": {
      "alert_type": "$.sensortype",
      "message": "$.message",
      "device_ip": "$.host",
      "device_name": "$.device"
    }
  }
}
```

**How Core Uses This:**
1. Core Webhook Receiver registers endpoint at `endpoint_path`
2. External system POSTs to that endpoint
3. Core extracts fields using `field_mappings`
4. Core applies severity/category mappings → NormalizedAlert

---

## 3. Common Addon Sections

All addons, regardless of method, include these sections:

### 3.1 Severity Mappings

```json
{
  "severity_mappings": {
    "<alert_type>": "critical|major|minor|warning|info|clear",
    "rf_link_down": "critical",
    "rssi_low": "warning",
    "config_change": "info"
  }
}
```

### 3.2 Category Mappings

```json
{
  "category_mappings": {
    "<alert_type>": "<category>",
    "rf_link_down": "wireless",
    "rssi_low": "wireless",
    "temperature_high": "environment"
  }
}
```

### 3.3 Clear Event Definitions

```json
{
  "clear_events": {
    "method": "oid_pair|suffix|field_value",
    
    // For oid_pair (SNMP traps with separate clear OID)
    "oid_pairs": {
      "1.3.6.1.4.1.31926.1.1.2.1.1": "1.3.6.1.4.1.31926.1.1.2.1.2"
    },
    
    // For suffix (alert_type ends with _clear)
    "clear_suffix": "_clear",
    
    // For field_value (a field indicates clear)
    "clear_field": "status",
    "clear_values": ["resolved", "cleared", "ok"]
  }
}
```

### 3.4 Device Identification

```json
{
  "device_identification": {
    "ip_field": "source_ip",                   // Which field contains device IP
    "name_field": "device_name",               // Optional: device name field
    "identifier_oids": [                       // For SNMP: OIDs to identify device type
      "1.3.6.1.2.1.1.1.0"                      // sysDescr
    ],
    "identifier_patterns": [
      "Siklu.*EtherHaul"                       // Regex to match sysDescr
    ]
  }
}
```

---

## 4. Core-Addon Interface

### 4.1 Addon Registration

When addon is installed, Core:
1. Reads `manifest.json`
2. Validates required fields
3. Registers with appropriate infrastructure:
   - `snmp_trap`: Adds enterprise OID to trap dispatcher
   - `webhook`: Registers HTTP endpoint
   - `snmp_poll`/`ssh`/`api_poll`: Creates Celery Beat schedule entries
4. Loads mappings into database
5. Marks addon as active

### 4.2 Addon Lifecycle Hooks

```
install   → load manifest → register with core → load mappings → enable
uninstall → disable → unregister from core → remove mappings → delete files
enable    → register with core infrastructure
disable   → unregister from core infrastructure (keep data)
```

### 4.3 Runtime Interface

Core infrastructure calls addon definitions at runtime:

```python
# Pseudocode: Core Trap Receiver
def handle_trap(trap):
    # 1. Find addon by enterprise OID
    addon = addon_registry.find_by_oid(trap.enterprise_oid)
    
    # 2. Get trap definition
    trap_def = addon.manifest['snmp_trap']['trap_definitions'].get(trap.oid)
    
    # 3. Extract fields using addon's varbind mappings
    fields = extract_fields(trap, addon.manifest['snmp_trap']['varbind_mappings'])
    
    # 4. Get alert type
    alert_type = trap_def['alert_type']
    
    # 5. Apply addon's severity/category mappings
    severity = addon.manifest['severity_mappings'].get(alert_type, 'warning')
    category = addon.manifest['category_mappings'].get(alert_type, 'unknown')
    
    # 6. Check if clear event
    is_clear = check_clear_event(trap, addon.manifest['clear_events'])
    
    # 7. Create normalized alert
    return NormalizedAlert(
        connector_type=addon.id,
        alert_type=alert_type,
        severity=severity,
        category=category,
        is_clear=is_clear,
        **fields
    )
```

---

## 5. Core-Frontend Interface

### 5.1 Addon Management API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/addons` | GET | List all addons |
| `/api/v1/addons/{id}` | GET | Get addon details |
| `/api/v1/addons/install` | POST | Install addon (upload zip) |
| `/api/v1/addons/{id}` | DELETE | Uninstall addon |
| `/api/v1/addons/{id}/enable` | POST | Enable addon |
| `/api/v1/addons/{id}/disable` | POST | Disable addon |
| `/api/v1/addons/{id}/config` | GET/PUT | Get/update addon config |

### 5.2 System Monitoring API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/system/celery/workers` | GET | List Celery workers, status |
| `/api/v1/system/celery/queues` | GET | Queue depths |
| `/api/v1/system/celery/tasks` | GET | Active/scheduled tasks |
| `/api/v1/system/health` | GET | System health (CPU, memory, DB) |
| `/api/v1/system/trap-receiver` | GET | Trap receiver status, stats |

### 5.3 Target/Device Management API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/targets` | GET/POST | List/create monitored devices |
| `/api/v1/targets/{id}` | GET/PUT/DELETE | Manage specific target |
| `/api/v1/targets/{id}/addon` | PUT | Assign addon to target |

---

## 6. Database Schema for Addons

### 6.1 Addon Registry

```sql
CREATE TABLE addons (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    version VARCHAR(32) NOT NULL,
    method VARCHAR(32) NOT NULL,        -- snmp_trap, ssh, api_poll, etc.
    category VARCHAR(32),
    description TEXT,
    author VARCHAR(128),
    manifest JSONB NOT NULL,            -- Full manifest.json
    enabled BOOLEAN DEFAULT true,
    installed BOOLEAN DEFAULT true,
    is_builtin BOOLEAN DEFAULT false,
    installed_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 6.2 Addon-Specific Mappings

```sql
-- Severity mappings owned by addon
CREATE TABLE addon_severity_mappings (
    id SERIAL PRIMARY KEY,
    addon_id VARCHAR(64) REFERENCES addons(id) ON DELETE CASCADE,
    alert_type VARCHAR(128) NOT NULL,
    severity VARCHAR(32) NOT NULL,
    UNIQUE(addon_id, alert_type)
);

-- Category mappings owned by addon
CREATE TABLE addon_category_mappings (
    id SERIAL PRIMARY KEY,
    addon_id VARCHAR(64) REFERENCES addons(id) ON DELETE CASCADE,
    alert_type VARCHAR(128) NOT NULL,
    category VARCHAR(64) NOT NULL,
    UNIQUE(addon_id, alert_type)
);
```

### 6.3 Targets/Devices

```sql
CREATE TABLE targets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    ip_address INET NOT NULL,
    addon_id VARCHAR(64) REFERENCES addons(id),
    credentials_id INTEGER REFERENCES credentials(id),
    poll_interval INTEGER DEFAULT 300,
    enabled BOOLEAN DEFAULT true,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 7. Complete Addon Package Structure

```
addon-id.zip
├── manifest.json              # Required: All definitions
├── README.md                  # Documentation
├── migrations/
│   ├── install.sql            # Load mappings into DB
│   └── uninstall.sql          # Remove mappings from DB
├── config/
│   ├── schema.json            # Config field definitions for UI
│   └── defaults.json          # Default config values
└── parsers/                   # Optional: Custom parsers (if needed)
    └── custom_parser.py       # Only for complex parsing not covered by rules
```

---

## 8. Example: Complete Siklu Addon

```json
{
  "id": "siklu",
  "name": "Siklu EtherHaul",
  "version": "1.0.0",
  "description": "Siklu wireless backhaul monitoring via SNMP traps",
  "author": "OpsConductor",
  "method": "snmp_trap",
  "category": "wireless",
  
  "snmp_trap": {
    "enterprise_oid": "1.3.6.1.4.1.31926",
    "trap_definitions": {
      "1.3.6.1.4.1.31926.1.1.2.1.1": {
        "alert_type": "rf_link_down",
        "clear_oid": "1.3.6.1.4.1.31926.1.1.2.1.2",
        "description": "RF link has gone down"
      },
      "1.3.6.1.4.1.31926.1.2.1.3.1": {
        "alert_type": "rssi_low",
        "clear_oid": "1.3.6.1.4.1.31926.1.2.1.3.2",
        "description": "RSSI below threshold"
      },
      "1.3.6.1.4.1.31926.1.5.1.0": {
        "alert_type": "device_reboot",
        "clear_oid": null,
        "description": "Device rebooted"
      }
    },
    "varbind_mappings": {
      "1.3.6.1.4.1.31926.1.1.1.0": "link_name",
      "1.3.6.1.4.1.31926.1.2.1.1.0": "rssi_value"
    }
  },
  
  "device_identification": {
    "ip_field": "source_ip",
    "identifier_oids": ["1.3.6.1.2.1.1.1.0"],
    "identifier_patterns": ["Siklu.*EtherHaul"]
  },
  
  "severity_mappings": {
    "rf_link_down": "critical",
    "rssi_low": "warning",
    "device_reboot": "major"
  },
  
  "category_mappings": {
    "rf_link_down": "wireless",
    "rssi_low": "wireless",
    "device_reboot": "system"
  },
  
  "clear_events": {
    "method": "oid_pair"
  }
}
```

---

## 9. Core Parser Library

Addons are **100% declarative** - no custom code. The core provides these parser types:

### 9.1 Parser Types

| Parser Type | Use Case | Example |
|-------------|----------|---------|
| `json` | JSON API responses | REST APIs |
| `xml` | XML responses | SOAP, some NMS |
| `regex` | Single-line pattern matching | Simple logs |
| `grok` | Named pattern extraction | Syslog, structured logs |
| `multiline` | Multi-line record parsing | SSH command output |
| `key_value` | Key: Value or Key=Value | Config output |
| `table` | Tabular data with headers | CLI table output |
| `snmp` | SNMP varbind extraction | Traps and polls |

### 9.2 JSON Parser

```json
{
  "parser": {
    "type": "json",
    "alerts_path": "$.data.alerts[*]",
    "field_mappings": {
      "alert_type": "$.type",
      "message": "$.description",
      "device_ip": "$.source.ip",
      "timestamp": "$.created_at"
    }
  }
}
```

### 9.3 Regex Parser

```json
{
  "parser": {
    "type": "regex",
    "pattern": "^(\\d{4}-\\d{2}-\\d{2})\\s+(\\w+)\\s+(.*)$",
    "fields": ["timestamp", "severity", "message"]
  }
}
```

### 9.4 Grok Parser (Syslog-style)

```json
{
  "parser": {
    "type": "grok",
    "pattern": "%{SYSLOGTIMESTAMP:timestamp} %{WORD:host} %{WORD:facility}-%{INT:level}-%{INT:code}: %{GREEDYDATA:message}",
    "custom_patterns": {
      "CISCO_ACTION": "(Deny|Permit|Drop)"
    }
  }
}
```

Built-in Grok patterns include: `IP`, `INT`, `WORD`, `GREEDYDATA`, `SYSLOGTIMESTAMP`, `MAC`, `HOSTNAME`, etc.

### 9.5 Multiline Parser

For SSH output spanning multiple lines per record:

```json
{
  "parser": {
    "type": "multiline",
    "record_start": "^Alarm ID:",
    "record_end": "^---$",
    "field_patterns": {
      "id": "Alarm ID:\\s*(\\d+)",
      "type": "Type:\\s*(\\w+)",
      "severity": "Severity:\\s*(\\w+)",
      "description": "Description:\\s*(.+)",
      "timestamp": "Timestamp:\\s*(.+)"
    }
  }
}
```

### 9.6 Key-Value Parser

```json
{
  "parser": {
    "type": "key_value",
    "delimiter": ":",
    "trim": true,
    "field_mappings": {
      "Status": "status",
      "Error Count": "error_count",
      "Last Update": "timestamp"
    }
  }
}
```

### 9.7 Table Parser

For CLI table output:

```json
{
  "parser": {
    "type": "table",
    "header_row": 0,
    "separator": "\\s{2,}",
    "field_mappings": {
      "Interface": "interface",
      "Status": "status",
      "Speed": "speed"
    }
  }
}
```

### 9.8 SNMP Parser

For SNMP traps and polls:

```json
{
  "parser": {
    "type": "snmp",
    "varbind_mappings": {
      "1.3.6.1.4.1.31926.1.1.1.0": "link_name",
      "1.3.6.1.4.1.31926.1.2.1.1.0": "rssi_value"
    },
    "index_position": 1
  }
}
```

### 9.9 Transformations

All parsers support post-extraction transformations:

```json
{
  "transformations": {
    "timestamp": {
      "type": "datetime",
      "format": "%Y-%m-%d %H:%M:%S"
    },
    "severity": {
      "type": "lookup",
      "map": {
        "1": "critical",
        "2": "major",
        "3": "minor",
        "4": "warning"
      }
    },
    "device_ip": {
      "type": "extract_ip",
      "pattern": "(\\d+\\.\\d+\\.\\d+\\.\\d+)"
    }
  }
}
```

---

## 10. Current Connectors → Declarative Mapping

| Current Connector | Method | Parser Type |
|-------------------|--------|-------------|
| Siklu | `snmp_trap` | `snmp` |
| Ubiquiti | `snmp_trap` | `snmp` |
| Axis | `webhook` | `json` |
| PRTG | `webhook` | `json`/`form` |
| Milestone | `webhook` | `json` |
| Eaton | `snmp_trap` | `snmp` |
| MCP | `api_poll` | `json` |
| Cradlepoint | `api_poll` | `json` |
| Cisco ASA | `snmp_trap` | `grok` (syslog) |

All current connectors can be expressed declaratively using these parser types.

---

## Summary

| Interface | Purpose |
|-----------|---------|
| **Addon Manifest** | Declarative definition of how to connect, parse, map |
| **Core-Addon** | Core reads manifest, registers addon, uses definitions at runtime |
| **Core-Frontend** | REST APIs for addon management, system monitoring, targets |
| **Core Parsers** | Library of parser types (json, regex, grok, multiline, etc.) |
| **Database** | Stores addon registry, mappings (owned by addon), targets |

The addon is **100% declarative** - no custom code. The core **executes** based on those declarations.
