"""
OpsConductor API - OpenAPI 3.x Specification
Network monitoring and automation platform organized by business capability
"""

from fastapi import FastAPI, Request, Query, HTTPException, Body, Security, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db
from backend.services.logging_service import logging_service, get_logger, LogSource
from backend.openapi.identity_impl import (
    authenticate_user, get_current_user_from_token, list_users_paginated,
    list_roles_with_counts, get_role_members, get_password_policy,
    update_password_policy, test_identity_endpoints,
    create_access_token, JWT_SECRET_KEY, JWT_ALGORITHM
)
from backend.openapi.inventory_impl import (
    list_devices_paginated, get_device_by_id, list_device_interfaces,
    get_network_topology, list_sites, list_modules, list_racks,
    test_inventory_endpoints
)
from backend.openapi.monitoring_impl import (
    list_alerts_paginated, acknowledge_alert, get_device_optical_metrics,
    get_device_interface_metrics, get_device_availability_metrics,
    get_telemetry_status, get_alert_stats, test_monitoring_endpoints
)
from backend.openapi.automation_impl import (
    list_workflows_paginated, get_workflow_by_id, list_job_executions_paginated,
    trigger_workflow_execution, get_execution_status, cancel_execution,
    list_schedules, get_job_statistics, test_automation_endpoints
)
from backend.openapi.integrations_impl import (
    list_integrations_paginated, get_integration_by_id, test_netbox_connection,
    test_prtg_connection, get_mcp_services_status, get_mcp_devices,
    get_integration_status, sync_integration, test_integrations_endpoints
)
from backend.openapi.system_impl import (
    get_system_health, get_system_info, get_system_logs, get_system_settings,
    update_system_setting, get_api_usage_stats, clear_system_cache,
    test_system_endpoints
)

# Configuration
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# Security
security = HTTPBearer()

# Logger
logger = get_logger(__name__, LogSource.SYSTEM)


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
    access_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    user: Optional['User'] = None

class User(BaseModel):
    """User model"""
    id: str
    username: str
    email: EmailStr
    display_name: str
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    status: str = "active"
    two_factor_enabled: bool = False
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    roles: List[str] = []

class Role(BaseModel):
    """Role model"""
    id: str
    name: str
    display_name: str
    description: str
    role_type: str
    is_default: bool = False
    priority: int = 100
    user_count: int = 0
    permission_count: int = 0
    created_at: datetime
    updated_at: datetime

class PasswordPolicy(BaseModel):
    """Password policy model"""
    min_length: int = 8
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_numbers: bool = True
    require_special: bool = True
    max_age_days: int = 90
    prevent_reuse: int = 5
    lockout_attempts: int = 5
    lockout_duration_minutes: int = 30

class PaginatedUsers(BaseModel):
    """Paginated users response"""
    items: List[User]
    total: int
    limit: int
    cursor: Optional[str] = None

# Inventory Models
class Device(BaseModel):
    """Device model"""
    id: str
    name: str
    ip_address: str
    hostname: Optional[str] = ""
    device_type: str
    vendor: Optional[str] = ""
    model: Optional[str] = ""
    os_version: Optional[str] = ""
    site_id: Optional[str] = ""
    status: str = "active"
    created_at: datetime
    updated_at: datetime
    last_seen: Optional[datetime] = None
    site_name: Optional[str] = ""

class Interface(BaseModel):
    """Network interface model"""
    id: str
    name: str
    description: Optional[str] = ""
    if_index: Optional[int] = None
    if_type: Optional[str] = ""
    admin_status: str = "up"
    oper_status: str = "down"
    speed: Optional[int] = None
    mtu: Optional[int] = None
    mac_address: Optional[str] = ""
    created_at: datetime
    updated_at: datetime

class TopologyNode(BaseModel):
    """Topology node model"""
    id: str
    name: str
    ip: str
    type: str
    vendor: Optional[str] = ""
    site: Optional[str] = ""
    status: str = "active"

class TopologyLink(BaseModel):
    """Topology link model"""
    source: str
    target: str
    type: str
    bandwidth: Optional[str] = ""
    status: str = "active"

class NetworkTopology(BaseModel):
    """Network topology model"""
    nodes: List[TopologyNode]
    links: List[TopologyLink]
    metadata: Dict[str, Any]

class Site(BaseModel):
    """Site model"""
    id: str
    name: str
    description: Optional[str] = ""
    address: Optional[str] = ""
    city: Optional[str] = ""
    state: Optional[str] = ""
    country: Optional[str] = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    device_count: int = 0

class Module(BaseModel):
    """Device module model"""
    id: str
    device_id: str
    name: str
    description: Optional[str] = ""
    type: Optional[str] = ""
    part_number: Optional[str] = ""
    serial_number: Optional[str] = ""
    status: str = "active"
    created_at: datetime
    updated_at: datetime
    device_name: Optional[str] = ""

class Rack(BaseModel):
    """Rack model"""
    id: str
    site_id: str
    name: str
    description: Optional[str] = ""
    height: Optional[int] = None
    position: Optional[str] = ""
    status: str = "active"
    created_at: datetime
    updated_at: datetime
    site_name: Optional[str] = ""

class PaginatedDevices(BaseModel):
    """Paginated devices response"""
    items: List[Device]
    total: int
    limit: int
    cursor: Optional[str] = None

# Monitoring Models
class Alert(BaseModel):
    """Alert model"""
    id: str
    title: str
    message: str
    severity: str  # info, warning, critical
    status: str    # active, acknowledged, resolved
    device_id: Optional[str] = ""
    source: Optional[str] = ""
    created_at: datetime
    updated_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = ""
    device_name: Optional[str] = ""
    device_ip: Optional[str] = ""

