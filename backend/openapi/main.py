"""
OpsConductor API - OpenAPI 3.x Specification
Network monitoring and automation platform organized by business capability
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import sys
from contextlib import asynccontextmanager

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db
from backend.services.logging_service import logging_service, get_logger, LogSource


# Standard API Models
class StandardError(BaseModel):
    """Standard error response format"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Standard paginated response format"""
    items: List[Dict[str, Any]]
    total: int
    limit: int
    cursor: Optional[str] = None


# Request/Response Models
class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    version: str
    services: Dict[str, str]


class LoginRequest(BaseModel):
    """Login request"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response"""
    success: bool
    token: Optional[str] = None
    expires_in: Optional[int] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    db = get_db()
    logging_service.initialize(db_connection=db, log_level=log_level)
    logger = get_logger(__name__, LogSource.SYSTEM)
    logger.info("OpsConductor API starting", category='startup')
    yield
    logger.info("OpsConductor API stopping", category='shutdown')


# Create FastAPI app with OpenAPI configuration
app = FastAPI(
    title="OpsConductor API",
    description="""
    ## Network Monitoring & Automation Platform
    
    ### API Organization
    - **Identity**: Authentication, users, roles, permissions
    - **Inventory**: Device management, interfaces, topology
    - **Monitoring**: SNMP polling, metrics, alerts, telemetry
    - **Automation**: Workflows, jobs, scheduling
    - **Integrations**: NetBox, PRTG, MCP services
    - **System**: Configuration, settings, logs, health
    
    ### Standards
    - OpenAPI 3.x specification
    - RESTful design with noun-based resources
    - Consistent error handling with trace IDs
    - Cursor-based pagination for large datasets
    - OAuth2/JWT authentication
    - Rate limiting by API key
    - Request ID tracking
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    servers=[
        {"url": "https://api.opsconductor.com", "description": "Production"},
        {"url": "https://staging-api.opsconductor.com", "description": "Staging"},
        {"url": "http://localhost:5000", "description": "Development"},
    ],
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware for request tracking
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add X-Request-ID header for tracing"""
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ============================================================================
# IDENTITY API (/identity/v1)
# ============================================================================

identity_tags = ["identity", "auth", "users", "roles"]

@app.post(
    "/identity/v1/auth/login",
    tags=identity_tags,
    summary="Authenticate user",
    description="Authenticate with username/password and receive JWT token",
    response_model=LoginResponse,
    responses={401: {"model": StandardError}}
)
async def identity_login(request: LoginRequest):
    """Login endpoint"""
    # Implementation would go here
    pass


@app.get(
    "/identity/v1/auth/me",
    tags=identity_tags,
    summary="Get current user",
    description="Get information about the authenticated user",
    responses={401: {"model": StandardError}}
)
async def identity_get_current_user():
    """Get current user info"""
    # Implementation would go here
    pass


@app.get(
    "/identity/v1/users",
    tags=identity_tags,
    summary="List users",
    description="List all users with cursor-based pagination",
    response_model=PaginatedResponse,
    responses={401: {"model": StandardError}}
)
async def identity_list_users(
    cursor: Optional[str] = None,
    limit: int = 50
):
    """List users"""
    # Implementation would go here
    pass


@app.get(
    "/identity/v1/roles",
    tags=identity_tags,
    summary="List roles",
    description="List all available roles",
    response_model=List[Dict[str, Any]],
    responses={401: {"model": StandardError}}
)
async def identity_list_roles():
    """List roles"""
    # Implementation would go here
    pass


# ============================================================================
# INVENTORY API (/inventory/v1)
# ============================================================================

inventory_tags = ["inventory", "devices", "interfaces", "topology"]

@app.get(
    "/inventory/v1/devices",
    tags=inventory_tags,
    summary="List devices",
    description="List all network devices with filtering and pagination",
    response_model=PaginatedResponse,
    responses={401: {"model": StandardError}}
)
async def inventory_list_devices(
    cursor: Optional[str] = None,
    limit: int = 50,
    site_id: Optional[str] = None,
    device_type: Optional[str] = None,
    status: Optional[str] = None
):
    """List devices"""
    # Implementation would go here
    pass


@app.get(
    "/inventory/v1/devices/{device_id}",
    tags=inventory_tags,
    summary="Get device details",
    description="Get detailed information about a specific device",
    responses={404: {"model": StandardError}}
)
async def inventory_get_device(device_id: str):
    """Get device details"""
    # Implementation would go here
    pass


@app.get(
    "/inventory/v1/devices/{device_id}/interfaces",
    tags=inventory_tags,
    summary="List device interfaces",
    description="List all interfaces for a specific device",
    response_model=List[Dict[str, Any]],
    responses={404: {"model": StandardError}}
)
async def inventory_list_device_interfaces(device_id: str):
    """List device interfaces"""
    # Implementation would go here
    pass


@app.get(
    "/inventory/v1/topology",
    tags=inventory_tags,
    summary="Get network topology",
    description="Get the complete network topology graph",
    responses={401: {"model": StandardError}}
)
async def inventory_get_topology():
    """Get network topology"""
    # Implementation would go here
    pass


# ============================================================================
# MONITORING API (/monitoring/v1)
# ============================================================================

monitoring_tags = ["monitoring", "metrics", "alerts", "snmp", "telemetry"]

@app.get(
    "/monitoring/v1/devices/{device_id}/metrics/optical",
    tags=monitoring_tags,
    summary="Get optical metrics",
    description="Get optical power metrics for a device",
    responses={404: {"model": StandardError}}
)
async def monitoring_get_optical_metrics(device_id: str):
    """Get optical metrics"""
    # Implementation would go here
    pass


@app.get(
    "/monitoring/v1/devices/{device_id}/metrics/interfaces",
    tags=monitoring_tags,
    summary="Get interface metrics",
    description="Get interface utilization metrics for a device",
    responses={404: {"model": StandardError}}
)
async def monitoring_get_interface_metrics(device_id: str):
    """Get interface metrics"""
    # Implementation would go here
    pass


@app.get(
    "/monitoring/v1/alerts",
    tags=monitoring_tags,
    summary="List alerts",
    description="List active alerts with filtering",
    response_model=PaginatedResponse,
    responses={401: {"model": StandardError}}
)
async def monitoring_list_alerts(
    cursor: Optional[str] = None,
    limit: int = 50,
    severity: Optional[str] = None,
    status: Optional[str] = None
):
    """List alerts"""
    # Implementation would go here
    pass


@app.post(
    "/monitoring/v1/alerts/{alert_id}/acknowledge",
    tags=monitoring_tags,
    summary="Acknowledge alert",
    description="Acknowledge an active alert",
    responses={404: {"model": StandardError}}
)
async def monitoring_acknowledge_alert(alert_id: str):
    """Acknowledge alert"""
    # Implementation would go here
    pass


@app.get(
    "/monitoring/v1/telemetry/status",
    tags=monitoring_tags,
    summary="Get telemetry status",
    description="Get status of telemetry collection services",
    responses={401: {"model": StandardError}}
)
async def monitoring_get_telemetry_status():
    """Get telemetry status"""
    # Implementation would go here
    pass


# ============================================================================
# AUTOMATION API (/automation/v1)
# ============================================================================

automation_tags = ["automation", "workflows", "jobs", "scheduling"]

@app.get(
    "/automation/v1/workflows",
    tags=automation_tags,
    summary="List workflows",
    description="List all available workflows",
    response_model=PaginatedResponse,
    responses={401: {"model": StandardError}}
)
async def automation_list_workflows(
    cursor: Optional[str] = None,
    limit: int = 50
):
    """List workflows"""
    # Implementation would go here
    pass


@app.post(
    "/automation/v1/workflows/{workflow_id}/execute",
    tags=automation_tags,
    summary="Execute workflow",
    description="Execute a workflow on specified targets",
    responses={404: {"model": StandardError}}
)
async def automation_execute_workflow(workflow_id: str):
    """Execute workflow"""
    # Implementation would go here
    pass


@app.get(
    "/automation/v1/jobs",
    tags=automation_tags,
    summary="List jobs",
    description="List job executions with status",
    response_model=PaginatedResponse,
    responses={401: {"model": StandardError}}
)
async def automation_list_jobs(
    cursor: Optional[str] = None,
    limit: int = 50,
    status: Optional[str] = None
):
    """List jobs"""
    # Implementation would go here
    pass


@app.get(
    "/automation/v1/jobs/{job_id}",
    tags=automation_tags,
    summary="Get job details",
    description="Get detailed information about a specific job",
    responses={404: {"model": StandardError}}
)
async def automation_get_job(job_id: str):
    """Get job details"""
    # Implementation would go here
    pass


@app.post(
    "/automation/v1/jobs/{job_id}/cancel",
    tags=automation_tags,
    summary="Cancel job",
    description="Cancel a running job",
    responses={404: {"model": StandardError}}
)
async def automation_cancel_job(job_id: str):
    """Cancel job"""
    # Implementation would go here
    pass


# ============================================================================
# INTEGRATIONS API (/integrations/v1)
# ============================================================================

integrations_tags = ["integrations", "netbox", "prtg", "mcp"]

@app.get(
    "/integrations/v1/netbox/status",
    tags=integrations_tags,
    summary="Get NetBox status",
    description="Get connection status and sync information for NetBox",
    responses={401: {"model": StandardError}}
)
async def integrations_get_netbox_status():
    """Get NetBox status"""
    # Implementation would go here
    pass


@app.post(
    "/integrations/v1/netbox/sync",
    tags=integrations_tags,
    summary="Sync with NetBox",
    description="Trigger synchronization with NetBox",
    responses={401: {"model": StandardError}}
)
async def integrations_sync_netbox():
    """Sync with NetBox"""
    # Implementation would go here
    pass


@app.get(
    "/integrations/v1/prtg/status",
    tags=integrations_tags,
    summary="Get PRTG status",
    description="Get connection status for PRTG monitoring",
    responses={401: {"model": StandardError}}
)
async def integrations_get_prtg_status():
    """Get PRTG status"""
    # Implementation would go here
    pass


@app.get(
    "/integrations/v1/mcp/services",
    tags=integrations_tags,
    summary="Get MCP services",
    description="List available MCP services and their status",
    responses={401: {"model": StandardError}}
)
async def integrations_get_mcp_services():
    """Get MCP services"""
    # Implementation would go here
    pass


# ============================================================================
# SYSTEM API (/system/v1)
# ============================================================================

system_tags = ["system", "health", "settings", "logs", "admin"]

@app.get(
    "/system/v1/health",
    tags=system_tags,
    summary="Health check",
    description="Get system health status and service availability",
    response_model=HealthResponse
)
async def system_health():
    """System health check"""
    # Implementation would go here
    pass


@app.get(
    "/system/v1/settings",
    tags=system_tags,
    summary="Get system settings",
    description="Get system configuration settings",
    responses={401: {"model": StandardError}}
)
async def system_get_settings():
    """Get system settings"""
    # Implementation would go here
    pass


@app.put(
    "/system/v1/settings",
    tags=system_tags,
    summary="Update system settings",
    description="Update system configuration settings",
    responses={401: {"model": StandardError}}
)
async def system_update_settings():
    """Update system settings"""
    # Implementation would go here
    pass


@app.get(
    "/system/v1/logs",
    tags=system_tags,
    summary="Get system logs",
    description="Get system logs with filtering and pagination",
    response_model=PaginatedResponse,
    responses={401: {"model": StandardError}}
)
async def system_get_logs(
    cursor: Optional[str] = None,
    limit: int = 50,
    level: Optional[str] = None,
    source: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    """Get system logs"""
    # Implementation would go here
    pass


# ============================================================================
# ADMIN API (/admin/v1)
# ============================================================================

admin_tags = ["admin", "privileged", "operations"]

@app.get(
    "/admin/v1/metrics",
    tags=admin_tags,
    summary="Get system metrics",
    description="Get internal system metrics and performance data",
    responses={401: {"model": StandardError}}
)
async def admin_get_metrics():
    """Get system metrics"""
    # Implementation would go here
    pass


@app.post(
    "/admin/v1/maintenance/enable",
    tags=admin_tags,
    summary="Enable maintenance mode",
    description="Put the system into maintenance mode",
    responses={401: {"model": StandardError}}
)
async def admin_enable_maintenance():
    """Enable maintenance mode"""
    # Implementation would go here
    pass


@app.delete(
    "/admin/v1/cache",
    tags=admin_tags,
    summary="Clear cache",
    description="Clear system caches",
    responses={401: {"model": StandardError}}
)
async def admin_clear_cache():
    """Clear cache"""
    # Implementation would go here
    pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
