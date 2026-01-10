"""
Ciena port xcvr diagnostics parser.

Parses output from 'port xcvr show port <N> diagnostics' command.
"""

from typing import Dict, List, Tuple, Optional
from ..base import BaseParser
from ..registry import register_parser


@register_parser
class CienaPortDiagnosticsParser(BaseParser):
    """Parser for Ciena 'port xcvr show port <N> diagnostics' command output."""
    
    @property
    def name(self) -> str:
        return 'ciena_port_xcvr_diagnostics'
    
    def parse(self, raw_output: str, context: Dict = None) -> List[Dict]:
        """
        Parse port diagnostics output into power/temperature readings.
        
        Args:
            raw_output: Raw command output
            context: Optional context with interface info
        
        Returns:
            List with single dictionary containing tx_power, rx_power, temperature
        """
        tx_power, rx_power, temperature = self._extract_diagnostics(raw_output)
        
        result = {
            'tx_power': tx_power,
            'rx_power': rx_power,
            'temperature': temperature,
            'has_power_reading': tx_power is not None or rx_power is not None,
        }
        
        # Add context info if provided
        if context:
            result['ip_address'] = context.get('ip_address')
            result['interface_index'] = context.get('interface_index')
            result['interface_name'] = context.get('interface_name')
            result['cli_port'] = context.get('cli_port')
        
        return [result]
    
    def _extract_diagnostics(self, output: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Extract TX power, RX power, and temperature from diagnostics output.
        
        Args:
            output: Raw diagnostics output
        
        Returns:
            Tuple of (tx_power, rx_power, temperature) as floats or None
        """
        tx_dbm = None
        rx_dbm = None
        temperature = None
        
        if not output:
            return tx_dbm, rx_dbm, temperature
        
        for line in output.splitlines():
            line = line.rstrip('\r\n')
            if not line or not line.startswith('|'):
                continue
            
            parts = [p.strip() for p in line.strip().strip('|').split('|')]
            if len(parts) < 2:
                continue
            
            label = parts[0].lower()
            value = parts[1].strip()
            
            # Parse TX power
            if tx_dbm is None and 'tx power' in label and 'dbm' in label:
                tx_dbm = self._parse_float(value)
            # Parse RX power
            elif rx_dbm is None and 'rx power' in label and 'dbm' in label:
                rx_dbm = self._parse_float(value)
            # Parse temperature
            elif temperature is None and ('temperature' in label or 'temp' in label) and 'c' in label.lower():
                temperature = self._parse_float(value)
            
            # Early exit if all values found
            if tx_dbm is not None and rx_dbm is not None and temperature is not None:
                break
        
        return tx_dbm, rx_dbm, temperature
    
    def _parse_float(self, value: str) -> Optional[float]:
        """
        Parse a string value to float.
        
        Args:
            value: String value to parse
        
        Returns:
            Float value or None if parsing fails
        """
        if not value:
            return None
        try:
            # Remove any non-numeric characters except minus and decimal
            cleaned = ''.join(c for c in value if c.isdigit() or c in '.-')
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None
