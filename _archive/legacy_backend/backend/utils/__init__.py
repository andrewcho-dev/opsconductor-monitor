"""Backend utilities package."""

from .errors import AppError, NotFoundError, ValidationError, DatabaseError
from .responses import success_response, error_response
from .serialization import serialize_datetime, serialize_decimal
from .db import (
    db_query, db_query_one, db_execute,
    get_setting, set_setting, get_settings_by_prefix,
    clear_settings_cache, table_exists, count_rows
)
from .http import NetBoxClient, PRTGClient, MCPClient

__all__ = [
    # Errors
    'AppError',
    'NotFoundError', 
    'ValidationError',
    'DatabaseError',
    # Responses
    'success_response',
    'error_response',
    # Serialization
    'serialize_datetime',
    'serialize_decimal',
    # Database utilities
    'db_query',
    'db_query_one',
    'db_execute',
    'get_setting',
    'set_setting',
    'get_settings_by_prefix',
    'clear_settings_cache',
    'table_exists',
    'count_rows',
    # HTTP clients
    'NetBoxClient',
    'PRTGClient',
    'MCPClient',
]
