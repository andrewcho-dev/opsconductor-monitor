"""
Config - Compatibility wrapper.

This module provides backward compatibility with code that imports from config.py.
It delegates to the new backend.config.settings module.
"""

from backend.config.settings import (
    Settings,
    get_settings as get_app_settings,
    get_json_settings,
    save_json_settings,
)

# Backward compatible aliases
get_settings = get_json_settings
save_settings = save_json_settings

__all__ = ['get_settings', 'save_settings', 'Settings', 'get_app_settings']
