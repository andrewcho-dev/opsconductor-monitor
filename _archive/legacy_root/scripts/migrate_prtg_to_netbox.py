#!/usr/bin/env python3
"""
One-time PRTG to NetBox Migration Script

Imports all PRTG devices into NetBox with auto-categorization:
- Extracts site code from PRTG group name
- Determines device role from group suffix (Cameras, Switches, NVRs, etc.)
- Creates missing sites/roles as needed
- Uses Generic device type for unknown models
- Optionally tests SNMP v2 connectivity

Usage:
    python scripts/migrate_prtg_to_netbox.py --dry-run    # Preview only
    python scripts/migrate_prtg_to_netbox.py              # Actually import
    python scripts/migrate_prtg_to_netbox.py --test-snmp  # Test SNMP on each device
"""

import sys
import os
import re
import argparse
import ipaddress
from typing import Dict, List, Optional, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.prtg_service import PRTGService
from backend.services.netbox_service import NetBoxService

# Role mapping from PRTG group suffix to NetBox role
ROLE_MAPPING = {
    'cameras': 'camera',
    'camera': 'camera',
    'switches': 'edge-switch',
    'switch': 'edge-switch',
    'nvrs': 'nvr',
    'nvr': 'nvr',
    'upss': 'ups',
    'ups': 'ups',
    'router': 'edge-router',
    'routers': 'edge-router',
    'wireless': 'edge-switch',  # Treat wireless APs as edge switches
    'workstations': 'workstation',
    'workstation': 'workstation',
    'servers': 'server',
    'server': 'server',
    'firewalls': 'firewall',
    'firewall': 'firewall',
    'extenders': 'edge-switch',
    'extender': 'edge-switch',
}

# Special group patterns that override the standard parsing
SPECIAL_GROUPS = {
    'ciena switches': 'backbone-switch',
    'core switches': 'backbone-switch',
    'core router': 'core-router',
    'core routers': 'core-router',
    'domain controllers': 'server',
    'virtual machines': 'server',
    'virtualization': 'virtualization-host',
}

# Groups to skip (probe devices only - not actual network devices)
SKIP_GROUPS = [
    'local probe',
    'remote probe',
    'internet service',
]

# Groups that map to SDN site
SDN_GROUPS = [
    'sdn infrastructure',
    'sdn routers',
]


def get_netbox_settings():
    """Get NetBox settings from database."""
    from database import DatabaseManager
    db = DatabaseManager()
    settings = {}
    
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT key, value FROM system_settings 
            WHERE key LIKE 'netbox_%'
        """)
        for row in cursor.fetchall():
            key = row['key'].replace('netbox_', '')
            settings[key] = row['value']
    
    return settings


def get_prtg_settings():
    """Get PRTG settings from database."""
    from database import DatabaseManager
    db = DatabaseManager()
    settings = {}
    
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT key, value FROM system_settings 
            WHERE key LIKE 'prtg_%'
        """)
        for row in cursor.fetchall():
            key = row['key'].replace('prtg_', '')
            settings[key] = row['value']
    
    return settings


