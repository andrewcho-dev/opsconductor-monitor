"""
Logs API Router - FastAPI.

Routes for system logs and audit logs.
"""

from fastapi import APIRouter, Query
from typing import Optional
import logging

from backend.database import get_db
from backend.utils.responses import success_response, list_response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("")
async def get_logs(
    level: Optional[str] = None,
    source: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    hours: int = 24
):
    """Get system logs with filtering."""
    db = get_db()
    
    query = """
        SELECT id, level, source, category, message, details, created_at
        FROM system_logs
        WHERE created_at > NOW() - INTERVAL '%s hours'
    """
    params = [hours]
    
    if level:
        query += " AND level = %s"
        params.append(level)
    
    if source:
        query += " AND source = %s"
        params.append(source)
    
    if category:
        query += " AND category = %s"
        params.append(category)
    
    if search:
        query += " AND message ILIKE %s"
        params.append(f"%{search}%")
    
    query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    with db.cursor() as cursor:
        cursor.execute(query, params)
        logs = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        count_query = """
            SELECT COUNT(*) FROM system_logs
            WHERE created_at > NOW() - INTERVAL '%s hours'
        """
        count_params = [hours]
        if level:
            count_query += " AND level = %s"
            count_params.append(level)
        if source:
            count_query += " AND source = %s"
            count_params.append(source)
        if category:
            count_query += " AND category = %s"
            count_params.append(category)
        if search:
            count_query += " AND message ILIKE %s"
            count_params.append(f"%{search}%")
        
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()['count']
    
    return {
        "success": True,
        "data": {
            "logs": logs,
            "total": total
        },
        "meta": {
            "total": total,
            "limit": limit,
            "offset": offset
        }
    }


@router.get("/audit")
async def get_audit_logs(
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get user audit logs."""
    db = get_db()
    
    query = """
        SELECT id, user_id, username, action, resource_type, resource_id, 
               details, ip_address, user_agent, created_at
        FROM audit_logs
        WHERE 1=1
    """
    params = []
    
    if user_id:
        query += " AND user_id = %s"
        params.append(user_id)
    
    if action:
        query += " AND action = %s"
        params.append(action)
    
    if resource_type:
        query += " AND resource_type = %s"
        params.append(resource_type)
    
    query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    with db.cursor() as cursor:
        cursor.execute(query, params)
        logs = [dict(row) for row in cursor.fetchall()]
    
    return list_response(logs)


@router.get("/stats")
async def get_log_stats(hours: int = 24):
    """Get log statistics for the specified time period."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE level = 'DEBUG') as debug,
                COUNT(*) FILTER (WHERE level = 'INFO') as info,
                COUNT(*) FILTER (WHERE level = 'WARNING') as warning,
                COUNT(*) FILTER (WHERE level = 'ERROR') as error,
                COUNT(*) FILTER (WHERE level = 'CRITICAL') as critical
            FROM system_logs
            WHERE created_at > NOW() - INTERVAL '%s hours'
        """, (hours,))
        stats = dict(cursor.fetchone())
        
        # Get counts by source
        cursor.execute("""
            SELECT source, COUNT(*) as count
            FROM system_logs
            WHERE created_at > NOW() - INTERVAL '%s hours'
            GROUP BY source
            ORDER BY count DESC
            LIMIT 10
        """, (hours,))
        stats['by_source'] = [dict(row) for row in cursor.fetchall()]
        
        # Get counts by category
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM system_logs
            WHERE created_at > NOW() - INTERVAL '%s hours' AND category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
            LIMIT 10
        """, (hours,))
        stats['by_category'] = [dict(row) for row in cursor.fetchall()]
    
    return success_response(stats)


@router.get("/levels")
async def get_log_levels():
    """Get available log levels."""
    return success_response({
        "levels": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    })


@router.get("/sources")
async def get_log_sources():
    """Get available log sources."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT DISTINCT source FROM system_logs ORDER BY source")
        sources = [row['source'] for row in cursor.fetchall()]
    return success_response({"sources": sources})


@router.get("/categories")
async def get_log_categories():
    """Get available log categories."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT DISTINCT category FROM system_logs WHERE category IS NOT NULL ORDER BY category")
        categories = [row['category'] for row in cursor.fetchall()]
    return success_response({"categories": categories})


@router.delete("")
async def clear_old_logs(days: int = 30):
    """Clear logs older than specified days."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(
            "DELETE FROM system_logs WHERE created_at < NOW() - INTERVAL '%s days' RETURNING id",
            (days,)
        )
        deleted = cursor.rowcount
        db.commit()
    
    return success_response({"deleted": deleted, "message": f"Deleted {deleted} logs older than {days} days"})
