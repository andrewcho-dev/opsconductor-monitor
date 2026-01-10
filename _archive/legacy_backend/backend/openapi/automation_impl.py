"""
Automation API Implementation - OpenAPI 3.x Migration
This implements the actual business logic for automation endpoints
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.utils.db import db_query, db_query_one, db_execute, table_exists, db_paginate, db_transaction
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
# Automation API Business Logic
# ============================================================================

async def list_workflows_paginated(
    cursor_str: Optional[str] = None, 
    limit: int = 50,
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    List workflows with pagination and filtering
    Uses same schema as legacy /api/workflows
    """
    where_clauses = ["1=1"]
    params = []
    
    if search:
        where_clauses.append("(w.name ILIKE %s OR w.description ILIKE %s)")
        search_param = f"%{search}%"
        params.extend([search_param, search_param])
    
    if status_filter:
        where_clauses.append("w.enabled = %s")
        params.append(status_filter == 'enabled')
    
    where_clause = "WHERE " + " AND ".join(where_clauses)
    
    return db_paginate(
        f"""SELECT w.id::text as id, w.name, w.description, 
               w.folder_id::text as folder_id, w.enabled,
               w.is_template, w.created_at, w.updated_at, w.last_run_at,
               (SELECT COUNT(*) FROM workflow_executions e WHERE e.workflow_id = w.id) as execution_count
            FROM workflows w {where_clause} ORDER BY w.id""",
        f"SELECT COUNT(*) as total FROM workflows w {where_clause}",
        params, limit
    )

async def get_workflow_by_id(workflow_id: str) -> Dict[str, Any]:
    """
    Get workflow details by ID
    Migrated from legacy /api/workflows/{id}
    """
    if not table_exists('workflows'):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WORKFLOW_NOT_FOUND", "message": f"Workflow with ID '{workflow_id}' not found"})
    
    workflow = db_query_one("""
        SELECT w.id, w.name, w.description, w.category, w.status,
               w.version, w.definition, w.parameters, w.created_at,
               w.updated_at, w.created_by, w.schedule_enabled,
               w.schedule_cron, w.last_run_at, w.next_run_at
        FROM workflows w WHERE w.id = %s
    """, (workflow_id,))
    
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WORKFLOW_NOT_FOUND", "message": f"Workflow with ID '{workflow_id}' not found"})
    
    return workflow

