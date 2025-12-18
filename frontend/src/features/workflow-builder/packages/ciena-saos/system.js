/**
 * Ciena SAOS System Nodes
 * 
 * Chassis, configuration save, and running config operations.
 */

import { PLATFORMS, PROTOCOLS } from '../../platforms';

const cienaPlatform = {
  platforms: [PLATFORMS.CIENA_SAOS],
  protocols: [PROTOCOLS.SSH],
  vendor: 'Ciena',
};

export const systemNodes = {
  'ciena:show-chassis': {
    name: 'Show Chassis',
    description: 'Display chassis and hardware information',
    category: 'discover',
    subcategory: 'network',
    ...cienaPlatform,
    icon: '🖥️',
    color: '#0066CC',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'targets', type: 'string[]', label: 'Targets (override)' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'results', type: 'object[]', label: 'All Results' },
      { id: 'chassis', type: 'object[]', label: 'Chassis Data' },
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
    ],
    
    execution: {
      type: 'action',
      executor: 'ciena_ssh',
      context: 'remote_ssh',
      platform: 'ciena-saos-8',
      command_template: 'show chassis',
      requirements: {
        connection: 'ssh',
        credentials: ['ciena_credentials'],
      },
    },
  },

  'ciena:config-save': {
    name: 'Save Configuration',
    description: 'Save running configuration to startup',
    category: 'configure',
    subcategory: 'remote',
    ...cienaPlatform,
    icon: '💾',
    color: '#22C55E',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'targets', type: 'string[]', label: 'Targets (override)' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'results', type: 'object[]', label: 'Results' },
    ],
    
    parameters: [
      {
        id: 'target_type',
        type: 'select',
        label: 'Target Source',
        default: 'ip_list',
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
        id: 'filename',
        type: 'text',
        label: 'Config Filename',
        default: 'startup-config',
        help: 'Name for saved configuration file',
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'ciena_ssh',
      context: 'remote_ssh',
      platform: 'ciena-saos-8',
      command_template: 'configuration save {filename}',
      requirements: {
        connection: 'ssh',
        credentials: ['ciena_credentials'],
      },
    },
  },

  'ciena:show-running-config': {
    name: 'Show Running Config',
    description: 'Display current running configuration',
    category: 'discover',
    subcategory: 'network',
    ...cienaPlatform,
    icon: '📄',
    color: '#0066CC',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'targets', type: 'string[]', label: 'Targets (override)' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'results', type: 'object[]', label: 'All Results' },
      { id: 'config', type: 'string[]', label: 'Configuration' },
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
        id: 'section',
        type: 'select',
        label: 'Config Section',
        default: 'all',
        options: [
          { value: 'all', label: 'Full Configuration' },
          { value: 'port', label: 'Port Configuration' },
          { value: 'vlan', label: 'VLAN Configuration' },
          { value: 'service', label: 'Service Configuration' },
        ],
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'ciena_ssh',
      context: 'remote_ssh',
      platform: 'ciena-saos-8',
      command_template: 'show running-config {section}',
      requirements: {
        connection: 'ssh',
        credentials: ['ciena_credentials'],
      },
    },
  },
};
