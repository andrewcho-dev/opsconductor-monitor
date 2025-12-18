/**
 * NetBox Discovery Nodes
 * 
 * Ping, SNMP, hostname, full discovery, and interface discovery operations.
 */

import { PLATFORMS, PROTOCOLS } from '../../platforms';

const netboxPlatform = {
  platforms: [PLATFORMS.ANY],
  protocols: [PROTOCOLS.NETBOX],
};

export const discoveryNodes = {
  'netbox:discover-ping': {
    name: 'Ping Discovery',
    description: 'Ping hosts and optionally create devices in NetBox',
    category: 'discovery',
    icon: '📡',
    color: '#EC4899',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'targets', type: 'string[]', label: 'Targets (override)' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'results', type: 'object[]', label: 'All Results' },
      { id: 'responding', type: 'string[]', label: 'Responding Hosts' },
      { id: 'created_devices', type: 'object[]', label: 'Created Devices' },
    ],
    
    parameters: [
      {
        id: 'target_type',
        type: 'select',
        label: 'Target Source',
        default: 'ip_list',
        options: [
          { value: 'ip_list', label: 'IP List' },
          { value: 'from_input', label: 'From Previous Node' },
        ],
      },
      {
        id: 'targets',
        type: 'textarea',
        label: 'Target IPs',
        placeholder: '192.168.1.1\n192.168.1.2',
        showIf: { field: 'target_type', value: 'ip_list' },
      },
      {
        id: 'create_devices',
        type: 'checkbox',
        label: 'Create Devices in NetBox',
        default: false,
        help: 'Automatically create devices for responding hosts',
      },
      {
        id: 'site_id',
        type: 'netbox-site-selector',
        label: 'Default Site',
        showIf: { field: 'create_devices', value: true },
      },
      {
        id: 'role_id',
        type: 'netbox-role-selector',
        label: 'Default Role',
        showIf: { field: 'create_devices', value: true },
      },
      {
        id: 'device_type_id',
        type: 'netbox-device-type-selector',
        label: 'Default Device Type',
        showIf: { field: 'create_devices', value: true },
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'discover.ping',
    },
  },

  'netbox:discover-snmp': {
    name: 'SNMP Discovery',
    description: 'Discover device info via SNMP and update NetBox',
    category: 'discovery',
    icon: '📊',
    color: '#EC4899',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'target', type: 'string', label: 'Target IP (override)' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'discovered', type: 'object', label: 'Discovered Info' },
      { id: 'hostname', type: 'string', label: 'Hostname' },
      { id: 'description', type: 'string', label: 'System Description' },
      { id: 'platform', type: 'string', label: 'Detected Platform' },
    ],
    
    parameters: [
      {
        id: 'target',
        type: 'text',
        label: 'Target IP',
        required: true,
      },
      {
        id: 'community',
        type: 'text',
        label: 'SNMP Community',
        default: 'public',
      },
      {
        id: 'version',
        type: 'select',
        label: 'SNMP Version',
        default: '2c',
        options: [
          { value: '1', label: 'v1' },
          { value: '2c', label: 'v2c' },
        ],
      },
      {
        id: 'update_netbox',
        type: 'checkbox',
        label: 'Update NetBox',
        default: true,
        help: 'Create/update device in NetBox with discovered info',
      },
      {
        id: 'site_id',
        type: 'netbox-site-selector',
        label: 'Default Site',
        showIf: { field: 'update_netbox', value: true },
      },
      {
        id: 'role_id',
        type: 'netbox-role-selector',
        label: 'Default Role',
        showIf: { field: 'update_netbox', value: true },
      },
      {
        id: 'device_type_id',
        type: 'netbox-device-type-selector',
        label: 'Default Device Type',
        showIf: { field: 'update_netbox', value: true },
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'discover.snmp',
    },
  },

  'netbox:discover-hostname': {
    name: 'Hostname Discovery',
    description: 'Resolve hostname via DNS and update NetBox',
    category: 'discovery',
    icon: '🏷️',
    color: '#EC4899',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'target', type: 'string', label: 'Target IP (override)' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'hostname', type: 'string', label: 'Resolved Hostname' },
      { id: 'discovered', type: 'object', label: 'Discovery Results' },
    ],
    
    parameters: [
      {
        id: 'target',
        type: 'text',
        label: 'Target IP',
        required: true,
      },
      {
        id: 'update_netbox',
        type: 'checkbox',
        label: 'Update NetBox',
        default: false,
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'discover.hostname',
    },
  },

  'netbox:discover-full': {
    name: 'Full Discovery',
    description: 'Run all discovery methods and create/update device in NetBox',
    category: 'discovery',
    icon: '🔬',
    color: '#EC4899',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'target', type: 'string', label: 'Target IP (override)' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'discovered', type: 'object', label: 'All Discovered Info' },
      { id: 'device', type: 'object', label: 'NetBox Device' },
    ],
    
    parameters: [
      {
        id: 'target',
        type: 'text',
        label: 'Target IP',
        required: true,
      },
      {
        id: 'snmp_community',
        type: 'text',
        label: 'SNMP Community',
        default: 'public',
      },
      {
        id: 'snmp_version',
        type: 'select',
        label: 'SNMP Version',
        default: '2c',
        options: [
          { value: '1', label: 'v1' },
          { value: '2c', label: 'v2c' },
        ],
      },
      {
        id: 'update_netbox',
        type: 'checkbox',
        label: 'Update NetBox',
        default: true,
      },
      {
        id: 'site_id',
        type: 'netbox-site-selector',
        label: 'Default Site',
        showIf: { field: 'update_netbox', value: true },
      },
      {
        id: 'role_id',
        type: 'netbox-role-selector',
        label: 'Default Role',
        showIf: { field: 'update_netbox', value: true },
      },
      {
        id: 'device_type_id',
        type: 'netbox-device-type-selector',
        label: 'Default Device Type',
        showIf: { field: 'update_netbox', value: true },
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'discover.full',
    },
  },

  'netbox:discover-interfaces': {
    name: 'Interface Discovery',
    description: 'Discover interfaces via SNMP and sync to NetBox',
    category: 'discovery',
    icon: '🔌',
    color: '#EC4899',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'target', type: 'string', label: 'Target IP (override)' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'interfaces', type: 'object[]', label: 'Discovered Interfaces' },
      { id: 'synced', type: 'object[]', label: 'Synced to NetBox' },
    ],
    
    parameters: [
      {
        id: 'target',
        type: 'text',
        label: 'Target IP',
        required: true,
      },
      {
        id: 'snmp_community',
        type: 'text',
        label: 'SNMP Community',
        default: 'public',
        required: true,
      },
      {
        id: 'snmp_version',
        type: 'select',
        label: 'SNMP Version',
        default: '2c',
        options: [
          { value: '1', label: 'v1' },
          { value: '2c', label: 'v2c' },
        ],
      },
      {
        id: 'sync_netbox',
        type: 'checkbox',
        label: 'Sync to NetBox',
        default: false,
      },
      {
        id: 'device_name',
        type: 'text',
        label: 'Device Name in NetBox',
        showIf: { field: 'sync_netbox', value: true },
      },
      {
        id: 'interface_type',
        type: 'select',
        label: 'Default Interface Type',
        default: '1000base-t',
        showIf: { field: 'sync_netbox', value: true },
        options: [
          { value: 'virtual', label: 'Virtual' },
          { value: '1000base-t', label: '1000BASE-T' },
          { value: '10gbase-t', label: '10GBASE-T' },
        ],
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'discover.interfaces',
    },
  },
};
