"""
PRTG to NetBox Device Importer Service

Imports devices from PRTG to NetBox with:
- IP address as the primary identifier
- Field mapping from PRTG to NetBox
- Selection filters (IP range, name, group, individual IPs)
- Site and device type assignment
"""

import logging
import ipaddress
import re
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import os

from backend.services.prtg_service import PRTGService
from backend.services.netbox_service import NetBoxService, NetBoxError

logger = logging.getLogger(__name__)


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


def get_configured_netbox_service():
    """Get NetBox service configured from database settings."""
    settings = get_netbox_settings()
    return NetBoxService(
        url=settings.get('url', ''),
        token=settings.get('token', ''),
        verify_ssl=settings.get('verify_ssl', 'true').lower() == 'true'
    )


# Field mapping documentation: PRTG field -> NetBox field
FIELD_MAPPING = {
    'host': 'primary_ip4',           # IP address (identifier)
    'device': 'name',                # Device name/hostname
    'group': 'comments',             # PRTG group -> NetBox comments
    'tags': 'tags',                  # PRTG tags -> NetBox tags
    'message': 'description',        # PRTG status message -> description
    'status_raw': 'status',          # PRTG status -> NetBox status (mapped)
    # These require user selection:
    # site_id -> site
    # device_type_id -> device_type
    # role_id -> role
}

# PRTG status to NetBox status mapping
STATUS_MAPPING = {
    3: 'active',      # Up
    4: 'active',      # Warning (still active)
    5: 'failed',      # Down
    7: 'offline',     # Paused by User
    8: 'offline',     # Paused by Dependency
    9: 'offline',     # Paused by Schedule
}


