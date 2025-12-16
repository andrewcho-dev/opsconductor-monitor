"""
Authentication API Routes

Handles login, logout, registration, 2FA, and user management.
"""

from functools import wraps
from flask import Blueprint, request, jsonify, g
import logging

from backend.services.auth_service import get_auth_service

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


# =============================================================================
# AUTH MIDDLEWARE
# =============================================================================

def get_current_user():
    """Get current user from request headers."""
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header[7:]  # Remove 'Bearer ' prefix
    
    auth_service = get_auth_service()
    session = auth_service.validate_session(token)
    
    if not session:
        return None
    
    return session


def login_required(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                'success': False,
                'error': {'code': 'UNAUTHORIZED', 'message': 'Authentication required'}
            }), 401
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def permission_required(permission_code):
    """Decorator to require a specific permission."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({
                    'success': False,
                    'error': {'code': 'UNAUTHORIZED', 'message': 'Authentication required'}
                }), 401
            
            auth_service = get_auth_service()
            if not auth_service.user_has_permission(user['user_id'], permission_code):
                return jsonify({
                    'success': False,
                    'error': {'code': 'FORBIDDEN', 'message': 'Permission denied'}
                }), 403
            
            g.current_user = user
            return f(*args, **kwargs)
        return decorated
    return decorator


# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate user with username/password.
    
    Request body:
        username: string
        password: string
    
    Returns:
        On success without 2FA: session tokens
        On success with 2FA: requires_2fa flag
        On failure: error message
    """
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': {'code': 'VALIDATION_ERROR', 'message': 'Username and password required'}
            }), 400
        
        auth_service = get_auth_service()
        
        success, result, error = auth_service.authenticate(
            username=username,
            password=password,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        if not success:
            return jsonify({
                'success': False,
                'error': {'code': 'AUTH_FAILED', 'message': error}
            }), 401
        
        # Check if 2FA is required
        if result.get('requires_2fa'):
            return jsonify({
                'success': True,
                'data': {
                    'requires_2fa': True,
                    'user_id': result['user_id'],
                    'two_factor_method': result['two_factor_method']
                }
            })
        
        # Get user roles and permissions
        roles = auth_service.get_user_roles(result['user_id'])
        permissions = auth_service.get_user_permissions(result['user_id'])
        
        return jsonify({
            'success': True,
            'data': {
                'user': {
                    'id': result['user_id'],
                    'username': result['username'],
                    'email': result['email'],
                    'display_name': result['display_name'],
                    'roles': [r['name'] for r in roles],
                    'permissions': permissions
                },
                'session_token': result['session_token'],
                'refresh_token': result['refresh_token'],
                'expires_at': result['expires_at']
            }
        })
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Login failed'}
        }), 500


@auth_bp.route('/login/enterprise', methods=['POST'])
def login_enterprise():
    """
    Authenticate user with enterprise auth (LDAP/AD).
    
    Request body:
        username: string
        password: string
        config_id: int (enterprise auth config ID)
    """
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        config_id = data.get('config_id')
        
        if not username or not password or not config_id:
            return jsonify({
                'success': False,
                'error': {'code': 'VALIDATION_ERROR', 'message': 'Username, password, and config_id required'}
            }), 400
        
        auth_service = get_auth_service()
        
        success, result, error = auth_service.authenticate_ldap(
            username=username,
            password=password,
            config_id=config_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        if not success:
            return jsonify({
                'success': False,
                'error': {'code': 'AUTH_FAILED', 'message': error}
            }), 401
        
        # Check if 2FA is required
        if result.get('requires_2fa'):
            return jsonify({
                'success': True,
                'data': {
                    'requires_2fa': True,
                    'user_id': result['user_id'],
                    'two_factor_method': result['two_factor_method']
                }
            })
        
        # Get user roles and permissions
        roles = auth_service.get_user_roles(result['user_id'])
        permissions = auth_service.get_user_permissions(result['user_id'])
        
        return jsonify({
            'success': True,
            'data': {
                'user': {
                    'id': result['user_id'],
                    'username': result['username'],
                    'email': result['email'],
                    'display_name': result['display_name'],
                    'roles': [r['name'] for r in roles],
                    'permissions': permissions
                },
                'session_token': result['session_token'],
                'refresh_token': result['refresh_token'],
                'expires_at': result['expires_at']
            }
        })
        
    except Exception as e:
        logger.error(f"Enterprise login error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Login failed'}
        }), 500


