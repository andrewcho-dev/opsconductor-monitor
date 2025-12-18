"""
Scheduler API Blueprint.

Routes for scheduler job management and execution history.
"""

from flask import Blueprint, request, jsonify
from ..utils.responses import success_response, error_response, list_response
from ..utils.errors import AppError, NotFoundError, ValidationError


scheduler_bp = Blueprint('scheduler', __name__, url_prefix='/api/scheduler')


def get_scheduler_service():
    """Get scheduler service instance."""
    from database import DatabaseManager
    from ..repositories.scheduler_repo import SchedulerJobRepository
    from ..repositories.execution_repo import ExecutionRepository
    from ..repositories.job_repo import JobDefinitionRepository
    from ..services.scheduler_service import SchedulerService
    
    db = DatabaseManager()
    scheduler_repo = SchedulerJobRepository(db)
    execution_repo = ExecutionRepository(db)
    job_repo = JobDefinitionRepository(db)
    return SchedulerService(scheduler_repo, execution_repo, job_repo)


@scheduler_bp.errorhandler(AppError)
def handle_app_error(error):
    """Handle application errors."""
    return jsonify(error_response(error.code, error.message, error.details)), error.status_code


@scheduler_bp.errorhandler(Exception)
def handle_generic_error(error):
    """Handle unexpected errors."""
    return jsonify(error_response('INTERNAL_ERROR', str(error))), 500


@scheduler_bp.route('/jobs', methods=['GET'])

def list_jobs():
    """
    List all scheduler jobs.
    
    Query params:
        enabled: Filter by enabled status ('true' or 'false')
    
    Returns:
        List of scheduler jobs
    """
    service = get_scheduler_service()
    
    enabled_param = request.args.get('enabled')
    enabled = None
    if enabled_param is not None:
        enabled = enabled_param.lower() == 'true'
    
    jobs = service.list_jobs(enabled=enabled)
    
    return jsonify(list_response(jobs))


@scheduler_bp.route('/jobs/<name>', methods=['GET'])

def get_job(name):
    """
    Get a single scheduler job by name.
    
    Args:
        name: Job name
    
    Query params:
        include_executions: Include recent executions (default: false)
        execution_limit: Max executions to include (default: 10)
    
    Returns:
        Scheduler job
    """
    service = get_scheduler_service()
    
    include_executions = request.args.get('include_executions', 'false').lower() == 'true'
    execution_limit = int(request.args.get('execution_limit', '10'))
    
    if include_executions:
        job = service.get_job_with_executions(name, execution_limit)
    else:
        job = service.get_job(name)
    
    return jsonify(success_response(job))


@scheduler_bp.route('/jobs', methods=['POST'])

def create_or_update_job():
    """
    Create or update a scheduler job.
    
    Body:
        name: Unique job name (required)
        task_name: Celery task name (required)
        config: Job configuration
        interval_seconds: Interval for interval scheduling
        cron_expression: Cron expression for cron scheduling
        enabled: Whether job is enabled (default: true)
        schedule_type: 'interval' or 'cron' (default: 'interval')
        job_definition_id: Optional linked job definition
    
    Returns:
        Created/updated job
    """
    service = get_scheduler_service()
    data = request.get_json() or {}
    
    required_fields = ['name', 'task_name']
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise ValidationError(f'Missing required fields: {", ".join(missing)}')
    
    job = service.create_or_update_job(
        name=data['name'],
        task_name=data['task_name'],
        config=data.get('config'),
        interval_seconds=data.get('interval_seconds'),
        cron_expression=data.get('cron_expression'),
        enabled=data.get('enabled', True),
        schedule_type=data.get('schedule_type', 'interval'),
        job_definition_id=data.get('job_definition_id')
    )
    
    return jsonify(success_response(job, message='Scheduler job saved'))


@scheduler_bp.route('/jobs/<name>', methods=['DELETE'])

def delete_job(name):
    """
    Delete a scheduler job.
    
    Args:
        name: Job name
    
    Returns:
        Success message
    """
    service = get_scheduler_service()
    service.delete_job(name)
    
    return jsonify(success_response(message='Scheduler job deleted'))


@scheduler_bp.route('/jobs/<name>/enable', methods=['POST'])

def enable_job(name):
    """
    Enable a scheduler job.
    
    Args:
        name: Job name
    
    Returns:
        Updated job
    """
    service = get_scheduler_service()
    job = service.set_enabled(name, True)
    
    return jsonify(success_response(job, message='Scheduler job enabled'))


@scheduler_bp.route('/jobs/<name>/disable', methods=['POST'])

def disable_job(name):
    """
    Disable a scheduler job.
    
    Args:
        name: Job name
    
    Returns:
        Updated job
    """
    service = get_scheduler_service()
    job = service.set_enabled(name, False)
    
    return jsonify(success_response(job, message='Scheduler job disabled'))


@scheduler_bp.route('/jobs/<name>/toggle', methods=['POST'])

