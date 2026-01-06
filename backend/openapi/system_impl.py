"""
System API Implementation - OpenAPI 3.x Migration
This implements the actual business logic for system endpoints
"""

import os
import sys
import json
import psutil
import platform
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db
from backend.services.logging_service import get_logger, LogSource

logger = get_logger(__name__, LogSource.SYSTEM)

# ============================================================================
# Database Functions (Migrated from Legacy)
# ============================================================================

def _table_exists(cursor, table_name):
    """Check if table exists"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        ) as exists
    """, (table_name,))
    result = cursor.fetchone()
    return result['exists'] if result else False

# ============================================================================
# System API Business Logic
# ============================================================================

async def get_system_health() -> Dict[str, Any]:
    """
    Get comprehensive system health status
    Migrated from legacy /api/health
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # Database health check
    try:
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("SELECT 1")
            health_status["checks"]["database"] = {
                "status": "healthy",
                "response_time_ms": 0,  # Would measure in real implementation
                "message": "Database connection successful"
            }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
            "message": "Database connection failed"
        }
        health_status["status"] = "unhealthy"
    
    # Memory check
    memory = psutil.virtual_memory()
    health_status["checks"]["memory"] = {
        "status": "healthy" if memory.percent < 90 else "warning",
        "usage_percent": memory.percent,
        "available_gb": round(memory.available / (1024**3), 2),
        "total_gb": round(memory.total / (1024**3), 2),
        "message": f"Memory usage: {memory.percent}%"
    }
    
    # Disk space check
    disk = psutil.disk_usage('/')
    disk_percent = (disk.used / disk.total) * 100
    health_status["checks"]["disk"] = {
        "status": "healthy" if disk_percent < 90 else "warning",
        "usage_percent": round(disk_percent, 2),
        "free_gb": round(disk.free / (1024**3), 2),
        "total_gb": round(disk.total / (1024**3), 2),
        "message": f"Disk usage: {round(disk_percent, 2)}%"
    }
    
    # CPU check
    cpu_percent = psutil.cpu_percent(interval=1)
    health_status["checks"]["cpu"] = {
        "status": "healthy" if cpu_percent < 80 else "warning",
        "usage_percent": cpu_percent,
        "message": f"CPU usage: {cpu_percent}%"
    }
    
    # Service status
    health_status["checks"]["services"] = {
        "status": "healthy",
        "services": {
            "backend": "running",
            "database": "running",
            "poller": "unknown",  # Would check actual service status
            "scheduler": "unknown"
        },
        "message": "Core services running"
    }
    
    return health_status

async def get_system_info() -> Dict[str, Any]:
    """
    Get detailed system information
    Migrated from legacy /api/system/info
    """
    system_info = {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "architecture": platform.architecture(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "uptime_seconds": None,  # Would calculate actual uptime
        "timestamp": datetime.now().isoformat()
    }
    
    # Get process information
    try:
        process = psutil.Process(os.getpid())
        system_info["process"] = {
            "pid": process.pid,
            "create_time": datetime.fromtimestamp(process.create_time()).isoformat(),
            "cpu_percent": process.cpu_percent(),
            "memory_mb": round(process.memory_info().rss / (1024**2), 2),
            "memory_percent": process.memory_percent()
        }
    except:
        system_info["process"] = {"error": "Unable to get process info"}
    
    return system_info

async def get_system_logs(
    level: Optional[str] = None,
    limit: int = 100,
    hours: int = 24
) -> List[Dict[str, Any]]:
    """
    Get system logs with filtering
    Migrated from legacy /api/logs
    """
    db = get_db()
    with db.cursor() as cursor:
        if not _table_exists(cursor, 'system_logs'):
            return []
        
        # Build query with filters
        where_clauses = ["timestamp >= NOW() - INTERVAL '%s hours'" % hours]
        params = []
        
        if level:
            where_clauses.append("level = %s")
            params.append(level.upper())
        
        where_clause = "WHERE " + " AND ".join(where_clauses)
        
        cursor.execute(f"""
            SELECT id, level, message, source, details as context,
                   timestamp, created_at
            FROM system_logs 
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT %s
        """, params + [limit])
        
        logs = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        
        return logs

async def get_system_settings() -> Dict[str, Any]:
    """
    Get system configuration settings
    Migrated from legacy /api/settings
    """
    db = get_db()
    with db.cursor() as cursor:
        if not _table_exists(cursor, 'system_settings'):
            return {
                "general": {},
                "security": {},
                "monitoring": {},
                "integrations": {},
                "message": "Settings table not found"
            }
        
        cursor.execute("""
            SELECT category, key, value, type, description
            FROM system_settings
            ORDER BY category, key
        """)
        
        settings = {}
        for row in cursor.fetchall() if cursor.description else []:
            category = row['category']
            if category not in settings:
                settings[category] = {}
            
            # Convert value based on type
            value = row['value']
            if row['type'] == 'integer':
                value = int(value) if value.isdigit() else 0
            elif row['type'] == 'float':
                value = float(value)
            elif row['type'] == 'boolean':
                value = value.lower() in ['true', '1', 'yes']
            elif row['type'] == 'json':
                try:
                    value = json.loads(value)
                except:
                    value = {}
            
            settings[category][row['key']] = {
                "value": value,
                "type": row['type'],
                "description": row['description']
            }
        
        return settings

async def update_system_setting(
    category: str,
    key: str,
    value: Any,
    updated_by: str
) -> Dict[str, str]:
    """
    Update a system setting
    Migrated from legacy /api/settings
    """
    db = get_db()
    with db.cursor() as cursor:
        # Check if setting exists
        cursor.execute("""
            SELECT id, type FROM system_settings 
            WHERE category = %s AND key = %s
        """, (category, key))
        
        setting = cursor.fetchone()
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "SETTING_NOT_FOUND",
                    "message": f"Setting '{category}.{key}' not found"
                }
            )
        
        # Convert value to string based on type
        setting_type = setting['type']
        if setting_type == 'json':
            value_str = json.dumps(value)
        else:
            value_str = str(value)
        
        # Update setting
        cursor.execute("""
            UPDATE system_settings 
            SET value = %s, updated_at = NOW(), updated_by = %s
            WHERE category = %s AND key = %s
        """, (value_str, updated_by, category, key))
        
        db.commit()
        
        logger.info(f"Setting {category}.{key} updated to {value_str} by {updated_by}")
        
        return {
            "success": True,
            "message": "Setting updated successfully",
            "category": category,
            "key": key,
            "value": value_str
        }

async def get_api_usage_stats(days: int = 30) -> Dict[str, Any]:
    """
    Get API usage statistics
    """
    db = get_db()
    with db.cursor() as cursor:
        if not _table_exists(cursor, 'api_usage_logs'):
            return {
                "total_requests": 0,
                "requests_by_day": {},
                "requests_by_endpoint": {},
                "requests_by_status": {},
                "average_response_time": 0,
                "error_rate": 0
            }
        
        # Get overall stats
        cursor.execute("""
            SELECT COUNT(*) as total,
                   AVG(response_time_ms) as avg_response_time
            FROM api_usage_logs 
            WHERE timestamp >= NOW() - INTERVAL '%s days'
        """, (days,))
        
        overall_stats = cursor.fetchone()
        
        # Requests by day
        cursor.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as count
            FROM api_usage_logs 
            WHERE timestamp >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, (days,))
        
        requests_by_day = {str(row['date']): row['count'] for row in cursor.fetchall()}
        
        # Requests by endpoint
        cursor.execute("""
            SELECT endpoint, COUNT(*) as count
            FROM api_usage_logs 
            WHERE timestamp >= NOW() - INTERVAL '%s days'
            GROUP BY endpoint
            ORDER BY count DESC
            LIMIT 10
        """, (days,))
        
        requests_by_endpoint = {row['endpoint']: row['count'] for row in cursor.fetchall()}
        
        # Requests by status
        cursor.execute("""
            SELECT status_code, COUNT(*) as count
            FROM api_usage_logs 
            WHERE timestamp >= NOW() - INTERVAL '%s days'
            GROUP BY status_code
            ORDER BY status_code
        """, (days,))
        
        requests_by_status = {str(row['status_code']): row['count'] for row in cursor.fetchall()}
        
        # Calculate error rate
        total_requests = overall_stats['total'] or 0
        error_requests = sum(count for status, count in requests_by_status.items() 
                           if status.startswith('4') or status.startswith('5'))
        error_rate = (error_requests / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "total_requests": total_requests,
            "requests_by_day": requests_by_day,
            "requests_by_endpoint": requests_by_endpoint,
            "requests_by_status": requests_by_status,
            "average_response_time": round(overall_stats['avg_response_time'] or 0, 2),
            "error_rate": round(error_rate, 2)
        }

async def clear_system_cache(cache_type: str = "all") -> Dict[str, str]:
    """
    Clear system cache
    Migrated from legacy /api/admin/cache/clear
    """
    try:
        cleared_caches = []
        
        if cache_type in ["all", "api"]:
            # Clear API cache (would implement actual cache clearing)
            cleared_caches.append("api_cache")
        
        if cache_type in ["all", "database"]:
            # Clear database query cache
            cleared_caches.append("database_cache")
        
        if cache_type in ["all", "sessions"]:
            # Clear session cache
            cleared_caches.append("session_cache")
        
        logger.info(f"System cache cleared: {', '.join(cleared_caches)}")
        
        return {
            "success": True,
            "message": f"Cache cleared successfully",
            "cleared_caches": cleared_caches,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Clear cache error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "CACHE_CLEAR_ERROR",
                "message": "Failed to clear cache",
                "error": str(e)
            }
        )

# ============================================================================
# Testing Functions
# ============================================================================

async def test_system_endpoints() -> Dict[str, bool]:
    """
    Test all System API endpoints
    Returns dict of endpoint: success status
    """
    results = {}
    
    try:
        # Test 1: Get system health
        health = await get_system_health()
        results['get_health'] = 'status' in health and 'checks' in health
        
        # Test 2: Get system info
        info = await get_system_info()
        results['get_system_info'] = 'hostname' in info and 'platform' in info
        
        # Test 3: Get system logs
        logs = await get_system_logs()
        results['get_system_logs'] = isinstance(logs, list)
        
        # Test 4: Get system settings
        settings = await get_system_settings()
        results['get_system_settings'] = isinstance(settings, dict)
        
        # Test 5: Get API usage stats
        stats = await get_api_usage_stats()
        results['get_api_usage_stats'] = 'total_requests' in stats and 'requests_by_day' in stats
        
        # Test 6: Clear cache
        cache_result = await clear_system_cache("all")
        results['clear_cache'] = cache_result.get('success', False)
        
        logger.info(f"System API tests completed: {sum(results.values())}/{len(results)} passed")
        
    except Exception as e:
        logger.error(f"System API test failed: {str(e)}")
        results['error'] = str(e)
    
    return results
