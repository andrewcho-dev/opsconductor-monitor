"""
SSH Node Executors

Executors for SSH command execution.
"""

from typing import Dict, List, Any
from ..logging_service import get_logger, LogSource

logger = get_logger(__name__, LogSource.SSH)


class SSHCommandExecutor:
    """Executor for SSH command nodes."""
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """
        Execute an SSH command on a remote host.
        
        Args:
            node: Node definition with parameters
            context: Execution context
        
        Returns:
            Command output and status
        """
        params = node.get('data', {}).get('parameters', {})
        target = params.get('target', '')
        command = params.get('command', '')
        username = params.get('username', 'admin')
        password = params.get('password', '')
        port = int(params.get('port', 22))
        timeout = int(params.get('timeout', 30))
        
        if not target:
            # Try to get target from context
            targets = context.get('variables', {}).get('online', [])
            if targets:
                target = targets[0]
        
        if not target:
            return {'error': 'No target specified', 'output': ''}
        
        if not command:
            return {'error': 'No command specified', 'output': ''}
        
        logger.info(
            f"Executing SSH command on {target}:{port}",
            device_ip=target,
            category='command',
            details={'command': command[:100], 'username': username}
        )
        
        try:
            result = self._execute_ssh(target, port, username, password, command, timeout)
            
            if result.get('success'):
                logger.info(
                    f"SSH command succeeded on {target}",
                    device_ip=target,
                    category='command',
                    details={'exit_code': result.get('exit_code')}
                )
            else:
                logger.warning(
                    f"SSH command failed on {target}: {result.get('error', 'unknown error')}",
                    device_ip=target,
                    category='command',
                    details={'error': result.get('error'), 'exit_code': result.get('exit_code')}
                )
            
            return result
        except ImportError:
            return {
                'target': target,
                'error': 'paramiko library not installed',
                'output': '',
                'exit_code': -1,
            }
    
    def _execute_ssh(self, target: str, port: int, username: str, password: str, 
                     command: str, timeout: int) -> Dict:
        """Execute SSH command using paramiko."""
        try:
            import paramiko
            
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                client.connect(
                    hostname=target,
                    port=port,
                    username=username,
                    password=password,
                    timeout=timeout,
                    allow_agent=False,
                    look_for_keys=False,
                )
                
                stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
                
                output = stdout.read().decode('utf-8', errors='replace')
                error_output = stderr.read().decode('utf-8', errors='replace')
                exit_code = stdout.channel.recv_exit_status()
                
                return {
                    'target': target,
                    'command': command,
                    'output': output,
                    'stderr': error_output,
                    'exit_code': exit_code,
                    'success': exit_code == 0,
                }
            finally:
                client.close()
                
        except paramiko.AuthenticationException:
            return {
                'target': target,
                'command': command,
                'error': 'Authentication failed',
                'output': '',
                'exit_code': -1,
                'success': False,
            }
        except paramiko.SSHException as e:
            return {
                'target': target,
                'command': command,
                'error': f'SSH error: {str(e)}',
                'output': '',
                'exit_code': -1,
                'success': False,
            }
        except Exception as e:
            return {
                'target': target,
                'command': command,
                'error': str(e),
                'output': '',
                'exit_code': -1,
                'success': False,
            }
