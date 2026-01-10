"""
Targeting registry for managing and accessing targeting strategies.

The registry provides a centralized way to:
- Register targeting strategies by type
- Retrieve strategies for use in job execution
- List available strategies
"""

from typing import Dict, List, Optional, Type
from .base import BaseTargeting


class TargetingRegistry:
    """
    Singleton registry for targeting strategies.
    
    Usage:
        # Register a strategy
        TargetingRegistry.register(DatabaseQueryTargeting)
        
        # Get a strategy by type
        strategy = TargetingRegistry.get('database_query')
        targets = strategy.resolve(config)
    """
    
    _strategies: Dict[str, Type[BaseTargeting]] = {}
    _instances: Dict[str, BaseTargeting] = {}
    
    @classmethod
    def register(cls, strategy_class: Type[BaseTargeting]) -> None:
        """
        Register a targeting strategy class.
        
        Args:
            strategy_class: Strategy class (must inherit from BaseTargeting)
        
        Raises:
            ValueError: If strategy_class is invalid or type already registered
        """
        if not issubclass(strategy_class, BaseTargeting):
            raise ValueError(f'{strategy_class} must inherit from BaseTargeting')
        
        # Create instance to get type
        instance = strategy_class()
        targeting_type = instance.targeting_type
        
        if targeting_type in cls._strategies:
            raise ValueError(f'Targeting "{targeting_type}" is already registered')
        
        cls._strategies[targeting_type] = strategy_class
        cls._instances[targeting_type] = instance
    
    @classmethod
    def get(cls, targeting_type: str) -> Optional[BaseTargeting]:
        """
        Get a targeting strategy instance by type.
        
        Args:
            targeting_type: Strategy type (e.g., 'database_query', 'group')
        
        Returns:
            Strategy instance or None if not found
        """
        return cls._instances.get(targeting_type)
    
    @classmethod
    def get_or_raise(cls, targeting_type: str) -> BaseTargeting:
        """
        Get a targeting strategy instance by type, raising if not found.
        
        Args:
            targeting_type: Strategy type
        
        Returns:
            Strategy instance
        
        Raises:
            ValueError: If strategy not found
        """
        strategy = cls.get(targeting_type)
        if strategy is None:
            raise ValueError(
                f'Unknown targeting type: {targeting_type}. '
                f'Available: {", ".join(cls.list_types())}'
            )
        return strategy
    
    @classmethod
    def resolve(cls, targeting_type: str, config: Dict) -> List[str]:
        """
        Resolve targets using a named strategy.
        
        Args:
            targeting_type: Strategy type
            config: Targeting configuration
        
        Returns:
            List of target IP addresses
        
        Raises:
            ValueError: If strategy not found
        """
        strategy = cls.get_or_raise(targeting_type)
        return strategy.resolve(config)
    
    @classmethod
    def safe_resolve(cls, targeting_type: str, config: Dict) -> Dict:
        """
        Resolve targets with error handling.
        
        Args:
            targeting_type: Strategy type
            config: Targeting configuration
        
        Returns:
            Dict with 'success', 'targets', and optionally 'error' keys
        """
        strategy = cls.get(targeting_type)
        if strategy is None:
            return {
                'success': False,
                'targets': [],
                'error': f'Unknown targeting type: {targeting_type}'
            }
        return strategy.safe_resolve(config)
    
    @classmethod
    def list_types(cls) -> List[str]:
        """
        List all registered targeting types.
        
        Returns:
            List of targeting types
        """
        return list(cls._strategies.keys())
    
    @classmethod
    def list_strategies(cls) -> List[Dict]:
        """
        List all registered strategies with metadata.
        
        Returns:
            List of strategy info dictionaries
        """
        return [
            {
                'type': targeting_type,
                'class': strategy_class.__name__,
                'module': strategy_class.__module__,
                'required_fields': cls._instances[targeting_type].get_required_fields()
            }
            for targeting_type, strategy_class in cls._strategies.items()
        ]
    
    @classmethod
    def is_registered(cls, targeting_type: str) -> bool:
        """
        Check if a targeting strategy is registered.
        
        Args:
            targeting_type: Strategy type
        
        Returns:
            True if strategy is registered
        """
        return targeting_type in cls._strategies
    
    @classmethod
    def unregister(cls, targeting_type: str) -> bool:
        """
        Unregister a targeting strategy.
        
        Args:
            targeting_type: Strategy type
        
        Returns:
            True if strategy was unregistered
        """
        if targeting_type in cls._strategies:
            del cls._strategies[targeting_type]
            del cls._instances[targeting_type]
            return True
        return False
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered strategies (mainly for testing)."""
        cls._strategies.clear()
        cls._instances.clear()


def register_targeting(strategy_class: Type[BaseTargeting]) -> Type[BaseTargeting]:
    """
    Decorator to register a targeting strategy class.
    
    Usage:
        @register_targeting
        class DatabaseQueryTargeting(BaseTargeting):
            ...
    """
    TargetingRegistry.register(strategy_class)
    return strategy_class
