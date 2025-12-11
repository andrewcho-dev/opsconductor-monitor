"""
Base service class providing common service patterns.

All domain-specific services should inherit from this class.
"""

from typing import Any, Dict, List, Optional
from backend.utils.errors import ValidationError


class BaseService:
    """
    Base service providing common business logic patterns.
    
    Services encapsulate business logic and coordinate between:
    - Repositories (data access)
    - Other services (cross-domain operations)
    - External systems (via executors)
    """
    
    def __init__(self, repository=None):
        """
        Initialize service with optional repository.
        
        Args:
            repository: Primary repository for this service
        """
        self.repo = repository
    
    def validate_required_fields(self, data: Dict, required_fields: List[str]) -> None:
        """
        Validate that required fields are present and non-empty.
        
        Args:
            data: Dictionary to validate
            required_fields: List of required field names
        
        Raises:
            ValidationError: If any required field is missing or empty
        """
        missing = []
        for field in required_fields:
            if field not in data or data[field] is None:
                missing.append(field)
            elif isinstance(data[field], str) and not data[field].strip():
                missing.append(field)
        
        if missing:
            raise ValidationError(
                f'Missing required fields: {", ".join(missing)}',
                details={'missing_fields': missing}
            )
    
    def validate_enum_field(
        self, 
        data: Dict, 
        field: str, 
        allowed_values: List[Any],
        default: Any = None
    ) -> Any:
        """
        Validate and return an enum field value.
        
        Args:
            data: Dictionary containing the field
            field: Field name
            allowed_values: List of allowed values
            default: Default value if field not present
        
        Returns:
            The validated value
        
        Raises:
            ValidationError: If value is not in allowed values
        """
        value = data.get(field, default)
        
        if value is not None and value not in allowed_values:
            raise ValidationError(
                f'{field} must be one of: {", ".join(str(v) for v in allowed_values)}',
                field=field,
                details={'allowed_values': allowed_values}
            )
        
        return value
    
    def get_or_raise(self, id: Any) -> Dict:
        """
        Get a record by ID, raising if not found.
        
        Args:
            id: Record ID
        
        Returns:
            Record dictionary
        
        Raises:
            NotFoundError: If record not found
        """
        return self.repo.get_by_id_or_raise(id)
    
    def list_all(self, filters: Dict = None, **kwargs) -> List[Dict]:
        """
        List all records with optional filtering.
        
        Args:
            filters: Optional filters
            **kwargs: Additional arguments passed to repository
        
        Returns:
            List of records
        """
        return self.repo.get_all(filters=filters, **kwargs)
    
    def create(self, data: Dict) -> Dict:
        """
        Create a new record.
        
        Override in subclass to add validation and business logic.
        
        Args:
            data: Record data
        
        Returns:
            Created record
        """
        return self.repo.create(data)
    
    def update(self, id: Any, data: Dict) -> Dict:
        """
        Update an existing record.
        
        Override in subclass to add validation and business logic.
        
        Args:
            id: Record ID
            data: Update data
        
        Returns:
            Updated record
        """
        return self.repo.update(id, data)
    
    def delete(self, id: Any) -> bool:
        """
        Delete a record.
        
        Override in subclass to add cascade logic.
        
        Args:
            id: Record ID
        
        Returns:
            True if deleted
        """
        return self.repo.delete(id)
