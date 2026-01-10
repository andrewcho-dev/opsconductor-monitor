"""
Enterprise Authentication

Robust, enterprise-grade authentication system:
- JWT tokens with refresh
- Role-based access control (RBAC)
- API key support for service accounts
- Session management
- Audit logging
- Rate limiting
"""

import os
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
import jwt

from backend_v2.core.db import query, query_one, execute

logger = logging.getLogger(__name__)

# Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', secrets.token_hex(32))
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7


class Role(str, Enum):
    """User roles for RBAC."""
    ADMIN = 'admin'          # Full system access
    OPERATOR = 'operator'    # Alert management, addon config
    VIEWER = 'viewer'        # Read-only dashboard access
    SERVICE = 'service'      # API-only access for integrations


@dataclass
class User:
    """Authenticated user."""
    id: int
    username: str
    email: Optional[str]
    role: Role
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    def has_permission(self, required_role: Role) -> bool:
        """Check if user has required role level."""
        role_hierarchy = {
            Role.ADMIN: 4,
            Role.OPERATOR: 3,
            Role.SERVICE: 2,
            Role.VIEWER: 1,
        }
        return role_hierarchy.get(self.role, 0) >= role_hierarchy.get(required_role, 0)


@dataclass
class TokenPair:
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60


# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name='X-API-Key', auto_error=False)


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt."""
    salt = os.environ.get('PASSWORD_SALT', 'opsconductor')
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return hash_password(password) == hashed


def create_access_token(user: User) -> str:
    """Create JWT access token."""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        'sub': str(user.id),
        'username': user.username,
        'role': user.role.value,
        'exp': expire,
        'type': 'access',
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user: User) -> str:
    """Create JWT refresh token."""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        'sub': str(user.id),
        'exp': expire,
        'type': 'refresh',
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict]:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_user_by_id(user_id: int) -> Optional[User]:
    """Get user from database by ID."""
    row = query_one("SELECT * FROM users WHERE id = %s AND is_active = true", (user_id,))
    if row:
        return User(
            id=row['id'],
            username=row['username'],
            email=row.get('email'),
            role=Role(row['role']),
            is_active=row['is_active'],
            created_at=row['created_at'],
            last_login=row.get('last_login')
        )
    return None


def get_user_by_username(username: str) -> Optional[User]:
    """Get user from database by username."""
    row = query_one("SELECT * FROM users WHERE username = %s AND is_active = true", (username,))
    if row:
        return User(
            id=row['id'],
            username=row['username'],
            email=row.get('email'),
            role=Role(row['role']),
            is_active=row['is_active'],
            created_at=row['created_at'],
            last_login=row.get('last_login')
        )
    return None


def get_user_by_api_key(api_key: str) -> Optional[User]:
    """Get user by API key."""
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    row = query_one("""
        SELECT u.* FROM users u
        JOIN api_keys k ON k.user_id = u.id
        WHERE k.key_hash = %s AND k.is_active = true AND u.is_active = true
    """, (key_hash,))
    
    if row:
        # Update last used
        execute("UPDATE api_keys SET last_used_at = NOW() WHERE key_hash = %s", (key_hash,))
        
        return User(
            id=row['id'],
            username=row['username'],
            email=row.get('email'),
            role=Role(row['role']),
            is_active=row['is_active'],
            created_at=row['created_at'],
            last_login=row.get('last_login')
        )
    return None


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate user with username and password."""
    row = query_one(
        "SELECT * FROM users WHERE username = %s AND is_active = true",
        (username,)
    )
    
    if not row:
        return None
    
    if not verify_password(password, row['password_hash']):
        # Log failed attempt
        log_audit('login_failed', None, {'username': username})
        return None
    
    user = User(
        id=row['id'],
        username=row['username'],
        email=row.get('email'),
        role=Role(row['role']),
        is_active=row['is_active'],
        created_at=row['created_at'],
        last_login=row.get('last_login')
    )
    
    # Update last login
    execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user.id,))
    
    # Log successful login
    log_audit('login_success', user.id, {'username': username})
    
    return user


