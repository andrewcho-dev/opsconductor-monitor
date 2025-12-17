"""
Platform Validator Utility.

Validates platform compatibility between workflow nodes and target devices.
Used during workflow execution to skip incompatible devices with clear logging.
"""

import logging
from typing import Dict, Any, List, Optional, Set

logger = logging.getLogger(__name__)

# Platform identifiers matching frontend definitions
class Platforms:
    LINUX = 'linux'
    WINDOWS = 'windows'
    MACOS = 'macos'
    UNIX = 'unix'
    CISCO_IOS = 'cisco-ios'
    CISCO_NXOS = 'cisco-nxos'
    CISCO_ASA = 'cisco-asa'
    JUNIPER_JUNOS = 'juniper-junos'
    ARISTA_EOS = 'arista-eos'
    CIENA_SAOS = 'ciena-saos'
    PALOALTO_PANOS = 'paloalto-panos'
    FORTINET_FORTIOS = 'fortinet-fortios'
    MIKROTIK_ROUTEROS = 'mikrotik-routeros'
    UBIQUITI_UNIFI = 'ubiquiti-unifi'
    HPE_ARUBA = 'hpe-aruba'
    DELL_OS10 = 'dell-os10'
    AXIS_CAMERA = 'axis-camera'
    GENERIC_CAMERA = 'generic-camera'
    NETWORK_DEVICE = 'network-device'
    ANY = 'any'


# Platform compatibility mappings
PLATFORM_COMPATIBILITY = {
    Platforms.LINUX: {Platforms.UNIX},
    Platforms.MACOS: {Platforms.UNIX},
    Platforms.UNIX: {Platforms.LINUX, Platforms.MACOS},
    Platforms.CISCO_IOS: {Platforms.NETWORK_DEVICE},
    Platforms.CISCO_NXOS: {Platforms.NETWORK_DEVICE},
    Platforms.CISCO_ASA: {Platforms.NETWORK_DEVICE},
    Platforms.JUNIPER_JUNOS: {Platforms.NETWORK_DEVICE},
    Platforms.ARISTA_EOS: {Platforms.NETWORK_DEVICE},
    Platforms.CIENA_SAOS: {Platforms.NETWORK_DEVICE},
    Platforms.PALOALTO_PANOS: {Platforms.NETWORK_DEVICE},
    Platforms.FORTINET_FORTIOS: {Platforms.NETWORK_DEVICE},
    Platforms.MIKROTIK_ROUTEROS: {Platforms.NETWORK_DEVICE},
    Platforms.UBIQUITI_UNIFI: {Platforms.NETWORK_DEVICE},
    Platforms.HPE_ARUBA: {Platforms.NETWORK_DEVICE},
    Platforms.DELL_OS10: {Platforms.NETWORK_DEVICE},
    Platforms.AXIS_CAMERA: {Platforms.GENERIC_CAMERA},
}

# Platform display names
PLATFORM_NAMES = {
    Platforms.LINUX: 'Linux',
    Platforms.WINDOWS: 'Windows',
    Platforms.MACOS: 'macOS',
    Platforms.UNIX: 'Unix',
    Platforms.CISCO_IOS: 'Cisco IOS',
    Platforms.CISCO_NXOS: 'Cisco NX-OS',
    Platforms.CISCO_ASA: 'Cisco ASA',
    Platforms.JUNIPER_JUNOS: 'Juniper Junos',
    Platforms.ARISTA_EOS: 'Arista EOS',
    Platforms.CIENA_SAOS: 'Ciena SAOS',
    Platforms.PALOALTO_PANOS: 'Palo Alto PAN-OS',
    Platforms.FORTINET_FORTIOS: 'Fortinet FortiOS',
    Platforms.MIKROTIK_ROUTEROS: 'MikroTik RouterOS',
    Platforms.UBIQUITI_UNIFI: 'Ubiquiti UniFi',
    Platforms.HPE_ARUBA: 'HPE Aruba',
    Platforms.DELL_OS10: 'Dell OS10',
    Platforms.AXIS_CAMERA: 'Axis Camera',
    Platforms.GENERIC_CAMERA: 'Camera',
    Platforms.NETWORK_DEVICE: 'Network Device',
    Platforms.ANY: 'Any Platform',
}


def get_platform_name(platform: str) -> str:
    """Get display name for a platform."""
    return PLATFORM_NAMES.get(platform, platform)


