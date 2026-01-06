"""
Permission Enforcement Middleware

Provides decorators and utilities for enforcing RBAC permissions on API endpoints.
Note: This module uses Flask for legacy compatibility. For FastAPI, use the 
authentication in backend/main.py instead.
"""

import functools
import logging
from typing import List, Optional, Union

# Flask imports for legacy middleware (optional)
try:
    from flask import request, jsonify, g
    FLASK_AVAILABLE = True
except ImportError:
    request = None
    jsonify = None
    g = None
    FLASK_AVAILABLE = False

from backend.database import get_db
from backend.services.auth_service import get_auth_service

logger = logging.getLogger(__name__)


def get_current_user():
    """
    Get the current authenticated user from the request.
    Returns user dict with id, username, roles, permissions or None if not authenticated.
    """
    # Check if user is already cached in request context
    if hasattr(g, 'current_user') and g.current_user:
        return g.current_user
    
    # Get session token from Authorization header or cookie
    auth_header = request.headers.get('Authorization', '')
    session_token = None
    
    if auth_header.startswith('Bearer '):
        session_token = auth_header[7:]
    elif request.cookies.get('session_token'):
        session_token = request.cookies.get('session_token')
    
    if not session_token:
        return None
    
    try:
        auth_service = get_auth_service()
        user = auth_service.validate_session(session_token)
        
        if user:
            # Cache in request context
            g.current_user = user
            
            # Set logging context for user attribution
            from backend.services.logging_service import set_context
            set_context(
                user_id=user.get('user_id'),
                username=user.get('username'),
                is_enterprise=user.get('is_enterprise', False)
            )
            
            return user
    except Exception as e:
        logger.error(f"Error validating session: {e}")
    
    return None


def get_user_permissions(user_id) -> List[str]:
    """
    Get all permission codes for a user based on their roles.
    
    For enterprise users (user_id starts with 'enterprise_'), looks up
    permissions via enterprise_user_roles table.
    For local users, looks up via user_roles table.
    """
    db = get_db()
    
    # Handle enterprise users
    if isinstance(user_id, str) and user_id.startswith('enterprise_'):
        enterprise_id = int(user_id.replace('enterprise_', ''))
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT p.code
                FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                JOIN enterprise_user_roles eur ON rp.role_id = eur.role_id
                WHERE eur.id = %s
            """, (enterprise_id,))
            return [row['code'] for row in cursor.fetchall()]
    
    # Handle local users
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT p.code
            FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            JOIN user_roles ur ON rp.role_id = ur.role_id
            WHERE ur.user_id = %s
        """, (user_id,))
        return [row['code'] for row in cursor.fetchall()]


def has_permission(user_id: int, permission_code: str) -> bool:
    """Check if a user has a specific permission."""
    permissions = get_user_permissions(user_id)
    return permission_code in permissions


def has_any_permission(user_id: int, permission_codes: List[str]) -> bool:
    """Check if a user has any of the specified permissions."""
    permissions = get_user_permissions(user_id)
    return any(code in permissions for code in permission_codes)


def has_all_permissions(user_id: int, permission_codes: List[str]) -> bool:
    """Check if a user has all of the specified permissions."""
    permissions = get_user_permissions(user_id)
    return all(code in permissions for code in permission_codes)


def is_admin(user_id) -> bool:
    """
    Check if user has admin role.
    
    For enterprise users (user_id starts with 'enterprise_'), checks
    enterprise_user_roles table. For local users, checks user_roles.
    """
    db = get_db()
    
    # Handle enterprise users
    if isinstance(user_id, str) and user_id.startswith('enterprise_'):
        enterprise_id = int(user_id.replace('enterprise_', ''))
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT 1 FROM enterprise_user_roles eur
                JOIN roles r ON eur.role_id = r.id
                WHERE eur.id = %s AND r.name IN ('admin', 'super_admin')
            """, (enterprise_id,))
            return cursor.fetchone() is not None
    
    # Handle local users
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT 1 FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = %s AND r.name IN ('admin', 'super_admin')
        """, (user_id,))
        return cursor.fetchone() is not None


