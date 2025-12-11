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


@scheduler_bp.route('/jobs/<name>/run-once', methods=['POST'])
def run_job_once(name):
    """
    Trigger a one-off run of a scheduler job.
    
    Args:
        name: Job name
    
    Returns:
        Task info
    """
    service = get_scheduler_service()
    
    # Get job to verify it exists and get config
    job = service.get_job(name)
    
    # Import celery and trigger task
    from celery_app import celery
    
    task_name = job.get('task_name', 'opsconductor.job.run')
    config = job.get('config', {})
    
    # Send task to celery
    result = celery.send_task(task_name, args=[config])
    
    return jsonify(success_response({
        'job_name': name,
        'task_id': result.id,
        'task_name': task_name,
        'status': 'queued'
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
    
    Returns:
        List of executions
    """
    service = get_scheduler_service()
    
    limit = int(request.args.get('limit', '100'))
    status = request.args.get('status')
    
    executions = service.get_recent_executions(limit=limit, status=status)
    
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
