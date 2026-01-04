#!/usr/bin/env python3
"""
Fix NetBox IP address assignments for Ciena switches.

The management IP should be assigned to a management interface, not port 1.
This script:
1. Creates a "mgmt" interface on each Ciena device (if not exists)
2. Moves the IP address from interface "1" to "mgmt"
3. Sets the device's primary IP to the management interface IP
"""

import requests
import psycopg2
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
    
    # Get all Ciena devices
    r = requests.get(f'{url}/api/dcim/devices/?manufacturer=ciena&limit=200', headers=headers)
    r.raise_for_status()
    devices = r.json().get('results', [])
    
    print(f"Processing {len(devices)} Ciena devices")
    print("=" * 60)
    
    for device in sorted(devices, key=lambda x: x['name']):
        device_id = device['id']
        device_name = device['name']
        
        # Get IP addresses assigned to this device
        r = requests.get(f'{url}/api/ipam/ip-addresses/?device_id={device_id}&limit=50', headers=headers)
        ip_addresses = r.json().get('results', [])
        
        # Find IP assigned to interface "1"
        ip_on_port1 = None
        for ip in ip_addresses:
            assigned_obj = ip.get('assigned_object')
            if assigned_obj and assigned_obj.get('name') == '1':
                ip_on_port1 = ip
                break
        
        if not ip_on_port1:
            print(f"- {device_name}: No IP on port 1, skipping")
            continue
        
        ip_id = ip_on_port1['id']
        ip_address = ip_on_port1['address']
        
        # Get interfaces for this device
        r = requests.get(f'{url}/api/dcim/interfaces/?device_id={device_id}&limit=50', headers=headers)
        interfaces = {iface['name']: iface for iface in r.json().get('results', [])}
        
        # Check if mgmt interface exists, create if not
        if 'mgmt' not in interfaces:
            # Create management interface
            mgmt_data = {
                'device': device_id,
                'name': 'mgmt',
                'type': 'virtual',
                'description': 'Management interface'
            }
            r = requests.post(f'{url}/api/dcim/interfaces/', headers=headers, json=mgmt_data)
            if r.status_code == 201:
                mgmt_iface = r.json()
                print(f"  Created mgmt interface for {device_name}")
            else:
                print(f"  ✗ Failed to create mgmt interface for {device_name}: {r.status_code} - {r.text[:100]}")
                continue
        else:
            mgmt_iface = interfaces['mgmt']
        
        mgmt_iface_id = mgmt_iface['id']
        
        # Move IP from port 1 to mgmt interface
        update_data = {
            'assigned_object_type': 'dcim.interface',
            'assigned_object_id': mgmt_iface_id
        }
        
        r = requests.patch(f'{url}/api/ipam/ip-addresses/{ip_id}/', headers=headers, json=update_data)
        
        if r.status_code == 200:
            change = f"{device_name}: Moved {ip_address} from port 1 to mgmt"
            print(f"✓ {change}")
            changes_made.append(change)
            
            # Update device's primary IP
            device_update = {
                'primary_ip4': ip_id
            }
            r = requests.patch(f'{url}/api/dcim/devices/{device_id}/', headers=headers, json=device_update)
            if r.status_code == 200:
                print(f"  Set {ip_address} as primary IP for {device_name}")
            else:
                print(f"  Warning: Could not set primary IP: {r.status_code}")
        else:
            print(f"✗ Failed to move IP for {device_name}: {r.status_code} - {r.text[:100]}")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"SUMMARY: Made {len(changes_made)} IP reassignments")
    print("=" * 60)
    for change in changes_made:
        print(f"  - {change}")
    
    return changes_made

if __name__ == '__main__':
    main()
