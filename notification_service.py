"""
Notification Service - Compatibility wrapper.

This module provides backward compatibility with code that imports from notification_service.py.
It delegates to the new backend.services.notification_service module.
"""

from backend.services.notification_service import (
    NotificationService,
    send_notification,
)

__all__ = ['NotificationService', 'send_notification']
