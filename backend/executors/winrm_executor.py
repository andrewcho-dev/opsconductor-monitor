"""
WinRM command executor.

Executes commands on remote Windows devices via WinRM (Windows Remote Management).
Supports PowerShell and CMD command execution.
"""

import time
from typing import Dict, Optional, List
from .base import BaseExecutor
from .registry import register_executor


@register_executor
class WinRMExecutor(BaseExecutor):
    """Executor for WinRM command execution on Windows systems."""
    
    @property
    def executor_type(self) -> str:
        return 'winrm'
    
    def get_default_config(self) -> Dict:
        """Get default WinRM configuration."""
        return {
            'timeout': 30,
            'port': 5985,  # HTTP default, 5986 for HTTPS
            'username': '',
            'password': '',
            'domain': '',
            'transport': 'ntlm',  # ntlm, kerberos, basic, credssp
            'server_cert_validation': 'ignore',
            'read_timeout_sec': 30,
            'operation_timeout_sec': 20,
        }
    
    def validate_config(self, config: Dict) -> bool:
        """Validate WinRM configuration."""
        if not config.get('username'):
            return False
        if not config.get('password'):
            return False
        return True
    
    def _get_winrm_session(self, target: str, config: Dict):
        """
        Create a WinRM session to the target.
        
        Args:
            target: Target IP address or hostname
            config: WinRM configuration
            
        Returns:
            winrm.Session object
        """
        import winrm
        
        port = config.get('port', 5985)
        transport = config.get('transport', 'ntlm')
        username = config.get('username', '')
        password = config.get('password', '')
        domain = config.get('domain', '')
        
        # Build the endpoint URL
        scheme = 'https' if port == 5986 else 'http'
        endpoint = f'{scheme}://{target}:{port}/wsman'
        
        # Format username with domain if provided
        if domain and not '\\' in username and not '@' in username:
            username = f'{domain}\\{username}'
        
        # Create session with appropriate transport
        session = winrm.Session(
            endpoint,
            auth=(username, password),
            transport=transport,
            server_cert_validation=config.get('server_cert_validation', 'ignore'),
            read_timeout_sec=config.get('read_timeout_sec', 30),
            operation_timeout_sec=config.get('operation_timeout_sec', 20),
        )
        
        return session
    
    def execute(self, target: str, command: str, config: Dict = None) -> Dict:
        """
        Execute a CMD command on a Windows target via WinRM.
        
        Args:
            target: Target IP address or hostname
            command: CMD command to execute
            config: WinRM configuration
        
        Returns:
            Dict with success, output, error, duration
        """
        start_time = time.time()
        config = config or {}
        
        try:
            session = self._get_winrm_session(target, config)
            
            # Execute CMD command
            result = session.run_cmd(command)
            
            output = result.std_out.decode('utf-8', errors='replace') if result.std_out else ''
            error_output = result.std_err.decode('utf-8', errors='replace') if result.std_err else ''
            
            return {
                'success': result.status_code == 0,
                'output': output,
                'error': error_output if error_output else None,
                'exit_code': result.status_code,
                'duration': time.time() - start_time,
            }
            
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'exit_code': -1,
                'duration': time.time() - start_time,
            }
    
    def execute_powershell(self, target: str, script: str, config: Dict = None) -> Dict:
        """
        Execute a PowerShell script on a Windows target via WinRM.
        
        Args:
            target: Target IP address or hostname
            script: PowerShell script to execute
            config: WinRM configuration
        
        Returns:
            Dict with success, output, error, duration
        """
        start_time = time.time()
        config = config or {}
        
        try:
            session = self._get_winrm_session(target, config)
            
            # Execute PowerShell script
            result = session.run_ps(script)
            
            output = result.std_out.decode('utf-8', errors='replace') if result.std_out else ''
            error_output = result.std_err.decode('utf-8', errors='replace') if result.std_err else ''
            
            return {
                'success': result.status_code == 0,
                'output': output,
                'error': error_output if error_output else None,
                'exit_code': result.status_code,
                'duration': time.time() - start_time,
            }
            
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'exit_code': -1,
                'duration': time.time() - start_time,
            }
    
    def execute_powershell_cmdlet(
        self, 
        target: str, 
        cmdlet: str, 
        parameters: Dict = None,
        config: Dict = None
    ) -> Dict:
        """
        Execute a PowerShell cmdlet with parameters.
        
        Args:
            target: Target IP address or hostname
            cmdlet: PowerShell cmdlet name (e.g., 'Get-Service')
            parameters: Dict of parameter names and values
            config: WinRM configuration
        
        Returns:
            Dict with success, output, error, duration
        """
        # Build the PowerShell command
        ps_command = cmdlet
        
        if parameters:
            for param_name, param_value in parameters.items():
                if isinstance(param_value, bool):
                    if param_value:
                        ps_command += f' -{param_name}'
                elif isinstance(param_value, str):
                    # Escape single quotes in string values
                    escaped_value = param_value.replace("'", "''")
                    ps_command += f" -{param_name} '{escaped_value}'"
                elif isinstance(param_value, (int, float)):
                    ps_command += f' -{param_name} {param_value}'
                elif isinstance(param_value, list):
                    items = ','.join(f"'{v}'" for v in param_value)
                    ps_command += f' -{param_name} @({items})'
        
        return self.execute_powershell(target, ps_command, config)
    
    def test_connection(self, target: str, config: Dict = None) -> Dict:
        """
        Test WinRM connectivity to a target.
        
        Args:
            target: Target IP address or hostname
            config: WinRM configuration
        
        Returns:
            Dict with success, message, duration
        """
        start_time = time.time()
        config = config or {}
        
        try:
            session = self._get_winrm_session(target, config)
            
            # Simple test command
            result = session.run_cmd('hostname')
            
            if result.status_code == 0:
                hostname = result.std_out.decode('utf-8', errors='replace').strip()
                return {
                    'success': True,
                    'message': f'Connected successfully to {hostname}',
                    'hostname': hostname,
                    'duration': time.time() - start_time,
                }
            else:
                return {
                    'success': False,
                    'message': 'Connection test failed',
                    'duration': time.time() - start_time,
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': str(e),
                'duration': time.time() - start_time,
            }
    
    def get_system_info(self, target: str, config: Dict = None) -> Dict:
        """
        Get comprehensive system information from a Windows target.
        
        Args:
            target: Target IP address or hostname
            config: WinRM configuration
        
        Returns:
            Dict with system information
        """
        ps_script = '''
        $info = @{
            Hostname = $env:COMPUTERNAME
            Domain = (Get-WmiObject Win32_ComputerSystem).Domain
            OS = (Get-WmiObject Win32_OperatingSystem).Caption
            OSVersion = (Get-WmiObject Win32_OperatingSystem).Version
            OSArchitecture = (Get-WmiObject Win32_OperatingSystem).OSArchitecture
            LastBoot = (Get-WmiObject Win32_OperatingSystem).LastBootUpTime
            Manufacturer = (Get-WmiObject Win32_ComputerSystem).Manufacturer
            Model = (Get-WmiObject Win32_ComputerSystem).Model
            TotalMemoryGB = [math]::Round((Get-WmiObject Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)
            ProcessorCount = (Get-WmiObject Win32_ComputerSystem).NumberOfProcessors
            LogicalProcessors = (Get-WmiObject Win32_ComputerSystem).NumberOfLogicalProcessors
        }
        $info | ConvertTo-Json
        '''
        
        result = self.execute_powershell(target, ps_script, config)
        
        if result['success'] and result['output']:
            try:
                import json
                system_info = json.loads(result['output'])
                result['system_info'] = system_info
            except:
                pass
        
        return result
    
    def get_services(
        self, 
        target: str, 
        service_name: str = None,
        status: str = None,
        config: Dict = None
    ) -> Dict:
        """
        Get Windows services information.
        
        Args:
            target: Target IP address or hostname
            service_name: Optional service name filter (supports wildcards)
            status: Optional status filter (Running, Stopped, etc.)
            config: WinRM configuration
        
        Returns:
            Dict with services list
        """
        ps_command = 'Get-Service'
        
        if service_name:
            ps_command += f" -Name '{service_name}'"
        
        ps_command += ' | Select-Object Name, DisplayName, Status, StartType | ConvertTo-Json'
        
        result = self.execute_powershell(target, ps_command, config)
        
        if result['success'] and result['output']:
            try:
                import json
                services = json.loads(result['output'])
                # Ensure it's always a list
                if isinstance(services, dict):
                    services = [services]
                
                # Filter by status if specified
                if status:
                    services = [s for s in services if s.get('Status', {}).get('Value') == status or str(s.get('Status')) == status]
                
                result['services'] = services
            except:
                pass
        
        return result
    
    def manage_service(
        self, 
        target: str, 
        service_name: str,
        action: str,
        config: Dict = None
    ) -> Dict:
        """
        Start, stop, or restart a Windows service.
        
        Args:
            target: Target IP address or hostname
            service_name: Name of the service
            action: 'start', 'stop', or 'restart'
            config: WinRM configuration
        
        Returns:
            Dict with result
        """
        action_map = {
            'start': 'Start-Service',
            'stop': 'Stop-Service',
            'restart': 'Restart-Service',
        }
        
        if action not in action_map:
            return {
                'success': False,
                'error': f'Invalid action: {action}. Must be start, stop, or restart.',
            }
        
        ps_command = f"{action_map[action]} -Name '{service_name}' -PassThru | Select-Object Name, Status | ConvertTo-Json"
        
        return self.execute_powershell(target, ps_command, config)
    
    def get_processes(
        self, 
        target: str, 
        process_name: str = None,
        config: Dict = None
    ) -> Dict:
        """
        Get running processes on a Windows target.
        
        Args:
            target: Target IP address or hostname
            process_name: Optional process name filter
            config: WinRM configuration
        
        Returns:
            Dict with processes list
        """
        ps_command = 'Get-Process'
        
        if process_name:
            ps_command += f" -Name '{process_name}'"
        
        ps_command += ' | Select-Object Id, ProcessName, CPU, WorkingSet64, StartTime | ConvertTo-Json'
        
        result = self.execute_powershell(target, ps_command, config)
        
        if result['success'] and result['output']:
            try:
                import json
                processes = json.loads(result['output'])
                if isinstance(processes, dict):
                    processes = [processes]
                result['processes'] = processes
            except:
                pass
        
        return result
    
    def get_event_log(
        self, 
        target: str, 
        log_name: str = 'System',
        entry_type: str = None,
        newest: int = 50,
        config: Dict = None
    ) -> Dict:
        """
        Get Windows Event Log entries.
        
        Args:
            target: Target IP address or hostname
            log_name: Event log name (System, Application, Security)
            entry_type: Filter by entry type (Error, Warning, Information)
            newest: Number of newest entries to retrieve
            config: WinRM configuration
        
        Returns:
            Dict with event log entries
        """
        ps_command = f"Get-EventLog -LogName '{log_name}' -Newest {newest}"
        
        if entry_type:
            ps_command += f" -EntryType '{entry_type}'"
        
        ps_command += ' | Select-Object TimeGenerated, EntryType, Source, EventID, Message | ConvertTo-Json'
        
        result = self.execute_powershell(target, ps_command, config)
        
        if result['success'] and result['output']:
            try:
                import json
                events = json.loads(result['output'])
                if isinstance(events, dict):
                    events = [events]
                result['events'] = events
            except:
                pass
        
        return result
    
    def get_disk_space(self, target: str, config: Dict = None) -> Dict:
        """
        Get disk space information from a Windows target.
        
        Args:
            target: Target IP address or hostname
            config: WinRM configuration
        
        Returns:
            Dict with disk information
        """
        ps_script = '''
        Get-WmiObject Win32_LogicalDisk -Filter "DriveType=3" | 
        Select-Object DeviceID, 
            @{N='SizeGB';E={[math]::Round($_.Size/1GB,2)}},
            @{N='FreeSpaceGB';E={[math]::Round($_.FreeSpace/1GB,2)}},
            @{N='UsedGB';E={[math]::Round(($_.Size - $_.FreeSpace)/1GB,2)}},
            @{N='PercentFree';E={[math]::Round($_.FreeSpace/$_.Size*100,2)}} |
        ConvertTo-Json
        '''
        
        result = self.execute_powershell(target, ps_script, config)
        
        if result['success'] and result['output']:
            try:
                import json
                disks = json.loads(result['output'])
                if isinstance(disks, dict):
                    disks = [disks]
                result['disks'] = disks
            except:
                pass
        
        return result
    
    def get_network_config(self, target: str, config: Dict = None) -> Dict:
        """
        Get network configuration from a Windows target.
        
        Args:
            target: Target IP address or hostname
            config: WinRM configuration
        
        Returns:
            Dict with network configuration
        """
        ps_script = '''
        Get-NetIPConfiguration | Select-Object InterfaceAlias, 
            @{N='IPv4Address';E={$_.IPv4Address.IPAddress}},
            @{N='IPv4Gateway';E={$_.IPv4DefaultGateway.NextHop}},
            @{N='DNSServer';E={$_.DNSServer.ServerAddresses -join ','}} |
        ConvertTo-Json
        '''
        
        result = self.execute_powershell(target, ps_script, config)
        
        if result['success'] and result['output']:
            try:
                import json
                network = json.loads(result['output'])
                if isinstance(network, dict):
                    network = [network]
                result['network_config'] = network
            except:
                pass
        
        return result
    
    def reboot_system(
        self, 
        target: str, 
        force: bool = False,
        delay_seconds: int = 0,
        config: Dict = None
    ) -> Dict:
        """
        Reboot a Windows system.
        
        Args:
            target: Target IP address or hostname
            force: Force reboot even if users are logged in
            delay_seconds: Delay before reboot
            config: WinRM configuration
        
        Returns:
            Dict with result
        """
        ps_command = 'Restart-Computer'
        
        if force:
            ps_command += ' -Force'
        
        if delay_seconds > 0:
            # Use shutdown command for delayed restart
            ps_command = f'shutdown /r /t {delay_seconds}'
            return self.execute(target, ps_command, config)
        
        return self.execute_powershell(target, ps_command, config)
    
    def shutdown_system(
        self, 
        target: str, 
        force: bool = False,
        delay_seconds: int = 0,
        config: Dict = None
    ) -> Dict:
        """
        Shutdown a Windows system.
        
        Args:
            target: Target IP address or hostname
            force: Force shutdown even if users are logged in
            delay_seconds: Delay before shutdown
            config: WinRM configuration
        
        Returns:
            Dict with result
        """
        ps_command = 'Stop-Computer'
        
        if force:
            ps_command += ' -Force'
        
        if delay_seconds > 0:
            ps_command = f'shutdown /s /t {delay_seconds}'
            return self.execute(target, ps_command, config)
        
        return self.execute_powershell(target, ps_command, config)