class OpticalMetric(BaseModel):
    """Optical power metric model"""
    interface_name: str
    rx_power: Optional[float] = None
    tx_power: Optional[float] = None
    rx_power_low_alarm: Optional[float] = None
    rx_power_high_alarm: Optional[float] = None
    tx_power_low_alarm: Optional[float] = None
    tx_power_high_alarm: Optional[float] = None
    timestamp: datetime
    unit: str = "dBm"

class InterfaceMetric(BaseModel):
    """Interface utilization metric model"""
    interface_name: str
    interface_index: Optional[int] = None
    admin_status: str = "up"
    oper_status: str = "down"
    speed: Optional[int] = None
    mtu: Optional[int] = None
    rx_bytes: Optional[int] = None
    tx_bytes: Optional[int] = None
    rx_packets: Optional[int] = None
    tx_packets: Optional[int] = None
    rx_errors: Optional[int] = None
    tx_errors: Optional[int] = None
    rx_drops: Optional[int] = None
    tx_drops: Optional[int] = None
    timestamp: datetime
    utilization_in: Optional[float] = None
    utilization_out: Optional[float] = None

class AvailabilityMetric(BaseModel):
    """Availability metric model"""
    date: str
    total_checks: int
    up_checks: int
    availability_percentage: float
    first_check: datetime
    last_check: datetime

class TelemetryStatus(BaseModel):
    """Telemetry service status model"""
    database: str
    polling: str
    metrics_collection: str
    alerting: str
    last_update: str
    services: Dict[str, Any]

class AlertStats(BaseModel):
    """Alert statistics model"""
    total: int
    by_severity: Dict[str, int]
    by_status: Dict[str, int]
    recent_24h: int
    acknowledged: int
    unacknowledged: int

class PaginatedAlerts(BaseModel):
    """Paginated alerts response"""
    items: List[Alert]
    total: int
    limit: int
    cursor: Optional[str] = None

# Automation Models
class Workflow(BaseModel):
    """Workflow model"""
    id: str
    name: str
    description: str
    category: str
    status: str  # active, inactive, draft
    version: str
    definition: Optional[Dict[str, Any]] = {}
    parameters: Optional[Dict[str, Any]] = {}
    created_at: datetime
    updated_at: datetime
    created_by: str
    schedule_enabled: bool = False
    schedule_cron: Optional[str] = None
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    execution_count: int = 0

class JobExecution(BaseModel):
    """Job execution model"""
    id: str
    workflow_id: str
    status: str  # running, completed, failed, cancelled
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    trigger_type: str  # manual, scheduled, webhook
    triggered_by: str
    result: Optional[Dict[str, Any]] = {}
    error_message: Optional[str] = None
    progress: int = 0
    workflow_name: Optional[str] = ""
    workflow_category: Optional[str] = ""

class Schedule(BaseModel):
    """Schedule model"""
    id: str
    name: str
    schedule_cron: str
    schedule_enabled: bool = True
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime
    scheduled_runs: int = 0

class JobStatistics(BaseModel):
    """Job statistics model"""
    total_executions: int
    by_status: Dict[str, int]
    by_trigger_type: Dict[str, int]
    recent_24h: int
    recent_7d: int
    average_duration: float

class PaginatedWorkflows(BaseModel):
    """Paginated workflows response"""
    items: List[Workflow]
    total: int
    limit: int
    cursor: Optional[str] = None

class PaginatedExecutions(BaseModel):
    """Paginated executions response"""
    items: List[JobExecution]
    total: int
    limit: int
    cursor: Optional[str] = None

# Integrations Models
class Integration(BaseModel):
    """Integration model"""
    id: str
    name: str
    integration_type: str  # netbox, prtg, mcp, webhook, etc.
    status: str  # active, inactive, error
    description: str
    config: Optional[Dict[str, Any]] = {}
    created_at: datetime
    updated_at: datetime
    last_sync_at: Optional[datetime] = None
    sync_enabled: bool = False
    error_message: Optional[str] = None

class MCPService(BaseModel):
    """MCP service model"""
    id: str
    name: str
    service_type: str
    status: str
    endpoint: str
    config: Optional[Dict[str, Any]] = {}
    created_at: datetime
    updated_at: datetime
    last_check_at: Optional[datetime] = None

class MCPDevice(BaseModel):
    """MCP device model"""
    id: str
    name: str
    device_type: str
    status: str
    endpoint: str
    config: Optional[Dict[str, Any]] = {}
    created_at: datetime
    updated_at: datetime
    last_seen_at: Optional[datetime] = None

class IntegrationStatus(BaseModel):
    """Integration status model"""
    integration_type: str
    status: str
    message: Optional[str] = None
    total_integrations: Optional[int] = 0
    active_integrations: Optional[int] = 0
    sync_enabled: Optional[int] = 0
    last_sync: Optional[str] = None

