"""
Authentication API Router - FastAPI.

Handles login, logout, registration, 2FA, and user management.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging

from backend.services.auth_service import get_auth_service

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class EnterpriseLoginRequest(BaseModel):
    username: str
    password: str
    config_id: int


class TwoFactorLoginRequest(BaseModel):
    user_id: int
    code: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ValidatePasswordRequest(BaseModel):
    password: str
    username: Optional[str] = None
    email: Optional[str] = None


class TwoFactorVerifyRequest(BaseModel):
    code: str


class TwoFactorDisableRequest(BaseModel):
    password: str


class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    auth_method: str = "local"
    roles: Optional[List[str]] = None


class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    status: Optional[str] = None


class UpdateUserRolesRequest(BaseModel):
    role_ids: List[int]


class CreateRoleRequest(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = None


# =============================================================================
# AUTH HELPERS
# =============================================================================

def get_current_user(request: Request):
    """Get current user from request headers."""
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header[7:]  # Remove 'Bearer ' prefix
    
    auth_service = get_auth_service()
    session = auth_service.validate_session(token)
    
    return session


def require_auth(request: Request):
    """Dependency to require authentication."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=401,
            detail={"success": False, "error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}
        )
    return user


def require_permission(permission_code: str):
    """Factory for permission-checking dependency."""
    def check_permission(request: Request):
        user = get_current_user(request)
        if not user:
            raise HTTPException(
                status_code=401,
                detail={"success": False, "error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}
            )
        
        auth_service = get_auth_service()
        if not auth_service.user_has_permission(user['user_id'], permission_code):
            raise HTTPException(
                status_code=403,
                detail={"success": False, "error": {"code": "FORBIDDEN", "message": "Permission denied"}}
            )
        return user
    return check_permission


# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

@router.post("/login")
async def login(req: LoginRequest, request: Request):
    """Authenticate user with username/password."""
    try:
        auth_service = get_auth_service()
        
        success, result, error = auth_service.authenticate(
            username=req.username,
            password=req.password,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('User-Agent')
        )
        
        if not success:
            return {"success": False, "error": {"code": "AUTH_FAILED", "message": error}}
        
        # Check if 2FA is required
        if result.get('requires_2fa'):
            return {
                "success": True,
                "data": {
                    "requires_2fa": True,
                    "user_id": result['user_id'],
                    "two_factor_method": result['two_factor_method']
                }
            }
        
        # Get user roles and permissions
        roles = auth_service.get_user_roles(result['user_id'])
        permissions = auth_service.get_user_permissions(result['user_id'])
        
        return {
            "success": True,
            "data": {
                "user": {
                    "id": result['user_id'],
                    "username": result['username'],
                    "email": result['email'],
                    "display_name": result['display_name'],
                    "roles": [r['name'] for r in roles],
                    "permissions": permissions
                },
                "session_token": result['session_token'],
                "refresh_token": result['refresh_token'],
                "expires_at": result['expires_at']
            }
        }
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Login failed"}})


@router.post("/login/enterprise")
async def login_enterprise(req: EnterpriseLoginRequest, request: Request):
    """Authenticate user with enterprise auth (LDAP/AD)."""
    try:
        auth_service = get_auth_service()
        
        success, result, error = auth_service.authenticate_ldap(
            username=req.username,
            password=req.password,
            config_id=req.config_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('User-Agent')
        )
        
        if not success:
            return {"success": False, "error": {"code": "AUTH_FAILED", "message": error}}
        
        if result.get('requires_2fa'):
            return {
                "success": True,
                "data": {
                    "requires_2fa": True,
                    "user_id": result['user_id'],
                    "two_factor_method": result['two_factor_method']
                }
            }
        
        if result.get('is_enterprise'):
            return {
                "success": True,
                "data": {
                    "user": {
                        "id": result['user_id'],
                        "username": result['username'],
                        "email": result.get('email', ''),
                        "display_name": result.get('display_name', result['username']),
                        "roles": result.get('roles', []),
                        "permissions": result.get('permissions', []),
                        "is_enterprise": True
                    },
                    "session_token": result['session_token'],
                    "refresh_token": result['refresh_token'],
                    "expires_at": result['expires_at']
                }
            }
        
        roles = auth_service.get_user_roles(result['user_id'])
        permissions = auth_service.get_user_permissions(result['user_id'])
        
        return {
            "success": True,
            "data": {
                "user": {
                    "id": result['user_id'],
                    "username": result['username'],
                    "email": result['email'],
                    "display_name": result['display_name'],
                    "roles": [r['name'] for r in roles],
                    "permissions": permissions
                },
                "session_token": result['session_token'],
                "refresh_token": result['refresh_token'],
                "expires_at": result['expires_at']
            }
        }
        
    except Exception as e:
        logger.error(f"Enterprise login error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Login failed"}})


