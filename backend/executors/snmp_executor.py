"""
SNMP executor.

Executes SNMP queries against targets.
"""

from typing import Dict, List, Optional
from .base import BaseExecutor
from .registry import register_executor


@register_executor
class SNMPExecutor(BaseExecutor):
    """Executor for SNMP queries."""
    
    @property
    def executor_type(self) -> str:
        return 'snmp'
    
    def get_default_config(self) -> Dict:
        """Get default SNMP configuration."""
        return {
            'timeout': 5,
            'retries': 1,
            'community': 'public',
            'version': '2c',
            'port': 161,
        }
    
    def execute(self, target: str, command: str, config: Dict = None) -> Dict:
        """
        Execute an SNMP query against a target.
        
        Args:
            target: Target IP address or hostname
            command: OID to query (e.g., '1.3.6.1.2.1.1.1.0' for sysDescr)
            config: SNMP configuration (community, version, timeout)
        
        Returns:
            Dict with success, output, error, duration
        """
        import time
        start_time = time.time()
        
        config = config or {}
        timeout = config.get('timeout', 5)
        community = config.get('community', 'public')
        version = config.get('version', '2c')
        port = config.get('port', 161)
        
        oid = command  # The "command" is the OID to query
        
        try:
            from pysnmp.hlapi import (
                getCmd, SnmpEngine, CommunityData, UdpTransportTarget,
                ContextData, ObjectType, ObjectIdentity
            )
            
            # Build SNMP version
            if version == '1':
                mp_model = 0
            else:
                mp_model = 1  # SNMPv2c
            
            # Execute SNMP GET
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=mp_model),
                UdpTransportTarget((target, port), timeout=timeout, retries=config.get('retries', 1)),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            if errorIndication:
                return {
                    'success': False,
                    'output': '',
                    'error': str(errorIndication),
                    'duration': time.time() - start_time,
                }
            
            if errorStatus:
                return {
                    'success': False,
                    'output': '',
                    'error': f'{errorStatus.prettyPrint()} at {errorIndex}',
                    'duration': time.time() - start_time,
                }
            
            # Extract values
            results = []
            for varBind in varBinds:
                oid_str = str(varBind[0])
                value = varBind[1].prettyPrint()
                results.append({
                    'oid': oid_str,
                    'value': value,
                })
            
            return {
                'success': True,
                'output': results[0]['value'] if results else '',
                'results': results,
                'error': None,
                'duration': time.time() - start_time,
            }
            
        except ImportError:
            return {
                'success': False,
                'output': '',
                'error': 'pysnmp library not installed',
                'duration': time.time() - start_time,
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'duration': time.time() - start_time,
            }
    
    def get_bulk(
        self, 
        target: str, 
        oid: str, 
        config: Dict = None,
        max_repetitions: int = 25
    ) -> Dict:
        """
        Execute an SNMP GETBULK query.
        
        Args:
            target: Target IP address
            oid: Base OID to query
            config: SNMP configuration
            max_repetitions: Max repetitions for bulk query
        
        Returns:
            Dict with success, results list, error
        """
        import time
        start_time = time.time()
        
        config = config or {}
        timeout = config.get('timeout', 5)
        community = config.get('community', 'public')
        port = config.get('port', 161)
        
        try:
            from pysnmp.hlapi import (
                bulkCmd, SnmpEngine, CommunityData, UdpTransportTarget,
                ContextData, ObjectType, ObjectIdentity
            )
            
            results = []
            
            for (errorIndication, errorStatus, errorIndex, varBinds) in bulkCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=1),
                UdpTransportTarget((target, port), timeout=timeout),
                ContextData(),
                0, max_repetitions,
                ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False
            ):
                if errorIndication:
                    return {
                        'success': False,
                        'results': results,
                        'error': str(errorIndication),
                        'duration': time.time() - start_time,
                    }
                
                if errorStatus:
                    return {
                        'success': False,
                        'results': results,
                        'error': f'{errorStatus.prettyPrint()} at {errorIndex}',
                        'duration': time.time() - start_time,
                    }
                
                for varBind in varBinds:
                    results.append({
                        'oid': str(varBind[0]),
                        'value': varBind[1].prettyPrint(),
                    })
            
            return {
                'success': True,
                'results': results,
                'error': None,
                'duration': time.time() - start_time,
            }
            
        except ImportError:
            return {
                'success': False,
                'results': [],
                'error': 'pysnmp library not installed',
                'duration': time.time() - start_time,
            }
        except Exception as e:
            return {
                'success': False,
                'results': [],
                'error': str(e),
                'duration': time.time() - start_time,
            }
    
    def check_agent(self, target: str, config: Dict = None) -> bool:
        """
        Check if SNMP agent is responding.
        
        Args:
            target: Target IP address
            config: SNMP configuration
        
        Returns:
            True if agent responds
        """
        # Query sysDescr.0 as a simple check
        result = self.execute(target, '1.3.6.1.2.1.1.1.0', config)
        return result.get('success', False)
