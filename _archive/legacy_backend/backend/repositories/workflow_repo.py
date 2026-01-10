"""
Workflow repository for workflows table operations.

Handles all database operations related to visual workflow definitions.
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import BaseRepository
from ..utils.serialization import serialize_datetime


class WorkflowRepository(BaseRepository):
    """Repository for workflows operations."""
    
    table_name = 'workflows'
    primary_key = 'id'
    resource_name = 'Workflow'
    
    def get_by_id(self, id: str, serialize: bool = True) -> Optional[Dict]:
        """
        Get a workflow by ID.
        
        Args:
            id: Workflow UUID
            serialize: Whether to serialize the result
        
        Returns:
            Workflow record or None
        """
        query = """
            SELECT w.*, 
                   COALESCE(
                       (SELECT json_agg(t.*)
                        FROM job_tags t
                        JOIN workflow_tags wt ON wt.tag_id = t.id
                        WHERE wt.workflow_id = w.id),
                       '[]'::json
                   ) as tags
            FROM workflows w
            WHERE w.id = %s
        """
        results = self.execute_query(query, (id,))
        
        if not results:
            return None
        
        row = results[0]
        if serialize:
            return self._serialize_workflow(row)
        return row
    
    def get_all(
        self,
        folder_id: Optional[str] = None,
        tag_ids: Optional[List[str]] = None,
        search: Optional[str] = None,
        enabled: Optional[bool] = None,
        include_templates: bool = False
    ) -> List[Dict]:
        """
        Get all workflows with optional filters.
        
        Args:
            folder_id: Filter by folder (None = root level)
            tag_ids: Filter by tags (any match)
            search: Search term for name/description
            enabled: Filter by enabled status
            include_templates: Include template workflows
        
        Returns:
            List of workflows
        """
        conditions = []
        params = []
        
        if folder_id is not None:
            if folder_id == 'root':
                conditions.append("w.folder_id IS NULL")
            else:
                conditions.append("w.folder_id = %s")
                params.append(folder_id)
        
        if tag_ids:
            conditions.append("""
                EXISTS (
                    SELECT 1 FROM workflow_tags wt 
                    WHERE wt.workflow_id = w.id AND wt.tag_id = ANY(%s)
                )
            """)
            params.append(tag_ids)
        
        if search:
            conditions.append("(w.name ILIKE %s OR w.description ILIKE %s)")
            search_pattern = f'%{search}%'
            params.extend([search_pattern, search_pattern])
        
        if enabled is not None:
            conditions.append("w.enabled = %s")
            params.append(enabled)
        
        if not include_templates:
            conditions.append("w.is_template = FALSE")
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        query = f"""
            SELECT w.*, 
                   COALESCE(
                       (SELECT json_agg(json_build_object('id', t.id, 'name', t.name, 'color', t.color))
                        FROM job_tags t
                        JOIN workflow_tags wt ON wt.tag_id = t.id
                        WHERE wt.workflow_id = w.id),
                       '[]'::json
                   ) as tags,
                   f.name as folder_name
            FROM workflows w
            LEFT JOIN job_folders f ON f.id = w.folder_id
            WHERE {where_clause}
            ORDER BY w.name
        """
        
        results = self.execute_query(query, tuple(params) if params else None)
        return [self._serialize_workflow(row) for row in results]
    
    def create(
        self,
        name: str,
        description: str = '',
        definition: Dict = None,
        settings: Dict = None,
        schedule: Dict = None,
        folder_id: str = None,
        enabled: bool = True
    ) -> Optional[Dict]:
        """
        Create a new workflow.
        
        Args:
            name: Workflow name
            description: Workflow description
            definition: Workflow definition (nodes, edges, viewport)
            settings: Workflow settings
            schedule: Schedule configuration
            folder_id: Parent folder ID
            enabled: Whether workflow is enabled
        
        Returns:
            Created workflow
        """
        query = """
            INSERT INTO workflows (name, description, definition, settings, schedule, folder_id, enabled)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        
        definition_json = json.dumps(definition or {})
        settings_json = json.dumps(settings or {
            'error_handling': 'continue',
            'timeout': 300,
            'notifications': {'on_success': False, 'on_failure': True}
        })
        schedule_json = json.dumps(schedule) if schedule else None
        
        results = self.execute_query(query, (
            name, description, definition_json, settings_json, 
            schedule_json, folder_id, enabled
        ))
        
        if results:
            return self._serialize_workflow(results[0])
        return None
    
    def update(
        self,
        id: str,
        name: str = None,
        description: str = None,
        definition: Dict = None,
        settings: Dict = None,
        schedule: Dict = None,
        folder_id: str = None,
        enabled: bool = None
    ) -> Optional[Dict]:
        """
        Update a workflow.
        
        Args:
            id: Workflow ID
            name: New name
            description: New description
            definition: New definition
            settings: New settings
            schedule: New schedule
            folder_id: New folder ID
            enabled: New enabled status
        
        Returns:
            Updated workflow
        """
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = %s")
            params.append(name)
        
        if description is not None:
            updates.append("description = %s")
            params.append(description)
        
        if definition is not None:
            updates.append("definition = %s")
            params.append(json.dumps(definition))
            updates.append("version = version + 1")
        
        if settings is not None:
            updates.append("settings = %s")
            params.append(json.dumps(settings))
        
        if schedule is not None:
            updates.append("schedule = %s")
            params.append(json.dumps(schedule) if schedule else None)
        
        if folder_id is not None:
            updates.append("folder_id = %s")
            params.append(folder_id if folder_id != 'null' else None)
        
        if enabled is not None:
            updates.append("enabled = %s")
            params.append(enabled)
        
        if not updates:
            return self.get_by_id(id)
        
        updates.append("updated_at = NOW()")
        params.append(id)
        
        query = f"""
            UPDATE workflows 
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING *
        """
        
        results = self.execute_query(query, tuple(params))
        
        if results:
            return self._serialize_workflow(results[0])
        return None
    
    def delete(self, id: str) -> bool:
        """
        Delete a workflow.
        
        Args:
            id: Workflow ID
        
        Returns:
            True if deleted
        """
        query = "DELETE FROM workflows WHERE id = %s RETURNING id"
        results = self.execute_query(query, (id,))
        return len(results) > 0 if results else False
    
    def duplicate(self, id: str, new_name: str) -> Optional[Dict]:
        """
        Duplicate a workflow.
        
        Args:
            id: Source workflow ID
            new_name: Name for the duplicate
        
        Returns:
            Duplicated workflow
        """
        source = self.get_by_id(id, serialize=False)
        if not source:
            return None
        
        query = """
            INSERT INTO workflows (name, description, definition, settings, schedule, folder_id, enabled)
            SELECT %s, description, definition, settings, schedule, folder_id, enabled
            FROM workflows WHERE id = %s
            RETURNING *
        """
        
        results = self.execute_query(query, (new_name, id))
        
        if results:
            return self._serialize_workflow(results[0])
        return None
    
    def update_tags(self, id: str, tag_ids: List[str]) -> Optional[Dict]:
        """
        Update workflow tags.
        
        Args:
            id: Workflow ID
            tag_ids: List of tag IDs
        
        Returns:
            Updated workflow
        """
        # Remove existing tags
        self.execute_query(
            "DELETE FROM workflow_tags WHERE workflow_id = %s",
            (id,),
            fetch=False
        )
        
        # Add new tags
        if tag_ids:
            values = [(id, tag_id) for tag_id in tag_ids]
            query = "INSERT INTO workflow_tags (workflow_id, tag_id) VALUES (%s, %s)"
            for workflow_id, tag_id in values:
                self.execute_query(query, (workflow_id, tag_id), fetch=False)
        
        return self.get_by_id(id)
    
    def move_to_folder(self, id: str, folder_id: Optional[str]) -> Optional[Dict]:
        """
        Move workflow to a folder.
        
        Args:
            id: Workflow ID
            folder_id: Target folder ID (None for root)
        
        Returns:
            Updated workflow
        """
        return self.update(id, folder_id=folder_id if folder_id else 'null')
    
    def record_execution(self, id: str) -> None:
        """Update last_run_at timestamp."""
        self.execute_query(
            "UPDATE workflows SET last_run_at = NOW() WHERE id = %s",
            (id,),
            fetch=False
        )
    
    def _serialize_workflow(self, row: Any) -> Dict:
        """
        Serialize a workflow row.
        
        Args:
            row: Database row
        
        Returns:
            Serialized dictionary
        """
        definition = row.get('definition', {})
        if isinstance(definition, str):
            try:
                definition = json.loads(definition)
            except json.JSONDecodeError:
                definition = {}
        
        settings = row.get('settings', {})
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except json.JSONDecodeError:
                settings = {}
        
        schedule = row.get('schedule')
        if isinstance(schedule, str):
            try:
                schedule = json.loads(schedule)
            except json.JSONDecodeError:
                schedule = None
        
        tags = row.get('tags', [])
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except json.JSONDecodeError:
                tags = []
        
        return {
            'id': str(row['id']),
            'name': row['name'],
            'description': row.get('description', ''),
            'folder_id': str(row['folder_id']) if row.get('folder_id') else None,
            'folder_name': row.get('folder_name'),
            'definition': definition,
            'settings': settings,
            'schedule': schedule,
            'version': row.get('version', 1),
            'enabled': row.get('enabled', True),
            'is_template': row.get('is_template', False),
            'tags': tags if tags else [],
            'created_at': serialize_datetime(row.get('created_at')),
            'updated_at': serialize_datetime(row.get('updated_at')),
            'last_run_at': serialize_datetime(row.get('last_run_at')),
        }


