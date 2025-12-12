"""
Job Migration Service

Migrates old job definitions from the CompleteJobBuilder format
to the new visual workflow format.
"""

import uuid
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class JobMigrationService:
    """
    Service for migrating old job definitions to new workflow format.
    """
    
    def __init__(self, db_manager=None):
        self.db = db_manager
    
    def migrate_job(self, old_job: Dict) -> Dict:
        """
        Convert an old job definition to new workflow format.
        
        Args:
            old_job: Job definition in old CompleteJobBuilder format
        
        Returns:
            Workflow definition in new format
        """
        nodes = []
        edges = []
        
        # Node positioning
        x_spacing = 320
        y_spacing = 150
        current_x = 100
        current_y = 100
        
        # Add start trigger node
        start_node_id = f"node-{uuid.uuid4().hex[:8]}"
        nodes.append({
            'id': start_node_id,
            'type': 'workflow',
            'position': {'x': current_x, 'y': current_y},
            'data': {
                'nodeType': 'trigger:manual',
                'label': 'Start',
                'description': '',
                'parameters': {},
            },
        })
        
        previous_node_id = start_node_id
        current_x += x_spacing
        
        # Convert each action to a node
        actions = old_job.get('actions', [])
        for i, action in enumerate(actions):
            if not action.get('enabled', True):
                continue
            
            node_id = f"node-{uuid.uuid4().hex[:8]}"
            node_type = self._map_action_type(action)
            
            # Extract parameters from action
            parameters = self._extract_parameters(action)
            
            nodes.append({
                'id': node_id,
                'type': 'workflow',
                'position': {'x': current_x, 'y': current_y},
                'data': {
                    'nodeType': node_type,
                    'label': action.get('name', f'Action {i + 1}'),
                    'description': action.get('description', ''),
                    'parameters': parameters,
                },
            })
            
            # Connect to previous node
            edges.append({
                'id': f"edge-{uuid.uuid4().hex[:8]}",
                'source': previous_node_id,
                'target': node_id,
                'sourceHandle': 'success' if previous_node_id != start_node_id else 'trigger',
                'targetHandle': 'trigger',
                'type': 'smoothstep',
            })
            
            previous_node_id = node_id
            current_x += x_spacing
        
        # Add database save node if configured
        db_config = self._get_database_config(old_job)
        if db_config:
            db_node_id = f"node-{uuid.uuid4().hex[:8]}"
            nodes.append({
                'id': db_node_id,
                'type': 'workflow',
                'position': {'x': current_x, 'y': current_y},
                'data': {
                    'nodeType': 'db:upsert',
                    'label': 'Save to Database',
                    'description': '',
                    'parameters': db_config,
                },
            })
            
            edges.append({
                'id': f"edge-{uuid.uuid4().hex[:8]}",
                'source': previous_node_id,
                'target': db_node_id,
                'sourceHandle': 'success',
                'targetHandle': 'trigger',
                'type': 'smoothstep',
            })
        
        # Build workflow definition
        workflow = {
            'name': old_job.get('name', 'Migrated Job'),
            'description': old_job.get('description', f"Migrated from job: {old_job.get('job_id', 'unknown')}"),
            'definition': {
                'nodes': nodes,
                'edges': edges,
                'viewport': {'x': 0, 'y': 0, 'zoom': 1},
            },
            'settings': {
                'error_handling': old_job.get('config', {}).get('error_handling', 'continue'),
                'timeout': old_job.get('config', {}).get('global_timeout', 300),
                'notifications': {
                    'on_success': False,
                    'on_failure': True,
                },
            },
            'enabled': True,
            'migrated_from': old_job.get('job_id') or old_job.get('id'),
            'migrated_at': datetime.utcnow().isoformat(),
        }
        
        return workflow
    
    def _map_action_type(self, action: Dict) -> str:
        """Map old action type to new node type."""
        action_type = action.get('type', '').lower()
        
        type_mapping = {
            'ping': 'network:ping',
            'ping_scan': 'network:ping',
            'icmp_ping': 'network:ping',
            'snmp': 'snmp:get',
            'snmp_scan': 'snmp:get',
            'snmp_get': 'snmp:get',
            'snmp_walk': 'snmp:walk',
            'ssh': 'ssh:command',
            'ssh_scan': 'ssh:command',
            'ssh_command': 'ssh:command',
            'rdp_scan': 'network:port-scan',
            'port_scan': 'network:port-scan',
            'traceroute': 'network:traceroute',
        }
        
        return type_mapping.get(action_type, 'ssh:command')
    
    def _extract_parameters(self, action: Dict) -> Dict:
        """Extract parameters from old action format."""
        params = {}
        
        # Targeting
        targeting = action.get('targeting', {})
        source = targeting.get('source', 'network_range')
        
        if source == 'network_range':
            params['target_type'] = 'network_range'
            params['network_range'] = targeting.get('network_range', '')
        elif source == 'device_group':
            params['target_type'] = 'device_group'
            params['device_group'] = targeting.get('device_group', '')
        elif source == 'ip_list':
            params['target_type'] = 'ip_list'
            params['ip_list'] = '\n'.join(targeting.get('ip_list', []))
        else:
            params['target_type'] = 'from_input'
        
        # Execution parameters
        execution = action.get('execution', {})
        if execution.get('command'):
            params['command'] = execution['command']
        if execution.get('timeout'):
            params['timeout'] = execution['timeout']
        if execution.get('count'):
            params['count'] = execution['count']
        
        # SNMP parameters
        if execution.get('community'):
            params['community'] = execution['community']
        if execution.get('oids'):
            params['oids'] = execution['oids']
        
        # SSH parameters
        if execution.get('username'):
            params['username'] = execution['username']
        if execution.get('port'):
            params['port'] = execution['port']
        
        # Login method
        login = action.get('login_method', {})
        if login.get('username'):
            params['username'] = login['username']
        if login.get('password'):
            params['password'] = login['password']
        
        return params
    
    def _get_database_config(self, old_job: Dict) -> Optional[Dict]:
        """Extract database configuration from old job."""
        for action in old_job.get('actions', []):
            db_config = action.get('database', {})
            if db_config.get('table'):
                return {
                    'table': db_config['table'],
                    'key_columns': ','.join(db_config.get('key_fields', ['ip_address'])),
                    'data_source': 'from_input',
                }
        return None
    
    def migrate_all_jobs(self) -> Dict:
        """
        Migrate all existing job definitions to workflows.
        
        Returns:
            Migration results with counts and errors
        """
        if not self.db:
            return {'error': 'Database not configured', 'migrated': 0}
        
        try:
            # Get all job definitions
            query = "SELECT * FROM job_definitions"
            jobs = self.db.execute_query(query)
            
            if not jobs:
                return {'message': 'No jobs to migrate', 'migrated': 0}
            
            migrated = 0
            skipped = 0
            errors = []
            
            for job_row in jobs:
                try:
                    # Parse job definition
                    job_def = job_row.get('definition', {})
                    if isinstance(job_def, str):
                        job_def = json.loads(job_def)
                    
                    job_def['job_id'] = job_row.get('job_id')
                    job_def['name'] = job_row.get('name', job_def.get('name', 'Unnamed Job'))
                    
                    # Check if already migrated
                    check_query = """
                        SELECT id FROM workflows 
                        WHERE (definition->>'migrated_from')::text = %s
                    """
                    existing = self.db.execute_query(check_query, (str(job_row.get('job_id')),))
                    
                    if existing:
                        skipped += 1
                        continue
                    
                    # Migrate the job
                    workflow = self.migrate_job(job_def)
                    
                    # Insert into workflows table
                    insert_query = """
                        INSERT INTO workflows (name, description, definition, settings, enabled)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                    """
                    result = self.db.execute_query(
                        insert_query,
                        (
                            workflow['name'],
                            workflow['description'],
                            json.dumps(workflow['definition']),
                            json.dumps(workflow['settings']),
                            workflow['enabled'],
                        )
                    )
                    
                    if result:
                        migrated += 1
                        logger.info(f"Migrated job {job_row.get('job_id')} to workflow {result[0]['id']}")
                    
                except Exception as e:
                    logger.error(f"Failed to migrate job {job_row.get('job_id')}: {e}")
                    errors.append({
                        'job_id': job_row.get('job_id'),
                        'error': str(e)
                    })
            
            return {
                'migrated': migrated,
                'skipped': skipped,
                'errors': errors,
                'total': len(jobs),
            }
            
        except Exception as e:
            logger.exception(f"Migration failed: {e}")
            return {'error': str(e), 'migrated': 0}
