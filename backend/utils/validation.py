"""
Input validation utilities.

Provides reusable validation functions for common data types and patterns.
"""

import re
from typing import Any, List, Optional, Union
from .errors import ValidationError


# Common regex patterns
IP_ADDRESS_PATTERN = re.compile(
    r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
)

CIDR_PATTERN = re.compile(
    r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)/(?:[0-9]|[1-2][0-9]|3[0-2])$'
)

UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)

HOSTNAME_PATTERN = re.compile(
    r'^(?=.{1,253}$)(?:(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)*(?!-)[A-Za-z0-9-]{1,63}(?<!-)$'
)


def validate_required(value: Any, field_name: str) -> Any:
    """
    Validate that a value is not None or empty.
    
    Args:
        value: Value to validate
        field_name: Name of the field for error message
    
    Returns:
        The value if valid
    
    Raises:
        ValidationError: If value is None or empty
    """
    if value is None:
        raise ValidationError(f'{field_name} is required', field=field_name)
    if isinstance(value, str) and not value.strip():
        raise ValidationError(f'{field_name} cannot be empty', field=field_name)
    return value


def validate_ip_address(ip: str, field_name: str = 'ip_address') -> str:
    """
    Validate an IPv4 address.
    
    Args:
        ip: IP address string
        field_name: Name of the field for error message
    
    Returns:
        The IP address if valid
    
    Raises:
        ValidationError: If IP address is invalid
    """
    if not ip or not IP_ADDRESS_PATTERN.match(ip):
        raise ValidationError(f'Invalid IP address: {ip}', field=field_name)
    return ip


def validate_cidr(cidr: str, field_name: str = 'cidr') -> str:
    """
    Validate a CIDR notation network.
    
    Args:
        cidr: CIDR string (e.g., '10.0.0.0/24')
        field_name: Name of the field for error message
    
    Returns:
        The CIDR if valid
    
    Raises:
        ValidationError: If CIDR is invalid
    """
    if not cidr or not CIDR_PATTERN.match(cidr):
        raise ValidationError(f'Invalid CIDR notation: {cidr}', field=field_name)
    return cidr


def validate_uuid(value: str, field_name: str = 'id') -> str:
    """
    Validate a UUID string.
    
    Args:
        value: UUID string
        field_name: Name of the field for error message
    
    Returns:
        The UUID string if valid
    
    Raises:
        ValidationError: If UUID is invalid
    """
    if not value or not UUID_PATTERN.match(value):
        raise ValidationError(f'Invalid UUID: {value}', field=field_name)
    return value


def validate_port(port: Union[int, str], field_name: str = 'port') -> int:
    """
    Validate a network port number.
    
    Args:
        port: Port number (int or string)
        field_name: Name of the field for error message
    
    Returns:
        The port as integer if valid
    
    Raises:
        ValidationError: If port is invalid
    """
    try:
        port_int = int(port)
    except (TypeError, ValueError):
        raise ValidationError(f'Invalid port: {port}', field=field_name)
    
    if not 1 <= port_int <= 65535:
        raise ValidationError(f'Port must be between 1 and 65535: {port}', field=field_name)
    
    return port_int


def validate_positive_int(value: Union[int, str], field_name: str) -> int:
    """
    Validate a positive integer.
    
    Args:
        value: Integer value (int or string)
        field_name: Name of the field for error message
    
    Returns:
        The value as integer if valid
    
    Raises:
        ValidationError: If value is not a positive integer
    """
    try:
        int_value = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f'{field_name} must be an integer', field=field_name)
    
    if int_value <= 0:
        raise ValidationError(f'{field_name} must be positive', field=field_name)
    
    return int_value


def validate_non_negative_int(value: Union[int, str], field_name: str) -> int:
    """
    Validate a non-negative integer (0 or positive).
    
    Args:
        value: Integer value (int or string)
        field_name: Name of the field for error message
    
    Returns:
        The value as integer if valid
    
    Raises:
        ValidationError: If value is negative
    """
    try:
        int_value = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f'{field_name} must be an integer', field=field_name)
    
    if int_value < 0:
        raise ValidationError(f'{field_name} cannot be negative', field=field_name)
    
    return int_value


def validate_enum(value: Any, allowed_values: List[Any], field_name: str) -> Any:
    """
    Validate that a value is one of the allowed values.
    
    Args:
        value: Value to validate
        allowed_values: List of allowed values
        field_name: Name of the field for error message
    
    Returns:
        The value if valid
    
    Raises:
        ValidationError: If value is not in allowed values
    """
    if value not in allowed_values:
        raise ValidationError(
            f'{field_name} must be one of: {", ".join(str(v) for v in allowed_values)}',
            field=field_name,
            details={'allowed_values': allowed_values}
        )
    return value


def validate_string_length(
    value: str, 
    field_name: str, 
    min_length: int = None, 
    max_length: int = None
) -> str:
    """
    Validate string length.
    
    Args:
        value: String to validate
        field_name: Name of the field for error message
        min_length: Minimum length (optional)
        max_length: Maximum length (optional)
    
    Returns:
        The string if valid
    
    Raises:
        ValidationError: If string length is out of bounds
    """
    if not isinstance(value, str):
        raise ValidationError(f'{field_name} must be a string', field=field_name)
    
    if min_length is not None and len(value) < min_length:
        raise ValidationError(
            f'{field_name} must be at least {min_length} characters',
            field=field_name
        )
    
    if max_length is not None and len(value) > max_length:
        raise ValidationError(
            f'{field_name} must be at most {max_length} characters',
            field=field_name
        )
    
    return value


def validate_list(value: Any, field_name: str, min_items: int = None) -> list:
    """
    Validate that a value is a list.
    
    Args:
        value: Value to validate
        field_name: Name of the field for error message
        min_items: Minimum number of items (optional)
    
    Returns:
        The list if valid
    
    Raises:
        ValidationError: If value is not a list or has too few items
    """
    if not isinstance(value, list):
        raise ValidationError(f'{field_name} must be a list', field=field_name)
    
    if min_items is not None and len(value) < min_items:
        raise ValidationError(
            f'{field_name} must have at least {min_items} items',
            field=field_name
        )
    
    return value


def validate_dict(value: Any, field_name: str, required_keys: List[str] = None) -> dict:
    """
    Validate that a value is a dictionary.
    
    Args:
        value: Value to validate
        field_name: Name of the field for error message
        required_keys: List of required keys (optional)
    
    Returns:
        The dictionary if valid
    
    Raises:
        ValidationError: If value is not a dict or missing required keys
    """
    if not isinstance(value, dict):
        raise ValidationError(f'{field_name} must be an object', field=field_name)
    
    if required_keys:
        missing = [k for k in required_keys if k not in value]
        if missing:
            raise ValidationError(
                f'{field_name} is missing required keys: {", ".join(missing)}',
                field=field_name,
                details={'missing_keys': missing}
            )
    
    return value
