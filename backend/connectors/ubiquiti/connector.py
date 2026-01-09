"""
Ubiquiti Direct Device Connector

Polls individual Ubiquiti UniFi access points and devices directly via their local API.
"""

import logging
import asyncio
import aiohttp
import ssl
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
    
    Polls individual Ubiquiti access points directly via their local HTTP API.
    Each device is polled independently with its own credentials.
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
        self._sessions: Dict[str, aiohttp.ClientSession] = {}
    
    @property
    def connector_type(self) -> str:
        return "ubiquiti"
    
    def _create_normalizer(self) -> BaseNormalizer:
        return UbiquitiNormalizer()
    
    async def start(self) -> None:
        if not self.targets:
            logger.warning("Ubiquiti connector: no targets configured")
        await super().start()
        logger.info(f"Ubiquiti connector started ({len(self.targets)} devices, poll interval: {self.poll_interval}s)")
    
    async def stop(self) -> None:
        for session in self._sessions.values():
            if session and not session.closed:
                await session.close()
        self._sessions.clear()
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
            try:
                result = await self._poll_device(target)
                if result:
                    success_count += 1
                else:
                    fail_count += 1
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
                # Device unreachable - create offline alert
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
        
        alerts = []
        
        # Create SSL context that doesn't verify (self-signed certs on devices)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=10)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Try UniFi device API endpoints
            device_info = await self._get_device_info(session, ip, username, password)
            
            if device_info:
                alerts.extend(self._check_device_status(ip, name, device_info))
            else:
                # Device didn't respond properly - might be offline
                alerts.append(self._create_offline_alert(target, "No response from device API"))
        
        return alerts
    
    async def _get_device_info(self, session: aiohttp.ClientSession, ip: str, username: str, password: str) -> Optional[Dict]:
        """Try to get device info from UniFi device local API."""
        
        # Try different API endpoints that UniFi devices expose
        endpoints = [
            f"https://{ip}/status.cgi",
            f"https://{ip}/api/s/default/stat/device",
            f"http://{ip}/status.cgi",
            f"https://{ip}:443/status.cgi",
        ]
        
        auth = aiohttp.BasicAuth(username, password)
        
        for url in endpoints:
            try:
                async with session.get(url, auth=auth) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            return data
                        except:
                            text = await response.text()
                            return {"raw": text, "reachable": True}
            except Exception:
                continue
        
        # Last resort: just try to ping/reach the device
        try:
            async with session.get(f"https://{ip}/", auth=auth) as response:
                if response.status in [200, 302, 401, 403]:
                    return {"reachable": True, "status_code": response.status}
        except Exception:
            pass
        
        return None
    
    def _check_device_status(self, ip: str, name: str, device_info: Dict) -> List[NormalizedAlert]:
        alerts = []
        
        # If we got a response, device is online
        if device_info.get("reachable"):
            # Device is reachable - no alert needed
            return alerts
        
        # Check CPU if available
        cpu = device_info.get("cpu") or device_info.get("system-stats", {}).get("cpu")
        if cpu is not None:
            try:
                cpu_val = float(cpu)
                if cpu_val > self.thresholds.get("cpu_warning", 80):
                    alerts.append(self._create_alert(ip, name, "high_cpu", {"cpu_percent": cpu_val}))
            except (ValueError, TypeError):
                pass
        
        # Check memory if available
        mem = device_info.get("mem") or device_info.get("system-stats", {}).get("mem")
        if mem is not None:
            try:
                mem_val = float(mem)
                if mem_val > self.thresholds.get("memory_warning", 80):
                    alerts.append(self._create_alert(ip, name, "high_memory", {"memory_percent": mem_val}))
            except (ValueError, TypeError):
                pass
        
        # Check wireless signal if available
        signal = device_info.get("signal") or device_info.get("wireless", {}).get("signal")
        if signal is not None:
            try:
                signal_val = int(signal)
                if signal_val < self.thresholds.get("signal_warning", -70):
                    alerts.append(self._create_alert(ip, name, "signal_degraded", {"signal": signal_val}))
            except (ValueError, TypeError):
                pass
        
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
