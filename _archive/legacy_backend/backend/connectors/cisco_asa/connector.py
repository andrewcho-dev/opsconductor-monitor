"""
Cisco ASA Connector

SSH/CLI-based monitoring for Cisco ASA firewalls.
Monitors IPSec VPN tunnels, system health, and interface status.
"""

import logging
import asyncio
import paramiko
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

from backend.connectors.base import PollingConnector, BaseNormalizer
from backend.core.models import NormalizedAlert, ConnectorStatus

from .normalizer import CiscoASANormalizer

logger = logging.getLogger(__name__)

# Thread pool for SSH operations (paramiko is not async-native)
_ssh_executor = ThreadPoolExecutor(max_workers=10)


class CiscoASAConnector(PollingConnector):
    """
    Cisco ASA connector using SSH/CLI.
    
    Monitors:
    - IPSec VPN tunnel status
    - IKE SA status
    - CPU and memory usage
    - Interface status
    - Failover status
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.targets = config.get("targets", [])
        self.thresholds = config.get("thresholds", {
            "cpu_warning": 80,
            "cpu_critical": 95,
            "memory_warning": 80,
            "memory_critical": 95,
        })
        self.monitor_vpn = config.get("monitor_vpn", True)
        self.monitor_interfaces = config.get("monitor_interfaces", True)
        self.monitor_failover = config.get("monitor_failover", True)
        self.monitor_system = config.get("monitor_system", True)
        self.vpn_peers = config.get("vpn_peers", [])  # List of expected VPN peer IPs
        self._connections: Dict[str, paramiko.SSHClient] = {}
    
    @property
    def connector_type(self) -> str:
        return "cisco_asa"
    
    def _create_normalizer(self) -> BaseNormalizer:
        return CiscoASANormalizer()
    
    def _get_connection_sync(self, target: Dict) -> paramiko.SSHClient:
        """Get or create SSH connection to ASA (synchronous)."""
        ip = target.get("ip")
        
        if ip in self._connections:
            try:
                # Test if connection is still alive
                transport = self._connections[ip].get_transport()
                if transport and transport.is_active():
                    return self._connections[ip]
            except Exception:
                pass
            # Connection dead, remove it
            try:
                self._connections[ip].close()
            except Exception:
                pass
            del self._connections[ip]
        
        # Create new connection
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=ip,
            port=target.get("port", 22),
            username=target.get("username", "admin"),
            password=target.get("password", ""),
            timeout=30,
            look_for_keys=False,
            allow_agent=False,
        )
        self._connections[ip] = client
        return client
    
    def _run_command_sync(self, client: paramiko.SSHClient, command: str) -> str:
        """Run a command on the ASA and return output (synchronous).
        
        ASA uses interactive shell, so we use invoke_shell instead of exec_command.
        """
        try:
            # Get or create shell channel
            if not hasattr(client, '_asa_shell') or client._asa_shell is None or client._asa_shell.closed:
                shell = client.invoke_shell(width=200, height=50)
                client._asa_shell = shell
                # Wait for initial prompt and clear buffer
                import time
                time.sleep(1)
                while shell.recv_ready():
                    shell.recv(65535)
                # Disable paging
                shell.send("terminal pager 0\n")
                time.sleep(0.5)
                while shell.recv_ready():
                    shell.recv(65535)
            
            shell = client._asa_shell
            
            # Send command
            shell.send(command + "\n")
            
            # Wait for output
            import time
            time.sleep(1)
            
            output = ""
            timeout = 10
            start = time.time()
            while time.time() - start < timeout:
                if shell.recv_ready():
                    chunk = shell.recv(65535).decode('utf-8', errors='ignore')
                    output += chunk
                    # Check if we got the prompt back
                    if output.rstrip().endswith('#') or output.rstrip().endswith('>'):
                        break
                else:
                    time.sleep(0.2)
            
            # Remove the command echo and prompt from output
            lines = output.split('\n')
            if lines and command in lines[0]:
                lines = lines[1:]
            if lines and (lines[-1].strip().endswith('#') or lines[-1].strip().endswith('>')):
                lines = lines[:-1]
            
            return '\n'.join(lines)
        except Exception as e:
            logger.error(f"Command failed: {command} - {e}")
            return ""
    
    async def _get_connection(self, target: Dict) -> paramiko.SSHClient:
        """Get or create SSH connection to ASA (async wrapper)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_ssh_executor, self._get_connection_sync, target)
    
    async def _run_command(self, client: paramiko.SSHClient, command: str) -> str:
        """Run a command on the ASA and return output (async wrapper)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_ssh_executor, self._run_command_sync, client, command)
    
    async def start(self) -> None:
        if not self.targets:
            logger.warning("No Cisco ASA targets configured")
        await super().start()
        logger.info(f"Cisco ASA connector started (poll interval: {self.poll_interval}s, targets: {len(self.targets)})")
    
    async def stop(self) -> None:
        for conn in self._connections.values():
            try:
                conn.close()
            except Exception:
                pass
        self._connections.clear()
        await super().stop()
        logger.info("Cisco ASA connector stopped")
    
    async def test_connection(self) -> Dict[str, Any]:
        if not self.targets:
            return {"success": False, "message": "No targets configured", "details": None}
        
        results = []
        for target in self.targets:
            try:
                conn = await self._get_connection(target)
                output = await self._run_command(conn, "show version | include Version")
                results.append({
                    "ip": target.get("ip"),
                    "success": True,
                    "version": output.strip()
                })
            except Exception as e:
                results.append({
                    "ip": target.get("ip"),
                    "success": False,
                    "error": str(e)
                })
        
        success = all(r["success"] for r in results)
        return {
            "success": success,
            "message": f"Tested {len(results)} ASA(s)",
            "details": {"results": results}
        }
    
    async def poll(self) -> List[NormalizedAlert]:
        alerts = []
        
        for target in self.targets:
            try:
                target_alerts = await self._poll_asa(target)
                alerts.extend([a for a in target_alerts if a is not None])
            except Exception as e:
                logger.error(f"Error polling ASA {target.get('ip')}: {e}")
                alert = self._create_alert(target, "device_offline", {"error": str(e)})
                if alert:
                    alerts.append(alert)
        
        logger.debug(f"Cisco ASA poll: {len(alerts)} alerts from {len(self.targets)} devices")
        return alerts
    
    async def _poll_asa(self, target: Dict) -> List[Optional[NormalizedAlert]]:
        """Poll a single ASA device."""
        alerts: List[Optional[NormalizedAlert]] = []
        
        try:
            conn = await self._get_connection(target)
            
            # Monitor VPN tunnels
            if self.monitor_vpn:
                vpn_alerts = await self._check_vpn_tunnels(conn, target)
                alerts.extend(vpn_alerts)
            
            # Monitor system health
            if self.monitor_system:
                system_alerts = await self._check_system_health(conn, target)
                alerts.extend(system_alerts)
            
            # Monitor interfaces
            if self.monitor_interfaces:
                interface_alerts = await self._check_interfaces(conn, target)
                alerts.extend(interface_alerts)
            
            # Monitor failover
            if self.monitor_failover:
                failover_alerts = await self._check_failover(conn, target)
                alerts.extend(failover_alerts)
                
        except paramiko.SSHException as e:
            logger.warning(f"SSH error for ASA {target.get('ip')}: {e}")
            alerts.append(self._create_alert(target, "device_offline", {"error": str(e)}))
        except Exception as e:
            logger.warning(f"ASA {target.get('ip')} appears offline: {e}")
            alerts.append(self._create_alert(target, "device_offline", {"error": str(e)}))
        
        return alerts
    
    async def _check_vpn_tunnels(self, conn: paramiko.SSHClient, target: Dict) -> List[Optional[NormalizedAlert]]:
        """Check IPSec VPN tunnel status."""
        alerts = []
        
        # Get configured peers from crypto map (these SHOULD be up)
        crypto_map_output = await self._run_command(conn, "show running-config crypto map | include set peer")
        configured_peers = self._parse_configured_peers(crypto_map_output)
        
        # Get active VPN sessions
        vpn_sessions = await self._run_command(conn, "show vpn-sessiondb l2l")
        active_sessions = self._parse_active_sessions(vpn_sessions)
        
        # Get tunnel-group names for better alert messages
        tunnel_groups = await self._run_command(conn, "show running-config tunnel-group | include tunnel-group.*ipsec-l2l")
        tunnel_names = self._parse_tunnel_names(tunnel_groups)
        
        logger.info(f"ASA {target.get('ip')}: {len(configured_peers)} configured peers, {len(active_sessions)} active sessions")
        
        # Check each configured peer - if not in active sessions, it's DOWN
        for peer_ip in configured_peers:
            if peer_ip not in active_sessions:
                # Find tunnel name if available
                tunnel_name = None
                for name, ip in tunnel_names.items():
                    if ip == peer_ip:
                        tunnel_name = name
                        break
                
                alerts.append(self._create_alert(target, "ipsec_tunnel_down", {
                    "peer_ip": peer_ip,
                    "tunnel_name": tunnel_name or "unknown",
                    "details": f"IPSec tunnel to {peer_ip} ({tunnel_name or 'unknown'}) is DOWN - configured but not active"
                }))
        
        # Also check manually specified peers (if any)
        for peer_ip in self.vpn_peers:
            if peer_ip not in active_sessions and peer_ip not in configured_peers:
                alerts.append(self._create_alert(target, "ipsec_tunnel_down", {
                    "peer_ip": peer_ip,
                    "details": f"IPSec tunnel to {peer_ip} is DOWN - manually monitored peer"
                }))
        
        return alerts
    
    def _parse_configured_peers(self, output: str) -> set:
        """Parse crypto map output to get configured peer IPs."""
        peers = set()
        # Match: crypto map outside_map0 1 set peer 107.91.179.170
        pattern = r'set peer\s+(\d+\.\d+\.\d+\.\d+)'
        for match in re.finditer(pattern, output):
            peers.add(match.group(1))
        return peers
    
    def _parse_active_sessions(self, output: str) -> set:
        """Parse vpn-sessiondb l2l output to get active session peer IPs."""
        sessions = set()
        # Match: IP Addr      : 107.89.21.97
        pattern = r'IP Addr\s*:\s*(\d+\.\d+\.\d+\.\d+)'
        for match in re.finditer(pattern, output):
            sessions.add(match.group(1))
        return sessions
    
    def _parse_tunnel_names(self, output: str) -> Dict[str, str]:
        """Parse tunnel-group config to map names to IPs (best effort)."""
        # This returns tunnel names, we'll need to correlate with peer IPs separately
        names = {}
        # Match: tunnel-group ind_tunnel type ipsec-l2l
        pattern = r'tunnel-group\s+(\S+)\s+type\s+ipsec-l2l'
        for match in re.finditer(pattern, output):
            names[match.group(1)] = None  # IP will be filled in later if possible
        return names
    
    def _parse_vpn_peers(self, ipsec_output: str, ikev1_output: str, ikev2_output: str, vpn_sessions: str) -> Dict[str, Dict]:
        """Parse VPN outputs to get peer status."""
        peers = {}
        
        # Parse IPSec SA output for active tunnels
        # Look for "peer" or "current_peer" lines
        peer_pattern = r'(?:peer|current_peer)[:\s]+(\d+\.\d+\.\d+\.\d+)'
        for match in re.finditer(peer_pattern, ipsec_output, re.IGNORECASE):
            peer_ip = match.group(1)
            if peer_ip not in peers:
                peers[peer_ip] = {"ipsec_active": False, "ike_active": False}
            peers[peer_ip]["ipsec_active"] = True
        
        # Parse IKEv1 SA - look for QM_IDLE state (active)
        ikev1_pattern = r'(\d+\.\d+\.\d+\.\d+)\s+\d+\.\d+\.\d+\.\d+\s+(\w+)'
        for match in re.finditer(ikev1_pattern, ikev1_output):
            peer_ip = match.group(1)
            state = match.group(2)
            if peer_ip not in peers:
                peers[peer_ip] = {"ipsec_active": False, "ike_active": False}
            if state.upper() == "QM_IDLE":
                peers[peer_ip]["ike_active"] = True
                peers[peer_ip]["ike_status"] = state
        
        # Parse IKEv2 SA - look for READY state
        ikev2_pattern = r'(\d+\.\d+\.\d+\.\d+)\s+\d+\s+(\w+)'
        for match in re.finditer(ikev2_pattern, ikev2_output):
            peer_ip = match.group(1)
            state = match.group(2)
            if peer_ip not in peers:
                peers[peer_ip] = {"ipsec_active": False, "ike_active": False}
            if state.upper() == "READY":
                peers[peer_ip]["ike_active"] = True
                peers[peer_ip]["ike_status"] = state
        
        # Parse VPN session DB
        session_pattern = r'Connection\s*:\s*(\S+).*?Peer IP\s*:\s*(\d+\.\d+\.\d+\.\d+)'
        for match in re.finditer(session_pattern, vpn_sessions, re.DOTALL):
            peer_ip = match.group(2)
            if peer_ip not in peers:
                peers[peer_ip] = {"ipsec_active": False, "ike_active": False}
            peers[peer_ip]["session_active"] = True
        
        return peers
    
    def _find_down_tunnels(self, ipsec_output: str, ikev1_output: str, ikev2_output: str) -> List[Dict]:
        """Find tunnels that appear to be down."""
        down_tunnels = []
        
        # Look for IKE SAs not in active state
        ikev1_pattern = r'(\d+\.\d+\.\d+\.\d+)\s+\d+\.\d+\.\d+\.\d+\s+(\w+)'
        for match in re.finditer(ikev1_pattern, ikev1_output):
            peer_ip = match.group(1)
            state = match.group(2)
            if state.upper() not in ("QM_IDLE", "ACTIVE"):
                down_tunnels.append({
                    "peer_ip": peer_ip,
                    "ike_status": state,
                    "details": f"IKEv1 SA to {peer_ip} in state {state}"
                })
        
        return down_tunnels
    
    async def _check_system_health(self, conn: paramiko.SSHClient, target: Dict) -> List[Optional[NormalizedAlert]]:
        """Check CPU and memory usage."""
        alerts = []
        
        # Get CPU usage
        cpu_output = await self._run_command(conn, "show cpu usage")
        cpu_percent = self._parse_cpu_usage(cpu_output)
        
        if cpu_percent is not None:
            if cpu_percent >= self.thresholds.get("cpu_critical", 95):
                alerts.append(self._create_alert(target, "cpu_critical", {
                    "cpu_percent": cpu_percent,
                    "threshold": self.thresholds.get("cpu_critical", 95)
                }))
            elif cpu_percent >= self.thresholds.get("cpu_warning", 80):
                alerts.append(self._create_alert(target, "cpu_high", {
                    "cpu_percent": cpu_percent,
                    "threshold": self.thresholds.get("cpu_warning", 80)
                }))
        
        # Get memory usage
        memory_output = await self._run_command(conn, "show memory")
        memory_percent = self._parse_memory_usage(memory_output)
        
        if memory_percent is not None:
            if memory_percent >= self.thresholds.get("memory_critical", 95):
                alerts.append(self._create_alert(target, "memory_critical", {
                    "memory_percent": memory_percent,
                    "threshold": self.thresholds.get("memory_critical", 95)
                }))
            elif memory_percent >= self.thresholds.get("memory_warning", 80):
                alerts.append(self._create_alert(target, "memory_high", {
                    "memory_percent": memory_percent,
                    "threshold": self.thresholds.get("memory_warning", 80)
                }))
        
        return alerts
    
    def _parse_cpu_usage(self, output: str) -> Optional[float]:
        """Parse CPU usage from show cpu usage output."""
        # Look for "CPU utilization for 5 seconds = X%"
        match = re.search(r'CPU utilization for 5 seconds\s*=\s*(\d+)%', output)
        if match:
            return float(match.group(1))
        
        # Alternative format
        match = re.search(r'(\d+)%\s+CPU', output)
        if match:
            return float(match.group(1))
        
        return None
    
    def _parse_memory_usage(self, output: str) -> Optional[float]:
        """Parse memory usage percentage from show memory output."""
        # Look for "Used memory" and "Free memory" or percentage
        used_match = re.search(r'Used memory\s*:\s*(\d+)', output)
        free_match = re.search(r'Free memory\s*:\s*(\d+)', output)
        
        if used_match and free_match:
            used = int(used_match.group(1))
            free = int(free_match.group(1))
            total = used + free
            if total > 0:
                return (used / total) * 100
        
        # Alternative: look for percentage directly
        match = re.search(r'(\d+)%\s+(?:used|memory)', output, re.IGNORECASE)
        if match:
            return float(match.group(1))
        
        return None
    
    async def _check_interfaces(self, conn: paramiko.SSHClient, target: Dict) -> List[Optional[NormalizedAlert]]:
        """Check interface status."""
        alerts = []
        
        output = await self._run_command(conn, "show interface ip brief")
        
        # Parse interface status
        # Format: Interface    IP-Address      OK? Method Status                Protocol
        lines = output.strip().split('\n')
        for line in lines:
            parts = line.split()
            if len(parts) >= 6:
                interface = parts[0]
                status = parts[4].lower()
                protocol = parts[5].lower()
                
                # Skip management and loopback interfaces
                if 'management' in interface.lower() or 'loopback' in interface.lower():
                    continue
                
                # Alert on down interfaces (but not administratively down)
                if status == 'down' and protocol == 'down':
                    # Check if it's admin down
                    detail_output = await self._run_command(conn, f"show interface {interface}")
                    if 'administratively down' not in detail_output.lower():
                        alerts.append(self._create_alert(target, "interface_down", {
                            "interface": interface,
                            "status": status,
                            "protocol": protocol
                        }))
        
        return alerts
    
    async def _check_failover(self, conn: paramiko.SSHClient, target: Dict) -> List[Optional[NormalizedAlert]]:
        """Check failover status."""
        alerts = []
        
        output = await self._run_command(conn, "show failover")
        
        # Check if failover is configured
        if 'Failover Off' in output or 'not configured' in output.lower():
            return alerts  # Failover not configured, skip
        
        # Check for failover state changes or issues
        if 'Standby Ready' not in output and 'Active' not in output:
            # Neither unit is in a good state
            alerts.append(self._create_alert(target, "failover_issue", {
                "details": "Failover state abnormal",
                "output": output[:500]
            }))
        
        # Check for failed state
        if 'Failed' in output:
            alerts.append(self._create_alert(target, "failover_failed", {
                "details": "Failover unit in Failed state",
                "output": output[:500]
            }))
        
        return alerts
    
    def _create_alert(self, target: Dict, event_type: str, data: Dict) -> Optional[NormalizedAlert]:
        """Create a normalized alert using the normalizer."""
        raw_event = {
            "event_type": event_type,
            "device_ip": target.get("ip"),
            "device_name": target.get("name", target.get("ip")),
            "timestamp": datetime.utcnow().isoformat(),
            **data
        }
        
        return self.normalizer.normalize(raw_event)
