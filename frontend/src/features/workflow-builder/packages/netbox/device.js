/**
 * NetBox Device CRUD Nodes
 * 
 * Device create, update, delete, get, and list operations.
 */

import { PLATFORMS, PROTOCOLS } from '../../platforms';

const netboxPlatform = {
  platforms: [PLATFORMS.ANY],
  protocols: [PROTOCOLS.NETBOX],
};

export const deviceNodes = {
  'netbox:device-create': {
    name: 'Create Device',
    description: 'Create a new device in NetBox. Supports batch creation from upstream data.',
    category: 'configure',
    subcategory: 'netbox',
    icon: '➕',
    color: '#00A4E4',
    ...netboxPlatform,
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { 
        id: 'items', 
        type: 'any[]', 
        label: 'Items to Process',
        description: 'Array of items (IPs, objects) to create devices from',
        acceptsFrom: ['network:ping.online', 'network:ping.results', 'network:port-scan.hosts'],
      },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'each', type: 'trigger', label: 'For Each Created', description: 'Fires for each device created' },
      { 
        id: 'device', 
        type: 'device', 
        label: 'Current Device',
        description: 'The current device being created (in loop)',
        schema: {
          id: { type: 'number', description: 'NetBox device ID' },
          name: { type: 'string', description: 'Device name' },
          primary_ip: { type: 'string', description: 'Primary IP address' },
          site: { type: 'string', description: 'Site name' },
          role: { type: 'string', description: 'Device role' },
          status: { type: 'string', description: 'Device status' },
          url: { type: 'string', description: 'NetBox URL for this device' },
        },
      },
      { id: 'devices', type: 'device[]', label: 'All Created Devices', description: 'All devices created in batch' },
      { id: 'count', type: 'number', label: 'Created Count', description: 'Number of devices created' },
      { id: 'failed_items', type: 'any[]', label: 'Failed Items', description: 'Items that failed to create' },
    ],
    
    parameters: [
      {
        id: 'mode',
        type: 'select',
        label: 'Mode',
        default: 'batch',
        options: [
          { value: 'single', label: 'Single Device' },
          { value: 'batch', label: 'Batch - One per Input Item' },
        ],
        help: 'Single creates one device; Batch creates one device per item in input array',
      },
      {
        id: 'input_expression',
        type: 'expression',
        label: 'Input Items',
        default: '{{online}}',
        showIf: { field: 'mode', value: 'batch' },
        help: 'Expression returning array of items (IPs or objects) to process',
      },
      {
        id: 'name_source',
        type: 'select',
        label: 'Device Name',
        default: 'from_item',
        options: [
          { value: 'from_item', label: 'From Input Item (IP/hostname)' },
          { value: 'expression', label: 'Expression' },
          { value: 'static', label: 'Static Value' },
        ],
      },
      {
        id: 'name_expression',
        type: 'expression',
        label: 'Name Expression',
        default: '{{$item}}',
        showIf: { field: 'name_source', value: 'expression' },
        help: 'Use {{$item}} for current item, {{$item.field}} for object fields, {{$index}} for index',
      },
      {
        id: 'name',
        type: 'text',
        label: 'Device Name',
        placeholder: 'switch-01',
        showIf: { field: 'name_source', value: 'static' },
      },
      {
        id: 'name_prefix',
        type: 'text',
        label: 'Name Prefix',
        placeholder: 'discovered-',
        showIf: { field: 'name_source', value: 'from_item' },
        help: 'Optional prefix added before the IP/hostname',
      },
      {
        id: 'site_id',
        type: 'netbox-site-selector',
        label: 'Site',
        required: true,
        help: 'NetBox site where devices will be created',
      },
      {
        id: 'role_id',
        type: 'netbox-role-selector',
        label: 'Device Role',
        required: true,
        help: 'Device role (e.g., Router, Switch, Server)',
      },
      {
        id: 'device_type_id',
        type: 'netbox-device-type-selector',
        label: 'Device Type',
        required: true,
        help: 'Hardware model/type',
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
          { value: 'inventory', label: 'Inventory' },
          { value: 'decommissioning', label: 'Decommissioning' },
          { value: 'offline', label: 'Offline' },
        ],
      },
      {
        id: 'create_primary_ip',
        type: 'checkbox',
        label: 'Create Primary IP',
        default: true,
        showIf: { field: 'mode', value: 'batch' },
        help: 'Automatically create and assign primary IP from input',
      },
      {
        id: 'description',
        type: 'expression',
        label: 'Description',
        placeholder: 'Discovered via ping scan on {{$now}}',
        help: 'Supports expressions: {{$item}}, {{$index}}, {{$now}}',
      },
    ],
    
    advanced: [
      {
        id: 'serial',
        type: 'text',
        label: 'Serial Number',
        placeholder: 'ABC123456',
      },
      {
        id: 'asset_tag',
        type: 'text',
        label: 'Asset Tag',
      },
      {
        id: 'comments',
        type: 'textarea',
        label: 'Comments',
      },
      {
        id: 'tags',
        type: 'netbox-tags-selector',
        label: 'Tags',
      },
      {
        id: 'skip_duplicates',
        type: 'checkbox',
        label: 'Skip Duplicates',
        default: true,
        help: 'Skip creating device if name already exists in NetBox',
      },
      {
        id: 'continue_on_error',
        type: 'checkbox',
        label: 'Continue on Error',
        default: true,
        help: 'Continue processing remaining items if one fails',
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'device.create',
      iterates: true,
    },
  },

  'netbox:device-update': {
    name: 'Update Device',
    description: 'Update an existing device in NetBox',
    category: 'configure',
    subcategory: 'netbox',
    ...netboxPlatform,
    icon: '✏️',
    color: '#00A4E4',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'device_id', type: 'number', label: 'Device ID (override)' },
      { id: 'update_data', type: 'object', label: 'Update Data (override)' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'device', type: 'object', label: 'Updated Device' },
    ],
    
    parameters: [
      {
        id: 'device_selector',
        type: 'select',
        label: 'Select Device By',
        default: 'name',
        options: [
          { value: 'name', label: 'Device Name' },
          { value: 'id', label: 'Device ID' },
          { value: 'from_input', label: 'From Previous Node' },
        ],
      },
      {
        id: 'name',
        type: 'text',
        label: 'Device Name',
        showIf: { field: 'device_selector', value: 'name' },
      },
      {
        id: 'device_id',
        type: 'number',
        label: 'Device ID',
        showIf: { field: 'device_selector', value: 'id' },
      },
      {
        id: 'input_expression',
        type: 'expression',
        label: 'Device ID Expression',
        default: '{{device_id}}',
        showIf: { field: 'device_selector', value: 'from_input' },
      },
      {
        id: 'update_status',
        type: 'select',
        label: 'Update Status',
        options: [
          { value: '', label: '-- No Change --' },
          { value: 'active', label: 'Active' },
          { value: 'planned', label: 'Planned' },
          { value: 'staged', label: 'Staged' },
          { value: 'failed', label: 'Failed' },
          { value: 'offline', label: 'Offline' },
        ],
      },
      {
        id: 'update_serial',
        type: 'text',
        label: 'Update Serial Number',
      },
      {
        id: 'update_description',
        type: 'text',
        label: 'Update Description',
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'device.update',
    },
  },

  'netbox:device-delete': {
    name: 'Delete Device',
    description: 'Delete a device from NetBox',
    category: 'configure',
    subcategory: 'netbox',
    ...netboxPlatform,
    icon: '🗑️',
    color: '#EF4444',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'device_id', type: 'number', label: 'Device ID (override)' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'deleted_id', type: 'number', label: 'Deleted Device ID' },
    ],
    
    parameters: [
      {
        id: 'device_selector',
        type: 'select',
        label: 'Select Device By',
        default: 'name',
        options: [
          { value: 'name', label: 'Device Name' },
          { value: 'id', label: 'Device ID' },
          { value: 'from_input', label: 'From Previous Node' },
        ],
      },
      {
        id: 'name',
        type: 'text',
        label: 'Device Name',
        showIf: { field: 'device_selector', value: 'name' },
      },
      {
        id: 'device_id',
        type: 'number',
        label: 'Device ID',
        showIf: { field: 'device_selector', value: 'id' },
      },
      {
        id: 'confirm_delete',
        type: 'checkbox',
        label: 'Confirm Deletion',
        default: false,
        required: true,
        help: 'Check to confirm device deletion',
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'device.delete',
    },
  },

  'netbox:device-get': {
    name: 'Get Device',
    description: 'Retrieve a device from NetBox',
    category: 'discover',
    subcategory: 'inventory',
    ...netboxPlatform,
    icon: '🔍',
    color: '#00A4E4',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'device_id', type: 'number', label: 'Device ID (override)' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'device', type: 'object', label: 'Device' },
      { id: 'primary_ip', type: 'string', label: 'Primary IP' },
    ],
    
    parameters: [
      {
        id: 'device_selector',
        type: 'select',
        label: 'Select Device By',
        default: 'name',
        options: [
          { value: 'name', label: 'Device Name' },
          { value: 'id', label: 'Device ID' },
          { value: 'from_input', label: 'From Previous Node' },
        ],
      },
      {
        id: 'name',
        type: 'text',
        label: 'Device Name',
        showIf: { field: 'device_selector', value: 'name' },
      },
      {
        id: 'device_id',
        type: 'number',
        label: 'Device ID',
        showIf: { field: 'device_selector', value: 'id' },
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'device.get',
    },
  },

  'netbox:device-list': {
    name: 'List Devices',
    description: 'List devices from NetBox with filters',
    category: 'discover',
    subcategory: 'inventory',
    ...netboxPlatform,
    icon: '📋',
    color: '#00A4E4',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Success' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'devices', type: 'object[]', label: 'Devices' },
      { id: 'count', type: 'number', label: 'Total Count' },
      { id: 'ip_addresses', type: 'string[]', label: 'IP Addresses' },
    ],
    
    parameters: [
      {
        id: 'site',
        type: 'netbox-site-selector',
        label: 'Filter by Site',
      },
      {
        id: 'role',
        type: 'netbox-role-selector',
        label: 'Filter by Role',
      },
      {
        id: 'status',
        type: 'select',
        label: 'Filter by Status',
        options: [
          { value: '', label: '-- All --' },
          { value: 'active', label: 'Active' },
          { value: 'planned', label: 'Planned' },
          { value: 'staged', label: 'Staged' },
          { value: 'failed', label: 'Failed' },
          { value: 'offline', label: 'Offline' },
        ],
      },
      {
        id: 'tag',
        type: 'netbox-tag-selector',
        label: 'Filter by Tag',
      },
      {
        id: 'search',
        type: 'text',
        label: 'Search Query',
        placeholder: 'Search by name, serial, etc.',
      },
      {
        id: 'limit',
        type: 'number',
        label: 'Limit',
        default: 100,
        min: 1,
        max: 1000,
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'netbox',
      command: 'device.list',
    },
  },
};
