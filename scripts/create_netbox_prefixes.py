#!/usr/bin/env python3
"""
Create Network Prefixes in NetBox

Creates /24 prefixes for each site based on the 3rd octet pattern:
- 10.120.X.0/24 and 10.121.X.0/24 where X corresponds to a site

This script analyzes existing devices in NetBox and creates the appropriate
prefixes for each site.

Usage:
    python scripts/create_netbox_prefixes.py --dry-run    # Preview only
    python scripts/create_netbox_prefixes.py              # Actually create
"""

import sys
import os
import argparse
from collections import defaultdict
from typing import Dict, Set

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.netbox_service import NetBoxService


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
            settings[row['key']] = row['value']
    
    return {
        'url': settings.get('netbox_url', ''),
        'token': settings.get('netbox_token', '')
    }


def main():
    parser = argparse.ArgumentParser(description='Create NetBox prefixes from device IPs')
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')
    args = parser.parse_args()
    
    # Get NetBox settings
    nb_settings = get_netbox_settings()
    if not nb_settings['url'] or not nb_settings['token']:
        print("Error: NetBox URL or token not configured in database")
        sys.exit(1)
    
    netbox = NetBoxService(nb_settings['url'], nb_settings['token'])
    
    print("=" * 60)
    print("NetBox Prefix Creator")
    print("=" * 60)
    
    # Get all devices with their IPs and sites
    print("\nFetching devices from NetBox...")
    devices = netbox._request('GET', 'dcim/devices/', params={'limit': 2000})
    
    # Get all sites
    print("Fetching sites from NetBox...")
    sites_response = netbox._request('GET', 'dcim/sites/', params={'limit': 500})
    sites_by_id = {s['id']: s for s in sites_response.get('results', [])}
    sites_by_slug = {s['slug']: s for s in sites_response.get('results', [])}
    
    # Get existing prefixes
    print("Fetching existing prefixes from NetBox...")
    existing_prefixes = netbox._request('GET', 'ipam/prefixes/', params={'limit': 1000})
    existing_prefix_set = {p['prefix'] for p in existing_prefixes.get('results', [])}
    print(f"  Found {len(existing_prefix_set)} existing prefixes")
    
    # Analyze device IPs to determine prefixes needed per site
    site_prefixes: Dict[int, Set[str]] = defaultdict(set)
    
    for device in devices.get('results', []):
        site_info = device.get('site')
        primary_ip = device.get('primary_ip4')
        
        if not site_info or not primary_ip:
            continue
        
        site_id = site_info['id']
        ip_address = primary_ip.get('address', '').split('/')[0]
        
        if not ip_address:
            continue
        
        # Parse IP and create /24 prefix
        parts = ip_address.split('.')
        if len(parts) == 4:
            prefix = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
            site_prefixes[site_id].add(prefix)
    
    # Create prefixes
    print(f"\nFound {sum(len(p) for p in site_prefixes.values())} unique prefixes across {len(site_prefixes)} sites")
    
    created = 0
    skipped = 0
    failed = 0
    
    for site_id, prefixes in sorted(site_prefixes.items()):
        site = sites_by_id.get(site_id, {})
        site_name = site.get('name', f'Site {site_id}')
        
        for prefix in sorted(prefixes):
            if prefix in existing_prefix_set:
                skipped += 1
                continue
            
            if args.dry_run:
                print(f"  [DRY-RUN] Would create prefix: {prefix} for site: {site_name}")
                created += 1
            else:
                try:
                    prefix_data = {
                        'prefix': prefix,
                        'site': site_id,
                        'status': 'active',
                        'description': f'Auto-created from PRTG migration for {site_name}'
                    }
                    netbox._request('POST', 'ipam/prefixes/', json=prefix_data)
                    print(f"  Created prefix: {prefix} for site: {site_name}")
                    created += 1
                    existing_prefix_set.add(prefix)
                except Exception as e:
                    print(f"  Failed to create {prefix}: {e}")
                    failed += 1
    
    print("\n" + "=" * 60)
    print("Prefix Creation Summary")
    print("=" * 60)
    print(f"Created:  {created}")
    print(f"Skipped:  {skipped} (already exist)")
    print(f"Failed:   {failed}")
    print("=" * 60)


if __name__ == '__main__':
    main()
