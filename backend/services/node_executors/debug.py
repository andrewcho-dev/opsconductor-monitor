"""
Debug/Utility Node Executors

Executors for debugging and utility nodes - similar to Node-RED's debug node.
Captures data flowing through the workflow for inspection.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class DebugExecutor:
    """
    Executor for debug nodes - captures and logs data flowing through the workflow.
    
    Like Node-RED's debug node, this captures the input data and makes it
    available in the execution results for inspection.
    """
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """
        Execute a debug node - capture and log input data.
        
        Args:
            node: Node definition with parameters
            context: Execution context with variables and previous node results
        
        Returns:
            Debug output with captured data
        """
        params = node.get('data', {}).get('parameters', {})
        node_id = node.get('id', 'unknown')
        
        # Get parameters
        log_level = params.get('log_level', 'info')
        message = params.get('message', 'Debug point reached')
        log_data = params.get('log_data', True)
        data_fields = params.get('data_fields', '')
        
        # Get input data from context (previous node's output)
        input_data = self._get_input_data(context)
        
        # Filter fields if specified
        captured_data = input_data
        if log_data and data_fields:
            fields = [f.strip() for f in data_fields.split(',') if f.strip()]
            if fields:
                captured_data = self._filter_fields(input_data, fields)
        
        # Create debug output
        timestamp = datetime.utcnow().isoformat() + 'Z'
        debug_output = {
            'timestamp': timestamp,
            'node_id': node_id,
            'message': message,
            'log_level': log_level,
            'data': captured_data if log_data else None,
            'data_type': type(input_data).__name__,
            'data_size': self._get_data_size(input_data),
        }
        
        # Log to backend logs
        log_func = getattr(logger, log_level, logger.info)
        log_func(f"[DEBUG:{node_id}] {message}")
        if log_data:
            # Truncate for logging but keep full data in output
            log_preview = json.dumps(captured_data, default=str)[:500]
            log_func(f"[DEBUG:{node_id}] Data: {log_preview}...")
        
        # Return the captured data - this will be stored in execution results
        # and visible in the UI
        return {
            'debug_output': debug_output,
            'captured_data': captured_data,
            'message': message,
            'pass_through': input_data,  # Pass data through unchanged
        }
    
    def _get_input_data(self, context: Dict) -> Any:
        """Get input data from the previous node's output or context variables."""
        variables = context.get('variables', {})
        node_results = context.get('node_results', {})
        
        # The workflow engine stores each node's output in variables under its label/id
        # Get the most recent result (last executed node before this one)
        if node_results:
            # Get all completed node results sorted by execution order
            completed_results = [
                (nid, nr) for nid, nr in node_results.items()
                if hasattr(nr, 'output_data') and nr.output_data
            ]
            if completed_results:
                # Return the last node's output
                last_node_id, last_result = completed_results[-1]
                return last_result.output_data
        
        # Also check 'results' variable which the engine sets
        if 'results' in variables:
            return variables['results']
        
        # Fall back to trigger data
        return variables.get('trigger', {})
    
    def _filter_fields(self, data: Any, fields: List[str]) -> Any:
        """Filter data to only include specified fields."""
        if not isinstance(data, dict):
            return data
        
        result = {}
        for field in fields:
            # Support nested fields with dot notation
            if '.' in field:
                parts = field.split('.')
                value = data
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        value = None
                        break
                if value is not None:
                    result[field] = value
            elif field in data:
                result[field] = data[field]
        
        return result if result else data
    
    def _get_data_size(self, data: Any) -> Dict:
        """Get size information about the data."""
        if data is None:
            return {'type': 'null', 'count': 0}
        elif isinstance(data, list):
            return {'type': 'array', 'count': len(data)}
        elif isinstance(data, dict):
            return {'type': 'object', 'keys': len(data)}
        elif isinstance(data, str):
            return {'type': 'string', 'length': len(data)}
        else:
            return {'type': type(data).__name__}


