#!/usr/bin/env python3
"""Generic Job Scheduler - Extracted from hardcoded poller jobs"""

import json
import subprocess
import ipaddress
import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Callable
from database import db
from scan_routes import ping_fast, check_snmp_agent, check_port_fast
from notification_service import send_notification

class GenericJobScheduler:
    """Generic job scheduler that supports any kind of action"""
    
    def __init__(self):
        self.login_methods = {
            'ping': self._ping_login,
            'snmp': self._snmp_login,
            'ssh_port': self._ssh_port_login,
            'rdp_port': self._rdp_port_login,
        }
        self.result_parsers = {
            'ping_result': self._parse_ping_result,
            'snmp_result': self._parse_snmp_result,
            'port_result': self._parse_port_result,
            'hostname_result': self._parse_hostname_result,
        }
        self.database_mappers = {
            'devices': self._map_to_devices_table,
            'interfaces': self._map_to_interfaces_table,
            'optical': self._map_to_optical_table,
        }
    
    def execute_job(self, job_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a generic job based on its definition"""
        start_time = datetime.now()
        results = {
            'job_id': job_definition['job_id'],
            'job_name': job_definition['name'],
            'started_at': start_time.isoformat(),
            'actions_completed': 0,
            'total_actions': len(job_definition['actions']),
            'errors': []
        }
        
        try:
            # Execute each action in the job
            for action in job_definition['actions']:
                action_result = self._execute_action(action, job_definition.get('config', {}))
                results[f'action_{action["type"]}'] = action_result
                results['actions_completed'] += 1

                # Per-action notifications for Job Builder style jobs
                self._maybe_send_action_notification(job_definition, action, action_result)
                
                if action_result.get('error'):
                    results['errors'].append(f"Action {action['type']}: {action_result['error']}")
        
        except Exception as e:
            results['errors'].append(f"Job execution failed: {str(e)}")
        
        finally:
            end_time = datetime.now()
            results['finished_at'] = end_time.isoformat()
            results['duration_seconds'] = (end_time - start_time).total_seconds()
        
        return results
    
    def _execute_action(self, action: Dict[str, Any], job_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single action within a job"""
        try:
            # Get targets for this action
            targets = self._get_targets(action, job_config)
            
            # Execute the action on each target
            action_results = []
            for target in targets:
                result = self._execute_on_target(target, action, job_config)
                action_results.append(result)
            
            # Parse and store results
            parsed_results = []
            for result in action_results:
                parsed = self._parse_result(result, action)
                if parsed:
                    self._store_result(parsed, action)
                    parsed_results.append(parsed)
            
            return {
                'action_type': action['type'],
                'targets_processed': len(targets),
                'successful_results': len(parsed_results),
                'results': parsed_results
            }
            
        except Exception as e:
            return {'error': str(e)}

    def _maybe_send_action_notification(self, job_definition: Dict[str, Any], action: Dict[str, Any], action_result: Dict[str, Any]):
        """Send per-action notifications based on action.notifications config."""
        try:
            notifications = action.get('notifications') or {}
            if not notifications.get('enabled'):
                return

            targets = notifications.get('targets') or []
            if not targets:
                return

            has_error = bool(action_result.get('error'))
            successful = action_result.get('successful_results', 0) > 0 and not has_error

            if has_error and not notifications.get('on_failure', True):
                return
            if successful and not notifications.get('on_success'):
                return
            if not successful and not has_error and not notifications.get('on_failure', True):
                return

            status = 'FAILED' if has_error or not successful else 'SUCCEEDED'
            job_name = job_definition.get('name', job_definition.get('job_id', 'job'))
            action_type = action.get('type', 'action')

            title = f"Job '{job_name}' action {action_type} {status}"

            if has_error:
                error_msg = action_result.get('error', 'Unknown error')
                body = f"Action {action_type} in job '{job_name}' failed. Error: {error_msg}"
            else:
                body = (
                    f"Action {action_type} in job '{job_name}' completed. "
                    f"Targets processed: {action_result.get('targets_processed', 0)}, "
                    f"successful results: {action_result.get('successful_results', 0)}."
                )

            tag_status = 'error' if has_error or not successful else 'success'
            tag = f"job_builder.{job_definition.get('job_id', 'job')}.{action_type}.{tag_status}"

            send_notification(targets=targets, title=title, body=body, tag=tag)
        except Exception:
            # Notification failures should never break job execution
            pass
    
    def _execute_on_target(self, target: str, action: Dict[str, Any], job_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute action on a single target"""
        login_method = action['login_method']
        command_template = action['command']
        
        # Get the login function
        login_func = self.login_methods.get(login_method)
        if not login_func:
            raise ValueError(f"Unknown login method: {login_method}")
        
        # Format the command with target
        command = command_template.format(target=target, **job_config)
        
        # Execute the command
        return login_func(target, command, action.get('timeout', 5))
    
    def _get_targets(self, action: Dict[str, Any], job_config: Dict[str, Any]) -> List[str]:
        """Get list of targets for an action"""
        target_source = action.get('target_source', 'network_range')
        
        if target_source == 'network_range':
            network = job_config.get('network', '10.127.0.0/24')
            network_obj = ipaddress.ip_network(network, strict=False)
            return [str(ip) for ip in network_obj.hosts()]
        
        elif target_source == 'device_list':
            devices = db.get_all_devices()
            return [d['ip_address'] for d in devices if d.get('ip_address')]
        
        elif target_source == 'ssh_devices':
            devices = db.get_all_devices()
            settings = self._get_settings()
            success_status = settings.get('ssh_success_status', 'YES')
            return [d['ip_address'] for d in devices if d.get('ssh_status') == success_status]
        
        elif target_source == 'custom_list':
            return job_config.get('custom_targets', '').split('\n')
        
        else:
            return []
    
    def _parse_result(self, raw_result: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw result using specified parser"""
        parser_name = action.get('result_parser', 'default')
        parser_func = self.result_parsers.get(parser_name)
        
        if parser_func:
            return parser_func(raw_result, action)
        else:
            return raw_result
    
    def _store_result(self, parsed_result: Dict[str, Any], action: Dict[str, Any]):
        """Store parsed result in database"""
        db_table = action.get('database_table', 'devices')
        mapper_func = self.database_mappers.get(db_table)
        
        if mapper_func:
            mapper_func(parsed_result, action)
    
    # Login Methods
    def _ping_login(self, target: str, command: str, timeout: int) -> Dict[str, Any]:
        """Ping login method"""
        try:
            success = ping_fast(target, timeout)
            return {
                'target': target,
                'login_method': 'ping',
                'success': success,
                'command': command,
                'raw_output': str(success)
            }
        except Exception as e:
            return {
                'target': target,
                'login_method': 'ping',
                'success': False,
                'error': str(e)
            }
    
    def _snmp_login(self, target: str, command: str, timeout: int) -> Dict[str, Any]:
        """SNMP login method"""
        try:
            settings = self._get_settings()
            result = check_snmp_agent(target, settings)
            return {
                'target': target,
                'login_method': 'snmp',
                'success': result != settings.get('snmp_fail_status', 'NO'),
                'command': command,
                'raw_output': result
            }
        except Exception as e:
            return {
                'target': target,
                'login_method': 'snmp',
                'success': False,
                'error': str(e)
            }
    
    def _ssh_port_login(self, target: str, command: str, timeout: int) -> Dict[str, Any]:
        """SSH port check login method"""
        try:
            settings = self._get_settings()
            success = check_port_fast(target, int(settings['ssh_port']), float(settings['ssh_timeout']))
            return {
                'target': target,
                'login_method': 'ssh_port',
                'success': success,
                'command': command,
                'raw_output': str(success)
            }
        except Exception as e:
            return {
                'target': target,
                'login_method': 'ssh_port',
                'success': False,
                'error': str(e)
            }
    
    def _rdp_port_login(self, target: str, command: str, timeout: int) -> Dict[str, Any]:
        """RDP port check login method"""
        try:
            settings = self._get_settings()
            success = check_port_fast(target, int(settings['rdp_port']), float(settings['rdp_timeout']))
            return {
                'target': target,
                'login_method': 'rdp_port',
                'success': success,
                'command': command,
                'raw_output': str(success)
            }
        except Exception as e:
            return {
                'target': target,
                'login_method': 'rdp_port',
                'success': False,
                'error': str(e)
            }
    
    # Result Parsers
    def _parse_ping_result(self, raw_result: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
        """Parse ping result for devices table"""
        settings = self._get_settings()
        ping_status = settings['online_status'] if raw_result['success'] else settings['offline_status']
        
        return {
            'ip_address': raw_result['target'],
            'ping_status': ping_status,
            'last_seen': datetime.now().isoformat()
        }
    
    def _parse_snmp_result(self, raw_result: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
        """Parse SNMP result for devices table"""
        settings = self._get_settings()
        snmp_status = settings['snmp_success_status'] if raw_result['success'] else settings['snmp_fail_status']
        
        return {
            'ip_address': raw_result['target'],
            'snmp_status': snmp_status,
            'last_seen': datetime.now().isoformat()
        }
    
    def _parse_port_result(self, raw_result: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
        """Parse port result (SSH/RDP) for devices table"""
        port_type = raw_result['login_method'].replace('_port', '')
        settings = self._get_settings()
        success_status = settings.get(f'{port_type}_success_status', 'YES')
        fail_status = settings.get(f'{port_type}_fail_status', 'NO')
        port_status = success_status if raw_result['success'] else fail_status
        
        return {
            'ip_address': raw_result['target'],
            f'{port_type}_status': port_status,
            'last_seen': datetime.now().isoformat()
        }
    
    def _parse_hostname_result(self, raw_result: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
        """Parse hostname result for devices table"""
        return {
            'ip_address': raw_result['target'],
            'hostname': raw_result.get('hostname', ''),
            'last_seen': datetime.now().isoformat()
        }
    
    # Database Mappers
    def _map_to_devices_table(self, parsed_result: Dict[str, Any], action: Dict[str, Any]):
        """Map result to devices table"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Check if device exists
            cursor.execute("SELECT id FROM devices WHERE ip_address = %s", (parsed_result['ip_address'],))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing device
                set_clauses = []
                values = []
                
                for key, value in parsed_result.items():
                    if key != 'ip_address':
                        set_clauses.append(f"{key} = %s")
                        values.append(value)
                
                if set_clauses:
                    values.append(parsed_result['ip_address'])
                    query = f"UPDATE devices SET {', '.join(set_clauses)} WHERE ip_address = %s"
                    cursor.execute(query, values)
            else:
                # Insert new device
                columns = list(parsed_result.keys())
                placeholders = ', '.join(['%s'] * len(columns))
                query = f"INSERT INTO devices ({', '.join(columns)}) VALUES ({placeholders})"
                cursor.execute(query, list(parsed_result.values()))
            
            conn.commit()
            
        except Exception as e:
            print(f"Database mapping error: {e}")
    
    def _map_to_interfaces_table(self, parsed_result: Dict[str, Any], action: Dict[str, Any]):
        """Map result to interfaces table"""
        # TODO: Implement interface mapping
        pass
    
    def _map_to_optical_table(self, parsed_result: Dict[str, Any], action: Dict[str, Any]):
        """Map result to optical table"""
        # TODO: Implement optical mapping
        pass
    
    def _get_settings(self) -> Dict[str, Any]:
        """Get application settings"""
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except:
            return {
                'online_status': 'online',
                'offline_status': 'offline',
                'ssh_success_status': 'YES',
                'ssh_fail_status': 'NO',
                'rdp_success_status': 'YES',
                'rdp_fail_status': 'NO',
                'snmp_success_status': 'YES',
                'snmp_fail_status': 'NO',
                'ssh_port': '22',
                'rdp_port': '3389',
                'ssh_timeout': '5',
                'rdp_timeout': '3'
            }


# Discovery Job Definition - Extracted from hardcoded version
DISCOVERY_JOB_DEFINITION = {
    "job_id": "network_discovery",
    "name": "Network Discovery",
    "description": "Discover devices on network using ping, SNMP, SSH, and RDP",
    "actions": [
        {
            "type": "ping_scan",
            "login_method": "ping",
            "command": "ping -c 1 -W 1 {target}",
            "target_source": "network_range",
            "result_parser": "ping_result",
            "database_table": "devices",
            "timeout": 1
        },
        {
            "type": "snmp_scan",
            "login_method": "snmp",
            "command": "snmpget -v2c -c public {target} sysDescr.0",
            "target_source": "network_range",
            "result_parser": "snmp_result",
            "database_table": "devices",
            "timeout": 3
        },
        {
            "type": "ssh_scan",
            "login_method": "ssh_port",
            "command": "nc -zv {target} 22",
            "target_source": "network_range",
            "result_parser": "port_result",
            "database_table": "devices",
            "timeout": 5
        },
        {
            "type": "rdp_scan",
            "login_method": "rdp_port",
            "command": "nc -zv {target} 3389",
            "target_source": "network_range",
            "result_parser": "port_result",
            "database_table": "devices",
            "timeout": 3
        }
    ],
    "config": {
        "network": "10.127.0.0/24",
        "parallel_threads": 20,
        "batch_size": 50
    }
}


def run_generic_discovery_job(config: Dict[str, Any]) -> Dict[str, Any]:
    """Run discovery job using generic scheduler"""
    scheduler = GenericJobScheduler()
    
    # Update job definition with config
    job_def = DISCOVERY_JOB_DEFINITION.copy()
    job_def['config'].update(config)
    
    return scheduler.execute_job(job_def)


def _translate_builder_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Translate a Job Builder style action into the generic scheduler format."""
    login = action.get('login_method') or {}
    targeting = action.get('targeting') or {}
    execution = action.get('execution') or {}

    login_type = login.get('type') or login.get('platform') or 'ping'

    if login_type == 'ping':
        result_parser = 'ping_result'
    elif login_type == 'snmp':
        result_parser = 'snmp_result'
    elif login_type in ('ssh_port', 'rdp_port'):
        result_parser = 'port_result'
    else:
        result_parser = 'default'

    target_source = targeting.get('source', 'network_range')

    return {
        'type': action.get('type', login_type),
        'login_method': login_type,
        'command': login.get('command', ''),
        'target_source': target_source,
        'result_parser': result_parser,
        'database_table': (action.get('database') or {}).get('table', 'devices'),
        'timeout': execution.get('timeout', 5),
        'notifications': action.get('notifications') or {},
    }


def run_job_builder_job(job_definition: Dict[str, Any]) -> Dict[str, Any]:
    """Run a Job Builder style job definition using the generic scheduler.

    This adapts the richer Job Builder schema into the simpler generic
    scheduler format so we can reuse the same execution engine and
    database mappings while supporting per-action notifications.
    """
    scheduler = GenericJobScheduler()

    actions = []
    for action in job_definition.get('actions', []):
        if not action.get('enabled', True):
            continue
        try:
            actions.append(_translate_builder_action(action))
        except Exception:
            continue

    config = job_definition.get('config', {}) or {}

    if 'network' not in config:
        for action in job_definition.get('actions', []):
            targeting = action.get('targeting') or {}
            if targeting.get('network_range'):
                config['network'] = targeting['network_range']
                break
    if 'network' not in config:
        config['network'] = '10.127.0.0/24'

    for action in job_definition.get('actions', []):
        targeting = action.get('targeting') or {}
        if targeting.get('source') == 'custom_list' and targeting.get('target_list'):
            config['custom_targets'] = targeting['target_list']
            break

    generic_job = {
        'job_id': job_definition.get('job_id', 'job_builder'),
        'name': job_definition.get('name', 'Job Builder Job'),
        'description': job_definition.get('description', ''),
        'actions': actions,
        'config': config,
    }

    return scheduler.execute_job(generic_job)
