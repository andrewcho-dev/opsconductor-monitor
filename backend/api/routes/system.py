"""
System Routes

Health checks, statistics, and system configuration.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.api.auth import get_current_user, require_role, Role, User, login, refresh_tokens, TokenPair
from backend.core.db import get_setting, set_setting, query
from backend.core.addon_registry import get_registry
from backend.core.trap_receiver import get_receiver
from backend.api.websocket import get_manager

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: str
    components: Dict[str, str]


class StatsResponse(BaseModel):
    """System statistics."""
    addons: Dict[str, Any]
    alerts: Dict[str, Any]
    trap_receiver: Dict[str, Any]
    websocket: Dict[str, Any]


class LoginRequest(BaseModel):
    """Login request."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class RefreshRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class SettingRequest(BaseModel):
    """Setting update request."""
    value: str


# Health and info

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns status of all system components.
    """
    components = {}
    
    # Database
    try:
        query("SELECT 1")
        components['database'] = 'healthy'
    except:
        components['database'] = 'unhealthy'
    
    # Trap receiver
    receiver = get_receiver()
    components['trap_receiver'] = 'running' if receiver.is_running else 'stopped'
    
    # Addon registry
    try:
        registry = get_registry()
        components['addon_registry'] = f'{len(registry.get_enabled())} addons'
    except:
        components['addon_registry'] = 'error'
    
    # WebSocket
    manager = get_manager()
    components['websocket'] = f'{manager.client_count} clients'
    
    overall = 'healthy' if components['database'] == 'healthy' else 'degraded'
    
    return HealthResponse(
        status=overall,
        version='2.0.0',
        timestamp=datetime.utcnow().isoformat(),
        components=components
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(user: User = Depends(get_current_user)):
    """Get system statistics."""
    from backend.core.alert_engine import get_engine
    
    # Addon stats
    registry = get_registry()
    addon_stats = {
        'total': len(registry.get_enabled()),
        'by_method': {}
    }
    for addon in registry.get_enabled():
        method = addon.method
        addon_stats['by_method'][method] = addon_stats['by_method'].get(method, 0) + 1
    
    # Alert stats
    engine = get_engine()
    alert_stats = await engine.get_stats()
    
    # Trap receiver stats
    receiver = get_receiver()
    trap_stats = receiver.stats
    trap_stats['running'] = receiver.is_running
    
    # WebSocket stats
    ws_stats = get_manager().get_stats()
    
    return StatsResponse(
        addons=addon_stats,
        alerts=alert_stats,
        trap_receiver=trap_stats,
        websocket=ws_stats
    )


# Authentication

@router.post("/auth/login", response_model=TokenResponse)
async def login_endpoint(request: LoginRequest):
    """
    Authenticate and get access tokens.
    """
    result = login(request.username, request.password)
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in=result.expires_in
    )


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_endpoint(request: RefreshRequest):
    """
    Refresh access token using refresh token.
    """
    result = refresh_tokens(request.refresh_token)
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
        expires_in=result.expires_in
    )


@router.get("/auth/me")
async def get_current_user_info(user: User = Depends(get_current_user)):
    """Get current user information."""
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role.value,
        'is_active': user.is_active,
    }


# Settings

@router.get("/settings/{key}")
async def get_setting_endpoint(
    key: str,
    user: User = Depends(require_role(Role.OPERATOR))
):
    """Get system setting."""
    value = get_setting(key)
    if value is None:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    return {'key': key, 'value': value}


@router.put("/settings/{key}")
async def set_setting_endpoint(
    key: str,
    request: SettingRequest,
    user: User = Depends(require_role(Role.ADMIN))
):
    """Set system setting (admin only)."""
    set_setting(key, request.value)
    return {'key': key, 'value': request.value, 'status': 'updated'}


@router.get("/settings")
async def list_settings(
    user: User = Depends(require_role(Role.ADMIN))
):
    """List all system settings (admin only)."""
    rows = query("SELECT key, value, updated_at FROM system_settings ORDER BY key")
    return {'settings': rows}


# =============================================================================
# Polling Configuration
# =============================================================================

class PollingConfig(BaseModel):
    """Polling system configuration."""
    worker_count: int = 1
    worker_concurrency: int = 4
    rate_limit: int = 100  # polls per second
    poll_interval: int = 60  # seconds between dispatch cycles
    default_target_interval: int = 300  # default per-target interval


class PollingConfigResponse(BaseModel):
    """Polling configuration response."""
    config: PollingConfig
    status: str
    requires_restart: bool


class ServiceStatusResponse(BaseModel):
    """Service status response."""
    celery_worker: str
    celery_beat: str
    backend: str
    frontend: str


@router.get("/polling/config", response_model=PollingConfigResponse)
async def get_polling_config(
    user: User = Depends(require_role(Role.OPERATOR))
):
    """
    Get current polling configuration.
    
    These settings control how the polling system operates:
    - worker_count: Number of Celery workers to run
    - worker_concurrency: Parallel tasks per worker
    - rate_limit: Max polls per second (prevents overwhelming network)
    - poll_interval: How often the dispatcher runs (seconds)
    - default_target_interval: Default polling interval for new targets
    """
    config = PollingConfig(
        worker_count=int(get_setting('polling_worker_count', '1')),
        worker_concurrency=int(get_setting('polling_worker_concurrency', '4')),
        rate_limit=int(get_setting('polling_rate_limit', '100')),
        poll_interval=int(get_setting('polling_interval', '60')),
        default_target_interval=int(get_setting('polling_default_target_interval', '300')),
    )
    
    return PollingConfigResponse(
        config=config,
        status='active',
        requires_restart=False
    )


@router.put("/polling/config", response_model=PollingConfigResponse)
async def update_polling_config(
    config: PollingConfig,
    user: User = Depends(require_role(Role.ADMIN))
):
    """
    Update polling configuration.
    
    Changes to worker_count and worker_concurrency require a service restart
    to take effect. Other settings may take effect on the next poll cycle.
    """
    # Validate ranges
    if config.worker_count < 1 or config.worker_count > 16:
        raise HTTPException(status_code=400, detail="worker_count must be between 1 and 16")
    if config.worker_concurrency < 1 or config.worker_concurrency > 16:
        raise HTTPException(status_code=400, detail="worker_concurrency must be between 1 and 16")
    if config.rate_limit < 10 or config.rate_limit > 1000:
        raise HTTPException(status_code=400, detail="rate_limit must be between 10 and 1000")
    if config.poll_interval < 10 or config.poll_interval > 3600:
        raise HTTPException(status_code=400, detail="poll_interval must be between 10 and 3600 seconds")
    if config.default_target_interval < 30 or config.default_target_interval > 86400:
        raise HTTPException(status_code=400, detail="default_target_interval must be between 30 and 86400 seconds")
    
    # Save settings
    set_setting('polling_worker_count', str(config.worker_count))
    set_setting('polling_worker_concurrency', str(config.worker_concurrency))
    set_setting('polling_rate_limit', str(config.rate_limit))
    set_setting('polling_interval', str(config.poll_interval))
    set_setting('polling_default_target_interval', str(config.default_target_interval))
    
    return PollingConfigResponse(
        config=config,
        status='pending_restart',
        requires_restart=True
    )


@router.get("/services/status", response_model=ServiceStatusResponse)
async def get_service_status(
    user: User = Depends(require_role(Role.OPERATOR))
):
    """Get status of all services."""
    import subprocess
    import os
    
    project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    logs_dir = os.path.join(project_dir, 'logs')
    
    def check_pid(pid_file):
        pid_path = os.path.join(logs_dir, pid_file)
        if os.path.exists(pid_path):
            try:
                with open(pid_path) as f:
                    pid = int(f.read().strip())
                # Check if process is running
                os.kill(pid, 0)
                return 'running'
            except (ProcessLookupError, ValueError):
                return 'stopped'
        return 'stopped'
    
    return ServiceStatusResponse(
        celery_worker=check_pid('celery-worker.pid'),
        celery_beat=check_pid('celery-beat.pid'),
        backend=check_pid('backend.pid'),
        frontend=check_pid('frontend.pid'),
    )


@router.post("/services/restart")
async def restart_services(
    user: User = Depends(require_role(Role.ADMIN))
):
    """
    Restart all services with current configuration.
    
    This will:
    1. Stop all services (Celery, Backend, Frontend)
    2. Apply new polling configuration
    3. Start all services
    
    The API will briefly become unavailable during restart.
    """
    import subprocess
    import os
    
    project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    restart_script = os.path.join(project_dir, 'restart.sh')
    
    if not os.path.exists(restart_script):
        raise HTTPException(status_code=500, detail="Restart script not found")
    
    # Run restart in background (non-blocking)
    subprocess.Popen(
        [restart_script],
        cwd=project_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    
    return {
        'status': 'restarting',
        'message': 'Services are restarting. Please wait a few seconds and refresh.'
    }
