#!/usr/bin/env python3
"""
Fix NetBox module bay / interface / inventory item associations for Ciena 5160 devices.

The Ciena 5160 is an all-optical switch with 24 SFP+ ports. Each port should have:
1. An interface (port 1-24)
2. A module bay (SFP+1 to SFP+24)
3. If an SFP is installed: a module in the bay, linked to the interface
4. An inventory item representing the physical SFP, linked to the interface

This script:
1. Gets all Ciena 5160 devices
2. For each device, matches inventory items to interfaces by port number
3. Links inventory items to their corresponding interfaces
4. Reports all changes made
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
    
    # Get all Ciena 5160 devices
    r = requests.get(f'{url}/api/dcim/devices/?device_type=5160&limit=100', headers=headers)
    r.raise_for_status()
    devices = r.json().get('results', [])
    
    print(f"Found {len(devices)} Ciena 5160 devices")
    print("=" * 60)
    
    for device in devices:
        device_id = device['id']
        device_name = device['name']
        print(f"\n### {device_name} (ID: {device_id}) ###")
        
        # Get interfaces for this device
        r = requests.get(f'{url}/api/dcim/interfaces/?device_id={device_id}&limit=50', headers=headers)
        r.raise_for_status()
        interfaces = {iface['name']: iface for iface in r.json().get('results', [])}
        
        # Get module bays for this device
        r = requests.get(f'{url}/api/dcim/module-bays/?device_id={device_id}&limit=50', headers=headers)
        r.raise_for_status()
        module_bays = r.json().get('results', [])
        module_bay_map = {}
        for mb in module_bays:
            # Extract port number from name like "SFP+1" or "SFP+24"
            match = re.search(r'(\d+)', mb['name'])
            if match:
                port_num = match.group(1)
                module_bay_map[port_num] = mb
        
        # Get inventory items for this device
        r = requests.get(f'{url}/api/dcim/inventory-items/?device_id={device_id}&limit=100', headers=headers)
        r.raise_for_status()
        inventory_items = r.json().get('results', [])
        
        print(f"  Interfaces: {len(interfaces)}, Module Bays: {len(module_bays)}, Inventory Items: {len(inventory_items)}")
        
        # Process each inventory item that looks like an SFP
        for item in inventory_items:
            item_name = item['name']
            item_id = item['id']
            
            # Skip non-SFP items (CHASSIS, PDU, etc.)
            if not item_name.upper().startswith('SFP'):
                continue
            
            # Extract port number from name like "SFP-1" or "SFP-22"
            match = re.search(r'SFP-?(\d+)', item_name, re.IGNORECASE)
            if not match:
                print(f"  WARNING: Cannot parse port number from '{item_name}'")
                continue
            
            port_num = match.group(1)
            
            # Check if already linked
            if item.get('component_type') and item.get('component_id'):
                print(f"  {item_name}: Already linked to {item['component_type']}")
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
