"""
Job service for business logic related to job definitions.

Handles job definition CRUD and validation.
"""

from typing import Dict, List, Optional, Any
from .base import BaseService
from ..repositories.job_repo import JobDefinitionRepository
from ..repositories.scheduler_repo import SchedulerJobRepository
from ..utils.errors import NotFoundError, ValidationError
from ..utils.validation import validate_required, validate_uuid, validate_dict
from ..config.constants import (
    ACTION_TYPES, TARGETING_SOURCES, DB_OPERATIONS,
    SYSTEM_JOB_IDS
)


class JobService(BaseService):
    """Service for job definition business logic."""
    
    def __init__(
        self, 
        job_repo: JobDefinitionRepository, 
        scheduler_repo: SchedulerJobRepository = None
    ):
        """
        Initialize job service.
        
        Args:
            job_repo: Job definition repository
            scheduler_repo: Optional scheduler repository for schedule operations
        """
        super().__init__(job_repo)
        self.job_repo = job_repo
        self.scheduler_repo = scheduler_repo
    
    def get_job(self, job_id: str) -> Dict:
        """
        Get a job definition by ID.
        
        Args:
            job_id: Job definition UUID
        
        Returns:
            Job definition
        
        Raises:
            NotFoundError: If job not found
        """
        validate_uuid(job_id, 'job_id')
        job = self.job_repo.get_by_id(job_id)
        
        if not job:
            raise NotFoundError('Job Definition', job_id)
        
        return job
    
    def list_jobs(self, enabled: bool = None) -> List[Dict]:
        """
        List all job definitions.
        
        Args:
            enabled: Optional filter by enabled status
        
        Returns:
            List of job definitions
        """
        return self.job_repo.get_all_definitions(enabled=enabled)
    
    def create_job(
        self,
        job_id: str,
        name: str,
        description: str,
        definition: Dict,
        enabled: bool = True
    ) -> Dict:
        """
        Create a new job definition.
        
        Args:
            job_id: Job definition UUID
            name: Job name
            description: Job description
            definition: Job definition JSON
            enabled: Whether job is enabled
        
        Returns:
            Created job definition
        
        Raises:
            ValidationError: If definition is invalid
        """
        validate_uuid(job_id, 'job_id')
        validate_required(name, 'name')
        validate_dict(definition, 'definition')
        
        # Validate definition structure
        self._validate_definition(definition)
        
        return self.job_repo.upsert_definition(
            id=job_id,
            name=name,
            description=description or '',
            definition=definition,
            enabled=enabled
        )
    
    def update_job(
        self,
        job_id: str,
        name: str = None,
        description: str = None,
        definition: Dict = None,
        enabled: bool = None
    ) -> Dict:
        """
        Update a job definition.
        
        Args:
            job_id: Job definition UUID
            name: New job name
            description: New description
            definition: New definition
            enabled: New enabled status
        
        Returns:
            Updated job definition
        
        Raises:
            NotFoundError: If job not found
            ValidationError: If definition is invalid
        """
        # Verify job exists
        existing = self.get_job(job_id)
        
        # Use existing values if not provided
        final_name = name if name is not None else existing['name']
        final_description = description if description is not None else existing['description']
        final_definition = definition if definition is not None else existing['definition']
        final_enabled = enabled if enabled is not None else existing['enabled']
        
        if definition is not None:
            self._validate_definition(definition)
        
        return self.job_repo.upsert_definition(
            id=job_id,
            name=final_name,
            description=final_description,
            definition=final_definition,
            enabled=final_enabled
        )
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job definition.
        
        Args:
            job_id: Job definition UUID
        
        Returns:
            True if deleted
        
        Raises:
            NotFoundError: If job not found
            ValidationError: If trying to delete system job
        """
        validate_uuid(job_id, 'job_id')
        
        # Prevent deletion of system jobs
        if job_id in SYSTEM_JOB_IDS:
            raise ValidationError(
                'Cannot delete system job definitions',
                details={'job_id': job_id}
            )
        
        # Verify job exists
        self.get_job(job_id)
        
        return self.job_repo.delete_definition(job_id)
    
    def set_enabled(self, job_id: str, enabled: bool) -> Dict:
        """
        Enable or disable a job definition.
        
        Args:
            job_id: Job definition UUID
            enabled: New enabled status
        
        Returns:
            Updated job definition
        """
        # Verify job exists
        self.get_job(job_id)
        
        return self.job_repo.update_enabled(job_id, enabled)
    
    def search_jobs(self, search_term: str) -> List[Dict]:
        """
        Search job definitions by name or description.
        
        Args:
            search_term: Search string
        
        Returns:
            List of matching jobs
        """
        return self.job_repo.search_definitions(search_term)
    
    def _validate_definition(self, definition: Dict) -> None:
        """
        Validate job definition structure.
        
        Args:
            definition: Job definition to validate
        
        Raises:
            ValidationError: If definition is invalid
        """
        # Check for required top-level fields
        if 'actions' not in definition:
            raise ValidationError(
                'Job definition must have "actions" field',
                field='definition.actions'
            )
        
        actions = definition['actions']
        if not isinstance(actions, list) or len(actions) == 0:
            raise ValidationError(
                'Job definition must have at least one action',
                field='definition.actions'
            )
        
        # Validate each action
        for i, action in enumerate(actions):
            self._validate_action(action, i)
    
    def _validate_action(self, action: Dict, index: int) -> None:
        """
        Validate a single action in a job definition.
        
        Args:
            action: Action to validate
            index: Action index for error messages
        
        Raises:
            ValidationError: If action is invalid
        """
        prefix = f'definition.actions[{index}]'
        
        # Check action type
        action_type = action.get('type')
        if not action_type:
            raise ValidationError(
                f'Action must have a "type" field',
                field=f'{prefix}.type'
            )
        
        if action_type not in ACTION_TYPES:
            raise ValidationError(
                f'Invalid action type: {action_type}',
                field=f'{prefix}.type',
                details={'allowed_types': ACTION_TYPES}
            )
        
        # Check targeting
        targeting = action.get('targeting', {})
        if targeting:
            source = targeting.get('source')
            if source and source not in TARGETING_SOURCES:
                raise ValidationError(
                    f'Invalid targeting source: {source}',
                    field=f'{prefix}.targeting.source',
                    details={'allowed_sources': TARGETING_SOURCES}
                )
        
        # Check database operations
        database = action.get('database', {})
        if database:
            tables = database.get('tables', [])
            for j, table in enumerate(tables):
                operation = table.get('operation')
                if operation and operation not in DB_OPERATIONS:
                    raise ValidationError(
                        f'Invalid database operation: {operation}',
                        field=f'{prefix}.database.tables[{j}].operation',
                        details={'allowed_operations': DB_OPERATIONS}
                    )
    
    def is_system_job(self, job_id: str) -> bool:
        """
        Check if a job is a system job.
        
        Args:
            job_id: Job definition UUID
        
        Returns:
            True if system job
        """
        return job_id in SYSTEM_JOB_IDS
