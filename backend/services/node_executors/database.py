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
    """Executor for database upsert (insert/update) nodes.
    
    Supports n8n-style column mapping where users can specify:
    - column_mapping: List of {source: 'input_field', target: 'db_column'} mappings
    - Or columns: Comma-separated list of columns to use (uses same name from input)
    """
    
    def __init__(self, db_manager=None):
        self.db = db_manager
    
    def execute(self, node: Dict, context) -> Dict:
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
        key_columns = params.get('key_columns', 'ip_address').split(',')
        data_source = params.get('data_source', 'from_input')
        
        # n8n-style column mapping: [{source: 'input_field', target: 'db_column'}, ...]
        column_mapping = params.get('column_mapping', [])
        # Or simple column list (uses same name for source and target)
        columns_param = params.get('columns', '')
        
        if not table:
            return {'error': 'No table specified', 'inserted': 0, 'updated': 0, 'success': False}
        
        if not self.db:
            return {'error': 'Database not configured', 'inserted': 0, 'updated': 0, 'success': False}
        
        # Get data to upsert (handle both dict and ExecutionContext)
        if data_source == 'from_input':
            if hasattr(context, 'variables'):
                variables = context.variables
            else:
                variables = context.get('variables', {})
            data = variables.get('results', [])
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
        
        # Build column mapping
        mapping = {}
        if column_mapping:
            # Explicit mapping: [{source: 'ip_address', target: 'ip_address'}, ...]
            for m in column_mapping:
                if isinstance(m, dict) and 'source' in m and 'target' in m:
                    mapping[m['source']] = m['target']
        elif columns_param:
            # Simple column list: 'ip_address,ping_status' - same name for source and target
            for col in columns_param.split(','):
                col = col.strip()
                if col:
                    mapping[col] = col
        
        # If no mapping specified, try to auto-detect safe columns
        # Only use columns that exist in the first row of data
        if not mapping and data:
            first_row = data[0] if isinstance(data[0], dict) else {}
            # Default safe columns for scan_results table
            safe_columns = ['ip_address', 'ping_status', 'scan_timestamp']
            for col in safe_columns:
                if col in first_row:
                    mapping[col] = col
        
        if not mapping:
            return {
                'table': table,
                'error': 'No column mapping specified. Configure columns or column_mapping parameter.',
                'inserted': 0,
                'updated': 0,
                'success': False,
            }
        
        inserted = 0
        updated = 0
        errors = []
        
        for row in data:
            if not isinstance(row, dict):
                continue
            
            try:
                # Apply column mapping - only include mapped columns
                mapped_row = {}
                for source_col, target_col in mapping.items():
                    if source_col in row:
                        mapped_row[target_col] = row[source_col]
                
                if not mapped_row:
                    continue
                
                # Build upsert query with only mapped columns
                columns = list(mapped_row.keys())
                values = [mapped_row[col] for col in columns]
                placeholders = ['%s'] * len(columns)
                
                # Build ON CONFLICT clause
                key_cols = [k.strip() for k in key_columns if k.strip() in columns]
                if not key_cols:
                    key_cols = [columns[0]] if columns else []
                
                update_cols = [c for c in columns if c not in key_cols]
                
                if update_cols:
                    update_clause = ', '.join([f"{c} = EXCLUDED.{c}" for c in update_cols])
                    query = f"""
                        INSERT INTO {table} ({', '.join(columns)})
                        VALUES ({', '.join(placeholders)})
                        ON CONFLICT ({', '.join(key_cols)})
                        DO UPDATE SET {update_clause}
                        RETURNING (xmax = 0) AS inserted
                    """
                else:
                    # No update columns, just insert or ignore
                    query = f"""
                        INSERT INTO {table} ({', '.join(columns)})
                        VALUES ({', '.join(placeholders)})
                        ON CONFLICT ({', '.join(key_cols)}) DO NOTHING
                        RETURNING (xmax = 0) AS inserted
                    """
                
                result = self.db.execute_query(query, tuple(values))
                
                if result and len(result) > 0 and result[0].get('inserted'):
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
            'columns_used': list(mapping.values()),
            'errors': errors[:10],
            'success': len(errors) == 0,
        }
