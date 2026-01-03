/**
 * Ciena SAOS VLAN Nodes
 * 
 * VLAN show, create, and port assignment operations.
 */

import { PLATFORMS, PROTOCOLS } from '../../platforms';

const cienaPlatform = {
  platforms: [PLATFORMS.CIENA_SAOS],
  protocols: [PROTOCOLS.SSH],
  vendor: 'Ciena',
};

export const vlanNodes = {
  'ciena:show-vlan': {
    name: 'Show VLAN',
    description: 'Display VLAN configuration and membership',
    category: 'discover',
    subcategory: 'network',
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
      { id: 'results', type: 'object[]', label: 'All Results' },
      { id: 'vlans', type: 'object[]', label: 'VLAN Data' },
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
        id: 'vlan_filter',
        type: 'select',
        label: 'VLAN Filter',
        default: 'all',
        options: [
          { value: 'all', label: 'All VLANs' },
          { value: 'specific', label: 'Specific VLAN' },
        ],
      },
      {
        id: 'vlan_id',
        type: 'number',
        label: 'VLAN ID',
        default: 1,
        min: 1,
        max: 4094,
        showIf: { field: 'vlan_filter', value: 'specific' },
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'ciena_ssh',
      context: 'remote_ssh',
      platform: 'ciena-saos-8',
      command_template: 'show vlan {vlan}',
      requirements: {
        connection: 'ssh',
        credentials: ['ciena_credentials'],
      },
    },
  },

  'ciena:vlan-create': {
    name: 'Create VLAN',
    description: 'Create a new VLAN on Ciena SAOS switch',
    category: 'configure',
    subcategory: 'remote',
    ...cienaPlatform,
    icon: '➕',
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
        id: 'vlan_id',
        type: 'number',
        label: 'VLAN ID',
        default: 100,
        required: true,
        min: 1,
        max: 4094,
      },
      {
        id: 'vlan_name',
        type: 'text',
        label: 'VLAN Name',
        default: '',
        help: 'Optional name for the VLAN',
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'ciena_ssh',
      context: 'remote_ssh',
      platform: 'ciena-saos-8',
      command_template: 'vlan create vlan {vlan_id} name {vlan_name}',
      requirements: {
        connection: 'ssh',
        credentials: ['ciena_credentials'],
      },
    },
  },

  'ciena:vlan-add-port': {
    name: 'Add Port to VLAN',
    description: 'Add a port to a VLAN (tagged or untagged)',
    category: 'configure',
    subcategory: 'remote',
    ...cienaPlatform,
    icon: '🔗',
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
        id: 'vlan_id',
        type: 'number',
        label: 'VLAN ID',
        default: 100,
        required: true,
        min: 1,
        max: 4094,
      },
      {
        id: 'port',
        type: 'text',
        label: 'Port',
        default: '1/1',
        required: true,
      },
      {
        id: 'tag_mode',
        type: 'select',
        label: 'Tag Mode',
        default: 'tagged',
        options: [
          { value: 'tagged', label: 'Tagged' },
          { value: 'untagged', label: 'Untagged' },
        ],
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'ciena_ssh',
      context: 'remote_ssh',
      platform: 'ciena-saos-8',
      command_template: 'vlan add vlan {vlan_id} port {port} {tag_mode}',
      requirements: {
        connection: 'ssh',
        credentials: ['ciena_credentials'],
      },
    },
  },
};
