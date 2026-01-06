"""
Automation API Router (/automation/v1)

Handles workflows, job executions, schedules, and automation tasks.
"""

from fastapi import APIRouter, Query, Path, Body, Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List, Dict, Any
import logging

from backend.utils.db import db_query
from backend.openapi.automation_impl import (
    list_workflows_paginated, get_workflow_by_id, list_job_executions_paginated,
    trigger_workflow_execution, get_execution_status, cancel_execution,
    list_schedules, get_job_statistics, test_automation_endpoints
)

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/automation/v1", tags=["automation", "workflows", "jobs"])


@router.get("/workflows", summary="List workflows")
async def list_workflows(
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    folder_id: Optional[int] = Query(None),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """List automation workflows"""
    try:
        return await list_workflows_paginated(cursor_str=cursor, limit=limit)
    except Exception as e:
        logger.error(f"List workflows error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "LIST_WORKFLOWS_ERROR", "message": str(e)})


@router.get("/workflows/{workflow_id}", summary="Get workflow")
async def get_workflow(
    workflow_id: int = Path(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get workflow details"""
    try:
        workflow = await get_workflow_by_id(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Workflow not found"})
        return workflow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get workflow error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "GET_WORKFLOW_ERROR", "message": str(e)})


@router.post("/workflows/{workflow_id}/execute", summary="Execute workflow")
async def execute_workflow(
    workflow_id: int = Path(...),
    request: Dict[str, Any] = Body(default={}),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Trigger workflow execution"""
    try:
        return await trigger_workflow_execution(str(workflow_id), "api_user", request.get('parameters', {}))
    except Exception as e:
        logger.error(f"Execute workflow error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "EXECUTE_ERROR", "message": str(e)})


@router.get("/executions", summary="List executions")
async def list_executions(
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """List job executions"""
    try:
        return await list_job_executions_paginated(cursor_str=cursor, limit=limit, status_filter=status)
    except Exception as e:
        logger.error(f"List executions error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "LIST_EXECUTIONS_ERROR", "message": str(e)})


@router.get("/executions/{execution_id}", summary="Get execution status")
async def get_execution(
    execution_id: str = Path(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get execution status"""
    try:
        return await get_execution_status(execution_id)
    except Exception as e:
        logger.error(f"Get execution error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "GET_EXECUTION_ERROR", "message": str(e)})


@router.post("/executions/{execution_id}/cancel", summary="Cancel execution")
async def cancel_exec(
    execution_id: str = Path(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Cancel a running execution"""
    try:
        return await cancel_execution(execution_id, "api_user")
    except Exception as e:
        logger.error(f"Cancel execution error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "CANCEL_ERROR", "message": str(e)})


@router.get("/schedules", summary="List schedules")
async def get_schedules(credentials: HTTPAuthorizationCredentials = Security(security)):
    """List job schedules"""
    try:
        return await list_schedules()
    except Exception as e:
        logger.error(f"List schedules error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "LIST_SCHEDULES_ERROR", "message": str(e)})


@router.get("/statistics", summary="Get job statistics")
async def get_statistics(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get job execution statistics"""
    try:
        return await get_job_statistics()
    except Exception as e:
        logger.error(f"Get statistics error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "STATISTICS_ERROR", "message": str(e)})


# Scheduler endpoints
@router.get("/scheduler/queues", summary="List job queues")
async def list_queues(credentials: HTTPAuthorizationCredentials = Security(security)):
    """List job queues - returns Celery queue info"""
    try:
        # Try to get real Celery worker info
        try:
            from backend.celery_app import celery_app
            inspect = celery_app.control.inspect(timeout=3.0)
            active = inspect.active() or {}
            reserved = inspect.reserved() or {}
            stats = inspect.stats() or {}
            
            workers = []
            active_total = 0
            reserved_total = 0
            
            for worker_name, worker_stats in stats.items():
                worker_active = active.get(worker_name, [])
                worker_reserved = reserved.get(worker_name, [])
                active_total += len(worker_active)
                reserved_total += len(worker_reserved)
                
                workers.append({
                    "name": worker_name,
                    "concurrency": worker_stats.get('pool', {}).get('max-concurrency', 1),
                    "active": len(worker_active),
                    "reserved": len(worker_reserved),
                    "active_tasks": [{"name": t.get('name', 'unknown'), "id": t.get('id')} for t in worker_active]
                })
            
            return {
                "workers": workers,
                "active_total": active_total,
                "reserved_total": reserved_total,
                "queues": [{"name": "default", "pending": 0}, {"name": "polling", "pending": 0}]
            }
        except Exception as celery_err:
            logger.warning(f"Could not get Celery info: {celery_err}")
            # Return empty but valid structure
            return {
                "workers": [],
                "active_total": 0,
                "reserved_total": 0,
                "queues": []
            }
    except Exception as e:
        logger.error(f"List queues error: {str(e)}")
        return {"workers": [], "active_total": 0, "reserved_total": 0, "queues": []}


@router.get("/scheduler/jobs", summary="List scheduled jobs")
async def list_jobs(credentials: HTTPAuthorizationCredentials = Security(security)):
    """List scheduled jobs"""
    try:
        jobs = db_query("SELECT * FROM scheduled_jobs ORDER BY name")
        return {"jobs": jobs, "total": len(jobs)}
    except Exception as e:
        logger.error(f"List jobs error: {str(e)}")
        return {"jobs": [], "total": 0}


@router.get("/scheduler/executions/recent", summary="Get recent executions")
async def recent_executions(
    limit: int = Query(200, ge=1, le=1000),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get recent job executions"""
    try:
        executions = db_query("""
            SELECT * FROM job_executions 
            ORDER BY started_at DESC LIMIT %s
        """, (limit,))
        return {"executions": executions}
    except Exception as e:
        logger.error(f"Get recent executions error: {str(e)}")
        return {"executions": []}


@router.get("/scheduler/executions/{execution_id}/audit", summary="Get execution audit")
async def execution_audit(
    execution_id: int = Path(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get execution audit trail"""
    return {"data": []}


@router.get("/test", include_in_schema=False)
async def test_api():
    """Test Automation API"""
    try:
        results = await test_automation_endpoints()
        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "error": str(e)}
