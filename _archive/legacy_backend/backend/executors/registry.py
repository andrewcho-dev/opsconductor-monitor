"""
Executor registry for managing and accessing command executors.

The registry provides a centralized way to:
- Register executors by type
- Retrieve executors for use in job execution
- List available executors
"""

from typing import Dict, List, Optional, Type
from .base import BaseExecutor


class ExecutorRegistry:
    """
    Singleton registry for command executors.
    
    Usage:
        # Register an executor
        ExecutorRegistry.register(SSHExecutor)
        
        # Get an executor by type
        executor = ExecutorRegistry.get('ssh')
        result = executor.execute(target, command, config)
    """
    
    _executors: Dict[str, Type[BaseExecutor]] = {}
    _instances: Dict[str, BaseExecutor] = {}
    
    @classmethod
    def register(cls, executor_class: Type[BaseExecutor]) -> None:
        """
        Register an executor class.
        
        Args:
            executor_class: Executor class (must inherit from BaseExecutor)
        
        Raises:
            ValueError: If executor_class is invalid or type already registered
        """
        if not issubclass(executor_class, BaseExecutor):
            raise ValueError(f'{executor_class} must inherit from BaseExecutor')
        
        # Create instance to get type
        instance = executor_class()
        executor_type = instance.executor_type
        
        if executor_type in cls._executors:
            raise ValueError(f'Executor "{executor_type}" is already registered')
        
        cls._executors[executor_type] = executor_class
        cls._instances[executor_type] = instance
    
    @classmethod
    def get(cls, executor_type: str) -> Optional[BaseExecutor]:
        """
        Get an executor instance by type.
        
        Args:
            executor_type: Executor type (e.g., 'ssh', 'snmp')
        
        Returns:
            Executor instance or None if not found
        """
        return cls._instances.get(executor_type)
    
    @classmethod
    def get_or_raise(cls, executor_type: str) -> BaseExecutor:
        """
        Get an executor instance by type, raising if not found.
        
        Args:
            executor_type: Executor type
        
        Returns:
            Executor instance
        
        Raises:
            ValueError: If executor not found
        """
        executor = cls.get(executor_type)
        if executor is None:
            raise ValueError(
                f'Unknown executor: {executor_type}. '
                f'Available: {", ".join(cls.list_types())}'
            )
        return executor
    
    @classmethod
    def execute(
        cls, 
        executor_type: str, 
        target: str, 
        command: str, 
        config: Dict = None
    ) -> Dict:
        """
        Execute a command using a named executor.
        
        Args:
            executor_type: Executor type
            target: Target address
            command: Command to execute
            config: Execution configuration
        
        Returns:
            Execution result dictionary
        
        Raises:
            ValueError: If executor not found
        """
        executor = cls.get_or_raise(executor_type)
        return executor.safe_execute(target, command, config)
    
    @classmethod
    def list_types(cls) -> List[str]:
        """
        List all registered executor types.
        
        Returns:
            List of executor types
        """
        return list(cls._executors.keys())
    
    @classmethod
    def list_executors(cls) -> List[Dict]:
        """
        List all registered executors with metadata.
        
        Returns:
            List of executor info dictionaries
        """
        return [
            {
                'type': executor_type,
                'class': executor_class.__name__,
                'module': executor_class.__module__,
            }
            for executor_type, executor_class in cls._executors.items()
        ]
    
    @classmethod
    def is_registered(cls, executor_type: str) -> bool:
        """
        Check if an executor is registered.
        
        Args:
            executor_type: Executor type
        
        Returns:
            True if executor is registered
        """
        return executor_type in cls._executors
    
    @classmethod
    def unregister(cls, executor_type: str) -> bool:
        """
        Unregister an executor.
        
        Args:
            executor_type: Executor type
        
        Returns:
            True if executor was unregistered
        """
        if executor_type in cls._executors:
            del cls._executors[executor_type]
            del cls._instances[executor_type]
            return True
        return False
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered executors (mainly for testing)."""
        cls._executors.clear()
        cls._instances.clear()


def register_executor(executor_class: Type[BaseExecutor]) -> Type[BaseExecutor]:
    """
    Decorator to register an executor class.
    
    Usage:
        @register_executor
        class SSHExecutor(BaseExecutor):
            ...
    """
    ExecutorRegistry.register(executor_class)
    return executor_class
