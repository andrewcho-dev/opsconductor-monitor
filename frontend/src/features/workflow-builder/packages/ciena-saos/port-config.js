/**
 * Ciena SAOS Port Configuration Nodes
 * 
 * Port enable, disable, and description configuration.
 */

import { PLATFORMS, PROTOCOLS } from '../../platforms';

const cienaPlatform = {
  platforms: [PLATFORMS.CIENA_SAOS],
  protocols: [PROTOCOLS.SSH],
  vendor: 'Ciena',
};

export const portConfigNodes = {
  'ciena:port-enable': {
    name: 'Enable Port',
    description: 'Enable/bring up a port on Ciena SAOS switch',
    category: 'configure',
    subcategory: 'remote',
    ...cienaPlatform,
    icon: '✅',
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
        id: 'port',
        type: 'text',
        label: 'Port',
        default: '1/1',
        required: true,
        help: 'Port to enable (e.g., 1/1, 2/24)',
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'ciena_ssh',
      context: 'remote_ssh',
      platform: 'ciena-saos-8',
      command_template: 'port enable port {port}',
      requirements: {
        connection: 'ssh',
        credentials: ['ciena_credentials'],
      },
    },
  },

  'ciena:port-disable': {
    name: 'Disable Port',
    description: 'Disable/shutdown a port on Ciena SAOS switch',
    category: 'configure',
    subcategory: 'remote',
    ...cienaPlatform,
    icon: '🚫',
    color: '#EF4444',
    
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
        id: 'port',
        type: 'text',
        label: 'Port',
        default: '1/1',
        required: true,
        help: 'Port to disable (e.g., 1/1, 2/24)',
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'ciena_ssh',
      context: 'remote_ssh',
      platform: 'ciena-saos-8',
      command_template: 'port disable port {port}',
      requirements: {
        connection: 'ssh',
        credentials: ['ciena_credentials'],
      },
    },
  },

  'ciena:port-set-description': {
    name: 'Set Port Description',
    description: 'Set the description/alias for a port',
    category: 'configure',
    subcategory: 'remote',
    ...cienaPlatform,
    icon: '🏷️',
    color: '#0066CC',
    
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
        id: 'port',
        type: 'text',
        label: 'Port',
        default: '1/1',
        required: true,
      },
      {
        id: 'description',
        type: 'text',
        label: 'Description',
        default: '',
        required: true,
        help: 'Port description/alias',
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'ciena_ssh',
      context: 'remote_ssh',
      platform: 'ciena-saos-8',
      command_template: 'port set port {port} description "{description}"',
      requirements: {
        connection: 'ssh',
        credentials: ['ciena_credentials'],
      },
    },
  },
};