class FolderRepository(BaseRepository):
    """Repository for job_folders operations."""
    
    table_name = 'job_folders'
    primary_key = 'id'
    resource_name = 'Folder'
    
    def get_all(self) -> List[Dict]:
        """Get all folders with hierarchy info."""
        query = """
            SELECT f.*,
                   (SELECT COUNT(*) FROM workflows w WHERE w.folder_id = f.id) as workflow_count
            FROM job_folders f
            ORDER BY f.sort_order, f.name
        """
        results = self.execute_query(query)
        return [self._serialize_folder(row) for row in results]
    
    def get_by_id(self, id: str) -> Optional[Dict]:
        """Get a folder by ID."""
        query = """
            SELECT f.*,
                   (SELECT COUNT(*) FROM workflows w WHERE w.folder_id = f.id) as workflow_count
            FROM job_folders f
            WHERE f.id = %s
        """
        results = self.execute_query(query, (id,))
        if results:
            return self._serialize_folder(results[0])
        return None
    
    def create(self, name: str, parent_id: str = None, color: str = '#6B7280', icon: str = 'folder') -> Optional[Dict]:
        """Create a new folder."""
        query = """
            INSERT INTO job_folders (name, parent_id, color, icon)
            VALUES (%s, %s, %s, %s)
            RETURNING *
        """
        results = self.execute_query(query, (name, parent_id, color, icon))
        if results:
            return self._serialize_folder(results[0])
        return None
    
    def update(self, id: str, name: str = None, parent_id: str = None, color: str = None, icon: str = None) -> Optional[Dict]:
        """Update a folder."""
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = %s")
            params.append(name)
        if parent_id is not None:
            updates.append("parent_id = %s")
            params.append(parent_id if parent_id != 'null' else None)
        if color is not None:
            updates.append("color = %s")
            params.append(color)
        if icon is not None:
            updates.append("icon = %s")
            params.append(icon)
        
        if not updates:
            return self.get_by_id(id)
        
        updates.append("updated_at = NOW()")
        params.append(id)
        
        query = f"UPDATE job_folders SET {', '.join(updates)} WHERE id = %s RETURNING *"
        results = self.execute_query(query, tuple(params))
        
        if results:
            return self._serialize_folder(results[0])
        return None
    
    def delete(self, id: str) -> bool:
        """Delete a folder (cascades to subfolders)."""
        query = "DELETE FROM job_folders WHERE id = %s RETURNING id"
        results = self.execute_query(query, (id,))
        return len(results) > 0 if results else False
    
    def _serialize_folder(self, row: Any) -> Dict:
        """Serialize a folder row."""
        return {
            'id': str(row['id']),
            'name': row['name'],
            'parent_id': str(row['parent_id']) if row.get('parent_id') else None,
            'color': row.get('color', '#6B7280'),
            'icon': row.get('icon', 'folder'),
            'sort_order': row.get('sort_order', 0),
            'workflow_count': row.get('workflow_count', 0),
            'created_at': serialize_datetime(row.get('created_at')),
            'updated_at': serialize_datetime(row.get('updated_at')),
        }


