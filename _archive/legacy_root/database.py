"""
Database module - Compatibility wrapper.

This module provides backward compatibility with code that imports from database.py.
It delegates to the new backend.database module.
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import DatabaseConnection, get_db

# Alias for backward compatibility
DatabaseManager = DatabaseConnection
db = get_db()

__all__ = ['DatabaseManager', 'DatabaseConnection', 'db', 'get_db']