class ConnectionTest(BaseModel):
    """Connection test result model"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    netbox_version: Optional[str] = None
    prtg_version: Optional[str] = None
    sensors_count: Optional[int] = None
    devices_count: Optional[int] = None

class PaginatedIntegrations(BaseModel):
    """Paginated integrations response"""
    items: List[Integration]
    total: int
    limit: int
    cursor: Optional[str] = None

# System Models
class HealthCheck(BaseModel):
    """Health check model"""
    status: str
    message: str
    response_time_ms: Optional[int] = None
    error: Optional[str] = None

class SystemHealth(BaseModel):
    """System health model"""
    status: str
    timestamp: str
    checks: Dict[str, Any]

class SystemInfo(BaseModel):
    """System information model"""
    hostname: str
    platform: str
    system: str
    release: str
    version: str
    architecture: str
    processor: str
    python_version: str
    uptime_seconds: Optional[int] = None
    timestamp: str
    process: Dict[str, Any]

class SystemLog(BaseModel):
    """System log model"""
    id: str
    level: str
    message: str
    source: str
    context: Optional[Dict[str, Any]] = {}
    timestamp: datetime
    created_at: datetime

class SystemSetting(BaseModel):
    """System setting model"""
    value: Any
    type: str
    description: str

class SystemSettings(BaseModel):
    """System settings model"""
    general: Dict[str, SystemSetting] = {}
    security: Dict[str, SystemSetting] = {}
    monitoring: Dict[str, SystemSetting] = {}
    integrations: Dict[str, SystemSetting] = {}

class APIUsageStats(BaseModel):
    """API usage statistics model"""
    total_requests: int
    requests_by_day: Dict[str, int]
    requests_by_endpoint: Dict[str, int]
    requests_by_status: Dict[str, int]
    average_response_time: float
    error_rate: float

class CacheClearResult(BaseModel):
    """Cache clear result model"""
    success: bool
    message: str
    cleared_caches: List[str]
    timestamp: str


class LoginRequest(BaseModel):
    """Login request"""
    username: str
    password: str




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
    "/auth/login",
    response_model=LoginResponse,
    responses={
        401: {"model": StandardError, "description": "Invalid credentials"},
        429: {"model": StandardError, "description": "Too many login attempts"}
    },
    summary="Authenticate user",
    description="Authenticate with username/password and receive JWT token"
)
async def login(
    request: LoginRequest,
    request_id: str = None  # Set by middleware
):
    """
    Authenticate a user and return a JWT token.
    
    - **username**: User's login name
    - **password**: User's password
    
    Returns JWT token valid for 24 hours and user information.
    """
    try:
        # Authenticate user using migrated function
        user_data = await authenticate_user(request.username, request.password)
        
        # Create JWT token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_data["id"], "username": user_data["username"]},
            expires_delta=access_token_expires
        )
        
        return LoginResponse(
            success=True,
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert minutes to seconds
            user=User(**user_data, updated_at=datetime.now())
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (invalid credentials, etc.)
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "LOGIN_ERROR",
                "message": "Authentication service unavailable",
                "trace_id": request_id
            }
        )


@app.get(
    "/api/auth/enterprise-configs",
    tags=["legacy", "auth"],
    summary="Get enterprise authentication configurations",
    description="Get available enterprise authentication providers",
    include_in_schema=False  # Legacy endpoint for frontend compatibility
)
async def get_enterprise_configs():
    """Get enterprise authentication configurations for frontend"""
    try:
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, auth_type, is_default, enabled, priority
                FROM enterprise_auth_configs 
                WHERE enabled = true
                ORDER BY priority ASC, name ASC
            """)
            
            configs = []
            for row in cursor.fetchall():
                config = dict(row)
                config['id'] = str(config['id'])
                configs.append(config)
            
            return {
                "success": True,
                "data": {
                    "configs": configs,
                    "default_method": "local"
                }
            }
    except Exception as e:
        logger.error(f"Get enterprise configs error: {str(e)}")
        return {
            "success": False,
            "error": "Failed to load enterprise configurations"
        }


@app.post(
    "/api/auth/login/enterprise",
    tags=["legacy", "auth"],
    summary="Enterprise authentication login",
    description="Authenticate using enterprise provider",
    include_in_schema=False  # Legacy endpoint for frontend compatibility
)
async def enterprise_login(request: dict = Body(...)):
    """Enterprise authentication endpoint for frontend compatibility"""
    try:
        username = request.get('username')
        password = request.get('password')
        config_id = request.get('config_id')
        
        # For now, delegate to regular authentication
        # In the future, this could integrate with actual enterprise providers
        user_data = await authenticate_user(username, password)
        
        # Create JWT token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_data["id"], "username": user_data["username"]},
            expires_delta=access_token_expires
        )
        
        return {
            "success": True,
            "data": {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user": User(**user_data, updated_at=datetime.now())
            }
        }
        
    except HTTPException:
        return {
            "success": False,
            "error": "Invalid credentials"
        }
    except Exception as e:
        logger.error(f"Enterprise login error: {str(e)}")
        return {
            "success": False,
            "error": "Authentication service unavailable"
        }


