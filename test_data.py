#!/usr/bin/env python3
import json

# Simple test to see if we can handle the data
try:
    from database import Database
    db = Database()
    
    print("Testing database connection...")
    devices = db.get_all_devices()
    print(f"Retrieved {len(devices)} devices")
    
    print("Testing JSON serialization...")
    json_data = json.dumps(devices)
    print(f"JSON serialized successfully, length: {len(json_data)}")
    
    print("Test completed successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
