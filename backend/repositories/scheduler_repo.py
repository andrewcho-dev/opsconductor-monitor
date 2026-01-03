"""
Scheduler repository for scheduler_jobs table operations.

Handles all database operations related to scheduled jobs.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import BaseRepository


class SchedulerJobRepository(BaseRepository):
    """Repository for scheduler_jobs operations."""
    
    table_name = 'scheduler_jobs'
    primary_key = 'name'
    resource_name = 'Scheduler Job'
    
    def get_by_name(self, name: str, serialize: bool = True) -> Optional[Dict]:
        """
        Get a scheduler job by name.
        
        Args:
            name: Job name
            serialize: Whether to serialize the result
        
        Returns:
            Job record or None
        """
        return self.get_by_id(name, serialize)
    
    def get_all_jobs(self, enabled: bool = None) -> List[Dict]:
        """
        Get all scheduler jobs with optional enabled filter.
        
        Args:
            enabled: Filter by enabled status (None = all)
        
        Returns:
            List of scheduler jobs
        """
        filters = {}
        if enabled is not None:
            filters['enabled'] = enabled
        
        return self.get_all(filters=filters, order_by='name')
    
    def get_enabled_jobs(self) -> List[Dict]:
        """Get all enabled scheduler jobs."""
        return self.get_all_jobs(enabled=True)
    
    def upsert_job(
        self,
        name: str,
        task_name: str,
        config: Dict = None,
        interval_seconds: int = None,
        cron_expression: str = None,
        enabled: bool = True,
        schedule_type: str = 'interval',
        start_at: datetime = None,
        end_at: datetime = None,
        max_runs: int = None,
        job_definition_id: str = None
    ) -> Optional[Dict]:
        """
        Insert or update a scheduler job.
        
        Args:
            name: Unique job name
            task_name: Celery task name
            config: Job configuration dictionary
            interval_seconds: Interval for interval-based scheduling
            cron_expression: Cron expression for cron-based scheduling
            enabled: Whether job is enabled
            schedule_type: 'interval' or 'cron'
            start_at: Optional start time
            end_at: Optional end time
            max_runs: Optional maximum number of runs
            job_definition_id: Optional linked job definition ID
        
        Returns:
            Upserted job record
        """
        import json
        
        data = {
            'name': name,
            'task_name': task_name,
            'config': json.dumps(config) if config else '{}',
            'enabled': enabled,
            'schedule_type': schedule_type,
            'updated_at': datetime.utcnow()
        }
        
        if interval_seconds is not None:
            data['interval_seconds'] = interval_seconds
        if cron_expression is not None:
            data['cron_expression'] = cron_expression
        if start_at is not None:
            data['start_at'] = start_at
        if end_at is not None:
            data['end_at'] = end_at
        if max_runs is not None:
            data['max_runs'] = max_runs
        if job_definition_id is not None:
            data['job_definition_id'] = job_definition_id
        
        return self.upsert(
            data=data,
            conflict_columns=['name'],
            update_columns=[k for k in data.keys() if k != 'name']
        )
    
    def update_enabled(self, name: str, enabled: bool) -> Optional[Dict]:
        """
        Update job enabled status.
        
        Args:
            name: Job name
            enabled: New enabled status
        
        Returns:
            Updated job record
        """
        return self.update(name, {'enabled': enabled, 'updated_at': datetime.utcnow()})
    
    def mark_job_run(self, name: str, last_run_at: datetime, next_run_at: datetime) -> bool:
        """
        Update job after a run.
        
        Args:
            name: Job name
            last_run_at: Time of last run
            next_run_at: Time of next scheduled run
        
        Returns:
            True if updated
        """
        query = """
            UPDATE scheduler_jobs 
            SET last_run_at = %s, 
                next_run_at = %s, 
                run_count = COALESCE(run_count, 0) + 1,
                updated_at = NOW()
            WHERE name = %s
        """
        self.execute_query(query, (last_run_at, next_run_at, name), fetch=False)
        return True
    
    def get_due_jobs(self, now: datetime) -> List[Dict]:
        """
        Get jobs that are due to run.
        
        Args:
            now: Current time
        
        Returns:
            List of due jobs
        """
        query = """
            SELECT * FROM scheduler_jobs
            WHERE enabled = true
              AND (next_run_at IS NULL OR next_run_at <= %s)
              AND (start_at IS NULL OR start_at <= %s)
              AND (end_at IS NULL OR end_at >= %s)
              AND (max_runs IS NULL OR run_count IS NULL OR run_count < max_runs)
            ORDER BY next_run_at NULLS FIRST
        """
        results = self.execute_query(query, (now, now, now))
        
        from backend.utils.serialization import serialize_rows
        return serialize_rows(results)
    
    def delete_by_name(self, name: str) -> bool:
        """
        Delete a scheduler job by name.
        
        Args:
            name: Job name
        
        Returns:
            True if deleted
        """
        return self.delete(name)
