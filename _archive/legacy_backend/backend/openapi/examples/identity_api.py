"""
Example: Refactored Identity API following OpenAPI 3.x standards
This shows how to transform the current auth endpoints into the new structure
"""

from fastapi import APIRouter, Depends, HTTPException, Security, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
import jwt
from passlib.context import CryptContext

# Router setup
router = APIRouter(prefix="/identity/v1", tags=["identity", "auth", "users", "roles"])
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============================================================================
# Pydantic Models (OpenAPI Schema)
# ============================================================================

class StandardError(BaseModel):
    """Standard error response format"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None

class User(BaseModel):
    """User model"""
    id: str
    username: str
    email: EmailStr
    display_name: str
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    status: str = "active"
    two_factor_enabled: bool = False
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    roles: List[str] = []

class UserCreate(BaseModel):
    """Create user request"""
    username: str
    email: EmailStr
    password: str
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    roles: List[str] = []

class UserUpdate(BaseModel):
    """Update user request"""
    email: Optional[EmailStr] = None
    display_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: Optional[str] = None
    roles: Optional[List[str]] = None

class LoginRequest(BaseModel):
    """Login request"""
    username: str
    password: str

class LoginResponse(BaseModel):
    """Login response"""
    success: bool
    access_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    user: Optional[User] = None

class Role(BaseModel):
    """Role model"""
    id: str
    name: str
    display_name: str
    description: str
    role_type: str
    is_default: bool = False
    priority: int = 100
    user_count: int = 0
    permission_count: int = 0
    created_at: datetime
    updated_at: datetime

class PasswordPolicy(BaseModel):
    """Password policy model"""
    min_length: int = 8
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_numbers: bool = True
    require_special: bool = True
    max_age_days: int = 90
    prevent_reuse: int = 5
    lockout_attempts: int = 5
    lockout_duration_minutes: int = 30

class PaginatedUsers(BaseModel):
    """Paginated users response"""
    items: List[User]
    total: int
    limit: int
    cursor: Optional[str] = None

# ============================================================================
# Helper Functions
# ============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, "YOUR_SECRET_KEY", algorithm="HS256")
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)

def encode_cursor(data: dict) -> str:
    """Encode pagination cursor"""
    import base64
    import json
    json_str = json.dumps(data)
    return base64.b64encode(json_str.encode()).decode()

def decode_cursor(cursor: str) -> dict:
    """Decode pagination cursor"""
    import base64
    import json
    json_str = base64.b64decode(cursor.encode()).decode()
    return json.loads(json_str)

# ============================================================================
# Authentication Dependencies
# ============================================================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get current authenticated user"""
    try:
        payload = jwt.decode(credentials.credentials, "YOUR_SECRET_KEY", algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # In real implementation, fetch user from database
    user = {
        "id": user_id,
        "username": "admin",
        "email": "admin@example.com",
        "display_name": "Administrator",
        "status": "active"
    }
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

async def require_permission(permission: str):
    """Check if user has specific permission"""
    def permission_checker(current_user: dict = Depends(get_current_user)):
        # In real implementation, check user permissions
        if permission == "identity.admin" and current_user.get("username") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return permission_checker

# ============================================================================
# API Endpoints
# ============================================================================

@router.post(
    "/auth/login",
    response_model=LoginResponse,
    responses={
        401: {"model": StandardError, "description": "Invalid credentials"},
        429: {"model": StandardError, "description": "Too many login attempts"}
    },
    summary="Authenticate user",
    description="Authenticate with username/password and receive JWT token"
)
async def login(
    request: LoginRequest,
    request_id: str = None  # Set by middleware
):
    """
    Authenticate a user and return a JWT token.
    
    - **username**: User's login name
    - **password**: User's password
    
    Returns JWT token valid for 24 hours and user information.
    """
    try:
        # In real implementation, verify credentials against database
        if request.username == "admin" and request.password == "password":
            user_data = {
                "id": "1",
                "username": "admin",
                "email": "admin@example.com",
                "display_name": "Administrator",
                "status": "active",
                "roles": ["super_admin"]
            }
            
            access_token_expires = timedelta(hours=24)
            access_token = create_access_token(
                data={"sub": user_data["id"], "username": user_data["username"]},
                expires_delta=access_token_expires
            )
            
            return LoginResponse(
                success=True,
                access_token=access_token,
                token_type="bearer",
                expires_in=86400,  # 24 hours in seconds
                user=User(**user_data, created_at=datetime.now(), updated_at=datetime.now())
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "INVALID_CREDENTIALS",
                    "message": "Invalid username or password",
                    "trace_id": request_id
                }
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "LOGIN_ERROR",
                "message": "Authentication service unavailable",
                "trace_id": request_id
            }
        )

