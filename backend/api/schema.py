"""
Schema API - Database schema discovery endpoints.

Provides endpoints for discovering available tables and columns
for use in the workflow builder's database nodes.
"""

from flask import Blueprint, jsonify
import logging
from database import DatabaseManager

logger = logging.getLogger(__name__)

schema_bp = Blueprint('schema', __name__, url_prefix='/api/schema')


@schema_bp.route('/tables', methods=['GET'])
def get_tables():
    """
    Get list of available database tables.
    
    Returns:
        JSON list of table names with metadata
    """
    try:
        db = DatabaseManager()
        
        # Query PostgreSQL information_schema for tables
        query = """
            SELECT 
                table_name,
                (SELECT COUNT(*) FROM information_schema.columns c 
                 WHERE c.table_name = t.table_name 
                 AND c.table_schema = 'public') as column_count
            FROM information_schema.tables t
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        
        results = db.execute_query(query)
        
        # Add friendly labels for known tables
        table_labels = {
            'scan_results': 'Scan Results (Devices)',
            'interfaces': 'Network Interfaces',
            'optical_power_readings': 'Optical Power Readings',
            'poller_configs': 'Poller Configurations',
            'job_definitions': 'Job Definitions',
            'scheduler_jobs': 'Scheduled Jobs',
            'workflow_definitions': 'Workflow Definitions',
            'workflow_folders': 'Workflow Folders',
            'workflow_executions': 'Workflow Executions',
            'alerts': 'Alerts',
            'credentials': 'Credentials',
        }
        
        tables = []
        for row in results:
            table_name = row['table_name']
            tables.append({
                'name': table_name,
                'label': table_labels.get(table_name, table_name.replace('_', ' ').title()),
                'column_count': row['column_count'],
            })
        
        return jsonify({
            'success': True,
            'tables': tables,
        })
        
    except Exception as e:
        logger.error(f"Failed to get tables: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'tables': [],
        }), 500


@schema_bp.route('/tables/<table_name>/columns', methods=['GET'])
def get_table_columns(table_name):
    """
    Get columns for a specific table.
    
    Args:
        table_name: Name of the table
        
    Returns:
        JSON list of column definitions
    """
    try:
        db = DatabaseManager()
        
        # Query PostgreSQL information_schema for columns
        query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = %s
            ORDER BY ordinal_position
        """
        
        results = db.execute_query(query, (table_name,))
        
        if not results:
            return jsonify({
                'success': False,
                'error': f'Table "{table_name}" not found',
                'columns': [],
            }), 404
        
        columns = []
        for row in results:
            columns.append({
                'name': row['column_name'],
                'type': row['data_type'],
                'nullable': row['is_nullable'] == 'YES',
                'has_default': row['column_default'] is not None,
                'max_length': row['character_maximum_length'],
            })
        
        return jsonify({
            'success': True,
            'table': table_name,
            'columns': columns,
        })
        
    except Exception as e:
        logger.error(f"Failed to get columns for {table_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'columns': [],
        }), 500


@schema_bp.route('/input-fields', methods=['GET'])
def get_common_input_fields():
    """
    Get common input field names from workflow node outputs.
    
    This helps users know what fields are typically available
    from common nodes like network:ping, snmp:get, etc.
    
    Returns:
        JSON object with node types and their output fields
    """
    # Static mapping of common node output fields
    node_outputs = {
        'network:ping': {
            'description': 'Ping results from network:ping node',
            'fields': [
                {'name': 'ip_address', 'type': 'string', 'description': 'Target IP address'},
                {'name': 'ping_status', 'type': 'string', 'description': 'online/offline/timeout'},
                {'name': 'target', 'type': 'string', 'description': 'Original target (same as ip_address)'},
                {'name': 'status', 'type': 'string', 'description': 'online/offline/timeout/error'},
                {'name': 'rtt_ms', 'type': 'number', 'description': 'Round-trip time in milliseconds'},
                {'name': 'packets_sent', 'type': 'number', 'description': 'Number of packets sent'},
                {'name': 'packets_received', 'type': 'number', 'description': 'Number of packets received'},
            ],
        },
        'snmp:get': {
            'description': 'SNMP GET results',
            'fields': [
                {'name': 'ip_address', 'type': 'string', 'description': 'Target IP address'},
                {'name': 'oid', 'type': 'string', 'description': 'OID that was queried'},
                {'name': 'value', 'type': 'string', 'description': 'SNMP value returned'},
                {'name': 'type', 'type': 'string', 'description': 'SNMP value type'},
            ],
        },
        'snmp:walk': {
            'description': 'SNMP WALK results',
            'fields': [
                {'name': 'ip_address', 'type': 'string', 'description': 'Target IP address'},
                {'name': 'results', 'type': 'array', 'description': 'Array of OID/value pairs'},
            ],
        },
        'db:query': {
            'description': 'Database query results',
            'fields': [
                {'name': 'results', 'type': 'array', 'description': 'Array of row objects'},
                {'name': 'count', 'type': 'number', 'description': 'Number of rows returned'},
            ],
        },
    }
    
    return jsonify({
        'success': True,
        'node_outputs': node_outputs,
    })