@app.get(
    "/identity/v1/auth/me",
    tags=identity_tags,
    summary="Get current user",
    description="Get information about the authenticated user",
    response_model=User,
    responses={401: {"model": StandardError}}
)
async def identity_get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Get current user info"""
    try:
        user_data = await get_current_user_from_token(credentials.credentials)
        return User(**user_data, updated_at=datetime.now())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "USER_FETCH_ERROR",
                "message": "Failed to fetch user information",
                "trace_id": request_id
            }
        )


@app.get(
    "/identity/v1/users",
    tags=identity_tags,
    summary="List users",
    description="List all users with cursor-based pagination",
    response_model=PaginatedUsers,
    responses={401: {"model": StandardError}}
)
async def identity_list_users(
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    search: Optional[str] = Query(None, description="Search by username or email"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """List users with pagination and filtering"""
    try:
        users_data = await list_users_paginated(cursor, limit, search, status_filter)
        
        # Convert to User objects
        users = [User(**user_data, updated_at=datetime.now()) 
                for user_data in users_data['items']]
        
        return PaginatedUsers(
            items=users,
            total=users_data['total'],
            limit=users_data['limit'],
            cursor=users_data['cursor']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List users error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "USERS_QUERY_ERROR",
                "message": "Failed to query users",
                "trace_id": request_id
            }
        )


@app.get(
    "/identity/v1/roles",
    tags=identity_tags,
    summary="List roles",
    description="List all available roles",
    response_model=List[Role],
    responses={401: {"model": StandardError}}
)
async def identity_list_roles(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """List roles"""
    try:
        roles_data = await list_roles_with_counts()
        
        # Convert to Role objects
        roles = [Role(**role_data, created_at=role_data.get('created_at', datetime.now()),
                   updated_at=role_data.get('updated_at', datetime.now())) 
                for role_data in roles_data]
        
        return roles
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List roles error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "ROLES_QUERY_ERROR",
                "message": "Failed to query roles",
                "trace_id": request_id
            }
        )


@app.get(
    "/identity/v1/test",
    tags=["identity", "test"],
    summary="Test Identity API",
    description="Test all Identity API endpoints",
    include_in_schema=False  # Hide from docs
)
async def test_identity_api():
    """Test all Identity API endpoints"""
    try:
        results = await test_identity_endpoints()
        return {
            "success": True,
            "results": results,
            "summary": f"{sum(results.values())}/{len(results)} tests passed"
        }
    except Exception as e:
        logger.error(f"Identity API test failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# INVENTORY API (/inventory/v1)
# ============================================================================

inventory_tags = ["inventory", "devices", "interfaces", "topology"]

@app.get(
    "/inventory/v1/devices",
    tags=inventory_tags,
    summary="List devices",
    description="List all network devices with filtering and pagination",
    response_model=PaginatedDevices,
    responses={401: {"model": StandardError}}
)
async def inventory_list_devices(
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    site_id: Optional[str] = Query(None, description="Filter by site ID"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name, IP, or hostname"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """List devices with pagination and filtering"""
    try:
        devices_data = await list_devices_paginated(cursor, limit, site_id, device_type, status, search)
        
        # Convert to Device objects
        devices = [Device(**device_data, created_at=device_data.get('created_at', datetime.now()),
                   updated_at=device_data.get('updated_at', datetime.now()),
                   last_seen=device_data.get('last_seen')) 
                for device_data in devices_data['items']]
        
        return PaginatedDevices(
            items=devices,
            total=devices_data['total'],
            limit=devices_data['limit'],
            cursor=devices_data['cursor']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List devices error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "DEVICES_QUERY_ERROR",
                "message": "Failed to query devices",
                "trace_id": request_id
            }
        )


@app.get(
    "/inventory/v1/devices/{device_id}",
    tags=inventory_tags,
    summary="Get device details",
    description="Get detailed information about a specific device",
    responses={404: {"model": StandardError}}
)
async def inventory_get_device(
    device_id: str,
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Get device details"""
    try:
        device_data = await get_device_by_id(device_id)
        return Device(**device_data, created_at=device_data.get('created_at', datetime.now()),
                   updated_at=device_data.get('updated_at', datetime.now()),
                   last_seen=device_data.get('last_seen'))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get device error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "DEVICE_FETCH_ERROR",
                "message": "Failed to fetch device information",
                "trace_id": request_id
            }
        )


@app.get(
    "/inventory/v1/devices/{device_id}/interfaces",
    tags=inventory_tags,
    summary="List device interfaces",
    description="List all interfaces for a specific device",
    response_model=List[Interface],
    responses={404: {"model": StandardError}}
)
async def inventory_list_device_interfaces(
    device_id: str,
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """List device interfaces"""
    try:
        interfaces_data = await list_device_interfaces(device_id)
        
        # Convert to Interface objects
        interfaces = [Interface(**interface_data, created_at=interface_data.get('created_at', datetime.now()),
                     updated_at=interface_data.get('updated_at', datetime.now())) 
                    for interface_data in interfaces_data]
        
        return interfaces
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List interfaces error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INTERFACES_QUERY_ERROR",
                "message": "Failed to query interfaces",
                "trace_id": request_id
            }
        )


@app.get(
    "/inventory/v1/topology",
    tags=inventory_tags,
    summary="Get network topology",
    description="Get the complete network topology graph",
    responses={401: {"model": StandardError}}
)
async def inventory_get_topology(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Get network topology"""
    try:
        topology_data = await get_network_topology()
        
        # Convert to proper objects
        nodes = [TopologyNode(**node) for node in topology_data['nodes']]
        links = [TopologyLink(**link) for link in topology_data['links']]
        
        return NetworkTopology(
            nodes=nodes,
            links=links,
            metadata=topology_data['metadata']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get topology error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "TOPOLOGY_QUERY_ERROR",
                "message": "Failed to query network topology",
                "trace_id": request_id
            }
        )


@app.get(
    "/inventory/v1/sites",
    tags=inventory_tags,
    summary="List sites",
    description="List all sites with device counts",
    response_model=List[Site],
    responses={401: {"model": StandardError}}
)
async def inventory_list_sites(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """List sites"""
    try:
        sites_data = await list_sites()
        
        # Convert to Site objects
        sites = [Site(**site_data, created_at=site_data.get('created_at', datetime.now()),
                 updated_at=site_data.get('updated_at', datetime.now())) 
                for site_data in sites_data]
        
        return sites
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List sites error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "SITES_QUERY_ERROR",
                "message": "Failed to query sites",
                "trace_id": request_id
            }
        )


@app.get(
    "/inventory/v1/modules",
    tags=inventory_tags,
    summary="List modules",
    description="List device modules, optionally filtered by device",
    response_model=List[Module],
    responses={401: {"model": StandardError}}
)
async def inventory_list_modules(
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """List modules"""
    try:
        modules_data = await list_modules(device_id)
        
        # Convert to Module objects
        modules = [Module(**module_data, created_at=module_data.get('created_at', datetime.now()),
                  updated_at=module_data.get('updated_at', datetime.now())) 
                 for module_data in modules_data]
        
        return modules
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List modules error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "MODULES_QUERY_ERROR",
                "message": "Failed to query modules",
                "trace_id": request_id
            }
        )


@app.get(
    "/inventory/v1/racks",
    tags=inventory_tags,
    summary="List racks",
    description="List racks, optionally filtered by site",
    response_model=List[Rack],
    responses={401: {"model": StandardError}}
)
async def inventory_list_racks(
    site_id: Optional[str] = Query(None, description="Filter by site ID"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """List racks"""
    try:
        racks_data = await list_racks(site_id)
        
        # Convert to Rack objects
        racks = [Rack(**rack_data, created_at=rack_data.get('created_at', datetime.now()),
                updated_at=rack_data.get('updated_at', datetime.now())) 
                for rack_data in racks_data]
        
        return racks
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List racks error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "RACKS_QUERY_ERROR",
                "message": "Failed to query racks",
                "trace_id": request_id
            }
        )


@app.get(
    "/inventory/v1/test",
    tags=["inventory", "test"],
    summary="Test Inventory API",
    description="Test all Inventory API endpoints",
    include_in_schema=False  # Hide from docs
)
async def test_inventory_api():
    """Test all Inventory API endpoints"""
    try:
        results = await test_inventory_endpoints()
        return {
            "success": True,
            "results": results,
            "summary": f"{sum(results.values())}/{len(results)} tests passed"
        }
    except Exception as e:
        logger.error(f"Inventory API test failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# MONITORING API (/monitoring/v1)
# ============================================================================

monitoring_tags = ["monitoring", "metrics", "alerts", "snmp", "telemetry"]

@app.get(
    "/monitoring/v1/devices/{device_id}/metrics/optical",
    tags=monitoring_tags,
    summary="Get optical metrics",
    description="Get optical power metrics for a device",
    response_model=List[OpticalMetric],
    responses={404: {"model": StandardError}}
)
async def monitoring_get_optical_metrics(
    device_id: str,
    hours: int = Query(24, ge=1, le=168, description="Hours of data to retrieve"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Get optical power metrics for a device"""
    try:
        metrics_data = await get_device_optical_metrics(device_id, hours)
        
        # Convert to OpticalMetric objects
        metrics = [OpticalMetric(**metric_data) for metric_data in metrics_data]
        
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get optical metrics error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "OPTICAL_METRICS_ERROR",
                "message": "Failed to retrieve optical metrics",
                "trace_id": request_id
            }
        )