class TagRepository(BaseRepository):
    """Repository for job_tags operations."""
    
    table_name = 'job_tags'
    primary_key = 'id'
    resource_name = 'Tag'
    
    def get_all(self) -> List[Dict]:
        """Get all tags with usage count."""
        query = """
            SELECT t.*,
                   (SELECT COUNT(*) FROM workflow_tags wt WHERE wt.tag_id = t.id) as usage_count
            FROM job_tags t
            ORDER BY t.name
        """
        results = self.execute_query(query)
        return [self._serialize_tag(row) for row in results]
    
    def get_by_id(self, id: str) -> Optional[Dict]:
        """Get a tag by ID."""
        query = "SELECT * FROM job_tags WHERE id = %s"
        results = self.execute_query(query, (id,))
        if results:
            return self._serialize_tag(results[0])
        return None
    
    def create(self, name: str, color: str = '#6B7280') -> Optional[Dict]:
        """Create a new tag."""
        query = "INSERT INTO job_tags (name, color) VALUES (%s, %s) RETURNING *"
        results = self.execute_query(query, (name, color))
        if results:
            return self._serialize_tag(results[0])
        return None
    
    def update(self, id: str, name: str = None, color: str = None) -> Optional[Dict]:
        """Update a tag."""
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = %s")
            params.append(name)
        if color is not None:
            updates.append("color = %s")
            params.append(color)
        
        if not updates:
            return self.get_by_id(id)
        
        params.append(id)
        query = f"UPDATE job_tags SET {', '.join(updates)} WHERE id = %s RETURNING *"
        results = self.execute_query(query, tuple(params))
        
        if results:
            return self._serialize_tag(results[0])
        return None
    
    def delete(self, id: str) -> bool:
        """Delete a tag."""
        query = "DELETE FROM job_tags WHERE id = %s RETURNING id"
        results = self.execute_query(query, (id,))
        return len(results) > 0 if results else False
    
    def _serialize_tag(self, row: Any) -> Dict:
        """Serialize a tag row."""
        return {
            'id': str(row['id']),
            'name': row['name'],
            'color': row.get('color', '#6B7280'),
            'usage_count': row.get('usage_count', 0),
            'created_at': serialize_datetime(row.get('created_at')),
        }


