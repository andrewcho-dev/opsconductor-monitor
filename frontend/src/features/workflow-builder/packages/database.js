/**
 * Database Package
 * 
 * Nodes for database operations:
 * - Insert
 * - Update
 * - Upsert
 * - Delete
 * - Query
 */

export default {
  id: 'database',
  name: 'Database',
  description: 'Database operations for storing and retrieving data',
  version: '1.0.0',
  icon: '💾',
  color: '#F59E0B',
  
  nodes: {
    'db:insert': {
      name: 'Insert Records',
      description: 'Insert new records into a database table',
      category: 'data',
      icon: '➕',
      color: '#F59E0B',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'data', type: 'object[]', label: 'Data to Insert' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'inserted', type: 'object[]', label: 'Inserted Records' },
        { id: 'ids', type: 'string[]', label: 'Inserted IDs' },
      ],
      
      parameters: [
        {
          id: 'table',
          type: 'table-selector',
          label: 'Table',
          default: 'devices',
          required: true,
          options: [
            { value: 'devices', label: 'Devices' },
            { value: 'interfaces', label: 'Interfaces' },
            { value: 'optical_power_readings', label: 'Optical Power Readings' },
            { value: 'scan_results', label: 'Scan Results' },
            { value: 'custom', label: 'Custom Table...' },
          ],
        },
        {
          id: 'custom_table',
          type: 'text',
          label: 'Custom Table Name',
          default: '',
          showIf: { field: 'table', value: 'custom' },
        },
        {
          id: 'data_source',
          type: 'select',
          label: 'Data Source',
          default: 'from_input',
          options: [
            { value: 'from_input', label: 'From Previous Node' },
            { value: 'manual', label: 'Manual Mapping' },
          ],
        },
        {
          id: 'data_expression',
          type: 'expression',
          label: 'Data Expression',
          default: '{{data}}',
          showIf: { field: 'data_source', value: 'from_input' },
          help: 'Expression that returns array of objects to insert',
        },
        {
          id: 'field_mapping',
          type: 'key-value',
          label: 'Field Mapping',
          default: {},
          showIf: { field: 'data_source', value: 'manual' },
          help: 'Map input fields to database columns',
        },
      ],
      
      advanced: [
        {
          id: 'on_conflict',
          type: 'select',
          label: 'On Conflict',
          default: 'error',
          options: [
            { value: 'error', label: 'Raise Error' },
            { value: 'ignore', label: 'Ignore' },
            { value: 'update', label: 'Update Existing' },
          ],
        },
        {
          id: 'conflict_columns',
          type: 'text',
          label: 'Conflict Columns',
          default: 'ip_address',
          showIf: { field: 'on_conflict', values: ['ignore', 'update'] },
          help: 'Comma-separated column names for conflict detection',
        },
        {
          id: 'batch_size',
          type: 'number',
          label: 'Batch Size',
          default: 100,
          min: 1,
          max: 10000,
          help: 'Number of records per batch insert',
        },
      ],
      
      execution: {
        type: 'data',
        executor: 'db_insert',
      },
    },

    'db:update': {
      name: 'Update Records',
      description: 'Update existing records in a database table',
      category: 'data',
      icon: '✏️',
      color: '#F59E0B',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'data', type: 'object[]', label: 'Data to Update' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'updated', type: 'object[]', label: 'Updated Records' },
        { id: 'count', type: 'number', label: 'Update Count' },
      ],
      
      parameters: [
        {
          id: 'table',
          type: 'table-selector',
          label: 'Table',
          default: 'devices',
          required: true,
        },
        {
          id: 'where_type',
          type: 'select',
          label: 'Where Condition',
          default: 'key_column',
          options: [
            { value: 'key_column', label: 'Match Key Column' },
            { value: 'expression', label: 'Custom Expression' },
          ],
        },
        {
          id: 'key_column',
          type: 'text',
          label: 'Key Column',
          default: 'ip_address',
          showIf: { field: 'where_type', value: 'key_column' },
        },
        {
          id: 'where_expression',
          type: 'text',
          label: 'Where Expression',
          default: '',
          showIf: { field: 'where_type', value: 'expression' },
          help: 'SQL WHERE clause (without WHERE keyword)',
        },
        {
          id: 'data_expression',
          type: 'expression',
          label: 'Data Expression',
          default: '{{data}}',
          help: 'Expression that returns array of objects to update',
        },
      ],
      
      execution: {
        type: 'data',
        executor: 'db_update',
      },
    },

    'db:upsert': {
      name: 'Upsert Records',
      description: 'Insert or update records (insert if not exists, update if exists)',
      category: 'data',
      icon: '🔄',
      color: '#F59E0B',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'data', type: 'object[]', label: 'Data to Upsert' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'results', type: 'object[]', label: 'Upserted Records' },
        { id: 'inserted_count', type: 'number', label: 'Inserted Count' },
        { id: 'updated_count', type: 'number', label: 'Updated Count' },
      ],
      
      parameters: [
        {
          id: 'table',
          type: 'table-selector',
          label: 'Table',
          default: 'devices',
          required: true,
        },
        {
          id: 'key_columns',
          type: 'text',
          label: 'Key Columns',
          default: 'ip_address',
          required: true,
          help: 'Comma-separated columns to match for upsert',
        },
        {
          id: 'data_expression',
          type: 'expression',
          label: 'Data Expression',
          default: '{{data}}',
          help: 'Expression that returns array of objects to upsert',
        },
        {
          id: 'update_columns',
          type: 'text',
          label: 'Columns to Update',
          default: '',
          help: 'Leave empty to update all columns, or specify comma-separated list',
        },
      ],
      
      execution: {
        type: 'data',
        executor: 'db_upsert',
      },
    },

    'db:delete': {
      name: 'Delete Records',
      description: 'Delete records from a database table',
      category: 'data',
      icon: '🗑️',
      color: '#EF4444',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'ids', type: 'string[]', label: 'IDs to Delete' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'count', type: 'number', label: 'Deleted Count' },
      ],
      
      parameters: [
        {
          id: 'table',
          type: 'table-selector',
          label: 'Table',
          default: 'devices',
          required: true,
        },
        {
          id: 'where_type',
          type: 'select',
          label: 'Delete Condition',
          default: 'by_ids',
          options: [
            { value: 'by_ids', label: 'By IDs from Input' },
            { value: 'by_column', label: 'By Column Value' },
            { value: 'expression', label: 'Custom Expression' },
          ],
        },
        {
          id: 'ids_expression',
          type: 'expression',
          label: 'IDs Expression',
          default: '{{ids}}',
          showIf: { field: 'where_type', value: 'by_ids' },
        },
        {
          id: 'column_name',
          type: 'text',
          label: 'Column Name',
          default: 'ip_address',
          showIf: { field: 'where_type', value: 'by_column' },
        },
        {
          id: 'column_values',
          type: 'expression',
          label: 'Column Values',
          default: '{{values}}',
          showIf: { field: 'where_type', value: 'by_column' },
        },
        {
          id: 'where_expression',
          type: 'text',
          label: 'Where Expression',
          default: '',
          showIf: { field: 'where_type', value: 'expression' },
          help: 'SQL WHERE clause (without WHERE keyword)',
        },
      ],
      
      execution: {
        type: 'data',
        executor: 'db_delete',
        requires_confirmation: true,
      },
    },

    'db:query': {
      name: 'Query Database',
      description: 'Execute a SELECT query and return results',
      category: 'query',
      icon: '🔎',
      color: '#F59E0B',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'results', type: 'object[]', label: 'Query Results' },
        { id: 'count', type: 'number', label: 'Row Count' },
        { id: 'first', type: 'object', label: 'First Row' },
      ],
      
      parameters: [
        {
          id: 'query_type',
          type: 'select',
          label: 'Query Type',
          default: 'simple',
          options: [
            { value: 'simple', label: 'Simple Query' },
            { value: 'custom', label: 'Custom SQL' },
          ],
        },
        {
          id: 'table',
          type: 'table-selector',
          label: 'Table',
          default: 'devices',
          showIf: { field: 'query_type', value: 'simple' },
        },
        {
          id: 'columns',
          type: 'text',
          label: 'Columns',
          default: '*',
          showIf: { field: 'query_type', value: 'simple' },
          help: 'Comma-separated column names or * for all',
        },
        {
          id: 'where',
          type: 'text',
          label: 'Where Clause',
          default: '',
          showIf: { field: 'query_type', value: 'simple' },
          help: 'Optional WHERE clause (without WHERE keyword)',
        },
        {
          id: 'order_by',
          type: 'text',
          label: 'Order By',
          default: '',
          showIf: { field: 'query_type', value: 'simple' },
        },
        {
          id: 'limit',
          type: 'number',
          label: 'Limit',
          default: 1000,
          min: 1,
          max: 100000,
          showIf: { field: 'query_type', value: 'simple' },
        },
        {
          id: 'custom_sql',
          type: 'code',
          label: 'SQL Query',
          default: 'SELECT * FROM devices WHERE ping_status = \'online\' LIMIT 100',
          language: 'sql',
          showIf: { field: 'query_type', value: 'custom' },
        },
      ],
      
      execution: {
        type: 'data',
        executor: 'db_query',
      },
    },
  },
};
