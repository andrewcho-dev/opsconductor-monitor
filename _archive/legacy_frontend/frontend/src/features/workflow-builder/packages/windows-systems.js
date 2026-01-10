/**
 * Windows Systems Package
 * 
 * Nodes for Windows system management via WinRM:
 * - PowerShell execution
 * - CMD execution
 * - Service management
 * - Process management
 * - System information
 * - Event logs
 * - Disk/network info
 * - Reboot/shutdown
 */

import { PLATFORMS, PROTOCOLS } from '../platforms';

// Common target parameters used by all nodes
const targetParams = [
  {
    id: 'target_type',
    type: 'select',
    label: 'Target Source',
    default: 'device_group',
    options: [
      { value: 'ip_list', label: 'IP List' },
      { value: 'device_group', label: 'Device Group' },
      { value: 'from_input', label: 'From Previous Node' },
    ],
  },
  {
    id: 'ip_list',
    type: 'textarea',
    label: 'Windows Hosts',
    default: '',
    showIf: { field: 'target_type', value: 'ip_list' },
    help: 'One IP or hostname per line',
  },
  {
    id: 'device_group',
    type: 'device-group-selector',
    label: 'Device Group',
    default: '',
    showIf: { field: 'target_type', value: 'device_group' },
  },
  {
    id: 'input_expression',
    type: 'expression',
    label: 'Targets Expression',
    default: '{{targets}}',
    showIf: { field: 'target_type', value: 'from_input' },
  },
];

