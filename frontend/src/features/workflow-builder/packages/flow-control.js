/**
 * Flow Control Package
 * 
 * Nodes for controlling workflow execution flow:
 * - Wait/Delay
 * - Retry
 * - Error Trigger
 * - Stop and Error
 * - No Operation
 */

export default {
  id: 'flow-control',
  name: 'Flow Control',
  description: 'Control workflow execution flow with delays, retries, and error handling',
  version: '1.0.0',
  icon: '🎛️',
  color: '#EC4899',
  
  nodes: {
    'flow:wait': {
      name: 'Wait',
      description: 'Pause workflow execution for a specified time',
      category: 'logic',
      icon: '⏱️',
      color: '#EC4899',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'output', type: 'trigger', label: 'Output' },
      ],
      
      parameters: [
        {
          id: 'wait_type',
          type: 'select',
          label: 'Wait Type',
          default: 'fixed',
          options: [
            { value: 'fixed', label: 'Fixed Duration' },
            { value: 'until_time', label: 'Until Specific Time' },
            { value: 'webhook', label: 'Until Webhook Received' },
          ],
        },
        {
          id: 'duration',
          type: 'number',
          label: 'Duration',
          default: 5,
          min: 0,
          showIf: { field: 'wait_type', value: 'fixed' },
        },
        {
          id: 'duration_unit',
          type: 'select',
          label: 'Unit',
          default: 'seconds',
          options: [
            { value: 'milliseconds', label: 'Milliseconds' },
            { value: 'seconds', label: 'Seconds' },
            { value: 'minutes', label: 'Minutes' },
            { value: 'hours', label: 'Hours' },
          ],
          showIf: { field: 'wait_type', value: 'fixed' },
        },
        {
          id: 'resume_time',
          type: 'datetime',
          label: 'Resume At',
          default: '',
          showIf: { field: 'wait_type', value: 'until_time' },
        },
        {
          id: 'webhook_id',
          type: 'text',
          label: 'Webhook ID',
          default: '',
          showIf: { field: 'wait_type', value: 'webhook' },
          help: 'Unique ID for the resume webhook',
        },
      ],
      
      execution: {
        type: 'flow',
        executor: 'wait',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'flow:delay': {
      name: 'Delay',
      description: 'Add a simple delay between nodes',
      category: 'logic',
      icon: '⏸️',
      color: '#EC4899',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'output', type: 'trigger', label: 'Output' },
      ],
      
      parameters: [
        {
          id: 'delay_seconds',
          type: 'number',
          label: 'Delay (seconds)',
          default: 1,
          min: 0,
          max: 3600,
        },
      ],
      
      execution: {
        type: 'flow',
        executor: 'delay',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'flow:retry': {
      name: 'Retry',
      description: 'Retry failed operations with configurable backoff',
      category: 'logic',
      icon: '🔁',
      color: '#EC4899',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Final Failure' },
      ],
      
      parameters: [
        {
          id: 'max_retries',
          type: 'number',
          label: 'Max Retries',
          default: 3,
          min: 1,
          max: 10,
        },
        {
          id: 'retry_delay',
          type: 'number',
          label: 'Delay Between Retries (seconds)',
          default: 1,
          min: 0,
        },
        {
          id: 'backoff',
          type: 'select',
          label: 'Backoff Strategy',
          default: 'fixed',
          options: [
            { value: 'fixed', label: 'Fixed Delay' },
            { value: 'linear', label: 'Linear (delay * attempt)' },
            { value: 'exponential', label: 'Exponential (delay ^ attempt)' },
          ],
        },
        {
          id: 'max_delay',
          type: 'number',
          label: 'Max Delay (seconds)',
          default: 60,
          min: 1,
          showIf: { field: 'backoff', value: ['linear', 'exponential'] },
        },
      ],
      
      execution: {
        type: 'flow',
        executor: 'retry',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'flow:error-trigger': {
      name: 'Error Trigger',
      description: 'Trigger when an error occurs in the workflow',
      category: 'triggers',
      icon: '⚠️',
      color: '#EF4444',
      
      inputs: [],
      outputs: [
        { id: 'error', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'error_source',
          type: 'select',
          label: 'Error Source',
          default: 'any',
          options: [
            { value: 'any', label: 'Any Node Error' },
            { value: 'specific', label: 'Specific Node' },
          ],
        },
        {
          id: 'source_node_id',
          type: 'node-selector',
          label: 'Source Node',
          default: '',
          showIf: { field: 'error_source', value: 'specific' },
        },
        {
          id: 'continue_workflow',
          type: 'checkbox',
          label: 'Continue Workflow on Error',
          default: true,
          help: 'If unchecked, workflow will stop after error handling',
        },
      ],
      
      execution: {
        type: 'trigger',
        executor: 'error_trigger',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'flow:stop': {
      name: 'Stop and Error',
      description: 'Stop workflow execution with an error',
      category: 'logic',
      icon: '🛑',
      color: '#EF4444',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [],
      
      parameters: [
        {
          id: 'error_message',
          type: 'text',
          label: 'Error Message',
          default: 'Workflow stopped',
          required: true,
        },
        {
          id: 'error_type',
          type: 'select',
          label: 'Error Type',
          default: 'error',
          options: [
            { value: 'error', label: 'Error' },
            { value: 'warning', label: 'Warning' },
            { value: 'info', label: 'Info (no error)' },
          ],
        },
      ],
      
      execution: {
        type: 'flow',
        executor: 'stop',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'flow:noop': {
      name: 'No Operation',
      description: 'Pass data through without modification (for debugging)',
      category: 'logic',
      icon: '➡️',
      color: '#6B7280',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'output', type: 'trigger', label: 'Output' },
      ],
      
      parameters: [
        {
          id: 'log_data',
          type: 'checkbox',
          label: 'Log Data',
          default: false,
          help: 'Log input data to console',
        },
        {
          id: 'label',
          type: 'text',
          label: 'Label',
          default: '',
          help: 'Optional label for debugging',
        },
      ],
      
      execution: {
        type: 'flow',
        executor: 'noop',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'flow:switch': {
      name: 'Switch',
      description: 'Route data to different outputs based on conditions',
      category: 'logic',
      icon: '🔀',
      color: '#EC4899',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'output_0', type: 'trigger', label: 'Case 1' },
        { id: 'output_1', type: 'trigger', label: 'Case 2' },
        { id: 'output_2', type: 'trigger', label: 'Case 3' },
        { id: 'default', type: 'trigger', label: 'Default' },
      ],
      
      parameters: [
        {
          id: 'mode',
          type: 'select',
          label: 'Mode',
          default: 'rules',
          options: [
            { value: 'rules', label: 'Rules (conditions)' },
            { value: 'expression', label: 'Expression (value matching)' },
          ],
        },
        {
          id: 'rules',
          type: 'rule-list',
          label: 'Rules',
          default: [],
          showIf: { field: 'mode', value: 'rules' },
        },
        {
          id: 'match_field',
          type: 'text',
          label: 'Field to Match',
          default: 'type',
          showIf: { field: 'mode', value: 'expression' },
        },
        {
          id: 'cases',
          type: 'case-list',
          label: 'Cases',
          default: [],
          showIf: { field: 'mode', value: 'expression' },
        },
        {
          id: 'fallback_output',
          type: 'select',
          label: 'Fallback',
          default: 'default',
          options: [
            { value: 'default', label: 'Route to Default' },
            { value: 'none', label: 'Drop Item' },
          ],
        },
      ],
      
      execution: {
        type: 'flow',
        executor: 'switch',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'flow:loop': {
      name: 'Loop',
      description: 'Loop over items or repeat a fixed number of times',
      category: 'logic',
      icon: '🔄',
      color: '#EC4899',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'loop', type: 'trigger', label: 'Loop Body' },
        { id: 'done', type: 'trigger', label: 'Done' },
      ],
      
      parameters: [
        {
          id: 'loop_type',
          type: 'select',
          label: 'Loop Type',
          default: 'items',
          options: [
            { value: 'items', label: 'Loop Over Items' },
            { value: 'count', label: 'Fixed Count' },
          ],
        },
        {
          id: 'count',
          type: 'number',
          label: 'Iterations',
          default: 10,
          min: 1,
          showIf: { field: 'loop_type', value: 'count' },
        },
        {
          id: 'batch_size',
          type: 'number',
          label: 'Batch Size',
          default: 1,
          min: 1,
          help: 'Process items in batches',
        },
      ],
      
      execution: {
        type: 'flow',
        executor: 'loop',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },
  },
};
