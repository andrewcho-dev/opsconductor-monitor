"""
Ciena LLDP neighbors parser.

Parses output from 'lldp show neighbors' command on Ciena SAOS devices.
"""

import re
from typing import Dict, List
from ..base import BaseParser
from ..registry import register_parser


@register_parser
class CienaLldpRemoteParser(BaseParser):
    """Parser for Ciena 'lldp show neighbors' command output."""
    
    @property
    def name(self) -> str:
        return 'ciena_lldp_neighbors'
    
    def parse(self, raw_output: str, context: Dict = None) -> List[Dict]:
        """
        Parse 'lldp show neighbors' output into neighbor info.
        
        Args:
            raw_output: Raw command output
            context: Optional context
        
        Returns:
            List of neighbor dictionaries with local_port as key info
        """
        neighbors_dict = self._parse_to_dict(raw_output)
        
        # Convert to list format
        neighbors = []
        for local_port, neighbor_info in neighbors_dict.items():
            neighbor_info['local_port'] = local_port
            neighbors.append(neighbor_info)
        
        return neighbors
    
    def _parse_to_dict(self, output: str) -> Dict[int, Dict]:
        """
        Parse output into dictionary keyed by local port.
        
        Args:
            output: Raw command output
        
        Returns:
            Dictionary mapping local port to neighbor info
        """
        neighbors = {}
        if not output:
            return neighbors
        
        # Match a new neighbor row: | <local> | <remote-port> | <info> |
        new_neighbor_re = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|?$")
        # Match continuation info row: |       |               | <info> |
        cont_re = re.compile(r"^\|\s*\|\s*\|\s*(.*?)\s*\|?$")
        
        current_local = None
        current_neighbor = None
        current_info_lines = []
        
        for line in output.splitlines():
            line = line.rstrip('\r\n')
            if not line or not line.startswith('|'):
                continue
            
            m_new = new_neighbor_re.match(line)
            if m_new:
                # Flush previous neighbor
                if current_local is not None and current_neighbor is not None:
                    if current_info_lines and 'lldp_raw_info' not in current_neighbor:
                        current_neighbor['lldp_raw_info'] = '\n'.join(current_info_lines)
                    neighbors[current_local] = current_neighbor
                
                local_port = int(m_new.group(1))
                remote_port = m_new.group(2).strip()
                info_text = m_new.group(3).strip()
                
                current_local = local_port
                current_neighbor = {
                    'lldp_remote_port': remote_port,
                }
                current_info_lines = []
                
                if info_text:
                    current_info_lines.append(info_text)
                    self._parse_info_line(info_text, current_neighbor)
                continue
            
            # Continuation line: additional info for current neighbor
            m_cont = cont_re.match(line)
            if m_cont and current_local is not None and current_neighbor is not None:
                info_text = m_cont.group(1).strip()
                if not info_text:
                    continue
                current_info_lines.append(info_text)
                self._parse_info_line(info_text, current_neighbor)
        
        # Flush last neighbor
        if current_local is not None and current_neighbor is not None:
            if current_info_lines and 'lldp_raw_info' not in current_neighbor:
                current_neighbor['lldp_raw_info'] = '\n'.join(current_info_lines)
            neighbors[current_local] = current_neighbor
        
        return neighbors
    
    def _parse_info_line(self, line: str, neighbor: Dict) -> None:
        """
        Parse a single info line and update neighbor dict.
        
        Args:
            line: Info line text
            neighbor: Neighbor dictionary to update
        """
        text = line.strip()
        if not text:
            return
        
        lower = text.lower()
        
        if lower.startswith('chassis id:'):
            neighbor['lldp_remote_chassis_id'] = text.split(':', 1)[1].strip()
        elif lower.startswith('mgmt addr:'):
            addr = text.split(':', 1)[1].strip()
            if addr:
                neighbor['lldp_remote_mgmt_addr'] = addr
        elif lower.startswith('system name:'):
            neighbor['lldp_remote_system_name'] = text.split(':', 1)[1].strip()
    
    def to_dict(self, raw_output: str) -> Dict[int, Dict]:
        """
        Parse output into dictionary keyed by local port.
        
        Useful for merging with other port data.
        
        Args:
            raw_output: Raw command output
        
        Returns:
            Dictionary mapping local port to neighbor info
        """
        return self._parse_to_dict(raw_output)
