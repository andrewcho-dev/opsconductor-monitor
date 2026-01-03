"""
User Action Audit Middleware.

Logs all user-initiated actions to the system_logs table for comprehensive audit trail.
Provides both manual logging functions and automatic request-level logging.
"""

import json
import logging
import re
from datetime import datetime
from functools import wraps
from flask import request, g, has_request_context

logger = logging.getLogger(__name__)

# Endpoints to skip logging (health checks, status, reads, etc.)
SKIP_ENDPOINTS = {
    'static',
    'health',
    'status',
}

# Paths to skip logging (regex patterns)
SKIP_PATH_PATTERNS = [
    r'^/api/auth/me$',  # Don't log auth checks
    r'^/api/auth/refresh$',  # Don't log token refresh
    r'^/api/logs',  # Don't log log viewing
    r'^/api/system/health',
    r'^/api/workflows/tasks/',  # Don't log task status checks
]


def get_current_user_info():
    """Get current user info from request context."""
    try:
        from ..api.auth import get_current_user
        user = get_current_user()
        if user:
            return {
                'user_id': user.get('user_id'),
                'username': user.get('username'),
                'display_name': user.get('display_name', user.get('username')),
                'is_enterprise': isinstance(user.get('user_id'), str) and str(user.get('user_id')).startswith('enterprise_'),
            }
    except Exception as e:
        logger.debug(f"Could not get current user: {e}")
    return None


def log_user_action(action_type, resource_type=None, resource_id=None, details=None, success=True, error_message=None):
    """
    Log a user action to the system_logs table.
    
    Args:
        action_type: Type of action (create, update, delete, run, etc.)
        resource_type: Type of resource (workflow, credential, device, etc.)
        resource_id: ID of the affected resource
        details: Additional details dict
        success: Whether the action succeeded
        error_message: Error message if failed
    """
    try:
        from ..database import get_db
        
        user_info = get_current_user_info()
        
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': 'INFO' if success else 'ERROR',
            'category': 'user_action',
            'source': 'api',
            'message': f"{action_type} {resource_type or 'resource'}" + (f" {resource_id}" if resource_id else ""),
            'details': json.dumps({
                'action_type': action_type,
                'resource_type': resource_type,
                'resource_id': resource_id,
                'user': user_info,
                'endpoint': request.endpoint if request else None,
                'method': request.method if request else None,
                'path': request.path if request else None,
                'ip_address': request.remote_addr if request else None,
                'success': success,
                'error_message': error_message,
                **(details or {})
            })
        }
        
        db = get_db()
        with db.get_connection().cursor() as cursor:
            cursor.execute("""
                INSERT INTO system_logs (timestamp, level, category, source, message, details)
                VALUES (%(timestamp)s, %(level)s, %(category)s, %(source)s, %(message)s, %(details)s)
            """, log_entry)
            db.get_connection().commit()
            
    except Exception as e:
        logger.error(f"Failed to log user action: {e}")


def audit_action(action_type, resource_type=None, get_resource_id=None):
    """
    Decorator to automatically log user actions.
    
    Args:
        action_type: Type of action (create, update, delete, run, etc.)
        resource_type: Type of resource
        get_resource_id: Function to extract resource ID from args/kwargs
    
    Usage:
        @audit_action('run', 'workflow', lambda *args, **kwargs: kwargs.get('workflow_id') or args[0])
        def run_workflow(workflow_id):
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            resource_id = None
            if get_resource_id:
                try:
                    resource_id = get_resource_id(*args, **kwargs)
                except:
                    pass
            
            try:
                result = f(*args, **kwargs)
                log_user_action(
                    action_type=action_type,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    success=True
                )
                return result
            except Exception as e:
                log_user_action(
                    action_type=action_type,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    success=False,
                    error_message=str(e)
                )
                raise
        return decorated
    return decorator


def should_log_request():
    """Check if the current request should be logged."""
    if not has_request_context():
        return False
    
    # Only log modifying requests
    if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
        return False
    
    # Skip certain endpoints
    if request.endpoint and any(skip in request.endpoint for skip in SKIP_ENDPOINTS):
        return False
    
    # Skip certain paths
    path = request.path
    for pattern in SKIP_PATH_PATTERNS:
        if re.match(pattern, path):
            return False
    
    return True


def extract_resource_info_from_path(path):
    """Extract resource type and ID from API path."""
    # Pattern: /api/<resource_type>/<resource_id>/...
    match = re.match(r'^/api/([^/]+)(?:/([^/]+))?(?:/(.+))?$', path)
    if match:
        resource_type = match.group(1)
        resource_id = match.group(2)
        action = match.group(3)
        return resource_type, resource_id, action
    return None, None, None


def get_action_type_from_request():
    """Determine action type from HTTP method and path."""
    method = request.method
    path = request.path
    
    # Check for specific action keywords in path
    if '/run' in path:
        return 'run'
    if '/test' in path:
        return 'test'
    if '/execute' in path:
        return 'execute'
    if '/start' in path:
        return 'start'
    if '/stop' in path:
        return 'stop'
    if '/pause' in path:
        return 'pause'
    if '/resume' in path:
        return 'resume'
    if '/enable' in path:
        return 'enable'
    if '/disable' in path:
        return 'disable'
    if '/login' in path:
        return 'login'
    if '/logout' in path:
        return 'logout'
    
    # Default based on HTTP method
    method_actions = {
        'POST': 'create',
        'PUT': 'update',
        'PATCH': 'update',
        'DELETE': 'delete'
    }
    return method_actions.get(method, 'action')


def log_request_action(response=None, error=None):
    """Log the current request as a user action."""
    if not should_log_request():
        return
    
    try:
        path = request.path
        resource_type, resource_id, sub_action = extract_resource_info_from_path(path)
        action_type = get_action_type_from_request()
        
        # Get request body for additional context (sanitized)
        request_data = None
        try:
            if request.is_json:
                data = request.get_json(silent=True)
                if data:
                    # Remove sensitive fields
                    sanitized = {k: v for k, v in data.items() 
                                if k.lower() not in ('password', 'secret', 'token', 'key', 'credential')}
                    request_data = sanitized
        except:
            pass
        
        # Determine success from response
        success = True
        error_message = None
        if error:
            success = False
            error_message = str(error)
        elif response:
            success = response.status_code < 400
            if not success:
                try:
                    resp_data = response.get_json()
                    error_message = resp_data.get('error') if isinstance(resp_data, dict) else None
                except:
                    error_message = f"HTTP {response.status_code}"
        
        log_user_action(
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            details={'request_data': request_data, 'sub_action': sub_action} if request_data or sub_action else None,
            success=success,
            error_message=error_message
        )
    except Exception as e:
        logger.error(f"Failed to log request action: {e}")


def init_audit_middleware(app):
    """
    Initialize the audit middleware on a Flask app.
    
    Call this in your app factory:
        from middleware.user_audit import init_audit_middleware
        init_audit_middleware(app)
    """
    @app.after_request
    def audit_after_request(response):
        try:
            log_request_action(response=response)
        except Exception as e:
            logger.error(f"Audit middleware error: {e}")
        return response
