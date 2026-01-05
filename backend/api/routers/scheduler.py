"""
Scheduler API Router - FastAPI.

Routes for scheduled job management.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from backend.database import get_db
from backend.utils.responses import success_response, error_response, list_response

logger = logging.getLogger(__name__)

router = APIRouter()


class ScheduleCreate(BaseModel):
    name: str
    workflow_id: int
    cron_expression: str
    target_ips: Optional[List[str]] = None
    target_group_id: Optional[int] = None
    parameters: Optional[Dict[str, Any]] = None
    enabled: bool = True
    description: Optional[str] = None


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    target_ips: Optional[List[str]] = None
    target_group_id: Optional[int] = None
    parameters: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None


@router.get("/queues")
async def get_queue_status():
    """Get Celery queue status."""
    try:
        from celery_app import celery_app
        
        # Get active workers
        inspect = celery_app.control.inspect()
        active = inspect.active() or {}
        scheduled = inspect.scheduled() or {}
        reserved = inspect.reserved() or {}
        stats = inspect.stats() or {}
        
        workers = []
        active_total = 0
        scheduled_total = 0
        
        for worker_name, worker_stats in stats.items():
            worker_active = len(active.get(worker_name, []))
            worker_scheduled = len(scheduled.get(worker_name, []))
            worker_reserved = len(reserved.get(worker_name, []))
            
            active_total += worker_active
            scheduled_total += worker_scheduled + worker_reserved
            
            workers.append({
                'name': worker_name,
                'active': worker_active,
                'scheduled': worker_scheduled,
                'reserved': worker_reserved,
                'concurrency': worker_stats.get('pool', {}).get('max-concurrency', 0),
                'pid': worker_stats.get('pid'),
            })
        
        return success_response({
            'workers': workers,
            'worker_count': len(workers),
            'active_total': active_total,
            'scheduled_total': scheduled_total,
            'concurrency': sum(w.get('concurrency', 0) for w in workers),
            'celery_connected': True,
        })
    except Exception as e:
        logger.error(f"Queue status error: {e}")
        return success_response({
            'workers': [],
            'worker_count': 0,
            'active_total': 0,
            'scheduled_total': 0,
            'concurrency': 0,
            'celery_connected': False,
            'error': str(e),
        })


@router.get("/executions/recent")
async def get_recent_executions(limit: int = 15, status: Optional[str] = None):
    """Get recent job executions from scheduler_job_executions table."""
    db = get_db()
    with db.cursor() as cursor:
        query = """
            SELECT id, job_name, task_name, task_id, status, started_at, finished_at,
                   error_message, result, worker, config, triggered_by, progress
            FROM scheduler_job_executions
            WHERE 1=1
        """
        params = []
        if status:
            query += " AND status = %s"
            params.append(status)
        query += " ORDER BY started_at DESC LIMIT %s"
        params.append(limit)
        cursor.execute(query, params)
        executions = [dict(row) for row in cursor.fetchall()]
    return success_response(executions)


@router.get("/jobs")
async def list_scheduler_jobs(enabled: Optional[bool] = None, limit: int = 50):
    """List scheduled jobs with optional filtering."""
    db = get_db()
    with db.cursor() as cursor:
        query = """
            SELECT id, name, task_name, config, enabled, schedule_type,
                   interval_seconds, cron_expression, start_at, end_at,
                   max_runs, run_count, last_run_at, next_run_at, 
                   created_at, updated_at, job_definition_id
            FROM scheduler_jobs
            WHERE 1=1
        """
        params = []
        if enabled is not None:
            query += " AND enabled = %s"
            params.append(enabled)
        query += " ORDER BY name LIMIT %s"
        params.append(limit)
        cursor.execute(query, params)
        jobs = [dict(row) for row in cursor.fetchall()]
    return success_response({"jobs": jobs})


@router.get("")
async def list_schedules():
    """List all scheduled jobs."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT s.id, s.name, s.workflow_id, s.cron_expression, s.enabled,
                   s.target_ips, s.target_group_id, s.parameters, s.description,
                   s.last_run_at, s.next_run_at, s.created_at,
                   w.name as workflow_name
            FROM scheduled_jobs s
            LEFT JOIN workflows w ON s.workflow_id = w.id
            ORDER BY s.name
        """)
        schedules = [dict(row) for row in cursor.fetchall()]
    return list_response(schedules)


@router.post("")
async def create_schedule(req: ScheduleCreate):
    """Create a new scheduled job."""
    from croniter import croniter
    from datetime import datetime
    
    # Validate cron expression
    try:
        cron = croniter(req.cron_expression, datetime.now())
        next_run = cron.get_next(datetime)
    except Exception as e:
        return error_response('VALIDATION_ERROR', f'Invalid cron expression: {e}')
    
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            INSERT INTO scheduled_jobs 
            (name, workflow_id, cron_expression, target_ips, target_group_id, parameters, enabled, description, next_run_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, name, workflow_id, cron_expression, enabled, next_run_at, created_at
        """, (
            req.name, req.workflow_id, req.cron_expression,
            req.target_ips, req.target_group_id, req.parameters,
            req.enabled, req.description, next_run
        ))
        schedule = dict(cursor.fetchone())
        db.commit()
    
    return success_response(schedule)


