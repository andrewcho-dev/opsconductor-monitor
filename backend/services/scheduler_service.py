"""
Scheduler service for business logic related to job scheduling.

Handles scheduler job management, execution tracking, and job triggering.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import BaseService
from ..repositories.scheduler_repo import SchedulerJobRepository
from ..repositories.execution_repo import ExecutionRepository
from ..repositories.job_repo import JobDefinitionRepository
from ..utils.errors import NotFoundError, ValidationError
from ..utils.validation import validate_required, validate_enum, validate_positive_int
from ..config.constants import (
    SCHEDULE_TYPES, JOB_STATUSES,
    JOB_STATUS_QUEUED, JOB_STATUS_RUNNING, JOB_STATUS_SUCCESS, JOB_STATUS_FAILED
)


class SchedulerService(BaseService):
    """Service for scheduler job business logic."""
    
    def __init__(
        self,
        scheduler_repo: SchedulerJobRepository,
        execution_repo: ExecutionRepository,
        job_repo: JobDefinitionRepository = None
    ):
        """
        Initialize scheduler service.
        
        Args:
            scheduler_repo: Scheduler job repository
            execution_repo: Execution history repository
            job_repo: Optional job definition repository
        """
        super().__init__(scheduler_repo)
        self.scheduler_repo = scheduler_repo
        self.execution_repo = execution_repo
        self.job_repo = job_repo
    
    def get_job(self, name: str) -> Dict:
        """
        Get a scheduler job by name.
        
        Args:
            name: Job name
        
        Returns:
            Scheduler job
        
        Raises:
            NotFoundError: If job not found
        """
        job = self.scheduler_repo.get_by_name(name)
        if not job:
            raise NotFoundError('Scheduler Job', name)
        return job
    
    def list_jobs(self, enabled: bool = None) -> List[Dict]:
        """
        List all scheduler jobs.
        
        Args:
            enabled: Optional filter by enabled status
        
        Returns:
            List of scheduler jobs
        """
        return self.scheduler_repo.get_all_jobs(enabled=enabled)
    
    def create_or_update_job(
        self,
        name: str,
        task_name: str,
        config: Dict = None,
        interval_seconds: int = None,
        cron_expression: str = None,
        enabled: bool = True,
        schedule_type: str = 'interval',
        job_definition_id: str = None
    ) -> Dict:
        """
        Create or update a scheduler job.
        
        Args:
            name: Unique job name
            task_name: Celery task name
            config: Job configuration
            interval_seconds: Interval for interval scheduling
            cron_expression: Cron expression for cron scheduling
            enabled: Whether job is enabled
            schedule_type: 'interval' or 'cron'
            job_definition_id: Optional linked job definition
        
        Returns:
            Created/updated job
        
        Raises:
            ValidationError: If parameters are invalid
        """
        validate_required(name, 'name')
        validate_required(task_name, 'task_name')
        validate_enum(schedule_type, SCHEDULE_TYPES, 'schedule_type')
        
        if schedule_type == 'interval' and not interval_seconds:
            raise ValidationError(
                'interval_seconds is required for interval schedule type',
                field='interval_seconds'
            )
        
        if schedule_type == 'cron' and not cron_expression:
            raise ValidationError(
                'cron_expression is required for cron schedule type',
                field='cron_expression'
            )
        
        return self.scheduler_repo.upsert_job(
            name=name,
            task_name=task_name,
            config=config or {},
            interval_seconds=interval_seconds,
            cron_expression=cron_expression,
            enabled=enabled,
            schedule_type=schedule_type,
            job_definition_id=job_definition_id
        )
    
    def delete_job(self, name: str) -> bool:
        """
        Delete a scheduler job.
        
        Args:
            name: Job name
        
        Returns:
            True if deleted
        
        Raises:
            NotFoundError: If job not found
        """
        # Verify job exists
        self.get_job(name)
        return self.scheduler_repo.delete_by_name(name)
    
    def set_enabled(self, name: str, enabled: bool) -> Dict:
        """
        Enable or disable a scheduler job.
        
        Args:
            name: Job name
            enabled: New enabled status
        
        Returns:
            Updated job
        """
        # Verify job exists
        self.get_job(name)
        return self.scheduler_repo.update_enabled(name, enabled)
    
    def get_job_with_executions(self, name: str, execution_limit: int = 10) -> Dict:
        """
        Get a scheduler job with recent executions.
        
        Args:
            name: Job name
            execution_limit: Maximum executions to include
        
        Returns:
            Job with 'recent_executions' field
        """
        job = self.get_job(name)
        job['recent_executions'] = self.execution_repo.get_executions_for_job(
            name, limit=execution_limit
        )
        return job
    
    def get_recent_executions(
        self,
        job_name: str = None,
        limit: int = 100,
        status: str = None,
        exclude_result: bool = True
    ) -> List[Dict]:
        """
        Get recent job executions.
        
        Args:
            job_name: Optional job name filter
            limit: Maximum results
            status: Optional status filter
            exclude_result: Exclude large result column for performance
        
        Returns:
            List of executions
        """
        if job_name:
            return self.execution_repo.get_executions_for_job(job_name, limit, status)
        return self.execution_repo.get_recent_executions(limit, status, exclude_result)
    
    def create_execution(
        self,
        job_name: str,
        task_name: str,
        task_id: str,
        config: Dict = None,
        worker: str = None
    ) -> Dict:
        """
        Create a new execution record.
        
        Args:
            job_name: Scheduler job name
            task_name: Celery task name
            task_id: Celery task ID
            config: Job configuration
            worker: Worker hostname
        
        Returns:
            Created execution record
        """
        return self.execution_repo.create_execution(
            job_name=job_name,
            task_name=task_name,
            task_id=task_id,
            status=JOB_STATUS_QUEUED,
            config=config,
            worker=worker
        )
    
    def update_execution(
        self,
        task_id: str,
        status: str,
        started_at: datetime = None,
        finished_at: datetime = None,
        result: Dict = None,
        error_message: str = None,
        worker: str = None
    ) -> bool:
        """
        Update an execution record.
        
        Args:
            task_id: Celery task ID
            status: New status
            started_at: When execution started
            finished_at: When execution finished
            result: Execution result
            error_message: Error message if failed
            worker: Worker hostname
        
        Returns:
            True if updated
        """
        validate_enum(status, JOB_STATUSES, 'status')
        
        return self.execution_repo.update_execution(
            task_id=task_id,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            result=result,
            error_message=error_message,
            worker=worker
        )
    
    def clear_executions(
        self,
        job_name: str = None,
        status: str = None,
        before: datetime = None
    ) -> int:
        """
        Clear execution history.
        
        Args:
            job_name: Optional job name filter
            status: Optional status filter
            before: Optional timestamp filter
        
        Returns:
            Number of deleted records
        """
        return self.execution_repo.clear_executions(job_name, status, before)
    
    def mark_stale_executions(self, timeout_seconds: int = 600) -> int:
        """
        Mark stale running/queued executions as timed out.
        
        Args:
            timeout_seconds: Timeout threshold
        
        Returns:
            Number of marked executions
        """
        return self.execution_repo.mark_stale_executions(timeout_seconds)
    
    def get_execution_stats(self, job_name: str = None, hours: int = 24) -> Dict:
        """
        Get execution statistics.
        
        Args:
            job_name: Optional job name filter
            hours: Time window in hours
        
        Returns:
            Statistics dictionary
        """
        return self.execution_repo.get_execution_stats(job_name, hours)
    
    def get_due_jobs(self) -> List[Dict]:
        """
        Get jobs that are due to run.
        
        Returns:
            List of due jobs
        """
        return self.scheduler_repo.get_due_jobs(datetime.utcnow())
    
    def mark_job_run(self, name: str, next_run_at: datetime) -> bool:
        """
        Mark a job as having run.
        
        Args:
            name: Job name
            next_run_at: Next scheduled run time
        
        Returns:
            True if updated
        """
        return self.scheduler_repo.mark_job_run(
            name=name,
            last_run_at=datetime.utcnow(),
            next_run_at=next_run_at
        )
