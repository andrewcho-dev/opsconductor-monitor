/**
 * NetBox Lookup Nodes
 * 
 * Reference data lookup operations for sites, roles, platforms, and tags.
 */

import { PLATFORMS, PROTOCOLS } from '../../platforms';

const netboxPlatform = {
  platforms: [PLATFORMS.ANY],
  protocols: [PROTOCOLS.NETBOX],
};

export const lookupNodes = {
  'netbox:lookup-sites': {
    name: 'Get Sites',
    description: 'Get list of sites from NetBox',
    category: 'discover',
    subcategory: 'inventory',
    ...netboxPlatform,
    icon: '🏢',
    color: '#64748B',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'sites', type: 'object[]', label: 'Sites' },
    ],
    
    parameters: [
      {
        id: 'limit',
        type: 'number',
        label: 'Limit',
        default: 500,
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'lookup.sites',
    },
  },

  'netbox:lookup-roles': {
    name: 'Get Device Roles',
    description: 'Get list of device roles from NetBox',
    category: 'discover',
    subcategory: 'inventory',
    ...netboxPlatform,
    icon: '🎭',
    color: '#64748B',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'roles', type: 'object[]', label: 'Device Roles' },
    ],
    
    parameters: [
      {
        id: 'limit',
        type: 'number',
        label: 'Limit',
        default: 500,
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'lookup.roles',
    },
  },

  'netbox:lookup-platforms': {
    name: 'Get Platforms',
    description: 'Get list of platforms from NetBox',
    category: 'discover',
    subcategory: 'inventory',
    ...netboxPlatform,
    icon: '💻',
    color: '#64748B',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'platforms', type: 'object[]', label: 'Platforms' },
    ],
    
    parameters: [
      {
        id: 'limit',
        type: 'number',
        label: 'Limit',
        default: 500,
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'lookup.platforms',
    },
  },

  'netbox:lookup-tags': {
    name: 'Get Tags',
    description: 'Get list of tags from NetBox',
    category: 'discover',
    subcategory: 'inventory',
    ...netboxPlatform,
    icon: '🏷️',
    color: '#64748B',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'tags', type: 'object[]', label: 'Tags' },
    ],
    
    parameters: [
      {
        id: 'limit',
        type: 'number',
        label: 'Limit',
        default: 500,
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'lookup.tags',
    },
  },
};
