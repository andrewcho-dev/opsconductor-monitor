"""
Network Node Executors

Executors for network discovery and diagnostic nodes.
"""

import subprocess
import ipaddress
import logging
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class PingExecutor:
    """Executor for ping scan nodes."""
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """
        Execute a ping scan.
        
        Args:
            node: Node definition with parameters
            context: Execution context with variables
        
        Returns:
            Results with online/offline hosts
        """
        params = node.get('data', {}).get('parameters', {})
        
        # Get targets
        targets = self._get_targets(params, context)
        
        # Ping parameters
        count = int(params.get('count', 3))
        timeout = int(params.get('timeout', 1))
        concurrency = int(params.get('concurrency', 50))
        
        results = []
        online = []
        offline = []
        
        # Execute pings in parallel
        with ThreadPoolExecutor(max_workers=min(concurrency, len(targets) or 1)) as executor:
            futures = {
                executor.submit(self._ping_host, target, count, timeout): target
                for target in targets
            }
            
            for future in as_completed(futures):
                target = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result['status'] == 'online':
                        online.append(target)
                    else:
                        offline.append(target)
                except Exception as e:
                    logger.error(f"Ping failed for {target}: {e}")
                    offline.append(target)
                    results.append({
                        'target': target,
                        'status': 'error',
                        'error': str(e)
                    })
        
        return {
            'results': results,
            'online': online,
            'offline': offline,
            'total': len(targets),
            'online_count': len(online),
            'offline_count': len(offline),
        }
    
    def _get_targets(self, params: Dict, context) -> List[str]:
        """Get target IPs based on target_type parameter."""
        target_type = params.get('target_type', 'network_range')
        
        if target_type == 'network_range':
            network_range = params.get('network_range', '')
            return self._expand_cidr(network_range)
        
        elif target_type == 'ip_list':
            ip_list = params.get('ip_list', '')
            return [ip.strip() for ip in ip_list.split('\n') if ip.strip()]
        
        elif target_type == 'from_input':
            # Handle both dict and ExecutionContext
            if hasattr(context, 'variables'):
                return context.variables.get('targets', [])
            return context.get('variables', {}).get('targets', [])
        
        elif target_type == 'device_group':
            # Would query database for group members
            return []
        
        return []
    
    def _expand_cidr(self, cidr: str) -> List[str]:
        """Expand CIDR notation to list of IPs."""
        if not cidr:
            return []
        
        try:
            network = ipaddress.ip_network(cidr, strict=False)
            # Limit to /24 or smaller to prevent huge scans
            if network.num_addresses > 256:
                logger.warning(f"Network {cidr} too large, limiting to first 256 hosts")
                return [str(ip) for ip in list(network.hosts())[:256]]
            return [str(ip) for ip in network.hosts()]
        except ValueError as e:
            logger.error(f"Invalid CIDR: {cidr} - {e}")
            # Try as single IP
            return [cidr] if cidr else []
    
    def _ping_host(self, target: str, count: int, timeout: int) -> Dict:
        """Ping a single host."""
        try:
            result = subprocess.run(
                ['ping', '-c', str(count), '-W', str(timeout), target],
                capture_output=True,
                text=True,
                timeout=timeout * count + 5
            )
            
            if result.returncode == 0:
                # Parse response time from output
                rtt = self._parse_ping_rtt(result.stdout)
                return {
                    'target': target,
                    'ip_address': target,  # For scan_results compatibility
                    'status': 'online',
                    'ping_status': 'online',  # For scan_results compatibility
                    'rtt_ms': rtt,
                    'packets_sent': count,
                    'packets_received': count,
                }
            else:
                return {
                    'target': target,
                    'ip_address': target,  # For scan_results compatibility
                    'status': 'offline',
                    'ping_status': 'offline',  # For scan_results compatibility
                    'packets_sent': count,
                    'packets_received': 0,
                }
        except subprocess.TimeoutExpired:
            return {
                'target': target,
                'ip_address': target,  # For scan_results compatibility
                'status': 'timeout',
                'ping_status': 'offline',  # For scan_results compatibility
                'error': 'Ping timed out'
            }
        except Exception as e:
            return {
                'target': target,
                'ip_address': target,  # For scan_results compatibility
                'status': 'error',
                'ping_status': 'offline',  # For scan_results compatibility
                'error': str(e)
            }
    
    def _parse_ping_rtt(self, output: str) -> float:
        """Parse RTT from ping output."""
        try:
            # Look for "time=X.XX ms" pattern
            import re
            match = re.search(r'time[=<](\d+\.?\d*)\s*ms', output)
            if match:
                return float(match.group(1))
        except:
            pass
        return 0.0


class TracerouteExecutor:
    """Executor for traceroute nodes."""
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """Execute a traceroute."""
        params = node.get('data', {}).get('parameters', {})
        target = params.get('target', '')
        max_hops = int(params.get('max_hops', 30))
        
        if not target:
            return {'error': 'No target specified', 'hops': []}
        
        try:
            result = subprocess.run(
                ['traceroute', '-m', str(max_hops), target],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            hops = self._parse_traceroute(result.stdout)
            
            return {
                'target': target,
                'hops': hops,
                'hop_count': len(hops),
                'reached': len(hops) > 0 and hops[-1].get('ip') == target,
            }
        except Exception as e:
            return {
                'target': target,
                'error': str(e),
                'hops': []
            }
    
    def _parse_traceroute(self, output: str) -> List[Dict]:
        """Parse traceroute output into hop list."""
        hops = []
        for line in output.split('\n')[1:]:  # Skip header
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                hop_num = parts[0]
                if hop_num.isdigit():
                    hop = {'hop': int(hop_num)}
                    # Try to extract IP and RTT
                    for part in parts[1:]:
                        if '.' in part and not part.endswith('ms'):
                            hop['ip'] = part.strip('()')
                        elif part.endswith('ms'):
                            hop['rtt_ms'] = float(part.replace('ms', ''))
                    hops.append(hop)
        return hops


class PortScanExecutor:
    """Executor for port scan nodes."""
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """Execute a port scan."""
        import socket
        
        params = node.get('data', {}).get('parameters', {})
        target = params.get('target', '')
        ports_str = params.get('ports', '22,80,443')
        timeout = float(params.get('timeout', 1))
        
        if not target:
            return {'error': 'No target specified', 'open_ports': []}
        
        # Parse ports
        ports = []
        for part in ports_str.split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-')
                ports.extend(range(int(start), int(end) + 1))
            elif part.isdigit():
                ports.append(int(part))
        
        open_ports = []
        closed_ports = []
        
        for port in ports[:100]:  # Limit to 100 ports
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((target, port))
                sock.close()
                
                if result == 0:
                    open_ports.append(port)
                else:
                    closed_ports.append(port)
            except Exception as e:
                logger.debug(f"Port scan error for {target}:{port}: {e}")
                closed_ports.append(port)
        
        return {
            'target': target,
            'open_ports': open_ports,
            'closed_ports': closed_ports,
            'total_scanned': len(ports),
        }
