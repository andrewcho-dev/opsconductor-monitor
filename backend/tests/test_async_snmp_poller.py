"""
Tests for the Async SNMP Poller

Run with: python -m pytest backend/tests/test_async_snmp_poller.py -v
Or directly: python backend/tests/test_async_snmp_poller.py
"""

import asyncio
import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.services.async_snmp_poller import (
    AsyncSNMPPoller, AsyncSNMPEngine, SNMPTarget, SNMPResult,
    CommonOIDs, PollerStats, poll_devices_simple
)


class TestSNMPTarget:
    """Tests for SNMPTarget dataclass."""
    
    def test_default_values(self):
        target = SNMPTarget(ip="192.168.1.1")
        assert target.ip == "192.168.1.1"
        assert target.community == "public"
        assert target.version == "2c"
        assert target.port == 161
        assert target.timeout == 2.0
        assert target.retries == 1
    
    def test_custom_values(self):
        target = SNMPTarget(
            ip="10.0.0.1",
            community="private",
            version="1",
            port=1161,
            timeout=5.0,
            retries=3,
        )
        assert target.ip == "10.0.0.1"
        assert target.community == "private"
        assert target.version == "1"
        assert target.port == 1161
        assert target.timeout == 5.0
        assert target.retries == 3
    
    def test_hashable(self):
        target1 = SNMPTarget(ip="192.168.1.1")
        target2 = SNMPTarget(ip="192.168.1.1")
        target3 = SNMPTarget(ip="192.168.1.2")
        
        # Same IP should have same hash
        assert hash(target1) == hash(target2)
        # Different IP should have different hash
        assert hash(target1) != hash(target3)


class TestPollerStats:
    """Tests for PollerStats."""
    
    def test_initial_values(self):
        stats = PollerStats()
        assert stats.total_queries == 0
        assert stats.successful_queries == 0
        assert stats.failed_queries == 0
        assert stats.success_rate == 0.0
    
    def test_record_success(self):
        stats = PollerStats()
        result = SNMPResult(
            target=SNMPTarget(ip="192.168.1.1"),
            success=True,
            duration=0.1,
        )
        stats.record(result)
        
        assert stats.total_queries == 1
        assert stats.successful_queries == 1
        assert stats.failed_queries == 0
        assert stats.success_rate == 100.0
    
    def test_record_failure(self):
        stats = PollerStats()
        result = SNMPResult(
            target=SNMPTarget(ip="192.168.1.1"),
            success=False,
            error="Timeout",
            duration=2.0,
        )
        stats.record(result)
        
        assert stats.total_queries == 1
        assert stats.successful_queries == 0
        assert stats.failed_queries == 1
        assert stats.success_rate == 0.0
        assert "Timeout" in stats.errors_by_type
    
    def test_avg_duration(self):
        stats = PollerStats()
        for duration in [0.1, 0.2, 0.3]:
            result = SNMPResult(
                target=SNMPTarget(ip="192.168.1.1"),
                success=True,
                duration=duration,
            )
            stats.record(result)
        
        assert abs(stats.avg_duration - 0.2) < 0.001


class TestAsyncSNMPEngine:
    """Tests for AsyncSNMPEngine."""
    
    def test_initialization(self):
        engine = AsyncSNMPEngine(
            max_concurrent=50,
            default_timeout=3.0,
            default_retries=2,
        )
        assert engine.max_concurrent == 50
        assert engine.default_timeout == 3.0
        assert engine.default_retries == 2
    
    def test_stats_reset(self):
        engine = AsyncSNMPEngine()
        # Record some stats
        engine._stats.total_queries = 100
        engine._stats.successful_queries = 90
        
        # Reset
        engine.reset_stats()
        
        assert engine.stats.total_queries == 0
        assert engine.stats.successful_queries == 0


class TestAsyncSNMPPoller:
    """Tests for AsyncSNMPPoller."""
    
    def test_initialization(self):
        poller = AsyncSNMPPoller(
            max_concurrent=100,
            batch_size=50,
            stagger_delay=0.01,
        )
        assert poller.batch_size == 50
        assert poller.stagger_delay == 0.01
    
    def test_progress_callback(self):
        progress_calls = []
        
        def callback(completed, total):
            progress_calls.append((completed, total))
        
        poller = AsyncSNMPPoller(
            max_concurrent=10,
            batch_size=5,
            progress_callback=callback,
        )
        
        # Progress callback is set
        assert poller.progress_callback is not None


async def test_poll_unreachable_device():
    """Test polling an unreachable device (should fail gracefully)."""
    poller = AsyncSNMPPoller(
        max_concurrent=10,
        batch_size=5,
        stagger_delay=0,
    )
    
    # Use a non-routable IP that will timeout quickly
    targets = [SNMPTarget(ip="192.0.2.1", timeout=0.5, retries=0)]
    oids = [CommonOIDs.SYS_DESCR]
    
    results = await poller.poll_devices(targets, oids)
    
    assert len(results) == 1
    assert results[0].success == False
    assert results[0].error is not None


