#!/usr/bin/env python3
"""
Fix NetBox module installations for Ciena 5160 and 3942 devices.

This script:
1. Creates missing module types for SFP models
2. Creates modules for each SFP inventory item
3. Installs modules in the correct module bays
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

def get_or_create_module_type(url, headers, part_id, manufacturer_id=3):
    """Get or create a module type for the given part ID."""
    # Check if module type exists
    r = requests.get(f'{url}/api/dcim/module-types/?model={part_id}', headers=headers)
    results = r.json().get('results', [])
    if results:
        return results[0]['id']
    
    # Create new module type
    data = {
        'manufacturer': manufacturer_id,  # FS.com or generic
        'model': part_id,
        'description': f'Auto-created SFP module type for {part_id}'
    }
    r = requests.post(f'{url}/api/dcim/module-types/', headers=headers, json=data)
    if r.status_code == 201:
        new_id = r.json()['id']
        print(f"  Created module type: {part_id} (ID: {new_id})")
        return new_id
    else:
        print(f"  Failed to create module type {part_id}: {r.status_code} - {r.text}")
        return None

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
    
    # Get FS.com manufacturer ID (or create generic one)
    r = requests.get(f'{url}/api/dcim/manufacturers/?name=FS.com', headers=headers)
    manufacturers = r.json().get('results', [])
    if manufacturers:
        manufacturer_id = manufacturers[0]['id']
    else:
        # Try generic
        r = requests.get(f'{url}/api/dcim/manufacturers/?slug=generic', headers=headers)
        manufacturers = r.json().get('results', [])
        if manufacturers:
            manufacturer_id = manufacturers[0]['id']
        else:
            # Create generic manufacturer
            r = requests.post(f'{url}/api/dcim/manufacturers/', headers=headers, 
                            json={'name': 'Generic', 'slug': 'generic'})
            manufacturer_id = r.json()['id']
    
    print(f"Using manufacturer ID: {manufacturer_id}")
    
    # Cache of module types
    module_type_cache = {}
    
    # Get all Ciena 5160 devices
    r = requests.get(f'{url}/api/dcim/devices/?device_type=5160&limit=100', headers=headers)
    devices_5160 = r.json().get('results', [])
    
    # Get all Ciena 3942 devices  
    r = requests.get(f'{url}/api/dcim/devices/?device_type=3942&limit=100', headers=headers)
    devices_3942 = r.json().get('results', [])
    
    all_devices = devices_5160 + devices_3942
    print(f"Processing {len(devices_5160)} 5160 devices and {len(devices_3942)} 3942 devices")
    print("=" * 60)
    
    for device in all_devices:
        device_id = device['id']
        device_name = device['name']
        device_type = device['device_type']['model']
        print(f"\n### {device_name} ({device_type}) ###")
        
        # Get module bays for this device
        r = requests.get(f'{url}/api/dcim/module-bays/?device_id={device_id}&limit=50', headers=headers)
        module_bays = r.json().get('results', [])
        
        # Build map: port number -> module bay
        # For 5160: SFP+1 -> port 1, SFP+24 -> port 24
        # For 3942: SFP+1 -> port 21, SFP+4 -> port 24
        module_bay_map = {}
        for mb in module_bays:
            bay_num_match = re.search(r'(\d+)', mb['name'])
            if bay_num_match:
                bay_num = int(bay_num_match.group(1))
                if device_type == '3942':
                    # 3942: SFP+1 = port 21, SFP+2 = port 22, etc.
                    port_num = 20 + bay_num
                else:
                    # 5160: SFP+1 = port 1, etc.
                    port_num = bay_num
                module_bay_map[str(port_num)] = mb
        
        # Get existing modules for this device
        r = requests.get(f'{url}/api/dcim/modules/?device_id={device_id}&limit=50', headers=headers)
        existing_modules = {m['module_bay']['id']: m for m in r.json().get('results', [])}
        
        # Get inventory items for this device
        r = requests.get(f'{url}/api/dcim/inventory-items/?device_id={device_id}&limit=100', headers=headers)
        inventory_items = r.json().get('results', [])
        
        sfp_count = 0
        installed_count = 0
        
        for item in inventory_items:
            item_name = item['name']
            
            # Skip non-SFP items
            if not item_name.upper().startswith('SFP'):
                continue
            
            sfp_count += 1
            
            # Extract port number
            match = re.search(r'SFP-?(\d+)', item_name, re.IGNORECASE)
            if not match:
                continue
            
            port_num = match.group(1)
            part_id = item.get('part_id') or 'Unknown-SFP'
            serial = item.get('serial') or ''
            
            # Find corresponding module bay
            if port_num not in module_bay_map:
                print(f"  WARNING: No module bay for port {port_num}")
                continue
            
            module_bay = module_bay_map[port_num]
            module_bay_id = module_bay['id']
            
            # Check if module already installed in this bay
            if module_bay_id in existing_modules:
                installed_count += 1
                continue
            
            # Get or create module type
            if part_id not in module_type_cache:
                module_type_id = get_or_create_module_type(url, headers, part_id, manufacturer_id)
                module_type_cache[part_id] = module_type_id
            else:
                module_type_id = module_type_cache[part_id]
            
            if not module_type_id:
                print(f"  Skipping {item_name}: no module type")
                continue
            
            # Create and install module
            module_data = {
                'device': device_id,
                'module_bay': module_bay_id,
                'module_type': module_type_id,
                'serial': serial,
                'description': f'Auto-installed from inventory item {item_name}'
            }
            
            r = requests.post(f'{url}/api/dcim/modules/', headers=headers, json=module_data)
            
            if r.status_code == 201:
                change = f"{device_name}: Installed {part_id} in {module_bay['name']} (port {port_num})"
                print(f"  ✓ {change}")
                changes_made.append(change)
                installed_count += 1
            else:
                print(f"  ✗ Failed to install module in {module_bay['name']}: {r.status_code} - {r.text[:200]}")
        
        print(f"  Summary: {sfp_count} SFPs, {installed_count} modules installed")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"SUMMARY: Made {len(changes_made)} module installations")
    print("=" * 60)
    for change in changes_made:
        print(f"  - {change}")
    
    return changes_made

if __name__ == '__main__':
    main()
