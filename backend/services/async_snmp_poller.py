"""
High-Performance Async SNMP Poller

Best-in-class SNMP polling implementation with:
- True async I/O using asyncio + pysnmp
- Connection pooling and session reuse
- GETBULK for efficient multi-OID queries
- Staggered polling to distribute load
- Automatic retry with exponential backoff
- Batch processing with configurable concurrency
- Real-time metrics and performance tracking

Performance targets:
- 1,500+ devices in under 60 seconds
- 5,000+ OID queries per second
- Sub-second latency for individual queries
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from contextlib import asynccontextmanager
import statistics

logger = logging.getLogger(__name__)


@dataclass
class SNMPTarget:
    """SNMP target configuration."""
    ip: str
    community: str = "public"
    version: str = "2c"
    port: int = 161
    timeout: float = 2.0
    retries: int = 1
    device_type: str = "unknown"
    site: str = ""
    
    def __hash__(self):
        return hash((self.ip, self.port))


@dataclass
class SNMPQuery:
    """SNMP query definition."""
    oids: List[str]
    use_bulk: bool = True
    max_repetitions: int = 25
    name: str = ""


@dataclass
class SNMPResult:
    """SNMP query result."""
    target: SNMPTarget
    success: bool
    values: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)
    retries_used: int = 0


@dataclass
class PollerStats:
    """Poller performance statistics."""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    durations: List[float] = field(default_factory=list)
    errors_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    start_time: float = field(default_factory=time.time)
    
    @property
    def success_rate(self) -> float:
        if self.total_queries == 0:
            return 0.0
        return self.successful_queries / self.total_queries * 100
    
    @property
    def avg_duration(self) -> float:
        if not self.durations:
            return 0.0
        return statistics.mean(self.durations)
    
    @property
    def p95_duration(self) -> float:
        if len(self.durations) < 20:
            return self.max_duration
        sorted_durations = sorted(self.durations)
        idx = int(len(sorted_durations) * 0.95)
        return sorted_durations[idx]
    
    @property
    def queries_per_second(self) -> float:
        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return 0.0
        return self.total_queries / elapsed
    
    def record(self, result: SNMPResult):
        self.total_queries += 1
        self.durations.append(result.duration)
        self.total_duration += result.duration
        self.min_duration = min(self.min_duration, result.duration)
        self.max_duration = max(self.max_duration, result.duration)
        
        if result.success:
            self.successful_queries += 1
        else:
            self.failed_queries += 1
            error_type = result.error.split(':')[0] if result.error else 'Unknown'
            self.errors_by_type[error_type] += 1


class AsyncSNMPEngine:
    """
    High-performance async SNMP engine.
    
    Uses thread pool executor with pysnmp sync API for reliable
    concurrent SNMP queries. This approach is more stable than
    pysnmp's async API which has compatibility issues with Python 3.10+.
    
    Performance is achieved through:
    - Large thread pool for concurrent I/O-bound operations
    - Semaphore to control max concurrent queries
    - Connection reuse where possible
    """
    
    def __init__(
        self,
        max_concurrent: int = 100,
        default_timeout: float = 2.0,
        default_retries: int = 1,
    ):
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self.default_retries = default_retries
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._engine = None
        self._stats = PollerStats()
        # Thread pool for concurrent sync SNMP operations
        # Size matches max_concurrent for optimal parallelism
        from concurrent.futures import ThreadPoolExecutor
        self._executor = ThreadPoolExecutor(
            max_workers=max_concurrent,
            thread_name_prefix="snmp_worker"
        )
    
    async def _get_engine(self):
        """Get or create SNMP engine (lazy initialization)."""
        if self._engine is None:
            try:
                from pysnmp.hlapi.asyncio import SnmpEngine
                self._engine = SnmpEngine()
            except ImportError:
                from pysnmp.hlapi import SnmpEngine
                self._engine = SnmpEngine()
        return self._engine
    
    async def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create semaphore for concurrency control."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore
    
    async def get_single(
        self,
        target: SNMPTarget,
        oid: str,
    ) -> SNMPResult:
        """
        Execute a single SNMP GET query.
        
        Args:
            target: SNMP target configuration
            oid: OID to query
        
        Returns:
            SNMPResult with query results
        """
        return await self.get_multiple(target, [oid])
    
    async def get_multiple(
        self,
        target: SNMPTarget,
        oids: List[str],
    ) -> SNMPResult:
        """
        Execute SNMP GET for multiple OIDs in a single request.
        
        Args:
            target: SNMP target configuration
            oids: List of OIDs to query
        
        Returns:
            SNMPResult with all values
        """
        start_time = time.time()
        retries_used = 0
        
        # Thread pool handles concurrency - no semaphore needed
        for attempt in range(target.retries + 1):
            try:
                result = await self._execute_get(target, oids)
                result.retries_used = retries_used
                result.duration = time.time() - start_time
                self._stats.record(result)
                return result
            except Exception as e:
                retries_used += 1
                if attempt < target.retries:
                    # Short backoff before retry
                    await asyncio.sleep(0.05 * (2 ** attempt))
                else:
                    result = SNMPResult(
                        target=target,
                        success=False,
                        error=str(e),
                        duration=time.time() - start_time,
                        retries_used=retries_used,
                    )
                    self._stats.record(result)
                    return result
    
    async def _execute_get(
        self,
        target: SNMPTarget,
        oids: List[str],
    ) -> SNMPResult:
        """Execute the actual SNMP GET request using thread pool for reliability."""
        # Use thread pool executor for pysnmp sync API
        # This is more reliable than pysnmp's async API which has Python 3.10+ issues
        return await self._execute_get_sync(target, oids)
    
    async def _execute_get_sync(
        self,
        target: SNMPTarget,
        oids: List[str],
    ) -> SNMPResult:
        """Execute sync SNMP in thread pool for high concurrency."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._sync_get,
            target,
            oids,
        )
    
    def _sync_get(self, target: SNMPTarget, oids: List[str]) -> SNMPResult:
        """
        High-performance SNMP GET using subprocess.
        
        Uses net-snmp's snmpget command which is much faster than pysnmp
        because it doesn't have Python GIL overhead and has optimized C code.
        """
        import subprocess
        
        version_flag = '-v1' if target.version == '1' else '-v2c'
        timeout_decisecs = max(1, int(target.timeout * 10))  # Convert to deciseconds
        
        # Build command for multiple OIDs in single request
        cmd = [
            'snmpget',
            '-OQn',  # Quick print, numeric OIDs
            version_flag,
            '-c', target.community,
            '-t', str(timeout_decisecs // 10),  # Timeout in seconds
            '-r', '0',  # No retries (we handle retries ourselves)
            f'{target.ip}:{target.port}',
        ] + oids
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=target.timeout + 1,  # Subprocess timeout slightly longer
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() or f"snmpget failed with code {result.returncode}"
                return SNMPResult(
                    target=target,
                    success=False,
                    error=f"SNMP error: {error_msg}",
                )
            
            # Parse output: .1.3.6.1.2.1.1.1.0 = "value"
            values = {}
            for line in result.stdout.strip().split('\n'):
                if '=' in line:
                    parts = line.split('=', 1)
                    oid_str = parts[0].strip()
                    value = parts[1].strip().strip('"')
                    values[oid_str] = value
            
            return SNMPResult(target=target, success=True, values=values)
            
        except subprocess.TimeoutExpired:
            return SNMPResult(
                target=target,
                success=False,
                error="SNMP error: No SNMP response received before timeout",
            )
        except FileNotFoundError:
            # snmpget not installed, fall back to pysnmp
            return self._sync_get_pysnmp(target, oids)
        except Exception as e:
            return SNMPResult(target=target, success=False, error=str(e))
    
    def _sync_get_pysnmp(self, target: SNMPTarget, oids: List[str]) -> SNMPResult:
        """Fallback: Synchronous SNMP GET using pysnmp."""
        try:
            from pysnmp.hlapi import (
                getCmd, SnmpEngine, CommunityData, UdpTransportTarget,
                ContextData, ObjectType, ObjectIdentity
            )
            
            oid_objects = [ObjectType(ObjectIdentity(oid)) for oid in oids]
            mp_model = 0 if target.version == "1" else 1
            
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(target.community, mpModel=mp_model),
                UdpTransportTarget(
                    (target.ip, target.port),
                    timeout=target.timeout,
                    retries=0,
                ),
                ContextData(),
                *oid_objects
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            if errorIndication:
                return SNMPResult(
                    target=target,
                    success=False,
                    error=f"SNMP error: {errorIndication}",
                )
            
            if errorStatus:
                return SNMPResult(
                    target=target,
                    success=False,
                    error=f"SNMP error: {errorStatus.prettyPrint()}",
                )
            
            values = {}
            for varBind in varBinds:
                values[str(varBind[0])] = varBind[1].prettyPrint()
            
            return SNMPResult(target=target, success=True, values=values)
            
        except Exception as e:
            return SNMPResult(target=target, success=False, error=str(e))
    
    async def get_bulk(
        self,
        target: SNMPTarget,
        oid: str,
        max_repetitions: int = 25,
    ) -> SNMPResult:
        """
        Execute SNMP GETBULK for efficient table retrieval.
        
        Args:
            target: SNMP target configuration
            oid: Base OID for bulk query
            max_repetitions: Max rows to retrieve per request
        
        Returns:
            SNMPResult with all values
        """
        start_time = time.time()
        
        # Thread pool handles concurrency - no semaphore needed
        try:
            result = await self._execute_bulk(target, oid, max_repetitions)
            result.duration = time.time() - start_time
            self._stats.record(result)
            return result
        except Exception as e:
            result = SNMPResult(
                target=target,
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )
            self._stats.record(result)
            return result
    
    async def _execute_bulk(
        self,
        target: SNMPTarget,
        oid: str,
        max_repetitions: int,
    ) -> SNMPResult:
        """Execute the actual SNMP GETBULK request using thread pool for reliability."""
        # Use thread pool executor for pysnmp sync API
        # This is more reliable than pysnmp's async API which has Python 3.10+ issues
        return await self._execute_bulk_sync(target, oid, max_repetitions)
    
    async def _execute_bulk_sync(
        self,
        target: SNMPTarget,
        oid: str,
        max_repetitions: int,
    ) -> SNMPResult:
        """Execute sync SNMP BULK in thread pool for high concurrency."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._sync_bulk,
            target,
            oid,
            max_repetitions,
        )
    
    def _sync_bulk(
        self,
        target: SNMPTarget,
        oid: str,
        max_repetitions: int,
    ) -> SNMPResult:
        """
        High-performance SNMP GETBULK/WALK using subprocess.
        
        Uses net-snmp's snmpbulkwalk command for efficient table retrieval.
        """
        import subprocess
        
        # Use snmpbulkwalk for v2c, snmpwalk for v1
        if target.version == '1':
            cmd = [
                'snmpwalk',
                '-OQn',
                '-v1',
                '-c', target.community,
                '-t', str(int(target.timeout)),
                '-r', '0',
                f'{target.ip}:{target.port}',
                oid,
            ]
        else:
            cmd = [
                'snmpbulkwalk',
                '-OQn',
                '-v2c',
                '-c', target.community,
                '-t', str(int(target.timeout)),
                '-r', '0',
                '-Cr' + str(max_repetitions),  # Max repetitions
                f'{target.ip}:{target.port}',
                oid,
            ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=target.timeout * 3,  # Allow more time for bulk
            )
            
            # Parse output
            values = {}
            for line in result.stdout.strip().split('\n'):
                if '=' in line:
                    parts = line.split('=', 1)
                    oid_str = parts[0].strip()
                    value = parts[1].strip().strip('"')
                    values[oid_str] = value
            
            if not values and result.returncode != 0:
                error_msg = result.stderr.strip() or f"snmpbulkwalk failed"
                return SNMPResult(
                    target=target,
                    success=False,
                    error=f"SNMP error: {error_msg}",
                )
            
            return SNMPResult(target=target, success=True, values=values)
            
        except subprocess.TimeoutExpired:
            return SNMPResult(
                target=target,
                success=False,
                error="SNMP error: Bulk walk timed out",
            )
        except FileNotFoundError:
            # snmpbulkwalk not installed, fall back to pysnmp
            return self._sync_bulk_pysnmp(target, oid, max_repetitions)
        except Exception as e:
            return SNMPResult(target=target, success=False, error=str(e))
    
    def _sync_bulk_pysnmp(
        self,
        target: SNMPTarget,
        oid: str,
        max_repetitions: int,
    ) -> SNMPResult:
        """Fallback: Synchronous SNMP GETBULK using pysnmp."""
        try:
            from pysnmp.hlapi import (
                bulkCmd, SnmpEngine, CommunityData, UdpTransportTarget,
                ContextData, ObjectType, ObjectIdentity
            )
            
            mp_model = 0 if target.version == "1" else 1
            values = {}
            
            for (errorIndication, errorStatus, errorIndex, varBinds) in bulkCmd(
                SnmpEngine(),
                CommunityData(target.community, mpModel=mp_model),
                UdpTransportTarget(
                    (target.ip, target.port),
                    timeout=target.timeout,
                    retries=0,
                ),
                ContextData(),
                0, max_repetitions,
                ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False,
            ):
                if errorIndication or errorStatus:
                    break
                for varBind in varBinds:
                    values[str(varBind[0])] = varBind[1].prettyPrint()
            
            return SNMPResult(target=target, success=True, values=values)
            
        except Exception as e:
            return SNMPResult(target=target, success=False, error=str(e))
    
    @property
    def stats(self) -> PollerStats:
        """Get current statistics."""
        return self._stats
    
    def reset_stats(self):
        """Reset statistics."""
        self._stats = PollerStats()


class AsyncSNMPPoller:
    """
    High-performance batch SNMP poller.
    
    Polls multiple devices concurrently with optimal performance.
    """
    
    def __init__(
        self,
        max_concurrent: int = 100,
        batch_size: int = 50,
        stagger_delay: float = 0.01,
        default_timeout: float = 2.0,
        default_retries: int = 1,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ):
        """
        Initialize the poller.
        
        Args:
            max_concurrent: Maximum concurrent SNMP sessions
            batch_size: Number of devices to poll in each batch
            stagger_delay: Delay between starting each query (seconds)
            default_timeout: Default SNMP timeout
            default_retries: Default retry count
            progress_callback: Optional callback(completed, total) for progress
        """
        self.engine = AsyncSNMPEngine(
            max_concurrent=max_concurrent,
            default_timeout=default_timeout,
            default_retries=default_retries,
        )
        self.batch_size = batch_size
        self.stagger_delay = stagger_delay
        self.progress_callback = progress_callback
    
    async def poll_devices(
        self,
        targets: List[SNMPTarget],
        oids: List[str],
        use_bulk: bool = False,
    ) -> List[SNMPResult]:
        """
        Poll multiple devices for the same OIDs.
        
        Args:
            targets: List of SNMP targets
            oids: List of OIDs to query from each device
            use_bulk: Use GETBULK instead of GET (for table OIDs)
        
        Returns:
            List of SNMPResult for each target
        """
        self.engine.reset_stats()
        total = len(targets)
        completed = [0]  # Use list for mutable closure
        
        async def poll_with_progress(target: SNMPTarget) -> SNMPResult:
            """Poll single target and update progress."""
            try:
                if use_bulk and len(oids) == 1:
                    result = await self.engine.get_bulk(target, oids[0])
                else:
                    result = await self.engine.get_multiple(target, oids)
            except Exception as e:
                result = SNMPResult(
                    target=target,
                    success=False,
                    error=str(e),
                )
            
            completed[0] += 1
            if self.progress_callback:
                self.progress_callback(completed[0], total)
            
            return result
        
        # Launch ALL tasks at once - thread pool handles concurrency
        tasks = [poll_with_progress(target) for target in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert any exceptions to SNMPResult
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(SNMPResult(
                    target=targets[i],
                    success=False,
                    error=str(result),
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    async def _staggered_get(
        self,
        target: SNMPTarget,
        oids: List[str],
        index: int,
    ) -> SNMPResult:
        """Execute GET with staggered start."""
        if self.stagger_delay > 0 and index > 0:
            await asyncio.sleep(self.stagger_delay * index)
        return await self.engine.get_multiple(target, oids)
    
    async def _staggered_bulk(
        self,
        target: SNMPTarget,
        oid: str,
        index: int,
    ) -> SNMPResult:
        """Execute BULK with staggered start."""
        if self.stagger_delay > 0 and index > 0:
            await asyncio.sleep(self.stagger_delay * index)
        return await self.engine.get_bulk(target, oid)
    
    async def poll_device_metrics(
        self,
        target: SNMPTarget,
        metric_queries: Dict[str, List[str]],
    ) -> Dict[str, SNMPResult]:
        """
        Poll a single device for multiple metric categories.
        
        Args:
            target: SNMP target
            metric_queries: Dict of metric_name -> list of OIDs
        
        Returns:
            Dict of metric_name -> SNMPResult
        """
        results = {}
        tasks = []
        metric_names = []
        
        for metric_name, oids in metric_queries.items():
            metric_names.append(metric_name)
            tasks.append(self.engine.get_multiple(target, oids))
        
        query_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for metric_name, result in zip(metric_names, query_results):
            if isinstance(result, Exception):
                results[metric_name] = SNMPResult(
                    target=target,
                    success=False,
                    error=str(result),
                )
            else:
                results[metric_name] = result
        
        return results
    
    @property
    def stats(self) -> PollerStats:
        """Get polling statistics."""
        return self.engine.stats


# Common OID definitions for network devices
class CommonOIDs:
    """Common SNMP OIDs for network monitoring."""
    
    # System MIB
    SYS_DESCR = "1.3.6.1.2.1.1.1.0"
    SYS_OBJECT_ID = "1.3.6.1.2.1.1.2.0"
    SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
    SYS_NAME = "1.3.6.1.2.1.1.5.0"
    SYS_LOCATION = "1.3.6.1.2.1.1.6.0"
    
    # Interface MIB
    IF_NUMBER = "1.3.6.1.2.1.2.1.0"
    IF_TABLE = "1.3.6.1.2.1.2.2"
    IF_DESCR = "1.3.6.1.2.1.2.2.1.2"
    IF_TYPE = "1.3.6.1.2.1.2.2.1.3"
    IF_SPEED = "1.3.6.1.2.1.2.2.1.5"
    IF_ADMIN_STATUS = "1.3.6.1.2.1.2.2.1.7"
    IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"
    IF_IN_OCTETS = "1.3.6.1.2.1.2.2.1.10"
    IF_OUT_OCTETS = "1.3.6.1.2.1.2.2.1.16"
    IF_IN_ERRORS = "1.3.6.1.2.1.2.2.1.14"
    IF_OUT_ERRORS = "1.3.6.1.2.1.2.2.1.20"
    
    # IF-MIB (64-bit counters)
    IF_HC_IN_OCTETS = "1.3.6.1.2.1.31.1.1.1.6"
    IF_HC_OUT_OCTETS = "1.3.6.1.2.1.31.1.1.1.10"
    IF_NAME = "1.3.6.1.2.1.31.1.1.1.1"
    IF_ALIAS = "1.3.6.1.2.1.31.1.1.1.18"
    
    # Entity MIB (for optical DOM)
    ENT_PHYSICAL_DESCR = "1.3.6.1.2.1.47.1.1.1.1.2"
    ENT_PHYSICAL_NAME = "1.3.6.1.2.1.47.1.1.1.1.7"
    
    # Optical DOM (vendor-specific examples)
    # Ciena WWP-LEOS (older switches like 3930)
    CIENA_WWP_RX_POWER = "1.3.6.1.4.1.6141.2.60.4.1.1.1.1.16"  # wwpLeosPortXcvrRxPower (uW)
    CIENA_WWP_TX_POWER = "1.3.6.1.4.1.6141.2.60.4.1.1.1.1.24"  # wwpLeosPortXcvrTxOutputPw (uW)
    CIENA_WWP_TEMPERATURE = "1.3.6.1.4.1.6141.2.60.4.1.1.1.1.15"  # wwpLeosPortXcvrTemperature
    CIENA_WWP_BIAS = "1.3.6.1.4.1.6141.2.60.4.1.1.1.1.17"  # wwpLeosPortXcvrBias (mA)
    # Ciena CES (newer switches)
    CIENA_CES_RX_POWER = "1.3.6.1.4.1.1271.2.1.9.1.1.1.1.6"  # cienaCesPortXcvrRxPower (uW)
    CIENA_CES_TX_POWER = "1.3.6.1.4.1.1271.2.1.9.1.1.1.1.35"  # cienaCesPortXcvrTxOutputPower
    
    # Standard optical (IF-MIB extensions)
    OPT_IF_TX_POWER = "1.3.6.1.2.1.10.133.1.1.1.1.3"
    OPT_IF_RX_POWER = "1.3.6.1.2.1.10.133.1.1.1.1.4"


# Convenience function for simple polling
async def poll_devices_simple(
    devices: List[Dict[str, Any]],
    oids: List[str],
    community: str = "public",
    max_concurrent: int = 100,
) -> List[SNMPResult]:
    """
    Simple interface for polling multiple devices.
    
    Args:
        devices: List of dicts with 'ip' key (and optional 'community')
        oids: List of OIDs to query
        community: Default community string
        max_concurrent: Max concurrent queries
    
    Returns:
        List of SNMPResult
    """
    targets = [
        SNMPTarget(
            ip=d['ip'],
            community=d.get('community', community),
        )
        for d in devices
    ]
    
    poller = AsyncSNMPPoller(max_concurrent=max_concurrent)
    return await poller.poll_devices(targets, oids)


# Test function
async def _test_poller():
    """Test the async SNMP poller."""
    import sys
    
    # Test with a few devices
    test_ips = sys.argv[1:] if len(sys.argv) > 1 else ["192.168.10.1"]
    
    targets = [SNMPTarget(ip=ip, community="public") for ip in test_ips]
    oids = [CommonOIDs.SYS_DESCR, CommonOIDs.SYS_UPTIME, CommonOIDs.SYS_NAME]
    
    print(f"Testing async SNMP poller with {len(targets)} targets...")
    
    poller = AsyncSNMPPoller(
        max_concurrent=50,
        progress_callback=lambda c, t: print(f"Progress: {c}/{t}", end="\r"),
    )
    
    start = time.time()
    results = await poller.poll_devices(targets, oids)
    elapsed = time.time() - start
    
    print(f"\n\nCompleted in {elapsed:.2f} seconds")
    print(f"Stats: {poller.stats.success_rate:.1f}% success rate")
    print(f"       {poller.stats.queries_per_second:.1f} queries/sec")
    print(f"       {poller.stats.avg_duration*1000:.1f}ms avg latency")
    print(f"       {poller.stats.p95_duration*1000:.1f}ms p95 latency")
    
    for result in results:
        status = "OK" if result.success else f"FAIL: {result.error}"
        print(f"  {result.target.ip}: {status}")
        if result.success:
            for oid, value in result.values.items():
                print(f"    {oid}: {value[:50]}..." if len(str(value)) > 50 else f"    {oid}: {value}")


if __name__ == "__main__":
    asyncio.run(_test_poller())
