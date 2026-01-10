"""
Audit repository for job_audit_events table operations.

Tracks every event in job execution with links to affected database records.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import BaseRepository
import json


class JobAuditRepository(BaseRepository):
    """Repository for job audit event operations."""
    
    table_name = 'job_audit_events'
    primary_key = 'id'
    resource_name = 'Job Audit Event'
    
    def log_event(
        self,
        event_type: str,
        execution_id: int = None,
        task_id: str = None,
        action_name: str = None,
        action_index: int = None,
        target_ip: str = None,
        table_name: str = None,
        record_id: int = None,
        record_ids: List[int] = None,
        operation_type: str = None,
        old_values: Dict = None,
        new_values: Dict = None,
        success: bool = True,
        error_message: str = None,
        details: Dict = None
    ) -> Optional[Dict]:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (job_started, action_started, db_insert, etc.)
            execution_id: Scheduler execution ID
            task_id: Celery task ID
            action_name: Name of the action
            action_index: Position in action list
            target_ip: Target device IP
            table_name: Database table affected
            record_id: Primary key of affected record
            record_ids: List of record IDs for bulk operations
            operation_type: insert, update, delete, upsert
            old_values: Previous values (for updates/deletes)
            new_values: New values (for inserts/updates)
            success: Whether operation succeeded
            error_message: Error message if failed
            details: Additional context
        
        Returns:
            Created audit event record
        """
        data = {
            'event_type': event_type,
            'event_timestamp': datetime.utcnow(),
            'success': success,
        }
        
        if execution_id is not None:
            data['execution_id'] = execution_id
        if task_id:
            data['task_id'] = task_id
        if action_name:
            data['action_name'] = action_name
        if action_index is not None:
            data['action_index'] = action_index
        if target_ip:
            data['target_ip'] = target_ip
        if table_name:
            data['table_name'] = table_name
        if record_id is not None:
            data['record_id'] = record_id
        if record_ids:
            data['record_ids'] = record_ids
        if operation_type:
            data['operation_type'] = operation_type
        if old_values:
            data['old_values'] = json.dumps(old_values)
        if new_values:
            data['new_values'] = json.dumps(new_values)
        if error_message:
            data['error_message'] = error_message
        if details:
            data['details'] = json.dumps(details)
        
        return self.create(data)
    
    def log_job_started(
        self,
        execution_id: int = None,
        task_id: str = None,
        job_name: str = None,
        job_config: Dict = None
    ) -> Optional[Dict]:
        """Log job started event."""
        return self.log_event(
            event_type='job_started',
            execution_id=execution_id,
            task_id=task_id,
            details={'job_name': job_name, 'config': job_config}
        )
    
    def log_job_completed(
        self,
        execution_id: int = None,
        task_id: str = None,
        success: bool = True,
        error_message: str = None,
        summary: Dict = None
    ) -> Optional[Dict]:
        """Log job completed event."""
        return self.log_event(
            event_type='job_completed',
            execution_id=execution_id,
            task_id=task_id,
            success=success,
            error_message=error_message,
            details=summary
        )
    
    def log_action_started(
        self,
        execution_id: int = None,
        task_id: str = None,
        action_name: str = None,
        action_index: int = None,
        action_config: Dict = None
    ) -> Optional[Dict]:
        """Log action started event."""
        return self.log_event(
            event_type='action_started',
            execution_id=execution_id,
            task_id=task_id,
            action_name=action_name,
            action_index=action_index,
            details=action_config
        )
    
    def log_action_completed(
        self,
        execution_id: int = None,
        task_id: str = None,
        action_name: str = None,
        action_index: int = None,
        success: bool = True,
        error_message: str = None,
        summary: Dict = None
    ) -> Optional[Dict]:
        """Log action completed event."""
        return self.log_event(
            event_type='action_completed',
            execution_id=execution_id,
            task_id=task_id,
            action_name=action_name,
            action_index=action_index,
            success=success,
            error_message=error_message,
            details=summary
        )
    
    def log_db_operation(
        self,
        operation_type: str,
        table_name: str,
        record_id: int = None,
        record_ids: List[int] = None,
        old_values: Dict = None,
        new_values: Dict = None,
        execution_id: int = None,
        task_id: str = None,
        action_name: str = None,
        target_ip: str = None,
        success: bool = True,
        error_message: str = None
    ) -> Optional[Dict]:
        """
        Log a database operation (insert, update, delete).
        
        This is the key method for audit trail - it records exactly
        which records were affected and links to them.
        """
        event_type = f'db_{operation_type}'
        
        return self.log_event(
            event_type=event_type,
            execution_id=execution_id,
            task_id=task_id,
            action_name=action_name,
            target_ip=target_ip,
            table_name=table_name,
            record_id=record_id,
            record_ids=record_ids,
            operation_type=operation_type,
            old_values=old_values,
            new_values=new_values,
            success=success,
            error_message=error_message
        )
    
    def log_target_processed(
        self,
        target_ip: str,
        execution_id: int = None,
        task_id: str = None,
        action_name: str = None,
        success: bool = True,
        error_message: str = None,
        details: Dict = None
    ) -> Optional[Dict]:
        """Log when a target device is processed."""
        return self.log_event(
            event_type='target_processed',
            execution_id=execution_id,
            task_id=task_id,
            action_name=action_name,
            target_ip=target_ip,
            success=success,
            error_message=error_message,
            details=details
        )
    
    def get_execution_audit_trail(
        self,
        execution_id: int = None,
        task_id: str = None
    ) -> List[Dict]:
        """
        Get complete audit trail for an execution.
        
        Args:
            execution_id: Execution ID
            task_id: Or Celery task ID
        
        Returns:
            List of audit events in chronological order
        """
        if execution_id:
            return self.get_all(
                filters={'execution_id': execution_id},
                order_by='event_timestamp ASC'
            )
        elif task_id:
            return self.get_all(
                filters={'task_id': task_id},
                order_by='event_timestamp ASC'
            )
        return []
    
    def get_db_operations_for_execution(
        self,
        execution_id: int = None,
        task_id: str = None
    ) -> List[Dict]:
        """
        Get all database operations for an execution.
        
        Returns only db_insert, db_update, db_delete events with
        record references.
        """
        query = """
            SELECT * FROM job_audit_events
            WHERE event_type IN ('db_insert', 'db_update', 'db_delete', 'db_upsert')
              AND (execution_id = %s OR task_id = %s)
            ORDER BY event_timestamp ASC
        """
        results = self.execute_query(query, (execution_id, task_id))
        return self.serialize_rows(results) if results else []
    
    def get_records_affected_by_execution(
        self,
        execution_id: int = None,
        task_id: str = None,
        table_name: str = None
    ) -> Dict[str, List[int]]:
        """
        Get all record IDs affected by an execution, grouped by table.
        
        Returns:
            Dict mapping table names to lists of record IDs
        """
        table_filter = "AND table_name = %s" if table_name else ""
        params = [execution_id, task_id]
        if table_name:
            params.append(table_name)
        
        query = f"""
            SELECT table_name, 
                   array_agg(DISTINCT record_id) FILTER (WHERE record_id IS NOT NULL) as record_ids,
                   array_agg(DISTINCT unnest_ids) FILTER (WHERE unnest_ids IS NOT NULL) as bulk_ids
            FROM job_audit_events
            LEFT JOIN LATERAL unnest(record_ids) as unnest_ids ON true
            WHERE event_type IN ('db_insert', 'db_update', 'db_delete', 'db_upsert')
              AND (execution_id = %s OR task_id = %s)
              {table_filter}
            GROUP BY table_name
        """
        
        results = self.execute_query(query, tuple(params))
        
        affected = {}
        if results:
            for row in results:
                table = row['table_name']
                ids = set()
                if row.get('record_ids'):
                    ids.update(row['record_ids'])
                if row.get('bulk_ids'):
                    ids.update(row['bulk_ids'])
                affected[table] = sorted(list(ids))
        
        return affected
