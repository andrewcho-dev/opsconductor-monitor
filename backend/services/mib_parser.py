"""
MIB Parser Service

Parses SNMP MIB files to extract OID definitions, descriptions, and types.
Uses pysmi for MIB parsing and organizes results into logical groups.
"""

import os
import re
import logging
import tempfile
from typing import Dict, List, Optional, Any, Tuple
from pysmi.parser.smi import parserFactory
from pysmi.codegen.pysnmp import PySnmpCodeGen
from pysmi.compiler import MibCompiler
from pysmi.reader.localfile import FileReader
from pysmi.searcher.stub import StubSearcher
from pysmi.writer.callback import CallbackWriter

logger = logging.getLogger(__name__)


class MibParser:
    """
    Parses MIB files and extracts OID definitions.
    """
    
    # SNMP data type mappings
    TYPE_MAPPINGS = {
        'Integer32': 'integer',
        'INTEGER': 'integer',
        'Unsigned32': 'integer',
        'Counter32': 'counter',
        'Counter64': 'counter',
        'Gauge32': 'gauge',
        'TimeTicks': 'timeticks',
        'OCTET STRING': 'string',
        'OctetString': 'string',
        'DisplayString': 'string',
        'IpAddress': 'string',
        'OBJECT IDENTIFIER': 'oid',
        'ObjectIdentifier': 'oid',
        'TruthValue': 'integer',
        'RowStatus': 'integer',
    }
    
    def __init__(self):
        self.parsed_mibs = {}
        
    def parse_mib_file(self, mib_content: str, mib_name: str = None) -> Dict[str, Any]:
        """
        Parse a MIB file content and extract OID definitions.
        
        Args:
            mib_content: The raw MIB file content
            mib_name: Optional name for the MIB
            
        Returns:
            Dictionary with parsed MIB data including groups and OIDs
        """
        # Try to extract MIB name from content if not provided
        if not mib_name:
            match = re.search(r'^([A-Z][A-Z0-9-]*)\s+DEFINITIONS\s*::=\s*BEGIN', mib_content, re.MULTILINE)
            if match:
                mib_name = match.group(1)
            else:
                mib_name = 'UNKNOWN-MIB'
        
        result = {
            'mib_name': mib_name,
            'description': '',
            'enterprise_oid': None,
            'groups': [],
            'errors': []
        }
        
        try:
            # Parse using regex-based extraction (more reliable than pysmi for many MIBs)
            result = self._parse_mib_regex(mib_content, mib_name)
        except Exception as e:
            logger.error(f"Failed to parse MIB {mib_name}: {e}")
            result['errors'].append(str(e))
            
        return result
    
    def _parse_mib_regex(self, content: str, mib_name: str) -> Dict[str, Any]:
        """
        Parse MIB using regex patterns to extract OID definitions.
        This is more reliable than pysmi for many vendor MIBs.
        """
        result = {
            'mib_name': mib_name,
            'description': '',
            'enterprise_oid': None,
            'groups': {},
            'objects': [],
            'errors': []
        }
        
        # Extract module description
        module_desc_match = re.search(
            r'MODULE-IDENTITY\s+.*?DESCRIPTION\s+"([^"]*)"',
            content, re.DOTALL
        )
        if module_desc_match:
            result['description'] = self._clean_description(module_desc_match.group(1))
        
        # Extract enterprise OID from IMPORTS or definitions
        enterprise_match = re.search(
            r'enterprises\s+(\d+)',
            content
        )
        if enterprise_match:
            result['enterprise_oid'] = f"1.3.6.1.4.1.{enterprise_match.group(1)}"
        
        # Find all OBJECT-TYPE definitions
        object_pattern = re.compile(
            r'(\w+)\s+OBJECT-TYPE\s+'
            r'SYNTAX\s+([^\n]+)\s+'
            r'(?:UNITS\s+"([^"]*)"\s+)?'
            r'(?:MAX-)?ACCESS\s+(\w+(?:-\w+)?)\s+'
            r'STATUS\s+(\w+)\s+'
            r'DESCRIPTION\s+"([^"]*)"'
            r'(?:.*?::=\s*\{\s*(\w+)\s+(\d+)\s*\})?',
            re.DOTALL
        )
        
        # Also find simpler OBJECT IDENTIFIER definitions
        oid_pattern = re.compile(
            r'(\w+)\s+OBJECT\s+IDENTIFIER\s*::=\s*\{\s*(\w+)\s+(\d+)\s*\}',
            re.MULTILINE
        )
        
        # Build OID tree from OBJECT IDENTIFIER definitions
        oid_tree = {}
        for match in oid_pattern.finditer(content):
            name, parent, index = match.groups()
            oid_tree[name] = {'parent': parent, 'index': index}
        
        # Parse OBJECT-TYPE definitions
        for match in object_pattern.finditer(content):
            name, syntax, units, access, status, description, parent, index = match.groups()
            
            # Skip deprecated/obsolete
            if status and status.lower() in ('obsolete',):
                continue
            
            # Determine data type
            data_type = self._map_syntax_to_type(syntax)
            
            # Build OID path
            oid_path = self._resolve_oid(parent, index, oid_tree) if parent and index else None
            
            # Determine group from parent
            group_name = self._determine_group(parent, name)
            
            obj = {
                'name': name,
                'oid': oid_path,
                'parent': parent,
                'index': index,
                'syntax': syntax.strip(),
                'data_type': data_type,
                'units': units,
                'access': access,
                'status': status,
                'description': self._clean_description(description),
                'mib_object_name': name,
                'is_table': 'Entry' in name or 'Table' in name,
                'is_index': 'Index' in name.lower() or access == 'not-accessible'
            }
            
            result['objects'].append(obj)
            
            # Add to group
            if group_name not in result['groups']:
                result['groups'][group_name] = {
                    'name': group_name,
                    'description': f'Objects from {group_name}',
                    'base_oid': None,
                    'is_table': False,
                    'objects': []
                }
            result['groups'][group_name]['objects'].append(obj)
            
            # Check if this is a table
            if 'Table' in name:
                result['groups'][group_name]['is_table'] = True
        
        # Convert groups dict to list
        result['groups'] = list(result['groups'].values())
        
        return result
    
    def _map_syntax_to_type(self, syntax: str) -> str:
        """Map MIB SYNTAX to our data type."""
        syntax = syntax.strip()
        
        # Check for direct matches
        for mib_type, our_type in self.TYPE_MAPPINGS.items():
            if mib_type in syntax:
                return our_type
        
        # Check for counter types
        if 'Counter' in syntax:
            return 'counter'
        if 'Gauge' in syntax:
            return 'gauge'
        if 'Integer' in syntax or 'INTEGER' in syntax:
            return 'integer'
        if 'String' in syntax or 'OCTET' in syntax:
            return 'string'
            
        return 'string'  # Default
    
    def _clean_description(self, desc: str) -> str:
        """Clean up MIB description text."""
        if not desc:
            return ''
        # Remove extra whitespace and newlines
        desc = re.sub(r'\s+', ' ', desc)
        return desc.strip()
    
    def _determine_group(self, parent: str, name: str) -> str:
        """Determine logical group for an object."""
        if not parent:
            return 'general'
        
        # Use parent name as group, removing common suffixes
        group = parent
        for suffix in ('Objects', 'MIBObjects', 'Mib', 'MIB', 'Entry', 'Table'):
            if group.endswith(suffix) and len(group) > len(suffix):
                group = group[:-len(suffix)]
                break
        
        return group or 'general'
    
    def _resolve_oid(self, parent: str, index: str, oid_tree: Dict) -> Optional[str]:
        """
        Resolve full OID path from parent reference.
        This is a simplified resolver - full resolution requires MIB imports.
        """
        # Common base OIDs
        base_oids = {
            'enterprises': '1.3.6.1.4.1',
            'mib-2': '1.3.6.1.2.1',
            'snmpV2': '1.3.6.1.6',
            'iso': '1',
            'org': '1.3',
            'dod': '1.3.6',
            'internet': '1.3.6.1',
            'mgmt': '1.3.6.1.2',
            'private': '1.3.6.1.4',
            'system': '1.3.6.1.2.1.1',
            'interfaces': '1.3.6.1.2.1.2',
            'ifEntry': '1.3.6.1.2.1.2.2.1',
        }
        
        if parent in base_oids:
            return f"{base_oids[parent]}.{index}"
        
        # Try to resolve from tree
        path_parts = [index]
        current = parent
        depth = 0
        while current and depth < 20:
            if current in base_oids:
                path_parts.insert(0, base_oids[current])
                return '.'.join(path_parts)
            if current in oid_tree:
                path_parts.insert(0, oid_tree[current]['index'])
                current = oid_tree[current]['parent']
            else:
                break
            depth += 1
        
        # Return partial OID with parent name
        return f"{parent}.{index}"