@app.get(
    "/monitoring/v1/devices/{device_id}/metrics/interfaces",
    tags=monitoring_tags,
    summary="Get interface metrics",
    description="Get interface utilization metrics for a device",
    response_model=List[InterfaceMetric],
    responses={404: {"model": StandardError}}
)
async def monitoring_get_interface_metrics(
    device_id: str,
    hours: int = Query(24, ge=1, le=168, description="Hours of data to retrieve"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Get interface utilization metrics for a device"""
    try:
        metrics_data = await get_device_interface_metrics(device_id, hours)
        
        # Convert to InterfaceMetric objects
        metrics = [InterfaceMetric(**metric_data) for metric_data in metrics_data]
        
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get interface metrics error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INTERFACE_METRICS_ERROR",
                "message": "Failed to retrieve interface metrics",
                "trace_id": request_id
            }
        )


@app.get(
    "/monitoring/v1/alerts",
    tags=monitoring_tags,
    summary="List alerts",
    description="List active alerts with filtering",
    response_model=PaginatedAlerts,
    responses={401: {"model": StandardError}}
)
async def monitoring_list_alerts(
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    status: Optional[str] = Query(None, description="Filter by status"),
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """List alerts with pagination and filtering"""
    try:
        alerts_data = await list_alerts_paginated(cursor, limit, severity, status, device_id)
        
        # Convert to Alert objects
        alerts = [Alert(**alert_data) for alert_data in alerts_data['items']]
        
        return PaginatedAlerts(
            items=alerts,
            total=alerts_data['total'],
            limit=alerts_data['limit'],
            cursor=alerts_data['cursor']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List alerts error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "ALERTS_QUERY_ERROR",
                "message": "Failed to query alerts",
                "trace_id": request_id
            }
        )


@app.post(
    "/monitoring/v1/alerts/{alert_id}/acknowledge",
    tags=monitoring_tags,
    summary="Acknowledge alert",
    description="Acknowledge an active alert",
    responses={404: {"model": StandardError}}
)
async def monitoring_acknowledge_alert(
    alert_id: str,
    acknowledged_by: str = Body(..., description="User acknowledging the alert"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Acknowledge an active alert"""
    try:
        result = await acknowledge_alert(alert_id, acknowledged_by)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Acknowledge alert error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "ALERT_ACKNOWLEDGE_ERROR",
                "message": "Failed to acknowledge alert",
                "trace_id": request_id
            }
        )


@app.get(
    "/monitoring/v1/alerts/stats",
    tags=monitoring_tags,
    summary="Get alert statistics",
    description="Get alert statistics and summary",
    response_model=AlertStats,
    responses={401: {"model": StandardError}}
)
async def monitoring_get_alert_stats(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Get alert statistics"""
    try:
        stats_data = await get_alert_stats()
        return AlertStats(**stats_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get alert stats error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "ALERT_STATS_ERROR",
                "message": "Failed to get alert statistics",
                "trace_id": request_id
            }
        )


@app.get(
    "/monitoring/v1/telemetry/status",
    tags=monitoring_tags,
    summary="Get telemetry status",
    description="Get telemetry and monitoring service status",
    response_model=TelemetryStatus,
    responses={401: {"model": StandardError}}
)
async def monitoring_get_telemetry_status(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Get telemetry service status"""
    try:
        telemetry_data = await get_telemetry_status()
        return TelemetryStatus(**telemetry_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get telemetry status error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "TELEMETRY_STATUS_ERROR",
                "message": "Failed to get telemetry status",
                "trace_id": request_id
            }
        )


