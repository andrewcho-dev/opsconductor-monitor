"""
Generic Job Scheduler - Compatibility wrapper.

This module provides backward compatibility with code that imports from generic_job_scheduler.py.
It delegates to the new backend.services.job_executor module.
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.services.job_executor import JobExecutor


class GenericJobScheduler:
    """
    Generic job scheduler - compatibility wrapper.
    
    Delegates to the new JobExecutor service.
    """
    
    def __init__(self):
        from database import DatabaseManager
        self.db = DatabaseManager()
        self.executor = JobExecutor(self.db)
    
    def execute_job(self, job_definition):
        """Execute a job definition."""
        return self.executor.execute_job(job_definition)


__all__ = ['GenericJobScheduler', 'JobExecutor']
