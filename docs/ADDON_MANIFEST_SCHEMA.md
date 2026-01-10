# Universal Addon Manifest Schema

This document defines the complete schema for addon manifests. The core system is 100% generic and uses these manifest configurations to handle any addon without addon-specific code.

## Design Principles

1. **All configuration in manifest** - No addon-specific code in core
2. **Sensible defaults** - Manifests only need to specify non-default values
3. **Extensible** - New features can be added without breaking existing addons
4. **Validated** - Schema can be validated before installation

---

## Required Fields

```json
{
  "id": "string",           // Unique addon identifier (lowercase, no spaces)
  "name": "string",         // Human-readable name
  "version": "string",      // Semantic version (e.g., "1.0.0")
  "description": "string",  // Brief description
  "author": "string",       // Author name
  "method": "string",       // One of: api_poll, snmp_poll, snmp_trap, webhook, ssh
  "category": "string"      // One of: video, network, wireless, power, nms, security, etc.
}
```

---

## Method-Specific Configuration

### API Polling (`method: "api_poll"`)

For addons that poll HTTP/REST APIs.

```json
{
  "api_poll": {
    "base_url_template": "string",  // URL template with {host}, {port} placeholders
    "auth_type": "string",          // "basic", "digest", or null (REQUIRED - no default)
    "verify_ssl": true,             // Whether to verify SSL certificates (default: true)
    "endpoints": [
      {
        "path": "string",           // API endpoint path
        "method": "string",         // HTTP method: GET, POST, PUT, DELETE (default: GET)
        "response_type": "string",  // "json" or "text" (default: json)
        "check": "string",          // What to check: "reachability", "storage", etc.
        "alert_on_failure": "string" // Alert type to create if endpoint fails
      }
    ]
  },
  "default_credentials": {
    "username": "string",           // Default username (can be overridden per-target)
    "password": "string"            // Default password (can be overridden per-target)
  }
}
```

**Auth Type Options:**
| Value | Description | Use Case |
|-------|-------------|----------|
| `"basic"` | HTTP Basic Authentication | Most REST APIs, UniFi, Cradlepoint |
| `"digest"` | HTTP Digest Authentication | Axis cameras, some legacy systems |
| `null` | No authentication | Public APIs, API key only |

### SNMP Polling (`method: "snmp_poll"`)

For addons that poll devices via SNMP GET/WALK.

```json
{
  "snmp_poll": {
    "version": "string",            // "1", "2c", or "3" (default: "2c")
    "port": 161,                    // SNMP port (default: 161)
    "default_community": "string",  // Default community string (default: "public")
    "poll_groups": [
      {
        "name": "string",           // Group name for organization
        "oids": [
          {
            "oid": "string",        // OID to poll
            "name": "string"        // Human-readable name
          }
        ],
        "alert_conditions": [
          {
            "field": "string",      // OID to check
            "operator": "string",   // equals, not_equals, greater_than, less_than, contains
            "value": "any",         // Threshold value
            "alert_type": "string"  // Alert type to create
          }
        ]
      }
    ]
  }
}
```

### SNMP Trap Receiver (`method: "snmp_trap"`)

For addons that receive SNMP traps.

```json
{
  "snmp_trap": {
    "enterprise_oid": "string",     // Enterprise OID prefix to match (e.g., "1.3.6.1.4.1.31926")
    "trap_definitions": {
      "<trap_oid>": {
        "alert_type": "string",     // Alert type to create
        "description": "string",    // Human-readable description
        "clear_oid": "string"       // Optional: OID that clears this trap
      }
    },
    "varbind_mappings": {
      "<oid>": "string"             // Map varbind OID to field name
    }
  }
}
```

### Webhook Receiver (`method: "webhook"`)

For addons that receive HTTP webhooks.

```json
{
  "webhook": {
    "endpoint_path": "string",      // Webhook path (e.g., "/webhooks/prtg")
    "auth_token": "string",         // Optional: Expected auth token
    "content_type": "string"        // Expected content type (default: "application/json")
  }
}
```

### SSH Polling (`method: "ssh"`)

For addons that poll devices via SSH commands.

```json
{
  "ssh": {
    "port": 22,                     // SSH port (default: 22)
    "commands": [
      {
        "command": "string",        // Command to execute
        "parse_type": "string"      // How to parse output: "json", "regex", "key_value"
      }
    ]
  }
}
```

---

## Alert Mappings

Define all alert types the addon can produce.

