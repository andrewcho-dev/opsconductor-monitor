"""
Ciena device parsers package.

Parsers for Ciena SAOS device command output.
Import this module to auto-register all Ciena parsers.
"""

from .port_xcvr import CienaPortXcvrParser
from .port_show import CienaPortShowParser
from .port_diagnostics import CienaPortDiagnosticsParser
from .lldp import CienaLldpRemoteParser

__all__ = [
    'CienaPortXcvrParser',
    'CienaPortShowParser', 
    'CienaPortDiagnosticsParser',
    'CienaLldpRemoteParser',
]


def register_all():
    """
    Ensure all Ciena parsers are registered.
    
    This is called automatically when the module is imported,
    but can be called explicitly if needed.
    """
    pass  # Parsers are registered via @register_parser decorator on import
