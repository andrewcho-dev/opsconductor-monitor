"""
HTTP Client Utilities

Centralized HTTP clients for external API integrations.
Use these instead of raw requests.get/post calls.

Usage:
    from backend.utils.http import NetBoxClient, PRTGClient
    
    # NetBox
    client = NetBoxClient()  # Auto-loads config from settings
    devices = client.get('/dcim/devices/')
    
    # Or with explicit config
    client = NetBoxClient(url='http://netbox.local', token='abc123')
"""

import requests
from typing import Any, Dict, List, Optional, Union
import logging

from backend.utils.db import get_setting, get_settings_by_prefix

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30


class BaseAPIClient:
    """Base class for API clients with common functionality."""
    
    def __init__(self, base_url: str, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip('/') if base_url else ''
        self.timeout = timeout
        self.session = requests.Session()
    
    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint."""
        endpoint = endpoint.lstrip('/')
        return f"{self.base_url}/{endpoint}"
    
    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with error handling."""
        url = self._build_url(endpoint)
        kwargs.setdefault('timeout', self.timeout)
        
        try:
            response = self.session.request(method, url, **kwargs)
            return response
        except requests.Timeout:
            logger.error(f"Request timeout: {method} {url}")
            raise
        except requests.RequestException as e:
            logger.error(f"Request failed: {method} {url} - {str(e)}")
            raise
    
    def get(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """GET request returning JSON."""
        response = self._request('GET', endpoint, params=params)
        response.raise_for_status()
        return response.json()
    
    def post(self, endpoint: str, data: Dict = None, json: Dict = None) -> Dict[str, Any]:
        """POST request returning JSON."""
        response = self._request('POST', endpoint, data=data, json=json)
        response.raise_for_status()
        return response.json()
    
    def put(self, endpoint: str, json: Dict = None) -> Dict[str, Any]:
        """PUT request returning JSON."""
        response = self._request('PUT', endpoint, json=json)
        response.raise_for_status()
        return response.json()
    
    def patch(self, endpoint: str, json: Dict = None) -> Dict[str, Any]:
        """PATCH request returning JSON."""
        response = self._request('PATCH', endpoint, json=json)
        response.raise_for_status()
        return response.json()
    
    def delete(self, endpoint: str) -> bool:
        """DELETE request."""
        response = self._request('DELETE', endpoint)
        response.raise_for_status()
        return True


class NetBoxClient(BaseAPIClient):
    """
    NetBox API Client.
    
    Auto-loads URL and token from system_settings if not provided.
    
    Usage:
        client = NetBoxClient()
        devices = client.get_devices()
        prefixes = client.get_prefixes()
    """
    
    def __init__(self, url: str = None, token: str = None, timeout: int = DEFAULT_TIMEOUT):
        # Load from settings if not provided
        if not url:
            url = get_setting('netbox_url', '')
        if not token:
            token = get_setting('netbox_token', '')
        
        super().__init__(url, timeout)
        self.token = token
        
        # Set auth header
        if self.token:
            self.session.headers['Authorization'] = f'Token {self.token}'
            self.session.headers['Content-Type'] = 'application/json'
    
    @property
    def is_configured(self) -> bool:
        """Check if NetBox is properly configured."""
        return bool(self.base_url and self.token)
    
    def test_connection(self) -> Dict[str, Any]:
        """Test NetBox connection and return status info."""
        if not self.is_configured:
            return {'success': False, 'error': 'NetBox not configured'}
        
        try:
            response = self.get('/api/status/')
            return {
                'success': True,
                'netbox_version': response.get('netbox-version'),
                'python_version': response.get('python-version'),
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_devices(self, limit: int = 1000, **filters) -> List[Dict]:
        """Get devices from NetBox."""
        params = {'limit': limit, **filters}
        response = self.get('/api/dcim/devices/', params=params)
        return response.get('results', [])
    
    def get_prefixes(self, limit: int = 500) -> List[Dict]:
        """Get IP prefixes from NetBox."""
        response = self.get('/api/ipam/prefixes/', params={'limit': limit})
        return response.get('results', [])
    
    def get_ip_ranges(self, limit: int = 500) -> List[Dict]:
        """Get IP ranges from NetBox."""
        response = self.get('/api/ipam/ip-ranges/', params={'limit': limit})
        return response.get('results', [])
    
    def get_tags(self) -> List[Dict]:
        """Get tags from NetBox."""
        response = self.get('/api/extras/tags/')
        return response.get('results', [])


class PRTGClient(BaseAPIClient):
    """
    PRTG API Client.
    
    Auto-loads config from system_settings if not provided.
    """
    
    def __init__(self, url: str = None, username: str = None, passhash: str = None, timeout: int = DEFAULT_TIMEOUT):
        # Load from settings if not provided
        if not url:
            url = get_setting('prtg_url', '')
        if not username:
            username = get_setting('prtg_username', '')
        if not passhash:
            passhash = get_setting('prtg_passhash', '')
        
        super().__init__(url, timeout)
        self.username = username
        self.passhash = passhash
    
    @property
    def is_configured(self) -> bool:
        """Check if PRTG is properly configured."""
        return bool(self.base_url and self.username and self.passhash)
    
    def _add_auth(self, params: Dict) -> Dict:
        """Add authentication to request params."""
        params = params or {}
        params['username'] = self.username
        params['passhash'] = self.passhash
        return params
    
    def get(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """GET request with PRTG auth."""
        params = self._add_auth(params or {})
        return super().get(endpoint, params)
    
    def test_connection(self) -> Dict[str, Any]:
        """Test PRTG connection."""
        if not self.is_configured:
            return {'success': False, 'error': 'PRTG not configured'}
        
        try:
            response = self.get('/api/status.json')
            return {'success': True, 'version': response.get('Version')}
        except Exception as e:
            return {'success': False, 'error': str(e)}


class MCPClient(BaseAPIClient):
    """
    MCP (Model Context Protocol) Client.
    
    For Ciena MCP integration.
    """
    
    def __init__(self, url: str = None, timeout: int = DEFAULT_TIMEOUT):
        if not url:
            url = get_setting('mcp_url', '')
        super().__init__(url, timeout)
    
    @property
    def is_configured(self) -> bool:
        """Check if MCP is configured."""
        return bool(self.base_url)
