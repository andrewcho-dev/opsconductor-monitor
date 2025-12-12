/**
 * Ciena SAOS Package
 * 
 * Nodes for Ciena SAOS switch operations:
 * - Show Interface
 * - Show Optics
 * - Show LLDP Neighbors
 * - Show Alarms
 * - Configuration commands
 */

export default {
  id: 'ciena-saos',
  name: 'Ciena SAOS',
  description: 'Ciena SAOS 8.x switch commands for optical network management',
  version: '1.0.0',
  icon: '🔷',
  color: '#0066CC',
  vendor: 'Ciena',
  
  nodes: {
    'ciena:show-interface': {
      name: 'Show Interface',
      description: 'Display interface status and statistics on Ciena SAOS switches',
      category: 'query',
      icon: '🔌',
      color: '#0066CC',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'targets', type: 'string[]', label: 'Targets (override)' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'results', type: 'object[]', label: 'All Results' },
        { id: 'interfaces', type: 'object[]', label: 'Interface Data' },
      ],
      
      parameters: [
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
          label: 'Target IPs',
          default: '',
          showIf: { field: 'target_type', value: 'ip_list' },
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
        {
          id: 'interface_filter',
          type: 'select',
          label: 'Interface Filter',
          default: 'all',
          options: [
            { value: 'all', label: 'All Interfaces' },
            { value: 'specific', label: 'Specific Interface' },
            { value: 'ethernet', label: 'Ethernet Only' },
            { value: 'optical', label: 'Optical Only' },
          ],
        },
        {
          id: 'interface_name',
          type: 'text',
          label: 'Interface Name',
          default: '1/1',
          showIf: { field: 'interface_filter', value: 'specific' },
          help: 'Format: slot/port (e.g., 1/1, 2/24)',
        },
        {
          id: 'include_stats',
          type: 'checkbox',
          label: 'Include Statistics',
          default: true,
        },
      ],
      
      advanced: [
        {
          id: 'cli_port',
          type: 'number',
          label: 'CLI Port',
          default: 22,
          min: 1,
          max: 65535,
        },
        {
          id: 'timeout',
          type: 'number',
          label: 'Timeout (seconds)',
          default: 30,
          min: 1,
          max: 300,
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'ciena_ssh',
        platform: 'ciena-saos-8',
        command_template: 'show interface {interface}',
      },
    },

    'ciena:show-optics': {
      name: 'Show Optics',
      description: 'Display optical power levels and SFP status on Ciena SAOS switches',
      category: 'query',
      icon: '💡',
      color: '#0066CC',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'targets', type: 'string[]', label: 'Targets (override)' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'results', type: 'object[]', label: 'All Results' },
        { id: 'optics', type: 'object[]', label: 'Optical Data' },
        { id: 'alerts', type: 'object[]', label: 'Power Alerts' },
      ],
      
      parameters: [
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
          label: 'Target IPs',
          default: '',
          showIf: { field: 'target_type', value: 'ip_list' },
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
        {
          id: 'interface_filter',
          type: 'select',
          label: 'Interface Filter',
          default: 'all',
          options: [
            { value: 'all', label: 'All Interfaces' },
            { value: 'specific', label: 'Specific Interface' },
          ],
        },
        {
          id: 'interface_name',
          type: 'text',
          label: 'Interface Name',
          default: '',
          showIf: { field: 'interface_filter', value: 'specific' },
        },
        {
          id: 'alert_thresholds',
          type: 'checkbox',
          label: 'Check Alert Thresholds',
          default: true,
          help: 'Flag interfaces with power outside normal range',
        },
        {
          id: 'tx_low_threshold',
          type: 'number',
          label: 'TX Low Threshold (dBm)',
          default: -10,
          showIf: { field: 'alert_thresholds', value: true },
        },
        {
          id: 'tx_high_threshold',
          type: 'number',
          label: 'TX High Threshold (dBm)',
          default: 3,
          showIf: { field: 'alert_thresholds', value: true },
        },
        {
          id: 'rx_low_threshold',
          type: 'number',
          label: 'RX Low Threshold (dBm)',
          default: -25,
          showIf: { field: 'alert_thresholds', value: true },
        },
        {
          id: 'rx_high_threshold',
          type: 'number',
          label: 'RX High Threshold (dBm)',
          default: 0,
          showIf: { field: 'alert_thresholds', value: true },
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'ciena_ssh',
        platform: 'ciena-saos-8',
        command_template: 'show optics {interface}',
      },
    },

    'ciena:show-lldp': {
      name: 'Show LLDP Neighbors',
      description: 'Display LLDP neighbor information for network topology discovery',
      category: 'discovery',
      icon: '🔗',
      color: '#0066CC',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'targets', type: 'string[]', label: 'Targets (override)' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'results', type: 'object[]', label: 'All Results' },
        { id: 'neighbors', type: 'object[]', label: 'LLDP Neighbors' },
        { id: 'links', type: 'object[]', label: 'Network Links' },
      ],
      
      parameters: [
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
          label: 'Target IPs',
          default: '',
          showIf: { field: 'target_type', value: 'ip_list' },
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
        {
          id: 'detail_level',
          type: 'select',
          label: 'Detail Level',
          default: 'summary',
          options: [
            { value: 'summary', label: 'Summary' },
            { value: 'detail', label: 'Detailed' },
          ],
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'ciena_ssh',
        platform: 'ciena-saos-8',
        command_template: 'show lldp neighbors {detail}',
      },
    },

    'ciena:show-alarms': {
      name: 'Show Alarms',
      description: 'Display active and historical alarms on Ciena SAOS switches',
      category: 'query',
      icon: '🚨',
      color: '#EF4444',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'targets', type: 'string[]', label: 'Targets (override)' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'results', type: 'object[]', label: 'All Results' },
        { id: 'alarms', type: 'object[]', label: 'Active Alarms' },
        { id: 'critical', type: 'object[]', label: 'Critical Alarms' },
        { id: 'major', type: 'object[]', label: 'Major Alarms' },
      ],
      
      parameters: [
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
          label: 'Target IPs',
          default: '',
          showIf: { field: 'target_type', value: 'ip_list' },
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
        {
          id: 'severity_filter',
          type: 'select',
          label: 'Severity Filter',
          default: 'all',
          options: [
            { value: 'all', label: 'All Severities' },
            { value: 'critical', label: 'Critical Only' },
            { value: 'major', label: 'Major and Above' },
            { value: 'minor', label: 'Minor and Above' },
          ],
        },
        {
          id: 'include_cleared',
          type: 'checkbox',
          label: 'Include Cleared Alarms',
          default: false,
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'ciena_ssh',
        platform: 'ciena-saos-8',
        command_template: 'show alarms {severity}',
      },
    },

    'ciena:show-version': {
      name: 'Show Version',
      description: 'Display software version and hardware information',
      category: 'query',
      icon: 'ℹ️',
      color: '#0066CC',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'targets', type: 'string[]', label: 'Targets (override)' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'results', type: 'object[]', label: 'All Results' },
        { id: 'versions', type: 'object[]', label: 'Version Info' },
      ],
      
      parameters: [
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
          label: 'Target IPs',
          default: '',
          showIf: { field: 'target_type', value: 'ip_list' },
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
      ],
      
      execution: {
        type: 'action',
        executor: 'ciena_ssh',
        platform: 'ciena-saos-8',
        command_template: 'show version',
      },
    },

    'ciena:custom-command': {
      name: 'Custom SAOS Command',
      description: 'Execute a custom CLI command on Ciena SAOS switches',
      category: 'query',
      icon: '⌨️',
      color: '#0066CC',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'targets', type: 'string[]', label: 'Targets (override)' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'results', type: 'object[]', label: 'All Results' },
        { id: 'output', type: 'string[]', label: 'Command Output' },
      ],
      
      parameters: [
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
          label: 'Target IPs',
          default: '',
          showIf: { field: 'target_type', value: 'ip_list' },
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
        {
          id: 'command',
          type: 'textarea',
          label: 'Command',
          default: '',
          required: true,
          placeholder: 'show interface all',
          help: 'SAOS CLI command to execute',
        },
        {
          id: 'expect_prompt',
          type: 'text',
          label: 'Expect Prompt',
          default: '>',
          help: 'CLI prompt to wait for',
        },
        {
          id: 'timeout',
          type: 'number',
          label: 'Timeout (seconds)',
          default: 30,
          min: 1,
          max: 300,
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'ciena_ssh',
        platform: 'ciena-saos-8',
      },
    },
  },
};