@router.get("/enterprise-configs")
async def get_enterprise_configs():
    """Get available enterprise auth configurations for login page."""
    try:
        auth_service = get_auth_service()
        configs = auth_service.get_enterprise_auth_configs_for_login()
        return {"success": True, "data": {"configs": configs}}
    except Exception as e:
        logger.error(f"Get enterprise configs error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Failed to get configs"}})


@router.post("/login/2fa")
async def login_2fa(req: TwoFactorLoginRequest, request: Request):
    """Complete login with 2FA verification."""
    try:
        auth_service = get_auth_service()
        
        success, result, error = auth_service.complete_2fa_login(
            user_id=req.user_id,
            code=req.code,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('User-Agent')
        )
        
        if not success:
            return {"success": False, "error": {"code": "2FA_FAILED", "message": error}}
        
        roles = auth_service.get_user_roles(result['user_id'])
        permissions = auth_service.get_user_permissions(result['user_id'])
        
        return {
            "success": True,
            "data": {
                "user": {
                    "id": result['user_id'],
                    "username": result['username'],
                    "email": result['email'],
                    "display_name": result['display_name'],
                    "roles": [r['name'] for r in roles],
                    "permissions": permissions
                },
                "session_token": result['session_token'],
                "refresh_token": result['refresh_token'],
                "expires_at": result['expires_at']
            }
        }
        
    except Exception as e:
        logger.error(f"2FA login error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "2FA verification failed"}})


@router.post("/logout")
async def logout(request: Request, user: dict = Depends(require_auth)):
    """Log out current session."""
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header[7:] if auth_header.startswith('Bearer ') else None
        
        if token:
            auth_service = get_auth_service()
            auth_service.revoke_session(token, reason='logout')
        
        return {"success": True, "data": {"message": "Logged out successfully"}}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Logout failed"}})


@router.post("/refresh")
async def refresh_token(req: RefreshTokenRequest):
    """Refresh session token."""
    try:
        auth_service = get_auth_service()
        result = auth_service.refresh_session(req.refresh_token)
        
        if not result:
            return {"success": False, "error": {"code": "INVALID_TOKEN", "message": "Invalid or expired refresh token"}}
        
        return {
            "success": True,
            "data": {
                "session_token": result['session_token'],
                "refresh_token": result['refresh_token'],
                "expires_at": result['expires_at'].isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Token refresh failed"}})


@router.get("/me")
async def get_current_user_info(request: Request, user: dict = Depends(require_auth)):
    """Get current user information."""
    try:
        user_id = user['user_id']
        auth_service = get_auth_service()
        
        # Handle enterprise users
        if isinstance(user_id, str) and user_id.startswith('enterprise_'):
            permissions = auth_service.get_user_permissions(user_id)
            return {
                "success": True,
                "data": {
                    "user": {
                        "id": user_id,
                        "username": user.get('username'),
                        "email": user.get('email', ''),
                        "display_name": user.get('display_name', user.get('username')),
                        "roles": user.get('roles', []),
                        "permissions": permissions,
                        "is_enterprise": True
                    }
                }
            }
        
        user_data = auth_service.get_user(user_id)
        roles = auth_service.get_user_roles(user_id)
        permissions = auth_service.get_user_permissions(user_id)
        
        return {
            "success": True,
            "data": {
                "user": {
                    **user_data,
                    "roles": [r['name'] for r in roles],
                    "permissions": permissions
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Failed to get user info"}})


@router.put("/me")
async def update_current_user(req: UpdateUserRequest, request: Request, user: dict = Depends(require_auth)):
    """Update current user profile."""
    try:
        auth_service = get_auth_service()
        updated_user = auth_service.update_user(user['user_id'], req.model_dump(exclude_unset=True))
        return {"success": True, "data": {"user": updated_user}}
    except Exception as e:
        logger.error(f"Update user error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Failed to update user"}})


@router.get("/password-policy")
async def get_password_policy():
    """Get password policy settings and requirements."""
    try:
        auth_service = get_auth_service()
        policy = auth_service.get_password_policy()
        requirements = auth_service.get_password_requirements_text()
        return {"success": True, "data": {"policy": policy, "requirements": requirements}}
    except Exception as e:
        logger.error(f"Get password policy error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Failed to get password policy"}})


@router.put("/password-policy")
async def update_password_policy(request: Request, user: dict = Depends(require_permission('system.settings.edit'))):
    """Update password policy settings (admin only)."""
    try:
        data = await request.json()
        auth_service = get_auth_service()
        policy = auth_service.update_password_policy(updates=data, updated_by=user['user_id'])
        return {"success": True, "data": {"policy": policy}}
    except Exception as e:
        logger.error(f"Update password policy error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Failed to update password policy"}})


