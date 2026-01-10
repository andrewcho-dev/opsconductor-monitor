"""
System Routes

Health checks, statistics, and system configuration.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend_v2.api.auth import get_current_user, require_role, Role, User, login, refresh_tokens, TokenPair
from backend_v2.core.db import get_setting, set_setting, query
from backend_v2.core.addon_registry import get_registry
from backend_v2.core.trap_receiver import get_receiver
from backend_v2.api.websocket import get_manager

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
    from backend_v2.core.alert_engine import get_engine
    
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
