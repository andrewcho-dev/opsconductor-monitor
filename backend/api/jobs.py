"""
Jobs API Blueprint.

Routes for job definition CRUD operations.
"""

from flask import Blueprint, request, jsonify
from ..utils.responses import success_response, error_response, list_response
from ..utils.errors import AppError, NotFoundError, ValidationError


jobs_bp = Blueprint('jobs', __name__, url_prefix='/api/job-definitions')


def get_job_service():
    """Get job service instance."""
    from database import DatabaseManager
    from ..repositories.job_repo import JobDefinitionRepository
    from ..repositories.scheduler_repo import SchedulerJobRepository
    from ..services.job_service import JobService
    
    db = DatabaseManager()
    job_repo = JobDefinitionRepository(db)
    scheduler_repo = SchedulerJobRepository(db)
    return JobService(job_repo, scheduler_repo)


@jobs_bp.errorhandler(AppError)
def handle_app_error(error):
    """Handle application errors."""
    return jsonify(error_response(error.code, error.message, error.details)), error.status_code


@jobs_bp.errorhandler(Exception)
def handle_generic_error(error):
    """Handle unexpected errors."""
    return jsonify(error_response('INTERNAL_ERROR', str(error))), 500


@jobs_bp.route('', methods=['GET'])
def list_jobs():
    """
    List all job definitions.
    
    Query params:
        enabled: Filter by enabled status ('true' or 'false')
        search: Search term
    
    Returns:
        List of job definitions
    """
    service = get_job_service()
    
    enabled_param = request.args.get('enabled')
    enabled = None
    if enabled_param is not None:
        enabled = enabled_param.lower() == 'true'
    
    search = request.args.get('search')
    
    if search:
        jobs = service.search_jobs(search)
    else:
        jobs = service.list_jobs(enabled=enabled)
    
    return jsonify(list_response(jobs))


@jobs_bp.route('/<job_id>', methods=['GET'])
def get_job(job_id):
    """
    Get a single job definition by ID.
    
    Args:
        job_id: Job definition UUID
    
    Returns:
        Job definition
    """
    service = get_job_service()
    job = service.get_job(job_id)
    
    return jsonify(success_response(job))


@jobs_bp.route('', methods=['POST'])
def create_job():
    """
    Create a new job definition.
    
    Body:
        id: Job definition UUID (required)
        name: Job name (required)
        description: Job description
        definition: Job definition JSON (required)
        enabled: Whether job is enabled (default: true)
    
    Returns:
        Created job definition
    """
    service = get_job_service()
    data = request.get_json() or {}
    
    required_fields = ['id', 'name', 'definition']
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise ValidationError(f'Missing required fields: {", ".join(missing)}')
    
    job = service.create_job(
        job_id=data['id'],
        name=data['name'],
        description=data.get('description', ''),
        definition=data['definition'],
        enabled=data.get('enabled', True)
    )
    
    return jsonify(success_response(job, message='Job definition created')), 201


@jobs_bp.route('/<job_id>', methods=['PUT'])
def update_job(job_id):
    """
    Update a job definition.
    
    Args:
        job_id: Job definition UUID
    
    Body:
        name: New job name
        description: New description
        definition: New definition
        enabled: New enabled status
    
    Returns:
        Updated job definition
    """
    service = get_job_service()
    data = request.get_json() or {}
    
    job = service.update_job(
        job_id=job_id,
        name=data.get('name'),
        description=data.get('description'),
        definition=data.get('definition'),
        enabled=data.get('enabled')
    )
    
    return jsonify(success_response(job, message='Job definition updated'))


@jobs_bp.route('/<job_id>', methods=['DELETE'])
def delete_job(job_id):
    """
    Delete a job definition.
    
    Args:
        job_id: Job definition UUID
    
    Returns:
        Success message
    """
    service = get_job_service()
    service.delete_job(job_id)
    
    return jsonify(success_response(message='Job definition deleted'))


@jobs_bp.route('/<job_id>/enable', methods=['POST'])
def enable_job(job_id):
    """
    Enable a job definition.
    
    Args:
        job_id: Job definition UUID
    
    Returns:
        Updated job definition
    """
    service = get_job_service()
    job = service.set_enabled(job_id, True)
    
    return jsonify(success_response(job, message='Job definition enabled'))


@jobs_bp.route('/<job_id>/disable', methods=['POST'])
def disable_job(job_id):
    """
    Disable a job definition.
    
    Args:
        job_id: Job definition UUID
    
    Returns:
        Updated job definition
    """
    service = get_job_service()
    job = service.set_enabled(job_id, False)
    
    return jsonify(success_response(job, message='Job definition disabled'))
