"""
Serialization utilities for converting Python objects to JSON-serializable formats.

These utilities handle common types that aren't natively JSON-serializable:
- datetime objects
- Decimal objects
- UUID objects
- Database row objects
"""

from datetime import datetime, date, time
from decimal import Decimal
from typing import Any, Dict, List, Union
import uuid


def serialize_datetime(dt: Union[datetime, date, time, None]) -> str:
    """
    Serialize datetime/date/time to ISO format string.
    
    Args:
        dt: datetime, date, or time object (or None)
    
    Returns:
        ISO format string or None
    """
    if dt is None:
        return None
    return dt.isoformat()


def serialize_decimal(value: Union[Decimal, float, int, None], precision: int = None) -> float:
    """
    Serialize Decimal to float.
    
    Args:
        value: Decimal, float, or int (or None)
        precision: Optional decimal places to round to
    
    Returns:
        float or None
    """
    if value is None:
        return None
    result = float(value)
    if precision is not None:
        result = round(result, precision)
    return result


def serialize_uuid(value: Union[uuid.UUID, str, None]) -> str:
    """
    Serialize UUID to string.
    
    Args:
        value: UUID object or string (or None)
    
    Returns:
        String representation or None
    """
    if value is None:
        return None
    return str(value)


def serialize_row(row: Any) -> Dict:
    """
    Serialize a database row (dict-like object) to a plain dictionary.
    
    Handles common database row types and converts special types.
    
    Args:
        row: Database row object (psycopg2 RealDictRow, etc.)
    
    Returns:
        Plain dictionary with serialized values
    """
    if row is None:
        return None
    
    if hasattr(row, '_asdict'):
        # Named tuple
        data = row._asdict()
    elif hasattr(row, 'keys'):
        # Dict-like (RealDictRow, etc.)
        data = dict(row)
    else:
        # Already a dict or unknown type
        data = row
    
    return serialize_dict(data)


def serialize_dict(data: Dict) -> Dict:
    """
    Serialize all values in a dictionary.
    
    Args:
        data: Dictionary with potentially non-serializable values
    
    Returns:
        Dictionary with all values serialized
    """
    if data is None:
        return None
    
    result = {}
    for key, value in data.items():
        result[key] = serialize_value(value)
    return result


def serialize_value(value: Any) -> Any:
    """
    Serialize a single value to JSON-compatible format.
    
    Args:
        value: Any Python value
    
    Returns:
        JSON-serializable value
    """
    if value is None:
        return None
    
    if isinstance(value, (str, int, float, bool)):
        return value
    
    if isinstance(value, datetime):
        return value.isoformat()
    
    if isinstance(value, date):
        return value.isoformat()
    
    if isinstance(value, time):
        return value.isoformat()
    
    if isinstance(value, Decimal):
        return float(value)
    
    if isinstance(value, uuid.UUID):
        return str(value)
    
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    
    if isinstance(value, (list, tuple)):
        return [serialize_value(item) for item in value]
    
    if isinstance(value, dict):
        return serialize_dict(value)
    
    if hasattr(value, '_asdict'):
        return serialize_dict(value._asdict())
    
    if hasattr(value, 'keys'):
        return serialize_dict(dict(value))
    
    # Fallback: convert to string
    return str(value)


def serialize_rows(rows: List[Any]) -> List[Dict]:
    """
    Serialize a list of database rows.
    
    Args:
        rows: List of database row objects
    
    Returns:
        List of plain dictionaries
    """
    if rows is None:
        return []
    return [serialize_row(row) for row in rows]