@auth_bp.route('/enterprise-configs', methods=['GET'])
def get_enterprise_configs():
    """Get available enterprise auth configurations for login page."""
    try:
        auth_service = get_auth_service()
        configs = auth_service.get_enterprise_auth_configs_for_login()
        
        return jsonify({
            'success': True,
            'data': {'configs': configs}
        })
        
    except Exception as e:
        logger.error(f"Get enterprise configs error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to get configs'}
        }), 500


@auth_bp.route('/login/2fa', methods=['POST'])
def login_2fa():
    """
    Complete login with 2FA verification.
    
    Request body:
        user_id: int
        code: string (TOTP code or backup code)
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        code = data.get('code')
        
        if not user_id or not code:
            return jsonify({
                'success': False,
                'error': {'code': 'VALIDATION_ERROR', 'message': 'User ID and code required'}
            }), 400
        
        auth_service = get_auth_service()
        
        success, result, error = auth_service.complete_2fa_login(
            user_id=user_id,
            code=code,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        if not success:
            return jsonify({
                'success': False,
                'error': {'code': '2FA_FAILED', 'message': error}
            }), 401
        
        # Get user roles and permissions
        roles = auth_service.get_user_roles(result['user_id'])
        permissions = auth_service.get_user_permissions(result['user_id'])
        
        return jsonify({
            'success': True,
            'data': {
                'user': {
                    'id': result['user_id'],
                    'username': result['username'],
                    'email': result['email'],
                    'display_name': result['display_name'],
                    'roles': [r['name'] for r in roles],
                    'permissions': permissions
                },
                'session_token': result['session_token'],
                'refresh_token': result['refresh_token'],
                'expires_at': result['expires_at']
            }
        })
        
    except Exception as e:
        logger.error(f"2FA login error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': '2FA verification failed'}
        }), 500


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Log out current session."""
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header[7:] if auth_header.startswith('Bearer ') else None
        
        if token:
            auth_service = get_auth_service()
            auth_service.revoke_session(token, reason='logout')
        
        return jsonify({'success': True, 'data': {'message': 'Logged out successfully'}})
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Logout failed'}
        }), 500


@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """Refresh session token."""
    try:
        data = request.get_json()
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return jsonify({
                'success': False,
                'error': {'code': 'VALIDATION_ERROR', 'message': 'Refresh token required'}
            }), 400
        
        auth_service = get_auth_service()
        result = auth_service.refresh_session(refresh_token)
        
        if not result:
            return jsonify({
                'success': False,
                'error': {'code': 'INVALID_TOKEN', 'message': 'Invalid or expired refresh token'}
            }), 401
        
        return jsonify({
            'success': True,
            'data': {
                'session_token': result['session_token'],
                'refresh_token': result['refresh_token'],
                'expires_at': result['expires_at'].isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Token refresh failed'}
        }), 500


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user_info():
    """Get current user information."""
    try:
        auth_service = get_auth_service()
        user = auth_service.get_user(g.current_user['user_id'])
        roles = auth_service.get_user_roles(g.current_user['user_id'])
        permissions = auth_service.get_user_permissions(g.current_user['user_id'])
        
        return jsonify({
            'success': True,
            'data': {
                'user': {
                    **user,
                    'roles': [r['name'] for r in roles],
                    'permissions': permissions
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to get user info'}
        }), 500


@auth_bp.route('/me', methods=['PUT'])
@login_required
def update_current_user():
    """Update current user profile."""
    try:
        data = request.get_json()
        auth_service = get_auth_service()
        
        user = auth_service.update_user(g.current_user['user_id'], data)
        
        return jsonify({
            'success': True,
            'data': {'user': user}
        })
        
    except Exception as e:
        logger.error(f"Update user error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to update user'}
        }), 500


@auth_bp.route('/me/password', methods=['PUT'])
@login_required
def change_password():
    """Change current user's password."""
    try:
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({
                'success': False,
                'error': {'code': 'VALIDATION_ERROR', 'message': 'Current and new password required'}
            }), 400
        
        if len(new_password) < 8:
            return jsonify({
                'success': False,
                'error': {'code': 'VALIDATION_ERROR', 'message': 'Password must be at least 8 characters'}
            }), 400
        
        auth_service = get_auth_service()
        success = auth_service.change_password(
            g.current_user['user_id'],
            current_password,
            new_password
        )
        
        if not success:
            return jsonify({
                'success': False,
                'error': {'code': 'AUTH_FAILED', 'message': 'Current password is incorrect'}
            }), 400
        
        return jsonify({
            'success': True,
            'data': {'message': 'Password changed successfully'}
        })
        
    except Exception as e:
        logger.error(f"Change password error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to change password'}
        }), 500


# =============================================================================
# 2FA MANAGEMENT
# =============================================================================

@auth_bp.route('/2fa/setup', methods=['POST'])
@login_required
def setup_2fa():
    """Start 2FA setup - returns secret and QR code URI."""
    try:
        auth_service = get_auth_service()
        result = auth_service.setup_totp(g.current_user['user_id'])
        
        return jsonify({
            'success': True,
            'data': {
                'secret': result['secret'],
                'provisioning_uri': result['provisioning_uri'],
                'backup_codes': result['backup_codes']
            }
        })
        
    except Exception as e:
        logger.error(f"2FA setup error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to setup 2FA'}
        }), 500


