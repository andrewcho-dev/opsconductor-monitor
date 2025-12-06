#!/usr/bin/env python3
"""Comprehensive test script for all poller job types"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from poller_manager import get_poller_manager

def test_all_job_types():
    """Test all three job types comprehensively"""
    print("=== Comprehensive Poller Test ===")
    
    # Get manager and start scheduler
    manager = get_poller_manager()
    manager.start_scheduler()
    print(f"✅ Scheduler started: {manager.scheduler.running}")
    
    # Test configurations
    discovery_config = {
        'enabled': True,
        'interval': 30,  # 30 seconds for testing
        'network': '10.127.0.0/24',
        'retention': 30,
        'ping': True,
        'snmp': True,
        'ssh': True,
        'rdp': False
    }
    
    interface_config = {
        'enabled': True,
        'interval': 45,  # 45 seconds for testing
        'targets': 'all',
        'custom': '',
        'retention': 7
    }
    
    optical_config = {
        'enabled': True,
        'interval': 60,  # 60 seconds for testing
        'targets': 'all',
        'retention': 90,
        'temperature_threshold': 70
    }
    
    configs = {
        'discovery': discovery_config,
        'interface': interface_config,
        'optical': optical_config
    }
    
    # Test starting all jobs
    print("\n=== Starting All Jobs ===")
    for job_type, config in configs.items():
        print(f"\n--- Starting {job_type} job ---")
        try:
            result = manager.start_job(job_type, config)
            print(f"✅ {job_type} job started: {result}")
        except Exception as e:
            print(f"❌ {job_type} job failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Check status after starting all jobs
    print("\n=== Status After Starting All Jobs ===")
    status = manager.get_job_status()
    print(f"Discovery: running={status['discovery']['running']}, next_run={status['discovery']['next_run']}")
    print(f"Interface: running={status['interface']['running']}, next_run={status['interface']['next_run']}")
    print(f"Optical: running={status['optical']['running']}, next_run={status['optical']['next_run']}")
    print(f"Scheduler running: {status['scheduler_running']}")
    
    # List all jobs
    print("\n=== All Scheduled Jobs ===")
    jobs = manager.scheduler.get_jobs()
    for job in jobs:
        print(f"✅ Job: {job.id}, Name: {job.name}, Next run: {job.next_run_time}")
    
    # Wait for first job to execute
    print("\n=== Waiting for Discovery Job Execution (30 seconds) ===")
    time.sleep(35)  # Wait for discovery job to run
    
    # Check status after execution
    print("\n=== Status After First Execution ===")
    status = manager.get_job_status()
    print(f"Discovery: running={status['discovery']['running']}, next_run={status['discovery']['next_run']}")
    print(f"Total scans today: {status.get('total_scans_today', 0)}")
    print(f"Last scan: {status.get('last_scan', 'None')}")
    
    # Test stopping individual jobs
    print("\n=== Stopping Individual Jobs ===")
    for job_type in ['discovery', 'interface', 'optical']:
        print(f"\n--- Stopping {job_type} job ---")
        try:
            result = manager.stop_job(job_type)
            print(f"✅ {job_type} job stopped: {result}")
        except Exception as e:
            print(f"❌ {job_type} stop failed: {e}")
    
    # Final status check
    print("\n=== Final Status ===")
    status = manager.get_job_status()
    print(f"Discovery: running={status['discovery']['running']}")
    print(f"Interface: running={status['interface']['running']}")
    print(f"Optical: running={status['optical']['running']}")
    
    # Test immediate execution
    print("\n=== Testing Immediate Execution ===")
    for job_type in ['discovery', 'interface', 'optical']:
        print(f"\n--- Immediate execution of {job_type} ---")
        try:
            result = manager.run_job_now(job_type)
            print(f"✅ {job_type} immediate execution: {result}")
        except Exception as e:
            print(f"❌ {job_type} immediate execution failed: {e}")
    
    # Wait for immediate executions to complete
    print("\n=== Waiting for Immediate Executions to Complete ===")
    time.sleep(10)
    
    # Check final statistics
    print("\n=== Final Statistics ===")
    status = manager.get_job_status()
    print(f"Total scans today: {status.get('total_scans_today', 0)}")
    print(f"Last scan: {status.get('last_scan', 'None')}")
    
    # Stop scheduler
    print("\n=== Stopping Scheduler ===")
    stopped = manager.stop_scheduler()
    print(f"✅ Scheduler stopped: {stopped}")
    
    print("\n🎉 Comprehensive test completed!")

if __name__ == "__main__":
    test_all_job_types()
