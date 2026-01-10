#!/usr/bin/env python3
"""Clean up duplicate Axis alerts."""
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="network_scan",
    user="postgres",
    password="postgres"
)
cur = conn.cursor()

# Delete all axis alerts to start fresh
cur.execute("DELETE FROM alerts WHERE source_system = 'axis'")
deleted = cur.rowcount
conn.commit()
print(f"Deleted {deleted} Axis alerts")

cur.close()
conn.close()
