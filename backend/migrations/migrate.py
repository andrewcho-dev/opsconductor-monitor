#!/usr/bin/env python3
"""
Database Migration Runner.

Applies SQL migrations in order based on version numbers.
"""

import os
import sys
import glob
import psycopg2
from psycopg2.extras import RealDictCursor

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def get_connection():
    """Get database connection from environment."""
    from dotenv import load_dotenv
    load_dotenv()
    
    return psycopg2.connect(
        host=os.environ.get('PG_HOST', 'localhost'),
        port=os.environ.get('PG_PORT', '5432'),
        database=os.environ.get('PG_DATABASE', 'network_scan'),
        user=os.environ.get('PG_USER', 'postgres'),
        password=os.environ.get('PG_PASSWORD', 'postgres'),
        cursor_factory=RealDictCursor
    )


def get_applied_versions(conn):
    """Get list of already applied migration versions."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT version FROM schema_versions ORDER BY version")
        return {row['version'] for row in cursor.fetchall()}
    except psycopg2.errors.UndefinedTable:
        # Table doesn't exist yet, no migrations applied
        return set()
    finally:
        cursor.close()


def get_migration_files():
    """Get list of migration SQL files in order."""
    migrations_dir = os.path.dirname(os.path.abspath(__file__))
    files = glob.glob(os.path.join(migrations_dir, '*.sql'))
    
    # Sort by version number (filename prefix)
    files.sort(key=lambda f: os.path.basename(f).split('_')[0])
    return files


def extract_version(filepath):
    """Extract version from migration filename."""
    filename = os.path.basename(filepath)
    return filename.split('_')[0]


def apply_migration(conn, filepath):
    """Apply a single migration file."""
    version = extract_version(filepath)
    filename = os.path.basename(filepath)
    
    print(f"Applying migration {filename}...")
    
    with open(filepath, 'r') as f:
        sql = f.read()
    
    # Reset any aborted transaction state
    conn.rollback()
    
    cursor = conn.cursor()
    try:
        # Execute each statement separately for better error handling
        statements = [s.strip() for s in sql.split(';') if s.strip()]
        for statement in statements:
            if statement:
                cursor.execute(statement)
        conn.commit()
        print(f"  ✓ Migration {version} applied successfully")
        return True
    except Exception as e:
        conn.rollback()
        print(f"  ✗ Migration {version} failed: {e}")
        return False
    finally:
        cursor.close()


def run_migrations():
    """Run all pending migrations."""
    print("OpsConductor Database Migration")
    print("=" * 40)
    
    try:
        conn = get_connection()
        print(f"Connected to database")
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return False
    
    try:
        applied = get_applied_versions(conn)
        print(f"Already applied: {len(applied)} migrations")
        
        migration_files = get_migration_files()
        print(f"Found: {len(migration_files)} migration files")
        print()
        
        pending = []
        for filepath in migration_files:
            version = extract_version(filepath)
            if version not in applied:
                pending.append(filepath)
        
        if not pending:
            print("No pending migrations.")
            return True
        
        print(f"Pending migrations: {len(pending)}")
        for filepath in pending:
            print(f"  - {os.path.basename(filepath)}")
        print()
        
        success = True
        for filepath in pending:
            if not apply_migration(conn, filepath):
                success = False
                break
        
        print()
        if success:
            print("All migrations completed successfully!")
        else:
            print("Migration failed. Please check errors above.")
        
        return success
        
    finally:
        conn.close()


def check_status():
    """Check migration status without applying."""
    print("OpsConductor Migration Status")
    print("=" * 40)
    
    try:
        conn = get_connection()
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return
    
    try:
        applied = get_applied_versions(conn)
        migration_files = get_migration_files()
        
        print(f"\nApplied migrations ({len(applied)}):")
        for version in sorted(applied):
            print(f"  ✓ {version}")
        
        pending = []
        for filepath in migration_files:
            version = extract_version(filepath)
            if version not in applied:
                pending.append(os.path.basename(filepath))
        
        print(f"\nPending migrations ({len(pending)}):")
        for filename in pending:
            print(f"  ○ {filename}")
        
        if not pending:
            print("  (none)")
            
    finally:
        conn.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='OpsConductor Database Migrations')
    parser.add_argument('--status', action='store_true', help='Check migration status')
    args = parser.parse_args()
    
    if args.status:
        check_status()
    else:
        success = run_migrations()
        sys.exit(0 if success else 1)
