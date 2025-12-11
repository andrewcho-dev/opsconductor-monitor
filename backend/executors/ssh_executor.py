"""
SSH command executor.

Executes commands on remote devices via SSH.
"""

import socket
from typing import Dict, Optional
from ..utils.errors import ConnectionError, TimeoutError
from .base import BaseExecutor
from .registry import register_executor


@register_executor
class SSHExecutor(BaseExecutor):
    """Executor for SSH command execution."""
    
    @property
    def executor_type(self) -> str:
        return 'ssh'
    
    def get_default_config(self) -> Dict:
        """Get default SSH configuration."""
        return {
            'timeout': 30,
            'port': 22,
            'username': '',
            'password': '',
            'retries': 1,
            'look_for_keys': False,
            'allow_agent': False,
        }
    
    def validate_config(self, config: Dict) -> bool:
        """Validate SSH configuration."""
        if not config.get('username'):
            return False
        if not config.get('password'):
            return False
        return True
    
    def execute(self, target: str, command: str, config: Dict = None) -> Dict:
        """
        Execute an SSH command on a target device.
        
        Args:
            target: Target IP address or hostname
            command: Command to execute
            config: SSH configuration (username, password, port, timeout)
        
        Returns:
            Dict with success, output, error, duration
        """
        import time
        start_time = time.time()
        
        config = config or {}
        timeout = config.get('timeout', 30)
        port = config.get('port', 22)
        username = config.get('username', '')
        password = config.get('password', '')
        
        try:
            import paramiko
            
            # Create SSH client
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect
            client.connect(
                hostname=target,
                port=port,
                username=username,
                password=password,
                timeout=timeout,
                look_for_keys=config.get('look_for_keys', False),
                allow_agent=config.get('allow_agent', False),
            )
            
            # Execute command
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            
            # Read output
            output = stdout.read().decode('utf-8', errors='replace')
            error_output = stderr.read().decode('utf-8', errors='replace')
            
            # Close connection
            client.close()
            
            return {
                'success': True,
                'output': output,
                'error': error_output if error_output else None,
                'duration': time.time() - start_time,
            }
            
        except paramiko.AuthenticationException as e:
            return {
                'success': False,
                'output': '',
                'error': f'Authentication failed: {str(e)}',
                'duration': time.time() - start_time,
            }
        except paramiko.SSHException as e:
            return {
                'success': False,
                'output': '',
                'error': f'SSH error: {str(e)}',
                'duration': time.time() - start_time,
            }
        except socket.timeout:
            return {
                'success': False,
                'output': '',
                'error': f'Connection timed out after {timeout}s',
                'duration': time.time() - start_time,
            }
        except socket.error as e:
            return {
                'success': False,
                'output': '',
                'error': f'Connection error: {str(e)}',
                'duration': time.time() - start_time,
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'duration': time.time() - start_time,
            }
    
    def execute_interactive(
        self, 
        target: str, 
        commands: list, 
        config: Dict = None,
        prompt_pattern: str = None
    ) -> Dict:
        """
        Execute multiple commands in an interactive SSH session.
        
        Useful for devices that require interactive shell (like Ciena SAOS).
        
        Args:
            target: Target IP address
            commands: List of commands to execute
            config: SSH configuration
            prompt_pattern: Regex pattern to detect command prompt
        
        Returns:
            Dict with success, outputs (list), error
        """
        import time
        import re
        
        start_time = time.time()
        config = config or {}
        timeout = config.get('timeout', 30)
        port = config.get('port', 22)
        username = config.get('username', '')
        password = config.get('password', '')
        
        # Default prompt pattern for Ciena devices
        if prompt_pattern is None:
            prompt_pattern = r'[>#\$]\s*$'
        
        outputs = []
        
        try:
            import paramiko
            
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            client.connect(
                hostname=target,
                port=port,
                username=username,
                password=password,
                timeout=timeout,
                look_for_keys=config.get('look_for_keys', False),
                allow_agent=config.get('allow_agent', False),
            )
            
            # Get interactive shell
            shell = client.invoke_shell()
            shell.settimeout(timeout)
            
            # Wait for initial prompt
            self._wait_for_prompt(shell, prompt_pattern, timeout)
            
            # Execute each command
            for cmd in commands:
                shell.send(cmd + '\n')
                output = self._wait_for_prompt(shell, prompt_pattern, timeout)
                outputs.append({
                    'command': cmd,
                    'output': output,
                })
            
            client.close()
            
            return {
                'success': True,
                'outputs': outputs,
                'error': None,
                'duration': time.time() - start_time,
            }
            
        except Exception as e:
            return {
                'success': False,
                'outputs': outputs,
                'error': str(e),
                'duration': time.time() - start_time,
            }
    
    def _wait_for_prompt(self, shell, prompt_pattern: str, timeout: int) -> str:
        """
        Wait for command prompt and return accumulated output.
        
        Args:
            shell: Paramiko shell channel
            prompt_pattern: Regex pattern for prompt
            timeout: Timeout in seconds
        
        Returns:
            Accumulated output string
        """
        import re
        import time
        
        output = ''
        start = time.time()
        
        while time.time() - start < timeout:
            if shell.recv_ready():
                chunk = shell.recv(4096).decode('utf-8', errors='replace')
                output += chunk
                
                # Check if we've reached a prompt
                if re.search(prompt_pattern, output):
                    break
            else:
                time.sleep(0.1)
        
        return output
