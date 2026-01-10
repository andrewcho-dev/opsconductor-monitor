"""
NetBox Device Cache Service

Syncs device inventory from NetBox to local cache table for fast lookups
and to enable metrics correlation without constant API calls.
"""

import os
import logging
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class NetBoxCacheService:
    """Service to sync and manage NetBox device cache."""
    
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        self.netbox_url = os.environ.get('NETBOX_URL', 'http://192.168.10.51:8000')
        self.netbox_token = os.environ.get('NETBOX_TOKEN', '')
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for NetBox API requests."""
        return {
            'Authorization': f'Token {self.netbox_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def fetch_all_devices(self) -> List[Dict[str, Any]]:
        """Fetch all devices from NetBox API."""
        devices = []
        url = f"{self.netbox_url}/api/dcim/devices/"
        params = {'limit': 100, 'offset': 0}
        
        while True:
            try:
                response = requests.get(
                    url, 
                    headers=self._get_headers(), 
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                
                devices.extend(data.get('results', []))
                
                if not data.get('next'):
                    break
                    
                params['offset'] += params['limit']
                
            except requests.RequestException as e:
                logger.error(f"Error fetching devices from NetBox: {e}")
                break
                
        logger.info(f"Fetched {len(devices)} devices from NetBox")
        return devices
    
    def sync_devices_to_cache(self) -> Dict[str, int]:
        """Sync all NetBox devices to local cache table."""
        if not self.db_pool:
            raise ValueError("Database pool not configured")
            
        devices = self.fetch_all_devices()
        
        inserted = 0
        updated = 0
        errors = 0
        
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                for device in devices:
                    try:
                        # Extract device data
                        netbox_id = device.get('id')
                        name = device.get('name', '')
                        
                        # Get primary IP
                        primary_ip = None
                        if device.get('primary_ip'):
                            primary_ip = device['primary_ip'].get('address', '').split('/')[0]
                        
                        # Get device type
                        device_type = None
                        if device.get('device_type'):
                            device_type = device['device_type'].get('model', '')
                        
                        # Get manufacturer
                        manufacturer = None
                        if device.get('device_type', {}).get('manufacturer'):
                            manufacturer = device['device_type']['manufacturer'].get('name', '')
                        
                        # Get site info
                        site_id = None
                        site_name = None
                        if device.get('site'):
                            site_id = device['site'].get('id')
                            site_name = device['site'].get('name', '')
                        
                        # Get role
                        role_name = None
                        if device.get('role'):
                            role_name = device['role'].get('name', '')
                        
                        # Get platform
                        platform = None
                        if device.get('platform'):
                            platform = device['platform'].get('name', '')
                        
                        # Get status
                        status = device.get('status', {}).get('value', 'unknown')
                        
                        # Upsert into cache
                        cur.execute("""
                            INSERT INTO netbox_device_cache 
                            (netbox_device_id, device_ip, device_name, device_type, manufacturer,
                             site_id, site_name, role_name, cached_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                            ON CONFLICT (netbox_device_id) DO UPDATE SET
                                device_ip = EXCLUDED.device_ip,
                                device_name = EXCLUDED.device_name,
                                device_type = EXCLUDED.device_type,
                                manufacturer = EXCLUDED.manufacturer,
                                site_id = EXCLUDED.site_id,
                                site_name = EXCLUDED.site_name,
                                role_name = EXCLUDED.role_name,
                                cached_at = NOW()
                            RETURNING (xmax = 0) as inserted
                        """, (
                            netbox_id,
                            primary_ip,
                            name,
                            device_type,
                            manufacturer,
                            site_id,
                            site_name,
                            role_name
                        ))
                        
                        result = cur.fetchone()
                        if result and result[0]:
                            inserted += 1
                        else:
                            updated += 1
                            
                    except Exception as e:
                        logger.error(f"Error caching device {device.get('name')}: {e}")
                        errors += 1
                        
                conn.commit()
                
        finally:
            self.db_pool.putconn(conn)
            
        logger.info(f"NetBox cache sync complete: {inserted} inserted, {updated} updated, {errors} errors")
        return {
            'inserted': inserted,
            'updated': updated,
            'errors': errors,
            'total': len(devices)
        }
    
    def get_device_by_ip(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Get cached device info by IP address."""
        if not self.db_pool:
            return None
            
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT netbox_device_id, device_ip, device_name, device_type, manufacturer,
                           site_id, site_name, role_name, cached_at
                    FROM netbox_device_cache
                    WHERE device_ip = %s
                """, (ip_address,))
                
                row = cur.fetchone()
                if row:
                    return {
                        'netbox_device_id': row[0],
                        'device_ip': str(row[1]) if row[1] else None,
                        'device_name': row[2],
                        'device_type': row[3],
                        'manufacturer': row[4],
                        'site_id': row[5],
                        'site_name': row[6],
                        'role_name': row[7],
                        'cached_at': row[8].isoformat() if row[8] else None
                    }
                return None
        finally:
            self.db_pool.putconn(conn)
    
    def get_devices_by_site(self, site_name: str) -> List[Dict[str, Any]]:
        """Get all cached devices for a site."""
        if not self.db_pool:
            return []
            
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT netbox_device_id, device_ip, device_name, device_type, manufacturer,
                           site_id, site_name, role_name, cached_at
                    FROM netbox_device_cache
                    WHERE site_name = %s
                    ORDER BY device_name
                """, (site_name,))
                
                devices = []
                for row in cur.fetchall():
                    devices.append({
                        'netbox_device_id': row[0],
                        'device_ip': str(row[1]) if row[1] else None,
                        'device_name': row[2],
                        'device_type': row[3],
                        'manufacturer': row[4],
                        'site_id': row[5],
                        'site_name': row[6],
                        'role_name': row[7],
                        'cached_at': row[8].isoformat() if row[8] else None
                    })
                return devices
        finally:
            self.db_pool.putconn(conn)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the device cache."""
        if not self.db_pool:
            return {}
            
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_devices,
                        COUNT(DISTINCT site_name) as total_sites,
                        COUNT(DISTINCT role_name) as total_roles,
                        MIN(cached_at) as oldest_sync,
                        MAX(cached_at) as newest_sync
                    FROM netbox_device_cache
                """)
                
                row = cur.fetchone()
                return {
                    'total_devices': row[0],
                    'total_sites': row[1],
                    'total_roles': row[2],
                    'oldest_sync': row[3].isoformat() if row[3] else None,
                    'newest_sync': row[4].isoformat() if row[4] else None
                }
        finally:
            self.db_pool.putconn(conn)
