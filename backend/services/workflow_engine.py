"""
Workflow Execution Engine

Executes visual workflows by traversing the node graph and running each node's action.
Handles control flow, error handling, and variable passing between nodes.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from .logging_service import get_logger, LogSource
from backend.utils.time import now_utc

logger = get_logger(__name__, LogSource.WORKFLOW)


class NodeStatus(Enum):
    """Status of a node during execution."""
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILURE = 'failure'
    SKIPPED = 'skipped'


@dataclass
class NodeResult:
    """Result of executing a single node."""
    node_id: str
    node_type: str
    status: NodeStatus
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: int = 0


@dataclass
class ExecutionContext:
    """Context passed between nodes during execution."""
    execution_id: str
    workflow_id: str
    variables: Dict[str, Any] = field(default_factory=dict)
    node_results: Dict[str, NodeResult] = field(default_factory=dict)
    current_path: List[str] = field(default_factory=list)


class WorkflowEngine:
    """
    Engine for executing visual workflows.
    
    Traverses the workflow graph starting from trigger nodes,
    executes each node in order, and handles branching/merging.
    """
    
    def __init__(self, db_manager=None):
        """
        Initialize the workflow engine.
        
        Args:
            db_manager: Database manager for storing execution results
        """
        self.db = db_manager
        self.node_executors: Dict[str, Callable] = {}
        self._register_default_executors()
    
    def _register_default_executors(self):
        """Register default node executors."""
        from .node_executors.network import PingExecutor, TracerouteExecutor, PortScanExecutor
        from .node_executors.snmp import SNMPGetExecutor, SNMPWalkExecutor
        from .node_executors.ssh import SSHCommandExecutor
        from .node_executors.database import DBQueryExecutor, DBUpsertExecutor
        from .node_executors.notifications import SlackExecutor, EmailExecutor, WebhookExecutor, TemplatedNotificationExecutor
        from .node_executors.netbox import NetBoxAutodiscoveryExecutor, NetBoxDeviceCreateExecutor, NetBoxLookupExecutor
        from .node_executors.prtg import PRTG_EXECUTORS
        
        # Create executor instances
        ping_exec = PingExecutor()
        traceroute_exec = TracerouteExecutor()
        port_scan_exec = PortScanExecutor()
        snmp_get_exec = SNMPGetExecutor()
        snmp_walk_exec = SNMPWalkExecutor()
        ssh_exec = SSHCommandExecutor()
        db_query_exec = DBQueryExecutor(self.db)
        db_upsert_exec = DBUpsertExecutor(self.db)
        slack_exec = SlackExecutor()
        email_exec = EmailExecutor()
        webhook_exec = WebhookExecutor()
        templated_notify_exec = TemplatedNotificationExecutor()
        netbox_autodiscovery_exec = NetBoxAutodiscoveryExecutor()
        netbox_device_create_exec = NetBoxDeviceCreateExecutor()
        netbox_sites_exec = NetBoxLookupExecutor('sites')
        netbox_roles_exec = NetBoxLookupExecutor('device-roles')
        netbox_types_exec = NetBoxLookupExecutor('device-types')
        
        self.node_executors = {
            # Triggers
            'trigger:manual': self._execute_trigger,
            'trigger:schedule': self._execute_trigger,
            'trigger:webhook': self._execute_trigger,
            
            # Network Discovery
            'network:ping': lambda n, c: ping_exec.execute(n, c),
            'network:traceroute': lambda n, c: traceroute_exec.execute(n, c),
            'network:port-scan': lambda n, c: port_scan_exec.execute(n, c),
            
            # SNMP
            'snmp:get': lambda n, c: snmp_get_exec.execute(n, c),
            'snmp:walk': lambda n, c: snmp_walk_exec.execute(n, c),
            'snmp:set': self._execute_placeholder,
            
            # SSH
            'ssh:command': lambda n, c: ssh_exec.execute(n, c),
            'ssh:script': self._execute_placeholder,
            
            # Database
            'db:query': lambda n, c: db_query_exec.execute(n, c),
            'db:insert': lambda n, c: db_upsert_exec.execute(n, c),
            'db:update': lambda n, c: db_upsert_exec.execute(n, c),
            'db:upsert': lambda n, c: db_upsert_exec.execute(n, c),
            
            # Logic
            'logic:if': self._execute_if,
            'logic:switch': self._execute_placeholder,
            'logic:loop': self._execute_placeholder,
            'logic:merge': self._execute_merge,
            'logic:delay': self._execute_delay,
            
            # Notifications
            'notify:email': lambda n, c: email_exec.execute(n, c),
            'notify:slack': lambda n, c: slack_exec.execute(n, c),
            'notify:webhook': lambda n, c: webhook_exec.execute(n, c),
            'notify:send': lambda n, c: templated_notify_exec.execute(n, c),  # Templated notification
            
            # NetBox
            'netbox:autodiscovery': lambda n, c: netbox_autodiscovery_exec.execute(n, c),
            'netbox:device-create': lambda n, c: netbox_device_create_exec.execute(n, c),
            'netbox:lookup-sites': lambda n, c: netbox_sites_exec.execute(n, c),
            'netbox:lookup-roles': lambda n, c: netbox_roles_exec.execute(n, c),
            'netbox:lookup-device-types': lambda n, c: netbox_types_exec.execute(n, c),
            
            # PRTG - register all PRTG executors
            **{k: lambda n, c, ex=v: ex.execute(n, c) for k, v in PRTG_EXECUTORS.items()},
        }
    
    def register_executor(self, node_type: str, executor: Callable):
        """Register a custom node executor."""
        self.node_executors[node_type] = executor
    
    def execute(self, workflow: Dict, trigger_data: Dict = None) -> Dict:
        """
        Execute a workflow.
        
        Args:
            workflow: Workflow definition with nodes and edges
            trigger_data: Optional data from the trigger
        
        Returns:
            Execution result with status and node results
        """
        execution_id = str(uuid.uuid4())
        started_at = now_utc()
        
        logger.info(
            f"Starting workflow execution {execution_id} for workflow {workflow.get('id')}",
            workflow_id=workflow.get('id'),
            execution_id=execution_id,
            category='execution'
        )
        
        # Create execution context
        context = ExecutionContext(
            execution_id=execution_id,
            workflow_id=workflow.get('id', ''),
            variables={'trigger': trigger_data or {}},
        )
        
        # Parse workflow definition
        definition = workflow.get('definition', {})
        nodes = {n['id']: n for n in definition.get('nodes', [])}
        edges = definition.get('edges', [])
        
        # Build adjacency lists
        outgoing = {}  # node_id -> [(target_id, source_handle, target_handle)]
        incoming = {}  # node_id -> [source_id]
        
        for node_id in nodes:
            outgoing[node_id] = []
            incoming[node_id] = []
        
        for edge in edges:
            source = edge.get('source')
            target = edge.get('target')
            if source in outgoing and target in incoming:
                outgoing[source].append((
                    target,
                    edge.get('sourceHandle', 'success'),
                    edge.get('targetHandle', 'trigger')
                ))
                incoming[target].append(source)
        
        # Find start nodes (triggers with no incoming edges)
        start_nodes = [
            node_id for node_id, sources in incoming.items()
            if len(sources) == 0
        ]
        
        if not start_nodes:
            logger.warning(
                "No start nodes found in workflow",
                workflow_id=workflow.get('id'),
                execution_id=execution_id,
                category='execution'
            )
            return self._create_execution_result(
                execution_id, workflow.get('id'), started_at,
                'failure', context, 'No start nodes found'
            )
        
        # Execute workflow starting from each start node
        try:
            for start_node_id in start_nodes:
                self._execute_node_chain(
                    start_node_id, nodes, outgoing, context
                )
            
            # Determine overall status
            has_failures = any(
                r.status == NodeStatus.FAILURE 
                for r in context.node_results.values()
            )
            status = 'failure' if has_failures else 'success'
            
        except Exception as e:
            logger.exception(
                f"Workflow execution failed: {e}",
                workflow_id=workflow.get('id'),
                execution_id=execution_id,
                category='execution'
            )
            status = 'failure'
            context.variables['error'] = str(e)
        
        return self._create_execution_result(
            execution_id, workflow.get('id'), started_at,
            status, context
        )
    
    def _execute_node_chain(
        self,
        node_id: str,
        nodes: Dict,
        outgoing: Dict,
        context: ExecutionContext,
        from_handle: str = None
    ):
        """
        Execute a node and its successors.
        
        Args:
            node_id: ID of the node to execute
            nodes: All nodes in the workflow
            outgoing: Outgoing edges for each node
            context: Execution context
            from_handle: The source handle that triggered this node
        """
        # Skip if already executed
        if node_id in context.node_results:
            return
        
        node = nodes.get(node_id)
        if not node:
            logger.warning(f"Node {node_id} not found")
            return
        
        # Execute the node
        result = self._execute_single_node(node, context)
        context.node_results[node_id] = result
        
        # Update context variables with node output for downstream nodes
        if result.status == NodeStatus.SUCCESS and result.output_data:
            # Store output under node label or id for reference
            node_label = node.get('data', {}).get('label', node_id)
            context.variables[node_label] = result.output_data
            context.variables[node_id] = result.output_data
            # Also set as 'results' for simple from_input data sources
            context.variables['results'] = result.output_data.get('results', result.output_data)
        
        # Determine which outputs to follow
        outputs_to_follow = self._get_outputs_to_follow(result, node)
        
        # Execute successor nodes
        for target_id, source_handle, target_handle in outgoing.get(node_id, []):
            if source_handle in outputs_to_follow:
                self._execute_node_chain(
                    target_id, nodes, outgoing, context, source_handle
                )
    
    def _execute_single_node(
        self,
        node: Dict,
        context: ExecutionContext
    ) -> NodeResult:
        """
        Execute a single node.
        
        Args:
            node: Node definition
            context: Execution context
        
        Returns:
            NodeResult with status and output
        """
        from .variable_resolver import VariableResolver
        
        node_id = node['id']
        node_type = node.get('data', {}).get('nodeType', 'unknown')
        
        logger.info(
            f"Executing node {node_id} ({node_type})",
            workflow_id=context.workflow_id,
            execution_id=context.execution_id,
            category='node_execution',
            details={'node_id': node_id, 'node_type': node_type}
        )
        
        started_at = now_utc()
        
        try:
            # Resolve variables in node parameters
            resolver = VariableResolver({
                'variables': context.variables,
                'workflow_id': context.workflow_id,
                'execution_id': context.execution_id,
                'node_results': context.node_results,
            })
            
            # Create a copy of the node with resolved parameters
            resolved_node = dict(node)
            if 'data' in resolved_node:
                resolved_node['data'] = dict(resolved_node['data'])
                if 'parameters' in resolved_node['data']:
                    resolved_node['data']['parameters'] = resolver.resolve(
                        resolved_node['data']['parameters']
                    )
            
            # Get executor for this node type
            executor = self.node_executors.get(node_type)
            
            if not executor:
                logger.warning(f"No executor for node type: {node_type}")
                executor = self._execute_placeholder
            
            # Execute the node with resolved parameters
            output_data = executor(resolved_node, context)
            
            finished_at = now_utc()
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)
            
            # Check if the executor returned a failure indicator
            node_failed = False
            error_message = None
            if isinstance(output_data, dict):
                if output_data.get('success') is False:
                    node_failed = True
                    error_message = output_data.get('error') or '; '.join(output_data.get('errors', []))
                elif output_data.get('error'):
                    node_failed = True
                    error_message = output_data.get('error')
            
            if node_failed:
                logger.error(
                    f"Node {node_id} returned failure: {error_message}",
                    workflow_id=context.workflow_id,
                    execution_id=context.execution_id,
                    category='node_execution',
                    details={'node_id': node_id, 'node_type': node_type, 'error': error_message}
                )
                return NodeResult(
                    node_id=node_id,
                    node_type=node_type,
                    status=NodeStatus.FAILURE,
                    output_data=output_data or {},
                    error_message=error_message,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_ms=duration_ms,
                )
            
            return NodeResult(
                node_id=node_id,
                node_type=node_type,
                status=NodeStatus.SUCCESS,
                output_data=output_data or {},
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
            )
            
        except Exception as e:
            logger.error(
                f"Node {node_id} failed: {e}",
                workflow_id=context.workflow_id,
                execution_id=context.execution_id,
                category='node_execution',
                details={'node_id': node_id, 'node_type': node_type, 'error': str(e)}
            )
            finished_at = now_utc()
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)
            
            return NodeResult(
                node_id=node_id,
                node_type=node_type,
                status=NodeStatus.FAILURE,
                error_message=str(e),
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
            )
    
    def _get_outputs_to_follow(self, result: NodeResult, node: Dict) -> List[str]:
        """
        Determine which output handles to follow based on node result.
        
        Args:
            result: Result of node execution
            node: Node definition
        
        Returns:
            List of output handle IDs to follow
        """
        node_type = node.get('data', {}).get('nodeType', '')
        
        # For if/else nodes, follow based on condition result
        if node_type == 'logic:if':
            condition_result = result.output_data.get('condition_result', False)
            return ['true'] if condition_result else ['false']
        
        # For switch nodes, follow the matched case
        if node_type == 'logic:switch':
            matched_case = result.output_data.get('matched_case', 'default')
            return [matched_case, 'default']
        
        # For loop nodes, follow iteration or complete
        if node_type == 'logic:loop':
            loop_completed = result.output_data.get('loop_completed', False)
            if loop_completed:
                return ['complete', 'done']
            return ['each', 'iteration']
        
        # For regular nodes, follow success or failure
        if result.status == NodeStatus.SUCCESS:
            return ['success', 'trigger', 'results', 'online', 'offline', 'data']
        else:
            return ['failure']
    
    def _create_execution_result(
        self,
        execution_id: str,
        workflow_id: str,
        started_at: datetime,
        status: str,
        context: ExecutionContext,
        error_message: str = None
    ) -> Dict:
        """Create the final execution result."""
        finished_at = now_utc()
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        
        node_results = {
            node_id: {
                'node_id': r.node_id,
                'node_type': r.node_type,
                'status': r.status.value,
                'output_data': r.output_data,
                'error_message': r.error_message,
                'duration_ms': r.duration_ms,
            }
            for node_id, r in context.node_results.items()
        }
        
        return {
            'execution_id': execution_id,
            'workflow_id': workflow_id,
            'status': status,
            'started_at': started_at.isoformat(),
            'finished_at': finished_at.isoformat(),
            'duration_ms': duration_ms,
            'node_results': node_results,
            'variables': context.variables,
            'error_message': error_message,
            'nodes_total': len(context.node_results),
            'nodes_completed': sum(
                1 for r in context.node_results.values()
                if r.status == NodeStatus.SUCCESS
            ),
            'nodes_failed': sum(
                1 for r in context.node_results.values()
                if r.status == NodeStatus.FAILURE
            ),
        }
    
    # =========================================================================
    # Node Executors
    # =========================================================================
    
    def _execute_trigger(self, node: Dict, context: ExecutionContext) -> Dict:
        """Execute a trigger node (just passes through)."""
        return {'triggered': True}
    
    def _execute_placeholder(self, node: Dict, context: ExecutionContext) -> Dict:
        """Placeholder executor for unimplemented node types."""
        logger.info(f"Placeholder execution for node {node['id']}")
        return {'placeholder': True, 'message': 'Not yet implemented'}
    
    def _execute_ping(self, node: Dict, context: ExecutionContext) -> Dict:
        """Execute a ping scan node."""
        import subprocess
        
        params = node.get('data', {}).get('parameters', {})
        target_type = params.get('target_type', 'network_range')
        
        # Get targets based on target_type
        targets = []
        if target_type == 'network_range':
            network_range = params.get('network_range', '')
            if network_range:
                # For now, just ping a single IP or expand CIDR
                # In production, use proper CIDR expansion
                targets = [network_range.split('/')[0]]
        elif target_type == 'from_input':
            # Get targets from previous node output
            targets = context.variables.get('targets', [])
        
        count = params.get('count', 3)
        timeout = params.get('timeout', 1)
        
        results = []
        online = []
        offline = []
        
        for target in targets[:10]:  # Limit to 10 for safety
            try:
                result = subprocess.run(
                    ['ping', '-c', str(count), '-W', str(timeout), target],
                    capture_output=True,
                    text=True,
                    timeout=timeout * count + 5
                )
                
                if result.returncode == 0:
                    online.append(target)
                    results.append({
                        'target': target,
                        'status': 'online',
                        'output': result.stdout
                    })
                else:
                    offline.append(target)
                    results.append({
                        'target': target,
                        'status': 'offline',
                        'output': result.stderr
                    })
            except Exception as e:
                offline.append(target)
                results.append({
                    'target': target,
                    'status': 'error',
                    'error': str(e)
                })
        
        return {
            'results': results,
            'online': online,
            'offline': offline,
            'total': len(targets),
            'online_count': len(online),
            'offline_count': len(offline),
        }
    
    def _execute_ssh_command(self, node: Dict, context: ExecutionContext) -> Dict:
        """Execute an SSH command node."""
        # Placeholder - would use paramiko or similar
        params = node.get('data', {}).get('parameters', {})
        command = params.get('command', '')
        
        logger.info(f"SSH command (placeholder): {command}")
        
        return {
            'command': command,
            'output': 'SSH execution not yet implemented',
            'exit_code': 0,
        }
    
    def _execute_if(self, node: Dict, context: ExecutionContext) -> Dict:
        """Execute an if/condition node."""
        params = node.get('data', {}).get('parameters', {})
        condition_type = params.get('condition_type', 'expression')
        
        result = False
        
        if condition_type == 'has_results':
            # Check if previous node has results
            prev_results = context.variables.get('results', [])
            result = len(prev_results) > 0
            
        elif condition_type == 'all_success':
            # Check if all previous nodes succeeded
            result = all(
                r.status == NodeStatus.SUCCESS
                for r in context.node_results.values()
            )
            
        elif condition_type == 'any_failure':
            # Check if any previous node failed
            result = any(
                r.status == NodeStatus.FAILURE
                for r in context.node_results.values()
            )
            
        elif condition_type == 'expression':
            # Evaluate expression
            expression = params.get('expression', 'true')
            result = self._evaluate_expression(expression, context)
        
        return {
            'condition_type': condition_type,
            'condition_result': result,
        }
    
    def _evaluate_expression(self, expression: str, context: ExecutionContext) -> bool:
        """
        Evaluate a condition expression.
        
        Supports:
            - {{value}} == "string"
            - {{value}} != "string"
            - {{value}} > 10
            - {{value}} < 10
            - {{array.length}} > 0
            - {{value}} contains "text"
            - {{value}} isEmpty
            - {{value}} isNotEmpty
        """
        from .variable_resolver import VariableResolver
        
        if not expression:
            return False
        
        expression = expression.strip()
        
        # Simple true/false
        if expression.lower() in ('true', '1', 'yes'):
            return True
        if expression.lower() in ('false', '0', 'no'):
            return False
        
        # Resolve variables first
        resolver = VariableResolver({
            'variables': context.variables,
            'node_results': context.node_results,
        })
        
        try:
            # isEmpty check
            if ' isEmpty' in expression:
                var_part = expression.replace(' isEmpty', '').strip()
                value = resolver._resolve_string(var_part)
                if value is None:
                    return True
                if isinstance(value, (list, dict, str)):
                    return len(value) == 0
                return False
            
            # isNotEmpty check
            if ' isNotEmpty' in expression:
                var_part = expression.replace(' isNotEmpty', '').strip()
                value = resolver._resolve_string(var_part)
                if value is None:
                    return False
                if isinstance(value, (list, dict, str)):
                    return len(value) > 0
                return True
            
            # contains check
            if ' contains ' in expression:
                parts = expression.split(' contains ', 1)
                left = resolver._resolve_string(parts[0].strip())
                right = resolver._resolve_string(parts[1].strip().strip('"\''))
                if isinstance(left, str):
                    return right in left
                if isinstance(left, list):
                    return right in left
                return False
            
            # Comparison operators
            for op in ['==', '!=', '>=', '<=', '>', '<']:
                if op in expression:
                    parts = expression.split(op, 1)
                    left = resolver._resolve_string(parts[0].strip())
                    right = resolver._resolve_string(parts[1].strip().strip('"\''))
                    
                    # Try numeric comparison
                    try:
                        left_num = float(left) if not isinstance(left, (int, float)) else left
                        right_num = float(right) if not isinstance(right, (int, float)) else right
                        
                        if op == '==': return left_num == right_num
                        if op == '!=': return left_num != right_num
                        if op == '>': return left_num > right_num
                        if op == '<': return left_num < right_num
                        if op == '>=': return left_num >= right_num
                        if op == '<=': return left_num <= right_num
                    except (ValueError, TypeError):
                        # String comparison
                        left_str = str(left) if left is not None else ''
                        right_str = str(right) if right is not None else ''
                        
                        if op == '==': return left_str == right_str
                        if op == '!=': return left_str != right_str
                    
                    return False
            
            # If nothing matched, try to evaluate as truthy
            value = resolver._resolve_string(expression)
            return bool(value)
            
        except Exception as e:
            logger.warning(f"Expression evaluation failed: {expression} - {e}")
            return False
    
    def _execute_switch(self, node: Dict, context: ExecutionContext) -> Dict:
        """Execute a switch node (multi-way branch)."""
        from .variable_resolver import VariableResolver
        
        params = node.get('data', {}).get('parameters', {})
        value_expr = params.get('value', '')
        cases = params.get('cases', [])
        
        # Resolve the value to switch on
        resolver = VariableResolver({
            'variables': context.variables,
            'node_results': context.node_results,
        })
        
        switch_value = resolver._resolve_string(value_expr)
        matched_case = 'default'
        
        # Check each case
        for case in cases:
            case_value = case.get('value', '')
            if str(switch_value) == str(case_value):
                matched_case = case.get('id', case_value)
                break
        
        return {
            'switch_value': switch_value,
            'matched_case': matched_case,
        }
    
    def _execute_loop(self, node: Dict, context: ExecutionContext) -> Dict:
        """
        Execute a loop node.
        
        Note: This sets up the loop context. The actual iteration
        is handled by the workflow engine's execution flow.
        """
        from .variable_resolver import VariableResolver
        
        params = node.get('data', {}).get('parameters', {})
        items_expr = params.get('items', '[]')
        item_var = params.get('item_variable', 'item')
        index_var = params.get('index_variable', 'index')
        batch_size = int(params.get('batch_size', 1))
        
        # Resolve the items to loop over
        resolver = VariableResolver({
            'variables': context.variables,
            'node_results': context.node_results,
        })
        
        items = resolver._resolve_string(items_expr)
        if not isinstance(items, list):
            items = [items] if items else []
        
        # Store loop state in context
        context.variables['_loop'] = {
            'items': items,
            'total': len(items),
            'current_index': 0,
            'item_variable': item_var,
            'index_variable': index_var,
            'batch_size': batch_size,
            'completed': False,
        }
        
        # Set first item
        if items:
            context.variables[item_var] = items[0]
            context.variables[index_var] = 0
        
        return {
            'items_count': len(items),
            'batch_size': batch_size,
            'loop_started': True,
        }
    
    def _execute_merge(self, node: Dict, context: ExecutionContext) -> Dict:
        """Execute a merge node (combines multiple inputs)."""
        # Collect outputs from all incoming nodes
        merged_data = {}
        for node_id, result in context.node_results.items():
            if result.output_data:
                merged_data[node_id] = result.output_data
        
        return {
            'merged': True,
            'sources': list(merged_data.keys()),
            'data': merged_data,
        }
    
    def _execute_delay(self, node: Dict, context: ExecutionContext) -> Dict:
        """Execute a delay node."""
        import time
        
        params = node.get('data', {}).get('parameters', {})
        delay_seconds = params.get('delay_seconds', 1)
        
        time.sleep(min(delay_seconds, 60))  # Cap at 60 seconds
        
        return {'delayed': delay_seconds}
