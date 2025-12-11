"""Backend targeting package - Target resolution strategies."""

from .base import BaseTargeting
from .registry import TargetingRegistry
from .strategies import (
    StaticTargeting,
    DatabaseQueryTargeting,
    GroupTargeting,
    NetworkRangeTargeting,
    PreviousResultTargeting,
)

__all__ = [
    'BaseTargeting',
    'TargetingRegistry',
    'StaticTargeting',
    'DatabaseQueryTargeting',
    'GroupTargeting',
    'NetworkRangeTargeting',
    'PreviousResultTargeting',
]
