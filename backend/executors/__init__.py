"""Backend executors package - Command execution engines."""

from .base import BaseExecutor
from .registry import ExecutorRegistry

__all__ = ['BaseExecutor', 'ExecutorRegistry']
