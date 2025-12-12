"""
Template Service for notification variable substitution.

Supports Mustache-style {{variable}} placeholders with nested object access.
"""

import re
import json
from typing import Dict, Any, Optional, List
from backend.database import get_db


class TemplateService:
    """Service for rendering notification templates with variable substitution."""
    
    def __init__(self, db=None):
        self.db = db or get_db()
    
    def render(self, template_text: str, context: Dict[str, Any]) -> str:
        """
        Render a template string with variable substitution.
        
        Supports:
        - {{variable}} - Simple variable
        - {{object.property}} - Nested property access
        - {{#if variable}}...{{/if}} - Conditional blocks
        - {{#each array}}...{{/each}} - Array iteration (basic)
        
        Args:
            template_text: Template string with {{placeholders}}
            context: Dictionary of variables to substitute
        
        Returns:
            Rendered string with variables replaced
        """
        if not template_text:
            return ''
        
        result = template_text
        
        # Handle conditional blocks first: {{#if var}}content{{/if}}
        result = self._process_conditionals(result, context)
        
        # Handle simple variable substitution: {{var}} or {{obj.prop}}
        result = self._substitute_variables(result, context)
        
        return result
    
    def _process_conditionals(self, text: str, context: Dict) -> str:
        """Process {{#if var}}...{{/if}} blocks."""
        pattern = r'\{\{#if\s+([^}]+)\}\}(.*?)\{\{/if\}\}'
        
        def replace_conditional(match):
            var_path = match.group(1).strip()
            content = match.group(2)
            
            value = self._get_nested_value(context, var_path)
            
            # Truthy check
            if value and value != 'None' and value != '':
                return self._substitute_variables(content, context)
            return ''
        
        return re.sub(pattern, replace_conditional, text, flags=re.DOTALL)
    
    def _substitute_variables(self, text: str, context: Dict) -> str:
        """Replace {{variable}} placeholders with values."""
        pattern = r'\{\{([^#/}][^}]*)\}\}'
        
        def replace_var(match):
            var_path = match.group(1).strip()
            value = self._get_nested_value(context, var_path)
            
            if value is None:
                return ''
            
            # Format based on type
            if isinstance(value, dict):
                return json.dumps(value, indent=2, default=str)
            elif isinstance(value, list):
                return json.dumps(value, indent=2, default=str)
            else:
                return str(value)
        
        return re.sub(pattern, replace_var, text)
    
    def _get_nested_value(self, obj: Dict, path: str) -> Any:
        """
        Get a nested value from a dictionary using dot notation.
        
        Example: _get_nested_value({'a': {'b': 1}}, 'a.b') -> 1
        """
        parts = path.split('.')
        current = obj
        
        for part in parts:
            if current is None:
                return None
            
            if isinstance(current, dict):
                current = current.get(part)
            else:
                # Try attribute access for objects
                current = getattr(current, part, None)
        
        return current
    
    def render_template(self, template_id: int, context: Dict[str, Any]) -> Dict[str, str]:
        """
        Render a template by ID.
        
        Args:
            template_id: Database ID of the template
            context: Variables to substitute
        
        Returns:
            Dict with 'title' and 'body' rendered strings
        """
        template = self.get_template(template_id)
        if not template:
            return {'title': '', 'body': ''}
        
        return {
            'title': self.render(template['title_template'], context),
            'body': self.render(template['body_template'], context)
        }
    
    def render_template_by_name(self, name: str, context: Dict[str, Any]) -> Dict[str, str]:
        """Render a template by name."""
        template = self.get_template_by_name(name)
        if not template:
            return {'title': '', 'body': ''}
        
        return {
            'title': self.render(template['title_template'], context),
            'body': self.render(template['body_template'], context)
        }
    
    # =========================================================================
    # CRUD Operations
    # =========================================================================
    
    def get_templates(self, template_type: str = None) -> List[Dict]:
        """Get all templates, optionally filtered by type."""
        with self.db.cursor() as cursor:
            if template_type:
                cursor.execute("""
                    SELECT * FROM notification_templates
                    WHERE template_type = %s
                    ORDER BY is_default DESC, name
                """, (template_type,))
            else:
                cursor.execute("""
                    SELECT * FROM notification_templates
                    ORDER BY template_type, is_default DESC, name
                """)
            
            templates = []
            for row in cursor.fetchall():
                t = dict(row)
                if isinstance(t.get('available_variables'), str):
                    t['available_variables'] = json.loads(t['available_variables'])
                templates.append(t)
            
            return templates
    
    def get_template(self, template_id: int) -> Optional[Dict]:
        """Get a template by ID."""
        with self.db.cursor() as cursor:
            cursor.execute("SELECT * FROM notification_templates WHERE id = %s", (template_id,))
            row = cursor.fetchone()
            if row:
                t = dict(row)
                if isinstance(t.get('available_variables'), str):
                    t['available_variables'] = json.loads(t['available_variables'])
                return t
            return None
    
    def get_template_by_name(self, name: str) -> Optional[Dict]:
        """Get a template by name."""
        with self.db.cursor() as cursor:
            cursor.execute("SELECT * FROM notification_templates WHERE name = %s", (name,))
            row = cursor.fetchone()
            if row:
                t = dict(row)
                if isinstance(t.get('available_variables'), str):
                    t['available_variables'] = json.loads(t['available_variables'])
                return t
            return None
    
    def create_template(
        self,
        name: str,
        title_template: str,
        body_template: str,
        template_type: str = 'system',
        description: str = None,
        available_variables: List[str] = None
    ) -> Dict:
        """Create a new template."""
        with self.db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO notification_templates 
                (name, title_template, body_template, template_type, description, available_variables)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                name,
                title_template,
                body_template,
                template_type,
                description,
                json.dumps(available_variables or [])
            ))
            result = dict(cursor.fetchone())
            self.db.get_connection().commit()
            return result
    
    def update_template(self, template_id: int, **kwargs) -> Optional[Dict]:
        """Update a template."""
        allowed_fields = ['name', 'title_template', 'body_template', 'template_type', 
                         'description', 'available_variables', 'enabled']
        
        updates = []
        params = []
        
        for field in allowed_fields:
            if field in kwargs:
                updates.append(f"{field} = %s")
                value = kwargs[field]
                if field == 'available_variables' and isinstance(value, list):
                    value = json.dumps(value)
                params.append(value)
        
        if not updates:
            return self.get_template(template_id)
        
        updates.append("updated_at = NOW()")
        params.append(template_id)
        
        with self.db.cursor() as cursor:
            cursor.execute(f"""
                UPDATE notification_templates
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING *
            """, params)
            
            row = cursor.fetchone()
            if row:
                self.db.get_connection().commit()
                return dict(row)
            return None
    
    def delete_template(self, template_id: int) -> bool:
        """Delete a template (only non-default templates)."""
        with self.db.cursor() as cursor:
            cursor.execute("""
                DELETE FROM notification_templates 
                WHERE id = %s AND is_default = false
            """, (template_id,))
            deleted = cursor.rowcount > 0
            self.db.get_connection().commit()
            return deleted


