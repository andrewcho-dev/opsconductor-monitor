# API Migration Plan: Legacy to OpenAPI 3.x Standards

## Overview
This document outlines the migration path from the current `/api/*` endpoint structure to the new domain-based organization following OpenAPI 3.x standards.

## Current vs New Structure

### Current Structure (Legacy)
```
/api/auth/login
/api/users
/api/devices
/api/alerts
/api/workflows
/api/netbox/settings
/api/prtg/status
/api/mcp/services
/api/settings
/api/logs
```

### New Structure (Standards-Based)
```
/identity/v1/auth/login
/identity/v1/users
/inventory/v1/devices
/monitoring/v1/alerts
/automation/v1/workflows
/integrations/v1/netbox/status
/integrations/v1/prtg/status
/integrations/v1/mcp/services
/system/v1/settings
/system/v1/logs
/admin/v1/metrics
```

---

## Migration Phases

### Phase 1: Setup New OpenAPI Structure (Week 1)
- [ ] Create new FastAPI app with OpenAPI 3.x structure
- [ ] Implement standard models (StandardError, PaginatedResponse, etc.)
- [ ] Add middleware for request tracking and rate limiting
- [ ] Set up authentication and authorization middleware
- [ ] Deploy alongside legacy API (different port or path prefix)

### Phase 2: Migrate Identity APIs (Week 2)
**Current → New Mapping:**
```
GET /api/auth/me → GET /identity/v1/auth/me
POST /api/auth/login → POST /identity/v1/auth/login
POST /api/auth/logout → POST /identity/v1/auth/logout
GET /api/auth/users → GET /identity/v1/users
GET /api/users → GET /identity/v1/users
GET /api/users/{id} → GET /identity/v1/users/{id}
GET /api/auth/roles → GET /identity/v1/roles
GET /api/roles → GET /identity/v1/roles
GET /api/auth/roles/{id}/members → GET /identity/v1/roles/{id}/members
GET /api/auth/password-policy → GET /identity/v1/password-policy
PUT /api/auth/password-policy → PUT /identity/v1/password-policy
```

**Tasks:**
- [ ] Implement OpenAPI models for User, Role, Auth
- [ ] Add cursor-based pagination to user lists
- [ ] Standardize error responses
- [ ] Add request ID tracking
- [ ] Update frontend to use new endpoints
- [ ] Add backward compatibility layer

### Phase 3: Migrate Inventory APIs (Week 3)
**Current → New Mapping:**
```
GET /api/devices → GET /inventory/v1/devices
GET /api/inventory/devices → GET /inventory/v1/devices
GET /api/inventory/interfaces → GET /inventory/v1/interfaces
GET /api/inventory/modules → GET /inventory/v1/modules
GET /api/inventory/links → GET /inventory/v1/links
GET /api/inventory/sites → GET /inventory/v1/sites
GET /api/inventory/racks → GET /inventory/v1/racks
GET /api/topology → GET /inventory/v1/topology
```

**Tasks:**
- [ ] Implement OpenAPI models for Device, Interface, Site, Rack
- [ ] Add filtering by site, device_type, status
- [ ] Add cursor-based pagination
- [ ] Standardize device ID format (UUID vs integer)
- [ ] Update frontend inventory pages
- [ ] Add device creation/update endpoints

### Phase 4: Migrate Monitoring APIs (Week 4)
**Current → New Mapping:**
```
GET /api/alerts → GET /monitoring/v1/alerts
POST /api/alerts/{id}/acknowledge → POST /monitoring/v1/alerts/{id}/acknowledge
GET /api/metrics/optical/{ip} → GET /monitoring/v1/devices/{id}/metrics/optical
GET /api/metrics/interfaces/{ip} → GET /monitoring/v1/devices/{id}/metrics/interfaces
GET /api/metrics/availability/{ip} → GET /monitoring/v1/devices/{id}/metrics/availability
GET /api/snmp/alarms/{host} → GET /monitoring/v1/devices/{id}/alarms
GET /api/snmp/system/{host} → GET /monitoring/v1/devices/{id}/status
GET /api/snmp/live → GET /monitoring/v1/devices/{id}/live-data
GET /api/ups/status → GET /monitoring/v1/devices/{id}/ups-status
```

