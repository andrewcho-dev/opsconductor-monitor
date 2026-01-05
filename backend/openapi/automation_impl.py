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
        )
    """, (table_name,))
    return cursor.fetchone()[0]

# ============================================================================
# Automation API Business Logic
# ============================================================================

async def list_workflows_paginated(
    cursor: Optional[str] = None, 
    limit: int = 50,
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    List workflows with pagination and filtering
    Migrated from legacy /api/workflows
    """
    db = get_db()
    with db.cursor() as cursor:
        # Build query with filters
        where_clauses = []
        params = []
        
        if search:
            where_clauses.append("(w.name ILIKE %s OR w.description ILIKE %s)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param])
        
        if status_filter:
            where_clauses.append("w.status = %s")
            params.append(status_filter)
        
        if category:
            where_clauses.append("w.category = %s")
            params.append(category)
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM workflows w
            {where_clause}
        """
        
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # Apply pagination
        if cursor:
            # Decode cursor (for simplicity, using workflow ID as cursor)
            try:
                import base64
                cursor_data = json.loads(base64.b64decode(cursor).decode())
                last_id = cursor_data.get('last_id')
                where_clauses.append("w.id > %s")
                params.append(last_id)
            except:
                pass
        
        # Get paginated results
        query = f"""
            SELECT w.id, w.name, w.description, w.category, w.status,
                   w.version, w.created_at, w.updated_at, w.created_by,
                   w.schedule_enabled, w.last_run_at, w.next_run_at,
                   (SELECT COUNT(*) FROM workflow_executions e 
                    WHERE e.workflow_id = w.id) as execution_count
            FROM workflows w
            {where_clause}
            ORDER BY w.id
            LIMIT %s
        """
        
        params.append(limit + 1)  # Get one extra to determine if there's a next page
        cursor.execute(query, params)
        
        workflows = [dict(row) for row in cursor.fetchall()]
        
        # Determine if there's a next page
        has_more = len(workflows) > limit
        if has_more:
            workflows = workflows[:-1]  # Remove the extra item
        
        # Generate next cursor
        next_cursor = None
        if has_more and workflows:
            last_id = workflows[-1]['id']
            cursor_data = json.dumps({'last_id': last_id})
            import base64
            next_cursor = base64.b64encode(cursor_data.encode()).decode()
        
        return {
            'items': workflows,
            'total': total,
            'limit': limit,
            'cursor': next_cursor
        }

async def get_workflow_by_id(workflow_id: str) -> Dict[str, Any]:
    """
    Get workflow details by ID
    Migrated from legacy /api/workflows/{id}
    """
    db = get_db()
    with db.cursor() as cursor:
        if not _table_exists(cursor, 'workflows'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "WORKFLOW_NOT_FOUND",
                    "message": f"Workflow with ID '{workflow_id}' not found"
                }
            )
        
        cursor.execute("""
            SELECT w.id, w.name, w.description, w.category, w.status,
                   w.version, w.definition, w.parameters, w.created_at,
                   w.updated_at, w.created_by, w.schedule_enabled,
                   w.schedule_cron, w.last_run_at, w.next_run_at
            FROM workflows w
            WHERE w.id = %s
        """, (workflow_id,))
        
        workflow = cursor.fetchone()
        
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "WORKFLOW_NOT_FOUND",
                    "message": f"Workflow with ID '{workflow_id}' not found"
                }
            )
        
        return dict(workflow)

async def list_job_executions_paginated(
    cursor: Optional[str] = None, 
    limit: int = 50,
    workflow_id: Optional[str] = None,
    status_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    List job executions with pagination and filtering
    Migrated from legacy /api/scheduler/executions
    """
    db = get_db()
    with db.cursor() as cursor:
        # Build query with filters
        where_clauses = []
        params = []
        
        if workflow_id:
            where_clauses.append("e.workflow_id = %s")
            params.append(workflow_id)
        
        if status_filter:
            where_clauses.append("e.status = %s")
            params.append(status_filter)
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM workflow_executions e
            {where_clause}
        """
        
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # Apply pagination
        if cursor:
            # Decode cursor (for simplicity, using execution ID as cursor)
            try:
                import base64
                cursor_data = json.loads(base64.b64decode(cursor).decode())
                last_id = cursor_data.get('last_id')
                where_clauses.append("e.id > %s")
                params.append(last_id)
            except:
                pass
        
        # Get paginated results
        query = f"""
            SELECT e.id, e.workflow_id, e.status, e.started_at, e.completed_at,
                   e.duration_seconds, e.trigger_type, e.triggered_by,
                   e.result, e.error_message, e.progress,
                   w.name as workflow_name, w.category as workflow_category
            FROM workflow_executions e
            LEFT JOIN workflows w ON e.workflow_id = w.id
            {where_clause}
            ORDER BY e.started_at DESC, e.id
            LIMIT %s
        """
        
        params.append(limit + 1)  # Get one extra to determine if there's a next page
        cursor.execute(query, params)
        
        executions = [dict(row) for row in cursor.fetchall()]
        
        # Determine if there's a next page
        has_more = len(executions) > limit
        if has_more:
            executions = executions[:-1]  # Remove the extra item
        
        # Generate next cursor
        next_cursor = None
        if has_more and executions:
            last_id = executions[-1]['id']
            cursor_data = json.dumps({'last_id': last_id})
            import base64
            next_cursor = base64.b64encode(cursor_data.encode()).decode()
        
        return {
            'items': executions,
            'total': total,
            'limit': limit,
            'cursor': next_cursor
        }

async def trigger_workflow_execution(
    workflow_id: str, 
    triggered_by: str,
    parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """
    Trigger a workflow execution
    Migrated from legacy /api/jobs/run
    """
    db = get_db()
    with db.cursor() as cursor:
        # Verify workflow exists and is active
        cursor.execute("""
            SELECT id, name, status FROM workflows 
            WHERE id = %s
        """, (workflow_id,))
        
        workflow = cursor.fetchone()
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "WORKFLOW_NOT_FOUND",
                    "message": f"Workflow with ID '{workflow_id}' not found"
                }
            )
        
        if workflow['status'] != 'active':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "WORKFLOW_INACTIVE",
                    "message": f"Workflow '{workflow['name']}' is not active"
                }
            )
        
        # Create execution record
        cursor.execute("""
            INSERT INTO workflow_executions 
            (workflow_id, status, started_at, trigger_type, triggered_by, parameters)
            VALUES (%s, 'running', NOW(), 'manual', %s, %s)
            RETURNING id
        """, (workflow_id, triggered_by, json.dumps(parameters or {})))
        
        execution_id = cursor.fetchone()['id']
        
        # Update workflow last run time
        cursor.execute("""
            UPDATE workflows 
            SET last_run_at = NOW() 
            WHERE id = %s
        """, (workflow_id,))
        
        db.commit()
        
        logger.info(f"Workflow {workflow_id} triggered by {triggered_by}, execution {execution_id}")
        
        # In a real implementation, you would queue the job for execution here
        # For now, we'll just return the execution ID
        
        return {
            "execution_id": str(execution_id),
            "status": "running",
            "message": "Workflow execution started successfully"
        }

async def get_execution_status(execution_id: str) -> Dict[str, Any]:
    """
    Get execution status and progress
    Migrated from legacy /api/scheduler/executions/{id}/progress
    """
    db = get_db()
    with db.cursor() as cursor:
        if not _table_exists(cursor, 'workflow_executions'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "EXECUTION_NOT_FOUND",
                    "message": f"Execution with ID '{execution_id}' not found"
                }
            )
        
        cursor.execute("""
            SELECT e.id, e.workflow_id, e.status, e.started_at, e.completed_at,
                   e.duration_seconds, e.trigger_type, e.triggered_by,
                   e.result, e.error_message, e.progress, e.log_output,
                   w.name as workflow_name
            FROM workflow_executions e
            LEFT JOIN workflows w ON e.workflow_id = w.id
            WHERE e.id = %s
        """, (execution_id,))
        
        execution = cursor.fetchone()
        
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "EXECUTION_NOT_FOUND",
                    "message": f"Execution with ID '{execution_id}' not found"
                }
            )
        
        return dict(execution)

async def cancel_execution(execution_id: str, cancelled_by: str) -> Dict[str, str]:
    """
    Cancel a running execution
    Migrated from legacy /api/scheduler/executions/{id}/cancel
    """
    db = get_db()
    with db.cursor() as cursor:
        # Check if execution exists and is running
        cursor.execute("""
            SELECT id, status, workflow_id FROM workflow_executions 
            WHERE id = %s
        """, (execution_id,))
        
        execution = cursor.fetchone()
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "EXECUTION_NOT_FOUND",
                    "message": f"Execution with ID '{execution_id}' not found"
                }
            )
        
        if execution['status'] not in ['running', 'pending']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "EXECUTION_NOT_CANCELLABLE",
                    "message": f"Execution cannot be cancelled (current status: {execution['status']})"
                }
            )
        
        # Update execution status
        cursor.execute("""
            UPDATE workflow_executions 
            SET status = 'cancelled', 
                completed_at = NOW(),
                error_message = 'Cancelled by ' || %s
            WHERE id = %s
        """, (cancelled_by, execution_id))
        
        db.commit()
        
        logger.info(f"Execution {execution_id} cancelled by {cancelled_by}")
        
        return {
            "success": True,
            "message": "Execution cancelled successfully"
        }

async def list_schedules() -> List[Dict[str, Any]]:
    """
    List workflow schedules
    Migrated from legacy /api/scheduler/schedules
    """
    db = get_db()
    with db.cursor() as cursor:
        if not _table_exists(cursor, 'workflows'):
            return []
        
        cursor.execute("""
            SELECT w.id, w.name, w.schedule_cron, w.schedule_enabled,
                   w.last_run_at, w.next_run_at, w.created_at,
                   (SELECT COUNT(*) FROM workflow_executions e 
                    WHERE e.workflow_id = w.id 
                    AND e.trigger_type = 'scheduled') as scheduled_runs
            FROM workflows w
            WHERE w.schedule_enabled = true
            ORDER BY w.name
        """)
        
        schedules = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        
        return schedules

async def get_job_statistics() -> Dict[str, Any]:
    """
    Get job execution statistics
    """
    db = get_db()
    with db.cursor() as cursor:
        if not _table_exists(cursor, 'workflow_executions'):
            return {
                "total_executions": 0,
                "by_status": {},
                "by_trigger_type": {},
                "recent_24h": 0,
                "recent_7d": 0,
                "average_duration": 0
            }
        
        # Overall stats
        cursor.execute("SELECT COUNT(*) as total FROM workflow_executions")
        total = cursor.fetchone()['total']
        
        # By status
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM workflow_executions 
            GROUP BY status
        """)
        by_status = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # By trigger type
        cursor.execute("""
            SELECT trigger_type, COUNT(*) as count 
            FROM workflow_executions 
            GROUP BY trigger_type
        """)
        by_trigger_type = {row['trigger_type']: row['count'] for row in cursor.fetchall()}
        
        # Recent activity
        cursor.execute("""
            SELECT COUNT(*) as count FROM workflow_executions 
            WHERE started_at >= NOW() - INTERVAL '24 hours'
        """)
        recent_24h = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM workflow_executions 
            WHERE started_at >= NOW() - INTERVAL '7 days'
        """)
        recent_7d = cursor.fetchone()['count']
        
        # Average duration
        cursor.execute("""
            SELECT AVG(duration_seconds) as avg_duration 
            FROM workflow_executions 
            WHERE status = 'completed' AND duration_seconds IS NOT NULL
        """)
        avg_duration = cursor.fetchone()['avg_duration'] or 0
        
        return {
            "total_executions": total,
            "by_status": by_status,
            "by_trigger_type": by_trigger_type,
            "recent_24h": recent_24h,
            "recent_7d": recent_7d,
            "average_duration": round(avg_duration, 2)
        }

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
