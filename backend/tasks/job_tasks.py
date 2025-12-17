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
        from celery_app import celery_app
        return celery_app
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


def run_workflow(workflow_id, trigger_data=None):
    """
    Run a workflow by ID.
    
    Args:
        workflow_id: Workflow UUID
        trigger_data: Optional trigger data dict
    
    Returns:
        Execution result
    """
    # Import with fallback for different execution contexts
    import sys
    import os
    from datetime import datetime
    
    # Ensure project root is in path for Celery worker
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    from database import DatabaseManager
    from backend.services.workflow_engine import WorkflowEngine
    from backend.repositories.workflow_repo import WorkflowRepository
    from backend.repositories.execution_repo import ExecutionRepository
    
    db = DatabaseManager()
    workflow_repo = WorkflowRepository(db)
    execution_repo = ExecutionRepository(db)
    
    # Get workflow
    workflow = workflow_repo.get_by_id(workflow_id)
    if not workflow:
        return {'error': f'Workflow not found: {workflow_id}', 'status': 'failure'}
    
    # Get task_id and worker from Celery if available
    task_id = None
    worker = None
    try:
        from celery import current_task
        if current_task:
            task_id = current_task.request.id
            worker = current_task.request.hostname
    except:
        pass
    
    # Generate task_id if not running in Celery
    if not task_id:
        import uuid
        task_id = str(uuid.uuid4())
    
    workflow_name = workflow.get('name', f'workflow_{workflow_id}')
    
    # Extract triggered_by from trigger_data
    triggered_by = None
    if trigger_data:
        triggered_by = trigger_data.pop('_triggered_by', None)
        logger.info(f"Extracted triggered_by from trigger_data: {triggered_by}")
    else:
        logger.warning(f"trigger_data is empty or None: {trigger_data}")
    
    # Create execution record with user attribution
    execution_repo.create_execution(
        job_name=workflow_name,
        task_name='opsconductor.workflow.run',
        task_id=task_id,
        status='running',
        config={'workflow_id': workflow_id, 'trigger_data': trigger_data},
        worker=worker,
        triggered_by=triggered_by
    )
    
    # Update to running status with start time
    execution_repo.update_execution(
        task_id=task_id,
        status='running',
        started_at=datetime.utcnow(),
        worker=worker
    )
    
    logger.info(f"Starting workflow execution: {workflow_name} (ID: {workflow_id}, Task: {task_id})")
    
    try:
        # Execute the workflow
        engine = WorkflowEngine(db_manager=db)
        result = engine.execute(workflow, trigger_data or {})
        
        # Record execution in workflow table
        workflow_repo.record_execution(workflow_id)
        
        # Update execution record with success
        execution_repo.update_execution(
            task_id=task_id,
            status='success',
            finished_at=datetime.utcnow(),
            result=result
        )
        
        logger.info(f"Workflow execution complete: {workflow_name} - Status: {result.get('status')}")
        return result
        
    except Exception as e:
        logger.exception(f"Workflow execution failed: {workflow_name}")
        
        # Update execution record with failure
        execution_repo.update_execution(
            task_id=task_id,
            status='failed',
            finished_at=datetime.utcnow(),
            error_message=str(e)
        )
        
        return {
            'status': 'failure',
            'error_message': str(e),
            'workflow_id': workflow_id,
        }


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
    
    @celery.task(name='opsconductor.workflow.run', bind=True)
    def celery_run_workflow(self, workflow_id, trigger_data=None):
        """Celery task wrapper for run_workflow."""
        logger.info(f"Celery task {self.request.id} starting workflow {workflow_id}")
        return run_workflow(workflow_id, trigger_data)
    
    @celery.task(name='opsconductor.alerts.evaluate')
    def celery_evaluate_alerts():
        """
        Celery task to evaluate all alert rules.
        
        Should be scheduled to run periodically (e.g., every minute)
        via Celery Beat or called manually.
        """
        from ..services.alert_service import AlertEvaluator
        
        evaluator = AlertEvaluator()
        results = evaluator.evaluate_all_rules()
        
        logger.info(f"Alert evaluation complete: {results['evaluated']} rules, {results['alerts_created']} alerts created")
        return results
    
    @celery.task(name='opsconductor.discovery.scan_chunk', bind=True)
    def celery_scan_chunk(self, hosts, config):
        """
        Scan a chunk of hosts for autodiscovery.
        
        This task is called in parallel by the main autodiscovery executor
        to distribute work across multiple Celery workers.
        
        Args:
            hosts: List of IP addresses to scan
            config: Discovery configuration dict
        
        Returns:
            List of discovered device dicts
        """
        import sys
        import os
        
        # Ensure project root is in path
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from backend.executors.netbox_autodiscovery_executor import NetBoxAutodiscoveryExecutor
        
        logger.info(f"Celery task {self.request.id} scanning {len(hosts)} hosts")
        
        executor = NetBoxAutodiscoveryExecutor()
        discovered = executor._discover_hosts(hosts, config)
        
        logger.info(f"Celery task {self.request.id} completed: {len(discovered)} devices discovered")
        return discovered
