# OpsConductor API Catalog

## Overview
OpsConductor provides a comprehensive set of RESTful APIs organized by business capability for network monitoring and automation. All APIs follow OpenAPI 3.x specifications with consistent patterns for authentication, pagination, error handling, and request tracking.

## API Standards
- **Specification**: OpenAPI 3.x
- **Authentication**: OAuth2/JWT with role-based access control
- **Pagination**: Cursor-based with `limit` parameter
- **Error Format**: `{code, message, details, traceId}`
- **Request Tracking**: `X-Request-ID` header
- **Rate Limiting**: 300 requests per minute per API key
- **Versioning**: URL-based (`/v1/`, `/v2/`)

---

## APIs by Domain

### Identity API
**Name:** Identity API  
**Domain:** identity  
**Purpose:** Authentication, user management, and role-based access control  
**Base URL:** `https://api.opsconductor.com/identity/v1`  
**Auth:** OAuth2 (scopes: `identity.read`, `identity.write`, `identity.admin`)  
**Owner:** Platform Team  
**OpenAPI:** `/identity/v1/openapi.json`  
**Lifecycle:** GA  
**Data class:** Internal/Restricted  
**Rate limit:** 300 rpm  
**Changelog:** [link](./CHANGELOG_IDENTITY.md)  
**Runbook:** [link](./RUNBOOK_IDENTITY.md)  

**Key Endpoints:**
- `POST /auth/login` - User authentication
- `GET /auth/me` - Current user info
- `GET /users` - List users (paginated)
- `GET /roles` - List roles
- `PUT /roles/{id}/members` - Manage role membership

---

### Inventory API
**Name:** Inventory API  
**Domain:** inventory  
**Purpose:** Network device management, interface discovery, and topology mapping  
**Base URL:** `https://api.opsconductor.com/inventory/v1`  
**Auth:** OAuth2 (scopes: `inventory.read`, `inventory.write`, `inventory.admin`)  
**Owner:** Network Engineering Team  
**OpenAPI:** `/inventory/v1/openapi.json`  
**Lifecycle:** GA  
**Data class:** Internal/Restricted  
**Rate limit:** 300 rpm  
**Changelog:** [link](./CHANGELOG_INVENTORY.md)  
**Runbook:** [link](./RUNBOOK_INVENTORY.md)  

**Key Endpoints:**
- `GET /devices` - List devices with filtering
- `GET /devices/{id}` - Device details
- `GET /devices/{id}/interfaces` - Device interfaces
- `GET /topology` - Network topology graph
- `POST /devices` - Create device

---

### Monitoring API
**Name:** Monitoring API  
**Domain:** monitoring  
**Purpose:** SNMP polling, metrics collection, alerting, and telemetry  
**Base URL:** `https://api.opsconductor.com/monitoring/v1`  
**Auth:** OAuth2 (scopes: `monitoring.read`, `monitoring.write`, `monitoring.admin`)  
**Owner:** Operations Team  
**OpenAPI:** `/monitoring/v1/openapi.json`  
**Lifecycle:** GA  
**Data class:** Internal/Restricted  
**Rate limit:** 600 rpm (higher for telemetry)  
**Changelog:** [link](./CHANGELOG_MONITORING.md)  
**Runbook:** [link](./RUNBOOK_MONITORING.md)  

**Key Endpoints:**
- `GET /devices/{id}/metrics/optical` - Optical power metrics
- `GET /devices/{id}/metrics/interfaces` - Interface utilization
- `GET /alerts` - Active alerts (paginated)
- `POST /alerts/{id}/acknowledge` - Acknowledge alert
- `GET /telemetry/status` - Collection service status

---

### Automation API
**Name:** Automation API  
**Domain:** automation  
**Purpose:** Workflow execution, job scheduling, and task automation  
**Base URL:** `https://api.opsconductor.com/automation/v1`  
**Auth:** OAuth2 (scopes: `automation.read`, `automation.write`, `automation.execute`)  
**Owner:** DevOps Team  
**OpenAPI:** `/automation/v1/openapi.json`  
**Lifecycle:** GA  
**Data class:** Internal/Restricted  
**Rate limit:** 300 rpm  
**Changelog:** [link](./CHANGELOG_AUTOMATION.md)  
**Runbook:** [link](./RUNBOOK_AUTOMATION.md)  

**Key Endpoints:**
- `GET /workflows` - List workflows
- `POST /workflows/{id}/execute` - Execute workflow
- `GET /jobs` - Job executions (paginated)
- `GET /jobs/{id}` - Job details
- `POST /jobs/{id}/cancel` - Cancel running job

---