def is_platform_compatible(node_platforms: List[str], device_platform: str) -> bool:
    """
    Check if a device platform is compatible with a node's supported platforms.
    
    Args:
        node_platforms: List of platforms the node supports
        device_platform: The platform of the target device
        
    Returns:
        True if compatible, False otherwise
    """
    # If node supports any platform, always compatible
    if Platforms.ANY in node_platforms:
        return True
    
    # If device platform is unknown, assume compatible (let it fail at runtime)
    if not device_platform:
        return True
    
    # Normalize platform string
    device_platform = device_platform.lower().strip()
    
    # Direct match
    if device_platform in node_platforms:
        return True
    
    # Check compatibility mappings
    for node_platform in node_platforms:
        compatible_with = PLATFORM_COMPATIBILITY.get(node_platform, set())
        if device_platform in compatible_with:
            return True
        
        # Reverse check - device platform is compatible with node platform
        device_compatible_with = PLATFORM_COMPATIBILITY.get(device_platform, set())
        if node_platform in device_compatible_with:
            return True
    
    return False


def filter_compatible_devices(
    devices: List[Dict[str, Any]], 
    node_platforms: List[str],
    platform_field: str = 'platform'
) -> tuple:
    """
    Filter a list of devices to only those compatible with the node's platforms.
    
    Args:
        devices: List of device dictionaries
        node_platforms: List of platforms the node supports
        platform_field: Field name containing the device's platform
        
    Returns:
        Tuple of (compatible_devices, skipped_devices)
    """
    # If node supports any platform, all devices are compatible
    if Platforms.ANY in node_platforms:
        return devices, []
    
    compatible = []
    skipped = []
    
    for device in devices:
        device_platform = device.get(platform_field) or device.get('_netbox', {}).get('platform', {}).get('slug')
        
        if is_platform_compatible(node_platforms, device_platform):
            compatible.append(device)
        else:
            skipped.append({
                'device': device,
                'reason': f"Platform '{get_platform_name(device_platform or 'unknown')}' not compatible with node platforms: {', '.join(get_platform_name(p) for p in node_platforms)}"
            })
    
    return compatible, skipped


def log_skipped_devices(skipped: List[Dict[str, Any]], node_name: str = None):
    """
    Log information about skipped devices due to platform incompatibility.
    
    Args:
        skipped: List of skipped device info from filter_compatible_devices
        node_name: Optional name of the node for logging
    """
    if not skipped:
        return
    
    node_info = f" for node '{node_name}'" if node_name else ""
    logger.warning(f"Skipped {len(skipped)} device(s){node_info} due to platform incompatibility:")
    
    for item in skipped:
        device = item['device']
        device_name = device.get('name') or device.get('ip_address') or device.get('ip') or 'unknown'
        logger.warning(f"  SKIPPED: {device_name} - {item['reason']}")


class PlatformValidationResult:
    """Result of platform validation for a workflow execution."""
    
    def __init__(self):
        self.compatible_devices = []
        self.skipped_devices = []
        self.warnings = []
    
    def add_compatible(self, device: Dict[str, Any]):
        self.compatible_devices.append(device)
    
    def add_skipped(self, device: Dict[str, Any], reason: str):
        self.skipped_devices.append({
            'device': device,
            'reason': reason
        })
        self.warnings.append(f"Skipped {device.get('name', device.get('ip_address', 'unknown'))}: {reason}")
    
    @property
    def has_compatible_devices(self) -> bool:
        return len(self.compatible_devices) > 0
    
    @property
    def has_skipped_devices(self) -> bool:
        return len(self.skipped_devices) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'compatible_count': len(self.compatible_devices),
            'skipped_count': len(self.skipped_devices),
            'warnings': self.warnings,
            'skipped_devices': [
                {
                    'name': s['device'].get('name', s['device'].get('ip_address', 'unknown')),
                    'reason': s['reason']
                }
                for s in self.skipped_devices
            ]
        }


def validate_workflow_node_platforms(
    node_config: Dict[str, Any],
    devices: List[Dict[str, Any]]
) -> PlatformValidationResult:
    """
    Validate platform compatibility for a workflow node against target devices.
    
    Args:
        node_config: Node configuration containing 'platforms' list
        devices: List of target devices
        
    Returns:
        PlatformValidationResult with compatible and skipped devices
    """
    result = PlatformValidationResult()
    node_platforms = node_config.get('platforms', [Platforms.ANY])
    
    # If node supports any platform, all devices are compatible
    if Platforms.ANY in node_platforms:
        result.compatible_devices = devices
        return result
    
    for device in devices:
        device_platform = (
            device.get('platform') or 
            device.get('_netbox', {}).get('platform', {}).get('slug') or
            device.get('device_type', {}).get('platform')
        )
        
        if is_platform_compatible(node_platforms, device_platform):
            result.add_compatible(device)
        else:
            platform_names = ', '.join(get_platform_name(p) for p in node_platforms)
            result.add_skipped(
                device,
                f"Platform '{get_platform_name(device_platform or 'unknown')}' not compatible. Node requires: {platform_names}"
            )
    
    return result
