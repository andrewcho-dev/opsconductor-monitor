#!/usr/bin/env python3
"""
Script to sync NetBox devices to local cache.
Run this periodically (e.g., every 15 minutes) to keep cache fresh.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2.pool
from backend.services.netbox_cache_service import NetBoxCacheService


def main():
    # Create database pool
    db_pool = psycopg2.pool.SimpleConnectionPool(
        minconn=1,
        maxconn=5,
        host=os.environ.get('PG_HOST', 'localhost'),
        port=os.environ.get('PG_PORT', '5432'),
        database=os.environ.get('PG_DATABASE', 'network_scan'),
        user=os.environ.get('PG_USER', 'postgres'),
        password=os.environ.get('PG_PASSWORD', 'postgres')
    )
    
    # Get NetBox settings from database
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT key, value FROM system_settings WHERE key LIKE 'netbox_%'")
            settings = {row[0]: row[1] for row in cur.fetchall()}
    finally:
        db_pool.putconn(conn)
    
    netbox_url = settings.get('netbox_url', 'http://192.168.10.51:8000')
    netbox_token = settings.get('netbox_token', '')
    
    print(f"Using NetBox URL: {netbox_url}")
    
    # Set environment variables for the service
    os.environ['NETBOX_URL'] = netbox_url
    os.environ['NETBOX_TOKEN'] = netbox_token
    
    # Create service and sync
    service = NetBoxCacheService(db_pool=db_pool)
    
    print("Starting NetBox device cache sync...")
    result = service.sync_devices_to_cache()
    
    print(f"\nSync complete:")
    print(f"  Total devices fetched: {result['total']}")
    print(f"  Inserted: {result['inserted']}")
    print(f"  Updated: {result['updated']}")
    print(f"  Errors: {result['errors']}")
    
    # Show cache stats
    stats = service.get_cache_stats()
    print(f"\nCache statistics:")
    print(f"  Total devices in cache: {stats['total_devices']}")
    print(f"  Total sites: {stats['total_sites']}")
    print(f"  Total roles: {stats['total_roles']}")
    
    db_pool.closeall()


if __name__ == '__main__':
    main()