@app.get(
    "/monitoring/v1/devices/{device_id}/metrics/availability",
    tags=monitoring_tags,
    summary="Get availability metrics",
    description="Get availability metrics for a device",
    response_model=List[AvailabilityMetric],
    responses={404: {"model": StandardError}}
)
async def monitoring_get_availability_metrics(
    device_id: str,
    days: int = Query(30, ge=1, le=365, description="Days of data to retrieve"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Get availability metrics for a device"""
    try:
        metrics_data = await get_device_availability_metrics(device_id, days)
        
        # Convert to AvailabilityMetric objects
        metrics = [AvailabilityMetric(**metric_data) for metric_data in metrics_data]
        
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get availability metrics error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "AVAILABILITY_METRICS_ERROR",
                "message": "Failed to retrieve availability metrics",
                "trace_id": request_id
            }
        )


@app.get(
    "/monitoring/v1/test",
    tags=["monitoring", "test"],
    summary="Test Monitoring API",
    description="Test all Monitoring API endpoints",
    include_in_schema=False  # Hide from docs
)
async def test_monitoring_api():
    """Test all Monitoring API endpoints"""
    try:
        results = await test_monitoring_endpoints()
        return {
            "success": True,
            "results": results,
            "summary": f"{sum(results.values())}/{len(results)} tests passed"
        }
    except Exception as e:
        logger.error(f"Monitoring API test failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }




# ============================================================================
# AUTOMATION API (/automation/v1)
# ============================================================================

automation_tags = ["automation", "workflows", "jobs", "scheduling"]

@app.get(
    "/automation/v1/workflows",
    tags=automation_tags,
    summary="List workflows",
    description="List all available workflows",
    response_model=PaginatedWorkflows,
    responses={401: {"model": StandardError}}
)
async def automation_list_workflows(
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """List workflows with pagination and filtering"""
    try:
        workflows_data = await list_workflows_paginated(cursor, limit, status, category, search)
        
        workflows = [Workflow(**workflow_data, created_at=workflow_data.get('created_at', datetime.now()),
                    updated_at=workflow_data.get('updated_at', datetime.now()),
                    last_run_at=workflow_data.get('last_run_at'),
                    next_run_at=workflow_data.get('next_run_at')) 
                   for workflow_data in workflows_data['items']]
        
        return PaginatedWorkflows(
            items=workflows,
            total=workflows_data['total'],
            limit=workflows_data['limit'],
            cursor=workflows_data['cursor']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List workflows error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "WORKFLOWS_QUERY_ERROR",
                "message": "Failed to query workflows",
                "trace_id": request_id
            }
        )


@app.post(
    "/automation/v1/workflows/{workflow_id}/execute",
    tags=automation_tags,
    summary="Execute workflow",
    description="Execute a workflow on specified targets",
    responses={404: {"model": StandardError}}
)
async def automation_execute_workflow(
    workflow_id: str,
    parameters: Optional[Dict[str, Any]] = Body(None, description="Workflow parameters"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Execute a workflow"""
    try:
        # Get user from token for triggered_by
        user_data = await get_current_user_from_token(credentials.credentials)
        triggered_by = user_data.get('username', 'unknown')
        
        result = await trigger_workflow_execution(workflow_id, triggered_by, parameters)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Execute workflow error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "WORKFLOW_EXECUTE_ERROR",
                "message": "Failed to execute workflow",
                "trace_id": request_id
            }
        )


@app.get(
    "/automation/v1/executions",
    tags=automation_tags,
    summary="List executions",
    description="List workflow executions",
    response_model=PaginatedExecutions,
    responses={401: {"model": StandardError}}
)
async def automation_list_executions(
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """List workflow executions"""
    try:
        executions_data = await list_job_executions_paginated(cursor, limit, workflow_id, status)
        
        executions = [JobExecution(**execution_data, started_at=execution_data.get('started_at', datetime.now()),
                     completed_at=execution_data.get('completed_at')) 
                    for execution_data in executions_data['items']]
        
        return PaginatedExecutions(
            items=executions,
            total=executions_data['total'],
            limit=executions_data['limit'],
            cursor=executions_data['cursor']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List executions error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "EXECUTIONS_QUERY_ERROR",
                "message": "Failed to query executions",
                "trace_id": request_id
            }
        )


@app.get(
    "/automation/v1/jobs",
    tags=automation_tags,
    summary="List jobs",
    description="List job executions with status",
    response_model=PaginatedResponse,
    responses={401: {"model": StandardError}}
)
async def automation_list_jobs(
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """List job executions (alias for executions)"""
    # Redirect to executions endpoint
    return await automation_list_executions(cursor, limit, None, None, credentials, request_id)


@app.get(
    "/automation/v1/schedules",
    tags=automation_tags,
    summary="List schedules",
    description="List workflow schedules",
    response_model=List[Schedule],
    responses={401: {"model": StandardError}}
)
async def automation_list_schedules(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """List workflow schedules"""
    try:
        schedules_data = await list_schedules()
        
        schedules = [Schedule(**schedule_data, created_at=schedule_data.get('created_at', datetime.now()),
                  last_run_at=schedule_data.get('last_run_at'),
                  next_run_at=schedule_data.get('next_run_at')) 
                 for schedule_data in schedules_data]
        
        return schedules
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List schedules error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "SCHEDULES_QUERY_ERROR",
                "message": "Failed to query schedules",
                "trace_id": request_id
            }
        )


@app.get(
    "/automation/v1/statistics",
    tags=automation_tags,
    summary="Get job statistics",
    description="Get job execution statistics",
    response_model=JobStatistics,
    responses={401: {"model": StandardError}}
)
async def automation_get_statistics(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Get job execution statistics"""
    try:
        stats_data = await get_job_statistics()
        return JobStatistics(**stats_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get statistics error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "STATISTICS_ERROR",
                "message": "Failed to get statistics",
                "trace_id": request_id
            }
        )


@app.get(
    "/automation/v1/test",
    tags=["automation", "test"],
    summary="Test Automation API",
    description="Test all Automation API endpoints",
    include_in_schema=False  # Hide from docs
)
async def test_automation_api():
    """Test all Automation API endpoints"""
    try:
        results = await test_automation_endpoints()
        return {
            "success": True,
            "results": results,
            "summary": f"{sum(results.values())}/{len(results)} tests passed"
        }
    except Exception as e:
        logger.error(f"Automation API test failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


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
async def integrations_get_netbox_status(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Get NetBox connection status"""
    try:
        status_data = await get_integration_status('netbox')
        return IntegrationStatus(**status_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get NetBox status error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "NETBOX_STATUS_ERROR",
                "message": "Failed to get NetBox status",
                "trace_id": request_id
            }
        )