def is_valid_ip(ip: str) -> bool:
    """Check if string is a valid IP address."""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def extract_ip_from_device_name(device_name: str) -> Optional[str]:
    """
    Extract IP address from device name like "10.121.61.71 (EVC-UPS01)" or "POS - Downtown (10.121.30.1)".
    """
    # Pattern 1: IP at start "10.x.x.x (name)"
    match = re.match(r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s', device_name)
    if match:
        return match.group(1)
    
    # Pattern 2: IP in parentheses "(10.x.x.x)"
    match = re.search(r'\((\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\)', device_name)
    if match:
        return match.group(1)
    
    return None


def extract_site_and_role(group: str, device_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract site code and role from PRTG group name.
    
    Examples:
        "AMF Cameras" -> ("AMF", "camera")
        "BUR Switches" -> ("BUR", "edge-switch")
        "T25 Cameras" -> ("T25", "camera")
        "MPK/MPL Router" -> ("MPK", "edge-router") or ("MPL", "edge-router")
    """
    group_lower = group.lower()
    
    # Check for groups to skip (probe devices)
    for skip in SKIP_GROUPS:
        if skip in group_lower:
            return None, None
    
    # Handle Tunnel sites (T25, T26, T27) - group starts with T2x
    tunnel_match = re.match(r'^(T2[567])\s+(.+)', group, re.IGNORECASE)
    if tunnel_match:
        site_code = tunnel_match.group(1).upper()
        type_part = tunnel_match.group(2).lower()
        for pattern, role in ROLE_MAPPING.items():
            if pattern in type_part:
                return site_code, role
        return site_code, 'edge-switch'
    
    # Handle "Tunnel 26/27" format
    tunnel_match2 = re.match(r'^Tunnel\s+(2[567])\s+(.+)', group, re.IGNORECASE)
    if tunnel_match2:
        site_code = f"T{tunnel_match2.group(1)}"
        type_part = tunnel_match2.group(2).lower()
        for pattern, role in ROLE_MAPPING.items():
            if pattern in type_part:
                return site_code, role
        return site_code, 'edge-switch'
    
    # Handle MPK/MPL - extract site from device name (MPK-xxx or MPL-xxx)
    if 'mpk/mpl' in group_lower:
        # Try to get MPK or MPL from device name
        if 'MPL-' in device_name.upper() or '(MPL-' in device_name.upper():
            site_code = 'MPL'
        elif 'MPK-' in device_name.upper() or '(MPK-' in device_name.upper():
            site_code = 'MPK'
        else:
            # Default to MPK if can't determine
            site_code = 'MPK'
        
        type_part = group_lower
        for pattern, role in ROLE_MAPPING.items():
            if pattern in type_part:
                return site_code, role
        return site_code, 'edge-switch'
    
    # Handle SDN Infrastructure
    for sdn_pattern in SDN_GROUPS:
        if sdn_pattern in group_lower:
            type_part = group_lower
            for pattern, role in ROLE_MAPPING.items():
                if pattern in type_part:
                    return 'SDN', role
            return 'SDN', 'server'
    
    # Check special groups
    for pattern, role in SPECIAL_GROUPS.items():
        if pattern in group_lower:
            site = extract_site_from_device_name(device_name)
            return site, role
    
    # Standard pattern: "{SITE} {TYPE}" or "{SITE} {TYPE}s"
    parts = group.split()
    if len(parts) >= 2:
        site_code = parts[0].upper()
        # Accept 2-4 character alphanumeric site codes (for T25, etc.)
        if 2 <= len(site_code) <= 4 and site_code.replace('-', '').isalnum():
            type_part = ' '.join(parts[1:]).lower()
            
            for pattern, role in ROLE_MAPPING.items():
                if pattern in type_part:
                    return site_code, role
            
            return site_code, 'edge-switch'
    
    # Fallback: try to extract site from device name
    site = extract_site_from_device_name(device_name)
    return site, None


def extract_site_from_device_name(device_name: str) -> Optional[str]:
    """
    Extract site code from device name.
    
    Examples:
        "10.120.130.104 (AMF-CAM04)" -> "AMF"
        "10.121.39.21-CMT-SW01" -> "CMT"
    """
    # Pattern: (XXX-...) or -XXX-
    match = re.search(r'\(([A-Z]{2,4})-', device_name.upper())
    if match:
        return match.group(1)
    
    match = re.search(r'-([A-Z]{2,4})-', device_name.upper())
    if match:
        return match.group(1)
    
    return None


def get_snmp_info(ip: str, community: str = 'public', timeout: int = 2) -> Optional[Dict]:
    """
    Get SNMP system info from a device.
    
    Returns dict with:
        - sysDescr: System description (often contains model info)
        - sysName: System hostname
        - sysObjectID: OID identifying the device type
    """
    try:
        from pysnmp.hlapi import (
            getCmd, SnmpEngine, CommunityData, UdpTransportTarget,
            ContextData, ObjectType, ObjectIdentity
        )
        
        # OIDs to query
        oids = [
            ('sysDescr', '1.3.6.1.2.1.1.1.0'),
            ('sysObjectID', '1.3.6.1.2.1.1.2.0'),
            ('sysName', '1.3.6.1.2.1.1.5.0'),
        ]
        
        result = {}
        
        for name, oid in oids:
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=1),  # v2c
                UdpTransportTarget((ip, 161), timeout=timeout, retries=0),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            if not errorIndication and not errorStatus and varBinds:
                result[name] = str(varBinds[0][1])
        
        return result if result else None
    except Exception as e:
        return None


# Device type detection patterns from sysDescr
SYSDESCR_PATTERNS = [
    # Axis cameras
    (r'AXIS\s+(M\d+[A-Z\-]+)', 'Axis', None),  # AXIS M3057-PLVE
    (r'AXIS\s+(P\d+[A-Z\-\s]+)', 'Axis', None),  # AXIS P3225-LVE MK II
    (r'AXIS\s+(Q\d+[A-Z\-]+)', 'Axis', None),  # AXIS Q6074-E
    (r'AXIS\s+(T\d+)', 'Axis', None),  # AXIS T8516
    
    # Ciena switches
    (r'Ciena.*(\d{4})', 'Ciena', None),  # Ciena 3942, 5160
    
    # Cisco
    (r'Cisco.*ASR(\d+[A-Z\-]*)', 'Cisco', 'ASR'),  # ASR1001-X
    (r'Cisco.*ASA(\d+)', 'Cisco', 'ASA'),  # ASA5516
    (r'Cisco IOS.*C(\d+)', 'Cisco', 'C'),  # Catalyst switches
    
    # Cradlepoint
    (r'Cradlepoint.*?(IBR\d+)', 'Cradlepoint', None),
    (r'IBR(\d+)', 'Cradlepoint', 'IBR'),
    
    # Eaton UPS
    (r'Eaton.*?(5PX\s*\d+)', 'Eaton', 'Eaton '),
    (r'EATON.*?(\d+\s*VA)', 'Eaton', 'Eaton '),
    
    # Planet switches
    (r'Planet.*?(GS-\d+[A-Z\-\d]+)', 'Planet USA', None),
    (r'Planet.*?(WGS-\d+[A-Z\-\d]+)', 'Planet USA', None),
    
    # Razberi NVR
    (r'Razberi.*?(SSIQ[A-Z\d\-]+)', 'Razberi', None),
    
    # Siklu wireless
    (r'Siklu.*?(EH-\d+[A-Z\-]+)', 'Siklu', None),
    (r'Siklu.*?(MH-[A-Z\d\-]+)', 'Siklu', None),
    
    # Dell
    (r'Dell.*PowerEdge\s*(\w+)', 'Dell', 'PowerEdge'),
    (r'Dell.*Precision\s*(\d+)', 'Dell', None),
    
    # FS.com
    (r'FS\.com.*?(S\d+[A-Z\-\d]+)', 'FS.com', None),
    
    # Generic Linux/Windows
    (r'(Linux)', 'Generic', 'Server'),
    (r'(Windows)', 'Generic', 'Server'),
]


def detect_device_type_from_snmp(snmp_info: Dict) -> Tuple[Optional[str], Optional[str]]:
    """
    Detect device manufacturer and model from SNMP sysDescr.
    
    Returns: (manufacturer, model) or (None, None) if not detected
    """
    if not snmp_info:
        return None, None
    
    sys_descr = snmp_info.get('sysDescr', '')
    
    for pattern, manufacturer, prefix in SYSDESCR_PATTERNS:
        match = re.search(pattern, sys_descr, re.IGNORECASE)
        if match:
            try:
                model = match.group(1).strip()
                if prefix and not model.startswith(prefix):
                    model = f"{prefix}{model}"
                return manufacturer, model
            except IndexError:
                # Pattern matched but no capture group
                continue
    
    return None, None


def detect_role_from_ip(ip: str) -> Optional[str]:
    """
    Detect device role from IP address patterns.
    
    For 10.120.x.x and 10.121.x.x networks:
    - Last octet 11-13: NVR
    - Last octet 20-29: Switch (edge-switch)
    - Last octet 70-79: UPS
    - Last octet 101-199: Camera
    """
    try:
        parts = ip.split('.')
        if len(parts) != 4:
            return None
        
        # Only apply to 10.120.x.x and 10.121.x.x
        if parts[0] != '10' or parts[1] not in ('120', '121'):
            return None
        
        last_octet = int(parts[3])
        
        if 11 <= last_octet <= 13:
            return 'nvr'
        elif 20 <= last_octet <= 29:
            return 'edge-switch'
        elif 70 <= last_octet <= 79:
            return 'ups'
        elif 101 <= last_octet <= 199:
            return 'camera'
        
        return None
    except (ValueError, IndexError):
        return None


class PRTGMigrator:
    """Handles the PRTG to NetBox migration."""
    
    def __init__(self, dry_run: bool = False, test_snmp: bool = False, snmp_community: str = 'public'):
        self.dry_run = dry_run
        self.test_snmp = test_snmp
        self.snmp_community = snmp_community
        
        # Initialize services
        prtg_settings = get_prtg_settings()
        self.prtg = PRTGService(
            url=prtg_settings.get('url', ''),
            username=prtg_settings.get('username', ''),
            passhash=prtg_settings.get('passhash', '')
        )
        
        netbox_settings = get_netbox_settings()
        self.netbox = NetBoxService(
            url=netbox_settings.get('url', ''),
            token=netbox_settings.get('token', ''),
            verify_ssl=netbox_settings.get('verify_ssl', 'true').lower() == 'true'
        )
        
        # Cache for lookups
        self.sites_cache = {}
        self.roles_cache = {}
        self.types_cache = {}
        self.existing_devices = set()
        
        # Stats
        self.stats = {
            'total': 0,
            'skipped_invalid_ip': 0,
            'skipped_exists': 0,
            'skipped_no_site': 0,
            'created': 0,
            'failed': 0,
            'snmp_ok': 0,
            'snmp_fail': 0,
            'types_detected': 0,
            'types_created': 0,
        }
    
    def load_caches(self):
        """Load NetBox data into caches."""
        print("Loading NetBox data...")
        
        # Load sites
        sites = self.netbox.get_sites(limit=1000).get('results', [])
        for s in sites:
            self.sites_cache[s['slug'].upper()] = s['id']
            self.sites_cache[s['name'].upper()] = s['id']
        print(f"  Loaded {len(sites)} sites")
        
        # Load roles
        roles = self.netbox.get_device_roles(limit=100).get('results', [])
        for r in roles:
            self.roles_cache[r['slug']] = r['id']
        print(f"  Loaded {len(roles)} roles")
        
        # Load device types
        types = self.netbox.get_device_types(limit=500).get('results', [])
        for t in types:
            self.types_cache[t['slug']] = t['id']
        print(f"  Loaded {len(types)} device types")
        
        # Load existing devices by IP
        devices = self.netbox.get_devices(limit=5000).get('results', [])
        for d in devices:
            if d.get('primary_ip4'):
                ip = d['primary_ip4'].get('address', '').split('/')[0]
                self.existing_devices.add(ip)
        print(f"  Loaded {len(self.existing_devices)} existing devices")
    
    def get_or_create_site(self, site_code: str) -> Optional[int]:
        """Get site ID, creating if necessary."""
        site_upper = site_code.upper()
        
        if site_upper in self.sites_cache:
            return self.sites_cache[site_upper]
        
        if self.dry_run:
            print(f"    [DRY-RUN] Would create site: {site_code}")
            return None
        
        # Create the site
        try:
            slug = site_code.lower()
            result = self.netbox._request('POST', 'dcim/sites/', json={
                'name': site_code.upper(),
                'slug': slug,
                'status': 'active'
            })
            site_id = result['id']
            self.sites_cache[site_upper] = site_id
            print(f"    Created site: {site_code}")
            return site_id
        except Exception as e:
            print(f"    Failed to create site {site_code}: {e}")
            return None
    
    def get_or_create_role(self, role_slug: str) -> Optional[int]:
        """Get role ID, creating if necessary."""
        if role_slug in self.roles_cache:
            return self.roles_cache[role_slug]
        
        if self.dry_run:
            print(f"    [DRY-RUN] Would create role: {role_slug}")
            return None
        
        # Create the role
        try:
            name = role_slug.replace('-', ' ').title()
            result = self.netbox._request('POST', 'dcim/device-roles/', json={
                'name': name,
                'slug': role_slug,
                'color': '9e9e9e'
            })
            role_id = result['id']
            self.roles_cache[role_slug] = role_id
            print(f"    Created role: {name}")
            return role_id
        except Exception as e:
            print(f"    Failed to create role {role_slug}: {e}")
            return None
    
    def get_or_create_generic_type(self) -> Optional[int]:
        """Get or create a Generic device type."""
        if 'generic' in self.types_cache:
            return self.types_cache['generic']
        
        if self.dry_run:
            print("    [DRY-RUN] Would create Generic device type")
            return None
        
        # First ensure Generic manufacturer exists
        try:
            mfr_result = self.netbox._request('GET', 'dcim/manufacturers/', params={'slug': 'generic'})
            if mfr_result.get('results'):
                mfr_id = mfr_result['results'][0]['id']
            else:
                mfr = self.netbox._request('POST', 'dcim/manufacturers/', json={
                    'name': 'Generic',
                    'slug': 'generic'
                })
                mfr_id = mfr['id']
                print("    Created Generic manufacturer")
            
            # Create Generic device type
            result = self.netbox._request('POST', 'dcim/device-types/', json={
                'manufacturer': mfr_id,
                'model': 'Generic',
                'slug': 'generic'
            })
            type_id = result['id']
            self.types_cache['generic'] = type_id
            print("    Created Generic device type")
            return type_id
        except Exception as e:
            print(f"    Failed to create Generic type: {e}")
            return None
    
    def get_or_create_device_type(self, manufacturer: str, model: str) -> Optional[int]:
        """Get or create a device type from SNMP-detected info."""
        # Generate slug
        slug = f"{model}".lower().replace(' ', '-').replace('_', '-')
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        slug = re.sub(r'-+', '-', slug).strip('-')
        
        if slug in self.types_cache:
            return self.types_cache[slug]
        
        if self.dry_run:
            print(f"    [DRY-RUN] Would create device type: {manufacturer} {model}")
            return None
        
        try:
            # Get or create manufacturer
            mfr_slug = manufacturer.lower().replace(' ', '-').replace('.', '')
            mfr_result = self.netbox._request('GET', 'dcim/manufacturers/', params={'slug': mfr_slug})
            if mfr_result.get('results'):
                mfr_id = mfr_result['results'][0]['id']
            else:
                mfr = self.netbox._request('POST', 'dcim/manufacturers/', json={
                    'name': manufacturer,
                    'slug': mfr_slug
                })
                mfr_id = mfr['id']
                print(f"    Created manufacturer: {manufacturer}")
            
            # Create device type
            result = self.netbox._request('POST', 'dcim/device-types/', json={
                'manufacturer': mfr_id,
                'model': model,
                'slug': slug
            })
            type_id = result['id']
            self.types_cache[slug] = type_id
            print(f"    Created device type: {manufacturer} {model}")
            return type_id
        except Exception as e:
            print(f"    Failed to create device type {manufacturer} {model}: {e}")
            return None
    
    def create_device(self, prtg_device: Dict, ip: str, site_id: int, role_id: int, type_id: int) -> bool:
        """Create a device in NetBox."""
        device_name = prtg_device.get('device', '')
        group = prtg_device.get('group', '')
        tags = prtg_device.get('tags', '')
        
        # Extract clean device name from patterns like "10.120.6.21 (CMF-SW01)" -> "CMF-SW01"
        name_match = re.search(r'\(([A-Z0-9\-]+)\)', device_name)
        if name_match:
            name = name_match.group(1)
        elif device_name and not device_name[0].isdigit():
            # Name doesn't start with digit, use as-is but clean it
            name = device_name.split('(')[0].strip()
        else:
            # Fallback to IP
            name = ip
        
        if self.dry_run:
            print(f"    [DRY-RUN] Would create: {name} ({ip})")
            return True
        
        try:
            # Prepare tags
            tag_list = ['prtg-import']
            if tags:
                for tag in tags.split(','):
                    tag = tag.strip().lower().replace(' ', '-')
                    tag = re.sub(r'[^a-z0-9\-]', '', tag)
                    tag = re.sub(r'-+', '-', tag).strip('-')
                    if tag and tag not in tag_list:
                        tag_list.append(tag)
            
            # Ensure tags exist
            for tag_slug in tag_list:
                try:
                    result = self.netbox._request('GET', 'extras/tags/', params={'slug': tag_slug})
                    if not result.get('results'):
                        self.netbox._request('POST', 'extras/tags/', json={
                            'name': tag_slug,
                            'slug': tag_slug,
                            'color': '2196f3'
                        })
                except:
                    pass
            
            # Create the device
            device_data = {
                'name': name,
                'device_type': type_id,
                'role': role_id,
                'site': site_id,
                'status': 'active',
                'comments': f"Imported from PRTG\nPRTG Group: {group}",
                'tags': [{'slug': t} for t in tag_list]
            }
            
            device = self.netbox._request('POST', 'dcim/devices/', json=device_data)
            device_id = device['id']
            
            # Create a management interface for the device
            interface_data = {
                'device': device_id,
                'name': 'mgmt0',
                'type': 'other'
            }
            interface = self.netbox._request('POST', 'dcim/interfaces/', json=interface_data)
            interface_id = interface['id']
            
            # Create and assign IP address to the interface
            ip_data = {
                'address': f"{ip}/32",
                'status': 'active',
                'assigned_object_type': 'dcim.interface',
                'assigned_object_id': interface_id
            }
            ip_obj = self.netbox._request('POST', 'ipam/ip-addresses/', json=ip_data)
            
            # Set as primary IP
            self.netbox._request('PATCH', f'dcim/devices/{device_id}/', json={
                'primary_ip4': ip_obj['id']
            })
            
            return True
        except Exception as e:
            print(f"    Failed to create {name}: {e}")
            return False
    
    def migrate(self):
        """Run the migration."""
        print("\n" + "="*60)
        print("PRTG to NetBox Migration")
        print("="*60)
        
        if self.dry_run:
            print("\n*** DRY RUN MODE - No changes will be made ***\n")
        
        # Load caches
        self.load_caches()
        
        # Get generic device type
        generic_type_id = self.get_or_create_generic_type()
        
        # Fetch PRTG devices
        print("\nFetching PRTG devices...")
        devices = self.prtg.get_devices()
        print(f"Found {len(devices)} devices in PRTG")
        
        # Process each device
        print("\nProcessing devices...")
        for i, device in enumerate(devices):
            self.stats['total'] += 1
            ip = device.get('host', '')
            name = device.get('device', ip)
            group = device.get('group', '')
            
            # If host is not a valid IP, try to extract from device name
            if not is_valid_ip(ip):
                extracted_ip = extract_ip_from_device_name(name)
                if extracted_ip and is_valid_ip(extracted_ip):
                    ip = extracted_ip
                else:
                    self.stats['skipped_invalid_ip'] += 1
                    continue
            
            # Skip if already exists
            if ip in self.existing_devices:
                self.stats['skipped_exists'] += 1
                continue
            
            # Extract site and role from group name
            site_code, role_slug = extract_site_and_role(group, name)
            
            if not site_code:
                self.stats['skipped_no_site'] += 1
                if self.dry_run:
                    print(f"  SKIP (no site): {name} | Group: {group}")
                continue
            
            # Try IP-based role detection as fallback/override
            ip_role = detect_role_from_ip(ip)
            if ip_role:
                role_slug = ip_role
            elif not role_slug:
                role_slug = 'edge-switch'
            
            # Get or create site
            site_id = self.get_or_create_site(site_code)
            if not site_id and not self.dry_run:
                self.stats['failed'] += 1
                continue
            
            # Get or create role
            role_id = self.get_or_create_role(role_slug)
            if not role_id and not self.dry_run:
                self.stats['failed'] += 1
                continue
            
            # Query SNMP for device type detection
            snmp_info = None
            detected_mfr = None
            detected_model = None
            snmp_status = ""
            
            if self.test_snmp:
                snmp_info = get_snmp_info(ip, self.snmp_community)
                if snmp_info:
                    self.stats['snmp_ok'] += 1
                    detected_mfr, detected_model = detect_device_type_from_snmp(snmp_info)
                    if detected_model:
                        self.stats['types_detected'] += 1
                        snmp_status = f"[SNMP: {detected_mfr} {detected_model}]"
                    else:
                        snmp_status = f"[SNMP OK, type unknown]"
                else:
                    self.stats['snmp_fail'] += 1
                    snmp_status = "[SNMP FAIL]"
            
            # Determine device type
            type_id = None
            if detected_mfr and detected_model:
                type_id = self.get_or_create_device_type(detected_mfr, detected_model)
            if not type_id:
                type_id = generic_type_id
            
            # Create device - pass the validated IP
            if self.dry_run:
                type_info = f"{detected_mfr} {detected_model}" if detected_model else "Generic"
                print(f"  [{i+1}/{len(devices)}] {name} -> Site: {site_code}, Role: {role_slug}, Type: {type_info} {snmp_status}")
                self.stats['created'] += 1
            else:
                if self.create_device(device, ip, site_id, role_id, type_id):
                    self.stats['created'] += 1
                    print(f"  [{i+1}/{len(devices)}] Created: {name} ({ip}) {snmp_status}")
                else:
                    self.stats['failed'] += 1
        
        # Print summary
        print("\n" + "="*60)
        print("Migration Summary")
        print("="*60)
        print(f"Total PRTG devices:     {self.stats['total']}")
        print(f"Skipped (invalid IP):   {self.stats['skipped_invalid_ip']}")
        print(f"Skipped (exists):       {self.stats['skipped_exists']}")
        print(f"Skipped (no site):      {self.stats['skipped_no_site']}")
        print(f"Created:                {self.stats['created']}")
        print(f"Failed:                 {self.stats['failed']}")
        if self.test_snmp:
            print(f"SNMP OK:                {self.stats['snmp_ok']}")
            print(f"SNMP Failed:            {self.stats['snmp_fail']}")
            print(f"Device types detected:  {self.stats['types_detected']}")
        print("="*60)


def main():
    parser = argparse.ArgumentParser(description='Migrate PRTG devices to NetBox')
    parser.add_argument('--dry-run', action='store_true', help='Preview only, no changes')
    parser.add_argument('--test-snmp', action='store_true', help='Test SNMP v2 on each device')
    parser.add_argument('--snmp-community', default='public', help='SNMP v2 community string')
    args = parser.parse_args()
    
    migrator = PRTGMigrator(
        dry_run=args.dry_run,
        test_snmp=args.test_snmp,
        snmp_community=args.snmp_community
    )
    migrator.migrate()


if __name__ == '__main__':
    main()
