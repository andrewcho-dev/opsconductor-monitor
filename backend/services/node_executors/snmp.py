"""
SNMP Node Executors

Executors for SNMP operations.
"""

from typing import Dict, List, Any
from ..logging_service import get_logger, LogSource

logger = get_logger(__name__, LogSource.SNMP)


class SNMPGetExecutor:
    """Executor for SNMP GET operations."""
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """
        Execute an SNMP GET.
        
        Args:
            node: Node definition with parameters
            context: Execution context
        
        Returns:
            SNMP response data
        """
        params = node.get('data', {}).get('parameters', {})
        target = params.get('target', '')
        community = params.get('community', 'public')
        oids = params.get('oids', '1.3.6.1.2.1.1.1.0')  # sysDescr
        version = params.get('version', '2c')
        
        if not target:
            # Try to get target from context
            targets = context.get('variables', {}).get('online', [])
            if targets:
                target = targets[0]
        
        if not target:
            return {'error': 'No target specified', 'values': {}}
        
        logger.info(
            f"SNMP GET on {target}",
            device_ip=target,
            category='get',
            details={'oids': oids, 'version': version}
        )
        
        try:
            # Try to use pysnmp if available
            result = self._snmp_get_pysnmp(target, community, oids, version)
            if result.get('success'):
                logger.info(f"SNMP GET succeeded on {target}", device_ip=target, category='get')
            else:
                logger.warning(f"SNMP GET failed on {target}: {result.get('error')}", device_ip=target, category='get')
            return result
        except ImportError:
            # Fall back to snmpget command
            return self._snmp_get_command(target, community, oids, version)
    
    def _snmp_get_pysnmp(self, target: str, community: str, oids: str, version: str) -> Dict:
        """Use pysnmp library for SNMP GET."""
        try:
            from pysnmp.hlapi import (
                getCmd, SnmpEngine, CommunityData, UdpTransportTarget,
                ContextData, ObjectType, ObjectIdentity
            )
            
            oid_list = [oid.strip() for oid in oids.split(',')]
            values = {}
            
            for oid in oid_list:
                iterator = getCmd(
                    SnmpEngine(),
                    CommunityData(community, mpModel=1 if version == '2c' else 0),
                    UdpTransportTarget((target, 161), timeout=2, retries=1),
                    ContextData(),
                    ObjectType(ObjectIdentity(oid))
                )
                
                errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
                
                if errorIndication:
                    values[oid] = {'error': str(errorIndication)}
                elif errorStatus:
                    values[oid] = {'error': str(errorStatus)}
                else:
                    for varBind in varBinds:
                        values[str(varBind[0])] = str(varBind[1])
            
            return {
                'target': target,
                'values': values,
                'success': True,
            }
        except Exception as e:
            logger.error(f"SNMP GET failed: {e}")
            return {
                'target': target,
                'error': str(e),
                'values': {},
                'success': False,
            }
    
    def _snmp_get_command(self, target: str, community: str, oids: str, version: str) -> Dict:
        """Use snmpget command for SNMP GET."""
        import subprocess
        
        oid_list = [oid.strip() for oid in oids.split(',')]
        values = {}
        
        version_flag = '-v2c' if version == '2c' else '-v1'
        
        for oid in oid_list:
            try:
                result = subprocess.run(
                    ['snmpget', version_flag, '-c', community, target, oid],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    # Parse output: OID = TYPE: VALUE
                    output = result.stdout.strip()
                    if '=' in output:
                        parts = output.split('=', 1)
                        value = parts[1].strip()
                        # Remove type prefix if present
                        if ':' in value:
                            value = value.split(':', 1)[1].strip()
                        values[oid] = value
                    else:
                        values[oid] = output
                else:
                    values[oid] = {'error': result.stderr.strip()}
            except Exception as e:
                values[oid] = {'error': str(e)}
        
        return {
            'target': target,
            'values': values,
            'success': len([v for v in values.values() if not isinstance(v, dict)]) > 0,
        }


class SNMPWalkExecutor:
    """Executor for SNMP WALK operations."""
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """Execute an SNMP WALK."""
        params = node.get('data', {}).get('parameters', {})
        target = params.get('target', '')
        community = params.get('community', 'public')
        oid = params.get('oid', '1.3.6.1.2.1.2.2')  # ifTable
        version = params.get('version', '2c')
        max_results = int(params.get('max_results', 100))
        
        if not target:
            targets = context.get('variables', {}).get('online', [])
            if targets:
                target = targets[0]
        
        if not target:
            return {'error': 'No target specified', 'results': []}
        
        try:
            return self._snmp_walk_command(target, community, oid, version, max_results)
        except Exception as e:
            return {
                'target': target,
                'error': str(e),
                'results': [],
            }
    
    def _snmp_walk_command(self, target: str, community: str, oid: str, version: str, max_results: int) -> Dict:
        """Use snmpwalk command."""
        import subprocess
        
        version_flag = '-v2c' if version == '2c' else '-v1'
        
        try:
            result = subprocess.run(
                ['snmpwalk', version_flag, '-c', community, target, oid],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            results = []
            for line in result.stdout.strip().split('\n')[:max_results]:
                if '=' in line:
                    parts = line.split('=', 1)
                    result_oid = parts[0].strip()
                    value = parts[1].strip()
                    if ':' in value:
                        value = value.split(':', 1)[1].strip()
                    results.append({
                        'oid': result_oid,
                        'value': value
                    })
            
            return {
                'target': target,
                'base_oid': oid,
                'results': results,
                'count': len(results),
                'success': len(results) > 0,
            }
        except subprocess.TimeoutExpired:
            return {
                'target': target,
                'error': 'SNMP walk timed out',
                'results': [],
            }
