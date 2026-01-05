"""
Jobs API Router - FastAPI.

Routes for job execution and management.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from backend.database import get_db
from backend.utils.responses import success_response, error_response, list_response

logger = logging.getLogger(__name__)

router = APIRouter()


class JobRunRequest(BaseModel):
    workflow_id: Optional[int] = None
    target_ips: Optional[List[str]] = None
    target_group_id: Optional[int] = None
    parameters: Optional[Dict[str, Any]] = None


@router.get("")
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List job executions."""
    db = get_db()
    
    query = """
        SELECT id, workflow_id, workflow_name, status, trigger_type, triggered_by,
               started_at, finished_at, duration_ms, error_message,
               nodes_total, nodes_completed, nodes_failed, nodes_skipped
        FROM workflow_executions
        WHERE 1=1
    """
    params = []
    
    if status:
        query += " AND status = %s"
        params.append(status)
    
    query += " ORDER BY started_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    with db.cursor() as cursor:
        cursor.execute(query, params)
        jobs = [dict(row) for row in cursor.fetchall()]
    
    return list_response(jobs)


@router.post("/run")
async def run_job(req: JobRunRequest):
    """Run a job/workflow."""
    try:
        from backend.services.job_service import JobService
        
        job_service = JobService()
        result = job_service.run_job(
            workflow_id=req.workflow_id,
            target_ips=req.target_ips,
            target_group_id=req.target_group_id,
            parameters=req.parameters
        )
        
        return success_response(result)
    except Exception as e:
        logger.error(f"Job run error: {e}")
        return error_response('JOB_ERROR', str(e))


@router.get("/{job_id}")
async def get_job(job_id: str):
    """Get job execution details."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT id, workflow_id, workflow_name, status, trigger_type, triggered_by,
                   started_at, finished_at, duration_ms, error_message,
                   nodes_total, nodes_completed, nodes_failed, nodes_skipped,
                   node_results, variables
            FROM workflow_executions WHERE id = %s
        """, (job_id,))
        job = cursor.fetchone()
        if not job:
            return error_response('NOT_FOUND', 'Job not found')
        
        job = dict(job)
        
        # Get node execution results
        cursor.execute("""
            SELECT id, node_id, node_type, node_label, status, started_at, finished_at,
                   duration_ms, input_data, output_data, error_message
            FROM workflow_node_executions WHERE execution_id = %s
            ORDER BY started_at
        """, (job_id,))
        job['node_executions'] = [dict(row) for row in cursor.fetchall()]
    
    return success_response(job)


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running job."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            UPDATE workflow_executions
            SET status = 'cancelled', finished_at = NOW()
            WHERE id = %s AND status IN ('pending', 'running')
            RETURNING id
        """, (job_id,))
        cancelled = cursor.fetchone()
        if not cancelled:
            return error_response('NOT_FOUND', 'Job not found or not running')
        db.commit()
    
    return success_response({"cancelled": True, "job_id": job_id})


@router.get("/{job_id}/logs")
async def get_job_logs(job_id: str):
    """Get logs for a job execution."""
    db = get_db()
    with db.cursor() as cursor:
        # Get node executions as logs
        cursor.execute("""
            SELECT id, node_id, node_type, node_label, status, 
                   started_at as created_at, error_message as message
            FROM workflow_node_executions WHERE execution_id = %s
            ORDER BY started_at
        """, (job_id,))
        logs = [dict(row) for row in cursor.fetchall()]
    
    return list_response(logs)


@router.get("/status/summary")
async def get_jobs_summary():
    """Get job execution summary."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'running') as running,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled,
                COUNT(*) FILTER (WHERE started_at > NOW() - INTERVAL '24 hours') as last_24h
            FROM job_executions
        """)
        summary = dict(cursor.fetchone())
    
    return success_response(summary)
