#!/usr/bin/env python3
"""Generic Job Scheduler - Extracted from hardcoded poller jobs"""

import json
import subprocess
import ipaddress
import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Callable
import logging
from database import db
from scan_routes import (
    ping_fast, check_snmp_agent, check_port_fast, _ssh_run_command,
    _parse_port_xcvr_show, _parse_port_show, _parse_port_xcvr_diagnostics,
    _parse_lldp_neighbors
)
from notification_service import send_notification

logger = logging.getLogger(__name__)

class GenericJobScheduler:
    """Generic job scheduler that supports any kind of action"""
    
    def __init__(self):
        self.login_methods = {
            'ping': self._ping_login,
            'snmp': self._snmp_login,
            'ssh': self._ssh_cli_login,
            'ssh_cli': self._ssh_cli_login,
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
        """Execute a single action within a job.
        
        Supports multi-command workflows via execution.commands array.
        Each command can have its own parser and can iterate over results
        from previous commands using execution.foreach.
        """
        try:
            # Get targets for this action
            targets = self._get_targets(action, job_config)
            
            # Check if this is a multi-command workflow
            execution = action.get('execution', {})
            commands = execution.get('commands', [])
            
            if commands and len(commands) > 0:
                # Multi-command workflow
                with open('/tmp/job_debug.log', 'a') as f:
                    f.write(f"[DEBUG] Using multi-command workflow with {len(commands)} commands for {len(targets)} targets\n")
                return self._execute_multi_command_action(targets, action, job_config)
            else:
                # Single command workflow (legacy)
                return self._execute_single_command_action(targets, action, job_config)
            
        except Exception as e:
            logger.exception(f"Action execution failed: {e}")
            return {'error': str(e)}
    
    def _execute_single_command_action(self, targets: List[str], action: Dict[str, Any], job_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single-command action (legacy mode)"""
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
    
    def _execute_multi_command_action(self, targets: List[str], action: Dict[str, Any], job_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a multi-command workflow action.
        
        Supports:
        - Sequential commands per target
        - foreach iteration over parsed results with filtering
        - Multiple parsers for different commands
        - Merging port_status and lldp data into interfaces
        - Multiple database table writes
        """
        execution = action.get('execution', {})
        commands = execution.get('commands', [])
        result_parsing = action.get('result_parsing', {})
        parsers = result_parsing.get('parsers', {})
        database_config = action.get('database', {})
        tables = database_config.get('tables', [])
        logger.info(f"[MULTI_CMD] Action type={action.get('type')}, commands={len(commands)}, parsers={len(parsers)}, tables={len(tables)}")
        
        settings = self._get_settings()
        all_results = []
        successful_count = 0
        
        for target in targets:
            target_context = {
                'target': target,
                'ip_address': target,
                'settings': settings,
                'parsed_data': {},
                'interfaces': [],
                'port_status': {},
                'lldp_neighbors': {},
            }
            
            try:
                # Execute each command in sequence
                for cmd_config in commands:
                    cmd_id = cmd_config.get('id', 'cmd')
                    cmd_template = cmd_config.get('command', '')
                    parser_id = cmd_config.get('parser')
                    foreach = cmd_config.get('foreach')
                    store_as = cmd_config.get('store_as')
                    cmd_filter = cmd_config.get('filter', {})
                    
                    if foreach:
                        # Iterate over items from previous command's parsed results
                        items = target_context.get(foreach, [])
                        for item in items:
                            # Apply filter if specified
                            if cmd_filter:
                                skip = False
                                for filter_key, filter_val in cmd_filter.items():
                                    if item.get(filter_key) != filter_val:
                                        skip = True
                                        break
                                if skip:
                                    continue
                            
                            # Get port number for command formatting
                            port_num = item.get('cli_port')
                            if not port_num:
                                idx = item.get('interface_index')
                                try:
                                    idx_int = int(idx)
                                    port_num = idx_int if idx_int < 10000 else idx_int - 10000
                                except Exception:
                                    continue
                            if not port_num:
                                continue
                            
                            # Format command with item data
                            item_context = {**target_context, **item, 'cli_port': port_num}
                            cmd = self._format_command(cmd_template, item_context)
                            output = _ssh_run_command(target, settings, cmd)
                            
                            # Parse output if parser specified
                            if parser_id and parser_id in parsers:
                                parsed = self._apply_parser(parsers[parser_id], output, item_context)
                                if parsed and isinstance(parsed, dict):
                                    # Merge parsed data back into item
                                    item.update(parsed)
                    else:
                        # Single execution
                        cmd = self._format_command(cmd_template, target_context)
                        output = _ssh_run_command(target, settings, cmd)
                        output_len = len(output) if output else 0
                        
                        # Parse output if parser specified
                        if parser_id and parser_id in parsers:
                            parsed = self._apply_parser(parsers[parser_id], output, target_context)
                            parsed_len = len(parsed) if isinstance(parsed, (list, dict)) else (1 if parsed else 0)
                            print(f"[DEBUG] {target} cmd={cmd_id} output={output_len} parsed={parsed_len}")
                            if parsed:
                                if store_as:
                                    target_context[store_as] = parsed
                                    print(f"[DEBUG] {target} stored {parsed_len} items as '{store_as}'")
                                    if cmd_id == 'lldp_neighbors':
                                        logger.info(f"[LLDP_PARSE] {target}: stored {parsed_len} LLDP neighbors")
                                else:
                                    target_context['parsed_data'].update(parsed if isinstance(parsed, dict) else {})
                        elif output:
                            logger.debug(f"[{target}] {cmd_id}: got {len(output)} chars but no parser")
                
                # Merge port_status into interfaces (like original code)
                port_status = target_context.get('port_status', {})
                if port_status and isinstance(port_status, dict):
                    for iface in target_context.get('interfaces', []):
                        port_key = iface.get('cli_port')
                        if not port_key:
                            idx = iface.get('interface_index')
                            try:
                                idx_int = int(idx)
                                port_key = idx_int if idx_int < 10000 else idx_int - 10000
                            except Exception:
                                port_key = None
                        
                        if port_key and port_key in port_status:
                            pinfo = port_status[port_key]
                            link = (pinfo.get('link') or '').strip().lower()
                            if link.startswith('up'):
                                iface['status'] = 'up'
                            elif link.startswith('down'):
                                iface['status'] = 'down'
                            
                            mode = (pinfo.get('mode') or '').strip()
                            if mode and not iface.get('speed'):
                                iface['speed'] = mode
                            
                            ptype = (pinfo.get('port_type') or '').strip()
                            if not iface.get('medium') and ptype:
                                iface['medium'] = ptype
                            if not iface.get('connector') and any(t in ptype.lower() for t in ['10/100', 'g']):
                                iface['connector'] = 'RJ45'
                
                # Merge LLDP neighbors into interfaces (like original code)
                lldp_neighbors = target_context.get('lldp_neighbors', {})
                if lldp_neighbors and isinstance(lldp_neighbors, dict):
                    for iface in target_context.get('interfaces', []):
                        port_key = iface.get('cli_port')
                        if not port_key:
                            idx = iface.get('interface_index')
                            try:
                                idx_int = int(idx)
                                port_key = idx_int if idx_int < 10000 else idx_int - 10000
                            except Exception:
                                continue
                        if not port_key:
                            continue
                        
                        neigh = lldp_neighbors.get(port_key)
                        if neigh:
                            iface['lldp_remote_port'] = neigh.get('lldp_remote_port')
                            iface['lldp_remote_mgmt_addr'] = neigh.get('lldp_remote_mgmt_addr')
                            iface['lldp_remote_chassis_id'] = neigh.get('lldp_remote_chassis_id')
                            iface['lldp_remote_system_name'] = neigh.get('lldp_remote_system_name')
                            iface['lldp_raw_info'] = neigh.get('lldp_raw_info')
                            # If LLDP sees a live neighbor, treat the port as up
                            if iface.get('status') != 'up':
                                iface['status'] = 'up'
                
                # Store results to database tables
                with open('/tmp/lldp_debug.log', 'a') as f:
                    f.write(f"[DB_WRITE] {target}: {len(tables)} tables, context_keys={list(target_context.keys())}\n")
                
                for table_config in tables:
                    table_name = table_config.get('table')
                    source = table_config.get('source', 'parsed_data')
                    source_data = target_context.get(source, {})
                    table_filter = table_config.get('filter', {})
                    operation = table_config.get('operation', 'upsert')
                    
                    with open('/tmp/lldp_debug.log', 'a') as f:
                        f.write(f"  Table={table_name}, source={source}, operation={operation}, data_type={type(source_data)}, data_len={len(source_data) if isinstance(source_data, (dict, list)) else 0}\n")
                    
                    # Special handling for LLDP updates
                    if operation == 'update_lldp':
                        with open('/tmp/lldp_debug.log', 'a') as f:
                            f.write(f"  [LLDP_UPDATE] Calling _update_lldp_data for {target_context['ip_address']}\n")
                        if isinstance(source_data, dict):
                            # LLDP data is a dict of {port_num: neighbor_info}
                            # Update existing interface records with LLDP info
                            self._update_lldp_data(target_context['ip_address'], source_data)
                        else:
                            with open('/tmp/lldp_debug.log', 'a') as f:
                                f.write(f"  [LLDP_ERROR] Expected dict but got {type(source_data)}\n")
                    elif isinstance(source_data, list):
                        for item in source_data:
                            # Apply table filter
                            if table_filter:
                                skip = False
                                for fk, fv in table_filter.items():
                                    if fk == 'has_power_reading':
                                        # Special filter: check if any power reading exists
                                        has_reading = item.get('tx_power') or item.get('rx_power') or item.get('temperature')
                                        if fv and not has_reading:
                                            skip = True
                                            break
                                    elif item.get(fk) != fv:
                                        skip = True
                                        break
                                if skip:
                                    continue
                            self._store_to_table(table_name, item, table_config, target_context)
                    elif source_data:
                        self._store_to_table(table_name, source_data, table_config, target_context)
                
                interfaces_count = len(target_context.get('interfaces', []))
                optical_count = len([i for i in target_context.get('interfaces', []) if i.get('is_optical')])
                
                all_results.append({
                    'target': target,
                    'success': True,
                    'interfaces': interfaces_count,
                    'optical_interfaces': optical_count,
                })
                successful_count += 1
                
            except Exception as e:
                logger.warning(f"Multi-command execution failed for {target}: {e}")
                all_results.append({
                    'target': target,
                    'success': False,
                    'error': str(e)
                })
        
        result = {
            'action_type': action['type'],
            'targets_processed': len(targets),
            'successful_results': successful_count,
            'results': all_results
        }
        logger.warning(f"[DEBUG] Multi-command action returning: targets={len(targets)}, successful={successful_count}, results={len(all_results)}")
        return result
    
    def _format_command(self, template: str, context: Dict[str, Any]) -> str:
        """Format a command template with context variables"""
        try:
            # Support {variable} syntax
            result = template
            for key, value in context.items():
                if isinstance(value, (str, int, float)):
                    result = result.replace('{' + key + '}', str(value))
            return result
        except Exception:
            return template
    
    def _apply_parser(self, parser_config: Dict[str, Any], output: str, context: Dict[str, Any]) -> Any:
        """Apply a parser configuration to command output.
        
        Supports:
        - builtin: use a built-in parser function (e.g., 'ciena_port_xcvr_show')
        - regex: apply regex patterns to extract fields
        - json: parse as JSON
        """
        parser_type = parser_config.get('type', 'regex')
        
        if parser_type == 'builtin':
            builtin_name = parser_config.get('name')
            return self._run_builtin_parser(builtin_name, output, context)
        
        elif parser_type == 'regex':
            patterns = parser_config.get('patterns', [])
            result = {}
            for pattern_config in patterns:
                import re
                pattern = pattern_config.get('pattern', '')
                field = pattern_config.get('field')
                group = pattern_config.get('group', 1)
                match = re.search(pattern, output)
                if match and field:
                    try:
                        result[field] = match.group(group)
                    except IndexError:
                        result[field] = match.group(0)
            return result
        
        elif parser_type == 'json':
            try:
                return json.loads(output)
            except Exception:
                return {}
        
        return {}
    
    def _run_builtin_parser(self, parser_name: str, output: str, context: Dict[str, Any]) -> Any:
        """Run a built-in parser function"""
        if parser_name == 'ciena_port_xcvr_show':
            return _parse_port_xcvr_show(output)
        elif parser_name == 'ciena_port_show':
            return _parse_port_show(output)
        elif parser_name == 'ciena_port_xcvr_diagnostics':
            tx_dbm, rx_dbm, temperature = _parse_port_xcvr_diagnostics(output)
            return {
                'tx_power': tx_dbm,
                'rx_power': rx_dbm,
                'temperature': temperature
            }
        elif parser_name == 'ciena_lldp_neighbors':
            return _parse_lldp_neighbors(output)
        else:
            logger.warning(f"Unknown builtin parser: {parser_name}")
            return {}
    
    def _update_lldp_data(self, ip_address: str, lldp_neighbors: Dict[int, Dict[str, Any]]) -> None:
        """Update existing interface records with LLDP neighbor information"""
        try:
            logger.info(f"Updating LLDP data for {ip_address}: {len(lldp_neighbors)} neighbors")
            for port_num, neighbor_info in lldp_neighbors.items():
                # Update ssh_cli_scans records with LLDP data
                query = """
                    UPDATE ssh_cli_scans 
                    SET lldp_remote_port = %s,
                        lldp_remote_mgmt_addr = %s,
                        lldp_remote_chassis_id = %s,
                        lldp_remote_system_name = %s,
                        lldp_raw_info = %s,
                        scan_timestamp = NOW()
                    WHERE ip_address = %s 
                    AND cli_port = %s
                """
                result = db.execute_query(query, (
                    neighbor_info.get('lldp_remote_port'),
                    neighbor_info.get('lldp_remote_mgmt_addr'),
                    neighbor_info.get('lldp_remote_chassis_id'),
                    neighbor_info.get('lldp_remote_system_name'),
                    neighbor_info.get('lldp_raw_info'),
                    ip_address,
                    str(port_num)
                ))
                logger.debug(f"Updated LLDP for {ip_address} port {port_num}: {neighbor_info.get('lldp_remote_system_name')}")
        except Exception as e:
            logger.warning(f"Failed to update LLDP data for {ip_address}: {e}")
    
    def _store_to_table(self, table_name: str, data: Dict[str, Any], table_config: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Store data to a specific database table"""
        try:
            if table_name == 'ssh_cli_scans':
                db.insert_ssh_cli_scan(
                    context['ip_address'],
                    data.get('interface_index', ''),
                    data.get('interface_name', ''),
                    data.get('cli_port', ''),
                    data.get('is_optical', False),
                    data.get('medium', ''),
                    data.get('connector', ''),
                    data.get('speed', ''),
                    data.get('tx_power', ''),
                    data.get('rx_power', ''),
                    data.get('temperature', ''),
                    data.get('status', ''),
                    data.get('raw_output', ''),
                    data.get('lldp_remote_port'),
                    data.get('lldp_remote_mgmt_addr'),
                    data.get('lldp_remote_chassis_id'),
                    data.get('lldp_remote_system_name'),
                    data.get('lldp_raw_info'),
                )
            elif table_name == 'optical_power_history':
                # Parse power values
                tx_val = self._parse_power_value(data.get('tx_power'))
                rx_val = self._parse_power_value(data.get('rx_power'))
                temp_val = self._parse_temp_value(data.get('temperature'))
                
                if tx_val is not None or rx_val is not None or temp_val is not None:
                    db.insert_optical_power_history(
                        context['ip_address'],
                        data.get('interface_index', ''),
                        data.get('interface_name', ''),
                        data.get('cli_port', ''),
                        tx_val,
                        rx_val,
                        temp_val
                    )
            elif table_name == 'scan_results' or table_name == 'devices':
                # Use existing device mapper
                self._map_to_devices_table(data, {'database_table': 'devices'})
            else:
                logger.warning(f"Unknown table for storage: {table_name}")
        except Exception as e:
            logger.warning(f"Failed to store to {table_name}: {e}")
    
    def _parse_power_value(self, value: Any) -> float:
        """Parse optical power value to float"""
        if value is None:
            return None
        try:
            val_str = str(value).replace('dBm', '').strip()
            return float(val_str)
        except Exception:
            return None
    
    def _parse_temp_value(self, value: Any) -> float:
        """Parse temperature value to float"""
        if value is None:
            return None
        try:
            val_str = str(value).replace('C', '').replace('°', '').strip()
            return float(val_str)
        except Exception:
            return None

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
            custom = action.get('custom_targets') or job_config.get('custom_targets', '')
            if isinstance(custom, list):
                return [t.strip() for t in custom if t.strip()]
            return [t.strip() for t in custom.split('\n') if t.strip()]
        
        elif target_source == 'database_query':
            # Execute the query from the action's targeting config
            query = action.get('database_query') or job_config.get('database_query')
            if query:
                try:
                    rows = db.execute_query(query)
                    # Extract first column from each row as target
                    targets = []
                    for row in rows:
                        if row:
                            val = row[0] if isinstance(row, (list, tuple)) else row.get('ip_address', row)
                            if val:
                                targets.append(str(val))
                    return targets
                except Exception as e:
                    logger.error(f"Database query targeting failed: {e}")
                    return []
            return []
        
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
    
    def _ssh_cli_login(self, target: str, command: str, timeout: int) -> Dict[str, Any]:
        """SSH CLI login method - executes commands via SSH"""
        try:
            settings = self._get_settings()
            # Use the command passed in, or a default
            ssh_command = command if command else 'show version'
            output = _ssh_run_command(target, settings, ssh_command)
            success = output is not None and len(output) > 0
            return {
                'target': target,
                'login_method': 'ssh_cli',
                'success': success,
                'command': ssh_command,
                'raw_output': output or ''
            }
        except Exception as e:
            logger.warning(f"SSH CLI login failed for {target}: {e}")
            return {
                'target': target,
                'login_method': 'ssh_cli',
                'success': False,
                'command': command,
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

    translated = {
        'type': action.get('type', login_type),
        'login_method': login_type,
        'command': login.get('command', ''),
        'target_source': target_source,
        'result_parser': result_parser,
        'database_table': (action.get('database') or {}).get('table', 'devices'),
        'timeout': execution.get('timeout', 5),
        'notifications': action.get('notifications') or {},
    }

    # Pass through database query if using database_query targeting
    if target_source == 'database_query' and targeting.get('query'):
        translated['database_query'] = targeting['query']

    # Pass through target list if using custom_list targeting
    if target_source == 'custom_list' and targeting.get('target_list'):
        translated['custom_targets'] = targeting['target_list']

    # Pass through multi-command workflow structure
    if execution.get('commands'):
        translated['execution'] = execution
        translated['result_parsing'] = action.get('result_parsing', {})
        db_config = action.get('database', {})
        translated['database'] = db_config
        with open('/tmp/job_debug.log', 'a') as f:
            tables = db_config.get('tables', [])
            f.write(f"[TRANSLATE] Added multi-command: {len(execution.get('commands'))} commands, {len(tables)} tables\n")
            if tables:
                for t in tables:
                    f.write(f"  Table: {t.get('table')}, source={t.get('source')}, operation={t.get('operation')}\n")
    else:
        with open('/tmp/job_debug.log', 'a') as f:
            f.write(f"[TRANSLATE] No commands in execution: {execution}\n")

    return translated


def run_job_builder_job(job_definition: Dict[str, Any]) -> Dict[str, Any]:
    """Run a Job Builder style job definition using the generic scheduler.

    This adapts the richer Job Builder schema into the simpler generic
    scheduler format so we can reuse the same execution engine and
    database mappings while supporting per-action notifications.
    """
    scheduler = GenericJobScheduler()

    with open('/tmp/job_debug.log', 'a') as f:
        f.write(f"[RUN_JOB_BUILDER] Job has {len(job_definition.get('actions', []))} actions\n")
        for i, a in enumerate(job_definition.get('actions', [])):
            exec_cfg = a.get('execution', {})
            f.write(f"  Action {i}: type={a.get('type')}, execution keys={list(exec_cfg.keys())}\n")

    actions = []
    for action in job_definition.get('actions', []):
        if not action.get('enabled', True):
            continue
        try:
            translated = _translate_builder_action(action)
            actions.append(translated)
        except Exception as e:
            logger.error(f"Failed to translate action {action.get('type')}: {e}")
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


def run_job_spec(job_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a generic job specification using GenericJobScheduler.

    This is the canonical entrypoint for Celery-based execution of
    Job Builder style definitions that have already been translated
    into the GenericJobScheduler format (job_id, name, actions, config).
    """
    scheduler = GenericJobScheduler()
    return scheduler.execute_job(job_spec)
