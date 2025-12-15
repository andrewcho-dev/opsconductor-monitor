/**
 * Debug/Utility Package
 * 
 * Nodes for debugging and utility functions:
 * - Debug
 * - Comment/Note
 * - Set Variable
 * - Get Variable
 */

export default {
  id: 'debug-utility',
  name: 'Debug / Utility',
  description: 'Debugging tools and utility nodes',
  version: '1.0.0',
  icon: '🔧',
  color: '#6B7280',
  
  nodes: {
    'debug:log': {
      name: 'Debug',
      description: 'Log data for debugging purposes',
      category: 'logic',
      icon: '🐛',
      color: '#6B7280',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'output', type: 'trigger', label: 'Output' },
      ],
      
      parameters: [
        {
          id: 'log_level',
          type: 'select',
          label: 'Log Level',
          default: 'info',
          options: [
            { value: 'debug', label: 'Debug' },
            { value: 'info', label: 'Info' },
            { value: 'warn', label: 'Warning' },
            { value: 'error', label: 'Error' },
          ],
        },
        {
          id: 'message',
          type: 'text',
          label: 'Message',
          default: 'Debug point reached',
        },
        {
          id: 'log_data',
          type: 'checkbox',
          label: 'Log Input Data',
          default: true,
        },
        {
          id: 'data_fields',
          type: 'text',
          label: 'Specific Fields (comma-separated)',
          default: '',
          help: 'Leave empty to log all fields',
          showIf: { field: 'log_data', value: true },
        },
        {
          id: 'pause_execution',
          type: 'checkbox',
          label: 'Pause Execution (breakpoint)',
          default: false,
          help: 'Pause workflow at this point for inspection',
        },
      ],
      
      execution: {
        type: 'utility',
        executor: 'debug',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'debug:comment': {
      name: 'Comment',
      description: 'Add a comment/note to the workflow (no execution)',
      category: 'logic',
      icon: '💬',
      color: '#9CA3AF',
      
      inputs: [],
      outputs: [],
      
      parameters: [
        {
          id: 'title',
          type: 'text',
          label: 'Title',
          default: 'Note',
        },
        {
          id: 'content',
          type: 'textarea',
          label: 'Content',
          default: '',
          placeholder: 'Add your notes here...',
        },
        {
          id: 'color',
          type: 'select',
          label: 'Color',
          default: 'yellow',
          options: [
            { value: 'yellow', label: 'Yellow' },
            { value: 'blue', label: 'Blue' },
            { value: 'green', label: 'Green' },
            { value: 'red', label: 'Red' },
            { value: 'purple', label: 'Purple' },
          ],
        },
      ],
      
      execution: {
        type: 'none',
        executor: null,
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'debug:set-variable': {
      name: 'Set Variable',
      description: 'Set a workflow variable for use in other nodes',
      category: 'logic',
      icon: '📌',
      color: '#6B7280',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'output', type: 'trigger', label: 'Output' },
      ],
      
      parameters: [
        {
          id: 'variable_name',
          type: 'text',
          label: 'Variable Name',
          default: 'myVariable',
          required: true,
        },
        {
          id: 'value_source',
          type: 'select',
          label: 'Value Source',
          default: 'input_field',
          options: [
            { value: 'input_field', label: 'From Input Field' },
            { value: 'static', label: 'Static Value' },
            { value: 'expression', label: 'Expression' },
          ],
        },
        {
          id: 'input_field',
          type: 'text',
          label: 'Input Field',
          default: 'data',
          showIf: { field: 'value_source', value: 'input_field' },
        },
        {
          id: 'static_value',
          type: 'text',
          label: 'Static Value',
          default: '',
          showIf: { field: 'value_source', value: 'static' },
        },
        {
          id: 'expression',
          type: 'expression',
          label: 'Expression',
          default: '{{$json.value}}',
          showIf: { field: 'value_source', value: 'expression' },
        },
        {
          id: 'scope',
          type: 'select',
          label: 'Scope',
          default: 'workflow',
          options: [
            { value: 'workflow', label: 'Workflow (this execution)' },
            { value: 'global', label: 'Global (persists across executions)' },
          ],
        },
      ],
      
      execution: {
        type: 'utility',
        executor: 'set_variable',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'debug:get-variable': {
      name: 'Get Variable',
      description: 'Get a workflow variable value',
      category: 'logic',
      icon: '📎',
      color: '#6B7280',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'output', type: 'trigger', label: 'Output' },
      ],
      
      parameters: [
        {
          id: 'variable_name',
          type: 'text',
          label: 'Variable Name',
          default: 'myVariable',
          required: true,
        },
        {
          id: 'output_field',
          type: 'text',
          label: 'Output Field',
          default: 'value',
        },
        {
          id: 'default_value',
          type: 'text',
          label: 'Default Value',
          default: '',
          help: 'Value to use if variable is not set',
        },
      ],
      
      execution: {
        type: 'utility',
        executor: 'get_variable',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'debug:execution-data': {
      name: 'Execution Data',
      description: 'Get metadata about the current workflow execution',
      category: 'logic',
      icon: 'ℹ️',
      color: '#6B7280',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'output', type: 'trigger', label: 'Output' },
      ],
      
      parameters: [
        {
          id: 'include',
          type: 'multi-select',
          label: 'Include',
          default: ['execution_id', 'workflow_id', 'started_at'],
          options: [
            { value: 'execution_id', label: 'Execution ID' },
            { value: 'workflow_id', label: 'Workflow ID' },
            { value: 'workflow_name', label: 'Workflow Name' },
            { value: 'started_at', label: 'Started At' },
            { value: 'trigger_type', label: 'Trigger Type' },
            { value: 'node_count', label: 'Node Count' },
            { value: 'current_node', label: 'Current Node' },
          ],
        },
        {
          id: 'output_field',
          type: 'text',
          label: 'Output Field',
          default: 'execution',
        },
      ],
      
      execution: {
        type: 'utility',
        executor: 'execution_data',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'debug:assert': {
      name: 'Assert',
      description: 'Assert a condition and fail if not met',
      category: 'logic',
      icon: '✓',
      color: '#6B7280',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'pass', type: 'trigger', label: 'Pass' },
        { id: 'fail', type: 'trigger', label: 'Fail' },
      ],
      
      parameters: [
        {
          id: 'condition',
          type: 'condition',
          label: 'Condition',
          default: { field: '', operator: 'exists', value: '' },
          required: true,
        },
        {
          id: 'fail_message',
          type: 'text',
          label: 'Failure Message',
          default: 'Assertion failed',
        },
        {
          id: 'stop_on_fail',
          type: 'checkbox',
          label: 'Stop Workflow on Failure',
          default: false,
        },
      ],
      
      execution: {
        type: 'utility',
        executor: 'assert',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },
  },
};