@router.post(
    "/auth/logout",
    responses={
        401: {"model": StandardError, "description": "Unauthorized"}
    },
    summary="Logout user",
    description="Invalidate the current session token"
)
async def logout(
    current_user: dict = Depends(get_current_user),
    request_id: str = None
):
    """
    Logout the current user.
    
    In a real implementation, this would:
    - Add the token to a blacklist
    - Clear any session data
    - Log the logout event
    """
    return {"success": True, "message": "Logged out successfully"}

@router.get(
    "/auth/me",
    response_model=User,
    responses={
        401: {"model": StandardError, "description": "Unauthorized"}
    },
    summary="Get current user",
    description="Get information about the authenticated user"
)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    request_id: str = None
):
    """
    Get the current authenticated user's information.
    
    Returns user profile including roles and permissions.
    """
    # In real implementation, fetch full user data from database
    return User(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        display_name=current_user["display_name"],
        status=current_user["status"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        roles=current_user.get("roles", [])
    )

@router.get(
    "/users",
    response_model=PaginatedUsers,
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        403: {"model": StandardError, "description": "Forbidden"}
    },
    summary="List users",
    description="List all users with cursor-based pagination and filtering"
)
async def list_users(
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    search: Optional[str] = Query(None, description="Search by username or email"),
    status: Optional[str] = Query(None, description="Filter by status"),
    role: Optional[str] = Query(None, description="Filter by role"),
    current_user: dict = Depends(require_permission("identity.read")),
    request_id: str = None
):
    """
    List users with pagination and filtering.
    
    - **cursor**: Pagination cursor from previous request
    - **limit**: Number of users to return (max 100)
    - **search**: Search term for username/email
    - **status**: Filter by user status (active, inactive, locked)
    - **role**: Filter by role name
    
    Returns paginated list of users with cursor for next page.
    """
    try:
        # In real implementation, query database with filters
        users = [
            User(
                id="1",
                username="admin",
                email="admin@example.com",
                display_name="Administrator",
                status="active",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                roles=["super_admin"]
            )
        ]
        
        # Mock pagination
        next_cursor = None if len(users) < limit else encode_cursor({"last_id": users[-1].id})
        
        return PaginatedUsers(
            items=users,
            total=len(users),
            limit=limit,
            cursor=next_cursor
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "USERS_QUERY_ERROR",
                "message": "Failed to query users",
                "trace_id": request_id
            }
        )

@router.get(
    "/users/{user_id}",
    response_model=User,
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "User not found"}
    },
    summary="Get user details",
    description="Get detailed information about a specific user"
)
async def get_user(
    user_id: str,
    current_user: dict = Depends(require_permission("identity.read")),
    request_id: str = None
):
    """
    Get detailed information about a specific user.
    
    Returns complete user profile including roles and recent activity.
    """
    # In real implementation, fetch user from database
    if user_id == "1":
        return User(
            id=user_id,
            username="admin",
            email="admin@example.com",
            display_name="Administrator",
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            roles=["super_admin"]
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "USER_NOT_FOUND",
                "message": f"User with ID '{user_id}' not found",
                "trace_id": request_id
            }
        )

