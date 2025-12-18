/**
 * Ciena SAOS Service Nodes
 * 
 * Service and virtual switch show operations.
 */

import { PLATFORMS, PROTOCOLS } from '../../platforms';

const cienaPlatform = {
  platforms: [PLATFORMS.CIENA_SAOS],
  protocols: [PROTOCOLS.SSH],
  vendor: 'Ciena',
};

export const serviceNodes = {
  'ciena:show-service': {
    name: 'Show Service',
    description: 'Display service configuration (EPL, EVPL, etc.)',
    category: 'discover',
    subcategory: 'network',
    ...cienaPlatform,
    icon: '🔧',
    color: '#0066CC',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'targets', type: 'string[]', label: 'Targets (override)' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'results', type: 'object[]', label: 'All Results' },
      { id: 'services', type: 'object[]', label: 'Service Data' },
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
        id: 'service_type',
        type: 'select',
        label: 'Service Type',
        default: 'all',
        options: [
          { value: 'all', label: 'All Services' },
          { value: 'epl', label: 'EPL (Point-to-Point)' },
          { value: 'evpl', label: 'EVPL (Virtual P2P)' },
          { value: 'eplan', label: 'E-LAN (Multipoint)' },
        ],
      },
      {
        id: 'service_name',
        type: 'text',
        label: 'Service Name',
        default: '',
        help: 'Filter by specific service name (optional)',
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'ciena_ssh',
      context: 'remote_ssh',
      platform: 'ciena-saos-8',
      command_template: 'show service {service_type}',
      requirements: {
        connection: 'ssh',
        credentials: ['ciena_credentials'],
      },
    },
  },

  'ciena:show-virtual-switch': {
    name: 'Show Virtual Switch',
    description: 'Display virtual switch configuration',
    category: 'discover',
    subcategory: 'network',
    ...cienaPlatform,
    icon: '🔀',
    color: '#0066CC',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'targets', type: 'string[]', label: 'Targets (override)' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'results', type: 'object[]', label: 'All Results' },
      { id: 'vs_data', type: 'object[]', label: 'Virtual Switch Data' },
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
        id: 'vs_name',
        type: 'text',
        label: 'Virtual Switch Name',
        default: '',
        help: 'Filter by specific VS name (optional)',
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'ciena_ssh',
      context: 'remote_ssh',
      platform: 'ciena-saos-8',
      command_template: 'show virtual-switch {vs_name}',
      requirements: {
        connection: 'ssh',
        credentials: ['ciena_credentials'],
      },
    },
  },
};