@auth_bp.route('/2fa/verify', methods=['POST'])
@login_required
def verify_2fa_setup():
    """Verify 2FA setup with a code from authenticator app."""
    try:
        data = request.get_json()
        code = data.get('code')
        
        if not code:
            return jsonify({
                'success': False,
                'error': {'code': 'VALIDATION_ERROR', 'message': 'Verification code required'}
            }), 400
        
        auth_service = get_auth_service()
        success = auth_service.verify_totp_setup(g.current_user['user_id'], code)
        
        if not success:
            return jsonify({
                'success': False,
                'error': {'code': 'INVALID_CODE', 'message': 'Invalid verification code'}
            }), 400
        
        return jsonify({
            'success': True,
            'data': {'message': '2FA enabled successfully'}
        })
        
    except Exception as e:
        logger.error(f"2FA verify error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to verify 2FA'}
        }), 500


@auth_bp.route('/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    """Disable 2FA (requires password confirmation)."""
    try:
        data = request.get_json()
        password = data.get('password')
        
        if not password:
            return jsonify({
                'success': False,
                'error': {'code': 'VALIDATION_ERROR', 'message': 'Password required to disable 2FA'}
            }), 400
        
        auth_service = get_auth_service()
        success = auth_service.disable_2fa(g.current_user['user_id'], password)
        
        if not success:
            return jsonify({
                'success': False,
                'error': {'code': 'AUTH_FAILED', 'message': 'Invalid password'}
            }), 400
        
        return jsonify({
            'success': True,
            'data': {'message': '2FA disabled successfully'}
        })
        
    except Exception as e:
        logger.error(f"2FA disable error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to disable 2FA'}
        }), 500


# =============================================================================
# USER MANAGEMENT (Admin)
# =============================================================================

@auth_bp.route('/users', methods=['GET'])
@permission_required('system.users.view')
def list_users():
    """List all users (admin only)."""
    try:
        auth_service = get_auth_service()
        
        status = request.args.get('status')
        search = request.args.get('search')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        result = auth_service.list_users(
            status=status,
            search=search,
            limit=limit,
            offset=offset
        )
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"List users error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to list users'}
        }), 500


@auth_bp.route('/users', methods=['POST'])
@permission_required('system.users.create')
def create_user():
    """Create a new user (admin only)."""
    try:
        data = request.get_json()
        
        required = ['username', 'email']
        for field in required:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': {'code': 'VALIDATION_ERROR', 'message': f'{field} is required'}
                }), 400
        
        auth_service = get_auth_service()
        
        user = auth_service.create_user(
            username=data['username'],
            email=data['email'],
            password=data.get('password'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            auth_method=data.get('auth_method', 'local'),
            role_names=data.get('roles'),
            created_by=g.current_user['user_id']
        )
        
        return jsonify({
            'success': True,
            'data': {'user': user}
        }), 201
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}
        }), 400
    except Exception as e:
        logger.error(f"Create user error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to create user'}
        }), 500


