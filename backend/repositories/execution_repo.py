"""
Execution repository for scheduler_job_executions table operations.

Handles all database operations related to job execution history.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import BaseRepository


class ExecutionRepository(BaseRepository):
    """Repository for scheduler_job_executions operations."""
    
    table_name = 'scheduler_job_executions'
    primary_key = 'id'
    resource_name = 'Job Execution'
    
    def create_execution(
        self,
        job_name: str,
        task_name: str,
        task_id: str,
        status: str = 'queued',
        config: Dict = None,
        worker: str = None,
        triggered_by: Dict = None
    ) -> Optional[Dict]:
        """
        Create a new execution record.
        
        Args:
            job_name: Name of the scheduler job
            task_name: Celery task name
            task_id: Celery task ID
            status: Initial status (queued, running, success, failed)
            config: Job configuration
            worker: Worker hostname
            triggered_by: User info dict {user_id, username, display_name, is_enterprise}
        
        Returns:
            Created execution record
        """
        import json
        
        data = {
            'job_name': job_name,
            'task_name': task_name,
            'task_id': task_id,
            'status': status,
            'config': json.dumps(config) if config else '{}',
            'created_at': datetime.utcnow()
        }
        
        if worker:
            data['worker'] = worker
        
        if triggered_by:
            data['triggered_by'] = json.dumps(triggered_by)
        
        return self.create(data)
    
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
        Update an execution record by task ID.
        
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
        import json
        
        updates = ['status = %s']
        params = [status]
        
        if started_at:
            updates.append('started_at = %s')
            params.append(started_at)
        
        if finished_at:
            updates.append('finished_at = %s')
            params.append(finished_at)
        
        if result is not None:
            updates.append('result = %s')
            params.append(json.dumps(result))
        
        if error_message is not None:
            updates.append('error_message = %s')
            params.append(error_message)
        
        if worker:
            updates.append('worker = %s')
            params.append(worker)
        
        params.append(task_id)
        
        query = f"""
            UPDATE scheduler_job_executions
            SET {', '.join(updates)}
            WHERE task_id = %s
        """
        
        self.execute_query(query, tuple(params), fetch=False)
        return True
    
    def get_by_task_id(self, task_id: str) -> Optional[Dict]:
        """
        Get execution by Celery task ID.
        
        Args:
            task_id: Celery task ID
        
        Returns:
            Execution record or None
        """
        return self.find_one({'task_id': task_id})
    
    def get_by_id(self, execution_id: int) -> Optional[Dict]:
        """
        Get execution by ID.
        
        Args:
            execution_id: Execution ID
        
        Returns:
            Execution record or None
        """
        return self.find_one({'id': execution_id})
    
    def update_status(self, execution_id: int, status: str) -> bool:
        """
        Update execution status by ID.
        
        Args:
            execution_id: Execution ID
            status: New status
        
        Returns:
            True if updated
        """
        query = """
            UPDATE scheduler_job_executions
            SET status = %s, finished_at = NOW()
            WHERE id = %s
        """
        self.execute_query(query, (status, execution_id), fetch=False)
        return True
    
    def get_executions_for_job(
        self,
        job_name: str,
        limit: int = 100,
        status: str = None
    ) -> List[Dict]:
        """
        Get executions for a specific job.
        
        Args:
            job_name: Scheduler job name
            limit: Maximum results
            status: Optional status filter
        
        Returns:
            List of execution records
        """
        filters = {'job_name': job_name}
        if status:
            filters['status'] = status
        
        return self.get_all(
            filters=filters,
            order_by='created_at DESC',
            limit=limit
        )
    
    def get_recent_executions(
        self,
        limit: int = 100,
        status: str = None
    ) -> List[Dict]:
        """
        Get recent executions across all jobs.
        
        Args:
            limit: Maximum results
            status: Optional status filter
        
        Returns:
            List of execution records
        """
        filters = {}
        if status:
            filters['status'] = status
        
        return self.get_all(
            filters=filters if filters else None,
            order_by='created_at DESC',
            limit=limit
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
            before: Optional timestamp filter (delete older than)
        
        Returns:
            Number of deleted records
        """
        conditions = []
        params = []
        
        if job_name:
            conditions.append('job_name = %s')
            params.append(job_name)
        
        if status:
            conditions.append('status = %s')
            params.append(status)
        
        if before:
            conditions.append('created_at < %s')
            params.append(before)
        
        where_clause = ' AND '.join(conditions) if conditions else '1=1'
        
        query = f"DELETE FROM scheduler_job_executions WHERE {where_clause} RETURNING id"
        results = self.execute_query(query, tuple(params) if params else None)
        return len(results) if results else 0
    
    def update_progress(
        self,
        task_id: str,
        current_step: str = None,
        step_status: str = None,
        message: str = None,
        percent: int = None,
        step_data: Dict = None
    ) -> bool:
        """
        Update execution progress for real-time tracking.
        
        Args:
            task_id: Celery task ID
            current_step: Name of current step being executed
            step_status: Status of current step (started, completed, failed)
            message: Progress message
            percent: Overall completion percentage (0-100)
            step_data: Additional step data
        
        Returns:
            True if updated
        """
        import json
        from datetime import datetime
        
        # Get current progress
        execution = self.get_by_task_id(task_id)
        if not execution:
            return False
        
        progress = execution.get('progress') or {'steps': [], 'current_step': None, 'percent': 0}
        if isinstance(progress, str):
            progress = json.loads(progress)
        
        steps = progress.get('steps', [])
        
        if current_step and step_status:
            # Find existing step or create new one
            existing_step = next((s for s in steps if s['name'] == current_step), None)
            
            if step_status == 'started':
                if not existing_step:
                    steps.append({
                        'name': current_step,
                        'status': 'running',
                        'started_at': datetime.utcnow().isoformat(),
                        'message': message,
                        'data': step_data
                    })
                else:
                    existing_step['status'] = 'running'
                    existing_step['started_at'] = datetime.utcnow().isoformat()
                    if message:
                        existing_step['message'] = message
                progress['current_step'] = current_step
                
            elif step_status == 'completed':
                if existing_step:
                    existing_step['status'] = 'completed'
                    existing_step['finished_at'] = datetime.utcnow().isoformat()
                    if message:
                        existing_step['message'] = message
                    if step_data:
                        existing_step['data'] = step_data
                progress['current_step'] = None
                
            elif step_status == 'failed':
                if existing_step:
                    existing_step['status'] = 'failed'
                    existing_step['finished_at'] = datetime.utcnow().isoformat()
                    if message:
                        existing_step['message'] = message
                progress['current_step'] = None
        
        if message and not current_step:
            progress['message'] = message
        
        if percent is not None:
            progress['percent'] = min(100, max(0, percent))
        
        progress['steps'] = steps
        progress['updated_at'] = datetime.utcnow().isoformat()
        
        query = """
            UPDATE scheduler_job_executions
            SET progress = %s
            WHERE task_id = %s
        """
        self.execute_query(query, (json.dumps(progress), task_id), fetch=False)
        return True
    
    def get_live_progress(self, task_id: str) -> Optional[Dict]:
        """
        Get live progress for a running execution.
        
        Args:
            task_id: Celery task ID
        
        Returns:
            Progress data or None
        """
        import json
        
        execution = self.get_by_task_id(task_id)
        if not execution:
            return None
        
        progress = execution.get('progress')
        if isinstance(progress, str):
            progress = json.loads(progress)
        
        return {
            'task_id': task_id,
            'status': execution.get('status'),
            'job_name': execution.get('job_name'),
            'started_at': execution.get('started_at'),
            'progress': progress or {'steps': [], 'current_step': None, 'percent': 0}
        }
    
    def mark_stale_executions(self, timeout_seconds: int = 600) -> int:
        """
        Mark stale running/queued executions as timed out.
        
        Args:
            timeout_seconds: Timeout threshold in seconds
        
        Returns:
            Number of marked executions
        """
        query = """
            UPDATE scheduler_job_executions
            SET status = 'timeout',
                finished_at = NOW(),
                error_message = 'Execution timed out'
            WHERE status IN ('running', 'queued')
              AND created_at < NOW() - INTERVAL '%s seconds'
            RETURNING id
        """
        results = self.execute_query(query, (timeout_seconds,))
        return len(results) if results else 0
    
    def get_execution_stats(self, job_name: str = None, hours: int = 24) -> Dict:
        """
        Get execution statistics.
        
        Args:
            job_name: Optional job name filter
            hours: Time window in hours
        
        Returns:
            Statistics dictionary
        """
        job_filter = "AND job_name = %s" if job_name else ""
        params = (hours, job_name) if job_name else (hours,)
        
        query = f"""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'success') as success,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                COUNT(*) FILTER (WHERE status = 'timeout') as timeout,
                COUNT(*) FILTER (WHERE status = 'running') as running,
                COUNT(*) FILTER (WHERE status = 'queued') as queued,
                AVG(EXTRACT(EPOCH FROM (finished_at - started_at))) FILTER (WHERE finished_at IS NOT NULL AND started_at IS NOT NULL) as avg_duration
            FROM scheduler_job_executions
            WHERE created_at >= NOW() - INTERVAL '%s hours'
            {job_filter}
        """
        
        results = self.execute_query(query, params)
        
        if results:
            row = results[0]
            return {
                'total': row['total'] or 0,
                'success': row['success'] or 0,
                'failed': row['failed'] or 0,
                'timeout': row['timeout'] or 0,
                'running': row['running'] or 0,
                'queued': row['queued'] or 0,
                'avg_duration_seconds': float(row['avg_duration']) if row['avg_duration'] else None
            }
        
        return {
            'total': 0, 'success': 0, 'failed': 0, 
            'timeout': 0, 'running': 0, 'queued': 0,
            'avg_duration_seconds': None
        }
