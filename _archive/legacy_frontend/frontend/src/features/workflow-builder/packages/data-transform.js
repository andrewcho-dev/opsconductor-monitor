import { PLATFORMS } from '../platforms';

const universalPlatform = {
  platforms: [PLATFORMS.ANY],
  protocols: [],
};

/**
 * Data Transformation Package
 * 
 * Nodes for transforming, filtering, and manipulating data:
 * - Set Fields
 * - Split
 * - Merge
 * - Aggregate
 * - Sort
 * - Limit
 * - Filter
 * - Code/Function
 */

export default {
  id: 'data-transform',
  name: 'Data Transform',
  description: 'Transform, filter, and manipulate data in workflows',
  version: '1.0.0',
  icon: '🔄',
  color: '#8B5CF6',
  
  nodes: {
    'transform:set-fields': {
      name: 'Set Fields',
      description: 'Add, rename, or remove fields from data items',
      category: 'data',
      ...universalPlatform,
      icon: '✏️',
      color: '#8B5CF6',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'output', type: 'trigger', label: 'Output' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'mode',
          type: 'select',
          label: 'Mode',
          default: 'manual',
          options: [
            { value: 'manual', label: 'Set Fields Manually' },
            { value: 'expression', label: 'Use Expressions' },
          ],
        },
        {
          id: 'fields',
          type: 'key-value-list',
          label: 'Fields to Set',
          default: [],
          showIf: { field: 'mode', value: 'manual' },
          help: 'Define field name and value pairs',
        },
        {
          id: 'expression',
          type: 'code',
          label: 'Expression',
          default: '// Return modified item\nreturn { ...item, newField: "value" };',
          language: 'javascript',
          showIf: { field: 'mode', value: 'expression' },
        },
        {
          id: 'keep_only_set',
          type: 'checkbox',
          label: 'Keep Only Set Fields',
          default: false,
          help: 'Remove all fields except those explicitly set',
        },
      ],
      
      execution: {
        type: 'transform',
        executor: 'set_fields',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'transform:split': {
      name: 'Split Out',
      description: 'Split array items into separate items',
      category: 'data',
      ...universalPlatform,
      icon: '↔️',
      color: '#8B5CF6',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'output', type: 'trigger', label: 'Output' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'field_to_split',
          type: 'text',
          label: 'Field to Split',
          default: 'items',
          required: true,
          help: 'Name of the array field to split',
        },
        {
          id: 'include_parent',
          type: 'checkbox',
          label: 'Include Parent Fields',
          default: true,
          help: 'Include parent object fields in each split item',
        },
        {
          id: 'destination_field',
          type: 'text',
          label: 'Destination Field Name',
          default: '',
          help: 'Optional: rename the split field (leave empty to keep original)',
        },
      ],
      
      execution: {
        type: 'transform',
        executor: 'split_out',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'transform:merge': {
      name: 'Merge',
      description: 'Merge data from multiple inputs',
      category: 'data',
      ...universalPlatform,
      icon: '🔀',
      color: '#8B5CF6',
      
      inputs: [
        { id: 'input1', type: 'trigger', label: 'Input 1', required: true },
        { id: 'input2', type: 'trigger', label: 'Input 2', required: true },
      ],
      outputs: [
        { id: 'output', type: 'trigger', label: 'Output' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'mode',
          type: 'select',
          label: 'Merge Mode',
          default: 'append',
          options: [
            { value: 'append', label: 'Append (combine all items)' },
            { value: 'combine_by_position', label: 'Combine by Position' },
            { value: 'combine_by_key', label: 'Combine by Key Field' },
            { value: 'keep_matches', label: 'Keep Matches Only (inner join)' },
            { value: 'enrich', label: 'Enrich (left join)' },
          ],
        },
        {
          id: 'key_field_1',
          type: 'text',
          label: 'Key Field (Input 1)',
          default: 'id',
          showIf: { field: 'mode', value: ['combine_by_key', 'keep_matches', 'enrich'] },
        },
        {
          id: 'key_field_2',
          type: 'text',
          label: 'Key Field (Input 2)',
          default: 'id',
          showIf: { field: 'mode', value: ['combine_by_key', 'keep_matches', 'enrich'] },
        },
        {
          id: 'clash_handling',
          type: 'select',
          label: 'Field Clash Handling',
          default: 'prefer_input1',
          options: [
            { value: 'prefer_input1', label: 'Prefer Input 1' },
            { value: 'prefer_input2', label: 'Prefer Input 2' },
            { value: 'add_suffix', label: 'Add Suffix to Input 2' },
          ],
        },
      ],
      
      execution: {
        type: 'transform',
        executor: 'merge',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'transform:aggregate': {
      name: 'Aggregate',
      description: 'Aggregate items (sum, count, average, group by)',
      category: 'data',
      ...universalPlatform,
      icon: '📊',
      color: '#8B5CF6',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'output', type: 'trigger', label: 'Output' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'group_by',
          type: 'text',
          label: 'Group By Field',
          default: '',
          help: 'Field to group items by (leave empty for all items)',
        },
        {
          id: 'aggregations',
          type: 'aggregation-list',
          label: 'Aggregations',
          default: [
            { field: '*', operation: 'count', output_name: 'count' },
          ],
          help: 'Define aggregation operations',
        },
      ],
      
      execution: {
        type: 'transform',
        executor: 'aggregate',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'transform:sort': {
      name: 'Sort',
      description: 'Sort items by one or more fields',
      category: 'data',
      ...universalPlatform,
      icon: '↕️',
      color: '#8B5CF6',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'output', type: 'trigger', label: 'Output' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'sort_fields',
          type: 'sort-field-list',
          label: 'Sort By',
          default: [
            { field: 'id', direction: 'asc' },
          ],
        },
        {
          id: 'case_sensitive',
          type: 'checkbox',
          label: 'Case Sensitive',
          default: false,
        },
      ],
      
      execution: {
        type: 'transform',
        executor: 'sort',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'transform:limit': {
      name: 'Limit',
      description: 'Limit the number of items',
      category: 'data',
      ...universalPlatform,
      icon: '✂️',
      color: '#8B5CF6',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'output', type: 'trigger', label: 'Output' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'max_items',
          type: 'number',
          label: 'Maximum Items',
          default: 10,
          min: 1,
          required: true,
        },
        {
          id: 'offset',
          type: 'number',
          label: 'Offset (Skip)',
          default: 0,
          min: 0,
          help: 'Number of items to skip from the beginning',
        },
      ],
      
      execution: {
        type: 'transform',
        executor: 'limit',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'transform:filter': {
      name: 'Filter',
      description: 'Filter items based on conditions',
      category: 'data',
      ...universalPlatform,
      icon: '🔍',
      color: '#8B5CF6',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'matched', type: 'trigger', label: 'Matched' },
        { id: 'unmatched', type: 'trigger', label: 'Not Matched' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'conditions',
          type: 'condition-list',
          label: 'Conditions',
          default: [],
          help: 'Define filter conditions',
        },
        {
          id: 'combine',
          type: 'select',
          label: 'Combine Conditions',
          default: 'and',
          options: [
            { value: 'and', label: 'AND (all must match)' },
            { value: 'or', label: 'OR (any must match)' },
          ],
        },
      ],
      
      execution: {
        type: 'transform',
        executor: 'filter',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'transform:code': {
      name: 'Code',
      description: 'Run custom JavaScript code to transform data',
      category: 'data',
      ...universalPlatform,
      icon: '💻',
      color: '#F59E0B',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'output', type: 'trigger', label: 'Output' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'mode',
          type: 'select',
          label: 'Mode',
          default: 'run_once_all_items',
          options: [
            { value: 'run_once_all_items', label: 'Run Once for All Items' },
            { value: 'run_once_each_item', label: 'Run Once for Each Item' },
          ],
        },
        {
          id: 'code',
          type: 'code',
          label: 'JavaScript Code',
          default: `// Available variables:
// - items: array of input items
// - item: current item (in each-item mode)
// - $input: input data helper
// - $json: current item's JSON data

// Return the modified items
return items.map(item => ({
  ...item,
  processed: true
}));`,
          language: 'javascript',
          required: true,
        },
      ],
      
      execution: {
        type: 'transform',
        executor: 'code',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'transform:remove-duplicates': {
      name: 'Remove Duplicates',
      description: 'Remove duplicate items based on a field',
      category: 'data',
      ...universalPlatform,
      icon: '🧹',
      color: '#8B5CF6',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'output', type: 'trigger', label: 'Output' },
        { id: 'duplicates', type: 'trigger', label: 'Duplicates' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'compare_field',
          type: 'text',
          label: 'Compare Field',
          default: 'id',
          required: true,
          help: 'Field to use for duplicate detection',
        },
        {
          id: 'keep',
          type: 'select',
          label: 'Keep',
          default: 'first',
          options: [
            { value: 'first', label: 'First Occurrence' },
            { value: 'last', label: 'Last Occurrence' },
          ],
        },
      ],
      
      execution: {
        type: 'transform',
        executor: 'remove_duplicates',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'transform:rename-keys': {
      name: 'Rename Keys',
      description: 'Rename field keys in data items',
      category: 'data',
      ...universalPlatform,
      icon: '🏷️',
      color: '#8B5CF6',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'output', type: 'trigger', label: 'Output' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'renames',
          type: 'key-value-list',
          label: 'Rename Mappings',
          default: [],
          help: 'Old name → New name mappings',
        },
      ],
      
      execution: {
        type: 'transform',
        executor: 'rename_keys',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },
  },
};