def toggle_job(name):
    """
    Toggle a scheduler job's enabled state.
    
    Args:
        name: Job name
    
    Body:
        enabled: New enabled state (boolean)
    
    Returns:
        Updated job
    """
    service = get_scheduler_service()
    data = request.get_json() or {}
    
    enabled = data.get('enabled')
    if enabled is None:
        # If not specified, toggle current state
        current_job = service.get_job(name)
        enabled = not current_job.get('enabled', True)
    
    job = service.set_enabled(name, enabled)
    
    message = 'Scheduler job enabled' if enabled else 'Scheduler job disabled'
    return jsonify(success_response(job, message=message))


@scheduler_bp.route('/jobs/<name>/run-once', methods=['POST'])

def run_job_once(name):
    """
    Trigger a one-off run of a scheduler job.
    
    Args:
        name: Job name
    
    Returns:
        Task info
    """
    from flask import g
    service = get_scheduler_service()
    
    # Get job to verify it exists and get config
    job = service.get_job(name)
    
    # Import celery and trigger task
    from celery_app import celery_app
    
    task_name = job.get('task_name', 'opsconductor.job.run')
    config = job.get('config', {})
    
    # Add user attribution to job config
    user = g.get('current_user')
    if user:
        config['triggered_by'] = {
            'user_id': user.get('user_id'),
            'username': user.get('username'),
            'is_enterprise': user.get('is_enterprise', False),
            'trigger_type': 'manual'
        }
    
    # Send task to celery
    result = celery_app.send_task(task_name, args=[config])
    
    return jsonify(success_response({
        'job_name': name,
        'task_id': result.id,
        'task_name': task_name,
        'status': 'queued',
        'triggered_by': config.get('triggered_by', {}).get('username')
    }, message='Job queued for execution'))


@scheduler_bp.route('/jobs/<name>/executions', methods=['GET'])

def get_job_executions(name):
    """
    Get execution history for a scheduler job.
    
    Args:
        name: Job name
    
    Query params:
        limit: Max results (default: 100)
        status: Filter by status
    
    Returns:
        List of executions
    """
    service = get_scheduler_service()
    
    limit = int(request.args.get('limit', '100'))
    status = request.args.get('status')
    
    executions = service.get_recent_executions(
        job_name=name,
        limit=limit,
        status=status
    )
    
    return jsonify(list_response(executions))


@scheduler_bp.route('/jobs/<name>/executions/clear', methods=['POST'])

def clear_job_executions(name):
    """
    Clear execution history for a scheduler job.
    
    Args:
        name: Job name
    
    Body:
        status: Optional status filter
    
    Returns:
        Number of deleted records
    """
    service = get_scheduler_service()
    data = request.get_json() or {}
    
    deleted = service.clear_executions(
        job_name=name,
        status=data.get('status')
    )
    
    return jsonify(success_response({'deleted': deleted}, message=f'Cleared {deleted} executions'))


@scheduler_bp.route('/executions/recent', methods=['GET'])
def get_recent_executions():
    """
    Get recent executions across all jobs.
    
    Query params:
        limit: Max results (default: 100)
        status: Filter by status
        include_result: Include full result data (default: false for list view)
    
    Returns:
        List of executions
    """
    service = get_scheduler_service()
    
    limit = int(request.args.get('limit', '100'))
    status = request.args.get('status')
    include_result = request.args.get('include_result', 'false').lower() == 'true'
    
    # Exclude result at database level for performance (32MB+ of data)
    executions = service.get_recent_executions(
        limit=limit,
        status=status,
        exclude_result=not include_result
    )
    
    return jsonify(list_response(executions))


@scheduler_bp.route('/executions/stats', methods=['GET'])

def get_execution_stats():
    """
    Get execution statistics.
    
    Query params:
        job_name: Optional job name filter
        hours: Time window in hours (default: 24)
    
    Returns:
        Statistics dictionary
    """
    service = get_scheduler_service()
    
    job_name = request.args.get('job_name')
    hours = int(request.args.get('hours', '24'))
    
    stats = service.get_execution_stats(job_name=job_name, hours=hours)
    
    return jsonify(success_response(stats))


@scheduler_bp.route('/executions/stale', methods=['POST'])

def mark_stale_executions():
    """
    Mark stale running/queued executions as timed out.
    
    Body:
        timeout_seconds: Timeout threshold (default: 600)
    
    Returns:
        Number of marked executions
    """
    service = get_scheduler_service()
    data = request.get_json() or {}
    
    timeout = data.get('timeout_seconds', 600)
    marked = service.mark_stale_executions(timeout)
    
    return jsonify(success_response({'marked': marked}, message=f'Marked {marked} stale executions'))


@scheduler_bp.route('/executions/<int:execution_id>/progress', methods=['GET'])

