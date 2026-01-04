#!/usr/bin/env python3
"""
Populate MAC addresses for Ciena switch interfaces in NetBox.

Ciena switches expose MAC addresses via SNMP ifPhysAddress (1.3.6.1.2.1.2.2.1.6).
Interface indices 10001-10024 correspond to physical ports 1-24.

This script:
1. Queries each Ciena switch via SNMP for interface MAC addresses
2. Updates the corresponding interfaces in NetBox with the MAC addresses
"""

import requests
import psycopg2
from pysnmp.hlapi import *
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

def get_mac_addresses_via_snmp(ip, community='public'):
    """Query a switch for interface MAC addresses via SNMP."""
    mac_addresses = {}
    
    for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
        SnmpEngine(),
        CommunityData(community, mpModel=1),  # SNMPv2c
        UdpTransportTarget((ip, 161), timeout=10, retries=2),
        ContextData(),
        ObjectType(ObjectIdentity('1.3.6.1.2.1.2.2.1.6')),  # ifPhysAddress
        lexicographicMode=False
    ):
        if errorIndication or errorStatus:
            break
        
        for varBind in varBinds:
            oid = str(varBind[0])
            value = varBind[1]
            if_index = int(oid.split('.')[-1])
            
            # Convert to port number
            # Ciena uses 10001-10024 for ports 1-24
            if 10001 <= if_index <= 10024:
                port_num = if_index - 10000
            elif 1 <= if_index <= 24:
                port_num = if_index
            else:
                continue
            
            # Convert MAC to readable format
            if value and hasattr(value, 'prettyPrint'):
                mac_bytes = bytes(value)
                if len(mac_bytes) == 6 and any(b != 0 for b in mac_bytes):
                    mac_str = ':'.join(f'{b:02X}' for b in mac_bytes)
                    mac_addresses[str(port_num)] = mac_str
    
    return mac_addresses

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
    errors = []
    
    # Get all Ciena devices
    r = requests.get(f'{url}/api/dcim/devices/?manufacturer=ciena&limit=200', headers=headers)
    r.raise_for_status()
    devices = r.json().get('results', [])
    
    print(f"Processing {len(devices)} Ciena devices")
    print("=" * 60)
    
    for device in sorted(devices, key=lambda x: x['name']):
        device_id = device['id']
        device_name = device['name']
        
        # Get device IP
        primary_ip = device.get('primary_ip4')
        if not primary_ip:
            print(f"- {device_name}: No primary IP, skipping")
            continue
        
        ip = primary_ip['address'].split('/')[0]
        
        print(f"\n### {device_name} ({ip}) ###")
        
        # Get MAC addresses via SNMP
        try:
            mac_addresses = get_mac_addresses_via_snmp(ip)
            if not mac_addresses:
                print(f"  No MAC addresses retrieved via SNMP")
                continue
            print(f"  Retrieved {len(mac_addresses)} MAC addresses via SNMP")
        except Exception as e:
            print(f"  SNMP error: {e}")
            errors.append(f"{device_name}: SNMP error - {e}")
            continue
        
        # Get interfaces for this device
        r = requests.get(f'{url}/api/dcim/interfaces/?device_id={device_id}&limit=50', headers=headers)
        interfaces = {iface['name']: iface for iface in r.json().get('results', [])}
        
        # Update each interface with its MAC address
        updated = 0
        for port_num, mac in mac_addresses.items():
            if port_num not in interfaces:
                continue
            
            iface = interfaces[port_num]
            iface_id = iface['id']
            current_mac = iface.get('mac_address')
            
            # Skip if already set correctly
            if current_mac and current_mac.upper() == mac.upper():
                continue
            
            # Update interface MAC address
            update_data = {'mac_address': mac}
            r = requests.patch(
                f'{url}/api/dcim/interfaces/{iface_id}/',
                headers=headers,
                json=update_data
            )
            
            if r.status_code == 200:
                change = f"{device_name} port {port_num}: {mac}"
                print(f"  ✓ Port {port_num}: {mac}")
                changes_made.append(change)
                updated += 1
            else:
                print(f"  ✗ Port {port_num}: Failed - {r.status_code}")
        
        if updated == 0:
            print(f"  No updates needed (MACs already set or no matching interfaces)")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"SUMMARY: Updated {len(changes_made)} interface MAC addresses")
    if errors:
        print(f"ERRORS: {len(errors)} devices had SNMP errors")
        for err in errors:
            print(f"  - {err}")
    print("=" * 60)
    
    return changes_made

if __name__ == '__main__':
    main()
