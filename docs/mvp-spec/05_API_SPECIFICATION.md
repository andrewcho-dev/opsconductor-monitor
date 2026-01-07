# 05 - API Specification

**OpsConductor MVP - REST API Endpoints**

---

## 1. API Design Principles

| Principle | Implementation |
|-----------|----------------|
| **RESTful** | Resource-based URLs, HTTP verbs |
| **Versioned** | `/api/v1/` prefix for all endpoints |
| **JSON** | All request/response bodies in JSON |
| **Authenticated** | JWT Bearer token required |
| **Consistent** | Standard response format |

---

## 2. Standard Response Format

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "total": 100,
    "page": 1,
    "per_page": 50
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ALERT_NOT_FOUND",
    "message": "Alert with ID xxx not found",
    "details": { ... }
  }
}
```

### HTTP Status Codes

| Code | Usage |
|------|-------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (delete) |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Server Error |

---

## 3. Authentication

All endpoints require authentication except `/api/v1/auth/*`.

### Headers
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

### Auth Endpoints (Existing)

```
POST   /api/v1/auth/login          # Get JWT token
POST   /api/v1/auth/refresh        # Refresh token
POST   /api/v1/auth/logout         # Invalidate token
GET    /api/v1/auth/me             # Current user info
```

---

## 4. Alerts API

### 4.1 List Alerts

```
GET /api/v1/alerts
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| status | string | active | Filter: active, acknowledged, suppressed, resolved, all |
| severity | string[] | | Filter by severity |
| category | string[] | | Filter by category |
| priority | string[] | | Filter by priority |
| device_ip | string | | Filter by device IP |
| source_system | string | | Filter by source |
| search | string | | Search title, message |
| from | datetime | | Start time |
| to | datetime | | End time |
| page | int | 1 | Page number |
| per_page | int | 50 | Items per page (max 200) |
| sort | string | -occurred_at | Sort field (prefix - for desc) |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "source_system": "prtg",
      "device_ip": "10.1.1.1",
      "device_name": "Core-Switch-1",
      "severity": "critical",
      "category": "network",
      "alert_type": "link_down",
      "title": "Interface Down - Gi0/1",
      "message": "Interface GigabitEthernet0/1 is down",
      "status": "active",
      "priority": "P1",
      "occurred_at": "2026-01-06T21:00:00Z",
      "received_at": "2026-01-06T21:00:01Z"
    }
  ],
  "meta": {
    "total": 150,
    "page": 1,
    "per_page": 50,
    "pages": 3
  }
}
```

### 4.2 Get Alert

```
GET /api/v1/alerts/{alert_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "source_system": "prtg",
    "source_alert_id": "1234",
    "device_ip": "10.1.1.1",
    "device_name": "Core-Switch-1",
    "severity": "critical",
    "category": "network",
    "alert_type": "link_down",
    "title": "Interface Down - Gi0/1",
    "message": "Interface GigabitEthernet0/1 is down",
    "status": "active",
    "is_clear": false,
    "impact": "high",
    "urgency": "high",
    "priority": "P1",
    "occurred_at": "2026-01-06T21:00:00Z",
    "received_at": "2026-01-06T21:00:01Z",
    "acknowledged_at": null,
    "acknowledged_by": null,
    "resolved_at": null,
    "resolved_by": null,
    "correlated_to_id": null,
    "tags": ["production", "critical-path"],
    "occurrence_count": 1,
    "raw_data": { ... },
    "history": [
      {
        "action": "created",
        "created_at": "2026-01-06T21:00:01Z"
      }
    ]
  }
}
```

### 4.3 Acknowledge Alert

```
POST /api/v1/alerts/{alert_id}/acknowledge
```

**Request:**
```json
{
  "notes": "Investigating the issue"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "status": "acknowledged",
    "acknowledged_at": "2026-01-06T21:05:00Z",
    "acknowledged_by": "jsmith"
  }
}
```

### 4.4 Resolve Alert

```
POST /api/v1/alerts/{alert_id}/resolve
```

**Request:**
```json
{
  "notes": "Replaced faulty cable, link restored"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "status": "resolved",
    "resolved_at": "2026-01-06T21:30:00Z",
    "resolved_by": "jsmith"
  }
}
```

### 4.5 Add Note to Alert

```
POST /api/v1/alerts/{alert_id}/notes
```

**Request:**
```json
{
  "notes": "Escalated to network team"
}
```

### 4.6 Get Alert History

```
GET /api/v1/alerts/{alert_id}/history
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "action": "acknowledged",
      "old_status": "active",
      "new_status": "acknowledged",
      "user_name": "jsmith",
      "notes": "Looking into it",
      "created_at": "2026-01-06T21:05:00Z"
    }
  ]
}
```

### 4.7 Bulk Actions

```
POST /api/v1/alerts/bulk/acknowledge
POST /api/v1/alerts/bulk/resolve
```

**Request:**
```json
{
  "alert_ids": ["uuid1", "uuid2", "uuid3"],
  "notes": "Bulk acknowledged during maintenance"
}
```

### 4.8 Alert Statistics

```
GET /api/v1/alerts/stats
```

**Query Parameters:** Same filters as list alerts

**Response:**
```json
{
  "success": true,
  "data": {
    "total_active": 42,
    "by_severity": {
      "critical": 5,
      "major": 12,
      "minor": 15,
      "warning": 10
    },
    "by_category": {
      "network": 20,
      "power": 8,
      "video": 14
    },
    "by_status": {
      "active": 42,
      "acknowledged": 15
    }
  }
}
```

---

## 5. Dependencies API

### 5.1 List Dependencies

```
GET /api/v1/dependencies
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| device_ip | string | Filter by device |
| depends_on_ip | string | Filter by upstream device |
| type | string | Filter by dependency type |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "device_ip": "10.1.1.10",
      "device_name": "Camera-Lobby",
      "depends_on_ip": "10.1.1.1",
      "depends_on_name": "Core-Switch-1",
      "dependency_type": "network",
      "description": "Connected via port Gi0/5",
      "created_at": "2026-01-06T12:00:00Z"
    }
  ]
}
```

### 5.2 Get Device Dependencies

```
GET /api/v1/dependencies/device/{device_ip}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "device_ip": "10.1.1.10",
    "device_name": "Camera-Lobby",
    "upstream": [
      {
        "device_ip": "10.1.1.1",
        "device_name": "Core-Switch-1",
        "dependency_type": "network"
      }
    ],
    "downstream": [
      {
        "device_ip": "10.1.1.20",
        "device_name": "NVR-1",
        "dependency_type": "service"
      }
    ]
  }
}
```

### 5.3 Create Dependency

```
POST /api/v1/dependencies
```

**Request:**
```json
{
  "device_ip": "10.1.1.10",
  "depends_on_ip": "10.1.1.1",
  "dependency_type": "network",
  "description": "Connected via port Gi0/5"
}
```

### 5.4 Update Dependency

```
PUT /api/v1/dependencies/{dependency_id}
```

### 5.5 Delete Dependency

```
DELETE /api/v1/dependencies/{dependency_id}
```

### 5.6 Bulk Create Dependencies

```
POST /api/v1/dependencies/bulk
```

**Request:**
```json
{
  "dependencies": [
    {
      "device_ip": "10.1.1.10",
      "depends_on_ip": "10.1.1.1",
      "dependency_type": "network"
    },
    {
      "device_ip": "10.1.1.11",
      "depends_on_ip": "10.1.1.1",
      "dependency_type": "network"
    }
  ]
}
```

---

## 6. Connectors API

### 6.1 List Connectors

```
GET /api/v1/connectors
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "name": "PRTG Production",
      "type": "prtg",
      "enabled": true,
      "status": "connected",
      "last_poll_at": "2026-01-06T21:00:00Z",
      "alerts_received": 1523,
      "alerts_today": 42
    }
  ]
}
```

### 6.2 Get Connector

```
GET /api/v1/connectors/{connector_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "PRTG Production",
    "type": "prtg",
    "enabled": true,
    "status": "connected",
    "config": {
      "url": "https://prtg.example.com",
      "username": "admin",
      "poll_interval": 60,
      "verify_ssl": true
    },
    "last_poll_at": "2026-01-06T21:00:00Z",
    "last_success_at": "2026-01-06T21:00:00Z",
    "alerts_received": 1523
  }
}
```

### 6.3 Create Connector

```
POST /api/v1/connectors
```

**Request:**
```json
{
  "name": "PRTG Production",
  "type": "prtg",
  "enabled": false,
  "config": {
    "url": "https://prtg.example.com",
    "username": "admin",
    "password": "secret",
    "poll_interval": 60,
    "verify_ssl": true
  }
}
```

### 6.4 Update Connector

```
PUT /api/v1/connectors/{connector_id}
```

### 6.5 Delete Connector

```
DELETE /api/v1/connectors/{connector_id}
```

### 6.6 Test Connector

```
POST /api/v1/connectors/{connector_id}/test
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "connected",
    "message": "Successfully connected to PRTG",
    "details": {
      "version": "22.1.0",
      "devices": 150,
      "sensors": 2300
    }
  }
}
```

### 6.7 Enable/Disable Connector

```
POST /api/v1/connectors/{connector_id}/enable
POST /api/v1/connectors/{connector_id}/disable
```

### 6.8 Connector Webhook (for PRTG, etc.)

```
POST /api/v1/connectors/{connector_type}/webhook
```

Receives alerts from external systems. No authentication required (use webhook secret).

---

## 7. Devices API

### 7.1 List Devices

```
GET /api/v1/devices
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| search | string | Search name, IP |
| site | string | Filter by site |
| device_type | string | Filter by type |
| status | string | Filter by status |

### 7.2 Get Device

```
GET /api/v1/devices/{device_ip}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "ip_address": "10.1.1.1",
    "name": "Core-Switch-1",
    "device_type": "Switch",
    "manufacturer": "Ciena",
    "model": "3942",
    "site": "HQ",
    "status": "active",
    "netbox_id": 123,
    "active_alerts": 2,
    "dependencies": {
      "upstream_count": 1,
      "downstream_count": 15
    }
  }
}
```

### 7.3 Get Device Alerts

```
GET /api/v1/devices/{device_ip}/alerts
```

### 7.4 Sync Devices from NetBox

```
POST /api/v1/devices/sync
```

---

## 8. Notifications API

### 8.1 List Notification Rules

```
GET /api/v1/notifications/rules
```

### 8.2 Create Notification Rule

```
POST /api/v1/notifications/rules
```

**Request:**
```json
{
  "name": "Critical Alerts to NOC",
  "enabled": true,
  "conditions": {
    "severity": ["critical", "major"],
    "category": ["network", "power"]
  },
  "channels": [
    {
      "type": "email",
      "recipients": ["noc@example.com"]
    },
    {
      "type": "webhook",
      "url": "https://slack.com/webhook/xxx"
    }
  ],
  "throttle_minutes": 5
}
```

### 8.3 Update/Delete Notification Rule

```
PUT    /api/v1/notifications/rules/{rule_id}
DELETE /api/v1/notifications/rules/{rule_id}
```

### 8.4 Test Notification

```
POST /api/v1/notifications/test
```

**Request:**
```json
{
  "channel": "email",
  "recipient": "test@example.com"
}
```

### 8.5 Notification Log

```
GET /api/v1/notifications/log
```

---

## 9. System API

### 9.1 Health Check

```
GET /api/v1/system/health
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "uptime_seconds": 86400,
    "database": "connected",
    "connectors": {
      "total": 5,
      "connected": 4,
      "error": 1
    }
  }
}
```

### 9.2 System Statistics

```
GET /api/v1/system/stats
```

**Response:**
```json
{
  "success": true,
  "data": {
    "alerts": {
      "total": 15000,
      "today": 250,
      "active": 42
    },
    "devices": {
      "total": 500
    },
    "connectors": {
      "total": 9,
      "enabled": 5
    }
  }
}
```

### 9.3 Settings

```
GET  /api/v1/system/settings
PUT  /api/v1/system/settings
```

---

## 10. OID Mappings API

### 10.1 List OID Mappings

```
GET /api/v1/oid-mappings
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| vendor | string | Filter by vendor |
| category | string | Filter by category |
| search | string | Search OID, description |

### 10.2 Create OID Mapping

```
POST /api/v1/oid-mappings
```

**Request:**
```json
{
  "oid_pattern": "1.3.6.1.4.1.6141.2.60.5.1.2.1.*",
  "vendor": "ciena",
  "alert_type": "optical_alarm",
  "category": "network",
  "default_severity": "major",
  "title_template": "Optical Alarm - {device_name}",
  "description": "Ciena optical power threshold exceeded",
  "mib_name": "WWP-LEOS-ALARM-MIB"
}
```

### 10.3 Update/Delete OID Mapping

```
PUT    /api/v1/oid-mappings/{mapping_id}
DELETE /api/v1/oid-mappings/{mapping_id}
```

---

## 11. WebSocket API

Real-time alert updates via WebSocket.

### Connection

```
ws://host/api/v1/ws/alerts?token=<jwt_token>
```

### Events Received

```json
{
  "event": "alert.created",
  "data": {
    "id": "uuid",
    "severity": "critical",
    "title": "Interface Down",
    ...
  }
}
```

```json
{
  "event": "alert.updated",
  "data": {
    "id": "uuid",
    "status": "acknowledged",
    ...
  }
}
```

```json
{
  "event": "alert.resolved",
  "data": {
    "id": "uuid"
  }
}
```

---

*Next: [06_CONNECTORS.md](./06_CONNECTORS.md)*
