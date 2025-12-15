/**
 * Core Package
 * 
 * Essential workflow nodes that are always available.
 * Cannot be disabled.
 */

export default {
  id: 'core',
  name: 'Core',
  description: 'Essential workflow nodes - triggers, logic, and flow control',
  version: '1.0.0',
  icon: '⚡',
  color: '#6366F1',
  builtin: true,
  canDisable: false,

  nodes: {
    // ============ TRIGGERS ============
    'trigger:manual': {
      name: 'Manual Start',
      description: 'Start workflow manually with a button click',
      category: 'triggers',
      icon: '▶️',
      color: '#22C55E',
      
      inputs: [],
      outputs: [
        { id: 'trigger', type: 'trigger', label: 'Start' },
      ],
      
      parameters: [
        {
          id: 'name',
          type: 'text',
          label: 'Trigger Name',
          default: 'Manual Start',
          required: false,
        },
      ],
      
      execution: {
        type: 'trigger',
        executor: 'manual_trigger',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'trigger:schedule': {
      name: 'Schedule',
      description: 'Start workflow on a schedule (cron or interval)',
      category: 'triggers',
      icon: '⏰',
      color: '#22C55E',
      
      inputs: [],
      outputs: [
        { id: 'trigger', type: 'trigger', label: 'On Schedule' },
      ],
      
      parameters: [
        {
          id: 'schedule_type',
          type: 'select',
          label: 'Schedule Type',
          default: 'interval',
          options: [
            { value: 'interval', label: 'Interval (every X minutes)' },
            { value: 'cron', label: 'Cron Expression' },
          ],
        },
        {
          id: 'interval_minutes',
          type: 'number',
          label: 'Interval (minutes)',
          default: 5,
          min: 1,
          max: 1440,
          showIf: { field: 'schedule_type', value: 'interval' },
        },
        {
          id: 'cron_expression',
          type: 'cron',
          label: 'Cron Expression',
          default: '*/5 * * * *',
          showIf: { field: 'schedule_type', value: 'cron' },
          help: 'Standard cron format: minute hour day month weekday',
        },
        {
          id: 'timezone',
          type: 'select',
          label: 'Timezone',
          default: 'UTC',
          options: [
            { value: 'UTC', label: 'UTC' },
            { value: 'America/Los_Angeles', label: 'Pacific Time' },
            { value: 'America/New_York', label: 'Eastern Time' },
            { value: 'Europe/London', label: 'London' },
          ],
        },
      ],
      
      execution: {
        type: 'trigger',
        executor: 'schedule_trigger',
        context: 'local',
        platform: 'any',
        requirements: {},
      },
    },

    'trigger:webhook': {
      name: 'Webhook',
      description: 'Start workflow when an HTTP webhook is received',
      category: 'triggers',
      icon: '🔗',
      color: '#22C55E',
      
      inputs: [],
      outputs: [
        { id: 'trigger', type: 'trigger', label: 'On Webhook' },
        { id: 'body', type: 'object', label: 'Request Body' },
        { id: 'headers', type: 'object', label: 'Headers' },
      ],
      
      parameters: [
        {
          id: 'path',
          type: 'text',
          label: 'Webhook Path',
          default: '/webhook/my-workflow',
          help: 'URL path for this webhook',
        },
        {
          id: 'method',
          type: 'select',
          label: 'HTTP Method',
          default: 'POST',
          options: [
            { value: 'GET', label: 'GET' },
            { value: 'POST', label: 'POST' },
            { value: 'PUT', label: 'PUT' },
          ],
        },
      ],
      
      execution: {
        type: 'trigger',
        executor: 'webhook_trigger',
        context: 'local',
        platform: 'any',
        requirements: {
          network: true,
        },
      },
    },

    // ============ LOGIC ============
    'logic:if': {
      name: 'If / Else',
      description: 'Branch workflow based on a condition',
      category: 'logic',
      icon: '🔀',
      color: '#A855F7',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Input' },
        { id: 'value', type: 'any', label: 'Value to Check' },
      ],
      outputs: [
        { id: 'true', type: 'trigger', label: 'True' },
        { id: 'false', type: 'trigger', label: 'False' },
      ],
      
      parameters: [
        {
          id: 'condition_type',
          type: 'select',
          label: 'Condition Type',
          default: 'expression',
          options: [
            { value: 'expression', label: 'Expression' },
            { value: 'equals', label: 'Equals' },
            { value: 'not_equals', label: 'Not Equals' },
            { value: 'greater_than', label: 'Greater Than' },
            { value: 'less_than', label: 'Less Than' },
            { value: 'contains', label: 'Contains' },
            { value: 'is_empty', label: 'Is Empty' },
            { value: 'is_not_empty', label: 'Is Not Empty' },
          ],
        },
        {
          id: 'expression',
          type: 'expression',
          label: 'Condition Expression',
          default: '{{value}} > 0',
          help: 'JavaScript expression that evaluates to true/false',
          showIf: { field: 'condition_type', value: 'expression' },
        },
        {
          id: 'compare_value',
          type: 'text',
          label: 'Compare Value',
          default: '',
          showIf: { field: 'condition_type', values: ['equals', 'not_equals', 'greater_than', 'less_than', 'contains'] },
        },
      ],
      
      execution: {
        type: 'logic',
        executor: 'if_executor',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'logic:switch': {
      name: 'Switch',
      description: 'Branch workflow based on multiple conditions',
      category: 'logic',
      icon: '🔀',
      color: '#A855F7',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Input' },
        { id: 'value', type: 'any', label: 'Value to Switch' },
      ],
      outputs: [
        { id: 'case_0', type: 'trigger', label: 'Case 1' },
        { id: 'case_1', type: 'trigger', label: 'Case 2' },
        { id: 'case_2', type: 'trigger', label: 'Case 3' },
        { id: 'default', type: 'trigger', label: 'Default' },
      ],
      
      parameters: [
        {
          id: 'switch_value',
          type: 'expression',
          label: 'Value to Switch On',
          default: '{{value}}',
        },
        {
          id: 'cases',
          type: 'array',
          label: 'Cases',
          itemType: 'object',
          default: [
            { value: 'case1', label: 'Case 1' },
            { value: 'case2', label: 'Case 2' },
          ],
        },
      ],
      
      execution: {
        type: 'logic',
        executor: 'switch_executor',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'logic:loop': {
      name: 'Loop',
      description: 'Iterate over an array of items',
      category: 'logic',
      icon: '🔄',
      color: '#A855F7',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Input' },
        { id: 'items', type: 'array', label: 'Items to Loop' },
      ],
      outputs: [
        { id: 'each', type: 'trigger', label: 'Each Item' },
        { id: 'item', type: 'any', label: 'Current Item' },
        { id: 'index', type: 'number', label: 'Current Index' },
        { id: 'done', type: 'trigger', label: 'Loop Complete' },
        { id: 'results', type: 'array', label: 'All Results' },
      ],
      
      parameters: [
        {
          id: 'items_expression',
          type: 'expression',
          label: 'Items to Loop Over',
          default: '{{items}}',
          help: 'Array expression to iterate',
        },
        {
          id: 'batch_size',
          type: 'number',
          label: 'Batch Size',
          default: 1,
          min: 1,
          max: 100,
          help: 'Process items in batches (1 = sequential)',
        },
        {
          id: 'continue_on_error',
          type: 'checkbox',
          label: 'Continue on Error',
          default: true,
          help: 'Continue loop even if an iteration fails',
        },
      ],
      
      execution: {
        type: 'logic',
        executor: 'loop_executor',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'logic:wait': {
      name: 'Wait',
      description: 'Pause workflow execution for a specified time',
      category: 'logic',
      icon: '⏱️',
      color: '#A855F7',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Input' },
      ],
      outputs: [
        { id: 'trigger', type: 'trigger', label: 'Continue' },
      ],
      
      parameters: [
        {
          id: 'wait_type',
          type: 'select',
          label: 'Wait Type',
          default: 'seconds',
          options: [
            { value: 'seconds', label: 'Fixed Time' },
            { value: 'until', label: 'Until Condition' },
          ],
        },
        {
          id: 'seconds',
          type: 'number',
          label: 'Wait Time (seconds)',
          default: 5,
          min: 1,
          max: 3600,
          showIf: { field: 'wait_type', value: 'seconds' },
        },
        {
          id: 'condition',
          type: 'expression',
          label: 'Wait Until',
          default: '',
          showIf: { field: 'wait_type', value: 'until' },
          help: 'Expression that must become true',
        },
        {
          id: 'timeout',
          type: 'number',
          label: 'Timeout (seconds)',
          default: 300,
          showIf: { field: 'wait_type', value: 'until' },
        },
      ],
      
      execution: {
        type: 'logic',
        executor: 'wait_executor',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'logic:merge': {
      name: 'Merge',
      description: 'Merge multiple workflow branches into one',
      category: 'logic',
      icon: '🔗',
      color: '#A855F7',
      
      inputs: [
        { id: 'input_1', type: 'trigger', label: 'Input 1' },
        { id: 'input_2', type: 'trigger', label: 'Input 2' },
        { id: 'input_3', type: 'trigger', label: 'Input 3' },
      ],
      outputs: [
        { id: 'trigger', type: 'trigger', label: 'Merged' },
        { id: 'data', type: 'array', label: 'All Data' },
      ],
      
      parameters: [
        {
          id: 'mode',
          type: 'select',
          label: 'Merge Mode',
          default: 'wait_all',
          options: [
            { value: 'wait_all', label: 'Wait for All' },
            { value: 'first', label: 'First to Arrive' },
          ],
        },
      ],
      
      execution: {
        type: 'logic',
        executor: 'merge_executor',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    // ============ DATA ============
    'data:set-variable': {
      name: 'Set Variable',
      description: 'Store a value in a workflow variable',
      category: 'data',
      icon: '📝',
      color: '#F59E0B',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Input' },
        { id: 'value', type: 'any', label: 'Value' },
      ],
      outputs: [
        { id: 'trigger', type: 'trigger', label: 'Continue' },
      ],
      
      parameters: [
        {
          id: 'variable_name',
          type: 'text',
          label: 'Variable Name',
          default: 'myVariable',
          required: true,
          help: 'Name to reference this variable (e.g., {{myVariable}})',
        },
        {
          id: 'value_expression',
          type: 'expression',
          label: 'Value',
          default: '{{value}}',
          help: 'Value to store in the variable',
        },
      ],
      
      execution: {
        type: 'data',
        executor: 'set_variable_executor',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'data:debug': {
      name: 'Debug',
      description: 'Inspect data flowing through the workflow',
      category: 'data',
      icon: '🔍',
      color: '#F59E0B',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Input' },
        { id: 'data', type: 'any', label: 'Data to Inspect' },
      ],
      outputs: [
        { id: 'trigger', type: 'trigger', label: 'Continue' },
        { id: 'data', type: 'any', label: 'Pass Through' },
      ],
      
      parameters: [
        {
          id: 'label',
          type: 'text',
          label: 'Debug Label',
          default: 'Debug Point',
          help: 'Label to identify this debug point in logs',
        },
        {
          id: 'log_to_console',
          type: 'checkbox',
          label: 'Log to Console',
          default: true,
        },
        {
          id: 'pause_execution',
          type: 'checkbox',
          label: 'Pause Execution (Test Mode Only)',
          default: false,
        },
      ],
      
      execution: {
        type: 'data',
        executor: 'debug_executor',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },

    'data:transform': {
      name: 'Transform',
      description: 'Transform data using JavaScript expressions',
      category: 'data',
      icon: '🔄',
      color: '#F59E0B',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Input' },
        { id: 'data', type: 'any', label: 'Input Data' },
      ],
      outputs: [
        { id: 'trigger', type: 'trigger', label: 'Continue' },
        { id: 'result', type: 'any', label: 'Transformed Data' },
      ],
      
      parameters: [
        {
          id: 'transform_type',
          type: 'select',
          label: 'Transform Type',
          default: 'expression',
          options: [
            { value: 'expression', label: 'Expression' },
            { value: 'map', label: 'Map Array' },
            { value: 'filter', label: 'Filter Array' },
            { value: 'pick', label: 'Pick Fields' },
          ],
        },
        {
          id: 'expression',
          type: 'code',
          label: 'Transform Expression',
          default: '{{data}}',
          language: 'javascript',
          help: 'JavaScript expression to transform the data',
        },
      ],
      
      execution: {
        type: 'data',
        executor: 'transform_executor',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },
  },
};
