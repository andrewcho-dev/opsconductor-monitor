"""Backend parsers package - Output parsing with registry pattern."""

from .base import BaseParser
from .registry import ParserRegistry

__all__ = ['BaseParser', 'ParserRegistry']
