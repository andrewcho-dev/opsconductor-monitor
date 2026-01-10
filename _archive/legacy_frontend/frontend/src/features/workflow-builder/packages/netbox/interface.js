/**
 * NetBox Interface Management Nodes
 * 
 * Interface create, assign IP, and list operations.
 */

import { PLATFORMS, PROTOCOLS } from '../../platforms';

const netboxPlatform = {
  platforms: [PLATFORMS.ANY],
  protocols: [PROTOCOLS.NETBOX],
};

export const interfaceNodes = {
  'netbox:interface-create': {
    name: 'Create Interface',
    description: 'Create an interface on a device',
    category: 'configure',
    subcategory: 'netbox',
    ...netboxPlatform,
    icon: '🔌',
    color: '#10B981',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'device_id', type: 'number', label: 'Device ID (override)' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'interface', type: 'object', label: 'Created Interface' },
      { id: 'interface_id', type: 'number', label: 'Interface ID' },
    ],
    
    parameters: [
      {
        id: 'device_name',
        type: 'text',
        label: 'Device Name',
        help: 'Name of device to add interface to',
      },
      {
        id: 'name',
        type: 'text',
        label: 'Interface Name',
        default: 'eth0',
        required: true,
      },
      {
        id: 'type',
        type: 'select',
        label: 'Interface Type',
        default: '1000base-t',
        options: [
          { value: 'virtual', label: 'Virtual' },
          { value: '100base-tx', label: '100BASE-TX (10/100ME)' },
          { value: '1000base-t', label: '1000BASE-T (1GE)' },
          { value: '10gbase-t', label: '10GBASE-T (10GE)' },
          { value: '25gbase-x-sfp28', label: 'SFP28 (25GE)' },
          { value: '40gbase-x-qsfpp', label: 'QSFP+ (40GE)' },
          { value: '100gbase-x-qsfp28', label: 'QSFP28 (100GE)' },
          { value: 'lag', label: 'Link Aggregation Group (LAG)' },
        ],
      },
      {
        id: 'enabled',
        type: 'checkbox',
        label: 'Enabled',
        default: true,
      },
      {
        id: 'mac_address',
        type: 'text',
        label: 'MAC Address',
        placeholder: 'AA:BB:CC:DD:EE:FF',
      },
      {
        id: 'description',
        type: 'text',
        label: 'Description',
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'interface.create',
    },
  },

  'netbox:interface-assign-ip': {
    name: 'Assign IP to Interface',
    description: 'Assign an IP address to a device interface',
    category: 'configure',
    subcategory: 'netbox',
    ...netboxPlatform,
    icon: '🔗',
    color: '#10B981',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'interface_id', type: 'number', label: 'Interface ID (override)' },
      { id: 'ip_address', type: 'string', label: 'IP Address (override)' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'ip', type: 'object', label: 'IP Address Record' },
    ],
    
    parameters: [
      {
        id: 'interface_id',
        type: 'number',
        label: 'Interface ID',
        required: true,
      },
      {
        id: 'ip_address',
        type: 'text',
        label: 'IP Address',
        required: true,
        placeholder: '192.168.1.1/24',
        help: 'IP address with prefix length',
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'interface.assign_ip',
    },
  },

  'netbox:interface-list': {
    name: 'List Interfaces',
    description: 'List interfaces for a device',
    category: 'discover',
    subcategory: 'inventory',
    ...netboxPlatform,
    icon: '🔌',
    color: '#10B981',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'device_id', type: 'number', label: 'Device ID (override)' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'interfaces', type: 'object[]', label: 'Interfaces' },
    ],
    
    parameters: [
      {
        id: 'device_name',
        type: 'text',
        label: 'Device Name',
      },
      {
        id: 'device_id',
        type: 'number',
        label: 'Device ID',
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'interface.list',
    },
  },
};
