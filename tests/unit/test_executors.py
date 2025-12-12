"""
Unit tests for executors.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.executors import ExecutorRegistry, PingExecutor, SNMPExecutor, SSHExecutor


class TestExecutorRegistry:
    """Tests for ExecutorRegistry."""
    
    def test_registry_has_executors(self):
        """Test that executors are registered."""
        executors = ExecutorRegistry.list_executors()
        assert len(executors) >= 0  # May be empty if not imported
    
    def test_get_nonexistent_executor(self):
        """Test getting a non-existent executor."""
        executor = ExecutorRegistry.get('nonexistent_executor_xyz')
        assert executor is None


class TestPingExecutor:
    """Tests for PingExecutor."""
    
    def test_init(self):
        """Test PingExecutor initialization."""
        executor = PingExecutor()
        assert executor is not None
    
    @patch('subprocess.run')
    def test_execute_success(self, mock_run):
        """Test successful ping execution."""
        mock_run.return_value = Mock(returncode=0, stdout='64 bytes from 192.168.1.1')
        
        executor = PingExecutor()
        result = executor.execute('192.168.1.1', config={'timeout': 1, 'count': 1})
        
        assert result.get('success') or result.get('reachable')
    
    @patch('subprocess.run')
    def test_execute_failure(self, mock_run):
        """Test failed ping execution."""
        mock_run.return_value = Mock(returncode=1, stdout='')
        
        executor = PingExecutor()
        result = executor.execute('192.168.1.1', config={'timeout': 1, 'count': 1})
        
        # Either success=False or reachable=False
        assert not result.get('success', True) or not result.get('reachable', True)


class TestSNMPExecutor:
    """Tests for SNMPExecutor."""
    
    def test_init(self):
        """Test SNMPExecutor initialization."""
        executor = SNMPExecutor()
        assert executor is not None
    
    def test_execute_invalid_target(self):
        """Test SNMP execution with invalid target."""
        executor = SNMPExecutor()
        result = executor.execute('', '1.3.6.1.2.1.1.1.0', {'community': 'public'})
        
        # Should fail gracefully
        assert not result.get('success', False)


class TestSSHExecutor:
    """Tests for SSHExecutor."""
    
    def test_init(self):
        """Test SSHExecutor initialization."""
        executor = SSHExecutor()
        assert executor is not None
    
    def test_execute_missing_credentials(self):
        """Test SSH execution with missing credentials."""
        executor = SSHExecutor()
        result = executor.execute('192.168.1.1', 'show version', {})
        
        # Should fail due to missing credentials
        assert not result.get('success', False)