```json
{
  "alert_mappings": [
    {
      "group": "string",            // Group name for UI organization
      "alerts": [
        {
          "alert_type": "string",   // Unique alert type identifier
          "enabled": true,          // Whether this alert is enabled by default
          "severity": "string",     // critical, major, minor, warning, info, clear
          "category": "string",     // video, network, power, storage, etc.
          "title": "string",        // Human-readable title
          "description": "string"   // Detailed description for operators
        }
      ]
    }
  ]
}
```

**Severity Levels (RFC 5424 inspired):**
| Level | Description |
|-------|-------------|
| `critical` | Immediate action required, service impacting |
| `major` | Significant issue, needs attention soon |
| `minor` | Minor issue, can wait for scheduled maintenance |
| `warning` | Potential issue, monitor closely |
| `info` | Informational, no action needed |
| `clear` | Condition has cleared, auto-resolves related alerts |

---

## Clear Events

Define how alerts are auto-resolved.

```json
{
  "clear_events": {
    "method": "string",             // "reconciliation", "suffix", "field_value", "oid_pair"
    "clear_suffix": "string",       // For suffix method: e.g., "_clear"
    "clear_field": "string",        // For field_value method: field to check
    "clear_values": ["string"],     // For field_value method: values that indicate clear
    "description": "string"         // Human-readable description
  }
}
```

**Clear Methods:**
| Method | Description |
|--------|-------------|
| `reconciliation` | Alert auto-resolves when polling succeeds |
| `suffix` | Alert type ending with suffix (e.g., `_clear`) resolves base alert |
| `field_value` | Field value matches clear values |
| `oid_pair` | SNMP trap OID has paired clear OID |

---

## Parser Configuration

Define how to parse raw data into alerts.

```json
{
  "parser": {
    "type": "string",               // "json", "snmp", "regex", "grok", "key_value"
    "field_mappings": {
      "alert_type": "$.path.to.field",
      "device_ip": "$.source_ip",
      "message": "$.description"
    }
  },
  "transformations": {
    "<field_name>": {
      "type": "string",             // "lookup", "datetime", "extract_ip", "lowercase", "uppercase"
      "map": {},                    // For lookup type
      "format": "string",           // For datetime type
      "pattern": "string"           // For extract_ip type
    }
  }
}
```

---

## Complete Example: Axis Camera Addon

```json
{
  "id": "axis",
  "name": "Axis Cameras",
  "version": "1.0.0",
  "description": "Axis camera monitoring via VAPIX API",
  "author": "OpsConductor",
  "method": "api_poll",
  "category": "video",
  "api_poll": {
    "base_url_template": "http://{host}",
    "auth_type": "digest",
    "verify_ssl": false,
    "endpoints": [
      {
        "path": "/axis-cgi/basicdeviceinfo.cgi",
        "method": "GET",
        "response_type": "text",
        "check": "reachability",
        "alert_on_failure": "camera_offline"
      }
    ]
  },
  "default_credentials": {
    "username": "root",
    "password": ""
  },
  "alert_mappings": [
    {
      "group": "Video & Camera Events",
      "alerts": [
        {
          "alert_type": "camera_offline",
          "enabled": true,
          "severity": "critical",
          "category": "video",
          "title": "Camera Offline",
          "description": "Camera is not responding to API requests"
        }
      ]
    }
  ],
  "clear_events": {
    "method": "reconciliation",
    "description": "Alerts auto-resolve when polling succeeds"
  }
}
```

---

## Target Configuration

Targets (devices to monitor) are stored in the database, not the manifest. Each target can override manifest defaults:

```json
{
  "id": 1,
  "addon_id": "axis",
  "name": "Lobby Camera",
  "ip_address": "10.1.1.100",
  "enabled": true,
  "poll_interval": 300,
  "config": {
    "username": "admin",           // Override default_credentials
    "password": "secret",
    "port": 8080,                  // Override default port
    "headers": {},                 // Additional headers
    "api_key": "string"            // API key if needed
  }
}
```

---

## Validation Rules

1. **id** - Must be lowercase, alphanumeric with underscores only
2. **method** - Must be one of the supported methods
3. **api_poll.auth_type** - Must be explicitly set (no default to avoid confusion)
4. **alert_mappings** - At least one alert type required
5. **severity** - Must be valid severity level
6. **category** - Should match predefined categories for consistency

---

## Adding New Addon Requirements

When a new addon needs a feature not in this schema:

1. **Check if existing options cover it** - Often existing config can handle it
2. **Add to manifest schema** - If truly new, add generic option to schema
3. **Update core to read it** - Core reads from manifest, never hardcodes addon IDs
4. **Document the option** - Add to this schema document

**NEVER add addon-specific code to core.** All behavior differences must come from manifest configuration.