async def test_poll_multiple_targets_performance():
    """Test polling multiple targets for performance metrics."""
    # Create many targets (they won't respond, but we test the framework)
    num_targets = 100
    targets = [
        SNMPTarget(ip=f"192.0.2.{i}", timeout=0.1, retries=0)
        for i in range(1, num_targets + 1)
    ]
    
    poller = AsyncSNMPPoller(
        max_concurrent=50,
        batch_size=25,
        stagger_delay=0.001,
    )
    
    start = time.time()
    results = await poller.poll_devices(targets, [CommonOIDs.SYS_DESCR])
    elapsed = time.time() - start
    
    assert len(results) == num_targets
    
    # With 0.1s timeout and 50 concurrent, 100 devices should complete
    # in roughly 0.2-0.5 seconds (2 batches * timeout + overhead)
    print(f"\nPolled {num_targets} devices in {elapsed:.2f}s")
    print(f"Rate: {num_targets/elapsed:.1f} devices/sec")
    
    # Should be much faster than sequential (which would be 10+ seconds)
    assert elapsed < 5.0, f"Polling took too long: {elapsed}s"


async def run_live_test(test_ips: list):
    """
    Run a live test against real devices.
    
    Args:
        test_ips: List of IP addresses to test
    """
    print(f"\n{'='*60}")
    print(f"LIVE SNMP POLLING TEST")
    print(f"{'='*60}")
    print(f"Testing {len(test_ips)} devices...")
    
    targets = [
        SNMPTarget(ip=ip, community="public", timeout=2.0, retries=1)
        for ip in test_ips
    ]
    
    oids = [
        CommonOIDs.SYS_DESCR,
        CommonOIDs.SYS_UPTIME,
        CommonOIDs.SYS_NAME,
    ]
    
    progress_count = [0]
    def progress(completed, total):
        progress_count[0] = completed
        pct = completed / total * 100
        print(f"\rProgress: {completed}/{total} ({pct:.0f}%)", end="", flush=True)
    
    poller = AsyncSNMPPoller(
        max_concurrent=50,
        batch_size=25,
        stagger_delay=0.005,
        progress_callback=progress,
    )
    
    start = time.time()
    results = await poller.poll_devices(targets, oids)
    elapsed = time.time() - start
    
    print(f"\n\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    print(f"Total devices:    {len(results)}")
    print(f"Successful:       {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
    print(f"Failed:           {len(failed)} ({len(failed)/len(results)*100:.1f}%)")
    print(f"Duration:         {elapsed:.2f} seconds")
    print(f"Rate:             {len(results)/elapsed:.1f} devices/sec")
    print(f"Avg latency:      {poller.stats.avg_duration*1000:.1f} ms")
    print(f"P95 latency:      {poller.stats.p95_duration*1000:.1f} ms")
    print(f"Queries/sec:      {poller.stats.queries_per_second:.1f}")
    
    if failed:
        print(f"\nFailed devices:")
        for r in failed[:10]:
            print(f"  {r.target.ip}: {r.error}")
        if len(failed) > 10:
            print(f"  ... and {len(failed)-10} more")
    
    if successful:
        print(f"\nSample successful results:")
        for r in successful[:3]:
            print(f"  {r.target.ip}:")
            for oid, value in list(r.values.items())[:2]:
                val_str = str(value)[:60] + "..." if len(str(value)) > 60 else value
                print(f"    {oid}: {val_str}")
    
    return results


def run_unit_tests():
    """Run unit tests."""
    print("Running unit tests...")
    
    # Test SNMPTarget
    test_target = TestSNMPTarget()
    test_target.test_default_values()
    test_target.test_custom_values()
    test_target.test_hashable()
    print("  SNMPTarget tests passed")
    
    # Test PollerStats
    test_stats = TestPollerStats()
    test_stats.test_initial_values()
    test_stats.test_record_success()
    test_stats.test_record_failure()
    test_stats.test_avg_duration()
    print("  PollerStats tests passed")
    
    # Test AsyncSNMPEngine
    test_engine = TestAsyncSNMPEngine()
    test_engine.test_initialization()
    test_engine.test_stats_reset()
    print("  AsyncSNMPEngine tests passed")
    
    # Test AsyncSNMPPoller
    test_poller = TestAsyncSNMPPoller()
    test_poller.test_initialization()
    test_poller.test_progress_callback()
    print("  AsyncSNMPPoller tests passed")
    
    print("\nAll unit tests passed!")


async def run_async_tests():
    """Run async tests."""
    print("\nRunning async tests...")
    
    await test_poll_unreachable_device()
    print("  Unreachable device test passed")
    
    await test_poll_multiple_targets_performance()
    print("  Performance test passed")
    
    print("\nAll async tests passed!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test async SNMP poller")
    parser.add_argument(
        "--live",
        nargs="+",
        metavar="IP",
        help="Run live test against specified IPs",
    )
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run unit tests only",
    )
    
    args = parser.parse_args()
    
    if args.unit:
        run_unit_tests()
    elif args.live:
        asyncio.run(run_live_test(args.live))
    else:
        # Run all tests
        run_unit_tests()
        asyncio.run(run_async_tests())
        print("\n" + "="*60)
        print("ALL TESTS PASSED")
        print("="*60)
        print("\nTo run a live test against real devices:")
        print("  python backend/tests/test_async_snmp_poller.py --live 192.168.10.1 192.168.10.2")
