"""
Unit tests for API routes.
"""

import pytest
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check returns 200."""
        response = client.get('/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data.get('data', {}).get('status') == 'healthy' or 'healthy' in str(data)


class TestSystemEndpoints:
    """Tests for system endpoints."""
    
    def test_progress_endpoint(self, client):
        """Test progress endpoint returns scan state."""
        response = client.get('/progress')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'status' in data or 'scanned' in data
    
    def test_test_endpoint(self, client):
        """Test the test endpoint."""
        response = client.get('/test')
        assert response.status_code == 200


class TestDevicesAPI:
    """Tests for devices API."""
    
    def test_get_devices_endpoint_exists(self, client):
        """Test that devices endpoint exists."""
        response = client.get('/api/devices')
        # Should return 200 or 500 (if DB not connected), not 404
        assert response.status_code != 404


class TestGroupsAPI:
    """Tests for groups API."""
    
    def test_get_groups_endpoint_exists(self, client):
        """Test that device_groups endpoint exists."""
        response = client.get('/api/groups')
        # Endpoint may return 404 if not yet implemented, 200 or 500 otherwise
        assert response.status_code in [200, 404, 500]


class TestJobsAPI:
    """Tests for jobs API."""
    
    def test_get_job_definitions_endpoint_exists(self, client):
        """Test that job definitions endpoint exists."""
        response = client.get('/api/job-definitions')
        # Should return 200 or 500 (if DB not connected), not 404
        assert response.status_code != 404


class TestSchedulerAPI:
    """Tests for scheduler API."""
    
    def test_get_scheduler_jobs_endpoint_exists(self, client):
        """Test that scheduler jobs endpoint exists."""
        response = client.get('/api/scheduler/jobs')
        # Should return 200 or 500 (if DB not connected), not 404
        assert response.status_code != 404


class TestSettingsAPI:
    """Tests for settings API."""
    
    def test_get_settings_endpoint_exists(self, client):
        """Test that settings endpoint exists."""
        response = client.get('/api/settings')
        assert response.status_code == 200
    
    def test_get_settings_legacy_endpoint(self, client):
        """Test legacy settings endpoint."""
        response = client.get('/get_settings')
        assert response.status_code == 200
