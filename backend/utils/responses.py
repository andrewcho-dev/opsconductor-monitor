"""
Standardized API response helpers.

All API endpoints should use these functions to ensure consistent response format.
"""

from typing import Any, Optional


def success_response(data: Any = None, message: str = None, meta: dict = None) -> dict:
    """
    Create a standardized success response.
    
    Args:
        data: The response payload (can be any JSON-serializable type)
        message: Optional success message
        meta: Optional metadata (pagination, counts, etc.)
    
    Returns:
        dict: Standardized success response
        
    Example:
        >>> success_response({'id': 1, 'name': 'Device'})
        {'success': True, 'data': {'id': 1, 'name': 'Device'}}
        
        >>> success_response([1, 2, 3], meta={'total': 100, 'page': 1})
        {'success': True, 'data': [1, 2, 3], 'meta': {'total': 100, 'page': 1}}
    """
    response = {'success': True}
    
    if data is not None:
        response['data'] = data
    
    if message:
        response['message'] = message
    
    if meta:
        response['meta'] = meta
    
    return response


def error_response(code: str, message: str, details: dict = None) -> dict:
    """
    Create a standardized error response.
    
    Args:
        code: Machine-readable error code (e.g., 'DEVICE_NOT_FOUND')
        message: Human-readable error message
        details: Optional additional error details
    
    Returns:
        dict: Standardized error response
        
    Example:
        >>> error_response('DEVICE_NOT_FOUND', 'Device with IP 10.0.0.1 not found')
        {'success': False, 'error': {'code': 'DEVICE_NOT_FOUND', 'message': 'Device with IP 10.0.0.1 not found'}}
    """
    response = {
        'success': False,
        'error': {
            'code': code,
            'message': message,
        }
    }
    
    if details:
        response['error']['details'] = details
    
    return response


def paginated_response(data: list, total: int, page: int = 1, per_page: int = 50) -> dict:
    """
    Create a standardized paginated response.
    
    Args:
        data: List of items for current page
        total: Total number of items across all pages
        page: Current page number (1-indexed)
        per_page: Number of items per page
    
    Returns:
        dict: Standardized paginated response
    """
    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    
    return success_response(
        data=data,
        meta={
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
        }
    )


def list_response(data: list, total: int = None) -> dict:
    """
    Create a standardized list response with count.
    
    Args:
        data: List of items
        total: Optional total count (defaults to len(data))
    
    Returns:
        dict: Standardized list response
    """
    return success_response(
        data=data,
        meta={'count': total if total is not None else len(data)}
    )
