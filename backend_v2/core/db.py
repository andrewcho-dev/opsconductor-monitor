"""
Database Layer

Single module for ALL database access. No other code touches psycopg2 directly.
Simple, clean, one way to do things.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from contextlib import contextmanager
from functools import lru_cache

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool

logger = logging.getLogger(__name__)

# Connection pool (thread-safe)
_pool: Optional[pool.ThreadedConnectionPool] = None


def _get_pool() -> pool.ThreadedConnectionPool:
    """Get or create connection pool."""
    global _pool
    if _pool is None:
        _pool = pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=20,
            host=os.environ.get('PG_HOST', 'localhost'),
            port=os.environ.get('PG_PORT', '5432'),
            database=os.environ.get('PG_DATABASE', 'opsconductor_v2'),
            user=os.environ.get('PG_USER', 'postgres'),
            password=os.environ.get('PG_PASSWORD', 'postgres'),
            cursor_factory=RealDictCursor
        )
        logger.info("Database connection pool initialized")
    return _pool


@contextmanager
def get_connection():
    """Get a connection from the pool (context manager)."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


@contextmanager
def get_cursor():
    """Get a cursor (context manager with auto-commit)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def query(sql: str, params: Tuple = None) -> List[Dict[str, Any]]:
    """
    Execute SELECT query, return all rows as list of dicts.
    
    Example:
        users = query("SELECT * FROM users WHERE role = %s", ('admin',))
    """
    with get_cursor() as cursor:
        cursor.execute(sql, params)
        if cursor.description:
            return [dict(row) for row in cursor.fetchall()]
        return []


def query_one(sql: str, params: Tuple = None) -> Optional[Dict[str, Any]]:
    """
    Execute SELECT query, return single row or None.
    
    Example:
        user = query_one("SELECT * FROM users WHERE id = %s", (123,))
    """
    with get_cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None


def execute(sql: str, params: Tuple = None) -> Union[int, Dict[str, Any]]:
    """
    Execute INSERT/UPDATE/DELETE. Returns row count, or row if RETURNING clause.
    
    Example:
        affected = execute("UPDATE users SET status = %s WHERE id = %s", ('active', 123))
        new_row = execute("INSERT INTO users (name) VALUES (%s) RETURNING *", ('John',))
    """
    with get_cursor() as cursor:
        cursor.execute(sql, params)
        if cursor.description:
            row = cursor.fetchone()
            return dict(row) if row else None
        return cursor.rowcount


def execute_many(sql: str, params_list: List[Tuple]) -> int:
    """
    Execute same SQL with multiple parameter sets.
    
    Example:
        execute_many("INSERT INTO logs (msg) VALUES (%s)", [('msg1',), ('msg2',)])
    """
    with get_cursor() as cursor:
        cursor.executemany(sql, params_list)
        return cursor.rowcount


# Settings cache
_settings_cache: Dict[str, Any] = {}


def get_setting(key: str, default: Any = None) -> Any:
    """
    Get system setting (cached).
    
    Example:
        url = get_setting('netbox_url')
    """
    if key in _settings_cache:
        return _settings_cache[key]
    
    row = query_one("SELECT value FROM system_settings WHERE key = %s", (key,))
    value = row['value'] if row else default
    _settings_cache[key] = value
    return value


def set_setting(key: str, value: Any) -> None:
    """
    Set system setting (upsert).
    
    Example:
        set_setting('netbox_url', 'http://netbox.local')
    """
    execute("""
        INSERT INTO system_settings (key, value, updated_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = NOW()
    """, (key, str(value), str(value)))
    
    _settings_cache[key] = value


def clear_settings_cache() -> None:
    """Clear settings cache."""
    global _settings_cache
    _settings_cache = {}


def table_exists(table_name: str) -> bool:
    """Check if table exists."""
    row = query_one("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = %s
        ) as exists
    """, (table_name,))
    return row['exists'] if row else False


def close_pool() -> None:
    """Close all connections in pool (call on shutdown)."""
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None
        logger.info("Database connection pool closed")