@router.get(
    "/roles",
    response_model=List[Role],
    responses={
        401: {"model": StandardError, "description": "Unauthorized"}
    },
    summary="List roles",
    description="List all available roles with user counts"
)
async def list_roles(
    current_user: dict = Depends(get_current_user),
    request_id: str = None
):
    """
    List all available roles in the system.
    
    Returns role definitions with user counts and permissions.
    """
    # In real implementation, fetch roles from database
    roles = [
        Role(
            id="1",
            name="super_admin",
            display_name="Super Administrator",
            description="Full system access with all permissions",
            role_type="system",
            priority=1000,
            user_count=1,
            permission_count=50,
            created_at=datetime.now(),
            updated_at=datetime.now()
        ),
        Role(
            id="2",
            name="operator",
            display_name="Operator",
            description="Can run jobs and manage devices",
            role_type="system",
            priority=500,
            user_count=0,
            permission_count=20,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    ]
    
    return roles

@router.get(
    "/roles/{role_id}/members",
    response_model=List[User],
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        404: {"model": StandardError, "description": "Role not found"}
    },
    summary="Get role members",
    description="Get all users assigned to a specific role"
)
async def get_role_members(
    role_id: str,
    current_user: dict = Depends(require_permission("identity.read")),
    request_id: str = None
):
    """
    Get all users assigned to a specific role.
    
    Returns list of users with their role assignments.
    """
    # In real implementation, fetch role members from database
    if role_id == "1":  # super_admin
        return [
            User(
                id="1",
                username="admin",
                email="admin@example.com",
                display_name="Administrator",
                status="active",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                roles=["super_admin"]
            )
        ]
    else:
        return []

@router.get(
    "/password-policy",
    response_model=PasswordPolicy,
    responses={
        401: {"model": StandardError, "description": "Unauthorized"}
    },
    summary="Get password policy",
    description="Get the current password policy settings"
)
async def get_password_policy(
    current_user: dict = Depends(require_permission("identity.read")),
    request_id: str = None
):
    """
    Get the current password policy settings.
    
    Returns password requirements and security settings.
    """
    return PasswordPolicy()

@router.put(
    "/password-policy",
    response_model=dict,
    responses={
        401: {"model": StandardError, "description": "Unauthorized"},
        403: {"model": StandardError, "description": "Forbidden"}
    },
    summary="Update password policy",
    description="Update the password policy settings"
)
async def update_password_policy(
    policy: PasswordPolicy,
    current_user: dict = Depends(require_permission("identity.admin")),
    request_id: str = None
):
    """
    Update the password policy settings.
    
    Requires admin privileges to modify security policies.
    """
    # In real implementation, update policy in database
    return {"success": True, "message": "Password policy updated successfully"}

# ============================================================================
# Example Usage in OpenAPI Documentation
# ============================================================================

"""
OpenAPI 3.x specification for this API:

openapi: 3.0.0
info:
  title: OpsConductor Identity API
  version: 1.0.0
  description: Authentication and user management API

paths:
  /identity/v1/auth/login:
    post:
      tags:
        - identity
        - auth
      summary: Authenticate user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/LoginRequest'
      responses:
        '200':
          description: Successful authentication
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/LoginResponse'
        '401':
          description: Invalid credentials
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/StandardError'

components:
  schemas:
    User:
      type: object
      required:
        - id
        - username
        - email
        - display_name
        - status
        - created_at
        - updated_at
      properties:
        id:
          type: string
          format: uuid
        username:
          type: string
          example: admin
        email:
          type: string
          format: email
          example: admin@example.com
        display_name:
          type: string
          example: Administrator
        status:
          type: string
          enum: [active, inactive, locked, pending]
          example: active
        roles:
          type: array
          items:
            type: string
          example: [super_admin]

    StandardError:
      type: object
      required:
        - code
        - message
      properties:
        code:
          type: string
          example: USER_NOT_FOUND
        message:
          type: string
          example: User not found
        details:
          type: object
          additionalProperties: true
        trace_id:
          type: string
          format: uuid

  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

security:
  - bearerAuth: []
"""