class PRTGNetBoxImporter:
    """Service for importing devices from PRTG to NetBox."""
    
    def __init__(self):
        self.prtg = PRTGService()
        self.netbox = get_configured_netbox_service()
    
    # ========================================================================
    # NetBox Lookups (for UI dropdowns)
    # ========================================================================
    
    def get_netbox_sites(self) -> List[Dict]:
        """Get all NetBox sites for selection."""
        try:
            result = self.netbox.get_sites(limit=1000)
            return [{'id': s['id'], 'name': s['name'], 'slug': s['slug']} 
                    for s in result.get('results', [])]
        except Exception as e:
            logger.error(f"Error fetching NetBox sites: {e}")
            return []
    
    def get_netbox_device_types(self) -> List[Dict]:
        """Get all NetBox device types for selection."""
        try:
            result = self.netbox.get_device_types(limit=1000)
            return [{'id': t['id'], 
                     'model': t['model'], 
                     'manufacturer': t.get('manufacturer', {}).get('name', ''),
                     'display': f"{t.get('manufacturer', {}).get('name', '')} {t['model']}"}
                    for t in result.get('results', [])]
        except Exception as e:
            logger.error(f"Error fetching NetBox device types: {e}")
            return []
    
    def get_netbox_device_roles(self) -> List[Dict]:
        """Get all NetBox device roles for selection."""
        try:
            result = self.netbox.get_device_roles(limit=1000)
            return [{'id': r['id'], 'name': r['name'], 'slug': r['slug']}
                    for r in result.get('results', [])]
        except Exception as e:
            logger.error(f"Error fetching NetBox device roles: {e}")
            return []
    
    def get_netbox_options(self) -> Dict[str, Any]:
        """Get all NetBox options for the import UI."""
        return {
            'sites': self.get_netbox_sites(),
            'device_types': self.get_netbox_device_types(),
            'device_roles': self.get_netbox_device_roles(),
            'field_mapping': FIELD_MAPPING,
            'status_mapping': STATUS_MAPPING,
        }
    
    # ========================================================================
    # PRTG Device Discovery with Filters
    # ========================================================================
    
    def get_prtg_devices(self, 
                         ip_range: str = None,
                         ip_addresses: List[str] = None,
                         name_filter: str = None,
                         group_filter: str = None,
                         status_filter: str = None) -> Dict[str, Any]:
        """
        Get PRTG devices with filtering options.
        
        Args:
            ip_range: CIDR range to filter (e.g., '10.120.0.0/16')
            ip_addresses: Specific IP addresses to include
            name_filter: Filter by device name (substring match)
            group_filter: Filter by PRTG group name (substring match)
            status_filter: Filter by status (up, down, warning, paused)
            
        Returns:
            Filtered device list with PRTG groups for reference
        """
        try:
            # Get all devices from PRTG
            all_devices = self.prtg.get_devices(status=status_filter)
            
            # Get existing NetBox IPs for comparison
            existing_netbox_ips = self._get_netbox_ips()
            
            # Build IP set for quick lookup if specific IPs provided
            ip_set = set(ip_addresses) if ip_addresses else None
            
            # Parse IP range if provided
            ip_network = None
            if ip_range:
                try:
                    ip_network = ipaddress.ip_network(ip_range, strict=False)
                except ValueError:
                    pass
            
            filtered = []
            groups = set()
            
            for device in all_devices:
                host = device.get('host', '').strip()
                name = device.get('device', '')
                group = device.get('group', '')
                
                # Skip devices without IP
                if not host:
                    continue
                
                # Validate IP address
                try:
                    ip = ipaddress.ip_address(host)
                except ValueError:
                    continue
                
                # Apply filters
                if ip_set and host not in ip_set:
                    continue
                
                if ip_network and ip not in ip_network:
                    continue
                
                if name_filter and name_filter.lower() not in name.lower():
                    continue
                
                if group_filter and group_filter.lower() not in group.lower():
                    continue
                
                groups.add(group)
                
                # Check if device already exists in NetBox
                in_netbox = host in existing_netbox_ips
                netbox_device_id = existing_netbox_ips.get(host, {}).get('device_id') if in_netbox else None
                
                # Add device with mapped fields preview
                filtered.append({
                    'prtg_id': device.get('objid'),
                    'ip_address': host,
                    'prtg_name': name,
                    'prtg_group': group,
                    'prtg_tags': device.get('tags', ''),
                    'prtg_status': device.get('status_text', 'Unknown'),
                    'prtg_status_raw': device.get('status_raw'),
                    'prtg_message': device.get('message_raw', ''),
                    'prtg_type': device.get('type', ''),
                    # Mapped NetBox fields (preview)
                    'netbox_name': self._sanitize_name(name),
                    'netbox_status': STATUS_MAPPING.get(device.get('status_raw'), 'active'),
                    # NetBox existence info
                    'in_netbox': in_netbox,
                    'netbox_device_id': netbox_device_id,
                })
            
            return {
                'success': True,
                'devices': filtered,
                'count': len(filtered),
                'groups': sorted(list(groups)),
            }
            
        except Exception as e:
            logger.error(f"Error getting PRTG devices: {e}")
            return {'success': False, 'error': str(e), 'devices': [], 'count': 0}
    
    def get_prtg_groups(self) -> List[str]:
        """Get all unique PRTG groups for filtering."""
        try:
            devices = self.prtg.get_devices()
            groups = set()
            for d in devices:
                if d.get('group'):
                    groups.add(d['group'])
            return sorted(list(groups))
        except Exception as e:
            logger.error(f"Error getting PRTG groups: {e}")
            return []
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize device name for NetBox (alphanumeric, hyphens, underscores)."""
        # Remove special characters, keep alphanumeric, hyphens, underscores, dots
        sanitized = re.sub(r'[^\w\-\.]', '-', name)
        # Remove consecutive hyphens
        sanitized = re.sub(r'-+', '-', sanitized)
        # Remove leading/trailing hyphens
        sanitized = sanitized.strip('-')
        # Limit length
        return sanitized[:64] if sanitized else 'unnamed-device'
    
    # ========================================================================
    # Import Preview
    # ========================================================================
    
    def preview_import(self, 
                       devices: List[Dict],
                       site_id: int,
                       device_type_id: int,
                       role_id: int) -> Dict[str, Any]:
        """
        Preview import without making changes.
        
        Args:
            devices: List of PRTG devices to import (from get_prtg_devices)
            site_id: NetBox site ID
            device_type_id: NetBox device type ID
            role_id: NetBox device role ID
            
        Returns:
            Preview showing what will be created/updated/skipped
        """
        try:
            # Get existing NetBox devices by IP
            existing_ips = self._get_netbox_ips()
            
            to_create = []
            to_update = []
            
            for device in devices:
                ip = device.get('ip_address')
                if not ip:
                    continue
                
                preview_item = {
                    'ip_address': ip,
                    'prtg_name': device.get('prtg_name'),
                    'prtg_group': device.get('prtg_group'),
                    'netbox_name': device.get('netbox_name'),
                    'netbox_status': device.get('netbox_status'),
                    'mapping': {
                        'PRTG host': f"{ip} → NetBox primary_ip4",
                        'PRTG device': f"{device.get('prtg_name')} → NetBox name: {device.get('netbox_name')}",
                        'PRTG group': f"{device.get('prtg_group')} → NetBox comments",
                        'PRTG tags': f"{device.get('prtg_tags')} → NetBox tags",
                        'PRTG status': f"{device.get('prtg_status')} → NetBox status: {device.get('netbox_status')}",
                    }
                }
                
                if ip in existing_ips:
                    preview_item['action'] = 'update'
                    preview_item['netbox_id'] = existing_ips[ip].get('device_id')
                    to_update.append(preview_item)
                else:
                    preview_item['action'] = 'create'
                    to_create.append(preview_item)
            
            return {
                'success': True,
                'to_create': to_create,
                'to_update': to_update,
                'create_count': len(to_create),
                'update_count': len(to_update),
                'site_id': site_id,
                'device_type_id': device_type_id,
                'role_id': role_id,
            }
            
        except Exception as e:
            logger.error(f"Error previewing import: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_netbox_ips(self) -> Dict[str, Dict]:
        """Get existing NetBox IPs mapped to device info."""
        try:
            result = self.netbox.get_ip_addresses(limit=10000)
            ip_map = {}
            for ip_record in result.get('results', []):
                address = ip_record.get('address', '').split('/')[0]
                if address:
                    ip_map[address] = {
                        'ip_id': ip_record.get('id'),
                        'device_id': ip_record.get('assigned_object', {}).get('device', {}).get('id') if ip_record.get('assigned_object') else None,
                    }
            return ip_map
        except Exception as e:
            logger.error(f"Error getting NetBox IPs: {e}")
            return {}
    
    # ========================================================================
    # Import Execution
    # ========================================================================
    
    def import_devices(self,
                       devices: List[Dict],
                       site_id: int,
                       device_type_id: int,
                       role_id: int,
                       update_existing: bool = False,
                       dry_run: bool = False) -> Dict[str, Any]:
        """
        Import PRTG devices to NetBox.
        
        Args:
            devices: List of PRTG devices to import
            site_id: NetBox site ID for all devices
            device_type_id: NetBox device type ID
            role_id: NetBox device role ID
            update_existing: Whether to update devices that already exist
            dry_run: If True, don't make changes
            
        Returns:
            Import results
        """
        if not self.netbox.is_configured:
            return {'success': False, 'error': 'NetBox not configured'}
        
        results = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': [],
            'details': [],
        }
        
        try:
            # Get existing NetBox data
            existing_ips = self._get_netbox_ips()
            existing_devices = self._get_netbox_devices_by_name()
            
            for device in devices:
                results['processed'] += 1
                ip = device.get('ip_address')
                name = device.get('netbox_name') or self._sanitize_name(device.get('prtg_name', ''))
                
                if not ip:
                    results['skipped'] += 1
                    results['details'].append({
                        'ip': None,
                        'name': device.get('prtg_name'),
                        'action': 'skipped',
                        'reason': 'no_ip_address',
                    })
                    continue
                
                try:
                    # Check if device exists by IP or name
                    existing_by_ip = existing_ips.get(ip)
                    existing_by_name = existing_devices.get(name.lower())
                    
                    if existing_by_ip or existing_by_name:
                        if update_existing:
                            if not dry_run:
                                device_id = existing_by_ip.get('device_id') if existing_by_ip else existing_by_name.get('id')
                                if device_id:
                                    self._update_netbox_device(device_id, device)
                            results['updated'] += 1
                            results['details'].append({
                                'ip': ip,
                                'name': name,
                                'action': 'updated' if not dry_run else 'would_update',
                            })
                        else:
                            results['skipped'] += 1
                            results['details'].append({
                                'ip': ip,
                                'name': name,
                                'action': 'skipped',
                                'reason': 'already_exists',
                            })
                    else:
                        if not dry_run:
                            self._create_netbox_device(
                                device, site_id, device_type_id, role_id
                            )
                        results['created'] += 1
                        results['details'].append({
                            'ip': ip,
                            'name': name,
                            'action': 'created' if not dry_run else 'would_create',
                        })
                        
                except Exception as e:
                    results['errors'].append({
                        'ip': ip,
                        'name': name,
                        'error': str(e),
                    })
            
            results['success'] = True
            
        except Exception as e:
            logger.error(f"Error importing devices: {e}")
            results['success'] = False
            results['error'] = str(e)
        
        return results
    
    def _get_netbox_devices_by_name(self) -> Dict[str, Dict]:
        """Get existing NetBox devices by name."""
        try:
            result = self.netbox.get_devices(limit=10000)
            return {d['name'].lower(): d for d in result.get('results', []) if d.get('name')}
        except Exception as e:
            logger.error(f"Error getting NetBox devices: {e}")
            return {}
    
    def _create_netbox_device(self, device: Dict, site_id: int, 
                               device_type_id: int, role_id: int) -> Dict:
        """Create a device in NetBox with IP address."""
        ip = device.get('ip_address')
        name = device.get('netbox_name') or self._sanitize_name(device.get('prtg_name', ''))
        status = device.get('netbox_status', 'active')
        
        # Build comments from PRTG group
        comments = f"Imported from PRTG\nPRTG Group: {device.get('prtg_group', '')}"
        if device.get('prtg_message'):
            comments += f"\nPRTG Status: {device.get('prtg_message')}"
        
        # Ensure prtg-import tag exists and get valid tag IDs
        valid_tags = self._ensure_tags_exist(device.get('prtg_tags', ''))
        
        # Create the device
        new_device = self.netbox.create_device(
            name=name,
            device_type_id=device_type_id,
            role_id=role_id,
            site_id=site_id,
            status=status,
            comments=comments,
            tags=valid_tags if valid_tags else None,
        )
        
        device_id = new_device.get('id')
        
        # Create management interface
        if device_id:
            try:
                interface = self.netbox.create_interface(
                    device_id=device_id,
                    name='mgmt0',
                    type='virtual',
                )
                interface_id = interface.get('id')
                
                # Create and assign IP address
                if interface_id:
                    ip_record = self.netbox.create_ip_address(
                        address=f"{ip}/32",
                        status='active',
                        description=f"Management IP for {name}",
                        assigned_object_type='dcim.interface',
                        assigned_object_id=interface_id,
                    )
                    
                    # Set as primary IP
                    if ip_record.get('id'):
                        self.netbox.update_device(device_id, primary_ip4=ip_record['id'])
                        
            except Exception as e:
                logger.warning(f"Error creating interface/IP for {name}: {e}")
        
        return new_device
    
    def _ensure_tags_exist(self, prtg_tags: str) -> List[str]:
        """
        Ensure tags exist in NetBox and return list of valid tag names.
        
        NetBox is authoritative for tags. PRTG tags are converted to NetBox
        standard format (lowercase, hyphenated slugs).
        
        The 'prtg-import' tag is always added to mark imported devices.
        """
        tag_names = ['prtg-import']  # Always include this marker tag
        
        # Convert PRTG tags to NetBox format (lowercase, hyphenated)
        if prtg_tags:
            for tag in prtg_tags.split(','):
                tag = tag.strip()
                if tag:
                    # Convert to NetBox slug format
                    slug = tag.lower().replace(' ', '-').replace('_', '-')
                    slug = re.sub(r'[^a-z0-9\-]', '', slug)
                    slug = re.sub(r'-+', '-', slug).strip('-')
                    if slug:
                        tag_names.append(slug)
        
        # Ensure each tag exists in NetBox
        valid_tags = []
        for tag_name in tag_names:
            try:
                # Check if tag exists
                result = self.netbox._request('GET', 'extras/tags/', params={'name': tag_name})
                if result.get('results'):
                    valid_tags.append(tag_name)
                else:
                    # Create the tag following NetBox conventions
                    try:
                        self.netbox._request('POST', 'extras/tags/', json={
                            'name': tag_name,
                            'slug': tag_name,
                            'color': '2196f3'  # Blue for imported tags
                        })
                        valid_tags.append(tag_name)
                    except Exception as e:
                        logger.warning(f"Could not create tag '{tag_name}': {e}")
            except Exception as e:
                logger.warning(f"Error checking tag '{tag_name}': {e}")
        
        return valid_tags
    
    def _update_netbox_device(self, device_id: int, device: Dict) -> Dict:
        """Update an existing NetBox device."""
        comments = f"Updated from PRTG\nPRTG Group: {device.get('prtg_group', '')}"
        
        return self.netbox.update_device(
            device_id,
            comments=comments,
            status=device.get('netbox_status', 'active'),
        )