### Integrations API
**Name:** Integrations API  
**Domain:** integrations  
**Purpose:** External system integrations (NetBox, PRTG, MCP services)  
**Base URL:** `https://api.opsconductor.com/integrations/v1`  
**Auth:** OAuth2 (scopes: `integrations.read`, `integrations.write`, `integrations.admin`)  
**Owner:** Integration Team  
**OpenAPI:** `/integrations/v1/openapi.json`  
**Lifecycle:** GA  
**Data class:** Internal/Restricted  
**Rate limit:** 300 rpm  
**Changelog:** [link](./CHANGELOG_INTEGRATIONS.md)  
**Runbook:** [link](./RUNBOOK_INTEGRATIONS.md)  

**Key Endpoints:**
- `GET /netbox/status` - NetBox connection status
- `POST /netbox/sync` - Trigger NetBox sync
- `GET /prtg/status` - PRTG monitoring status
- `GET /mcp/services` - MCP service list
- `POST /mcp/test` - Test MCP connection

---

### System API
**Name:** System API  
**Domain:** system  
**Purpose:** System configuration, health monitoring, and administrative functions  
**Base URL:** `https://api.opsconductor.com/system/v1`  
**Auth:** OAuth2 (scopes: `system.read`, `system.write`, `system.admin`)  
**Owner:** Platform Team  
**OpenAPI:** `/system/v1/openapi.json`  
**Lifecycle:** GA  
**Data class:** Internal/Restricted  
**Rate limit:** 300 rpm  
**Changelog:** [link](./CHANGELOG_SYSTEM.md)  
**Runbook:** [link](./RUNBOOK_SYSTEM.md)  

**Key Endpoints:**
- `GET /health` - System health check
- `GET /settings` - System configuration
- `PUT /settings` - Update configuration
- `GET /logs` - System logs (paginated)
- `POST /settings/backup` - Backup configuration

---

### Admin API
**Name:** Admin API  
**Domain:** admin  
**Purpose:** Privileged administrative operations and system maintenance  
**Base URL:** `https://api.opsconductor.com/admin/v1`  
**Auth:** OAuth2 (scopes: `admin.full` only)  
**Owner:** Platform Team  
**OpenAPI:** `/admin/v1/openapi.json`  
**Lifecycle:** GA  
**Data class:** Restricted  
**Rate limit:** 100 rpm (lower for admin ops)  
**Changelog:** [link](./CHANGELOG_ADMIN.md)  
**Runbook:** [link](./RUNBOOK_ADMIN.md)  

**Key Endpoints:**
- `GET /metrics` - Internal system metrics
- `POST /maintenance/enable` - Enable maintenance mode
- `DELETE /cache` - Clear system caches
- `GET /audit/log` - Audit trail
- `POST /system/restart` - Restart services

---

## API Type Classification

### Public/Product APIs
- **None** - All APIs are internal to OpsConductor platform

### Internal Service APIs
- Identity API
- Inventory API  
- Monitoring API
- Automation API
- Integrations API

### Admin/Backoffice APIs
- System API
- Admin API

### Telemetry/Observability APIs
- Monitoring API (telemetry endpoints)
- System API (health/logs endpoints)
- Admin API (metrics endpoints)

---

## Cross-Cutting Standards

### Authentication
All APIs use OAuth2 with JWT tokens. Include in requests:
```
Authorization: Bearer <jwt_token>
```

### Pagination
For large datasets, use cursor-based pagination:
```
GET /inventory/v1/devices?limit=50&cursor=abc123
```

Response format:
```json
{
  "items": [...],
  "total": 1250,
  "limit": 50,
  "cursor": "def456"
}
```

### Error Handling
Standard error response:
```json
{
  "code": "DEVICE_NOT_FOUND",
  "message": "Device with ID '123' not found",
  "details": {
    "device_id": "123",
    "timestamp": "2026-01-04T20:00:00Z"
  },
  "trace_id": "abc123-def456"
}
```

### Request Tracking
Every request includes a trace ID:
```
X-Request-ID: abc123-def456-ghi789
```

### Rate Limits
- Standard APIs: 300 requests per minute
- Telemetry APIs: 600 requests per minute  
- Admin APIs: 100 requests per minute

Rate limit headers are included:
```
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 299
X-RateLimit-Reset: 1641345600
```

---

## Environment URLs

| Environment | Base URL | Purpose |
|-------------|----------|---------|
| Production | https://api.opsconductor.com | Live production traffic |
| Staging | https://staging-api.opsconductor.com | Pre-production testing |
| Development | http://localhost:5000 | Local development |

---

## Support

**Team:** Platform Engineering  
**Email:** api-support@enabledconsultants.com  
**Slack:** #opsconductor-api  
**Documentation:** https://docs.opsconductor.com/api  
**Status Page:** https://status.opsconductor.com
