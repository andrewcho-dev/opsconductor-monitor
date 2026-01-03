"""
Notification Service.

Centralized notification helper using Apprise.
Provides a wrapper around Apprise so the rest of the application can send 
notifications without depending on provider-specific APIs.
"""

from __future__ import annotations

import logging
from typing import Iterable, List, Optional

try:
    import apprise
    APPRISE_AVAILABLE = True
except ImportError:
    APPRISE_AVAILABLE = False

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for sending notifications via Apprise.
    
    Supports email, Slack, MS Teams, SMS, webhooks, etc.
    """
    
    def __init__(self, targets: Optional[List[str]] = None):
        """
        Initialize notification service.
        
        Args:
            targets: List of Apprise URLs
        """
        self.targets = targets or []
    
    def send(
        self,
        title: str,
        body: str,
        tag: Optional[str] = None,
        targets: Optional[Iterable[str]] = None,
    ) -> bool:
        """
        Send a notification.
        
        Args:
            title: Short title for the notification
            body: Main message body
            tag: Optional tag/context (e.g. "job.completed")
            targets: Override default targets
        
        Returns:
            True if at least one notification was successfully delivered
        """
        if not APPRISE_AVAILABLE:
            logger.warning("Apprise not installed, notifications disabled")
            return False
        
        target_list = list(targets or self.targets or [])
        if not target_list:
            logger.debug("No notification targets configured")
            return False
        
        app = apprise.Apprise()
        for url in target_list:
            if not url:
                continue
            try:
                app.add(url)
            except Exception as e:
                logger.warning(f"Invalid Apprise URL: {e}")
                continue
        
        if not app:
            return False
        
        full_body = body
        if tag:
            full_body = f"[{tag}] {body}"
        
        try:
            result = bool(app.notify(title=title, body=full_body))
            if result:
                logger.info(f"Notification sent: {title}")
            return result
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False
    
    def send_job_notification(
        self,
        job_name: str,
        status: str,
        message: str,
        details: Optional[dict] = None,
    ) -> bool:
        """
        Send a job-related notification.
        
        Args:
            job_name: Name of the job
            status: Job status (success, failed, etc.)
            message: Notification message
            details: Optional additional details
        """
        title = f"Job {status.upper()}: {job_name}"
        body = message
        
        if details:
            body += "\n\nDetails:\n"
            for key, value in details.items():
                body += f"  {key}: {value}\n"
        
        return self.send(title, body, tag=f"job.{status}")
    
    def send_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = "warning",
    ) -> bool:
        """
        Send an alert notification.
        
        Args:
            alert_type: Type of alert (e.g., "optical_power", "device_offline")
            message: Alert message
            severity: Alert severity (info, warning, error, critical)
        """
        title = f"[{severity.upper()}] {alert_type}"
        return self.send(title, message, tag=f"alert.{alert_type}")


# Module-level function for backward compatibility
def send_notification(
    targets: Iterable[str],
    title: str,
    body: str,
    tag: Optional[str] = None,
) -> bool:
    """
    Send a notification to one or more Apprise target URLs.
    
    Backward compatible function.
    """
    service = NotificationService(list(targets))
    return service.send(title, body, tag)
