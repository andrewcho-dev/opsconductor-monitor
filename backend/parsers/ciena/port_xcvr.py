"""
Ciena port xcvr show parser.

Parses output from 'port xcvr show' command on Ciena SAOS devices.
"""

from typing import Dict, List
from ..base import BaseParser
from ..registry import register_parser


@register_parser
class CienaPortXcvrParser(BaseParser):
    """Parser for Ciena 'port xcvr show' command output."""
    
    @property
    def name(self) -> str:
        return 'ciena_port_xcvr_show'
    
    def parse(self, raw_output: str, context: Dict = None) -> List[Dict]:
        """
        Parse 'port xcvr show' output into interface dictionaries.
        
        The table has columns:
          Port | Admin State | Oper State | Vendor Name & Part Number | 
          Ciena Rev | Ether Medium & Connector Type | Diag Data
        
        Args:
            raw_output: Raw command output
            context: Optional context (e.g., ip_address)
        
        Returns:
            List of interface dictionaries
        """
        interfaces = []
        if not raw_output:
            return interfaces
        
        for line in raw_output.splitlines():
            line = line.rstrip('\r\n')
            if not line or not line.startswith('|'):
                continue
            
            # Strip leading/trailing '|' and split into columns
            parts = [p.strip() for p in line.strip().strip('|').split('|')]
            if not parts:
                continue
            
            # Skip header rows
            first_col = parts[0].lower()
            if first_col in ('port', 'port#'):
                continue
            
            # Data rows should start with numeric port
            if not parts[0].isdigit():
                continue
            
            # Ensure we have at least up to the Diag column
            if len(parts) < 7:
                continue
            
            port_str, admin_state, oper_state, vendor_part, ciena_rev, medium_connector, diag_data = (
                (parts + [''] * 7)[:7]
            )
            
            if not port_str.isdigit():
                continue
            
            port_num = int(port_str)
            # Use a high offset for interface_index to avoid collision with SNMP ifIndex
            interface_index = 10000 + port_num
            
            # Skip empty ports
            if vendor_part.lower().startswith('empty'):
                continue
            
            # Parse medium and connector
            medium = medium_connector
            connector = ''
            if '/' in medium_connector:
                m, c = medium_connector.split('/', 1)
                medium = m.strip()
                connector = c.strip()
            
            speed = medium  # textual speed/medium description
            
            # Determine operational status
            oper_lower = oper_state.lower()
            status = 'up' if oper_lower.startswith(('ena', 'up')) else 'down'
            
            # Classify optical vs electrical
            is_optical = self._is_optical_interface(medium, connector)
            
            interfaces.append({
                'interface_index': interface_index,
                'interface_name': f'Port {port_num}',
                'cli_port': port_num,
                'is_optical': is_optical,
                'medium': medium,
                'connector': connector,
                'speed': speed,
                'tx_power': '',
                'rx_power': '',
                'temperature': '',
                'status': status,
                'raw_output': line,
            })
        
        return interfaces
    
    def _is_optical_interface(self, medium: str, connector: str) -> bool:
        """
        Determine if interface is optical based on medium/connector.
        
        Args:
            medium: Medium type string
            connector: Connector type string
        
        Returns:
            True if optical interface
        """
        medium_lower = medium.lower()
        connector_lower = connector.lower()
        
        # Optical indicators
        optical_medium_tags = ('lx', 'lr', 'sr', 'zx', 'sx', 'fx')
        optical_connector_tags = ('lc', 'sc', 'fc', 'mtp', 'mpo')
        
        is_optical = (
            any(tag in medium_lower for tag in optical_medium_tags) or
            any(tag in connector_lower for tag in optical_connector_tags)
        )
        
        # Copper indicators take precedence
        copper_tags = ('base-t', 'rj45', 'copper')
        if any(tag in medium_lower for tag in copper_tags) or 'rj45' in connector_lower:
            is_optical = False
        
        return is_optical
