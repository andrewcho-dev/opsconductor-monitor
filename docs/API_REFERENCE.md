# OpsConductor API Reference

Complete REST API documentation for OpsConductor. All endpoints return JSON responses.

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Response Format](#response-format)
4. [Devices API](#devices-api)
5. [Groups API](#groups-api)
6. [Workflows API](#workflows-api)
7. [Scheduler API](#scheduler-api)
8. [Credentials API](#credentials-api)
9. [Notifications API](#notifications-api)
10. [System API](#system-api)
11. [NetBox API](#netbox-api)
12. [Logs API](#logs-api)
13. [Alerts API](#alerts-api)
14. [Scans API](#scans-api)
15. [Legacy Endpoints](#legacy-endpoints)

---

## Overview

### Base URL

```
http://localhost:5000
```

### Content Type

All requests should include:
```
Content-Type: application/json
```

### Authentication

Include session token in Authorization header:
```
Authorization: Bearer <session_token>
```

---

## Authentication

### Login

```http
POST /api/auth/login
```

**Request:**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**Response (success, no 2FA):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "roles": ["admin"]
    },
    "session_token": "eyJ...",
    "refresh_token": "eyJ...",
    "expires_at": "2024-12-17T00:00:00Z"
  }
}
```

**Response (2FA required):**
```json
{
  "success": true,
  "requires_2fa": true,
  "session_token": "temporary-token",
  "methods": ["totp", "email"]
}
```

### Verify 2FA

```http
POST /api/auth/verify-2fa
```

**Request:**
```json
{
  "session_token": "temporary-token",
  "code": "123456",
  "method": "totp"
}
```

### Logout

```http
POST /api/auth/logout
```

### Refresh Token

```http
POST /api/auth/refresh
```

**Request:**
```json
{
  "refresh_token": "eyJ..."
}
```

### Get Current User

```http
GET /api/auth/me
```

### Change Password

```http
POST /api/auth/change-password
```

**Request:**
```json
{
  "current_password": "oldpass",
  "new_password": "newpass123!"
}
```

---

## Response Format

### Success Response

```json
{
  "success": true,
  "data": { ... },
  "message": "Optional success message"
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": { ... }
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 400 | Invalid input data |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Permission denied |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Devices API

### List Devices

```http
GET /api/devices
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `group_id` | integer | Filter by group |
| `status` | string | Filter by status (up, down, unknown) |
| `search` | string | Search by IP or hostname |
| `limit` | integer | Max results (default: 100) |
| `offset` | integer | Pagination offset |

**Response:**
```json
{
  "success": true,
  "data": {
    "devices": [
      {
        "id": 1,
        "ip_address": "192.168.1.1",
        "hostname": "switch-01",
        "device_type": "switch",
        "vendor": "Ciena",
        "model": "3930",
        "status": "up",
        "last_seen": "2024-12-16T12:00:00Z",
        "groups": [1, 2]
      }
    ],
    "total": 150,
    "limit": 100,
    "offset": 0
  }
}
```

### Get Device

```http
GET /api/devices/:id
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "ip_address": "192.168.1.1",
    "hostname": "switch-01",
    "device_type": "switch",
    "vendor": "Ciena",
    "model": "3930",
    "software_version": "8.15.0",
    "status": "up",
    "last_seen": "2024-12-16T12:00:00Z",
    "interfaces": [...],
    "groups": [...]
  }
}
```

### Create Device

```http
POST /api/devices
```

**Request:**
```json
{
  "ip_address": "192.168.1.100",
  "hostname": "new-switch",
  "device_type": "switch",
  "vendor": "Ciena",
  "model": "3930",
  "groups": [1]
}
```

### Update Device

```http
PUT /api/devices/:id
```

### Delete Device

```http
DELETE /api/devices/:id
```

### Get Device Interfaces

```http
GET /api/devices/:id/interfaces
```

### Get Device Power History

```http
GET /api/devices/:id/power-history
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `interface` | string | Filter by interface |
| `start` | datetime | Start time |
| `end` | datetime | End time |

---

## Groups API

### List Groups

```http
GET /api/groups
```

**Response:**
```json
{
  "success": true,
  "data": {
    "groups": [
      {
        "id": 1,
        "name": "Core Switches",
        "description": "Core network switches",
        "device_count": 12,
        "created_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

### Get Group

```http
GET /api/groups/:id
```

### Create Group

```http
POST /api/groups
```

**Request:**
```json
{
  "name": "Edge Routers",
  "description": "Edge routing devices"
}
```

### Update Group

```http
PUT /api/groups/:id
```

### Delete Group

```http
DELETE /api/groups/:id
```

### Add Device to Group

```http
POST /api/groups/:id/devices
```

**Request:**
```json
{
  "device_id": 5
}
```

### Remove Device from Group

```http
DELETE /api/groups/:id/devices/:device_id
```

### Get Group Devices

```http
GET /api/groups/:id/devices
```

---

## Workflows API

### List Workflows

```http
GET /api/workflows
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `folder_id` | string | Filter by folder |
| `tag_id` | string[] | Filter by tags |
| `search` | string | Search by name |
| `enabled` | boolean | Filter by enabled status |
| `include_templates` | boolean | Include template workflows |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid-1234",
      "name": "Network Discovery",
      "description": "Discover devices on network",
      "enabled": true,
      "folder_id": "folder-uuid",
      "tags": ["network", "discovery"],
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-12-01T00:00:00Z",
      "last_run_at": "2024-12-15T10:00:00Z",
      "last_run_status": "success"
    }
  ],
  "count": 25
}
```

### Get Workflow

```http
GET /api/workflows/:id
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid-1234",
    "name": "Network Discovery",
    "description": "Discover devices on network",
    "enabled": true,
    "nodes": [
      {
        "id": "node-1",
        "type": "trigger:manual",
        "position": { "x": 100, "y": 100 },
        "data": { ... }
      }
    ],
    "edges": [
      {
        "id": "edge-1",
        "source": "node-1",
        "target": "node-2",
        "sourceHandle": "output",
        "targetHandle": "input"
      }
    ],
    "variables": { ... },
    "settings": { ... }
  }
}
```

### Create Workflow

```http
POST /api/workflows
```

**Request:**
```json
{
  "name": "New Workflow",
  "description": "Workflow description",
  "folder_id": "folder-uuid",
  "tags": ["tag1", "tag2"],
  "nodes": [...],
  "edges": [...],
  "variables": {},
  "settings": {}
}
```

### Update Workflow

```http
PUT /api/workflows/:id
```

### Delete Workflow

```http
DELETE /api/workflows/:id
```

### Execute Workflow

```http
POST /api/workflows/:id/execute
```

**Request:**
```json
{
  "trigger_data": {
    "target": "192.168.1.1"
  },
  "test_mode": false
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "execution_id": "exec-uuid",
    "status": "running",
    "started_at": "2024-12-16T12:00:00Z"
  }
}
```

### Get Workflow Executions

```http
GET /api/workflows/:id/executions
```

### Get Execution Details

```http
GET /api/workflows/:workflow_id/executions/:execution_id
```

### Workflow Folders

```http
GET /api/workflows/folders
POST /api/workflows/folders
PUT /api/workflows/folders/:id
DELETE /api/workflows/folders/:id
```

### Workflow Tags

```http
GET /api/workflows/tags
POST /api/workflows/tags
PUT /api/workflows/tags/:id
DELETE /api/workflows/tags/:id
```

---

## Scheduler API

### List Scheduled Jobs

```http
GET /api/scheduler/jobs
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `enabled` | boolean | Filter by enabled status |
| `status` | string | Filter by status |

**Response:**
```json
{
  "success": true,
  "data": {
    "jobs": [
      {
        "id": 1,
        "name": "daily-discovery",
        "workflow_id": "uuid-1234",
        "schedule_type": "cron",
        "cron_expression": "0 0 * * *",
        "enabled": true,
        "last_run_at": "2024-12-16T00:00:00Z",
        "next_run_at": "2024-12-17T00:00:00Z",
        "last_status": "success"
      }
    ]
  }
}
```

### Get Scheduled Job

```http
GET /api/scheduler/jobs/:id
```

### Create Scheduled Job

```http
POST /api/scheduler/jobs
```

**Request:**
```json
{
  "name": "hourly-check",
  "workflow_id": "uuid-1234",
  "schedule_type": "interval",
  "interval_seconds": 3600,
  "enabled": true,
  "config": {
    "target": "192.168.1.0/24"
  }
}
```

### Update Scheduled Job

```http
PUT /api/scheduler/jobs/:id
```

### Delete Scheduled Job

```http
DELETE /api/scheduler/jobs/:id
```

### Enable/Disable Job

```http
POST /api/scheduler/jobs/:id/enable
POST /api/scheduler/jobs/:id/disable
```

### Run Job Now

```http
POST /api/scheduler/jobs/:id/run
```

### Get Job Executions

```http
GET /api/scheduler/jobs/:id/executions
```

---

## Credentials API

### List Credentials

```http
GET /api/credentials
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `type` | string | Filter by type (ssh, snmp, api_key, etc.) |
| `category` | string | Filter by category |
| `environment` | string | Filter by environment |
| `status` | string | Filter by status |
| `include_expired` | boolean | Include expired (default: true) |

**Response:**
```json
{
  "success": true,
  "data": {
    "credentials": [
      {
        "id": 1,
        "name": "Network SSH",
        "credential_type": "ssh",
        "category": "network",
        "environment": "production",
        "status": "active",
        "expires_at": "2025-12-31T00:00:00Z",
        "created_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

### Get Credential

```http
GET /api/credentials/:id
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `decrypt` | boolean | Include decrypted data |

### Create Credential

```http
POST /api/credentials
```

**Request (SSH):**
```json
{
  "name": "New SSH Credential",
  "credential_type": "ssh",
  "category": "network",
  "environment": "production",
  "username": "admin",
  "password": "secret123",
  "port": 22,
  "expires_at": "2025-12-31T00:00:00Z"
}
```

**Request (SNMP v3):**
```json
{
  "name": "SNMP v3",
  "credential_type": "snmp",
  "snmp_version": "3",
  "security_name": "snmpuser",
  "auth_protocol": "SHA",
  "auth_password": "authpass",
  "priv_protocol": "AES",
  "priv_password": "privpass"
}
```

### Update Credential

```http
PUT /api/credentials/:id
```

### Delete Credential

```http
DELETE /api/credentials/:id
```

### Rotate Credential

```http
POST /api/credentials/:id/rotate
```

### Test Credential

```http
POST /api/credentials/:id/test
```

**Request:**
```json
{
  "target": "192.168.1.1"
}
```

### Get Credential Audit Log

```http
GET /api/credentials/audit
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `credential_id` | integer | Filter by credential |
| `user_id` | integer | Filter by user |
| `action` | string | Filter by action |
| `start_date` | datetime | Start date |
| `end_date` | datetime | End date |

---

## Notifications API

### Channels

#### List Channels

```http
GET /api/notifications/channels
```

**Response:**
```json
{
  "success": true,
  "data": {
    "channels": [
      {
        "id": 1,
        "name": "Slack Alerts",
        "channel_type": "slack",
        "config": {
          "webhook_url": "https://hooks.slack.com/..."
        },
        "enabled": true,
        "last_test_at": "2024-12-15T10:00:00Z",
        "last_test_success": true
      }
    ]
  }
}
```

#### Create Channel

```http
POST /api/notifications/channels
```

**Request (Slack):**
```json
{
  "name": "Slack Alerts",
  "channel_type": "slack",
  "config": {
    "webhook_url": "https://hooks.slack.com/services/..."
  },
  "enabled": true
}
```

**Request (Email):**
```json
{
  "name": "Email Alerts",
  "channel_type": "email",
  "config": {
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "smtp_user": "alerts@example.com",
    "smtp_password": "password",
    "from_address": "alerts@example.com",
    "to_addresses": ["admin@example.com"]
  }
}
```

#### Update Channel

```http
PUT /api/notifications/channels/:id
```

#### Delete Channel

```http
DELETE /api/notifications/channels/:id
```

#### Test Channel

```http
POST /api/notifications/channels/:id/test
```

### Rules

#### List Rules

```http
GET /api/notifications/rules
```

#### Create Rule

```http
POST /api/notifications/rules
```

**Request:**
```json
{
  "name": "Device Down Alert",
  "event_type": "device.status.changed",
  "conditions": {
    "status": "down"
  },
  "channel_ids": [1, 2],
  "template_id": 1,
  "enabled": true
}
```

#### Update Rule

```http
PUT /api/notifications/rules/:id
```

#### Delete Rule

```http
DELETE /api/notifications/rules/:id
```

### Templates

#### List Templates

```http
GET /api/notifications/templates
```

#### Create Template

```http
POST /api/notifications/templates
```

**Request:**
```json
{
  "name": "Device Alert",
  "subject": "Alert: {{device.hostname}} is {{status}}",
  "body": "Device {{device.hostname}} ({{device.ip_address}}) changed status to {{status}} at {{timestamp}}.",
  "format": "text"
}
```

### Send Notification

```http
POST /api/notifications/send
```

**Request:**
```json
{
  "channel_ids": [1],
  "subject": "Test Alert",
  "message": "This is a test notification",
  "data": {}
}
```

---

## System API

### Health Check

```http
GET /api/system/health
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "database": "connected",
    "redis": "connected",
    "uptime_seconds": 86400
  }
}
```

### System Info

```http
GET /api/system/info
```

**Response:**
```json
{
  "success": true,
  "data": {
    "version": "1.0.0",
    "python_version": "3.10.12",
    "database_version": "PostgreSQL 14.5",
    "started_at": "2024-12-15T00:00:00Z"
  }
}
```

### System Statistics

```http
GET /api/system/stats
```

**Response:**
```json
{
  "success": true,
  "data": {
    "devices": {
      "total": 150,
      "up": 145,
      "down": 5
    },
    "workflows": {
      "total": 25,
      "enabled": 20
    },
    "jobs": {
      "running": 2,
      "queued": 5,
      "completed_today": 48
    }
  }
}
```

### Settings

#### Get Settings

```http
GET /api/settings
```

#### Update Settings

```http
PUT /api/settings
```

**Request:**
```json
{
  "log_level": "INFO",
  "session_timeout_hours": 24,
  "max_concurrent_jobs": 10
}
```

### Users

#### List Users

```http
GET /api/auth/users
```

#### Create User

```http
POST /api/auth/users
```

**Request:**
```json
{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "SecurePass123!",
  "roles": ["operator"]
}
```

#### Update User

```http
PUT /api/auth/users/:id
```

#### Delete User

```http
DELETE /api/auth/users/:id
```

### Roles

#### List Roles

```http
GET /api/auth/roles
```

#### Create Role

```http
POST /api/auth/roles
```

**Request:**
```json
{
  "name": "network_admin",
  "description": "Network administrators",
  "permissions": [
    "devices.*.*",
    "jobs.job.view",
    "jobs.job.execute"
  ]
}
```

---

## NetBox API

### Connection Status

```http
GET /api/netbox/status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "connected": true,
    "url": "https://netbox.example.com",
    "version": "3.5.0"
  }
}
```

### Get Devices

```http
GET /api/netbox/devices
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `site` | string | Filter by site |
| `role` | string | Filter by role |
| `status` | string | Filter by status |
| `search` | string | Search term |

### Get Sites

```http
GET /api/netbox/sites
```

### Get Device Roles

```http
GET /api/netbox/device-roles
```

### Get Device Types

```http
GET /api/netbox/device-types
```

### Sync Device

```http
POST /api/netbox/sync/:device_id
```

### Auto-Discovery

```http
POST /api/netbox/autodiscovery
```

**Request:**
```json
{
  "network": "192.168.1.0/24",
  "site_id": 1,
  "role_id": 2,
  "create_in_netbox": true
}
```

---

## Logs API

### Get Logs

```http
GET /api/logs
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `level` | string | Filter by level (DEBUG, INFO, WARNING, ERROR) |
| `source` | string | Filter by source |
| `category` | string | Filter by category |
| `search` | string | Search in message |
| `start` | datetime | Start time |
| `end` | datetime | End time |
| `limit` | integer | Max results (default: 100) |

**Response:**
```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "id": 12345,
        "timestamp": "2024-12-16T12:00:00Z",
        "level": "INFO",
        "source": "workflow",
        "category": "execution",
        "message": "Workflow completed successfully",
        "extra": {
          "workflow_id": "uuid-1234",
          "duration_ms": 5432
        }
      }
    ],
    "total": 1000
  }
}
```

### Clear Logs

```http
DELETE /api/logs
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `before` | datetime | Delete logs before this date |
| `level` | string | Delete only this level |

---

## Alerts API

### List Alerts

```http
GET /api/alerts
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status (active, acknowledged, resolved) |
| `severity` | string | Filter by severity (critical, warning, info) |
| `source` | string | Filter by source |

**Response:**
```json
{
  "success": true,
  "data": {
    "alerts": [
      {
        "id": 1,
        "title": "Device Unreachable",
        "message": "Device 192.168.1.1 is not responding",
        "severity": "critical",
        "status": "active",
        "source": "monitor",
        "device_id": 5,
        "created_at": "2024-12-16T12:00:00Z",
        "acknowledged_at": null,
        "resolved_at": null
      }
    ]
  }
}
```

### Get Alert

```http
GET /api/alerts/:id
```

### Acknowledge Alert

```http
POST /api/alerts/:id/acknowledge
```

### Resolve Alert

```http
POST /api/alerts/:id/resolve
```

### Delete Alert

```http
DELETE /api/alerts/:id
```

---

## Scans API

### Start Scan

```http
POST /api/scans
```

**Request:**
```json
{
  "type": "discovery",
  "targets": ["192.168.1.0/24"],
  "options": {
    "ping": true,
    "snmp": true,
    "ssh": false
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "scan_id": "scan-uuid",
    "status": "running",
    "started_at": "2024-12-16T12:00:00Z"
  }
}
```

### Get Scan Status

```http
GET /api/scans/:id
```

### Get Scan Progress

```http
GET /api/scans/:id/progress
```

**Response:**
```json
{
  "success": true,
  "data": {
    "scan_id": "scan-uuid",
    "status": "running",
    "progress": 45,
    "total_targets": 254,
    "completed_targets": 114,
    "discovered_devices": 23
  }
}
```

### Cancel Scan

```http
POST /api/scans/:id/cancel
```

### Get Scan Results

```http
GET /api/scans/:id/results
```

---

## Legacy Endpoints

These endpoints are maintained for backward compatibility:

### Data Endpoint

```http
GET /data
```

Returns device data in legacy format.

### Progress Endpoint

```http
GET /progress
```

Returns scan progress in legacy format.

### Scan Endpoints

```http
POST /scan
POST /scan_selected
POST /snmp_scan
POST /ssh_scan
```

### Device Groups

```http
GET /device_groups
```

### Settings

```http
GET /get_settings
POST /save_settings
POST /test_settings
```

### Topology

```http
GET /topology_data
```

### Power History

```http
GET /power_history
```

### Poller Status

```http
GET /poller/status
GET /poller/logs
POST /poller/run_all
```

---

## Rate Limiting

Currently no rate limiting is enforced. Future versions may implement:
- 100 requests per minute for authenticated users
- 10 requests per minute for unauthenticated endpoints

## Pagination

List endpoints support pagination:

```http
GET /api/devices?limit=50&offset=100
```

Response includes pagination info:
```json
{
  "data": [...],
  "total": 500,
  "limit": 50,
  "offset": 100
}
```

## Filtering

Most list endpoints support filtering via query parameters:

```http
GET /api/devices?status=up&group_id=1&search=switch
```

## Sorting

Some endpoints support sorting:

```http
GET /api/devices?sort=hostname&order=asc
```
