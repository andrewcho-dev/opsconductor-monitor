"""
Device Importer Service

Provides unified device import functionality from PRTG to:
- NetBox (external DCIM/IPAM)
- OpsConductor local database (scan_results table)

Supports preview, selective import, and batch operations.
"""

import logging
import ipaddress
from typing import Dict, List, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import os

from backend.database import DatabaseConnection
from backend.services.prtg_service import PRTGService
from backend.services.netbox_service import NetBoxService

logger = logging.getLogger(__name__)


class DeviceImporterService:
    """Service for importing devices from PRTG to NetBox and OpsConductor."""
    
    def __init__(self):
        self.prtg = PRTGService()
        self.netbox = NetBoxService()
        self.db = DatabaseConnection()
    
    # ========================================================================
    # PRTG Device Discovery
    # ========================================================================
    
    def discover_prtg_devices(self, group: str = None, status: str = None,
                               include_sensors: bool = False) -> Dict[str, Any]:
        """
        Discover all devices from PRTG.
        
        Args:
            group: Filter by PRTG group name
            status: Filter by status (up, down, warning, paused)
            include_sensors: Include sensor count per device
            
        Returns:
            Dictionary with discovered devices and metadata
        """
        try:
            devices = self.prtg.get_devices(group=group, status=status)
            
            # Enrich with sensor counts if requested
            if include_sensors:
                sensors = self.prtg.get_sensors()
                sensor_counts = {}
                for sensor in sensors:
                    parent_id = sensor.get('parentid')
                    if parent_id:
                        sensor_counts[parent_id] = sensor_counts.get(parent_id, 0) + 1
                
                for device in devices:
                    device['sensor_count'] = sensor_counts.get(device.get('objid'), 0)
            
            # Extract unique networks
            networks = set()
            for device in devices:
                host = device.get('host', '')
                if host:
                    try:
                        ip = ipaddress.ip_address(host)
                        # Get /24 network
                        if isinstance(ip, ipaddress.IPv4Address):
                            network = ipaddress.ip_network(f"{host}/24", strict=False)
                            networks.add(str(network))
                    except ValueError:
                        pass
            
            return {
                'success': True,
                'devices': devices,
                'count': len(devices),
                'networks': sorted(list(networks)),
                'groups': list(set(d.get('group', '') for d in devices if d.get('group'))),
            }
        except Exception as e:
            logger.error(f"Error discovering PRTG devices: {e}")
            return {
                'success': False,
                'error': str(e),
                'devices': [],
                'count': 0,
            }
    
    # ========================================================================
    # Import Preview
    # ========================================================================
    
    def preview_import(self, target: str = 'all') -> Dict[str, Any]:
        """
        Preview what would be imported without making changes.
        
        Args:
            target: 'netbox', 'opsconductor', or 'all'
            
        Returns:
            Preview of import operations
        """
        result = {
            'prtg_devices': [],
            'netbox_preview': None,
            'opsconductor_preview': None,
        }
        
        # Get PRTG devices
        prtg_result = self.discover_prtg_devices()
        if not prtg_result['success']:
            return {'success': False, 'error': prtg_result.get('error')}
        
        prtg_devices = prtg_result['devices']
        result['prtg_devices'] = prtg_devices
        result['prtg_count'] = len(prtg_devices)
        
        # Preview NetBox import
        if target in ('netbox', 'all'):
            result['netbox_preview'] = self._preview_netbox_import(prtg_devices)
        
        # Preview OpsConductor import
        if target in ('opsconductor', 'all'):
            result['opsconductor_preview'] = self._preview_opsconductor_import(prtg_devices)
        
        result['success'] = True
        return result
    
    def _preview_netbox_import(self, prtg_devices: List[Dict]) -> Dict[str, Any]:
        """Preview NetBox import."""
        try:
            if not self.netbox.is_configured:
                return {'configured': False, 'error': 'NetBox not configured'}
            
            # Get existing NetBox devices
            netbox_result = self.netbox.get_devices(limit=1000)
            netbox_devices = netbox_result.get('results', [])
            
            # Build lookup sets
            netbox_ips = set()
            netbox_names = set()
            for d in netbox_devices:
                if d.get('primary_ip4'):
                    ip = d['primary_ip4'].get('address', '').split('/')[0]
                    if ip:
                        netbox_ips.add(ip)
                if d.get('name'):
                    netbox_names.add(d['name'].lower())
            
            # Categorize PRTG devices
            to_create = []
            existing = []
            
            for device in prtg_devices:
                host = device.get('host', '')
                name = device.get('device', '')
                
                if host in netbox_ips or name.lower() in netbox_names:
                    existing.append({
                        'prtg_id': device.get('objid'),
                        'name': name,
                        'host': host,
                        'group': device.get('group'),
                        'status': 'exists',
                    })
                else:
                    to_create.append({
                        'prtg_id': device.get('objid'),
                        'name': name,
                        'host': host,
                        'group': device.get('group'),
                        'type': device.get('type'),
                        'status': 'new',
                    })
            
            return {
                'configured': True,
                'existing_count': len(existing),
                'new_count': len(to_create),
                'existing': existing,
                'to_create': to_create,
            }
        except Exception as e:
            logger.error(f"Error previewing NetBox import: {e}")
            return {'configured': True, 'error': str(e)}
    
    def _preview_opsconductor_import(self, prtg_devices: List[Dict]) -> Dict[str, Any]:
        """Preview OpsConductor import."""
        try:
            # Get existing OpsConductor devices
            with self.db.cursor() as cur:
                cur.execute("SELECT ip_address::text as ip_address, snmp_hostname FROM scan_results")
                existing = cur.fetchall()
            
            existing_ips = {r['ip_address'] for r in existing}
            existing_names = {r['snmp_hostname'].lower() for r in existing if r['snmp_hostname']}
            
            # Categorize PRTG devices
            to_create = []
            to_update = []
            
            for device in prtg_devices:
                host = device.get('host', '')
                name = device.get('device', '')
                
                if host in existing_ips:
                    to_update.append({
                        'prtg_id': device.get('objid'),
                        'name': name,
                        'host': host,
                        'group': device.get('group'),
                        'status': 'update',
                    })
                else:
                    to_create.append({
                        'prtg_id': device.get('objid'),
                        'name': name,
                        'host': host,
                        'group': device.get('group'),
                        'type': device.get('type'),
                        'status': 'new',
                    })
            
            return {
                'existing_count': len(to_update),
                'new_count': len(to_create),
                'to_update': to_update,
                'to_create': to_create,
            }
        except Exception as e:
            logger.error(f"Error previewing OpsConductor import: {e}")
            return {'error': str(e)}
    
    # ========================================================================
    # Import Operations
    # ========================================================================
    
    def import_to_opsconductor(self, device_ids: List[int] = None,
                                update_existing: bool = True,
                                create_missing: bool = True,
                                dry_run: bool = False) -> Dict[str, Any]:
        """
        Import PRTG devices to OpsConductor local database.
        
        Args:
            device_ids: Specific PRTG device IDs to import (None = all)
            update_existing: Update devices that already exist
            create_missing: Create devices that don't exist
            dry_run: Preview only, don't make changes
            
        Returns:
            Import results
        """
        results = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': [],
            'details': [],
        }
        
        try:
            # Get PRTG devices
            prtg_devices = self.prtg.get_devices()
            if device_ids:
                prtg_devices = [d for d in prtg_devices if d.get('objid') in device_ids]
            
            # Get existing devices
            with self.db.cursor() as cur:
                cur.execute("SELECT ip_address::text as ip_address FROM scan_results")
                existing_ips = {r['ip_address'] for r in cur.fetchall()}
            
            for device in prtg_devices:
                results['processed'] += 1
                host = device.get('host', '')
                name = device.get('device', '')
                
                if not host:
                    results['skipped'] += 1
                    results['details'].append({
                        'name': name,
                        'action': 'skipped',
                        'reason': 'no_ip_address',
                    })
                    continue
                
                # Validate IP
                try:
                    ipaddress.ip_address(host)
                except ValueError:
                    results['skipped'] += 1
                    results['details'].append({
                        'name': name,
                        'host': host,
                        'action': 'skipped',
                        'reason': 'invalid_ip',
                    })
                    continue
                
                if host in existing_ips:
                    if update_existing and not dry_run:
                        self._update_device(host, device)
                        results['updated'] += 1
                        results['details'].append({
                            'name': name,
                            'host': host,
                            'action': 'updated',
                        })
                    else:
                        results['skipped'] += 1
                        results['details'].append({
                            'name': name,
                            'host': host,
                            'action': 'skipped' if not update_existing else 'would_update',
                        })
                elif create_missing:
                    if not dry_run:
                        self._create_device(host, device)
                        results['created'] += 1
                        results['details'].append({
                            'name': name,
                            'host': host,
                            'action': 'created',
                        })
                    else:
                        results['created'] += 1
                        results['details'].append({
                            'name': name,
                            'host': host,
                            'action': 'would_create',
                        })
                else:
                    results['skipped'] += 1
            
            results['success'] = True
            
        except Exception as e:
            logger.error(f"Error importing to OpsConductor: {e}")
            results['success'] = False
            results['error'] = str(e)
        
        return results
    
    def _create_device(self, ip: str, prtg_device: Dict) -> None:
        """Create a device in OpsConductor database."""
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO scan_results (
                    ip_address, snmp_hostname, snmp_description, snmp_vendor_name,
                    ping_status, scan_timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (ip_address) DO UPDATE SET
                    snmp_hostname = EXCLUDED.snmp_hostname,
                    snmp_description = EXCLUDED.snmp_description,
                    snmp_vendor_name = EXCLUDED.snmp_vendor_name,
                    ping_status = EXCLUDED.ping_status,
                    scan_timestamp = EXCLUDED.scan_timestamp
            """, (
                ip,
                prtg_device.get('device', ''),
                f"PRTG Group: {prtg_device.get('group', '')} | Tags: {prtg_device.get('tags', '')}",
                prtg_device.get('type', 'unknown'),
                'up' if prtg_device.get('status_raw') == 3 else 'down',
                datetime.utcnow(),
            ))
        self.db.commit()
    
    def _update_device(self, ip: str, prtg_device: Dict) -> None:
        """Update a device in OpsConductor database."""
        with self.db.cursor() as cur:
            cur.execute("""
                UPDATE scan_results SET
                    snmp_hostname = COALESCE(snmp_hostname, %s),
                    snmp_description = COALESCE(snmp_description, '') || %s,
                    ping_status = %s,
                    scan_timestamp = %s
                WHERE ip_address = %s
            """, (
                prtg_device.get('device', ''),
                f" | PRTG: {prtg_device.get('group', '')}",
                'up' if prtg_device.get('status_raw') == 3 else 'down',
                datetime.utcnow(),
                ip,
            ))
        self.db.commit()
    
    def import_to_netbox(self, device_ids: List[int] = None,
                          default_site_id: int = None,
                          default_role_id: int = None,
                          default_device_type_id: int = None,
                          update_existing: bool = False,
                          create_missing: bool = True,
                          dry_run: bool = False) -> Dict[str, Any]:
        """
        Import PRTG devices to NetBox.
        
        Args:
            device_ids: Specific PRTG device IDs to import (None = all)
            default_site_id: Default NetBox site ID for new devices
            default_role_id: Default NetBox device role ID
            default_device_type_id: Default NetBox device type ID
            update_existing: Update devices that already exist
            create_missing: Create devices that don't exist
            dry_run: Preview only, don't make changes
            
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
            # Get PRTG devices
            prtg_devices = self.prtg.get_devices()
            if device_ids:
                prtg_devices = [d for d in prtg_devices if d.get('objid') in device_ids]
            
            # Get existing NetBox devices
            netbox_result = self.netbox.get_devices(limit=1000)
            netbox_devices = netbox_result.get('results', [])
            
            # Build lookup
            netbox_by_ip = {}
            netbox_by_name = {}
            for d in netbox_devices:
                if d.get('primary_ip4'):
                    ip = d['primary_ip4'].get('address', '').split('/')[0]
                    if ip:
                        netbox_by_ip[ip] = d
                if d.get('name'):
                    netbox_by_name[d['name'].lower()] = d
            
            def process_device(device):
                detail = {'processed': 1, 'created': 0, 'updated': 0, 'skipped': 0, 'error': None}
                
                host = device.get('host', '')
                name = device.get('device', '')
                
                if not host or not name:
                    detail['skipped'] = 1
                    detail['detail'] = {'name': name, 'host': host, 'action': 'skipped', 'reason': 'missing_data'}
                    return detail
                
                existing = netbox_by_ip.get(host) or netbox_by_name.get(name.lower())
                
                try:
                    if existing:
                        if update_existing and not dry_run:
                            self.netbox.update_device(existing['id'], 
                                comments=f"Synced from PRTG. Group: {device.get('group')}"
                            )
                            detail['updated'] = 1
                            detail['detail'] = {'name': name, 'host': host, 'action': 'updated', 'netbox_id': existing['id']}
                        else:
                            detail['skipped'] = 1
                            detail['detail'] = {'name': name, 'host': host, 'action': 'skipped', 'reason': 'exists'}
                    elif create_missing:
                        if not dry_run:
                            # Create device in NetBox
                            new_device = self.netbox.create_device(
                                name=name,
                                device_type_id=default_device_type_id or 1,
                                role_id=default_role_id or 1,
                                site_id=default_site_id or 1,
                                status='active',
                                comments=f"Imported from PRTG. Group: {device.get('group')}, Tags: {device.get('tags')}",
                            )
                            
                            # Create IP address and assign to device
                            if host:
                                try:
                                    self.netbox.create_ip_address(
                                        address=f"{host}/32",
                                        status='active',
                                        description=f"Primary IP for {name}",
                                    )
                                except Exception:
                                    pass  # IP might already exist
                            
                            detail['created'] = 1
                            detail['detail'] = {'name': name, 'host': host, 'action': 'created', 'netbox_id': new_device.get('id')}
                        else:
                            detail['created'] = 1
                            detail['detail'] = {'name': name, 'host': host, 'action': 'would_create'}
                    else:
                        detail['skipped'] = 1
                        detail['detail'] = {'name': name, 'host': host, 'action': 'skipped', 'reason': 'create_disabled'}
                        
                except Exception as e:
                    detail['error'] = {'name': name, 'host': host, 'error': str(e)}
                
                return detail
            
            # Process devices in parallel
            max_workers = min(os.cpu_count() * 2 or 4, len(prtg_devices), 20)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                process_results = list(executor.map(process_device, prtg_devices))
            
            for detail in process_results:
                results['processed'] += detail['processed']
                results['created'] += detail['created']
                results['updated'] += detail['updated']
                results['skipped'] += detail['skipped']
                if detail.get('detail'):
                    results['details'].append(detail['detail'])
                if detail.get('error'):
                    results['errors'].append(detail['error'])
            
            results['success'] = True
            
        except Exception as e:
            logger.error(f"Error importing to NetBox: {e}")
            results['success'] = False
            results['error'] = str(e)
        
        return results
    
    def import_to_all(self, device_ids: List[int] = None,
                       netbox_site_id: int = None,
                       netbox_role_id: int = None,
                       netbox_device_type_id: int = None,
                       update_existing: bool = False,
                       dry_run: bool = False) -> Dict[str, Any]:
        """
        Import PRTG devices to both NetBox and OpsConductor.
        
        Args:
            device_ids: Specific PRTG device IDs to import
            netbox_site_id: Default NetBox site ID
            netbox_role_id: Default NetBox role ID
            netbox_device_type_id: Default NetBox device type ID
            update_existing: Update existing devices
            dry_run: Preview only
            
        Returns:
            Combined import results
        """
        results = {
            'opsconductor': None,
            'netbox': None,
        }
        
        # Import to OpsConductor
        results['opsconductor'] = self.import_to_opsconductor(
            device_ids=device_ids,
            update_existing=update_existing,
            dry_run=dry_run,
        )
        
        # Import to NetBox if configured
        if self.netbox.is_configured:
            results['netbox'] = self.import_to_netbox(
                device_ids=device_ids,
                default_site_id=netbox_site_id,
                default_role_id=netbox_role_id,
                default_device_type_id=netbox_device_type_id,
                update_existing=update_existing,
                dry_run=dry_run,
            )
        else:
            results['netbox'] = {'success': False, 'error': 'NetBox not configured'}
        
        results['success'] = results['opsconductor'].get('success', False)
        return results
    
    # ========================================================================
    # Network Discovery
    # ========================================================================
    
    def get_discovered_networks(self) -> Dict[str, Any]:
        """
        Get networks discovered from PRTG devices.
        
        Returns:
            List of networks with device counts
        """
        try:
            devices = self.prtg.get_devices()
            
            networks = {}
            for device in devices:
                host = device.get('host', '')
                if host:
                    try:
                        ip = ipaddress.ip_address(host)
                        if isinstance(ip, ipaddress.IPv4Address):
                            network = str(ipaddress.ip_network(f"{host}/24", strict=False))
                            if network not in networks:
                                networks[network] = {
                                    'network': network,
                                    'devices': [],
                                    'count': 0,
                                }
                            networks[network]['devices'].append({
                                'ip': host,
                                'name': device.get('device'),
                                'prtg_id': device.get('objid'),
                            })
                            networks[network]['count'] += 1
                    except ValueError:
                        pass
            
            return {
                'success': True,
                'networks': sorted(networks.values(), key=lambda x: x['count'], reverse=True),
                'total_networks': len(networks),
            }
        except Exception as e:
            logger.error(f"Error getting discovered networks: {e}")
            return {'success': False, 'error': str(e)}
