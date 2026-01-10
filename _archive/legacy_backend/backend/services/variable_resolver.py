"""
Variable Resolver

Resolves {{variable}} template syntax in workflow parameters.
Supports nested property access, array indexing, and built-in variables.
"""

import re
import json
from datetime import datetime
from typing import Dict, Any, Union, List


class VariableResolver:
    """
    Resolves variable references in strings and objects.
    
    Syntax:
        {{variable_name}}           - Simple reference
        {{results.online}}          - Nested property
        {{results[0].ip}}           - Array access
        {{$env.SNMP_COMMUNITY}}     - Environment variable
        {{$input.targets}}          - Input from previous node
        {{$node.ping_scan.online}}  - Output from specific node
        {{$workflow.id}}            - Workflow metadata
        {{$execution.id}}           - Execution metadata
        {{$now}}                    - Current timestamp
        {{$today}}                  - Today's date
    """
    
    # Pattern to match {{variable}} references
    VARIABLE_PATTERN = re.compile(r'\{\{([^}]+)\}\}')
    
    def __init__(self, context: Dict[str, Any] = None):
        """
        Initialize resolver with context.
        
        Args:
            context: ExecutionContext or dict with variables
        """
        self.context = context or {}
        self.variables = self._extract_variables(context)
    
    def _extract_variables(self, context: Dict) -> Dict:
        """Extract variables from context."""
        if hasattr(context, 'variables'):
            return context.variables
        return context.get('variables', {})
    
    def resolve(self, value: Any) -> Any:
        """
        Resolve all variable references in a value.
        
        Args:
            value: String, dict, list, or primitive to resolve
        
        Returns:
            Value with all {{variable}} references replaced
        """
        if isinstance(value, str):
            return self._resolve_string(value)
        elif isinstance(value, dict):
            return {k: self.resolve(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.resolve(item) for item in value]
        else:
            return value
    
    def _resolve_string(self, text: str) -> Any:
        """
        Resolve variable references in a string.
        
        If the entire string is a single variable reference,
        return the actual value (preserving type).
        Otherwise, substitute and return string.
        """
        if not text or '{{' not in text:
            return text
        
        # Check if entire string is a single variable reference
        match = self.VARIABLE_PATTERN.fullmatch(text.strip())
        if match:
            # Return the actual value, preserving type
            return self._get_value(match.group(1).strip())
        
        # Multiple references or mixed content - substitute as strings
        def replace_match(match):
            var_path = match.group(1).strip()
            value = self._get_value(var_path)
            if value is None:
                return ''
            if isinstance(value, (dict, list)):
                return json.dumps(value)
            return str(value)
        
        return self.VARIABLE_PATTERN.sub(replace_match, text)
    
    def _get_value(self, path: str) -> Any:
        """
        Get value from variable path.
        
        Args:
            path: Variable path like "results.online" or "$node.ping.output"
        
        Returns:
            Resolved value or None if not found
        """
        # Handle built-in variables
        if path.startswith('$'):
            return self._get_builtin(path)
        
        # Handle regular variables
        return self._navigate_path(self.variables, path)
    
    def _get_builtin(self, path: str) -> Any:
        """Get built-in variable value."""
        parts = path.split('.', 1)
        builtin = parts[0]
        rest = parts[1] if len(parts) > 1 else None
        
        if builtin == '$now':
            return datetime.utcnow().isoformat()
        
        elif builtin == '$today':
            return datetime.utcnow().strftime('%Y-%m-%d')
        
        elif builtin == '$env':
            import os
            if rest:
                return os.environ.get(rest, '')
            return {}
        
        elif builtin == '$workflow':
            workflow_data = {
                'id': self.context.get('workflow_id', ''),
                'name': self.context.get('workflow_name', ''),
            }
            if rest:
                return workflow_data.get(rest)
            return workflow_data
        
        elif builtin == '$execution':
            execution_data = {
                'id': self.context.get('execution_id', ''),
                'started_at': self.context.get('started_at', ''),
            }
            if rest:
                return execution_data.get(rest)
            return execution_data
        
        elif builtin == '$input':
            # Get input from previous node
            inputs = self.variables.get('_inputs', {})
            if rest:
                return self._navigate_path(inputs, rest)
            return inputs
        
        elif builtin == '$node':
            # Get output from specific node
            node_results = self.context.get('node_results', {})
            if rest:
                parts = rest.split('.', 1)
                node_id = parts[0]
                prop = parts[1] if len(parts) > 1 else 'output_data'
                
                node_result = node_results.get(node_id)
                if node_result:
                    if hasattr(node_result, 'output_data'):
                        data = node_result.output_data
                    else:
                        data = node_result.get('output_data', {})
                    
                    if prop == 'output_data' or prop == 'output':
                        return data
                    return self._navigate_path(data, prop)
            return {}
        
        return None
    
    def _navigate_path(self, obj: Any, path: str) -> Any:
        """
        Navigate a dot-separated path through an object.
        
        Supports:
            - Dot notation: results.online
            - Array indexing: results[0].ip
            - Mixed: devices[0].interfaces[1].name
        """
        if obj is None or not path:
            return obj
        
        # Parse path into segments
        segments = self._parse_path(path)
        
        current = obj
        for segment in segments:
            if current is None:
                return None
            
            if isinstance(segment, int):
                # Array index
                if isinstance(current, (list, tuple)) and 0 <= segment < len(current):
                    current = current[segment]
                else:
                    return None
            else:
                # Property access
                if isinstance(current, dict):
                    current = current.get(segment)
                elif hasattr(current, segment):
                    current = getattr(current, segment)
                else:
                    return None
        
        return current
    
    def _parse_path(self, path: str) -> List[Union[str, int]]:
        """
        Parse a path string into segments.
        
        "results.online" -> ["results", "online"]
        "results[0].ip" -> ["results", 0, "ip"]
        """
        segments = []
        current = ''
        i = 0
        
        while i < len(path):
            char = path[i]
            
            if char == '.':
                if current:
                    segments.append(current)
                    current = ''
            elif char == '[':
                if current:
                    segments.append(current)
                    current = ''
                # Find closing bracket
                j = path.find(']', i)
                if j > i:
                    index_str = path[i+1:j]
                    try:
                        segments.append(int(index_str))
                    except ValueError:
                        # String index (for dict access)
                        segments.append(index_str.strip('"\''))
                    i = j
            elif char == ']':
                pass  # Skip
            else:
                current += char
            
            i += 1
        
        if current:
            segments.append(current)
        
        return segments


def resolve_parameters(parameters: Dict, context: Dict) -> Dict:
    """
    Convenience function to resolve all parameters.
    
    Args:
        parameters: Node parameters dict
        context: Execution context
    
    Returns:
        Parameters with all variables resolved
    """
    resolver = VariableResolver(context)
    return resolver.resolve(parameters)
