"""
System API Router - FastAPI.

Routes for system information and status.
"""

import os
import platform
from datetime import datetime
from fastapi import APIRouter
import logging

from backend.database import get_db
from backend.utils.responses import success_response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status")
async def get_system_status():
    """Get system status."""
    db = get_db()
    
    status = {
        "api": "healthy",
        "database": "unknown",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT 1")
            status["database"] = "healthy"
    except Exception as e:
        status["database"] = f"error: {str(e)}"
    
    return success_response(status)


@router.get("/info")
async def get_system_info():
    """Get system information."""
    return success_response({
        "version": "2.0.0",
        "framework": "FastAPI",
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "hostname": platform.node(),
    })


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "opsconductor-api"}


@router.get("/database/status")
async def get_database_status():
    """Get database connection status."""
    db = get_db()
    
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()['version']
            
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM netbox_device_cache) as device_count,
                    (SELECT COUNT(*) FROM polling_configs) as polling_configs,
                    (SELECT COUNT(*) FROM system_logs WHERE created_at > NOW() - INTERVAL '24 hours') as logs_24h
            """)
            stats = dict(cursor.fetchone())
        
        return success_response({
            "connected": True,
            "version": version,
            "stats": stats
        })
    except Exception as e:
        return success_response({
            "connected": False,
            "error": str(e)
        })


@router.get("/environment")
async def get_environment():
    """Get environment variables (non-sensitive)."""
    safe_vars = [
        'PG_HOST', 'PG_PORT', 'PG_DATABASE',
        'LOG_LEVEL', 'FLASK_ENV', 'NODE_ENV'
    ]
    
    env = {}
    for var in safe_vars:
        value = os.environ.get(var)
        if value:
            env[var] = value
    
    return success_response(env)


@router.get("/services")
async def get_services_status():
    """Get status of related services."""
    services = {
        "api": {"status": "running", "port": 5000},
        "celery": {"status": "unknown"},
        "redis": {"status": "unknown"},
    }
    
    # Check Redis
    try:
        import redis
        r = redis.Redis(host=os.environ.get('REDIS_HOST', 'localhost'), port=6379)
        r.ping()
        services["redis"]["status"] = "running"
    except Exception:
        services["redis"]["status"] = "not available"
    
    return success_response(services)