async def list_job_executions_paginated(
    cursor_str: Optional[str] = None, 
    limit: int = 50,
    workflow_id: Optional[str] = None,
    status_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    List job executions with pagination and filtering
    Migrated from legacy /api/scheduler/executions
    """
    where_clauses = []
    params = []
    
    if workflow_id:
        where_clauses.append("e.workflow_id = %s")
        params.append(workflow_id)
    
    if status_filter:
        where_clauses.append("e.status = %s")
        params.append(status_filter)
    
    where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    return db_paginate(
        f"""SELECT e.id, e.workflow_id, e.status, e.started_at, e.completed_at,
               e.duration_seconds, e.trigger_type, e.triggered_by,
               e.result, e.error_message, e.progress,
               w.name as workflow_name, w.category as workflow_category
            FROM workflow_executions e LEFT JOIN workflows w ON e.workflow_id = w.id
            {where_clause} ORDER BY e.started_at DESC, e.id""",
        f"SELECT COUNT(*) as total FROM workflow_executions e {where_clause}",
        params, limit
    )

async def trigger_workflow_execution(
    workflow_id: str, 
    triggered_by: str,
    parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """
    Trigger a workflow execution
    Migrated from legacy /api/jobs/run
    """
    with db_transaction() as tx:
        workflow = tx.query_one("SELECT id, name, status FROM workflows WHERE id = %s", (workflow_id,))
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "WORKFLOW_NOT_FOUND", "message": f"Workflow with ID '{workflow_id}' not found"})
        
        if workflow['status'] != 'active':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "WORKFLOW_INACTIVE", "message": f"Workflow '{workflow['name']}' is not active"})
        
        result = tx.execute("""
            INSERT INTO workflow_executions (workflow_id, status, started_at, trigger_type, triggered_by, parameters)
            VALUES (%s, 'running', NOW(), 'manual', %s, %s) RETURNING id
        """, (workflow_id, triggered_by, json.dumps(parameters or {})))
        execution_id = result['id']
        
        tx.execute("UPDATE workflows SET last_run_at = NOW() WHERE id = %s", (workflow_id,))
        logger.info(f"Workflow {workflow_id} triggered by {triggered_by}, execution {execution_id}")
        
        return {"execution_id": str(execution_id), "status": "running", "message": "Workflow execution started successfully"}

async def get_execution_status(execution_id: str) -> Dict[str, Any]:
    """
    Get execution status and progress
    Migrated from legacy /api/scheduler/executions/{id}/progress
    """
    if not table_exists('workflow_executions'):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EXECUTION_NOT_FOUND", "message": f"Execution with ID '{execution_id}' not found"})
    
    execution = db_query_one("""
        SELECT e.id, e.workflow_id, e.status, e.started_at, e.completed_at,
               e.duration_seconds, e.trigger_type, e.triggered_by,
               e.result, e.error_message, e.progress, e.log_output,
               w.name as workflow_name
        FROM workflow_executions e
        LEFT JOIN workflows w ON e.workflow_id = w.id WHERE e.id = %s
    """, (execution_id,))
    
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EXECUTION_NOT_FOUND", "message": f"Execution with ID '{execution_id}' not found"})
    
    return execution

async def cancel_execution(execution_id: str, cancelled_by: str) -> Dict[str, str]:
    """
    Cancel a running execution
    Migrated from legacy /api/scheduler/executions/{id}/cancel
    """
    with db_transaction() as tx:
        execution = tx.query_one("SELECT id, status, workflow_id FROM workflow_executions WHERE id = %s", (execution_id,))
        if not execution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "EXECUTION_NOT_FOUND", "message": f"Execution with ID '{execution_id}' not found"})
        
        if execution['status'] not in ['running', 'pending']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "EXECUTION_NOT_CANCELLABLE", "message": f"Execution cannot be cancelled (current status: {execution['status']})"})
        
        tx.execute("""
            UPDATE workflow_executions SET status = 'cancelled', completed_at = NOW(),
                error_message = 'Cancelled by ' || %s WHERE id = %s
        """, (cancelled_by, execution_id))
        
        logger.info(f"Execution {execution_id} cancelled by {cancelled_by}")
        return {"success": True, "message": "Execution cancelled successfully"}

async def list_schedules() -> List[Dict[str, Any]]:
    """
    List workflow schedules
    Migrated from legacy /api/scheduler/schedules
    """
    if not table_exists('workflows'):
        return []
    return db_query("""
        SELECT w.id, w.name, w.schedule_cron, w.schedule_enabled,
               w.last_run_at, w.next_run_at, w.created_at,
               (SELECT COUNT(*) FROM workflow_executions e 
                WHERE e.workflow_id = w.id AND e.trigger_type = 'scheduled') as scheduled_runs
        FROM workflows w WHERE w.schedule_enabled = true ORDER BY w.name
    """)

async def get_job_statistics() -> Dict[str, Any]:
    """
    Get job execution statistics
    """
    if not table_exists('workflow_executions'):
        return {"total_executions": 0, "by_status": {}, "by_trigger_type": {},
                "recent_24h": 0, "recent_7d": 0, "average_duration": 0}
    
    total_row = db_query_one("SELECT COUNT(*) as total FROM workflow_executions")
    total = total_row['total'] if total_row else 0
    
    status_rows = db_query("SELECT status, COUNT(*) as count FROM workflow_executions GROUP BY status")
    by_status = {row['status']: row['count'] for row in status_rows}
    
    trigger_rows = db_query("SELECT trigger_type, COUNT(*) as count FROM workflow_executions GROUP BY trigger_type")
    by_trigger_type = {row['trigger_type']: row['count'] for row in trigger_rows}
    
    recent_24h_row = db_query_one("SELECT COUNT(*) as count FROM workflow_executions WHERE started_at >= NOW() - INTERVAL '24 hours'")
    recent_24h = recent_24h_row['count'] if recent_24h_row else 0
    
    recent_7d_row = db_query_one("SELECT COUNT(*) as count FROM workflow_executions WHERE started_at >= NOW() - INTERVAL '7 days'")
    recent_7d = recent_7d_row['count'] if recent_7d_row else 0
    
    avg_row = db_query_one("SELECT AVG(duration_seconds) as avg_duration FROM workflow_executions WHERE status = 'completed' AND duration_seconds IS NOT NULL")
    avg_duration = avg_row['avg_duration'] or 0 if avg_row else 0
    
    return {"total_executions": total, "by_status": by_status, "by_trigger_type": by_trigger_type,
            "recent_24h": recent_24h, "recent_7d": recent_7d, "average_duration": round(avg_duration, 2)}

# ============================================================================
# Testing Functions
# ============================================================================

async def test_automation_endpoints() -> Dict[str, bool]:
    """
    Test all Automation API endpoints
    Returns dict of endpoint: success status
    """
    results = {}
    
    try:
        # Test 1: List workflows (empty)
        workflows_data = await list_workflows_paginated()
        results['list_workflows'] = 'items' in workflows_data and 'total' in workflows_data
        
        # Test 2: Get job statistics
        stats = await get_job_statistics()
        results['get_job_statistics'] = 'total_executions' in stats and 'by_status' in stats
        
        # Test 3: List schedules
        schedules = await list_schedules()
        results['list_schedules'] = isinstance(schedules, list)
        
        # Test 4: List executions
        executions_data = await list_job_executions_paginated()
        results['list_executions'] = 'items' in executions_data and 'total' in executions_data
        
        # Test 5: Get workflow (will fail validation, but should handle gracefully)
        try:
            await get_workflow_by_id("nonexistent")
            results['get_workflow'] = False  # Should not succeed
        except HTTPException:
            results['get_workflow'] = True  # Expected to fail
        
        logger.info(f"Automation API tests completed: {sum(results.values())}/{len(results)} passed")
        
    except Exception as e:
        logger.error(f"Automation API test failed: {str(e)}")
        results['error'] = str(e)
    
    return results
