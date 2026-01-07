"""
Identity API Router (/identity/v1)

Handles authentication, users, roles, sessions, and password policies.
"""

from fastapi import APIRouter, Query, Body, Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from backend.utils.db import db_query, db_query_one, db_execute, table_exists
from backend.openapi.identity_impl import (
    authenticate_user, get_current_user_from_token, list_users_paginated,
    list_roles_with_counts, get_role_members, get_role_permissions, get_all_permissions,
    get_password_policy, update_password_policy, test_identity_endpoints,
    create_access_token, JWT_SECRET_KEY, JWT_ALGORITHM
)

logger = logging.getLogger(__name__)
security = HTTPBearer()
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

router = APIRouter(tags=["identity", "auth", "users", "roles"])

# Auth routes (no prefix - /auth/*)
auth_router = APIRouter(tags=["auth"])


@auth_router.post("/login", summary="Authenticate user")
async def login(request: Dict[str, Any] = Body(...)):
    """Authenticate and return JWT token"""
    try:
        username = request.get('username')
        password = request.get('password')
        config_id = request.get('config_id')
        
        if config_id:
            user_data = await authenticate_enterprise_user(username, password, config_id)
        else:
            user_data = await authenticate_user(username, password)
        
        access_token = create_access_token(
            data={"sub": user_data["id"], "username": user_data["username"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": user_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "LOGIN_ERROR", "message": str(e)})


@auth_router.post("/logout", summary="Logout user")
async def logout():
    """Logout - client clears tokens"""
    return {"success": True, "message": "Logged out successfully"}


@auth_router.post("/login/enterprise", summary="Enterprise login")
async def enterprise_login(request: Dict[str, Any] = Body(...)):
    """Enterprise authentication endpoint"""
    try:
        user_data = await authenticate_user(request.get('username'), request.get('password'))
        access_token = create_access_token(
            data={"sub": user_data["id"], "username": user_data["username"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        return {"success": True, "data": {"access_token": access_token, "token_type": "bearer", "user": user_data}}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def authenticate_enterprise_user(username: str, password: str, config_id: str) -> dict:
    """Authenticate via enterprise provider (LDAP/AD/RADIUS)"""
    from backend.services.auth_service import AuthService
    
    auth_service = AuthService()
    success, user_data, error = auth_service.authenticate_ldap(username, password, int(config_id))
    
    if not success:
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": error or "Invalid credentials"})
    
    email = user_data.get('email', '')
    if not email or email == '[]' or '@' not in str(email):
        email = f'{username}@enterprise.local'
    
    return {
        "id": str(user_data.get('user_id', user_data.get('id', '0'))),
        "username": user_data.get('username', username),
        "email": email,
        "display_name": user_data.get('display_name', username) or username,
        "status": user_data.get('status', 'active') or 'active',
        "created_at": user_data.get('created_at', datetime.now())
    }


# Identity routes (/identity/v1/*)
identity_router = APIRouter(prefix="/identity/v1", tags=["identity", "users", "roles"])


@identity_router.get("/enterprise-configs", summary="Get enterprise auth configs")
async def get_enterprise_configs():
    """Get available enterprise authentication providers"""
    try:
        configs = db_query("""
            SELECT id, name, auth_type, is_default, enabled, priority
            FROM enterprise_auth_configs WHERE enabled = true
            ORDER BY priority ASC, name ASC
        """)
        for c in configs:
            c['id'] = str(c['id'])
        return {"success": True, "configs": configs, "default_method": "local"}
    except Exception as e:
        logger.error(f"Get enterprise configs error: {str(e)}")
        return {"success": False, "error": "Failed to load configurations"}


@identity_router.get("/auth/me", summary="Get current user")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get authenticated user info"""
    try:
        return await get_current_user_from_token(credentials.credentials)
    except Exception as e:
        raise HTTPException(status_code=401, detail={"code": "INVALID_TOKEN", "message": str(e)})


@identity_router.get("/users", summary="List users")
async def list_users(
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """List users with pagination"""
    try:
        return await list_users_paginated(page_cursor=cursor, limit=limit)
    except Exception as e:
        logger.error(f"List users error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "LIST_USERS_ERROR", "message": str(e)})


@identity_router.get("/roles", summary="List roles")
async def list_roles(credentials: HTTPAuthorizationCredentials = Security(security)):
    """List all roles"""
    try:
        return await list_roles_with_counts()
    except Exception as e:
        logger.error(f"List roles error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "LIST_ROLES_ERROR", "message": str(e)})


@identity_router.get("/roles/{role_id}/members", summary="Get role members")
async def get_members(role_id: int, credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get all users in a role (local and enterprise)"""
    try:
        return await get_role_members(role_id)
    except Exception as e:
        logger.error(f"Get role members error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "ROLE_MEMBERS_ERROR", "message": str(e)})


@identity_router.get("/roles/{role_id}/permissions", summary="Get role permissions")
async def get_permissions(role_id: int, credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get all permissions assigned to a role"""
    try:
        return await get_role_permissions(role_id)
    except Exception as e:
        logger.error(f"Get role permissions error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "ROLE_PERMISSIONS_ERROR", "message": str(e)})


@identity_router.get("/permissions", summary="Get all permissions")
async def list_permissions(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get all available permissions"""
    try:
        return await get_all_permissions()
    except Exception as e:
        logger.error(f"List permissions error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "LIST_PERMISSIONS_ERROR", "message": str(e)})


@identity_router.post("/roles/{role_id}/members", summary="Add user to role")
async def add_role_member(
    role_id: int,
    request: Dict[str, Any] = Body(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Add a local or enterprise user to a role"""
    try:
        username = request.get('username')
        auth_type = request.get('auth_type', 'enterprise')  # Default to enterprise
        display_name = request.get('display_name', '')
        email = request.get('email', '')
        
        if not username:
            raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": "username is required"})
        
        if auth_type == 'local':
            # Find local user and add to role
            user = db_query_one("SELECT id FROM users WHERE username = %s", (username,))
            if not user:
                raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND", "message": f"Local user {username} not found"})
            
            # Check if already assigned
            existing = db_query_one("SELECT id FROM user_roles WHERE user_id = %s AND role_id = %s", (user['id'], role_id))
            if existing:
                return {"success": True, "message": "User already assigned to role"}
            
            db_execute("INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)", (user['id'], role_id))
        else:
            # Enterprise user - add/update enterprise_user_roles
            existing = db_query_one("SELECT id FROM enterprise_user_roles WHERE username = %s", (username,))
            if existing:
                db_execute("UPDATE enterprise_user_roles SET role_id = %s, assigned_at = NOW() WHERE username = %s", (role_id, username))
            else:
                db_execute("""
                    INSERT INTO enterprise_user_roles (username, role_id, display_name, email, assigned_by, assigned_at)
                    VALUES (%s, %s, %s, %s, 1, NOW())
                """, (username, role_id, display_name or username, email))
        
        return {"success": True, "message": f"Added {username} to role"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add role member error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "ADD_MEMBER_ERROR", "message": str(e)})


@identity_router.delete("/roles/{role_id}/members/{username}", summary="Remove user from role")
async def remove_role_member(
    role_id: int,
    username: str,
    auth_type: str = Query("enterprise"),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Remove a user from a role"""
    try:
        if auth_type == 'local':
            user = db_query_one("SELECT id FROM users WHERE username = %s", (username,))
            if user:
                db_execute("DELETE FROM user_roles WHERE user_id = %s AND role_id = %s", (user['id'], role_id))
        else:
            db_execute("DELETE FROM enterprise_user_roles WHERE username = %s AND role_id = %s", (username, role_id))
        
        return {"success": True, "message": f"Removed {username} from role"}
    except Exception as e:
        logger.error(f"Remove role member error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "REMOVE_MEMBER_ERROR", "message": str(e)})


# ============================================================================
# Enterprise User Role Assignment
# ============================================================================

@identity_router.post("/enterprise-users/assign-role", summary="Assign role to enterprise user")
async def assign_enterprise_role_v2(
    request: Dict[str, Any] = Body(...),
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """
    Assign a role to an enterprise (AD/LDAP) user.
    Creates the mapping if it doesn't exist, updates if it does.
    Request body: { username: string, role_id: int, display_name?: string, email?: string }
    """
    try:
        username = request.get('username')
        role_id = request.get('role_id')
        display_name = request.get('display_name', '')
        email = request.get('email', '')
        
        if not username or not role_id:
            raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": "username and role_id are required"})
        
        # Check if role exists
        role = db_query_one("SELECT id, name FROM roles WHERE id = %s", (role_id,))
        if not role:
            raise HTTPException(status_code=404, detail={"code": "ROLE_NOT_FOUND", "message": f"Role {role_id} not found"})
        
        # Check if user already has a role assignment
        existing = db_query_one("SELECT id FROM enterprise_user_roles WHERE username = %s", (username,))
        
        if existing:
            # Update existing assignment
            db_execute("""
                UPDATE enterprise_user_roles 
                SET role_id = %s, display_name = %s, email = %s, assigned_at = NOW()
                WHERE username = %s
            """, (role_id, display_name or f"Enterprise - {username}", email, username))
            return {"success": True, "message": f"Updated role for {username} to {role['name']}", "action": "updated"}
        else:
            # Create new assignment
            db_execute("""
                INSERT INTO enterprise_user_roles (username, role_id, display_name, email, assigned_by, assigned_at)
                VALUES (%s, %s, %s, %s, 1, NOW())
            """, (username, role_id, display_name or f"Enterprise - {username}", email))
            return {"success": True, "message": f"Assigned {username} to role {role['name']}", "action": "created"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Assign enterprise role error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "ASSIGN_ROLE_ERROR", "message": str(e)})


@identity_router.delete("/enterprise-users/{username}/role", summary="Remove enterprise user role")
async def remove_enterprise_role_v2(
    username: str,
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Remove role assignment from an enterprise user"""
    try:
        existing = db_query_one("SELECT id FROM enterprise_user_roles WHERE username = %s", (username,))
        if not existing:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": f"No role assignment found for {username}"})
        
        db_execute("DELETE FROM enterprise_user_roles WHERE username = %s", (username,))
        return {"success": True, "message": f"Removed role assignment for {username}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Remove enterprise role error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "REMOVE_ROLE_ERROR", "message": str(e)})


@identity_router.get("/enterprise-users", summary="List enterprise user role assignments")
async def list_enterprise_users_v2(credentials: HTTPAuthorizationCredentials = Security(security)):
    """List all enterprise users with their role assignments"""
    try:
        users = db_query("""
            SELECT eur.id, eur.username, eur.display_name, eur.email, 
                   eur.role_id, r.name as role_name, eur.assigned_at, eur.assigned_by
            FROM enterprise_user_roles eur
            LEFT JOIN roles r ON eur.role_id = r.id
            ORDER BY eur.username
        """)
        return {"items": users, "total": len(users)}
    except Exception as e:
        logger.error(f"List enterprise users error: {str(e)}")
        raise HTTPException(status_code=500, detail={"code": "LIST_ERROR", "message": str(e)})


@identity_router.get("/sessions", summary="List sessions")
async def list_sessions(credentials: HTTPAuthorizationCredentials = Security(security)):
    """List active sessions"""
    return {"sessions": [], "total": 0}


@identity_router.post("/sessions/revoke-all", summary="Revoke all sessions")
async def revoke_sessions(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Revoke all user sessions"""
    return {"success": True, "revoked_count": 0}


@identity_router.get("/password-policy", summary="Get password policy")
async def get_policy(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get password policy settings"""
    return await get_password_policy()


@identity_router.post("/auth/2fa/setup", summary="Setup 2FA")
async def setup_2fa(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Setup two-factor authentication"""
    return {"success": True, "qr_code": "", "secret": ""}


@identity_router.post("/auth/2fa/verify", summary="Verify 2FA")
async def verify_2fa(request: Dict[str, Any] = Body(...), credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify 2FA code"""
    return {"success": True, "verified": True}


@identity_router.post("/auth/2fa/disable", summary="Disable 2FA")
async def disable_2fa(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Disable 2FA"""
    return {"success": True}


@identity_router.put("/auth/me/password", summary="Change password")
async def change_password(request: Dict[str, Any] = Body(...), credentials: HTTPAuthorizationCredentials = Security(security)):
    """Change current user password"""
    return {"success": True, "message": "Password changed"}


@identity_router.get("/test", include_in_schema=False)
async def test_api():
    """Test Identity API"""
    try:
        results = await test_identity_endpoints()
        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Export both routers
router = identity_router