@auth_bp.route('/users/<int:user_id>', methods=['GET'])
@permission_required('system.users.view')
def get_user(user_id):
    """Get user details (admin only)."""
    try:
        auth_service = get_auth_service()
        user = auth_service.get_user(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'User not found'}
            }), 404
        
        roles = auth_service.get_user_roles(user_id)
        user['roles'] = roles
        
        return jsonify({
            'success': True,
            'data': {'user': user}
        })
        
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to get user'}
        }), 500


@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@permission_required('system.users.edit')
def update_user(user_id):
    """Update user (admin only)."""
    try:
        data = request.get_json()
        auth_service = get_auth_service()
        
        user = auth_service.update_user(user_id, data)
        
        if not user:
            return jsonify({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'User not found'}
            }), 404
        
        return jsonify({
            'success': True,
            'data': {'user': user}
        })
        
    except Exception as e:
        logger.error(f"Update user error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to update user'}
        }), 500


@auth_bp.route('/users/<int:user_id>/roles', methods=['PUT'])
@permission_required('system.users.edit')
def update_user_roles(user_id):
    """Update user roles (admin only)."""
    try:
        data = request.get_json()
        role_ids = data.get('role_ids', [])
        
        auth_service = get_auth_service()
        
        # Get current roles
        current_roles = auth_service.get_user_roles(user_id)
        current_role_ids = {r['id'] for r in current_roles}
        new_role_ids = set(role_ids)
        
        # Remove roles
        for role_id in current_role_ids - new_role_ids:
            auth_service.remove_role(user_id, role_id)
        
        # Add roles
        for role_id in new_role_ids - current_role_ids:
            auth_service.assign_role(user_id, role_id, g.current_user['user_id'])
        
        # Get updated roles
        roles = auth_service.get_user_roles(user_id)
        
        return jsonify({
            'success': True,
            'data': {'roles': roles}
        })
        
    except Exception as e:
        logger.error(f"Update user roles error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to update user roles'}
        }), 500


# =============================================================================
# ROLE MANAGEMENT
# =============================================================================

@auth_bp.route('/roles', methods=['GET'])
@login_required
def list_roles():
    """List all roles."""
    try:
        auth_service = get_auth_service()
        roles = auth_service.list_roles()
        
        return jsonify({
            'success': True,
            'data': {'roles': roles}
        })
        
    except Exception as e:
        logger.error(f"List roles error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to list roles'}
        }), 500


@auth_bp.route('/roles/<int:role_id>', methods=['GET'])
@login_required
def get_role(role_id):
    """Get role details with permissions."""
    try:
        auth_service = get_auth_service()
        role = auth_service.get_role(role_id)
        
        if not role:
            return jsonify({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Role not found'}
            }), 404
        
        return jsonify({
            'success': True,
            'data': {'role': role}
        })
        
    except Exception as e:
        logger.error(f"Get role error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to get role'}
        }), 500


@auth_bp.route('/roles', methods=['POST'])
@permission_required('system.roles.manage')
def create_role():
    """Create a new role."""
    try:
        data = request.get_json()
        
        if not data.get('name') or not data.get('display_name'):
            return jsonify({
                'success': False,
                'error': {'code': 'VALIDATION_ERROR', 'message': 'name and display_name are required'}
            }), 400
        
        auth_service = get_auth_service()
        role = auth_service.create_role(
            name=data['name'],
            display_name=data['display_name'],
            description=data.get('description', ''),
            permissions=data.get('permissions', [])
        )
        
        return jsonify({
            'success': True,
            'data': {'role': role}
        }), 201
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}
        }), 400
    except Exception as e:
        logger.error(f"Create role error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to create role'}
        }), 500