class SetVariableExecutor:
    """Executor for setting workflow variables."""
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """Set a variable in the workflow context."""
        params = node.get('data', {}).get('parameters', {})
        
        variable_name = params.get('variable_name', 'myVariable')
        value_source = params.get('value_source', 'input_field')
        
        # Get the value based on source
        if value_source == 'static':
            value = params.get('static_value', '')
        elif value_source == 'expression':
            # TODO: Implement expression evaluation
            value = params.get('expression', '')
        else:  # input_field
            input_field = params.get('input_field', 'data')
            input_data = self._get_input_data(context)
            value = input_data.get(input_field) if isinstance(input_data, dict) else input_data
        
        # Store in context variables
        context.setdefault('variables', {})[variable_name] = value
        
        return {
            'variable_name': variable_name,
            'value': value,
            'scope': params.get('scope', 'workflow'),
        }
    
    def _get_input_data(self, context: Dict) -> Any:
        """Get input data from the previous node's output."""
        variables = context.get('variables', {})
        node_results = context.get('node_results', {})
        
        if node_results:
            completed_results = [
                (nid, nr) for nid, nr in node_results.items()
                if hasattr(nr, 'output_data') and nr.output_data
            ]
            if completed_results:
                last_node_id, last_result = completed_results[-1]
                return last_result.output_data
        
        if 'results' in variables:
            return variables['results']
        
        return variables.get('trigger', {})


class GetVariableExecutor:
    """Executor for getting workflow variables."""
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """Get a variable from the workflow context."""
        params = node.get('data', {}).get('parameters', {})
        
        variable_name = params.get('variable_name', 'myVariable')
        output_field = params.get('output_field', 'value')
        default_value = params.get('default_value', '')
        
        # Get from context variables
        variables = context.get('variables', {})
        value = variables.get(variable_name, default_value)
        
        return {
            output_field: value,
            'variable_name': variable_name,
        }


class AssertExecutor:
    """Executor for assertion nodes - validates conditions."""
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """Execute an assertion check."""
        params = node.get('data', {}).get('parameters', {})
        
        condition = params.get('condition', {})
        fail_message = params.get('fail_message', 'Assertion failed')
        stop_on_fail = params.get('stop_on_fail', False)
        
        # Get input data
        input_data = self._get_input_data(context)
        
        # Evaluate condition
        passed = self._evaluate_condition(condition, input_data)
        
        result = {
            'passed': passed,
            'condition': condition,
            'input_data': input_data,
        }
        
        if not passed:
            result['error_message'] = fail_message
            if stop_on_fail:
                raise AssertionError(fail_message)
        
        return result
    
    def _get_input_data(self, context: Dict) -> Any:
        """Get input data from the previous node's output."""
        variables = context.get('variables', {})
        node_results = context.get('node_results', {})
        
        if node_results:
            completed_results = [
                (nid, nr) for nid, nr in node_results.items()
                if hasattr(nr, 'output_data') and nr.output_data
            ]
            if completed_results:
                last_node_id, last_result = completed_results[-1]
                return last_result.output_data
        
        if 'results' in variables:
            return variables['results']
        
        return variables.get('trigger', {})
    
    def _evaluate_condition(self, condition: Dict, data: Any) -> bool:
        """Evaluate a condition against data."""
        field = condition.get('field', '')
        operator = condition.get('operator', 'exists')
        value = condition.get('value', '')
        
        # Get field value from data
        if field and isinstance(data, dict):
            field_value = data.get(field)
        else:
            field_value = data
        
        # Evaluate based on operator
        if operator == 'exists':
            return field_value is not None
        elif operator == 'not_exists':
            return field_value is None
        elif operator == 'equals':
            return str(field_value) == str(value)
        elif operator == 'not_equals':
            return str(field_value) != str(value)
        elif operator == 'contains':
            return str(value) in str(field_value) if field_value else False
        elif operator == 'greater_than':
            try:
                return float(field_value) > float(value)
            except (TypeError, ValueError):
                return False
        elif operator == 'less_than':
            try:
                return float(field_value) < float(value)
            except (TypeError, ValueError):
                return False
        elif operator == 'is_empty':
            return not field_value or (isinstance(field_value, (list, dict, str)) and len(field_value) == 0)
        elif operator == 'is_not_empty':
            return field_value and (not isinstance(field_value, (list, dict, str)) or len(field_value) > 0)
        
        return False
