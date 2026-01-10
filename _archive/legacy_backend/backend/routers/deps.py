"""
Shared Dependencies for Routers

Common dependencies, security, and utilities used across all routers.
This eliminates duplicate boilerplate code in each router.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import Depends, HTTPException, Security, Query, Body, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette import status
import logging

from backend.db import get_db

logger = logging.getLogger(__name__)

# Shared security scheme
security = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user.
    Returns user dict or raises 401.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Authentication required"}
        )
    # Token validation would go here - for now just return placeholder
    return {"token": credentials.credentials}


def db_query(query: str, params: tuple = None, fetch_one: bool = False) -> Any:
    """
    Execute a database query and return results.
    Reduces boilerplate for simple queries.
    """
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(query, params)
        if fetch_one:
            row = cursor.fetchone()
            return dict(row) if row else None
        return [dict(row) for row in cursor.fetchall()]


def db_execute(query: str, params: tuple = None) -> bool:
    """
    Execute a database command (INSERT/UPDATE/DELETE).
    Returns True on success.
    """
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(query, params)
        db.commit()
    return True


def table_exists(table_name: str) -> bool:
    """Check if a database table exists."""
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, (table_name,))
        return cursor.fetchone()[0]


def handle_db_error(e: Exception, operation: str, request_id: str = None) -> HTTPException:
    """
    Standard error handler for database operations.
    Logs the error and returns appropriate HTTP exception.
    """
    logger.error(f"{operation} error: {str(e)}")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "code": f"{operation.upper().replace(' ', '_')}_ERROR",
            "message": f"Failed to {operation.lower()}",
            "trace_id": request_id
        }
    )


# Standard response models
class StandardError:
    """Standard error response model"""
    code: str
    message: str
    trace_id: Optional[str] = None


# Re-export common FastAPI components for convenience
__all__ = [
    'Depends', 'HTTPException', 'Security', 'Query', 'Body', 'Path',
    'status', 'security', 'logger',
    'get_db', 'get_current_user', 
    'db_query', 'db_execute', 'table_exists',
    'handle_db_error', 'StandardError',
    'Any', 'Dict', 'List', 'Optional', 'datetime',
    'HTTPAuthorizationCredentials',
]