**Tasks:**
- [ ] Implement OpenAPI models for Alert, Metrics, DeviceStatus
- [ ] Standardize device identification (use inventory IDs)
- [ ] Add time-series data support
- [ ] Implement real-time streaming endpoints
- [ ] Update frontend monitoring dashboards
- [ ] Add alert management endpoints

### Phase 5: Migrate Automation APIs (Week 5)
**Current → New Mapping:**
```
GET /api/workflows → GET /automation/v1/workflows
GET /api/workflows/definitions → GET /automation/v1/workflows
GET /api/workflows/executions → GET /automation/v1/jobs
GET /api/scheduler/jobs → GET /automation/v1/jobs
GET /api/scheduler/executions → GET /automation/v1/jobs
GET /api/scheduler/executions/{id}/progress → GET /automation/v1/jobs/{id}/progress
POST /api/scheduler/executions/{id}/cancel → POST /automation/v1/jobs/{id}/cancel
POST /api/workflows → POST /automation/v1/workflows
GET /api/workflows/schedules → GET /automation/v1/schedules
```

**Tasks:**
- [ ] Implement OpenAPI models for Workflow, Job, Schedule
- [ ] Add workflow execution endpoints
- [ ] Standardize job status tracking
- [ ] Add job scheduling capabilities
- [ ] Update frontend workflow builder
- [ ] Add job template management

### Phase 6: Migrate Integration APIs (Week 6)
**Current → New Mapping:**
```
GET /api/netbox/settings → GET /integrations/v1/netbox/settings
PUT /api/netbox/settings → PUT /integrations/v1/netbox/settings
POST /api/netbox/test → POST /integrations/v1/netbox/test
GET /api/prtg/settings → GET /integrations/v1/prtg/settings
PUT /api/prtg/settings → PUT /integrations/v1/prtg/settings
GET /api/prtg/status → GET /integrations/v1/prtg/status
POST /api/prtg/test → POST /integrations/v1/prtg/test
GET /api/mcp/services → GET /integrations/v1/mcp/services
GET /api/mcp/settings → GET /integrations/v1/mcp/settings
PUT /api/mcp/settings → PUT /integrations/v1/mcp/settings
POST /api/mcp/test → POST /integrations/v1/mcp/test
```

**Tasks:**
- [ ] Implement OpenAPI models for NetBox, PRTG, MCP configurations
- [ ] Add integration health monitoring
- [ ] Standardize connection testing
- [ ] Add sync status tracking
- [ ] Update frontend integration settings
- [ ] Add integration event webhooks

### Phase 7: Migrate System APIs (Week 7)
**Current → New Mapping:**
```
GET /api/health → GET /system/v1/health
GET /api/settings → GET /system/v1/settings
POST /api/save_settings → PUT /system/v1/settings
GET /api/logs → GET /system/v1/logs
GET /api/logs/sources → GET /system/v1/logs/sources
GET /api/logs/levels → GET /system/v1/logs/levels
GET /api/logs/stats → GET /system/v1/logs/stats
GET /api/notifications → GET /system/v1/notifications
GET /api/notifications/channels → GET /system/v1/notifications/channels
GET /api/notifications/rules → GET /system/v1/notifications/rules
GET /api/notifications/templates → GET /system/v1/notifications/templates
```

**Tasks:**
- [ ] Implement OpenAPI models for Settings, Logs, Notifications
- [ ] Add system metrics endpoints
- [ ] Standardize log filtering and pagination
- [ ] Add notification management
- [ ] Update frontend system pages
- [ ] Add configuration backup/restore

### Phase 8: Add Admin APIs (Week 8)
**New Endpoints:**
```
GET /admin/v1/metrics
POST /admin/v1/maintenance/enable
POST /admin/v1/maintenance/disable
DELETE /admin/v1/cache
GET /admin/v1/audit/log
POST /admin/v1/system/restart
GET /admin/v1/performance/profile
```

