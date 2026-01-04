#!/usr/bin/env python3
"""
Fix NetBox module bay / interface / inventory item associations for Ciena 3942 devices.

The Ciena 3942 has:
- Ports 1-20: RJ45 copper (no SFPs)
- Ports 21-24: SFP/SFP+ slots (4 module bays)

Module bays are named SFP+1 to SFP+4, corresponding to ports 21-24.
Inventory items are named SFP-21, SFP-22, etc.

This script links inventory items to their corresponding interfaces.
"""

import requests
import psycopg2
import re
import sys

def get_netbox_settings():
    """Get NetBox settings from database."""
    conn = psycopg2.connect(host='localhost', database='network_scan', user='postgres', password='postgres')
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM system_settings WHERE key LIKE 'netbox_%'")
    settings = {row[0].replace('netbox_', ''): row[1] for row in cur.fetchall()}
    cur.close()
    conn.close()
    return settings

def main():
    settings = get_netbox_settings()
    url = settings.get('url', '').rstrip('/')
    token = settings.get('token', '')
    
    if not url or not token:
        print("ERROR: NetBox URL or token not configured")
        sys.exit(1)
    
    headers = {
        'Authorization': f'Token {token}',
        'Content-Type': 'application/json'
    }
    
    changes_made = []
    
    # Get all Ciena 3942 devices
    r = requests.get(f'{url}/api/dcim/devices/?device_type=3942&limit=100', headers=headers)
    r.raise_for_status()
    devices = r.json().get('results', [])
    
    print(f"Found {len(devices)} Ciena 3942 devices")
    print("=" * 60)
    
    for device in devices:
        device_id = device['id']
        device_name = device['name']
        print(f"\n### {device_name} (ID: {device_id}) ###")
        
        # Get interfaces for this device
        r = requests.get(f'{url}/api/dcim/interfaces/?device_id={device_id}&limit=50', headers=headers)
        r.raise_for_status()
        interfaces = {iface['name']: iface for iface in r.json().get('results', [])}
        
        # Get inventory items for this device
        r = requests.get(f'{url}/api/dcim/inventory-items/?device_id={device_id}&limit=100', headers=headers)
        r.raise_for_status()
        inventory_items = r.json().get('results', [])
        
        sfp_items = [i for i in inventory_items if i['name'].upper().startswith('SFP')]
        print(f"  Interfaces: {len(interfaces)}, SFP Inventory Items: {len(sfp_items)}")
        
        # Process each SFP inventory item
        for item in inventory_items:
            item_name = item['name']
            item_id = item['id']
            
            # Skip non-SFP items
            if not item_name.upper().startswith('SFP'):
                continue
            
            # Extract port number from name like "SFP-21" or "SFP-24"
            match = re.search(r'SFP-?(\d+)', item_name, re.IGNORECASE)
            if not match:
                print(f"  WARNING: Cannot parse port number from '{item_name}'")
                continue
            
            port_num = match.group(1)
            
            # Check if already linked
            if item.get('component_type') and item.get('component_id'):
                print(f"  {item_name}: Already linked")
                continue
            
            # Find corresponding interface
            if port_num not in interfaces:
                print(f"  WARNING: No interface found for port {port_num} (item: {item_name})")
                continue
            
            interface = interfaces[port_num]
            interface_id = interface['id']
            
            # Link inventory item to interface
            update_data = {
                'component_type': 'dcim.interface',
                'component_id': interface_id
            }
            
            r = requests.patch(
                f'{url}/api/dcim/inventory-items/{item_id}/',
                headers=headers,
                json=update_data
            )
            
            if r.status_code == 200:
                change = f"{device_name}: Linked {item_name} -> Interface {port_num}"
                print(f"  ✓ {change}")
                changes_made.append(change)
            else:
                print(f"  ✗ Failed to link {item_name}: {r.status_code} - {r.text}")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"SUMMARY: Made {len(changes_made)} changes")
    print("=" * 60)
    for change in changes_made:
        print(f"  - {change}")
    
    return changes_made

if __name__ == '__main__':
    main()
