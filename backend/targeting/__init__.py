"""Backend targeting package - Target resolution strategies."""

from .base import BaseTargeting
from .registry import TargetingRegistry

__all__ = ['BaseTargeting', 'TargetingRegistry']
