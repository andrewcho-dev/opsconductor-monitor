"""
Base targeting interface.

All targeting strategies should inherit from BaseTargeting and implement the resolve method.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseTargeting(ABC):
    """
    Abstract base class for target resolution strategies.
    
    Targeting strategies resolve job configuration into a list of targets
    (IP addresses) to execute against.
    """
    
    @property
    @abstractmethod
    def targeting_type(self) -> str:
        """
        Return the targeting type identifier.
        
        This is used to reference the strategy in job definitions.
        Examples: 'database_query', 'group', 'static', 'network_range'
        """
        pass
    
    @abstractmethod
    def resolve(self, config: Dict) -> List[str]:
        """
        Resolve targeting configuration to a list of target IPs.
        
        Args:
            config: Targeting configuration from job definition
        
        Returns:
            List of target IP addresses
        """
        pass
    
    def validate_config(self, config: Dict) -> bool:
        """
        Validate targeting configuration.
        
        Override in subclass for specific validation.
        
        Args:
            config: Configuration to validate
        
        Returns:
            True if config is valid
        """
        return config is not None
    
    def get_required_fields(self) -> List[str]:
        """
        Get list of required configuration fields.
        
        Override in subclass to specify required fields.
        
        Returns:
            List of required field names
        """
        return []
    
    def safe_resolve(self, config: Dict) -> Dict:
        """
        Resolve with error handling.
        
        Args:
            config: Targeting configuration
        
        Returns:
            Dict with 'success', 'targets', and optionally 'error' keys
        """
        try:
            if not self.validate_config(config):
                return {
                    'success': False,
                    'targets': [],
                    'error': 'Invalid targeting configuration'
                }
            
            # Check required fields
            missing = []
            for field in self.get_required_fields():
                if field not in config or config[field] is None:
                    missing.append(field)
            
            if missing:
                return {
                    'success': False,
                    'targets': [],
                    'error': f'Missing required fields: {", ".join(missing)}'
                }
            
            targets = self.resolve(config)
            
            return {
                'success': True,
                'targets': targets,
                'count': len(targets)
            }
            
        except Exception as e:
            return {
                'success': False,
                'targets': [],
                'error': str(e)
            }
