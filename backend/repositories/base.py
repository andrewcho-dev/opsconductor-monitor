"""
Base repository class providing common database operations.

All domain-specific repositories should inherit from this class.
"""

from typing import Any, Dict, List, Optional, Tuple
from ..utils.errors import DatabaseError, NotFoundError
from ..utils.serialization import serialize_row, serialize_rows


class BaseRepository:
    """
    Base repository providing common CRUD operations.
    
    Subclasses should define:
    - table_name: Name of the database table
    - primary_key: Name of the primary key column (default: 'id')
    - resource_name: Human-readable name for error messages
    """
    
    table_name: str = None
    primary_key: str = 'id'
    resource_name: str = 'Resource'
    
    def __init__(self, db_manager):
        """
        Initialize repository with database manager.
        
        Args:
            db_manager: DatabaseManager instance with execute_query method
        """
        self.db = db_manager
    
    def execute_query(self, query: str, params: tuple = None, fetch: bool = True) -> Any:
        """
        Execute a query with standard error handling.
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch: Whether to fetch results
        
        Returns:
            Query results if fetch=True, else None
        
        Raises:
            DatabaseError: If query fails
        """
        try:
            return self.db.execute_query(query, params, fetch=fetch)
        except Exception as e:
            raise DatabaseError(str(e), operation='query')
    
    def get_by_id(self, id: Any, serialize: bool = True) -> Optional[Dict]:
        """
        Get a single record by primary key.
        
        Args:
            id: Primary key value
            serialize: Whether to serialize the result
        
        Returns:
            Record as dictionary or None if not found
        """
        query = f"SELECT * FROM {self.table_name} WHERE {self.primary_key} = %s"
        results = self.execute_query(query, (id,))
        
        if not results:
            return None
        
        return serialize_row(results[0]) if serialize else results[0]
    
    def get_by_id_or_raise(self, id: Any, serialize: bool = True) -> Dict:
        """
        Get a single record by primary key, raising if not found.
        
        Args:
            id: Primary key value
            serialize: Whether to serialize the result
        
        Returns:
            Record as dictionary
        
        Raises:
            NotFoundError: If record not found
        """
        result = self.get_by_id(id, serialize)
        if result is None:
            raise NotFoundError(self.resource_name, str(id))
        return result
    
    def get_all(
        self, 
        filters: Dict[str, Any] = None,
        order_by: str = None,
        limit: int = None,
        offset: int = None,
        serialize: bool = True
    ) -> List[Dict]:
        """
        Get all records with optional filtering and pagination.
        
        Args:
            filters: Dictionary of column=value filters (AND logic)
            order_by: ORDER BY clause (e.g., 'created_at DESC')
            limit: Maximum number of records
            offset: Number of records to skip
            serialize: Whether to serialize results
        
        Returns:
            List of records as dictionaries
        """
        query = f"SELECT * FROM {self.table_name}"
        params = []
        
        # Add WHERE clause
        if filters:
            conditions = []
            for column, value in filters.items():
                if value is None:
                    conditions.append(f"{column} IS NULL")
                else:
                    conditions.append(f"{column} = %s")
                    params.append(value)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
        
        # Add ORDER BY
        if order_by:
            query += f" ORDER BY {order_by}"
        
        # Add LIMIT/OFFSET
        if limit:
            query += f" LIMIT {int(limit)}"
        if offset:
            query += f" OFFSET {int(offset)}"
        
        results = self.execute_query(query, tuple(params) if params else None)
        return serialize_rows(results) if serialize else results
    
    def count(self, filters: Dict[str, Any] = None) -> int:
        """
        Count records with optional filtering.
        
        Args:
            filters: Dictionary of column=value filters
        
        Returns:
            Number of matching records
        """
        query = f"SELECT COUNT(*) as count FROM {self.table_name}"
        params = []
        
        if filters:
            conditions = []
            for column, value in filters.items():
                if value is None:
                    conditions.append(f"{column} IS NULL")
                else:
                    conditions.append(f"{column} = %s")
                    params.append(value)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
        
        results = self.execute_query(query, tuple(params) if params else None)
        return results[0]['count'] if results else 0
    
    def exists(self, id: Any) -> bool:
        """
        Check if a record exists by primary key.
        
        Args:
            id: Primary key value
        
        Returns:
            True if record exists
        """
        query = f"SELECT 1 FROM {self.table_name} WHERE {self.primary_key} = %s LIMIT 1"
        results = self.execute_query(query, (id,))
        return bool(results)
    
    def create(self, data: Dict[str, Any], returning: bool = True) -> Optional[Dict]:
        """
        Create a new record.
        
        Args:
            data: Dictionary of column=value pairs
            returning: Whether to return the created record
        
        Returns:
            Created record if returning=True, else None
        """
        columns = list(data.keys())
        placeholders = ["%s"] * len(columns)
        values = [data[col] for col in columns]
        
        query = f"""
            INSERT INTO {self.table_name} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
        """
        
        if returning:
            query += " RETURNING *"
        
        results = self.execute_query(query, tuple(values), fetch=returning)
        
        if returning and results:
            return serialize_row(results[0])
        return None
    
    def update(self, id: Any, data: Dict[str, Any], returning: bool = True) -> Optional[Dict]:
        """
        Update an existing record.
        
        Args:
            id: Primary key value
            data: Dictionary of column=value pairs to update
            returning: Whether to return the updated record
        
        Returns:
            Updated record if returning=True, else None
        
        Raises:
            NotFoundError: If record not found
        """
        if not data:
            return self.get_by_id(id)
        
        set_clauses = [f"{col} = %s" for col in data.keys()]
        values = list(data.values()) + [id]
        
        query = f"""
            UPDATE {self.table_name}
            SET {', '.join(set_clauses)}
            WHERE {self.primary_key} = %s
        """
        
        if returning:
            query += " RETURNING *"
        
        results = self.execute_query(query, tuple(values), fetch=returning)
        
        if returning:
            if not results:
                raise NotFoundError(self.resource_name, str(id))
            return serialize_row(results[0])
        return None
    
    def upsert(
        self, 
        data: Dict[str, Any], 
        conflict_columns: List[str] = None,
        update_columns: List[str] = None,
        returning: bool = True
    ) -> Optional[Dict]:
        """
        Insert or update a record (upsert).
        
        Args:
            data: Dictionary of column=value pairs
            conflict_columns: Columns to check for conflict (default: primary key)
            update_columns: Columns to update on conflict (default: all except conflict columns)
            returning: Whether to return the record
        
        Returns:
            Upserted record if returning=True, else None
        """
        columns = list(data.keys())
        placeholders = ["%s"] * len(columns)
        values = [data[col] for col in columns]
        
        if conflict_columns is None:
            conflict_columns = [self.primary_key]
        
        if update_columns is None:
            update_columns = [c for c in columns if c not in conflict_columns]
        
        query = f"""
            INSERT INTO {self.table_name} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            ON CONFLICT ({', '.join(conflict_columns)})
        """
        
        if update_columns:
            set_clauses = [f"{col} = EXCLUDED.{col}" for col in update_columns]
            query += f" DO UPDATE SET {', '.join(set_clauses)}"
        else:
            query += " DO NOTHING"
        
        if returning:
            query += " RETURNING *"
        
        results = self.execute_query(query, tuple(values), fetch=returning)
        
        if returning and results:
            return serialize_row(results[0])
        return None
    
    def delete(self, id: Any) -> bool:
        """
        Delete a record by primary key.
        
        Args:
            id: Primary key value
        
        Returns:
            True if record was deleted, False if not found
        """
        query = f"DELETE FROM {self.table_name} WHERE {self.primary_key} = %s RETURNING {self.primary_key}"
        results = self.execute_query(query, (id,))
        return bool(results)
    
    def delete_or_raise(self, id: Any) -> None:
        """
        Delete a record by primary key, raising if not found.
        
        Args:
            id: Primary key value
        
        Raises:
            NotFoundError: If record not found
        """
        if not self.delete(id):
            raise NotFoundError(self.resource_name, str(id))
    
    def delete_many(self, filters: Dict[str, Any]) -> int:
        """
        Delete multiple records matching filters.
        
        Args:
            filters: Dictionary of column=value filters
        
        Returns:
            Number of deleted records
        """
        if not filters:
            raise ValueError("Filters required for delete_many to prevent accidental deletion")
        
        conditions = []
        params = []
        for column, value in filters.items():
            if value is None:
                conditions.append(f"{column} IS NULL")
            else:
                conditions.append(f"{column} = %s")
                params.append(value)
        
        query = f"DELETE FROM {self.table_name} WHERE {' AND '.join(conditions)} RETURNING {self.primary_key}"
        results = self.execute_query(query, tuple(params))
        return len(results) if results else 0
    
    def find_one(self, filters: Dict[str, Any], serialize: bool = True) -> Optional[Dict]:
        """
        Find a single record matching filters.
        
        Args:
            filters: Dictionary of column=value filters
            serialize: Whether to serialize the result
        
        Returns:
            First matching record or None
        """
        results = self.get_all(filters=filters, limit=1, serialize=serialize)
        return results[0] if results else None
    
    def find_by_column(
        self, 
        column: str, 
        value: Any, 
        serialize: bool = True
    ) -> List[Dict]:
        """
        Find all records where column equals value.
        
        Args:
            column: Column name
            value: Value to match
            serialize: Whether to serialize results
        
        Returns:
            List of matching records
        """
        return self.get_all(filters={column: value}, serialize=serialize)
