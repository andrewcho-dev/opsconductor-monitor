"""
Base executor interface.

All command executors should inherit from BaseExecutor and implement the execute method.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseExecutor(ABC):
    """
    Abstract base class for command executors.
    
    Executors handle the actual execution of commands against targets
    (SSH, SNMP, Ping, etc.).
    """
    
    @property
    @abstractmethod
    def executor_type(self) -> str:
        """
        Return the executor type identifier.
        
        This is used to reference the executor in job definitions.
        Examples: 'ssh', 'snmp', 'ping'
        """
        pass
    
    @abstractmethod
    def execute(
        self, 
        target: str, 
        command: str, 
        config: Dict = None
    ) -> Dict:
        """
        Execute a command against a target.
        
        Args:
            target: Target IP address or hostname
            command: Command to execute
            config: Execution configuration (credentials, timeout, etc.)
        
        Returns:
            Dict with keys:
                - success: bool
                - output: str (raw output)
                - error: str (error message if failed)
                - duration: float (execution time in seconds)
        """
        pass
    
    def validate_target(self, target: str) -> bool:
        """
        Validate that a target is reachable/valid.
        
        Override in subclass for specific validation.
        
        Args:
            target: Target to validate
        
        Returns:
            True if target is valid
        """
        return target is not None and len(target.strip()) > 0
    
    def validate_config(self, config: Dict) -> bool:
        """
        Validate execution configuration.
        
        Override in subclass for specific validation.
        
        Args:
            config: Configuration to validate
        
        Returns:
            True if config is valid
        """
        return True
    
    def get_default_config(self) -> Dict:
        """
        Get default configuration for this executor.
        
        Override in subclass to provide defaults.
        
        Returns:
            Default configuration dictionary
        """
        return {
            'timeout': 30,
            'retries': 1
        }
    
    def merge_config(self, config: Dict = None) -> Dict:
        """
        Merge provided config with defaults.
        
        Args:
            config: User-provided configuration
        
        Returns:
            Merged configuration
        """
        defaults = self.get_default_config()
        if config:
            defaults.update(config)
        return defaults
    
    def safe_execute(
        self, 
        target: str, 
        command: str, 
        config: Dict = None
    ) -> Dict:
        """
        Execute with error handling.
        
        Args:
            target: Target IP address or hostname
            command: Command to execute
            config: Execution configuration
        
        Returns:
            Execution result dict
        """
        import time
        
        start_time = time.time()
        
        try:
            if not self.validate_target(target):
                return {
                    'success': False,
                    'output': '',
                    'error': f'Invalid target: {target}',
                    'duration': 0
                }
            
            merged_config = self.merge_config(config)
            
            if not self.validate_config(merged_config):
                return {
                    'success': False,
                    'output': '',
                    'error': 'Invalid configuration',
                    'duration': 0
                }
            
            result = self.execute(target, command, merged_config)
            result['duration'] = time.time() - start_time
            return result
            
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'duration': time.time() - start_time
            }
    
    def execute_batch(
        self, 
        targets: List[str], 
        command: str, 
        config: Dict = None
    ) -> List[Dict]:
        """
        Execute command against multiple targets in parallel.
        
        Args:
            targets: List of target addresses
            command: Command to execute
            config: Execution configuration
        
        Returns:
            List of execution results
        """
        from concurrent.futures import ThreadPoolExecutor
        import os
        
        def execute_target(target):
            result = self.safe_execute(target, command, config)
            result['target'] = target
            return result
        
        # Use optimal parallelism based on system resources
        cpu_count = os.cpu_count() or 4
        max_workers = min(cpu_count * 50, len(targets), 1000)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(execute_target, targets))
        
        return results
