"""
IP address utilities.

Provides functions for IP address manipulation, sorting, and network calculations.
"""

import ipaddress
from typing import List, Tuple, Union


def ip_to_int(ip: str) -> int:
    """
    Convert an IP address string to an integer for sorting/comparison.
    
    Args:
        ip: IP address string (e.g., '10.0.0.1')
    
    Returns:
        Integer representation of the IP address
    """
    try:
        return int(ipaddress.IPv4Address(ip))
    except (ipaddress.AddressValueError, ValueError):
        return 0


def int_to_ip(value: int) -> str:
    """
    Convert an integer to an IP address string.
    
    Args:
        value: Integer representation of IP address
    
    Returns:
        IP address string
    """
    return str(ipaddress.IPv4Address(value))


def sort_ips(ips: List[str]) -> List[str]:
    """
    Sort a list of IP addresses numerically.
    
    Args:
        ips: List of IP address strings
    
    Returns:
        Sorted list of IP addresses
    """
    return sorted(ips, key=ip_to_int)


def is_valid_ip(ip: str) -> bool:
    """
    Check if a string is a valid IPv4 address.
    
    Args:
        ip: String to validate
    
    Returns:
        True if valid IPv4 address, False otherwise
    """
    try:
        ipaddress.IPv4Address(ip)
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


def is_valid_cidr(cidr: str) -> bool:
    """
    Check if a string is a valid CIDR notation.
    
    Args:
        cidr: String to validate (e.g., '10.0.0.0/24')
    
    Returns:
        True if valid CIDR, False otherwise
    """
    try:
        ipaddress.IPv4Network(cidr, strict=False)
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


def get_network_range(cidr: str) -> Tuple[str, str]:
    """
    Get the first and last IP addresses in a CIDR range.
    
    Args:
        cidr: CIDR notation string (e.g., '10.0.0.0/24')
    
    Returns:
        Tuple of (first_ip, last_ip)
    """
    network = ipaddress.IPv4Network(cidr, strict=False)
    return str(network.network_address), str(network.broadcast_address)


def expand_cidr(cidr: str) -> List[str]:
    """
    Expand a CIDR range to a list of all IP addresses.
    
    Warning: Use with caution on large ranges (e.g., /16 = 65536 IPs)
    
    Args:
        cidr: CIDR notation string
    
    Returns:
        List of all IP addresses in the range
    """
    network = ipaddress.IPv4Network(cidr, strict=False)
    return [str(ip) for ip in network.hosts()]


def ip_in_network(ip: str, cidr: str) -> bool:
    """
    Check if an IP address is within a CIDR range.
    
    Args:
        ip: IP address to check
        cidr: CIDR notation network
    
    Returns:
        True if IP is in the network, False otherwise
    """
    try:
        address = ipaddress.IPv4Address(ip)
        network = ipaddress.IPv4Network(cidr, strict=False)
        return address in network
    except (ipaddress.AddressValueError, ValueError):
        return False


def get_network_for_ip(ip: str, prefix_length: int = 24) -> str:
    """
    Get the network CIDR for an IP address with given prefix length.
    
    Args:
        ip: IP address
        prefix_length: Network prefix length (default: 24)
    
    Returns:
        CIDR notation for the network
    """
    try:
        interface = ipaddress.IPv4Interface(f'{ip}/{prefix_length}')
        return str(interface.network)
    except (ipaddress.AddressValueError, ValueError):
        return None


def parse_ip_range(range_str: str) -> List[str]:
    """
    Parse an IP range string into a list of IPs.
    
    Supports formats:
    - Single IP: '10.0.0.1'
    - CIDR: '10.0.0.0/24'
    - Range: '10.0.0.1-10.0.0.10'
    - Comma-separated: '10.0.0.1,10.0.0.2,10.0.0.3'
    
    Args:
        range_str: IP range string
    
    Returns:
        List of IP addresses
    """
    range_str = range_str.strip()
    
    # Comma-separated list
    if ',' in range_str:
        ips = []
        for part in range_str.split(','):
            ips.extend(parse_ip_range(part.strip()))
        return ips
    
    # CIDR notation
    if '/' in range_str:
        return expand_cidr(range_str)
    
    # IP range (start-end)
    if '-' in range_str:
        parts = range_str.split('-')
        if len(parts) == 2:
            start_ip = parts[0].strip()
            end_part = parts[1].strip()
            
            # Handle partial end IP (e.g., '10.0.0.1-10' means '10.0.0.1-10.0.0.10')
            if '.' not in end_part:
                base = '.'.join(start_ip.split('.')[:-1])
                end_ip = f'{base}.{end_part}'
            else:
                end_ip = end_part
            
            start_int = ip_to_int(start_ip)
            end_int = ip_to_int(end_ip)
            
            if start_int <= end_int:
                return [int_to_ip(i) for i in range(start_int, end_int + 1)]
    
    # Single IP
    if is_valid_ip(range_str):
        return [range_str]
    
    return []


def group_ips_by_network(ips: List[str], prefix_length: int = 24) -> dict:
    """
    Group IP addresses by their network.
    
    Args:
        ips: List of IP addresses
        prefix_length: Network prefix length for grouping
    
    Returns:
        Dictionary mapping network CIDR to list of IPs
    """
    groups = {}
    for ip in ips:
        network = get_network_for_ip(ip, prefix_length)
        if network:
            if network not in groups:
                groups[network] = []
            groups[network].append(ip)
    
    # Sort IPs within each group
    for network in groups:
        groups[network] = sort_ips(groups[network])
    
    return groups
