"""
Job definition repository for job_definitions table operations.

Handles all database operations related to job definitions.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import BaseRepository
from ..utils.serialization import serialize_datetime


class JobDefinitionRepository(BaseRepository):
    """Repository for job_definitions operations."""
    
    table_name = 'job_definitions'
    primary_key = 'id'
    resource_name = 'Job Definition'
    
    def get_by_id(self, id: str, serialize: bool = True) -> Optional[Dict]:
        """
        Get a job definition by ID.
        
        Args:
            id: Job definition UUID
            serialize: Whether to serialize the result
        
        Returns:
            Job definition record or None
        """
        query = "SELECT * FROM job_definitions WHERE id = %s"
        results = self.execute_query(query, (id,))
        
        if not results:
            return None
        
        row = results[0]
        if serialize:
            return self._serialize_job_definition(row)
        return row
    
    def get_all_definitions(self, enabled: bool = None) -> List[Dict]:
        """
        Get all job definitions.
        
        Args:
            enabled: Optional filter by enabled status
        
        Returns:
            List of job definitions
        """
        if enabled is not None:
            query = "SELECT * FROM job_definitions WHERE enabled = %s ORDER BY name"
            results = self.execute_query(query, (enabled,))
        else:
            query = "SELECT * FROM job_definitions ORDER BY name"
            results = self.execute_query(query)
        
        return [self._serialize_job_definition(row) for row in results]
    
    def get_enabled_definitions(self) -> List[Dict]:
        """Get all enabled job definitions."""
        return self.get_all_definitions(enabled=True)
    
    def upsert_definition(
        self,
        id: str,
        name: str,
        description: str,
        definition: Dict,
        enabled: bool = True
    ) -> Optional[Dict]:
        """
        Insert or update a job definition.
        
        Args:
            id: Job definition UUID
            name: Job name
            description: Job description
            definition: Job definition JSON
            enabled: Whether job is enabled
        
        Returns:
            Upserted job definition
        """
        import json
        
        query = """
            INSERT INTO job_definitions (id, name, description, definition, enabled, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                definition = EXCLUDED.definition,
                enabled = EXCLUDED.enabled,
                updated_at = NOW()
            RETURNING *
        """
        
        definition_json = json.dumps(definition) if isinstance(definition, dict) else definition
        results = self.execute_query(query, (id, name, description, definition_json, enabled))
        
        if results:
            return self._serialize_job_definition(results[0])
        return None
    
    def update_enabled(self, id: str, enabled: bool) -> Optional[Dict]:
        """
        Update job definition enabled status.
        
        Args:
            id: Job definition ID
            enabled: New enabled status
        
        Returns:
            Updated job definition
        """
        query = """
            UPDATE job_definitions 
            SET enabled = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING *
        """
        results = self.execute_query(query, (enabled, id))
        
        if results:
            return self._serialize_job_definition(results[0])
        return None
    
    def delete_definition(self, id: str) -> bool:
        """
        Delete a job definition.
        
        Args:
            id: Job definition ID
        
        Returns:
            True if deleted
        """
        return self.delete(id)
    
    def search_definitions(self, search_term: str) -> List[Dict]:
        """
        Search job definitions by name or description.
        
        Args:
            search_term: Search string
        
        Returns:
            List of matching job definitions
        """
        query = """
            SELECT * FROM job_definitions
            WHERE name ILIKE %s OR description ILIKE %s
            ORDER BY name
        """
        search_pattern = f'%{search_term}%'
        results = self.execute_query(query, (search_pattern, search_pattern))
        
        return [self._serialize_job_definition(row) for row in results]
    
    def _serialize_job_definition(self, row: Any) -> Dict:
        """
        Serialize a job definition row.
        
        Args:
            row: Database row
        
        Returns:
            Serialized dictionary
        """
        import json
        
        definition = row['definition']
        if isinstance(definition, str):
            try:
                definition = json.loads(definition)
            except json.JSONDecodeError:
                definition = {}
        
        return {
            'id': str(row['id']),
            'name': row['name'],
            'description': row['description'],
            'definition': definition,
            'enabled': row['enabled'],
            'created_at': serialize_datetime(row.get('created_at')),
            'updated_at': serialize_datetime(row.get('updated_at'))
        }
