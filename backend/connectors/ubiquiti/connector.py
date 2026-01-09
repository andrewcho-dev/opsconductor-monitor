"""
Ubiquiti Direct Device Connector

Polls individual Ubiquiti AirOS access points directly via SSH.
Uses mca-status command to get device metrics.
"""

import logging
import asyncio
import asyncssh
from datetime import datetime
from typing import Dict, Any, Optional, List

from backend.connectors.base import PollingConnector, BaseNormalizer
from backend.core.models import NormalizedAlert, ConnectorStatus
from backend.core.alert_manager import get_alert_manager

from .normalizer import UbiquitiNormalizer

logger = logging.getLogger(__name__)


class UbiquitiConnector(PollingConnector):
    """
    Ubiquiti Direct Device Connector.
    
    Polls individual Ubiquiti AirOS access points directly via SSH.
    Uses mca-status command to get device metrics (CPU, memory, signal, etc).
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.targets = config.get("targets", [])
        self.default_username = config.get("default_username", "ubnt")
        self.default_password = config.get("default_password", "")
        self.thresholds = config.get("thresholds", {
            "cpu_warning": 80,
            "memory_warning": 80,
            "signal_warning": -70,
        })
    
    @property
    def connector_type(self) -> str:
        return "ubiquiti"
    
    def _create_normalizer(self) -> BaseNormalizer:
        return UbiquitiNormalizer()
    
    async def start(self) -> None:
        if not self.targets:
            logger.warning("Ubiquiti connector: no targets configured")
        await super().start()
        logger.info(f"Ubiquiti connector started ({len(self.targets)} devices via SSH, poll interval: {self.poll_interval}s)")
    
    async def stop(self) -> None:
        await super().stop()
        logger.info("Ubiquiti connector stopped")
    
    async def test_connection(self) -> Dict[str, Any]:
        if not self.targets:
            return {"success": False, "message": "No devices configured", "details": None}
        
        success_count = 0
        fail_count = 0
        errors = []
        
        for target in self.targets[:5]:  # Test first 5
            ip = target.get("ip", "")
            username = target.get("username") or self.default_username
            password = target.get("password") or self.default_password
            
            try:
                device_info = await self._get_device_info_ssh(ip, username, password)
                if device_info:
                    success_count += 1
                else:
                    fail_count += 1
                    errors.append(f"{ip}: SSH failed")
            except Exception as e:
                fail_count += 1
                errors.append(f"{ip}: {str(e)[:50]}")
        
        if success_count > 0:
            return {
                "success": True,
                "message": f"Connected to {success_count}/{success_count + fail_count} devices",
                "details": {"success": success_count, "failed": fail_count}
            }
        else:
            return {
                "success": False,
                "message": f"Failed to connect. {errors[0] if errors else 'Check credentials'}",
                "details": {"errors": errors[:3]}
            }
    
    async def poll(self) -> List[NormalizedAlert]:
        alerts = []
        
        if not self.targets:
            return alerts
        
        tasks = [self._poll_device_safe(target) for target in self.targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for target, result in zip(self.targets, results):
            if isinstance(result, Exception):
                logger.debug(f"Ubiquiti poll error for {target.get('ip')}: {result}")
                alerts.append(self._create_offline_alert(target, str(result)))
            elif result:
                alerts.extend(result)
        
        logger.debug(f"Ubiquiti poll: {len(alerts)} alerts from {len(self.targets)} devices")
        return alerts
    
    async def _poll_device_safe(self, target: Dict) -> List[NormalizedAlert]:
        try:
            return await self._poll_device(target)
        except Exception as e:
            raise e
    
    async def _poll_device(self, target: Dict) -> List[NormalizedAlert]:
        ip = target.get("ip", "")
        name = target.get("name", ip)
        username = target.get("username") or self.default_username
        password = target.get("password") or self.default_password
        
        device_info = await self._get_device_info_ssh(ip, username, password)
        
        if device_info:
            return self._check_device_status(ip, name, device_info)
        else:
            return [self._create_offline_alert(target, "SSH connection failed")]
    
    async def _get_device_info_ssh(self, ip: str, username: str, password: str) -> Optional[Dict]:
        """Connect via SSH and run mca-status to get device metrics."""
        try:
            async with asyncssh.connect(
                ip,
                username=username,
                password=password,
                known_hosts=None,
                server_host_key_algs=['ssh-rsa'],
                connect_timeout=10
            ) as conn:
                result = await conn.run('mca-status', check=True)
                return self._parse_mca_status(result.stdout)
        except asyncssh.PermissionDenied:
            logger.warning(f"SSH auth failed for {ip} - check credentials")
            return None
        except asyncssh.ConnectionLost:
            logger.debug(f"SSH connection lost to {ip}")
            return None
        except Exception as e:
            logger.debug(f"SSH failed for {ip}: {e}")
            return None
    
    def _parse_mca_status(self, output: str) -> Dict:
        """Parse mca-status output into a dictionary."""
        data = {"reachable": True}
        
        for line in output.strip().split('\n'):
            # First line is comma-separated: deviceName=X,deviceId=Y,...
            if ',' in line and '=' in line:
                for part in line.split(','):
                    if '=' in part:
                        key, value = part.split('=', 1)
                        data[key] = value
            elif '=' in line:
                key, value = line.split('=', 1)
                # Try to convert numeric values
                try:
                    if '.' in value:
                        data[key] = float(value)
                    else:
                        data[key] = int(value)
                except ValueError:
                    data[key] = value
        return data
    
    def _check_device_status(self, ip: str, name: str, device_info: Dict) -> List[NormalizedAlert]:
        """Check device metrics from mca-status output and generate alerts."""
        alerts = []
        
        # Get device name from mca-status output
        device_name = name or device_info.get("deviceName", ip)
        model = device_info.get("platform", "")
        
        # Check CPU (mca-status: cpuUsage)
        cpu = device_info.get("cpuUsage")
        if cpu is not None:
            try:
                cpu_val = float(cpu)
                if cpu_val > self.thresholds.get("cpu_warning", 80):
                    alerts.append(self._create_alert(ip, device_name, "high_cpu", {
                        "cpu_percent": cpu_val,
                        "hostname": device_info.get("deviceName"),
                        "model": model,
                    }))
            except (ValueError, TypeError):
                pass
        
        # Check memory (mca-status: memTotal, memFree in kB)
        total_ram = device_info.get("memTotal")
        free_ram = device_info.get("memFree")
        if total_ram and free_ram:
            try:
                mem_percent = ((total_ram - free_ram) / total_ram) * 100
                if mem_percent > self.thresholds.get("memory_warning", 80):
                    alerts.append(self._create_alert(ip, device_name, "high_memory", {
                        "memory_percent": round(mem_percent, 1),
                        "hostname": device_info.get("deviceName"),
                        "model": model,
                    }))
            except (ValueError, TypeError, ZeroDivisionError):
                pass
        
        # Check wireless signal (mca-status: signal in dBm)
        signal = device_info.get("signal")
        if signal is not None:
            try:
                signal_val = int(signal)
                if signal_val < self.thresholds.get("signal_warning", -70):
                    alerts.append(self._create_alert(ip, device_name, "signal_degraded", {
                        "signal": signal_val,
                        "noise": device_info.get("noise"),
                        "hostname": device_info.get("deviceName"),
                        "essid": device_info.get("essid"),
                    }))
            except (ValueError, TypeError):
                pass
        
        # Log successful poll
        logger.debug(f"Ubiquiti {ip} ({device_info.get('deviceName', 'unknown')}): "
                    f"CPU={device_info.get('cpuUsage')}%, Signal={device_info.get('signal')}dBm")
        
        return alerts
    
    def _create_alert(self, ip: str, name: str, alert_type: str, metrics: Dict) -> NormalizedAlert:
        raw_data = {
            "device_ip": ip,
            "device_name": name,
            "alert_type": alert_type,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return self.normalizer.normalize(raw_data)
    
    def _create_offline_alert(self, target: Dict, error: str) -> NormalizedAlert:
        ip = target.get("ip", "")
        name = target.get("name", ip)
        
        raw_data = {
            "device_ip": ip,
            "device_name": name,
            "alert_type": "device_offline",
            "metrics": {"error": error},
            "timestamp": datetime.utcnow().isoformat(),
        }
        return self.normalizer.normalize(raw_data)
    
    async def _process_alerts(self, alerts: List[NormalizedAlert]) -> None:
        alert_manager = get_alert_manager()
        for normalized in alerts:
            try:
                await alert_manager.process_alert(normalized)
            except Exception as e:
                logger.warning(f"Failed to process Ubiquiti alert: {e}")
