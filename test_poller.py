#!/usr/bin/env python3
"""Test script to debug poller manager directly"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from poller_manager import get_poller_manager

def test_poller_manager():
    """Test the poller manager directly"""
    print("=== Testing Poller Manager ===")
    
    # Get manager
    manager = get_poller_manager()
    print(f"Manager created: {manager}")
    print(f"Scheduler running: {manager.scheduler.running}")
    
    # Start scheduler
    print("\n=== Starting Scheduler ===")
    try:
        started = manager.start_scheduler()
        print(f"Scheduler started: {started}")
        print(f"Scheduler running: {manager.scheduler.running}")
    except Exception as e:
        print(f"Start scheduler exception: {e}")
        import traceback
        traceback.print_exc()
    
    # Test configuration
    config = {
        'enabled': True,
        'interval': 60,
        'network': '10.127.0.0/24',
        'retention': 30,
        'ping': True,
        'snmp': True,
        'ssh': True,
        'rdp': False
    }
    
    print(f"Test config: {config}")
    print(f"Config enabled: {config.get('enabled', False)}")
    
    # Try to start job
    print("\n=== Starting Discovery Job ===")
    try:
        result = manager.start_job('discovery', config)
        print(f"Start job result: {result}")
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()
    
    # Check status
    print("\n=== Checking Status ===")
    try:
        status = manager.get_job_status()
        print(f"Status: {status}")
    except Exception as e:
        print(f"Status exception: {e}")
        import traceback
        traceback.print_exc()
    
    # List jobs
    print("\n=== Listing Jobs ===")
    try:
        jobs = manager.scheduler.get_jobs()
        print(f"Jobs: {jobs}")
        for job in jobs:
            print(f"  Job: {job.id}, Next run: {job.next_run_time}")
    except Exception as e:
        print(f"Jobs exception: {e}")
        import traceback
        traceback.print_exc()
    
    # Wait a moment and check again
    import time
    print("\n=== Waiting 5 seconds and checking again ===")
    time.sleep(5)
    
    try:
        jobs = manager.scheduler.get_jobs()
        print(f"Jobs after wait: {jobs}")
        for job in jobs:
            print(f"  Job: {job.id}, Next run: {job.next_run_time}")
    except Exception as e:
        print(f"Jobs after wait exception: {e}")
        import traceback
        traceback.print_exc()
    
    # Test immediate execution
    print("\n=== Testing Immediate Execution ===")
    try:
        result = manager.run_job_now('discovery')
        print(f"Immediate execution result: {result}")
    except Exception as e:
        print(f"Immediate execution exception: {e}")
        import traceback
        traceback.print_exc()
    
    # Stop scheduler
    print("\n=== Stopping Scheduler ===")
    try:
        stopped = manager.stop_scheduler()
        print(f"Scheduler stopped: {stopped}")
    except Exception as e:
        print(f"Stop scheduler exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_poller_manager()
