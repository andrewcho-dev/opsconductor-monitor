/**
 * NetBox IP Address Management Nodes
 * 
 * IP address create and primary assignment operations.
 */

import { PLATFORMS, PROTOCOLS } from '../../platforms';

const netboxPlatform = {
  platforms: [PLATFORMS.ANY],
  protocols: [PROTOCOLS.NETBOX],
};

export const ipNodes = {
  'netbox:ip-create': {
    name: 'Create IP Address',
    description: 'Create an IP address in NetBox IPAM',
    category: 'configure',
    subcategory: 'netbox',
    ...netboxPlatform,
    icon: '🌐',
    color: '#F59E0B',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'ip', type: 'object', label: 'Created IP' },
      { id: 'ip_id', type: 'number', label: 'IP ID' },
    ],
    
    parameters: [
      {
        id: 'address',
        type: 'text',
        label: 'IP Address',
        required: true,
        placeholder: '192.168.1.1/24',
        help: 'IP address with prefix length',
      },
      {
        id: 'status',
        type: 'select',
        label: 'Status',
        default: 'active',
        options: [
          { value: 'active', label: 'Active' },
          { value: 'reserved', label: 'Reserved' },
          { value: 'deprecated', label: 'Deprecated' },
          { value: 'dhcp', label: 'DHCP' },
          { value: 'slaac', label: 'SLAAC' },
        ],
      },
      {
        id: 'dns_name',
        type: 'text',
        label: 'DNS Name',
        placeholder: 'host.example.com',
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
      command: 'ip.create',
    },
  },

  'netbox:ip-assign-primary': {
    name: 'Set Primary IP',
    description: 'Set an IP as the primary IP for a device',
    category: 'configure',
    subcategory: 'netbox',
    ...netboxPlatform,
    icon: '⭐',
    color: '#F59E0B',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'device_id', type: 'number', label: 'Device ID (override)' },
      { id: 'ip_id', type: 'number', label: 'IP ID (override)' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'device', type: 'object', label: 'Updated Device' },
    ],
    
    parameters: [
      {
        id: 'device_name',
        type: 'text',
        label: 'Device Name',
      },
      {
        id: 'ip_address',
        type: 'text',
        label: 'IP Address',
        help: 'IP address to set as primary',
      },
      {
        id: 'ip_version',
        type: 'select',
        label: 'IP Version',
        default: '4',
        options: [
          { value: '4', label: 'IPv4' },
          { value: '6', label: 'IPv6' },
        ],
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'ip.assign_primary',
    },
  },
};
