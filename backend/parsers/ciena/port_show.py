"""
Ciena port show parser.

Parses output from 'port show' command on Ciena SAOS devices.
"""

from typing import Dict, List
from ..base import BaseParser
from ..registry import register_parser


@register_parser
class CienaPortShowParser(BaseParser):
    """Parser for Ciena 'port show' command output."""
    
    @property
    def name(self) -> str:
        return 'ciena_port_show'
    
    def parse(self, raw_output: str, context: Dict = None) -> List[Dict]:
        """
        Parse 'port show' output into per-port operational info.
        
        Expected row example:
          | 5       |10/100/G | Up |  62d10h13m30s|    |FWD|1000/FD| On |Ena |1000/FD| On |
        
        Args:
            raw_output: Raw command output
            context: Optional context
        
        Returns:
            List of port dictionaries
        """
        ports = []
        if not raw_output:
            return ports
        
        for line in raw_output.splitlines():
            line = line.rstrip('\r\n')
            if not line or not line.startswith('|'):
                continue
            
            parts = [p.strip() for p in line.strip().strip('|').split('|')]
            if len(parts) < 3:
                continue
            
            col0 = parts[0].lower()
            col1 = parts[1].lower()
            
            # Skip header rows
            if col0 in ('port', 'port name') or col1 in ('port', 'type'):
                continue
            
            # Data rows start with numeric port
            if not parts[0] or not parts[0].isdigit():
                continue
            
            port_num = int(parts[0])
            port_type = parts[1]
            link = parts[2]
            mode = parts[6] if len(parts) > 6 else ''
            
            ports.append({
                'cli_port': port_num,
                'port_type': port_type,
                'link': link,
                'mode': mode,
                'raw_output': line,
            })
        
        return ports
    
    def to_dict(self, raw_output: str) -> Dict[int, Dict]:
        """
        Parse output into a dictionary keyed by port number.
        
        Useful for merging with other port data.
        
        Args:
            raw_output: Raw command output
        
        Returns:
            Dictionary mapping port number to port info
        """
        ports = self.parse(raw_output)
        return {p['cli_port']: p for p in ports}
