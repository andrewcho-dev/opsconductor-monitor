"""
Custom exception classes for standardized error handling.

All exceptions inherit from AppError and include:
- code: Machine-readable error code (e.g., 'DEVICE_NOT_FOUND')
- message: Human-readable error message
- status_code: HTTP status code for API responses
"""


class AppError(Exception):
    """Base application error class."""
    
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
    
    def to_dict(self) -> dict:
        """Convert error to dictionary for JSON response."""
        result = {
            'code': self.code,
            'message': self.message,
        }
        if self.details:
            result['details'] = self.details
        return result


class NotFoundError(AppError):
    """Resource not found error."""
    
    def __init__(self, resource: str, identifier: str = None):
        message = f'{resource} not found'
        if identifier:
            message = f'{resource} with ID "{identifier}" not found'
        super().__init__(
            code=f'{resource.upper().replace(" ", "_")}_NOT_FOUND',
            message=message,
            status_code=404
        )


class ValidationError(AppError):
    """Input validation error."""
    
    def __init__(self, message: str, field: str = None, details: dict = None):
        super().__init__(
            code='VALIDATION_ERROR',
            message=message,
            status_code=400,
            details=details or {}
        )
        if field:
            self.details['field'] = field


class DatabaseError(AppError):
    """Database operation error."""
    
    def __init__(self, message: str, operation: str = None):
        super().__init__(
            code='DATABASE_ERROR',
            message=message,
            status_code=500,
            details={'operation': operation} if operation else {}
        )


class AuthenticationError(AppError):
    """Authentication error."""
    
    def __init__(self, message: str = 'Authentication required'):
        super().__init__(
            code='AUTHENTICATION_ERROR',
            message=message,
            status_code=401
        )


class AuthorizationError(AppError):
    """Authorization/permission error."""
    
    def __init__(self, message: str = 'Permission denied'):
        super().__init__(
            code='AUTHORIZATION_ERROR',
            message=message,
            status_code=403
        )


class ConflictError(AppError):
    """Resource conflict error (e.g., duplicate)."""
    
    def __init__(self, resource: str, message: str = None):
        super().__init__(
            code=f'{resource.upper().replace(" ", "_")}_CONFLICT',
            message=message or f'{resource} already exists',
            status_code=409
        )


class ExecutionError(AppError):
    """Job/task execution error."""
    
    def __init__(self, message: str, job_id: str = None, details: dict = None):
        super().__init__(
            code='EXECUTION_ERROR',
            message=message,
            status_code=500,
            details=details or {}
        )
        if job_id:
            self.details['job_id'] = job_id


class ConnectionError(AppError):
    """External connection error (SSH, SNMP, etc.)."""
    
    def __init__(self, target: str, protocol: str, message: str = None):
        super().__init__(
            code='CONNECTION_ERROR',
            message=message or f'Failed to connect to {target} via {protocol}',
            status_code=502,
            details={'target': target, 'protocol': protocol}
        )


class TimeoutError(AppError):
    """Operation timeout error."""
    
    def __init__(self, operation: str, timeout_seconds: int = None):
        message = f'{operation} timed out'
        if timeout_seconds:
            message = f'{operation} timed out after {timeout_seconds} seconds'
        super().__init__(
            code='TIMEOUT_ERROR',
            message=message,
            status_code=504,
            details={'timeout_seconds': timeout_seconds} if timeout_seconds else {}
        )