@auth_bp.route('/roles/<int:role_id>', methods=['PUT'])
@permission_required('system.roles.manage')
def update_role(role_id):
    """Update a role."""
    try:
        data = request.get_json()
        
        auth_service = get_auth_service()
        
        # Check if role exists and is not a system role
        role = auth_service.get_role(role_id)
        if not role:
            return jsonify({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Role not found'}
            }), 404
        
        if role.get('is_system'):
            return jsonify({
                'success': False,
                'error': {'code': 'FORBIDDEN', 'message': 'Cannot modify system roles'}
            }), 403
        
        updated_role = auth_service.update_role(
            role_id=role_id,
            display_name=data.get('display_name'),
            description=data.get('description'),
            permissions=data.get('permissions')
        )
        
        return jsonify({
            'success': True,
            'data': {'role': updated_role}
        })
        
    except Exception as e:
        logger.error(f"Update role error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to update role'}
        }), 500


@auth_bp.route('/roles/<int:role_id>', methods=['DELETE'])
@permission_required('system.roles.manage')
def delete_role(role_id):
    """Delete a role."""
    try:
        auth_service = get_auth_service()
        
        # Check if role exists and is not a system role
        role = auth_service.get_role(role_id)
        if not role:
            return jsonify({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Role not found'}
            }), 404
        
        if role.get('is_system'):
            return jsonify({
                'success': False,
                'error': {'code': 'FORBIDDEN', 'message': 'Cannot delete system roles'}
            }), 403
        
        auth_service.delete_role(role_id)
        
        return jsonify({
            'success': True,
            'data': {'message': 'Role deleted'}
        })
        
    except Exception as e:
        logger.error(f"Delete role error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to delete role'}
        }), 500


@auth_bp.route('/permissions', methods=['GET'])
@login_required
def list_permissions():
    """List all permissions."""
    try:
        auth_service = get_auth_service()
        
        module = request.args.get('module')
        permissions = auth_service.list_permissions(module)
        modules = auth_service.get_permission_modules()
        
        return jsonify({
            'success': True,
            'data': {
                'permissions': permissions,
                'modules': modules
            }
        })
        
    except Exception as e:
        logger.error(f"List permissions error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to list permissions'}
        }), 500


# =============================================================================
# AUDIT LOG
# =============================================================================

@auth_bp.route('/audit', methods=['GET'])
@permission_required('system.audit.view')
def get_audit_log():
    """Get authentication audit log."""
    try:
        auth_service = get_auth_service()
        
        user_id = request.args.get('user_id', type=int)
        event_type = request.args.get('event_type')
        limit = int(request.args.get('limit', 100))
        
        entries = auth_service.get_auth_audit_log(
            user_id=user_id,
            event_type=event_type,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'data': {'entries': entries}
        })
        
    except Exception as e:
        logger.error(f"Get audit log error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to get audit log'}
        }), 500


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================

@auth_bp.route('/sessions', methods=['GET'])
@login_required
def list_sessions():
    """List current user's active sessions."""
    try:
        auth_service = get_auth_service()
        
        with auth_service.db.cursor() as cursor:
            cursor.execute("""
                SELECT id, ip_address, user_agent, created_at, last_activity_at, expires_at
                FROM user_sessions
                WHERE user_id = %s AND revoked = FALSE AND expires_at > NOW()
                ORDER BY last_activity_at DESC
            """, (g.current_user['user_id'],))
            sessions = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'data': {'sessions': sessions}
        })
        
    except Exception as e:
        logger.error(f"List sessions error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to list sessions'}
        }), 500


@auth_bp.route('/sessions/revoke-all', methods=['POST'])
@login_required
def revoke_all_sessions():
    """Revoke all sessions except current."""
    try:
        auth_header = request.headers.get('Authorization', '')
        current_token = auth_header[7:] if auth_header.startswith('Bearer ') else None
        
        auth_service = get_auth_service()
        auth_service.revoke_all_sessions(g.current_user['user_id'], except_session=current_token)
        
        return jsonify({
            'success': True,
            'data': {'message': 'All other sessions revoked'}
        })
        
    except Exception as e:
        logger.error(f"Revoke sessions error: {e}")
        return jsonify({
            'success': False,
            'error': {'code': 'SERVER_ERROR', 'message': 'Failed to revoke sessions'}
        }), 500