@router.post("/validate-password")
async def validate_password(req: ValidatePasswordRequest):
    """Validate a password against the policy."""
    try:
        auth_service = get_auth_service()
        is_valid, errors = auth_service.validate_password(
            password=req.password,
            username=req.username,
            email=req.email
        )
        return {"success": True, "data": {"valid": is_valid, "errors": errors}}
    except Exception as e:
        logger.error(f"Validate password error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Failed to validate password"}})


@router.put("/me/password")
async def change_password(req: ChangePasswordRequest, request: Request, user: dict = Depends(require_auth)):
    """Change current user's password."""
    try:
        auth_service = get_auth_service()
        user_data = auth_service.get_user(user['user_id'])
        
        is_valid, errors = auth_service.validate_password(
            password=req.new_password,
            username=user_data.get('username'),
            email=user_data.get('email'),
            user_id=user['user_id']
        )
        
        if not is_valid:
            return {"success": False, "error": {"code": "VALIDATION_ERROR", "message": errors[0] if errors else "Password does not meet requirements", "details": errors}}
        
        success = auth_service.change_password(user['user_id'], req.current_password, req.new_password)
        
        if not success:
            return {"success": False, "error": {"code": "AUTH_FAILED", "message": "Current password is incorrect"}}
        
        return {"success": True, "data": {"message": "Password changed successfully"}}
        
    except Exception as e:
        logger.error(f"Change password error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Failed to change password"}})


# =============================================================================
# 2FA MANAGEMENT
# =============================================================================

@router.post("/2fa/setup")
async def setup_2fa(request: Request, user: dict = Depends(require_auth)):
    """Start 2FA setup - returns secret and QR code URI."""
    try:
        auth_service = get_auth_service()
        result = auth_service.setup_totp(user['user_id'])
        return {
            "success": True,
            "data": {
                "secret": result['secret'],
                "provisioning_uri": result['provisioning_uri'],
                "backup_codes": result['backup_codes']
            }
        }
    except Exception as e:
        logger.error(f"2FA setup error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Failed to setup 2FA"}})


@router.post("/2fa/verify")
async def verify_2fa_setup(req: TwoFactorVerifyRequest, request: Request, user: dict = Depends(require_auth)):
    """Verify 2FA setup with a code from authenticator app."""
    try:
        auth_service = get_auth_service()
        success = auth_service.verify_totp_setup(user['user_id'], req.code)
        
        if not success:
            return {"success": False, "error": {"code": "INVALID_CODE", "message": "Invalid verification code"}}
        
        return {"success": True, "data": {"message": "2FA enabled successfully"}}
    except Exception as e:
        logger.error(f"2FA verify error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": f"Failed to verify 2FA: {str(e)}"}})


@router.post("/2fa/disable")
async def disable_2fa(req: TwoFactorDisableRequest, request: Request, user: dict = Depends(require_auth)):
    """Disable 2FA (requires password confirmation)."""
    try:
        auth_service = get_auth_service()
        success = auth_service.disable_2fa(user['user_id'], req.password)
        
        if not success:
            return {"success": False, "error": {"code": "AUTH_FAILED", "message": "Invalid password"}}
        
        return {"success": True, "data": {"message": "2FA disabled successfully"}}
    except Exception as e:
        logger.error(f"2FA disable error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Failed to disable 2FA"}})


# =============================================================================
# USER MANAGEMENT (Admin)
# =============================================================================

@router.get("/users")
async def list_users(
    request: Request,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    user: dict = Depends(require_permission('system.users.view'))
):
    """List all users (admin only)."""
    try:
        auth_service = get_auth_service()
        result = auth_service.list_users(status=status, search=search, limit=limit, offset=offset)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"List users error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Failed to list users"}})


@router.post("/users")
async def create_user(req: CreateUserRequest, request: Request, user: dict = Depends(require_permission('system.users.create'))):
    """Create a new user (admin only)."""
    try:
        auth_service = get_auth_service()
        
        new_user = auth_service.create_user(
            username=req.username,
            email=req.email,
            password=req.password,
            first_name=req.first_name,
            last_name=req.last_name,
            auth_method=req.auth_method,
            role_names=req.roles,
            created_by=user['user_id']
        )
        
        return {"success": True, "data": {"user": new_user}}
        
    except ValueError as e:
        return {"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(e)}}
    except Exception as e:
        logger.error(f"Create user error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Failed to create user"}})


