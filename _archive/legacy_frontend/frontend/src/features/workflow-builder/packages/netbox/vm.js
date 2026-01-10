/**
 * NetBox VM CRUD Nodes
 * 
 * Virtual machine create and list operations.
 */

import { PLATFORMS, PROTOCOLS } from '../../platforms';

const netboxPlatform = {
  platforms: [PLATFORMS.ANY],
  protocols: [PROTOCOLS.NETBOX],
};

export const vmNodes = {
  'netbox:vm-create': {
    name: 'Create VM',
    description: 'Create a virtual machine in NetBox',
    category: 'configure',
    subcategory: 'netbox',
    ...netboxPlatform,
    icon: '🖥️',
    color: '#8B5CF6',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'vm', type: 'object', label: 'Created VM' },
      { id: 'vm_id', type: 'number', label: 'VM ID' },
    ],
    
    parameters: [
      {
        id: 'name',
        type: 'text',
        label: 'VM Name',
        required: true,
      },
      {
        id: 'cluster_id',
        type: 'netbox-cluster-selector',
        label: 'Cluster',
        required: true,
      },
      {
        id: 'status',
        type: 'select',
        label: 'Status',
        default: 'active',
        options: [
          { value: 'active', label: 'Active' },
          { value: 'planned', label: 'Planned' },
          { value: 'staged', label: 'Staged' },
          { value: 'failed', label: 'Failed' },
          { value: 'offline', label: 'Offline' },
        ],
      },
      {
        id: 'vcpus',
        type: 'number',
        label: 'vCPUs',
        min: 1,
      },
      {
        id: 'memory',
        type: 'number',
        label: 'Memory (MB)',
        min: 1,
      },
      {
        id: 'disk',
        type: 'number',
        label: 'Disk (GB)',
        min: 1,
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
      command: 'vm.create',
    },
  },

  'netbox:vm-list': {
    name: 'List VMs',
    description: 'List virtual machines from NetBox',
    category: 'discover',
    subcategory: 'inventory',
    ...netboxPlatform,
    icon: '🖥️',
    color: '#8B5CF6',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'vms', type: 'object[]', label: 'Virtual Machines' },
      { id: 'count', type: 'number', label: 'Total Count' },
    ],
    
    parameters: [
      {
        id: 'cluster',
        type: 'netbox-cluster-selector',
        label: 'Filter by Cluster',
      },
      {
        id: 'status',
        type: 'select',
        label: 'Filter by Status',
        options: [
          { value: '', label: '-- All --' },
          { value: 'active', label: 'Active' },
          { value: 'offline', label: 'Offline' },
        ],
      },
      {
        id: 'tag',
        type: 'netbox-tag-selector',
        label: 'Filter by Tag',
      },
      {
        id: 'limit',
        type: 'number',
        label: 'Limit',
        default: 100,
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'vm.list',
    },
  },
};
