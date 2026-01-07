"""
Database Utility Functions

Centralized database access patterns to eliminate duplicate code.
All database operations should use these functions instead of raw cursor access.

Usage:
    from backend.utils.db import db_query, db_query_one, db_execute, get_setting, set_setting
    
    # Query multiple rows
    users = db_query("SELECT * FROM users WHERE status = %s", ('active',))
    
    # Query single row
    user = db_query_one("SELECT * FROM users WHERE id = %s", (user_id,))
    
    # Execute INSERT/UPDATE/DELETE
    db_execute("UPDATE users SET status = %s WHERE id = %s", ('inactive', user_id))
    
    # Get system setting (cached)
    netbox_url = get_setting('netbox_url')
    
    # Set system setting
    set_setting('netbox_url', 'http://netbox.local', updated_by='admin')
"""

from typing import Any, Dict, List, Optional, Tuple, Union
from functools import lru_cache
import logging

from backend.database import get_db

logger = logging.getLogger(__name__)

# Settings cache - cleared on set_setting calls
_settings_cache: Dict[str, Any] = {}
_settings_cache_enabled = True


def db_query(sql: str, params: Tuple = None) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query and return all rows as list of dicts.
    
    Args:
        sql: SQL query string with %s placeholders
        params: Tuple of parameters to substitute
        
    Returns:
        List of dictionaries, one per row
        
    Example:
        users = db_query("SELECT * FROM users WHERE role = %s", ('admin',))
    """
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(sql, params)
        if cursor.description:
            return [dict(row) for row in cursor.fetchall()]
        return []


def db_query_one(sql: str, params: Tuple = None) -> Optional[Dict[str, Any]]:
    """
    Execute a SELECT query and return single row as dict, or None.
    
    Args:
        sql: SQL query string with %s placeholders
        params: Tuple of parameters to substitute
        
    Returns:
        Dictionary for the row, or None if not found
        
    Example:
        user = db_query_one("SELECT * FROM users WHERE id = %s", (123,))
        if user:
            print(user['username'])
    """
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None


def db_execute(sql: str, params: Tuple = None, returning: bool = False) -> Union[int, Dict[str, Any], None]:
    """
    Execute an INSERT/UPDATE/DELETE statement.
    
    Args:
        sql: SQL statement with %s placeholders
        params: Tuple of parameters to substitute
        returning: If True and SQL has RETURNING clause, return the row
        
    Returns:
        If returning=True: Dictionary of returned row
        Otherwise: Number of affected rows
        
    Example:
        # Simple update
        affected = db_execute("UPDATE users SET status = %s WHERE id = %s", ('active', 123))
        
        # Insert with RETURNING
        new_user = db_execute(
            "INSERT INTO users (username) VALUES (%s) RETURNING id, username",
            ('newuser',),
            returning=True
        )
    """
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(sql, params)
        # Note: autocommit is enabled on the connection, no explicit commit needed
        
        if returning and cursor.description:
            row = cursor.fetchone()
            return dict(row) if row else None
        
        return cursor.rowcount


def get_setting(key: str, default: Any = None) -> Any:
    """
    Get a system setting by key (cached).
    
    Args:
        key: Setting key (e.g., 'netbox_url', 'netbox_token')
        default: Default value if setting not found
        
    Returns:
        Setting value, or default if not found
        
    Example:
        netbox_url = get_setting('netbox_url')
        timeout = get_setting('api_timeout', 30)
    """
    global _settings_cache
    
    # Check cache first
    if _settings_cache_enabled and key in _settings_cache:
        return _settings_cache[key]
    
    # Query database
    row = db_query_one("SELECT value FROM system_settings WHERE key = %s", (key,))
    value = row['value'] if row else default
    
    # Cache the result
    if _settings_cache_enabled:
        _settings_cache[key] = value
    
    return value


def get_settings_by_prefix(prefix: str) -> Dict[str, Any]:
    """
    Get all settings matching a key prefix.
    
    Args:
        prefix: Key prefix (e.g., 'netbox_' for netbox_url, netbox_token, etc.)
        
    Returns:
        Dictionary of key: value pairs
        
    Example:
        netbox_settings = get_settings_by_prefix('netbox_')
        # Returns: {'netbox_url': '...', 'netbox_token': '...'}
    """
    rows = db_query(
        "SELECT key, value FROM system_settings WHERE key LIKE %s",
        (f"{prefix}%",)
    )
    return {row['key']: row['value'] for row in rows}


def set_setting(key: str, value: Any, updated_by: str = 'system') -> bool:
    """
    Set a system setting (upsert).
    
    Args:
        key: Setting key
        value: Setting value (will be converted to string)
        updated_by: Username of who made the change
        
    Returns:
        True on success
        
    Example:
        set_setting('netbox_url', 'http://netbox.local', updated_by='admin')
    """
    global _settings_cache
    
    # Clear cache for this key
    if key in _settings_cache:
        del _settings_cache[key]
    
    db_execute("""
        INSERT INTO system_settings (key, value, updated_by, updated_at)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (key) DO UPDATE SET value = %s, updated_by = %s, updated_at = NOW()
    """, (key, str(value), updated_by, str(value), updated_by))
    
    return True


def clear_settings_cache():
    """Clear the settings cache (useful after bulk updates)."""
    global _settings_cache
    _settings_cache = {}


def table_exists(table_name: str) -> bool:
    """
    Check if a database table exists.
    
    Args:
        table_name: Name of the table
        
    Returns:
        True if table exists
    """
    row = db_query_one("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = %s
        ) as exists
    """, (table_name,))
    return row['exists'] if row else False


