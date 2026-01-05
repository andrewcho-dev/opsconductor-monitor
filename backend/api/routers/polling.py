"""Polling router - FastAPI."""

from fastapi import APIRouter
from backend.database import get_db

router = APIRouter()


@router.get("/polling/status")
async def get_polling_status():
    """Get polling system status."""
    db = get_db()
    
    with db.cursor() as cursor:
        # Get polling configs summary
        cursor.execute("""
            SELECT 
                COUNT(*) as total_configs,
                COUNT(*) FILTER (WHERE enabled = true) as enabled_configs,
                COUNT(*) FILTER (WHERE last_run_status = 'success') as successful_last_run,
                COUNT(*) FILTER (WHERE last_run_status = 'failed') as failed_last_run
            FROM polling_configs
        """)
        configs = dict(cursor.fetchone())
        
        # Get recent executions
        cursor.execute("""
            SELECT 
                COUNT(*) as total_executions,
                COUNT(*) FILTER (WHERE status = 'success') as successful,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                AVG(duration_ms) as avg_duration_ms,
                SUM(records_stored) as total_records
            FROM polling_executions
            WHERE started_at > NOW() - INTERVAL '24 hours'
        """)
        executions = dict(cursor.fetchone())
        
        # Get upcoming polls
        cursor.execute("""
            SELECT name, poll_type, interval_seconds, last_run_at
            FROM polling_configs
            WHERE enabled = true
            ORDER BY last_run_at ASC NULLS FIRST
            LIMIT 10
        """)
        upcoming = [dict(row) for row in cursor.fetchall()]
    
    return {
        "success": True,
        "data": {
            "configs": configs,
            "executions_24h": executions,
            "upcoming_polls": upcoming
        }
    }
