"""
Parallelism Utilities

Centralized configuration for optimal parallelism based on system resources.
All executors should use these functions to ensure consistent, optimal performance.
"""

import os
from typing import Optional


def get_cpu_count() -> int:
    """Get the number of CPU cores available."""
    return os.cpu_count() or 4


def get_optimal_thread_count(target_count: int, max_threads: int = 200) -> int:
    """
    Calculate optimal thread count for network I/O operations.
    
    Formula: min(CPU_cores × 10, target_count, max_threads)
    
    Args:
        target_count: Number of targets to process
        max_threads: Maximum threads to use (default 200)
    
    Returns:
        Optimal number of threads
    """
    cpu_count = get_cpu_count()
    return min(cpu_count * 10, target_count, max_threads)


def get_optimal_worker_count(max_workers: int = 32) -> int:
    """
    Calculate optimal Celery worker count for CPU-bound tasks.
    
    Formula: min(CPU_cores × 2, max_workers)
    
    Args:
        max_workers: Maximum workers (default 32)
    
    Returns:
        Optimal number of workers
    """
    cpu_count = get_cpu_count()
    return min(cpu_count * 2, max_workers)


# Pre-calculated values for quick access
CPU_COUNT = get_cpu_count()
MAX_NETWORK_THREADS = min(CPU_COUNT * 10, 200)
MAX_CELERY_WORKERS = min(CPU_COUNT * 2, 32)


def log_parallelism_config():
    """Log the current parallelism configuration."""
    return {
        'cpu_count': CPU_COUNT,
        'max_network_threads': MAX_NETWORK_THREADS,
        'max_celery_workers': MAX_CELERY_WORKERS,
        'formula': '10x CPU cores for network I/O, 2x CPU cores for Celery workers',
    }
