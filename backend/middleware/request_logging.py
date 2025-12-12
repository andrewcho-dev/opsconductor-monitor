"""
Request Logging Middleware

Automatically logs all HTTP requests and responses with timing,
status codes, and request context.
"""

import time
import uuid
from flask import request, g
from functools import wraps

from ..services.logging_service import logging_service, get_logger, LogSource

logger = get_logger(__name__, LogSource.API)


def init_request_logging(app):
    """
    Initialize request logging middleware for a Flask app.
    
    Args:
        app: Flask application instance
    """
    
    @app.before_request
    def before_request():
        """Set up request context and timing."""
        g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        g.request_start_time = time.time()
        
        # Set logging context
        g.log_context = {
            'request_id': g.request_id,
            'ip_address': request.remote_addr,
        }
    
    @app.after_request
    def after_request(response):
        """Log completed request."""
        # Calculate duration
        duration_ms = None
        if hasattr(g, 'request_start_time'):
            duration_ms = int((time.time() - g.request_start_time) * 1000)
        
        # Skip logging for static files and health checks
        if request.path.startswith('/static') or request.path == '/api/system/health':
            return response
        
        # Determine log level based on status code
        status_code = response.status_code
        if status_code >= 500:
            log_level = 'error'
        elif status_code >= 400:
            log_level = 'warning'
        else:
            log_level = 'info'
        
        # Build log message
        message = f"{request.method} {request.path} {status_code}"
        
        # Log the request
        log_func = getattr(logger, log_level)
        log_func(
            message,
            category='request',
            status_code=status_code,
            duration_ms=duration_ms,
            details={
                'method': request.method,
                'path': request.path,
                'query_string': request.query_string.decode('utf-8') if request.query_string else None,
                'content_length': request.content_length,
                'user_agent': request.user_agent.string if request.user_agent else None,
            }
        )
        
        # Add request ID to response headers
        response.headers['X-Request-ID'] = g.get('request_id', '')
        
        return response
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Log unhandled exceptions."""
        logger.exception(
            f"Unhandled exception: {str(error)}",
            category='exception',
            details={
                'method': request.method,
                'path': request.path,
                'error_type': type(error).__name__,
            }
        )
        # Re-raise to let Flask handle the response
        raise error


def log_operation(operation_name: str, source: str = LogSource.API):
    """
    Decorator to log function execution with timing.
    
    Usage:
        @log_operation("fetch_devices")
        def get_devices():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_logger = get_logger(func.__module__, source)
            start_time = time.time()
            
            op_logger.debug(
                f"Starting operation: {operation_name}",
                category='operation',
            )
            
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                op_logger.info(
                    f"Completed operation: {operation_name}",
                    category='operation',
                    duration_ms=duration_ms,
                )
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                op_logger.error(
                    f"Failed operation: {operation_name} - {str(e)}",
                    category='operation',
                    duration_ms=duration_ms,
                    details={'error': str(e), 'error_type': type(e).__name__},
                )
                raise
        
        return wrapper
    return decorator