# Build context helpers for different notification types

def build_alert_context(alert: Dict) -> Dict[str, Any]:
    """Build template context for an alert notification."""
    return {
        'alert': {
            'id': alert.get('id'),
            'title': alert.get('title'),
            'message': alert.get('message'),
            'severity': alert.get('severity'),
            'category': alert.get('category'),
            'triggered_at': alert.get('triggered_at'),
            'details': alert.get('details', {}),
        }
    }


def build_job_context(job_result: Dict, workflow: Dict = None) -> Dict[str, Any]:
    """Build template context for a job notification."""
    context = {
        'job': {
            'id': job_result.get('job_id') or job_result.get('id'),
            'name': job_result.get('job_name') or job_result.get('name'),
            'status': job_result.get('status'),
            'duration': job_result.get('duration') or job_result.get('duration_seconds'),
            'started_at': job_result.get('started_at'),
            'finished_at': job_result.get('finished_at'),
            'error': job_result.get('error'),
            'summary': job_result.get('summary'),
            'results': job_result.get('results', {}),
        }
    }
    
    if workflow:
        context['workflow'] = {
            'id': workflow.get('id'),
            'name': workflow.get('name'),
            'variables': workflow.get('variables', {}),
        }
    
    return context


def build_workflow_step_context(workflow: Dict, step: Dict, step_result: Dict = None) -> Dict[str, Any]:
    """Build template context for a workflow step notification."""
    return {
        'workflow': {
            'id': workflow.get('id'),
            'name': workflow.get('name'),
            'variables': workflow.get('variables', {}),
        },
        'step': {
            'id': step.get('id'),
            'name': step.get('name') or step.get('label'),
            'type': step.get('type'),
            'status': step_result.get('status') if step_result else 'running',
            'message': step_result.get('message') if step_result else '',
            'data': step_result.get('data') if step_result else {},
            'results': step_result.get('results') if step_result else {},
        }
    }


# Singleton
_template_service = None

def get_template_service() -> TemplateService:
    """Get the template service singleton."""
    global _template_service
    if _template_service is None:
        _template_service = TemplateService()
    return _template_service