def get_execution_progress(execution_id):
    """
    Get live progress for a running execution.
    
    Args:
        execution_id: Execution ID
    
    Returns:
        Progress data including steps, current step, and percent complete
    """
    from database import DatabaseManager
    from ..repositories.execution_repo import ExecutionRepository
    
    db = DatabaseManager()
    execution_repo = ExecutionRepository(db)
    execution = execution_repo.get_by_id(execution_id)
    
    if not execution:
        raise NotFoundError(f'Execution {execution_id} not found')
    
    task_id = execution.get('task_id')
    progress_data = execution_repo.get_live_progress(task_id) if task_id else None
    
    if not progress_data:
        progress_data = {
            'task_id': task_id,
            'status': execution.get('status'),
            'job_name': execution.get('job_name'),
            'started_at': execution.get('started_at'),
            'progress': {'steps': [], 'current_step': None, 'percent': 0}
        }
    
    return jsonify(success_response(progress_data))


@scheduler_bp.route('/executions/<int:execution_id>/cancel', methods=['POST'])

def cancel_execution(execution_id):
    """
    Cancel a running execution.
    
    Args:
        execution_id: Execution ID
    
    Returns:
        Success message
    """
    service = get_scheduler_service()
    
    # Get the execution to find its task_id
    from database import DatabaseManager
    from ..repositories.execution_repo import ExecutionRepository
    
    db = DatabaseManager()
    execution_repo = ExecutionRepository(db)
    execution = execution_repo.get_by_id(execution_id)
    
    if not execution:
        raise NotFoundError(f'Execution {execution_id} not found')
    
    task_id = execution.get('task_id')
    
    # Try to revoke the Celery task if we have a task_id
    if task_id:
        try:
            from celery_app import celery_app
            celery_app.control.revoke(task_id, terminate=True)
        except Exception as e:
            # Log but don't fail - task may have already completed
            import logging
            logging.warning(f"Failed to revoke task {task_id}: {e}")
    
    # Update execution status to cancelled
    execution_repo.update_status(execution_id, 'cancelled')
    
    return jsonify(success_response(message='Execution cancelled'))


@scheduler_bp.route('/queues', methods=['GET'])

def get_queue_status():
    """
    Get Celery queue status.
    
    Returns:
        Queue statistics including active, reserved, scheduled counts
    """
    try:
        from celery_app import celery_app
        
        inspect = celery_app.control.inspect()
        
        # Get active tasks (currently executing)
        active = inspect.active() or {}
        active_total = sum(len(tasks) for tasks in active.values())
        
        # Get reserved tasks (received but not yet executing)
        reserved = inspect.reserved() or {}
        reserved_total = sum(len(tasks) for tasks in reserved.values())
        
        # Get scheduled tasks (eta/countdown)
        scheduled = inspect.scheduled() or {}
        scheduled_total = sum(len(tasks) for tasks in scheduled.values())
        
        # Get list of all workers from active, reserved, or scheduled
        all_workers = set(active.keys()) | set(reserved.keys()) | set(scheduled.keys())
        
        # Build worker details
        worker_details = {}
        for worker in all_workers:
            worker_details[worker] = {
                'active': len(active.get(worker, [])),
                'active_tasks': active.get(worker, []),
                'reserved': len(reserved.get(worker, [])),
                'scheduled': len(scheduled.get(worker, [])),
                'concurrency': None,  # Would need stats() call
            }
        
        return jsonify(success_response({
            'workers': list(all_workers),
            'worker_details': worker_details,
            'active': active_total,
            'active_total': active_total,
            'active_by_worker': {k: len(v) for k, v in active.items()},
            'reserved': reserved_total,
            'reserved_total': reserved_total,
            'scheduled': scheduled_total,
            'scheduled_total': scheduled_total,
        }))
    except Exception as e:
        # Return zeros if Celery is not available
        return jsonify(success_response({
            'active': 0,
            'active_total': 0,
            'active_by_worker': {},
            'reserved': 0,
            'reserved_total': 0,
            'scheduled': 0,
            'scheduled_total': 0,
            'error': str(e)
        }))


@scheduler_bp.route('/executions/<int:execution_id>/audit', methods=['GET'])

def get_execution_audit_trail(execution_id):
    """
    Get complete audit trail for an execution.
    
    Returns all events that occurred during the execution including:
    - Job start/end timestamps
    - Each action start/end
    - Every database operation with record IDs
    - All errors
    
    Args:
        execution_id: Execution ID
    
    Returns:
        List of audit events in chronological order
    """
    from database import get_db
    from ..repositories.audit_repo import JobAuditRepository
    
    db = get_db()
    audit_repo = JobAuditRepository(db)
    
    events = audit_repo.get_execution_audit_trail(execution_id=execution_id)
    
    return jsonify(success_response(events))


@scheduler_bp.route('/executions/<int:execution_id>/db-operations', methods=['GET'])

def get_execution_db_operations(execution_id):
    """
    Get all database operations for an execution.
    
    Returns only insert/update/delete events with links to affected records.
    
    Args:
        execution_id: Execution ID
    
    Returns:
        List of database operations with record references
    """
    from database import get_db
    from ..repositories.audit_repo import JobAuditRepository
    
    db = get_db()
    audit_repo = JobAuditRepository(db)
    
    operations = audit_repo.get_db_operations_for_execution(execution_id=execution_id)
    affected_records = audit_repo.get_records_affected_by_execution(execution_id=execution_id)
    
    return jsonify(success_response({
        'operations': operations,
        'affected_records': affected_records
    }))
