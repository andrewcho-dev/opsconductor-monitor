"""
IP Address Utilities

Provides IP validation and hostname resolution for cross-system correlation.
All connectors MUST use device_ip (not hostname) for exact correlation.
"""

import socket
import logging
import re
from functools import lru_cache

logger = logging.getLogger(__name__)


def is_valid_ip(value: str) -> bool:
    """Check if value is a valid IPv4 address."""
    if not value:
        return False
    
    parts = value.split(".")
    if len(parts) != 4:
        return False
    
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


def extract_ip_from_string(value: str) -> str:
    """
    Extract IP address from a string that may contain hostname, URL, or IP in parentheses.
    
    Examples:
        "10.120.4.105" -> "10.120.4.105"
        "10.120.12.22 (BUR-SW02)" -> "10.120.12.22"
        "http://10.120.81.107/" -> "10.120.81.107"
        "http://10.120.81.107:8080/path" -> "10.120.81.107"
        "Device (10.120.1.5)" -> "10.120.1.5"
        "BUR-SW02" -> raises ValueError
    """
    if not value:
        raise ValueError("Value cannot be empty - device_ip is required")
    
    value = value.strip()
    
    # Find any IP address pattern anywhere in the string
    ip_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    match = re.search(ip_pattern, value)
    
    if match:
        ip = match.group(1)
        if is_valid_ip(ip):
            return ip
    
    raise ValueError(f"Cannot extract IP address from '{value}'")


@lru_cache(maxsize=1000)
def resolve_to_ip(host: str) -> str:
    """
    Resolve hostname to IP address.
    
    Returns the IP if already an IP, resolves DNS if hostname.
    Raises ValueError if cannot resolve.
    
    Results are cached for performance.
    """
    if not host:
        raise ValueError("Host cannot be empty - device_ip is required")
    
    host = host.strip()
    
    # Already an IP?
    if is_valid_ip(host):
        return host
    
    # Try to extract IP from string like "10.1.2.3 (hostname)"
    try:
        return extract_ip_from_string(host)
    except ValueError:
        pass
    
    # Try DNS resolution
    try:
        ip = socket.gethostbyname(host)
        logger.debug(f"Resolved {host} to {ip}")
        return ip
    except socket.gaierror as e:
        logger.warning(f"Cannot resolve hostname {host}: {e}")
        raise ValueError(f"Cannot resolve hostname '{host}' to IP address - device_ip is required for correlation")


def validate_device_ip(device_ip: str, device_name: str = None) -> str:
    """
    Validate and return a proper device_ip for alert correlation.
    
    Tries in order:
    1. device_ip if it's a valid IP
    2. Extract IP from device_ip if it contains one
    3. Extract IP from device_name if it contains one
    4. Resolve device_ip via DNS
    5. Resolve device_name via DNS
    
    Raises ValueError if no valid IP can be determined.
    """
    # Try device_ip first
    if device_ip:
        device_ip = device_ip.strip()
        
        # Already a valid IP?
        if is_valid_ip(device_ip):
            return device_ip
        
        # Try to extract IP from string
        try:
            return extract_ip_from_string(device_ip)
        except ValueError:
            pass
        
        # Try DNS resolution
        try:
            return resolve_to_ip(device_ip)
        except ValueError:
            pass
    
    # Try device_name as fallback
    if device_name:
        device_name = device_name.strip()
        
        # Try to extract IP from device_name
        try:
            return extract_ip_from_string(device_name)
        except ValueError:
            pass
        
        # Try DNS resolution
        try:
            return resolve_to_ip(device_name)
        except ValueError:
            pass
    
    # Nothing worked
    raise ValueError(
        f"Cannot determine device_ip from device_ip='{device_ip}' or device_name='{device_name}'. "
        "A valid IP address is required for cross-system correlation."
    )
