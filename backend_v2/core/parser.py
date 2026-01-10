"""
Parser Engine

Apply addon parse rules to raw data. Supports multiple parser types:
- json: JSONPath extraction
- snmp: SNMP varbind mapping
- regex: Regular expression extraction
- grok: Grok pattern matching (like Logstash)
- key_value: Key-value pair parsing
"""

import re
import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ParsedAlert:
    """Result of parsing raw data through addon rules."""
    addon_id: str
    alert_type: str
    device_ip: str
    device_name: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[datetime] = None
    is_clear: bool = False
    raw_data: Dict = field(default_factory=dict)
    fields: Dict = field(default_factory=dict)


class Parser:
    """
    Parse engine that applies addon rules to raw data.
    
    Usage:
        parser = Parser()
        result = parser.parse(raw_data, addon.manifest)
    """
    
    # Built-in Grok patterns
    GROK_PATTERNS = {
        'INT': r'(?:[+-]?(?:[0-9]+))',
        'NUMBER': r'(?:[+-]?(?:(?:[0-9]+(?:\.[0-9]+)?)|(?:\.[0-9]+)))',
        'WORD': r'\b\w+\b',
        'NOTSPACE': r'\S+',
        'SPACE': r'\s*',
        'DATA': r'.*?',
        'GREEDYDATA': r'.*',
        'IP': r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)',
        'IPV6': r'(?:[0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4}',
        'MAC': r'(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}',
        'HOSTNAME': r'\b(?:[0-9A-Za-z][0-9A-Za-z-]{0,62})(?:\.(?:[0-9A-Za-z][0-9A-Za-z-]{0,62}))*\.?\b',
        'SYSLOGTIMESTAMP': r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}',
        'TIMESTAMP_ISO8601': r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?',
    }
    
    def parse(self, raw_data: Any, manifest: Dict, addon_id: str = None) -> Optional[ParsedAlert]:
        """
        Parse raw data using addon manifest rules.
        
        Args:
            raw_data: Raw data from source (dict, string, etc.)
            manifest: Addon manifest with parser config
            addon_id: Addon ID for the result
            
        Returns:
            ParsedAlert or None if parsing fails
        """
        parser_config = manifest.get('parser', {})
        parser_type = parser_config.get('type', 'json')
        
        try:
            if parser_type == 'json':
                fields = self._parse_json(raw_data, parser_config)
            elif parser_type == 'snmp':
                fields = self._parse_snmp(raw_data, manifest)
            elif parser_type == 'regex':
                fields = self._parse_regex(raw_data, parser_config)
            elif parser_type == 'grok':
                fields = self._parse_grok(raw_data, parser_config)
            elif parser_type == 'key_value':
                fields = self._parse_key_value(raw_data, parser_config)
            else:
                logger.warning(f"Unknown parser type: {parser_type}")
                fields = {}
            
            if not fields:
                return None
            
            # Apply transformations
            transformations = manifest.get('transformations', {})
            fields = self._apply_transformations(fields, transformations)
            
            # Extract required fields
            alert_type = fields.get('alert_type', 'unknown')
            device_ip = fields.get('device_ip', '')
            device_name = fields.get('device_name')
            message = fields.get('message', '')
            
            # Check for clear event
            is_clear = self._is_clear_event(alert_type, fields, manifest)
            
            # Parse timestamp
            timestamp = self._parse_timestamp(fields.get('timestamp'))
            
            return ParsedAlert(
                addon_id=addon_id or manifest.get('id', 'unknown'),
                alert_type=alert_type,
                device_ip=device_ip,
                device_name=device_name,
                message=message,
                timestamp=timestamp,
                is_clear=is_clear,
                raw_data=raw_data if isinstance(raw_data, dict) else {'raw': raw_data},
                fields=fields
            )
            
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return None
    
    def _parse_json(self, data: Dict, config: Dict) -> Dict:
        """Parse JSON data using JSONPath-like field mappings."""
        if not isinstance(data, dict):
            return {}
        
        field_mappings = config.get('field_mappings', {})
        result = {}
        
        for target_field, json_path in field_mappings.items():
            value = self._extract_jsonpath(data, json_path)
            if value is not None:
                result[target_field] = value
        
        return result
    
    def _extract_jsonpath(self, data: Dict, path: str) -> Any:
        """Extract value using simplified JSONPath ($.field.subfield)."""
        if not path.startswith('$.'):
            return data.get(path)
        
        parts = path[2:].split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                current = current[idx] if idx < len(current) else None
            else:
                return None
            
            if current is None:
                return None
        
        return current
    
    def _parse_snmp(self, data: Dict, manifest: Dict) -> Dict:
        """Parse SNMP trap data using varbind mappings."""
        result = {}
        
        # Get varbind mappings from manifest
        snmp_config = manifest.get('snmp_trap', {})
        varbind_mappings = snmp_config.get('varbind_mappings', {})
        
        # Source IP is typically in trap metadata
        if 'source_ip' in data:
            result['device_ip'] = data['source_ip']
        
        # Map trap OID to alert type
        trap_oid = data.get('trap_oid', data.get('oid', ''))
        trap_definitions = snmp_config.get('trap_definitions', {})
        
        if trap_oid in trap_definitions:
            trap_def = trap_definitions[trap_oid]
            result['alert_type'] = trap_def.get('alert_type', 'unknown')
            result['message'] = trap_def.get('description', '')
        
        # Extract varbind values
        varbinds = data.get('varbinds', {})
        for oid, field_name in varbind_mappings.items():
            if oid in varbinds:
                result[field_name] = varbinds[oid]
        
        return result
    
    def _parse_regex(self, data: str, config: Dict) -> Dict:
        """Parse string data using regex pattern."""
        if not isinstance(data, str):
            data = str(data)
        
        pattern = config.get('pattern', '')
        field_names = config.get('fields', [])
        
        match = re.search(pattern, data)
        if not match:
            return {}
        
        result = {}
        groups = match.groups()
        
        for i, field_name in enumerate(field_names):
            if i < len(groups):
                result[field_name] = groups[i]
        
        return result
    
    def _parse_grok(self, data: str, config: Dict) -> Dict:
        """Parse string using Grok patterns."""
        if not isinstance(data, str):
            data = str(data)
        
        pattern = config.get('pattern', '')
        custom_patterns = config.get('custom_patterns', {})
        
        # Merge custom patterns with built-in
        all_patterns = {**self.GROK_PATTERNS, **custom_patterns}
        
        # Convert Grok pattern to regex with named groups
        regex_pattern = self._grok_to_regex(pattern, all_patterns)
        
        match = re.search(regex_pattern, data)
        if not match:
            return {}
        
        return match.groupdict()
    
    def _grok_to_regex(self, pattern: str, patterns: Dict[str, str]) -> str:
        """Convert Grok pattern to Python regex with named groups."""
        result = pattern
        
        # Replace %{PATTERN:name} with named capture group
        def replace_grok(match):
            pattern_name = match.group(1)
            field_name = match.group(2) if match.group(2) else None
            
            if pattern_name in patterns:
                regex = patterns[pattern_name]
                if field_name:
                    return f'(?P<{field_name}>{regex})'
                return f'({regex})'
            return match.group(0)
        
        result = re.sub(r'%\{(\w+)(?::(\w+))?\}', replace_grok, result)
        return result
    
    def _parse_key_value(self, data: str, config: Dict) -> Dict:
        """Parse key-value pairs from string."""
        if not isinstance(data, str):
            data = str(data)
        
        delimiter = config.get('delimiter', ':')
        trim = config.get('trim', True)
        field_mappings = config.get('field_mappings', {})
        
        result = {}
        
        for line in data.split('\n'):
            if delimiter in line:
                parts = line.split(delimiter, 1)
                key = parts[0].strip() if trim else parts[0]
                value = parts[1].strip() if trim else parts[1]
                
                # Map to target field name if specified
                target_field = field_mappings.get(key, key)
                result[target_field] = value
        
        return result
    
    def _apply_transformations(self, fields: Dict, transformations: Dict) -> Dict:
        """Apply transformations to extracted fields."""
        result = fields.copy()
        
        for field_name, transform in transformations.items():
            if field_name not in result:
                continue
            
            value = result[field_name]
            transform_type = transform.get('type', '')
            
            if transform_type == 'lookup':
                lookup_map = transform.get('map', {})
                result[field_name] = lookup_map.get(str(value), value)
            
            elif transform_type == 'datetime':
                fmt = transform.get('format', '%Y-%m-%d %H:%M:%S')
                try:
                    result[field_name] = datetime.strptime(str(value), fmt)
                except ValueError:
                    pass
            
            elif transform_type == 'extract_ip':
                ip_pattern = transform.get('pattern', r'(\d+\.\d+\.\d+\.\d+)')
                match = re.search(ip_pattern, str(value))
                if match:
                    result[field_name] = match.group(1)
            
            elif transform_type == 'lowercase':
                result[field_name] = str(value).lower()
            
            elif transform_type == 'uppercase':
                result[field_name] = str(value).upper()
        
        return result
    
    def _is_clear_event(self, alert_type: str, fields: Dict, manifest: Dict) -> bool:
        """Determine if this is a clear/recovery event."""
        clear_config = manifest.get('clear_events', {})
        method = clear_config.get('method', 'suffix')
        
        if method == 'suffix':
            suffix = clear_config.get('clear_suffix', '_clear')
            return alert_type.endswith(suffix)
        
        elif method == 'field_value':
            field = clear_config.get('clear_field', 'status')
            clear_values = clear_config.get('clear_values', ['clear', 'ok', 'resolved'])
            value = str(fields.get(field, '')).lower()
            return value in [v.lower() for v in clear_values]
        
        elif method == 'oid_pair':
            # For SNMP, clear is determined by trap_receiver based on OID
            return fields.get('_is_clear', False)
        
        return False
    
    def _parse_timestamp(self, value: Any) -> Optional[datetime]:
        """Parse timestamp from various formats."""
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return value
        
        value = str(value)
        
        # Try common formats
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        
        return None


# Global parser instance
_parser: Optional[Parser] = None


def get_parser() -> Parser:
    """Get global parser instance."""
    global _parser
    if _parser is None:
        _parser = Parser()
    return _parser


def parse(raw_data: Any, manifest: Dict, addon_id: str = None) -> Optional[ParsedAlert]:
    """Convenience function to parse using global parser."""
    return get_parser().parse(raw_data, manifest, addon_id)
