#!/usr/bin/env python3
"""One-time script to fix Axis connector password in database."""
import json
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="network_scan",
    user="postgres",
    password="postgres"
)
cur = conn.cursor()

# Get current config
cur.execute("SELECT id, config FROM connectors WHERE type = 'axis'")
row = cur.fetchone()
if row:
    connector_id, config = row
    if config is None:
        config = {}
    
    # Add default_username and default_password
    config['default_username'] = 'root'
    config['default_password'] = 'Metrolink202'
    
    # Update
    cur.execute(
        "UPDATE connectors SET config = %s WHERE id = %s",
        (json.dumps(config), connector_id)
    )
    conn.commit()
    print(f"Updated Axis connector {connector_id} with password")
else:
    print("No Axis connector found")

cur.close()
conn.close()