def count_rows(table_name: str, where: str = None, params: Tuple = None) -> int:
    """
    Count rows in a table with optional WHERE clause.
    
    Args:
        table_name: Name of the table
        where: Optional WHERE clause (without 'WHERE' keyword)
        params: Parameters for WHERE clause
        
    Returns:
        Row count
        
    Example:
        total_users = count_rows('users')
        active_users = count_rows('users', "status = %s", ('active',))
    """
    sql = f"SELECT COUNT(*) as count FROM {table_name}"
    if where:
        sql += f" WHERE {where}"
    
    row = db_query_one(sql, params)
    return row['count'] if row else 0


def db_paginate(
    select_sql: str,
    count_sql: str,
    params: List = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Execute a paginated query with count and cursor support.
    
    Args:
        select_sql: SELECT query (should include ORDER BY, LIMIT will be added)
        count_sql: COUNT query for total
        params: Parameters list (will be modified to add limit)
        limit: Number of items per page
        
    Returns:
        Dict with 'items', 'total', 'limit', 'cursor'
        
    Example:
        result = db_paginate(
            "SELECT * FROM users WHERE status = %s ORDER BY id",
            "SELECT COUNT(*) as total FROM users WHERE status = %s",
            ['active'],
            limit=50
        )
    """
    import base64
    import json
    
    params = list(params) if params else []
    
    # Get total count
    total_row = db_query_one(count_sql, tuple(params) if params else None)
    total = total_row['total'] if total_row else 0
    
    # Add limit + 1 to check for more pages
    select_params = params + [limit + 1]
    items = db_query(select_sql + " LIMIT %s", tuple(select_params))
    
    # Determine if there's a next page
    has_more = len(items) > limit
    if has_more:
        items = items[:-1]
    
    # Generate cursor
    next_cursor = None
    if has_more and items:
        last_id = items[-1].get('id')
        if last_id:
            cursor_data = json.dumps({'last_id': str(last_id)})
            next_cursor = base64.b64encode(cursor_data.encode()).decode()
    
    return {
        'items': items,
        'total': total,
        'limit': limit,
        'cursor': next_cursor
    }


class db_transaction:
    """
    Context manager for database transactions with multiple operations.
    
    Usage:
        with db_transaction() as tx:
            row = tx.query_one("SELECT * FROM users WHERE id = %s", (user_id,))
            if row:
                tx.execute("UPDATE users SET status = %s WHERE id = %s", ('active', user_id))
                tx.execute("INSERT INTO logs (msg) VALUES (%s)", ('User activated',))
            # Automatically commits on exit, rolls back on exception
    """
    
    def __init__(self):
        self.db = None
        self.cursor = None
    
    def __enter__(self):
        self.db = get_db()
        self.cursor = self.db.cursor()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.db.commit()
        else:
            self.db.rollback()
        self.cursor.close()
        return False
    
    def query(self, sql: str, params: Tuple = None) -> List[Dict[str, Any]]:
        """Execute SELECT and return all rows."""
        self.cursor.execute(sql, params)
        if self.cursor.description:
            return [dict(row) for row in self.cursor.fetchall()]
        return []
    
    def query_one(self, sql: str, params: Tuple = None) -> Optional[Dict[str, Any]]:
        """Execute SELECT and return single row."""
        self.cursor.execute(sql, params)
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def execute(self, sql: str, params: Tuple = None) -> Union[int, Dict[str, Any]]:
        """Execute INSERT/UPDATE/DELETE, returns row if RETURNING clause used."""
        self.cursor.execute(sql, params)
        if self.cursor.description:
            row = self.cursor.fetchone()
            return dict(row) if row else None
        return self.cursor.rowcount
