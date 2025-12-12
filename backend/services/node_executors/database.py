"""
Database Node Executors

Executors for database operations.
"""

import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class DBQueryExecutor:
    """Executor for database query nodes."""
    
    def __init__(self, db_manager=None):
        self.db = db_manager
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """
        Execute a database query.
        
        Args:
            node: Node definition with parameters
            context: Execution context
        
        Returns:
            Query results
        """
        params = node.get('data', {}).get('parameters', {})
        table = params.get('table', '')
        query_type = params.get('query_type', 'select')
        columns = params.get('columns', '*')
        where_clause = params.get('where', '')
        limit = int(params.get('limit', 100))
        
        if not table:
            return {'error': 'No table specified', 'results': []}
        
        if not self.db:
            return {'error': 'Database not configured', 'results': []}
        
        try:
            # Build query
            query = f"SELECT {columns} FROM {table}"
            query_params = []
            
            if where_clause:
                query += f" WHERE {where_clause}"
            
            query += f" LIMIT {limit}"
            
            results = self.db.execute_query(query, tuple(query_params) if query_params else None)
            
            # Convert to list of dicts
            rows = [dict(row) for row in results] if results else []
            
            return {
                'table': table,
                'results': rows,
                'count': len(rows),
                'success': True,
            }
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            return {
                'table': table,
                'error': str(e),
                'results': [],
                'success': False,
            }


class DBUpsertExecutor:
    """Executor for database upsert (insert/update) nodes."""
    
    def __init__(self, db_manager=None):
        self.db = db_manager
    
    def execute(self, node: Dict, context: Dict) -> Dict:
        """
        Execute a database upsert operation.
        
        Args:
            node: Node definition with parameters
            context: Execution context with data to insert
        
        Returns:
            Upsert results
        """
        params = node.get('data', {}).get('parameters', {})
        table = params.get('table', '')
        key_columns = params.get('key_columns', 'id').split(',')
        data_source = params.get('data_source', 'from_input')
        
        if not table:
            return {'error': 'No table specified', 'inserted': 0, 'updated': 0}
        
        if not self.db:
            return {'error': 'Database not configured', 'inserted': 0, 'updated': 0}
        
        # Get data to upsert
        if data_source == 'from_input':
            data = context.get('variables', {}).get('results', [])
            if not isinstance(data, list):
                data = [data] if data else []
        else:
            data = []
        
        if not data:
            return {
                'table': table,
                'message': 'No data to upsert',
                'inserted': 0,
                'updated': 0,
                'success': True,
            }
        
        inserted = 0
        updated = 0
        errors = []
        
        for row in data:
            if not isinstance(row, dict):
                continue
            
            try:
                # Build upsert query
                columns = list(row.keys())
                values = [row[col] for col in columns]
                placeholders = ['%s'] * len(columns)
                
                # Build ON CONFLICT clause
                key_cols = [k.strip() for k in key_columns if k.strip() in columns]
                if not key_cols:
                    key_cols = [columns[0]] if columns else []
                
                update_cols = [c for c in columns if c not in key_cols]
                update_clause = ', '.join([f"{c} = EXCLUDED.{c}" for c in update_cols])
                
                query = f"""
                    INSERT INTO {table} ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                    ON CONFLICT ({', '.join(key_cols)})
                    DO UPDATE SET {update_clause}
                    RETURNING (xmax = 0) AS inserted
                """
                
                result = self.db.execute_query(query, tuple(values))
                
                if result and result[0].get('inserted'):
                    inserted += 1
                else:
                    updated += 1
                    
            except Exception as e:
                logger.error(f"Upsert failed for row: {e}")
                errors.append(str(e))
        
        return {
            'table': table,
            'inserted': inserted,
            'updated': updated,
            'total': inserted + updated,
            'errors': errors[:10],  # Limit error messages
            'success': len(errors) == 0,
        }