@router.get("/{schedule_id}")
async def get_schedule(schedule_id: int):
    """Get a scheduled job by ID."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT s.*, w.name as workflow_name
            FROM scheduled_jobs s
            LEFT JOIN workflows w ON s.workflow_id = w.id
            WHERE s.id = %s
        """, (schedule_id,))
        schedule = cursor.fetchone()
        if not schedule:
            return error_response('NOT_FOUND', 'Schedule not found')
    return success_response(dict(schedule))


@router.put("/{schedule_id}")
async def update_schedule(schedule_id: int, req: ScheduleUpdate):
    """Update a scheduled job."""
    from croniter import croniter
    from datetime import datetime
    
    updates = []
    params = []
    
    if req.name is not None:
        updates.append("name = %s")
        params.append(req.name)
    if req.cron_expression is not None:
        # Validate cron expression
        try:
            cron = croniter(req.cron_expression, datetime.now())
            next_run = cron.get_next(datetime)
            updates.append("cron_expression = %s")
            params.append(req.cron_expression)
            updates.append("next_run_at = %s")
            params.append(next_run)
        except Exception as e:
            return error_response('VALIDATION_ERROR', f'Invalid cron expression: {e}')
    if req.target_ips is not None:
        updates.append("target_ips = %s")
        params.append(req.target_ips)
    if req.target_group_id is not None:
        updates.append("target_group_id = %s")
        params.append(req.target_group_id)
    if req.parameters is not None:
        updates.append("parameters = %s")
        params.append(req.parameters)
    if req.enabled is not None:
        updates.append("enabled = %s")
        params.append(req.enabled)
    if req.description is not None:
        updates.append("description = %s")
        params.append(req.description)
    
    if not updates:
        return error_response('VALIDATION_ERROR', 'No fields to update')
    
    updates.append("updated_at = NOW()")
    params.append(schedule_id)
    
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(f"""
            UPDATE scheduled_jobs
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id, name, workflow_id, cron_expression, enabled, next_run_at
        """, params)
        schedule = cursor.fetchone()
        if not schedule:
            return error_response('NOT_FOUND', 'Schedule not found')
        db.commit()
    
    return success_response(dict(schedule))


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int):
    """Delete a scheduled job."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("DELETE FROM scheduled_jobs WHERE id = %s RETURNING id", (schedule_id,))
        deleted = cursor.fetchone()
        if not deleted:
            return error_response('NOT_FOUND', 'Schedule not found')
        db.commit()
    return success_response({"deleted": True, "id": schedule_id})


@router.post("/{schedule_id}/run")
async def run_schedule_now(schedule_id: int):
    """Run a scheduled job immediately."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT workflow_id, target_ips, target_group_id, parameters
            FROM scheduled_jobs WHERE id = %s
        """, (schedule_id,))
        schedule = cursor.fetchone()
        if not schedule:
            return error_response('NOT_FOUND', 'Schedule not found')
    
    try:
        from backend.services.job_service import JobService
        
        job_service = JobService()
        result = job_service.run_job(
            workflow_id=schedule['workflow_id'],
            target_ips=schedule['target_ips'],
            target_group_id=schedule['target_group_id'],
            parameters=schedule['parameters']
        )
        
        return success_response(result)
    except Exception as e:
        logger.error(f"Schedule run error: {e}")
        return error_response('JOB_ERROR', str(e))


@router.post("/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: int):
    """Toggle a schedule's enabled state."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            UPDATE scheduled_jobs
            SET enabled = NOT enabled, updated_at = NOW()
            WHERE id = %s
            RETURNING id, enabled
        """, (schedule_id,))
        result = cursor.fetchone()
        if not result:
            return error_response('NOT_FOUND', 'Schedule not found')
        db.commit()
    
    return success_response(dict(result))