**Tasks:**
- [ ] Implement admin-specific models
- [ ] Add maintenance mode functionality
- [ ] Implement cache management
- [ ] Add audit trail endpoints
- [ ] Create admin dashboard
- [ ] Add performance profiling

---

## Implementation Details

### 1. OpenAPI Models
Create standardized Pydantic models:

```python
# Standard response models
class StandardError(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    limit: int
    cursor: Optional[str] = None

# Domain-specific models
class Device(BaseModel):
    id: str
    name: str
    ip_address: str
    device_type: str
    site_id: str
    status: str
    created_at: datetime
    updated_at: datetime
```

### 2. Authentication Middleware
```python
from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    # JWT validation logic
    pass

async def require_scope(scope: str):
    # Scope validation logic
    pass
```

### 3. Request Tracking Middleware
```python
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

### 4. Rate Limiting
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

@app.get("/identity/v1/users")
@limiter.limit("300/minute")
async def list_users(request: Request):
    pass
```

### 5. Cursor-based Pagination
```python
def get_cursor_params(cursor: Optional[str] = None, limit: int = 50):
    if limit > 100:
        limit = 100
    return {"cursor": cursor, "limit": limit}

def paginate_query(query, cursor: Optional[str] = None, limit: int = 50):
    if cursor:
        # Decode cursor and apply to query
        decoded = decode_cursor(cursor)
        query = query.where(table.id > decoded['last_id'])
    
    results = query.limit(limit + 1).all()
    
    has_more = len(results) > limit
    items = results[:limit] if has_more else results
    
    next_cursor = None
    if has_more and items:
        next_cursor = encode_cursor({'last_id': items[-1].id})
    
    return items, next_cursor, has_more
```

---

## Backward Compatibility Strategy

### Phase 1-2: Parallel Operation
- Run both legacy and new APIs simultaneously
- Use nginx routing to direct traffic
- Monitor for breaking changes

### Phase 3-4: Gradual Migration
- Update frontend components to use new endpoints
- Add API gateway layer for routing
- Implement feature flags for gradual rollout

### Phase 5-6: Legacy Deprecation
- Add deprecation headers to legacy endpoints
```
Warning: 299 - "Legacy API deprecated. Use /identity/v1/users instead"
```
- Send migration notices to API consumers
- Set sunset dates for legacy endpoints

### Phase 7-8: Legacy Removal
- Remove legacy endpoints after sunset date
- Clean up deprecated code
- Update documentation

---

## Testing Strategy

### 1. Contract Testing
- Use OpenAPI specs to generate tests
- Validate request/response formats
- Test error scenarios

### 2. Integration Testing
- Test authentication flows
- Verify pagination behavior
- Test rate limiting

### 3. Performance Testing
- Compare new vs legacy API performance
- Load test cursor-based pagination
- Validate rate limiting effectiveness

### 4. Migration Testing
- Test data consistency between APIs
- Verify frontend compatibility
- Test rollback procedures

---

## Rollout Plan

### Week 1: Infrastructure Setup
- Deploy new API alongside legacy
- Set up monitoring and alerting
- Configure API gateway

### Week 2-3: Core APIs
- Migrate Identity and Inventory APIs
- Update authentication flows
- Test critical user journeys

### Week 4-5: Feature APIs
- Migrate Monitoring and Automation APIs
- Update dashboards and workflows
- Performance testing

### Week 6-7: Integration & System APIs
- Migrate Integration and System APIs
- Update settings and configurations
- End-to-end testing

### Week 8: Admin & Cleanup
- Deploy Admin APIs
- Remove legacy endpoints
- Documentation updates

---

## Success Metrics

### Technical Metrics
- 100% API coverage in OpenAPI specs
- <100ms response time for 95% of requests
- 99.9% uptime during migration
- Zero data loss during transition

### Business Metrics
- No disruption to users
- All frontend features working
- Improved developer experience
- Reduced API response times

### Compliance Metrics
- All APIs follow OpenAPI 3.x standards
- Consistent error handling across APIs
- Proper authentication and authorization
- Complete audit trail for admin actions
