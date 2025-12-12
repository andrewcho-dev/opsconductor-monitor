"""
Celery tasks for job execution.

Thin wrappers that delegate to services.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def get_celery():
    """Get Celery app instance."""
    try:
        from celery_app import celery
        return celery
    except ImportError:
        return None


def run_job(job_config):
    """
    Run a job from its configuration.
    
    Args:
        job_config: Job configuration dictionary
    
    Returns:
        Execution result
    """
    from database import DatabaseManager
    from ..services.job_executor import JobExecutor
    from ..repositories.execution_repo import ExecutionRepository
    
    db = DatabaseManager()
    
    # Get task_id from Celery if available
    task_id = None
    execution_id = None
    try:
        from celery import current_task
        if current_task:
            task_id = current_task.request.id
    except:
        pass
    
    # Get job definition if job_definition_id provided
    job_definition = job_config
    
    if 'job_definition_id' in job_config:
        from ..repositories.job_repo import JobDefinitionRepository
        job_repo = JobDefinitionRepository(db)
        job_def = job_repo.get_by_id(job_config['job_definition_id'])
        if job_def:
            job_definition = {
                **job_def.get('definition', {}),
                'id': job_def['id'],
                'name': job_def['name'],
                'job_definition_id': job_config['job_definition_id'],
                'config': {**job_config, **job_def.get('definition', {}).get('config', {})},
            }
    
    # Create executor with audit logging context
    executor = JobExecutor(db, task_id=task_id, execution_id=execution_id)
    
    # Execute the job
    result = executor.execute_job(job_definition)
    
    return result


def run_scheduled_job(job_name, task_id=None):
    """
    Run a scheduled job by name.
    
    Args:
        job_name: Scheduler job name
        task_id: Optional Celery task ID
    
    Returns:
        Execution result
    """
    from database import DatabaseManager
    from ..repositories.scheduler_repo import SchedulerJobRepository
    from ..repositories.execution_repo import ExecutionRepository
    from ..services.job_executor import JobExecutor
    
    db = DatabaseManager()
    scheduler_repo = SchedulerJobRepository(db)
    execution_repo = ExecutionRepository(db)
    
    # Get scheduler job
    job = scheduler_repo.get_by_name(job_name)
    if not job:
        return {'error': f'Job not found: {job_name}'}
    
    # Create execution record and get its ID for audit logging
    execution_id = None
    if task_id:
        execution = execution_repo.create_execution(
            job_name=job_name,
            task_name=job.get('task_name', 'opsconductor.job.run'),
            task_id=task_id,
            status='running',
            config=job.get('config'),
        )
        if execution:
            execution_id = execution.get('id')
    
    try:
        # Get job definition if available
        job_config = job.get('config', {})
        job_definition = job_config
        
        if 'job_definition_id' in job_config:
            from ..repositories.job_repo import JobDefinitionRepository
            job_repo = JobDefinitionRepository(db)
            job_def = job_repo.get_by_id(job_config['job_definition_id'])
            if job_def:
                job_definition = {
                    **job_def.get('definition', {}),
                    'id': job_def['id'],
                    'name': job_def['name'],
                    'job_definition_id': job_config['job_definition_id'],
                    'config': {**job_config, **job_def.get('definition', {}).get('config', {})},
                }
        
        # Create executor with audit logging context
        executor = JobExecutor(db, task_id=task_id, execution_id=execution_id)
        
        # Execute the job
        result = executor.execute_job(job_definition)
        
        # Update execution record
        if task_id:
            execution_repo.update_execution(
                task_id=task_id,
                status='success' if not result.get('errors') else 'failed',
                finished_at=datetime.utcnow(),
                result=result,
            )
        
        return result
        
    except Exception as e:
        logger.exception(f"Job {job_name} failed")
        
        if task_id:
            execution_repo.update_execution(
                task_id=task_id,
                status='failed',
                finished_at=datetime.utcnow(),
                error_message=str(e),
            )
        
        return {'error': str(e)}


# Register Celery tasks if Celery is available
celery = get_celery()

if celery:
    @celery.task(name='opsconductor.job.run')
    def celery_run_job(job_config):
        """Celery task wrapper for run_job."""
        return run_job(job_config)
    
    @celery.task(name='opsconductor.job.scheduled')
    def celery_run_scheduled_job(job_name):
        """Celery task wrapper for run_scheduled_job."""
        from celery import current_task
        task_id = current_task.request.id if current_task else None
        return run_scheduled_job(job_name, task_id)
