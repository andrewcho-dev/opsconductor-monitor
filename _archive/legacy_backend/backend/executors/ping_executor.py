"""
Ping executor.

Executes ICMP ping checks against targets.
"""

import subprocess
import platform
from typing import Dict
from .base import BaseExecutor
from .registry import register_executor


@register_executor
class PingExecutor(BaseExecutor):
    """Executor for ICMP ping checks."""
    
    @property
    def executor_type(self) -> str:
        return 'ping'
    
    def get_default_config(self) -> Dict:
        """Get default ping configuration."""
        return {
            'timeout': 5,
            'count': 1,
            'retries': 1,
        }
    
    def execute(self, target: str, command: str = None, config: Dict = None) -> Dict:
        """
        Execute a ping check against a target.
        
        Args:
            target: Target IP address or hostname
            command: Ignored for ping (uses target directly)
            config: Ping configuration (timeout, count)
        
        Returns:
            Dict with success, output, error, duration
        """
        import time
        start_time = time.time()
        
        config = config or {}
        timeout = config.get('timeout', 5)
        count = config.get('count', 1)
        
        try:
            # Build ping command based on OS
            if platform.system().lower() == 'windows':
                cmd = ['ping', '-n', str(count), '-w', str(timeout * 1000), target]
            else:
                cmd = ['ping', '-c', str(count), '-W', str(timeout), target]
            
            # Execute ping
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 5  # Extra buffer for subprocess
            )
            
            success = result.returncode == 0
            output = result.stdout
            error = result.stderr if result.stderr else None
            
            # Parse response time if successful
            response_time = None
            if success and output:
                response_time = self._parse_response_time(output)
            
            return {
                'success': success,
                'output': output,
                'error': error,
                'duration': time.time() - start_time,
                'response_time_ms': response_time,
                'reachable': success,
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': '',
                'error': f'Ping timed out after {timeout}s',
                'duration': time.time() - start_time,
                'response_time_ms': None,
                'reachable': False,
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'duration': time.time() - start_time,
                'response_time_ms': None,
                'reachable': False,
            }
    
    def _parse_response_time(self, output: str) -> float:
        """
        Parse response time from ping output.
        
        Args:
            output: Ping command output
        
        Returns:
            Response time in milliseconds or None
        """
        import re
        
        # Try to find time=X.Xms or time=X.X ms patterns
        patterns = [
            r'time[=<](\d+\.?\d*)\s*ms',
            r'time[=<](\d+\.?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass
        
        return None
    
    def is_reachable(self, target: str, timeout: int = 5) -> bool:
        """
        Quick check if target is reachable.
        
        Args:
            target: Target IP address
            timeout: Timeout in seconds
        
        Returns:
            True if target responds to ping
        """
        result = self.execute(target, config={'timeout': timeout, 'count': 1})
        return result.get('reachable', False)