@router.get("/users/{user_id}")
async def get_user(user_id: int, request: Request, user: dict = Depends(require_permission('system.users.view'))):
    """Get user details (admin only)."""
    try:
        auth_service = get_auth_service()
        user_data = auth_service.get_user(user_id)
        
        if not user_data:
            return {"success": False, "error": {"code": "NOT_FOUND", "message": "User not found"}}
        
        roles = auth_service.get_user_roles(user_id)
        user_data['roles'] = roles
        
        return {"success": True, "data": {"user": user_data}}
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Failed to get user"}})


@router.put("/users/{user_id}")
async def update_user(user_id: int, req: UpdateUserRequest, request: Request, user: dict = Depends(require_permission('system.users.edit'))):
    """Update user (admin only)."""
    try:
        auth_service = get_auth_service()
        updated_user = auth_service.update_user(user_id, req.model_dump(exclude_unset=True))
        
        if not updated_user:
            return {"success": False, "error": {"code": "NOT_FOUND", "message": "User not found"}}
        
        return {"success": True, "data": {"user": updated_user}}
    except Exception as e:
        logger.error(f"Update user error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Failed to update user"}})


@router.put("/users/{user_id}/roles")
async def update_user_roles(user_id: int, req: UpdateUserRolesRequest, request: Request, user: dict = Depends(require_permission('system.users.edit'))):
    """Update user roles (admin only)."""
    try:
        auth_service = get_auth_service()
        
        current_roles = auth_service.get_user_roles(user_id)
        current_role_ids = {r['id'] for r in current_roles}
        new_role_ids = set(req.role_ids)
        
        for role_id in current_role_ids - new_role_ids:
            auth_service.remove_role(user_id, role_id)
        
        for role_id in new_role_ids - current_role_ids:
            auth_service.assign_role(user_id, role_id, user['user_id'])
        
        roles = auth_service.get_user_roles(user_id)
        return {"success": True, "data": {"roles": roles}}
    except Exception as e:
        logger.error(f"Update user roles error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Failed to update user roles"}})


# =============================================================================
# ROLE MANAGEMENT
# =============================================================================

@router.get("/roles")
async def list_roles(request: Request, user: dict = Depends(require_auth)):
    """List all roles."""
    try:
        auth_service = get_auth_service()
        roles = auth_service.list_roles()
        return {"success": True, "data": {"roles": roles}}
    except Exception as e:
        logger.error(f"List roles error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Failed to list roles"}})


@router.get("/roles/{role_id}")
async def get_role(role_id: int, request: Request, user: dict = Depends(require_auth)):
    """Get role details with permissions."""
    try:
        auth_service = get_auth_service()
        role = auth_service.get_role(role_id)
        
        if not role:
            return {"success": False, "error": {"code": "NOT_FOUND", "message": "Role not found"}}
        
        return {"success": True, "data": {"role": role}}
    except Exception as e:
        logger.error(f"Get role error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Failed to get role"}})


@router.get("/roles/{role_id}/members")
async def get_role_members(role_id: int, request: Request, user: dict = Depends(require_auth)):
    """Get users assigned to a role."""
    try:
        from backend.database import get_db
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT u.id, u.username, u.email, u.display_name, u.status, u.created_at
                FROM users u
                JOIN user_roles ur ON u.id = ur.user_id
                WHERE ur.role_id = %s
                ORDER BY u.username
            """, (role_id,))
            members = [dict(row) for row in cursor.fetchall()]
        return {"success": True, "data": {"members": members}}
    except Exception as e:
        logger.error(f"Get role members error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Failed to get role members"}})


@router.post("/roles")
async def create_role(req: CreateRoleRequest, request: Request, user: dict = Depends(require_permission('system.roles.manage'))):
    """Create a new role."""
    try:
        auth_service = get_auth_service()
        role = auth_service.create_role(
            name=req.name,
            display_name=req.display_name,
            description=req.description,
            permission_ids=req.permission_ids,
            created_by=user['user_id']
        )
        return {"success": True, "data": {"role": role}}
    except Exception as e:
        logger.error(f"Create role error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Failed to create role"}})


@router.get("/permissions")
async def list_permissions(request: Request, user: dict = Depends(require_auth)):
    """List all available permissions."""
    try:
        auth_service = get_auth_service()
        permissions = auth_service.list_permissions()
        return {"success": True, "data": {"permissions": permissions}}
    except Exception as e:
        logger.error(f"List permissions error: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "error": {"code": "SERVER_ERROR", "message": "Failed to list permissions"}})


@router.get("/status")
async def auth_status(request: Request):
    """Check authentication status."""
    user = get_current_user(request)
    if user:
        return {"success": True, "data": {"authenticated": True, "user": user}}
    return {"success": True, "data": {"authenticated": False}}