def login(username: str, password: str) -> Optional[TokenPair]:
    """Authenticate and return token pair."""
    user = authenticate_user(username, password)
    if not user:
        return None
    
    return TokenPair(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(user)
    )


def refresh_tokens(refresh_token: str) -> Optional[TokenPair]:
    """Refresh access token using refresh token."""
    payload = decode_token(refresh_token)
    if not payload or payload.get('type') != 'refresh':
        return None
    
    user = get_user_by_id(int(payload['sub']))
    if not user:
        return None
    
    return TokenPair(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(user)
    )


async def get_current_user(
    request: Request,
    bearer: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    api_key: str = Depends(api_key_header)
) -> User:
    """
    Get current authenticated user from JWT or API key.
    
    Raises HTTPException if not authenticated.
    """
    user = None
    
    # Try API key first
    if api_key:
        user = get_user_by_api_key(api_key)
    
    # Try JWT bearer token
    if not user and bearer:
        payload = decode_token(bearer.credentials)
        if payload and payload.get('type') == 'access':
            user = get_user_by_id(int(payload['sub']))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_user_optional(
    request: Request,
    bearer: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    api_key: str = Depends(api_key_header)
) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    try:
        return await get_current_user(request, bearer, api_key)
    except HTTPException:
        return None


def require_role(required_role: Role):
    """
    Dependency that requires a specific role.
    
    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user: User = Depends(require_role(Role.ADMIN))):
            ...
    """
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if not user.has_permission(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role.value}' required"
            )
        return user
    
    return role_checker


def log_audit(action: str, user_id: Optional[int], details: Dict = None) -> None:
    """Log audit event."""
    try:
        execute("""
            INSERT INTO audit_log (user_id, action, details, created_at)
            VALUES (%s, %s, %s, NOW())
        """, (user_id, action, str(details) if details else None))
    except Exception as e:
        logger.error(f"Audit log error: {e}")


# User management functions

def create_user(
    username: str,
    password: str,
    role: Role = Role.VIEWER,
    email: str = None
) -> User:
    """Create a new user."""
    password_hash = hash_password(password)
    
    row = execute("""
        INSERT INTO users (username, password_hash, email, role, is_active, created_at)
        VALUES (%s, %s, %s, %s, true, NOW())
        RETURNING *
    """, (username, password_hash, email, role.value))
    
    log_audit('user_created', None, {'username': username, 'role': role.value})
    
    return User(
        id=row['id'],
        username=row['username'],
        email=row.get('email'),
        role=Role(row['role']),
        is_active=row['is_active'],
        created_at=row['created_at'],
        last_login=None
    )


def create_api_key(user_id: int, name: str = 'default') -> str:
    """Create API key for user. Returns the raw key (only shown once)."""
    raw_key = f"opc_{secrets.token_hex(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    execute("""
        INSERT INTO api_keys (user_id, name, key_hash, is_active, created_at)
        VALUES (%s, %s, %s, true, NOW())
    """, (user_id, name, key_hash))
    
    log_audit('api_key_created', user_id, {'name': name})
    
    return raw_key


def revoke_api_key(key_id: int, user_id: int) -> bool:
    """Revoke an API key."""
    result = execute(
        "UPDATE api_keys SET is_active = false WHERE id = %s AND user_id = %s",
        (key_id, user_id)
    )
    return result > 0


def list_api_keys(user_id: int) -> List[Dict]:
    """List API keys for user (without actual key values)."""
    return query("""
        SELECT id, name, created_at, last_used_at, is_active
        FROM api_keys WHERE user_id = %s ORDER BY created_at DESC
    """, (user_id,))


def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    """Change user password."""
    row = query_one("SELECT password_hash FROM users WHERE id = %s", (user_id,))
    if not row or not verify_password(old_password, row['password_hash']):
        return False
    
    new_hash = hash_password(new_password)
    execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, user_id))
    
    log_audit('password_changed', user_id, {})
    return True
