"""
Job Executor Service.

Executes job definitions using the modular executor, parser, and targeting systems.
This replaces the monolithic generic_job_scheduler.py.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..executors import ExecutorRegistry, SSHExecutor, PingExecutor, SNMPExecutor, DiscoveryExecutor
from ..parsers.registry import ParserRegistry
from ..targeting import TargetingRegistry
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from ..config.constants import ACTION_TYPES, JOB_STATUS_SUCCESS, JOB_STATUS_FAILED
from .credential_service import get_credential_service

logger = logging.getLogger(__name__)


class JobExecutor:
    """
    Executes job definitions.
    
    Coordinates between targeting, execution, parsing, and database operations.
    """
    
    def __init__(self, db_manager=None, task_id: str = None, execution_id: int = None):
        """
        Initialize job executor.
        
        Args:
            db_manager: Optional database manager for DB operations
            task_id: Celery task ID for audit logging
            execution_id: Execution record ID for audit logging
        """
        self.db = db_manager
        self.task_id = task_id
        self.execution_id = execution_id
        self.audit_repo = None
        
        # Initialize audit repository if db available
        if db_manager:
            from ..repositories.audit_repo import JobAuditRepository
            self.audit_repo = JobAuditRepository(db_manager)
        
        # Ensure executors are registered
        self._ensure_executors_registered()
    
    def _ensure_executors_registered(self):
        """Ensure all executors are registered."""
        # Import to trigger registration
        from ..executors import SSHExecutor, PingExecutor, SNMPExecutor
    
    def _get_credentials_for_target(self, target: str, credential_type: str, job_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get credentials for a target, supporting both local vault credentials and enterprise auth.
        
        Resolution order:
        1. Job config specifies a credential by name
        2. Device has assigned credentials (local or enterprise auth)
        3. Default credential of the type from vault
        4. Fallback to job config or settings
        
        Args:
            target: Target IP address or hostname
            credential_type: Type of credential (ssh, snmp, etc.)
            job_config: Job configuration that may contain inline credentials
        
        Returns:
            Credential data dictionary with keys like username, password, etc.
            For enterprise auth, also includes auth_method and server_config.
        """
        try:
            cred_service = get_credential_service()
            
            # First, check if job config specifies a credential by name
            credential_name = job_config.get(f'{credential_type}_credential')
            if credential_name:
                cred = cred_service.get_credential_by_name(credential_name, include_secret=True)
                if cred and cred.get('secret_data'):
                    logger.debug(f"Using named credential '{credential_name}' for {target}")
                    cred_service.log_usage(
                        credential_id=cred['id'],
                        credential_name=cred['name'],
                        used_by=job_config.get('name', 'job'),
                        used_for=target,
                        success=True
                    )
                    return cred['secret_data']
            
            # Second, try resolve_device_credentials which handles both local and enterprise auth
            resolved = cred_service.resolve_device_credentials(
                device_ip=target,
                credential_type=credential_type,
                include_secret=True
            )
            if resolved:
                auth_method = resolved.get('auth_method', 'local')
                credentials = resolved.get('credentials', {})
                
                if auth_method != 'local':
                    # Enterprise auth - log and return with auth context
                    logger.info(f"Using {auth_method} enterprise auth for {target}")
                    # For enterprise auth, the credentials contain username/password
                    # that will be validated by the enterprise server when used
                    credentials['_auth_method'] = auth_method
                    credentials['_server_config'] = resolved.get('server_config', {})
                else:
                    logger.debug(f"Using device-assigned credential for {target}")
                
                # Log usage
                if resolved.get('credential_id'):
                    cred_service.log_usage(
                        credential_id=resolved['credential_id'],
                        credential_name=resolved.get('credential_name', 'unknown'),
                        used_by=job_config.get('name', 'job'),
                        used_for=target,
                        success=True
                    )
                
                return credentials
            
            # Third, fallback to legacy method - check for credentials assigned to this target
            target_creds = cred_service.get_credentials_for_device(
                ip_address=target,
                credential_type=credential_type,
                include_secret=True
            )
            if target_creds:
                cred = target_creds[0]  # Highest priority
                logger.debug(f"Using device-assigned credential '{cred['name']}' for {target}")
                cred_service.log_usage(
                    credential_id=cred['id'],
                    credential_name=cred['name'],
                    used_by=job_config.get('name', 'job'),
                    used_for=target,
                    success=True
                )
                return cred.get('secret_data', {})
            
            # Third, check for a default credential of this type
            all_creds = cred_service.list_credentials(credential_type=credential_type)
            if all_creds:
                # Use the first one as default
                cred = cred_service.get_credential(all_creds[0]['id'], include_secret=True)
                if cred and cred.get('secret_data'):
                    logger.debug(f"Using default credential '{cred['name']}' for {target}")
                    cred_service.log_usage(
                        credential_id=cred['id'],
                        credential_name=cred['name'],
                        used_by=job_config.get('name', 'job'),
                        used_for=target,
                        success=True
                    )
                    return cred['secret_data']
        except Exception as e:
            logger.warning(f"Error getting credentials from vault: {e}")
        
        # Fallback to job config or settings
        logger.debug(f"No vault credentials found for {target}, using job config/settings")
        return {}
    
    def _log_audit(self, event_type: str, **kwargs):
        """Log an audit event if audit repository is available."""
        if self.audit_repo:
            try:
                self.audit_repo.log_event(
                    event_type=event_type,
                    execution_id=self.execution_id,
                    task_id=self.task_id,
                    **kwargs
                )
            except Exception as e:
                logger.warning(f"Failed to log audit event: {e}")
    
    def execute_job(self, job_definition: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a complete job definition.
        
        Args:
            job_definition: Job definition with actions
        
        Returns:
            Execution result dictionary
        """
        start_time = datetime.now()
        job_name = job_definition.get('name')
        
        result = {
            'job_id': job_definition.get('id') or job_definition.get('job_id'),
            'job_name': job_name,
            'job_definition_id': job_definition.get('job_definition_id'),
            'started_at': start_time.isoformat(),
            'actions_completed': 0,
            'total_actions': len(job_definition.get('actions', [])),
            'errors': [],
            'audit_events': [],  # Track audit event IDs for reference
        }
        
        # Extract user attribution if present
        triggered_by = job_definition.get('config', {}).get('triggered_by') or job_definition.get('triggered_by')
        if triggered_by:
            result['triggered_by'] = triggered_by
        
        # Log job started
        self._log_audit('job_started', details={
            'job_name': job_name,
            'job_id': result['job_id'],
            'total_actions': result['total_actions'],
            'triggered_by': triggered_by
        })
        
        try:
            actions = job_definition.get('actions', [])
            config = job_definition.get('config', {})
            
            for i, action in enumerate(actions):
                action_type = action.get('type', f'action_{i}')
                action_name = action.get('name', action_type)
                
                # Log action started
                self._log_audit('action_started', 
                    action_name=action_name,
                    action_index=i,
                    details={'action_type': action_type, 'config': action.get('execution', {})}
                )
                
                try:
                    action_result = self._execute_action(action, config, action_name, i)
                    result[f'action_{action_name}'] = action_result
                    result['actions_completed'] += 1
                    
                    # Log action completed
                    self._log_audit('action_completed',
                        action_name=action_name,
                        action_index=i,
                        success=not action_result.get('error'),
                        error_message=action_result.get('error'),
                        details={
                            'targets_processed': action_result.get('targets_processed', 0),
                            'successful_results': action_result.get('successful_results', 0)
                        }
                    )
                    
                    if action_result.get('error'):
                        result['errors'].append(f"{action_type}: {action_result['error']}")
                        
                except Exception as e:
                    error_msg = f"{action_type}: {str(e)}"
                    result['errors'].append(error_msg)
                    result[f'action_{action_name}'] = {'error': str(e)}
                    
                    # Log action error
                    self._log_audit('action_completed',
                        action_name=action_name,
                        action_index=i,
                        success=False,
                        error_message=str(e)
                    )
                    logger.exception(f"Action {action_type} failed")
        
        except Exception as e:
            result['errors'].append(f"Job execution failed: {str(e)}")
            self._log_audit('error', error_message=str(e), details={'phase': 'job_execution'})
            logger.exception("Job execution failed")
        
        finally:
            end_time = datetime.now()
            result['finished_at'] = end_time.isoformat()
            result['duration_seconds'] = (end_time - start_time).total_seconds()
            result['status'] = JOB_STATUS_SUCCESS if not result['errors'] else JOB_STATUS_FAILED
            
            # Log job completed
            self._log_audit('job_completed',
                success=result['status'] == JOB_STATUS_SUCCESS,
                error_message='; '.join(result['errors']) if result['errors'] else None,
                details={
                    'duration_seconds': result['duration_seconds'],
                    'actions_completed': result['actions_completed'],
                    'total_actions': result['total_actions']
                }
            )
        
        return result
    
    def _execute_action(
        self, 
        action: Dict[str, Any], 
        job_config: Dict[str, Any],
        action_name: str = None,
        action_index: int = None
    ) -> Dict[str, Any]:
        """
        Execute a single action.
        
        Args:
            action: Action definition
            job_config: Job-level configuration
            action_name: Name of the action for audit logging
            action_index: Index of the action for audit logging
        
        Returns:
            Action result dictionary
        """
        action_type = action.get('type')
        
        # Get targets for this action
        targets = self._resolve_targets(action, job_config)
        
        if not targets:
            return {
                'success': False,
                'error': 'No targets resolved',
                'targets_count': 0,
            }
        
        # Execute based on action type
        if action_type == 'ssh_command':
            return self._execute_ssh_action(targets, action, job_config, action_name)
        elif action_type == 'ping':
            return self._execute_ping_action(targets, action, job_config, action_name)
        elif action_type == 'snmp':
            return self._execute_snmp_action(targets, action, job_config, action_name)
        elif action_type == 'discovery':
            return self._execute_discovery_action(targets, action, job_config, action_name)
        elif action_type == 'database':
            return self._execute_database_action(targets, action, job_config, action_name)
        else:
            return {
                'success': False,
                'error': f'Unknown action type: {action_type}',
            }
    
    def _resolve_targets(self, action: Dict[str, Any], job_config: Dict[str, Any]) -> List[str]:
        """
        Resolve targets for an action.
        
        Args:
            action: Action definition with targeting config
            job_config: Job-level configuration
        
        Returns:
            List of target IP addresses
        """
        targeting = action.get('targeting', {})
        source = targeting.get('source', 'static')
        
        # Merge job config into targeting config
        config = {**job_config, **targeting}
        
        try:
            return TargetingRegistry.resolve(source, config)
        except Exception as e:
            logger.error(f"Target resolution failed: {e}")
            return []
    
    def _execute_ssh_action(
        self, 
        targets: List[str], 
        action: Dict[str, Any], 
        job_config: Dict[str, Any],
        action_name: str = None
    ) -> Dict[str, Any]:
        """Execute SSH command action."""
        execution = action.get('execution', {})
        commands = execution.get('commands', [])
        
        if not commands:
            command = execution.get('command')
            if command:
                commands = [{'command': command}]
        
        results = []
        success_count = 0
        
        def execute_ssh_target(target):
            target_result = {
                'target': target,
                'commands': [],
                'success': True,
            }
            
            try:
                # Get SSH credentials from vault, then job config, then settings
                vault_creds = self._get_credentials_for_target(target, 'ssh', job_config)
                
                ssh_config = {
                    'username': vault_creds.get('username') or job_config.get('ssh_username') or self._get_setting('ssh_username'),
                    'password': vault_creds.get('password') or job_config.get('ssh_password') or self._get_setting('ssh_password'),
                    'port': vault_creds.get('port') or job_config.get('ssh_port') or self._get_setting('ssh_port', 22),
                    'timeout': job_config.get('timeout', 30),
                    'private_key': vault_creds.get('private_key'),
                    'passphrase': vault_creds.get('passphrase'),
                }
                
                executor = SSHExecutor()
                
                for cmd_config in commands:
                    cmd = cmd_config.get('command', '')
                    parser_name = cmd_config.get('parser')
                    
                    # Execute command
                    exec_result = executor.execute(target, cmd, ssh_config)
                    
                    cmd_result = {
                        'command': cmd,
                        'success': exec_result.get('success', False),
                        'output': exec_result.get('output', ''),
                        'error': exec_result.get('error'),
                    }
                    
                    # Parse output if parser specified
                    if parser_name and exec_result.get('success'):
                        try:
                            parsed = ParserRegistry.parse(
                                parser_name, 
                                exec_result.get('output', ''),
                                {'ip_address': target}
                            )
                            cmd_result['parsed'] = parsed
                        except Exception as e:
                            cmd_result['parse_error'] = str(e)
                    
                    target_result['commands'].append(cmd_result)
                    
                    if not exec_result.get('success'):
                        target_result['success'] = False
                    
            except Exception as e:
                target_result['success'] = False
                target_result['error'] = str(e)
            
            return target_result
        
        # Execute SSH commands in parallel
        cpu_count = os.cpu_count() or 4
        max_workers = min(cpu_count * 50, len(targets), 1000)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_results = list(executor.map(execute_ssh_target, targets))
        
        for target_result in future_results:
            results.append(target_result)
            if target_result['success']:
                success_count += 1
        
        return {
            'success': success_count > 0,
            'targets_count': len(targets),
            'success_count': success_count,
            'failed_count': len(targets) - success_count,
            'results': results,
        }
    
    def _execute_ping_action(
        self, 
        targets: List[str], 
        action: Dict[str, Any], 
        job_config: Dict[str, Any],
        action_name: str = None
    ) -> Dict[str, Any]:
        """Execute ping action in parallel."""
        execution = action.get('execution', {})
        
        ping_config = {
            'timeout': execution.get('timeout', 5),
            'count': execution.get('count', 1),
        }
        
        def ping_target(target):
            executor = PingExecutor()
            result = executor.execute(target, config=ping_config)
            return {
                'target': target,
                'reachable': result.get('reachable', False),
                'response_time_ms': result.get('response_time_ms'),
            }
        
        # Execute pings in parallel
        cpu_count = os.cpu_count() or 4
        max_workers = min(cpu_count * 50, len(targets), 1000)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(ping_target, targets))
        
        online_count = sum(1 for r in results if r.get('reachable'))
        
        return {
            'success': True,
            'targets_count': len(targets),
            'online_count': online_count,
            'offline_count': len(targets) - online_count,
            'results': results,
        }
    
    def _execute_snmp_action(
        self, 
        targets: List[str], 
        action: Dict[str, Any], 
        job_config: Dict[str, Any],
        action_name: str = None
    ) -> Dict[str, Any]:
        """Execute SNMP action in parallel."""
        execution = action.get('execution', {})
        oid = execution.get('oid', '1.3.6.1.2.1.1.1.0')
        
        def snmp_target(target):
            # Get SNMP credentials from vault, then job config, then settings
            vault_creds = self._get_credentials_for_target(target, 'snmp', job_config)
            
            snmp_config = {
                'community': vault_creds.get('community') or job_config.get('snmp_community') or self._get_setting('snmp_community', 'public'),
                'version': vault_creds.get('version', '2c'),
                'timeout': execution.get('timeout', 5),
                # SNMPv3 fields
                'security_name': vault_creds.get('security_name'),
                'auth_protocol': vault_creds.get('auth_protocol'),
                'auth_password': vault_creds.get('auth_password'),
                'priv_protocol': vault_creds.get('priv_protocol'),
                'priv_password': vault_creds.get('priv_password'),
            }
            
            executor = SNMPExecutor()
            result = executor.execute(target, oid, snmp_config)
            
            return {
                'target': target,
                'success': result.get('success', False),
                'value': result.get('output'),
                'error': result.get('error'),
            }
        
        # Execute SNMP queries in parallel
        cpu_count = os.cpu_count() or 4
        max_workers = min(cpu_count * 50, len(targets), 1000)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(snmp_target, targets))
        
        success_count = sum(1 for r in results if r.get('success'))
        
        return {
            'success': success_count > 0,
            'targets_count': len(targets),
            'success_count': success_count,
            'results': results,
        }
    
    def _execute_discovery_action(
        self, 
        targets: List[str], 
        action: Dict[str, Any], 
        job_config: Dict[str, Any],
        action_name: str = None
    ) -> Dict[str, Any]:
        """Execute network discovery action with NetBox sync."""
        execution = action.get('execution', {})
        
        # Build discovery config
        discovery_config = {
            'ping_timeout': execution.get('ping_timeout', 2),
            'snmp_community': execution.get('snmp_community') or job_config.get('snmp_community', 'public'),
            'snmp_timeout': execution.get('snmp_timeout', 3),
            'sync_to_netbox': execution.get('sync_to_netbox', True),
            'netbox_site_id': execution.get('netbox_site_id'),
            'netbox_role_id': execution.get('netbox_role_id'),
            'netbox_device_type_id': execution.get('netbox_device_type_id'),
            'max_workers': execution.get('max_workers', 20),
        }
        
        executor = DiscoveryExecutor()
        
        # Check if targets is a network range or list of IPs
        if len(targets) == 1 and '/' in targets[0]:
            # Single network range - use execute_range
            result = executor.execute_range(targets[0], discovery_config)
            return {
                'success': result.get('success', False),
                'network': targets[0],
                'total_ips': result.get('total_ips', 0),
                'online_count': result.get('online_count', 0),
                'snmp_responding_count': result.get('snmp_responding_count', 0),
                'netbox_synced_count': result.get('netbox_synced_count', 0),
                'devices': result.get('devices', []),
            }
        else:
            # List of individual IPs - execute in parallel
            def discover_target(target):
                return executor.execute(target, discovery_config)
            
            cpu_count = os.cpu_count() or 4
            max_workers = min(cpu_count * 50, len(targets), 1000)
            
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                results = list(pool.map(discover_target, targets))
            
            online_count = sum(1 for r in results if r.get('ping_status') == 'online')
            snmp_count = sum(1 for r in results if r.get('snmp_status') == 'responding')
            netbox_count = sum(1 for r in results if r.get('netbox_synced'))
            
            return {
                'success': True,
                'targets_count': len(targets),
                'online_count': online_count,
                'snmp_responding_count': snmp_count,
                'netbox_synced_count': netbox_count,
                'devices': results,
            }
    
    def _execute_database_action(
        self, 
        targets: List[str], 
        action: Dict[str, Any], 
        job_config: Dict[str, Any],
        action_name: str = None
    ) -> Dict[str, Any]:
        """Execute database action (store results)."""
        database = action.get('database', {})
        tables = database.get('tables', [])
        
        if not self.db:
            return {
                'success': False,
                'error': 'No database connection available',
            }
        
        results = []
        
        for table_config in tables:
            table_name = table_config.get('table')
            operation = table_config.get('operation', 'upsert')
            
            # This would be expanded based on the specific table operations needed
            results.append({
                'table': table_name,
                'operation': operation,
                'success': True,
            })
        
        return {
            'success': True,
            'tables_processed': len(tables),
            'results': results,
        }
    
    def _get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        import os
        import json
        
        settings_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'settings.json'
        )
        
        try:
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    return settings.get(key, default)
        except:
            pass
        
        return default
