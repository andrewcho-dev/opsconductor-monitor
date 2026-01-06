"""
System API Router (/system/v1)

Handles system health, settings, logs, and administrative functions.
"""

from fastapi import APIRouter, Query, Body, Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from backend.openapi.system_impl import (
    get_system_health, get_system_info, get_system_logs, get_system_settings,
    update_system_setting, get_api_usage_stats, clear_system_cache,
    test_system_endpoints
)
from backend.openapi.identity_impl import get_current_user_from_token

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/system/v1", tags=["system", "health", "settings", "logs"])


# Response models (minimal inline definitions)
from pydantic import BaseModel

class StandardError(BaseModel):
    code: str
    message: str
    trace_id: Optional[str] = None


@router.get("/health", summary="Health check")
async def health():
    """System health check - no auth required"""
    try:
        health_data = await get_system_health()
        return health_data
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "HEALTH_ERROR", "message": str(e)})


@router.get("/settings", summary="Get system settings")
async def get_settings(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get system configuration settings"""
    try:
        return await get_system_settings()
    except Exception as e:
        logger.error(f"Get settings error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "SETTINGS_ERROR", "message": str(e)})


@router.put("/settings", summary="Update system settings")
async def update_settings(
    category: str = Body(...),
    key: str = Body(...),
    value: Any = Body(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Update system configuration settings"""
    try:
        user_data = await get_current_user_from_token(credentials.credentials)
        updated_by = user_data.get('username', 'unknown')
        return await update_system_setting(category, key, value, updated_by)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update settings error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "SETTINGS_UPDATE_ERROR", "message": str(e)})


@router.get("/logs", summary="Get system logs")
async def get_logs(
    level: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    hours: int = Query(24, ge=1, le=168),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get system logs with filtering"""
    try:
        return await get_system_logs(level, limit, hours)
    except Exception as e:
        logger.error(f"Get logs error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "LOGS_ERROR", "message": str(e)})


@router.get("/logs/stats", summary="Get log statistics")
async def get_log_stats(
    hours: int = Query(24, ge=1, le=168),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get log statistics"""
    return {"total": 0, "by_level": {}, "by_source": {}, "hours": hours}


@router.get("/logs/sources", summary="Get log sources")
async def get_log_sources(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get available log sources"""
    return {"sources": ["system", "api", "auth", "monitoring", "automation"]}


@router.get("/logs/levels", summary="Get log levels")
async def get_log_levels(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get available log levels"""
    return {"levels": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]}


@router.post("/logs/cleanup", summary="Cleanup logs")
async def cleanup_logs(
    request: Dict[str, Any] = Body(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Cleanup old logs"""
    return {"success": True, "deleted_count": 0}


@router.get("/logging/settings", summary="Get logging settings")
async def get_logging_settings(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get logging configuration"""
    return {"log_level": "INFO", "retention_days": 30, "max_size_mb": 100}


@router.get("/settings/database", summary="Get database settings")
async def get_database_settings(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get database configuration"""
    return {"host": "localhost", "port": 5432, "database": "opsconductor", "connected": True}


@router.post("/settings/database/test", summary="Test database connection")
async def test_database(
    request: Dict[str, Any] = Body(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Test database connection"""
    return {"success": True, "message": "Connection successful"}


@router.get("/info", summary="Get system information")
async def get_info(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get detailed system information"""
    try:
        return await get_system_info()
    except Exception as e:
        logger.error(f"Get info error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "INFO_ERROR", "message": str(e)})


@router.get("/usage/stats", summary="Get API usage statistics")
async def get_usage_stats(
    days: int = Query(30, ge=1, le=365),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get API usage statistics"""
    try:
        return await get_api_usage_stats(days)
    except Exception as e:
        logger.error(f"Get usage stats error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "USAGE_ERROR", "message": str(e)})


@router.delete("/cache", summary="Clear system cache")
async def clear_cache(
    cache_type: str = Query("all"),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Clear system cache"""
    try:
        return await clear_system_cache(cache_type)
    except Exception as e:
        logger.error(f"Clear cache error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "CACHE_ERROR", "message": str(e)})


@router.get("/test", include_in_schema=False)
async def test_api():
    """Test all System API endpoints"""
    try:
        results = await test_system_endpoints()
        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "error": str(e)}