def parse_mib_content(content: str, mib_name: str = None) -> Dict[str, Any]:
    """
    Convenience function to parse MIB content.
    
    Args:
        content: Raw MIB file content
        mib_name: Optional MIB name
        
    Returns:
        Parsed MIB data
    """
    parser = MibParser()
    return parser.parse_mib_file(content, mib_name)


def discover_oids_from_device(host: str, community: str = 'public', 
                               base_oid: str = '1.3.6.1.4.1') -> List[Dict]:
    """
    Walk a device's SNMP tree to discover available OIDs.
    
    Args:
        host: Device IP address
        community: SNMP community string
        base_oid: Base OID to start walking from
        
    Returns:
        List of discovered OIDs with their values and types
    """
    from pysnmp.hlapi import (
        nextCmd, SnmpEngine, CommunityData,
        UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
    )
    
    discovered = []
    
    try:
        for errorIndication, errorStatus, errorIndex, varBinds in nextCmd(
            SnmpEngine(),
            CommunityData(community),
            UdpTransportTarget((host, 161), timeout=5, retries=1),
            ContextData(),
            ObjectType(ObjectIdentity(base_oid)),
            lexicographicMode=False
        ):
            if errorIndication or errorStatus:
                break
                
            for varBind in varBinds:
                oid_str = str(varBind[0])
                value = varBind[1]
                
                discovered.append({
                    'oid': oid_str,
                    'value': str(value),
                    'type': value.__class__.__name__,
                    'name': oid_str.split('.')[-1]  # Last component as name
                })
                
            # Limit results
            if len(discovered) >= 500:
                break
                
    except Exception as e:
        logger.error(f"SNMP walk failed for {host}: {e}")
        
    return discovered
