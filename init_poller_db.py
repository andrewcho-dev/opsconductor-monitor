#!/usr/bin/env python3
"""Initialize poller database tables"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import db
from poller_database import PollerDatabase

def init_database():
    """Initialize the poller database tables"""
    print("=== Initializing Poller Database ===")
    
    try:
        # Create poller database extension
        poller_db = PollerDatabase(db)
        print("✅ Poller database tables created successfully")
        
        return True
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    init_database()
