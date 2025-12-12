"""
Database connection management for backend.

Provides a centralized database connection that can be used by repositories.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager


class DatabaseConnection:
    """
    Database connection manager.
    
    Provides connection pooling and context management for database operations.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._connection = None
        
        # Load connection parameters from environment
        self.host = os.environ.get('PG_HOST', 'localhost')
        self.port = os.environ.get('PG_PORT', '5432')
        self.database = os.environ.get('PG_DATABASE', 'network_scan')
        self.user = os.environ.get('PG_USER', 'postgres')
        self.password = os.environ.get('PG_PASSWORD', 'postgres')
    
    def get_connection(self):
        """Get database connection, creating if needed."""
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                cursor_factory=RealDictCursor
            )
            self._connection.autocommit = True
        return self._connection
    
    @contextmanager
    def cursor(self):
        """Context manager for database cursor."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    
    def execute_query(self, query, params=None, fetch=True):
        """Execute a query and return results."""
        with self.cursor() as cursor:
            cursor.execute(query, params)
            if fetch and cursor.description:
                return cursor.fetchall()
            return None
    
    def execute_one(self, query, params=None):
        """Execute a query and return single result."""
        with self.cursor() as cursor:
            cursor.execute(query, params)
            if cursor.description:
                return cursor.fetchone()
            return None
    
    def close(self):
        """Close the database connection."""
        if self._connection and not self._connection.closed:
            self._connection.close()
            self._connection = None


# Singleton instance
db = DatabaseConnection()


def get_db():
    """Get the database connection singleton."""
    return db