def require_auth(f):
    """
    Decorator that requires authentication.
    Returns 401 if user is not authenticated.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            logger.warning(f"Unauthorized access attempt to {request.path}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'Authentication required'
                }
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def require_permission(permission_code: Union[str, List[str]], require_all: bool = False):
    """
    Decorator that requires specific permission(s).
    
    Args:
        permission_code: Single permission code or list of codes
        require_all: If True, user must have ALL permissions. If False, ANY permission suffices.
    
    Returns 401 if not authenticated, 403 if permission denied.
    
    Usage:
        @require_permission('jobs.job.execute')
        def run_job():
            ...
        
        @require_permission(['jobs.job.create', 'jobs.job.edit'])
        def save_job():
            ...
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            
            if not user:
                logger.warning(f"Unauthorized access attempt to {request.path}")
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'UNAUTHORIZED',
                        'message': 'Authentication required'
                    }
                }), 401
            
            user_id = user.get('user_id') or user.get('id')
            
            # Admins bypass permission checks
            if is_admin(user_id):
                return f(*args, **kwargs)
            
            # Check permissions
            codes = [permission_code] if isinstance(permission_code, str) else permission_code
            
            if require_all:
                has_perm = has_all_permissions(user_id, codes)
            else:
                has_perm = has_any_permission(user_id, codes)
            
            if not has_perm:
                logger.warning(
                    f"Permission denied for user {user.get('username')} "
                    f"on {request.method} {request.path}. "
                    f"Required: {codes}"
                )
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': f'Permission denied. Required: {", ".join(codes)}'
                    }
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_admin(f):
    """
    Decorator that requires admin role.
    Returns 401 if not authenticated, 403 if not admin.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        
        if not user:
            logger.warning(f"Unauthorized access attempt to {request.path}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNAUTHORIZED',
                    'message': 'Authentication required'
                }
            }), 401
        
        if not is_admin(user.get('id')):
            logger.warning(
                f"Admin access denied for user {user.get('username')} "
                f"on {request.method} {request.path}"
            )
            return jsonify({
                'success': False,
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Admin access required'
                }
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function


# Permission code constants for easy reference
class Permissions:
    """Permission code constants."""
    
    # Devices
    DEVICES_VIEW = 'devices.device.view'
    DEVICES_CREATE = 'devices.device.create'
    DEVICES_EDIT = 'devices.device.edit'
    DEVICES_DELETE = 'devices.device.delete'
    DEVICES_CONNECT = 'devices.device.connect'
    
    # Groups
    GROUPS_VIEW = 'devices.group.view'
    GROUPS_MANAGE = 'devices.group.manage'
    
    # Jobs/Workflows
    JOBS_VIEW = 'jobs.job.view'
    JOBS_CREATE = 'jobs.job.create'
    JOBS_EDIT = 'jobs.job.edit'
    JOBS_DELETE = 'jobs.job.delete'
    JOBS_EXECUTE = 'jobs.job.execute'
    JOBS_SCHEDULE = 'jobs.job.schedule'
    
    # Credentials
    CREDENTIALS_VIEW = 'credentials.credential.view'
    CREDENTIALS_CREATE = 'credentials.credential.create'
    CREDENTIALS_EDIT = 'credentials.credential.edit'
    CREDENTIALS_DELETE = 'credentials.credential.delete'
    CREDENTIALS_USE = 'credentials.credential.use'
    CREDENTIALS_VIEW_SECRET = 'credentials.credential.view_secret'
    
    # Credential Groups
    CREDENTIAL_GROUPS_MANAGE = 'credentials.group.manage'
    
    # Enterprise Auth
    ENTERPRISE_MANAGE = 'credentials.enterprise.manage'
    
    # System
    SYSTEM_SETTINGS_VIEW = 'system.settings.view'
    SYSTEM_SETTINGS_EDIT = 'system.settings.edit'
    SYSTEM_USERS_VIEW = 'system.users.view'
    SYSTEM_USERS_MANAGE = 'system.users.manage'
    SYSTEM_ROLES_MANAGE = 'system.roles.manage'
    SYSTEM_AUDIT_VIEW = 'system.audit.view'
    
    # Notifications
    NOTIFICATIONS_VIEW = 'notifications.channel.view'
    NOTIFICATIONS_MANAGE = 'notifications.channel.manage'
    
    # Reports
    REPORTS_VIEW = 'reports.report.view'
    REPORTS_CREATE = 'reports.report.create'
    REPORTS_EXPORT = 'reports.report.export'
