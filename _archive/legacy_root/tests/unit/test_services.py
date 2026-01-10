"""
Unit tests for services.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.services import JobExecutor, NotificationService


class TestJobExecutor:
    """Tests for JobExecutor."""
    
    def test_init(self):
        """Test JobExecutor initialization."""
        executor = JobExecutor()
        assert executor is not None
    
    def test_execute_empty_job(self):
        """Test executing an empty job definition."""
        executor = JobExecutor()
        result = executor.execute_job({
            'id': 'test-job',
            'name': 'Test Job',
            'actions': [],
        })
        
        assert result['job_id'] == 'test-job'
        assert result['actions_completed'] == 0
        assert result['total_actions'] == 0
    
    def test_execute_job_with_unknown_action(self):
        """Test executing a job with unknown action type."""
        executor = JobExecutor()
        result = executor.execute_job({
            'id': 'test-job',
            'name': 'Test Job',
            'actions': [
                {'type': 'unknown_action_type'}
            ],
        })
        
        assert 'errors' in result or 'action_results' in result


class TestNotificationService:
    """Tests for NotificationService."""
    
    def test_init_empty(self):
        """Test NotificationService initialization with no targets."""
        service = NotificationService()
        assert service.targets == []
    
    def test_init_with_targets(self):
        """Test NotificationService initialization with targets."""
        targets = ['mailto://user@example.com', 'slack://token']
        service = NotificationService(targets)
        assert service.targets == targets
    
    def test_send_no_targets(self):
        """Test sending notification with no targets."""
        service = NotificationService()
        result = service.send('Test', 'Test message')
        assert result == False
    
    @patch('backend.services.notification_service.APPRISE_AVAILABLE', False)
    def test_send_apprise_unavailable(self):
        """Test sending notification when Apprise is not available."""
        service = NotificationService(['mailto://test@test.com'])
        result = service.send('Test', 'Test message')
        assert result == False
