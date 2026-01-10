"""
Users API Routes

User management and API key operations.
"""

import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend_v2.api.auth import get_current_user, require_role, Role, User, hash_password
from backend_v2.core.db import query, query_one, execute

router = APIRouter(tags=["users"])


class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str
    role: str = "viewer"
    is_active: bool = True


class UserUpdate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class ApiKeyCreate(BaseModel):
    name: str


@router.get("/users")
async def list_users(
    user: User = Depends(require_role(Role.ADMIN))
):
    """List all users."""
    users = query("""
        SELECT id, username, email, role, is_active, created_at, last_login
        FROM users ORDER BY username
    """)
    return {"items": users, "total": len(users)}


@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    user: User = Depends(require_role(Role.ADMIN))
):
    """Get a specific user."""
    result = query_one("""
        SELECT id, username, email, role, is_active, created_at, last_login
        FROM users WHERE id = %s
    """, (user_id,))
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.post("/users")
async def create_user(
    data: UserCreate,
    user: User = Depends(require_role(Role.ADMIN))
):
    """Create a new user."""
    existing = query_one("SELECT id FROM users WHERE username = %s", (data.username,))
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    password_hash = hash_password(data.password)
    
    result = query_one("""
        INSERT INTO users (username, email, password_hash, role, is_active)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, username, email, role, is_active, created_at
    """, (data.username, data.email, password_hash, data.role, data.is_active))
    
    return result


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    data: UserUpdate,
    user: User = Depends(require_role(Role.ADMIN))
):
    """Update a user."""
    existing = query_one("SELECT * FROM users WHERE id = %s", (user_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    updates = []
    params = []
    
    if data.email is not None:
        updates.append("email = %s")
        params.append(data.email)
    if data.password is not None:
        updates.append("password_hash = %s")
        params.append(hash_password(data.password))
    if data.role is not None:
        updates.append("role = %s")
        params.append(data.role)
    if data.is_active is not None:
        updates.append("is_active = %s")
        params.append(data.is_active)
    
    if not updates:
        return existing
    
    params.append(user_id)
    sql = f"UPDATE users SET {', '.join(updates)} WHERE id = %s RETURNING id, username, email, role, is_active, created_at, last_login"
    
    result = query_one(sql, tuple(params))
    return result


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    user: User = Depends(require_role(Role.ADMIN))
):
    """Delete a user."""
    existing = query_one("SELECT username FROM users WHERE id = %s", (user_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    if existing['username'] == 'admin':
        raise HTTPException(status_code=400, detail="Cannot delete admin user")
    
    execute("DELETE FROM users WHERE id = %s", (user_id,))
    return {"status": "deleted", "id": user_id}


@router.get("/api-keys")
async def list_api_keys(
    user: User = Depends(get_current_user)
):
    """List API keys for current user (admin sees all)."""
    if user.role == Role.ADMIN:
        keys = query("""
            SELECT id, user_id, name, key_prefix, created_at, last_used_at, expires_at
            FROM api_keys ORDER BY created_at DESC
        """)
    else:
        keys = query("""
            SELECT id, user_id, name, key_prefix, created_at, last_used_at, expires_at
            FROM api_keys WHERE user_id = %s ORDER BY created_at DESC
        """, (user.id,))
    
    return {"items": keys, "total": len(keys)}


@router.post("/api-keys")
async def create_api_key(
    data: ApiKeyCreate,
    user: User = Depends(get_current_user)
):
    """Create a new API key."""
    key = secrets.token_urlsafe(32)
    key_hash = hash_password(key)
    key_prefix = key[:8]
    
    result = query_one("""
        INSERT INTO api_keys (user_id, name, key_hash, key_prefix)
        VALUES (%s, %s, %s, %s)
        RETURNING id, name, key_prefix, created_at
    """, (user.id, data.name, key_hash, key_prefix))
    
    return {
        **result,
        "key": key  # Only returned once at creation
    }


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    user: User = Depends(get_current_user)
):
    """Revoke an API key."""
    if user.role == Role.ADMIN:
        existing = query_one("SELECT id FROM api_keys WHERE id = %s", (key_id,))
    else:
        existing = query_one(
            "SELECT id FROM api_keys WHERE id = %s AND user_id = %s",
            (key_id, user.id)
        )
    
    if not existing:
        raise HTTPException(status_code=404, detail="API key not found")
    
    execute("DELETE FROM api_keys WHERE id = %s", (key_id,))
    return {"status": "revoked", "id": key_id}