class PackageRepository(BaseRepository):
    """Repository for enabled_packages operations."""
    
    table_name = 'enabled_packages'
    primary_key = 'id'
    resource_name = 'Package'
    
    def get_all(self) -> List[Dict]:
        """Get all packages."""
        query = "SELECT * FROM enabled_packages ORDER BY package_id"
        results = self.execute_query(query)
        return [self._serialize_package(row) for row in results]
    
    def get_enabled(self) -> List[str]:
        """Get list of enabled package IDs."""
        query = "SELECT package_id FROM enabled_packages WHERE enabled = TRUE"
        results = self.execute_query(query)
        return [row['package_id'] for row in results]
    
    def set_enabled(self, package_id: str, enabled: bool) -> Optional[Dict]:
        """Enable or disable a package."""
        query = """
            UPDATE enabled_packages 
            SET enabled = %s, enabled_at = CASE WHEN %s THEN NOW() ELSE enabled_at END
            WHERE package_id = %s
            RETURNING *
        """
        results = self.execute_query(query, (enabled, enabled, package_id))
        if results:
            return self._serialize_package(results[0])
        return None
    
    def _serialize_package(self, row: Any) -> Dict:
        """Serialize a package row."""
        config = row.get('config', {})
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except json.JSONDecodeError:
                config = {}
        
        return {
            'id': str(row['id']),
            'package_id': row['package_id'],
            'enabled': row.get('enabled', True),
            'config': config,
            'enabled_at': serialize_datetime(row.get('enabled_at')),
        }