// Common inputs/outputs
const standardInputs = [
  { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
  { id: 'targets', type: 'string[]', label: 'Targets (override)' },
];

const standardOutputs = [
  { id: 'success', type: 'trigger', label: 'On Success' },
  { id: 'failure', type: 'trigger', label: 'On Failure' },
  { id: 'results', type: 'object[]', label: 'Results' },
];

const advancedTimeout = [
  { id: 'timeout', type: 'number', label: 'Timeout (seconds)', default: 60, min: 10, max: 600 },
];

// Base execution config for WinRM
const baseExecution = {
  context: 'remote_winrm',
};

// Common platform config for all Windows nodes
const windowsPlatform = {
  platforms: [PLATFORMS.WINDOWS],
  protocols: [PROTOCOLS.WINRM],
};

export default {
  id: 'windows-systems',
  name: 'Windows Systems',
  description: 'Windows system management via WinRM (PowerShell, services, processes, etc.)',
  version: '1.0.0',
  icon: '🪟',
  color: '#0078D4', // Windows blue
  vendor: 'Microsoft',
  
  nodes: {
    // =========================================================================
    // COMMAND EXECUTION
    // =========================================================================
    
    'windows:powershell': {
      name: 'Run PowerShell',
      description: 'Execute a PowerShell script on Windows targets',
      category: 'configure',
      subcategory: 'remote',
      icon: '⚡',
      color: '#0078D4',
      ...windowsPlatform,
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'output', type: 'string', label: 'Script Output' }],
      parameters: [
        ...targetParams,
        {
          id: 'script',
          type: 'code',
          label: 'PowerShell Script',
          default: 'Get-Date',
          language: 'powershell',
          help: 'PowerShell commands to execute',
        },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'action', executor: 'winrm', api_endpoint: '/automation/v1/winrm/execute/powershell' },
    },

    'windows:cmd': {
      name: 'Run CMD Command',
      description: 'Execute a CMD command on Windows targets',
      category: 'configure',
      subcategory: 'remote',
      icon: '💻',
      color: '#0078D4',
      ...windowsPlatform,
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'output', type: 'string', label: 'Command Output' }],
      parameters: [
        ...targetParams,
        {
          id: 'command',
          type: 'text',
          label: 'Command',
          default: 'hostname',
          help: 'CMD command to execute',
        },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'action', executor: 'winrm', api_endpoint: '/automation/v1/winrm/execute/cmd' },
    },

    // =========================================================================
    // SYSTEM INFORMATION
    // =========================================================================

    'windows:system-info': {
      name: 'Get System Info',
      description: 'Retrieve Windows system information (OS, hardware, uptime)',
      category: 'query',
      subcategory: 'discover',
      ...windowsPlatform,
      icon: 'ℹ️',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'system_info', type: 'object[]', label: 'System Info' }],
      parameters: targetParams,
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'winrm', api_endpoint: '/automation/v1/winrm/system-info' },
    },

    'windows:disk-space': {
      name: 'Get Disk Space',
      description: 'Retrieve disk space information from Windows targets',
      category: 'query',
      subcategory: 'discover',
      ...windowsPlatform,
      icon: '💾',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'disks', type: 'object[]', label: 'Disk Info' }],
      parameters: targetParams,
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'winrm', api_endpoint: '/automation/v1/winrm/disk-space' },
    },

    'windows:network-config': {
      name: 'Get Network Config',
      description: 'Retrieve network configuration from Windows targets',
      category: 'query',
      subcategory: 'discover',
      ...windowsPlatform,
      icon: '🌐',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'network_config', type: 'object[]', label: 'Network Config' }],
      parameters: targetParams,
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'winrm', api_endpoint: '/automation/v1/winrm/network-config' },
    },

    // =========================================================================
    // SERVICE MANAGEMENT
    // =========================================================================

    'windows:get-services': {
      name: 'Get Services',
      description: 'List Windows services and their status',
      category: 'query',
      subcategory: 'discover',
      ...windowsPlatform,
      icon: '⚙️',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'services', type: 'object[]', label: 'Services' }],
      parameters: [
        ...targetParams,
        {
          id: 'service_name',
          type: 'text',
          label: 'Service Name Filter',
          default: '',
          help: 'Filter by service name (supports wildcards like *sql*)',
        },
        {
          id: 'status_filter',
          type: 'select',
          label: 'Status Filter',
          default: '',
          options: [
            { value: '', label: 'All' },
            { value: 'Running', label: 'Running' },
            { value: 'Stopped', label: 'Stopped' },
          ],
        },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'winrm', api_endpoint: '/automation/v1/winrm/services' },
    },

    'windows:start-service': {
      name: 'Start Service',
      description: 'Start a Windows service',
      category: 'configure',
      subcategory: 'remote',
      ...windowsPlatform,
      icon: '▶️',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: standardOutputs,
      parameters: [
        ...targetParams,
        {
          id: 'service_name',
          type: 'text',
          label: 'Service Name',
          default: '',
          help: 'Name of the service to start',
        },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'action', executor: 'winrm', api_endpoint: '/automation/v1/winrm/services/manage', api_params: { action: 'start' } },
    },

    'windows:stop-service': {
      name: 'Stop Service',
      description: 'Stop a Windows service',
      category: 'configure',
      subcategory: 'remote',
      ...windowsPlatform,
      icon: '⏹️',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: standardOutputs,
      parameters: [
        ...targetParams,
        {
          id: 'service_name',
          type: 'text',
          label: 'Service Name',
          default: '',
          help: 'Name of the service to stop',
        },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'action', executor: 'winrm', api_endpoint: '/automation/v1/winrm/services/manage', api_params: { action: 'stop' } },
    },

    'windows:restart-service': {
      name: 'Restart Service',
      description: 'Restart a Windows service',
      category: 'configure',
      subcategory: 'remote',
      ...windowsPlatform,
      icon: '🔄',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: standardOutputs,
      parameters: [
        ...targetParams,
        {
          id: 'service_name',
          type: 'text',
          label: 'Service Name',
          default: '',
          help: 'Name of the service to restart',
        },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'action', executor: 'winrm', api_endpoint: '/automation/v1/winrm/services/manage', api_params: { action: 'restart' } },
    },

    // =========================================================================
    // PROCESS MANAGEMENT
    // =========================================================================

    'windows:get-processes': {
      name: 'Get Processes',
      description: 'List running processes on Windows targets',
      category: 'query',
      subcategory: 'discover',
      ...windowsPlatform,
      icon: '📊',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'processes', type: 'object[]', label: 'Processes' }],
      parameters: [
        ...targetParams,
        {
          id: 'process_name',
          type: 'text',
          label: 'Process Name Filter',
          default: '',
          help: 'Filter by process name (e.g., chrome, sqlservr)',
        },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'winrm', api_endpoint: '/automation/v1/winrm/processes' },
    },

    'windows:stop-process': {
      name: 'Stop Process',
      description: 'Terminate a running process on Windows targets',
      category: 'configure',
      subcategory: 'remote',
      ...windowsPlatform,
      icon: '🛑',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: standardOutputs,
      parameters: [
        ...targetParams,
        {
          id: 'process_name',
          type: 'text',
          label: 'Process Name',
          default: '',
          help: 'Name of the process to stop',
        },
        {
          id: 'force',
          type: 'checkbox',
          label: 'Force Kill',
          default: false,
          help: 'Force terminate the process',
        },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'action', executor: 'winrm' },
    },

    // =========================================================================
    // EVENT LOGS
    // =========================================================================

    'windows:event-log': {
      name: 'Get Event Log',
      description: 'Retrieve Windows Event Log entries',
      category: 'query',
      subcategory: 'discover',
      ...windowsPlatform,
      icon: '📜',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'events', type: 'object[]', label: 'Event Log' }],
      parameters: [
        ...targetParams,
        {
          id: 'log_name',
          type: 'select',
          label: 'Log Name',
          default: 'System',
          options: [
            { value: 'System', label: 'System' },
            { value: 'Application', label: 'Application' },
            { value: 'Security', label: 'Security' },
            { value: 'Setup', label: 'Setup' },
          ],
        },
        {
          id: 'entry_type',
          type: 'select',
          label: 'Entry Type',
          default: '',
          options: [
            { value: '', label: 'All' },
            { value: 'Error', label: 'Error' },
            { value: 'Warning', label: 'Warning' },
            { value: 'Information', label: 'Information' },
          ],
        },
        {
          id: 'newest',
          type: 'number',
          label: 'Number of Entries',
          default: 50,
          min: 1,
          max: 1000,
        },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'winrm', api_endpoint: '/automation/v1/winrm/event-log' },
    },

    // =========================================================================
    // INSTALLED SOFTWARE
    // =========================================================================

    'windows:installed-software': {
      name: 'Get Installed Software',
      description: 'List installed software on Windows targets',
      category: 'query',
      subcategory: 'discover',
      ...windowsPlatform,
      icon: '📦',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'software', type: 'object[]', label: 'Installed Software' }],
      parameters: [
        ...targetParams,
        {
          id: 'name_filter',
          type: 'text',
          label: 'Name Filter',
          default: '',
          help: 'Filter by software name (supports wildcards)',
        },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'winrm' },
    },

    // =========================================================================
    // WINDOWS UPDATES
    // =========================================================================

    'windows:pending-updates': {
      name: 'Get Pending Updates',
      description: 'List pending Windows updates',
      category: 'query',
      subcategory: 'discover',
      ...windowsPlatform,
      icon: '🔄',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'updates', type: 'object[]', label: 'Pending Updates' }],
      parameters: targetParams,
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'winrm' },
    },

    'windows:update-history': {
      name: 'Get Update History',
      description: 'Retrieve Windows update history',
      category: 'query',
      subcategory: 'discover',
      ...windowsPlatform,
      icon: '📋',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'history', type: 'object[]', label: 'Update History' }],
      parameters: [
        ...targetParams,
        {
          id: 'max_results',
          type: 'number',
          label: 'Max Results',
          default: 50,
          min: 1,
          max: 500,
        },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'winrm' },
    },

    // =========================================================================
    // USER MANAGEMENT
    // =========================================================================

    'windows:local-users': {
      name: 'Get Local Users',
      description: 'List local user accounts on Windows targets',
      category: 'query',
      subcategory: 'discover',
      ...windowsPlatform,
      icon: '👤',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'users', type: 'object[]', label: 'Local Users' }],
      parameters: targetParams,
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'winrm' },
    },

    'windows:local-groups': {
      name: 'Get Local Groups',
      description: 'List local groups on Windows targets',
      category: 'query',
      subcategory: 'discover',
      ...windowsPlatform,
      icon: '👥',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'groups', type: 'object[]', label: 'Local Groups' }],
      parameters: targetParams,
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'winrm' },
    },

    // =========================================================================
    // FILE OPERATIONS
    // =========================================================================

    'windows:file-exists': {
      name: 'Check File Exists',
      description: 'Check if a file or directory exists on Windows targets',
      category: 'query',
      subcategory: 'discover',
      ...windowsPlatform,
      icon: '📄',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'exists', type: 'boolean', label: 'Exists' }],
      parameters: [
        ...targetParams,
        {
          id: 'path',
          type: 'text',
          label: 'File Path',
          default: 'C:\\Windows\\System32\\config\\system',
          help: 'Full path to the file or directory',
        },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'winrm' },
    },

    'windows:get-file-content': {
      name: 'Get File Content',
      description: 'Read the contents of a file on Windows targets',
      category: 'query',
      subcategory: 'discover',
      ...windowsPlatform,
      icon: '📖',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'content', type: 'string', label: 'File Content' }],
      parameters: [
        ...targetParams,
        {
          id: 'path',
          type: 'text',
          label: 'File Path',
          default: '',
          help: 'Full path to the file',
        },
        {
          id: 'encoding',
          type: 'select',
          label: 'Encoding',
          default: 'UTF8',
          options: [
            { value: 'UTF8', label: 'UTF-8' },
            { value: 'ASCII', label: 'ASCII' },
            { value: 'Unicode', label: 'Unicode' },
          ],
        },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'winrm' },
    },

    'windows:list-directory': {
      name: 'List Directory',
      description: 'List files and folders in a directory on Windows targets',
      category: 'query',
      subcategory: 'discover',
      ...windowsPlatform,
      icon: '📁',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'items', type: 'object[]', label: 'Directory Items' }],
      parameters: [
        ...targetParams,
        {
          id: 'path',
          type: 'text',
          label: 'Directory Path',
          default: 'C:\\',
          help: 'Full path to the directory',
        },
        {
          id: 'recurse',
          type: 'checkbox',
          label: 'Include Subdirectories',
          default: false,
        },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'winrm' },
    },

    // =========================================================================
    // SYSTEM OPERATIONS
    // =========================================================================

    'windows:reboot': {
      name: 'Reboot System',
      description: 'Reboot a Windows system',
      category: 'configure',
      subcategory: 'remote',
      ...windowsPlatform,
      icon: '🔄',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: standardOutputs,
      parameters: [
        ...targetParams,
        {
          id: 'confirm',
          type: 'checkbox',
          label: 'Confirm Reboot',
          default: false,
          help: 'Must be checked to execute reboot',
        },
        {
          id: 'force',
          type: 'checkbox',
          label: 'Force (ignore logged-in users)',
          default: false,
        },
        {
          id: 'delay_seconds',
          type: 'number',
          label: 'Delay (seconds)',
          default: 0,
          min: 0,
          max: 3600,
          help: 'Delay before reboot (0 = immediate)',
        },
        {
          id: 'wait_for_recovery',
          type: 'checkbox',
          label: 'Wait for Recovery',
          default: true,
          help: 'Wait for system to come back online',
        },
      ],
      advanced: [
        { id: 'timeout', type: 'number', label: 'Timeout (seconds)', default: 300, min: 60, max: 1800 },
      ],
      execution: { ...baseExecution, type: 'action', executor: 'winrm', api_endpoint: '/automation/v1/winrm/reboot' },
    },

    'windows:shutdown': {
      name: 'Shutdown System',
      description: 'Shutdown a Windows system',
      category: 'configure',
      subcategory: 'remote',
      ...windowsPlatform,
      icon: '⏻',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: standardOutputs,
      parameters: [
        ...targetParams,
        {
          id: 'confirm',
          type: 'checkbox',
          label: 'Confirm Shutdown',
          default: false,
          help: 'Must be checked to execute shutdown',
        },
        {
          id: 'force',
          type: 'checkbox',
          label: 'Force (ignore logged-in users)',
          default: false,
        },
        {
          id: 'delay_seconds',
          type: 'number',
          label: 'Delay (seconds)',
          default: 0,
          min: 0,
          max: 3600,
        },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'action', executor: 'winrm', api_endpoint: '/automation/v1/winrm/shutdown' },
    },

    // =========================================================================
    // CONNECTION TEST
    // =========================================================================

    'windows:test-connection': {
      name: 'Test WinRM Connection',
      description: 'Test WinRM connectivity to Windows targets',
      category: 'query',
      subcategory: 'discover',
      ...windowsPlatform,
      icon: '🔌',
      color: '#0078D4',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'hostname', type: 'string', label: 'Hostname' }],
      parameters: targetParams,
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'winrm', api_endpoint: '/automation/v1/winrm/test' },
    },
  },
};