@app.post(
    "/integrations/v1/netbox/sync",
    tags=integrations_tags,
    summary="Sync with NetBox",
    description="Trigger synchronization with NetBox",
    responses={401: {"model": StandardError}}
)
async def integrations_sync_netbox(
    integration_id: str = Body(..., description="NetBox integration ID"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Sync with NetBox"""
    try:
        # Get user from token for triggered_by
        user_data = await get_current_user_from_token(credentials.credentials)
        triggered_by = user_data.get('username', 'unknown')
        
        result = await sync_integration(integration_id, triggered_by)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync NetBox error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "NETBOX_SYNC_ERROR",
                "message": "Failed to sync with NetBox",
                "trace_id": request_id
            }
        )


@app.get(
    "/integrations/v1/prtg/status",
    tags=integrations_tags,
    summary="Get PRTG status",
    description="Get connection status for PRTG monitoring",
    responses={401: {"model": StandardError}}
)
async def integrations_get_prtg_status(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Get PRTG connection status"""
    try:
        status_data = await get_integration_status('prtg')
        return IntegrationStatus(**status_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get PRTG status error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "PRTG_STATUS_ERROR",
                "message": "Failed to get PRTG status",
                "trace_id": request_id
            }
        )


@app.get(
    "/integrations/v1/mcp/services",
    tags=integrations_tags,
    summary="Get MCP services",
    description="Get MCP (Model Context Protocol) services",
    response_model=Dict[str, Any],  # Custom response with services array and metadata
    responses={401: {"model": StandardError}}
)
async def integrations_get_mcp_services(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Get MCP services"""
    try:
        services_data = await get_mcp_services_status()
        
        # Convert to proper objects
        services = [MCPService(**service_data, created_at=service_data.get('created_at', datetime.now()),
                  updated_at=service_data.get('updated_at', datetime.now()),
                  last_check_at=service_data.get('last_check_at')) 
                 for service_data in services_data['services']]
        
        return {
            "services": services,
            "total_count": services_data['total_count'],
            "active_count": services_data['active_count'],
            "last_updated": services_data['last_updated']
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get MCP services error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "MCP_SERVICES_ERROR",
                "message": "Failed to get MCP services",
                "trace_id": request_id
            }
        )


@app.get(
    "/integrations/v1/mcp/services/sample",
    tags=integrations_tags,
    summary="Get MCP service sample",
    description="Get sample MCP service for schema documentation",
    response_model=MCPService,
    responses={401: {"model": StandardError}}
)
async def integrations_get_mcp_service_sample(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Get sample MCP service"""
    return MCPService(
        id="sample-service",
        name="Sample MCP Service",
        service_type="test",
        status="active",
        endpoint="http://localhost:8080",
        config={"test": True},
        created_at=datetime.now(),
        updated_at=datetime.now(),
        last_check_at=datetime.now()
    )


@app.get(
    "/integrations/v1/mcp/devices",
    tags=integrations_tags,
    summary="Get MCP devices",
    description="Get MCP devices",
    response_model=List[MCPDevice],
    responses={401: {"model": StandardError}}
)
async def integrations_get_mcp_devices(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Get MCP devices"""
    try:
        devices_data = await get_mcp_devices()
        
        devices = [MCPDevice(**device_data, created_at=device_data.get('created_at', datetime.now()),
                  updated_at=device_data.get('updated_at', datetime.now()),
                  last_seen_at=device_data.get('last_seen_at')) 
                 for device_data in devices_data]
        
        return devices
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get MCP devices error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "MCP_DEVICES_ERROR",
                "message": "Failed to get MCP devices",
                "trace_id": request_id
            }
        )


@app.post(
    "/integrations/v1/netbox/test",
    tags=integrations_tags,
    summary="Test NetBox connection",
    description="Test connection to NetBox API",
    response_model=ConnectionTest,
    responses={401: {"model": StandardError}}
)
async def integrations_test_netbox(
    config: Dict[str, Any] = Body(..., description="NetBox configuration"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Test NetBox connection"""
    try:
        result = await test_netbox_connection(config)
        return ConnectionTest(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test NetBox error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "NETBOX_TEST_ERROR",
                "message": "Failed to test NetBox connection",
                "trace_id": request_id
            }
        )


@app.post(
    "/integrations/v1/prtg/test",
    tags=integrations_tags,
    summary="Test PRTG connection",
    description="Test connection to PRTG API",
    response_model=ConnectionTest,
    responses={401: {"model": StandardError}}
)
async def integrations_test_prtg(
    config: Dict[str, Any] = Body(..., description="PRTG configuration"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Test PRTG connection"""
    try:
        result = await test_prtg_connection(config)
        return ConnectionTest(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test PRTG error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "PRTG_TEST_ERROR",
                "message": "Failed to test PRTG connection",
                "trace_id": request_id
            }
        )


@app.get(
    "/integrations/v1/list",
    tags=integrations_tags,
    summary="List integrations",
    description="List all configured integrations",
    response_model=PaginatedIntegrations,
    responses={401: {"model": StandardError}}
)
async def integrations_list(
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """List integrations with pagination"""
    try:
        integrations_data = await list_integrations_paginated(cursor, limit)
        
        integrations = [Integration(**integration_data) for integration_data in integrations_data['items']]
        
        return {
            "items": integrations,
            "total": integrations_data['total'],
            "limit": integrations_data['limit'],
            "cursor": integrations_data.get('cursor')
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List integrations error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INTEGRATIONS_LIST_ERROR",
                "message": "Failed to list integrations",
                "trace_id": request_id
            }
        )


@app.get(
    "/integrations/v1/test",
    tags=["integrations", "test"],
    summary="Test Integrations API",
    description="Test all Integrations API endpoints",
    include_in_schema=False  # Hide from docs
)
async def test_integrations_api():
    """Test all Integrations API endpoints"""
    try:
        results = await test_integrations_endpoints()
        return {
            "success": True,
            "results": results,
            "summary": f"{sum(results.values())}/{len(results)} tests passed"
        }
    except Exception as e:
        logger.error(f"Integrations API test failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# SYSTEM API (/system/v1)
# ============================================================================

system_tags = ["system", "health", "settings", "logs", "admin"]

@app.get(
    "/system/v1/health",
    tags=system_tags,
    summary="Health check",
    description="Get system health status and service availability",
    response_model=SystemHealth
)
async def system_health():
    """System health check"""
    try:
        health_data = await get_system_health()
        return SystemHealth(**health_data)
    except Exception as e:
        logger.error(f"System health check error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "HEALTH_CHECK_ERROR",
                "message": "Failed to get system health",
                "error": str(e)
            }
        )


@app.get(
    "/system/v1/settings",
    tags=system_tags,
    summary="Get system settings",
    description="Get system configuration settings",
    response_model=SystemSettings,
    responses={401: {"model": StandardError}}
)
async def system_get_settings(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Get system settings"""
    try:
        settings_data = await get_system_settings()
        return SystemSettings(**settings_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get system settings error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "SETTINGS_GET_ERROR",
                "message": "Failed to get system settings",
                "trace_id": request_id
            }
        )


@app.put(
    "/system/v1/settings",
    tags=system_tags,
    summary="Update system settings",
    description="Update system configuration settings",
    responses={401: {"model": StandardError}}
)
async def system_update_settings(
    category: str = Body(..., description="Setting category"),
    key: str = Body(..., description="Setting key"),
    value: Any = Body(..., description="Setting value"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Update system settings"""
    try:
        # Get user from token for updated_by
        user_data = await get_current_user_from_token(credentials.credentials)
        updated_by = user_data.get('username', 'unknown')
        
        result = await update_system_setting(category, key, value, updated_by)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update system settings error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "SETTINGS_UPDATE_ERROR",
                "message": "Failed to update system settings",
                "trace_id": request_id
            }
        )


@app.get(
    "/system/v1/logs",
    tags=system_tags,
    summary="Get system logs",
    description="Get system logs with filtering and pagination",
    response_model=List[SystemLog],
    responses={401: {"model": StandardError}}
)
async def system_get_logs(
    level: Optional[str] = Query(None, description="Filter by log level"),
    limit: int = Query(100, ge=1, le=1000, description="Number of logs to return"),
    hours: int = Query(24, ge=1, le=168, description="Hours of logs to retrieve"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Get system logs"""
    try:
        logs_data = await get_system_logs(level, limit, hours)
        
        logs = [SystemLog(**log_data, timestamp=log_data.get('timestamp', datetime.now()),
                created_at=log_data.get('created_at', datetime.now())) 
               for log_data in logs_data]
        
        return logs
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get system logs error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "LOGS_GET_ERROR",
                "message": "Failed to get system logs",
                "trace_id": request_id
            }
        )


@app.get(
    "/system/v1/info",
    tags=system_tags,
    summary="Get system information",
    description="Get detailed system information and metrics",
    response_model=SystemInfo,
    responses={401: {"model": StandardError}}
)
async def system_get_info(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Get system information"""
    try:
        info_data = await get_system_info()
        return SystemInfo(**info_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get system info error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "SYSTEM_INFO_ERROR",
                "message": "Failed to get system information",
                "trace_id": request_id
            }
        )


@app.get(
    "/system/v1/usage/stats",
    tags=system_tags,
    summary="Get API usage statistics",
    description="Get API usage statistics and analytics",
    response_model=APIUsageStats,
    responses={401: {"model": StandardError}}
)
async def system_get_usage_stats(
    days: int = Query(30, ge=1, le=365, description="Days of statistics to retrieve"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Get API usage statistics"""
    try:
        stats_data = await get_api_usage_stats(days)
        return APIUsageStats(**stats_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get usage stats error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "USAGE_STATS_ERROR",
                "message": "Failed to get usage statistics",
                "trace_id": request_id
            }
        )


@app.delete(
    "/system/v1/cache",
    tags=system_tags,
    summary="Clear system cache",
    description="Clear system cache and temporary data",
    response_model=CacheClearResult,
    responses={401: {"model": StandardError}}
)
async def system_clear_cache(
    cache_type: str = Query("all", description="Type of cache to clear"),
    credentials: HTTPAuthorizationCredentials = Security(security),
    request_id: str = None
):
    """Clear system cache"""
    try:
        result = await clear_system_cache(cache_type)
        return CacheClearResult(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Clear cache error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "CACHE_CLEAR_ERROR",
                "message": "Failed to clear cache",
                "trace_id": request_id
            }
        )


@app.get(
    "/system/v1/test",
    tags=["system", "test"],
    summary="Test System API",
    description="Test all System API endpoints",
    include_in_schema=False  # Hide from docs
)
async def test_system_api():
    """Test all System API endpoints"""
    try:
        results = await test_system_endpoints()
        return {
            "success": True,
            "results": results,
            "summary": f"{sum(results.values())}/{len(results)} tests passed"
        }
    except Exception as e:
        logger.error(f"System API test failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


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
