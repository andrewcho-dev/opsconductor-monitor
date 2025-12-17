/**
 * NetBox Package
 * 
 * Nodes for NetBox integration:
 * - Device CRUD operations
 * - VM CRUD operations
 * - Interface management
 * - IP address management
 * - Discovery functions
 * - Bulk operations
 * - Lookup/reference data
 */

import { PLATFORMS, PROTOCOLS } from '../platforms';

// Common platform config for NetBox nodes (platform-agnostic API calls)
const netboxPlatform = {
  platforms: [PLATFORMS.ANY],
  protocols: [PROTOCOLS.NETBOX],
};

export default {
  id: 'netbox',
  name: 'NetBox',
  description: 'NetBox DCIM/IPAM integration for device inventory management',
  version: '1.0.0',
  icon: '🗄️',
  color: '#00A4E4',
  
  nodes: {
    // ==================== DEVICE CRUD ====================
    
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
        // === Data Source ===
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
        
        // === Device Name ===
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
        
        // === Required NetBox Fields ===
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
        
        // === Optional Fields ===
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
        iterates: true, // Indicates this node can iterate over input array
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

    // ==================== VM CRUD ====================

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

    // ==================== INTERFACE MANAGEMENT ====================

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

    // ==================== IP ADDRESS MANAGEMENT ====================

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

    // ==================== DISCOVERY FUNCTIONS ====================

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

    // ==================== BULK OPERATIONS ====================

    'netbox:bulk-update': {
      name: 'Bulk Update Field',
      description: 'Update a field on multiple devices',
      category: 'configure',
      subcategory: 'netbox',
      ...netboxPlatform,
      icon: '📝',
      color: '#6366F1',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'device_ids', type: 'number[]', label: 'Device IDs (override)' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'updated', type: 'number[]', label: 'Updated Device IDs' },
        { id: 'errors', type: 'object[]', label: 'Errors' },
      ],
      
      parameters: [
        {
          id: 'device_ids',
          type: 'textarea',
          label: 'Device IDs',
          placeholder: '1\n2\n3',
          help: 'One device ID per line',
        },
        {
          id: 'field',
          type: 'select',
          label: 'Field to Update',
          required: true,
          options: [
            { value: 'status', label: 'Status' },
            { value: 'site', label: 'Site' },
            { value: 'role', label: 'Role' },
            { value: 'platform', label: 'Platform' },
            { value: 'description', label: 'Description' },
          ],
        },
        {
          id: 'value',
          type: 'text',
          label: 'New Value',
          required: true,
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'netbox',
        command: 'bulk.update_field',
      },
    },

    'netbox:bulk-tag': {
      name: 'Bulk Tag Devices',
      description: 'Add or remove tags from multiple devices',
      category: 'configure',
      subcategory: 'netbox',
      ...netboxPlatform,
      icon: '🏷️',
      color: '#6366F1',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'device_ids', type: 'number[]', label: 'Device IDs (override)' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'updated', type: 'number[]', label: 'Updated Device IDs' },
        { id: 'errors', type: 'object[]', label: 'Errors' },
      ],
      
      parameters: [
        {
          id: 'device_ids',
          type: 'textarea',
          label: 'Device IDs',
          placeholder: '1\n2\n3',
        },
        {
          id: 'tags',
          type: 'netbox-tags-selector',
          label: 'Tags to Add',
        },
        {
          id: 'remove_tags',
          type: 'netbox-tags-selector',
          label: 'Tags to Remove',
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'netbox',
        command: 'bulk.tag',
      },
    },

    // ==================== LOOKUP FUNCTIONS ====================

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

    // ==================== AUTODISCOVERY ====================

    'netbox:autodiscovery': {
      name: 'NetBox Autodiscovery',
      description: 'Comprehensive network discovery with automatic NetBox device creation. Discovers hosts, identifies vendors/models via SNMP, and syncs to NetBox.',
      category: 'discover',
      subcategory: 'netbox',
      ...netboxPlatform,
      icon: '🔮',
      color: '#00A4E4',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { 
          id: 'targets', 
          type: 'ip[]', 
          label: 'Target IPs (override)',
          description: 'Optional: Override targets from previous node',
          acceptsFrom: ['network:ping.online', 'netbox:device-list.devices'],
        },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Complete' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'each_device', type: 'trigger', label: 'For Each Device', description: 'Fires for each device discovered' },
        { 
          id: 'created_devices', 
          type: 'device[]', 
          label: 'Created Devices',
          description: 'Devices newly created in NetBox',
          schema: {
            id: { type: 'number', description: 'NetBox device ID' },
            name: { type: 'string', description: 'Device name' },
            ip_address: { type: 'string', description: 'Primary IP' },
            vendor: { type: 'string', description: 'Identified vendor' },
            model: { type: 'string', description: 'Identified model' },
            device_type: { type: 'string', description: 'NetBox device type' },
            device_role: { type: 'string', description: 'NetBox device role' },
            site: { type: 'string', description: 'NetBox site' },
          },
        },
        { 
          id: 'updated_devices', 
          type: 'device[]', 
          label: 'Updated Devices',
          description: 'Existing devices that were updated',
        },
        { 
          id: 'skipped_devices', 
          type: 'object[]', 
          label: 'Skipped Devices',
          description: 'Devices skipped (already exist, no changes)',
        },
        { 
          id: 'failed_hosts', 
          type: 'ip[]', 
          label: 'Failed Hosts',
          description: 'Hosts that could not be discovered or synced',
        },
        { 
          id: 'discovery_report', 
          type: 'object', 
          label: 'Discovery Report',
          description: 'Detailed report of the discovery process',
          schema: {
            total_targets: { type: 'number', description: 'Total IPs scanned' },
            hosts_online: { type: 'number', description: 'Hosts responding to ping' },
            snmp_success: { type: 'number', description: 'Hosts with SNMP data' },
            devices_created: { type: 'number', description: 'New devices in NetBox' },
            devices_updated: { type: 'number', description: 'Existing devices updated' },
            devices_skipped: { type: 'number', description: 'Devices skipped' },
            errors: { type: 'string[]', description: 'Error messages' },
            duration_seconds: { type: 'number', description: 'Total execution time' },
          },
        },
        { 
          id: 'current_device', 
          type: 'device', 
          label: 'Current Device',
          description: 'Current device in loop (for each_device trigger)',
        },
      ],
      
      parameters: [
        // ==================== TARGET SELECTION ====================
        {
          id: 'target_type',
          type: 'select',
          label: 'Target Source',
          default: 'network_range',
          options: [
            { value: 'network_range', label: 'Network Range (CIDR)' },
            { value: 'ip_range', label: 'IP Range (start-end)' },
            { value: 'ip_list', label: 'IP List' },
            { value: 'netbox_prefix', label: 'NetBox Prefix' },
            { value: 'netbox_ip_range', label: 'NetBox IP Range' },
            { value: 'from_input', label: 'From Previous Node' },
          ],
          help: 'How to specify target hosts for discovery',
        },
        {
          id: 'network_range',
          type: 'text',
          label: 'Network Range (CIDR)',
          default: '10.127.0.0/24',
          placeholder: '192.168.1.0/24',
          showIf: { field: 'target_type', value: 'network_range' },
          help: 'CIDR notation (e.g., 192.168.1.0/24)',
        },
        {
          id: 'ip_range_start',
          type: 'text',
          label: 'Start IP',
          placeholder: '10.127.0.1',
          showIf: { field: 'target_type', value: 'ip_range' },
        },
        {
          id: 'ip_range_end',
          type: 'text',
          label: 'End IP',
          placeholder: '10.127.0.254',
          showIf: { field: 'target_type', value: 'ip_range' },
        },
        {
          id: 'ip_list',
          type: 'textarea',
          label: 'IP Addresses',
          placeholder: '192.168.1.1\n192.168.1.2\n10.0.0.1-10.0.0.10',
          showIf: { field: 'target_type', value: 'ip_list' },
          help: 'One IP per line. Supports ranges like 10.0.0.1-10.0.0.10',
        },
        {
          id: 'netbox_prefix_id',
          type: 'netbox-prefix-selector',
          label: 'NetBox Prefix',
          showIf: { field: 'target_type', value: 'netbox_prefix' },
          help: 'Discover all IPs in a NetBox prefix',
        },
        {
          id: 'netbox_ip_range_id',
          type: 'netbox-ip-range-selector',
          label: 'NetBox IP Range',
          showIf: { field: 'target_type', value: 'netbox_ip_range' },
          help: 'Discover all IPs in a NetBox IP range',
        },
        {
          id: 'input_expression',
          type: 'expression',
          label: 'Targets Expression',
          default: '{{targets}}',
          showIf: { field: 'target_type', value: 'from_input' },
          help: 'Expression returning array of IPs',
        },
        {
          id: 'exclude_ips',
          type: 'textarea',
          label: 'Exclude IPs',
          placeholder: '192.168.1.1\n192.168.1.254',
          help: 'IPs to exclude from discovery (one per line)',
        },

        // ==================== DISCOVERY OPTIONS ====================
        {
          id: 'discovery_methods',
          type: 'multi-select',
          label: 'Discovery Methods',
          default: ['ping', 'snmp', 'ports'],
          options: [
            { value: 'ping', label: 'Ping (ICMP)' },
            { value: 'arp', label: 'ARP Scan (local network)' },
            { value: 'snmp', label: 'SNMP Discovery' },
            { value: 'ports', label: 'Port Scan' },
            { value: 'ssh', label: 'SSH (Linux/Unix)' },
            { value: 'dns', label: 'DNS Lookup' },
          ],
          help: 'Methods to use for discovering device information',
        },
        
        // ==================== SNMP SETTINGS ====================
        {
          id: 'snmp_enabled',
          type: 'checkbox',
          label: 'Enable SNMP Discovery',
          default: true,
          help: 'Query devices via SNMP for detailed information',
        },
        {
          id: 'snmp_version',
          type: 'select',
          label: 'SNMP Version',
          default: '2c',
          showIf: { field: 'snmp_enabled', value: true },
          options: [
            { value: '1', label: 'SNMPv1' },
            { value: '2c', label: 'SNMPv2c' },
            { value: '3', label: 'SNMPv3' },
          ],
        },
        {
          id: 'snmp_communities',
          type: 'textarea',
          label: 'Community Strings',
          default: 'public\nprivate',
          placeholder: 'public\nprivate\ncommunity123',
          showIf: { field: 'snmp_version', values: ['1', '2c'] },
          help: 'Community strings to try (one per line). Will try each until one works.',
        },
        {
          id: 'snmp_credential',
          type: 'credential-selector',
          label: 'SNMPv3 Credential',
          showIf: { field: 'snmp_version', value: '3' },
          credentialType: 'snmpv3',
        },
        
        // ==================== SSH SETTINGS ====================
        {
          id: 'ssh_enabled',
          type: 'checkbox',
          label: 'Enable SSH Discovery',
          default: false,
          help: 'Try SSH for Linux/Unix hosts (requires credentials)',
        },
        {
          id: 'ssh_credential',
          type: 'credential-selector',
          label: 'SSH Credential',
          showIf: { field: 'ssh_enabled', value: true },
          credentialType: 'ssh',
        },
        
        // ==================== PORT SCAN SETTINGS ====================
        {
          id: 'port_scan_enabled',
          type: 'checkbox',
          label: 'Enable Port Scan',
          default: true,
          help: 'Scan for open ports to identify services',
        },
        {
          id: 'ports_to_scan',
          type: 'text',
          label: 'Ports to Scan',
          default: '22,23,80,161,443,3389,8080,8443',
          showIf: { field: 'port_scan_enabled', value: true },
          help: 'Comma-separated ports or ranges (e.g., 22,80,443,1000-2000)',
        },
        
        // ==================== NETBOX DEFAULTS ====================
        {
          id: 'default_site',
          type: 'netbox-site-selector',
          label: 'Default Site',
          help: 'Site to assign when location cannot be determined',
        },
        {
          id: 'default_role',
          type: 'netbox-role-selector',
          label: 'Default Device Role',
          help: 'Role to assign when type cannot be determined (e.g., "Unknown")',
        },
        {
          id: 'default_device_type',
          type: 'netbox-device-type-selector',
          label: 'Default Device Type',
          help: 'Device type for unidentified devices (e.g., "Unknown Device")',
        },
        {
          id: 'default_status',
          type: 'select',
          label: 'Default Status',
          default: 'active',
          options: [
            { value: 'active', label: 'Active' },
            { value: 'planned', label: 'Planned' },
            { value: 'staged', label: 'Staged' },
            { value: 'inventory', label: 'Inventory' },
          ],
        },
        
        // ==================== NAMING OPTIONS ====================
        {
          id: 'device_naming',
          type: 'select',
          label: 'Device Naming',
          default: 'hostname_or_ip',
          options: [
            { value: 'hostname_or_ip', label: 'Hostname (fallback to IP)' },
            { value: 'hostname_only', label: 'Hostname Only (skip if none)' },
            { value: 'ip_only', label: 'IP Address Only' },
            { value: 'prefix_ip', label: 'Prefix + IP' },
            { value: 'dns_reverse', label: 'DNS Reverse Lookup' },
          ],
          help: 'How to name devices in NetBox',
        },
        {
          id: 'name_prefix',
          type: 'text',
          label: 'Name Prefix',
          placeholder: 'discovered-',
          showIf: { field: 'device_naming', value: 'prefix_ip' },
        },
        
        // ==================== SYNC OPTIONS ====================
        {
          id: 'sync_mode',
          type: 'select',
          label: 'Sync Mode',
          default: 'create_update',
          options: [
            { value: 'create_only', label: 'Create Only (skip existing)' },
            { value: 'update_only', label: 'Update Only (skip new)' },
            { value: 'create_update', label: 'Create and Update' },
          ],
          help: 'How to handle existing vs new devices',
        },
        {
          id: 'match_by',
          type: 'select',
          label: 'Match Existing Devices By',
          default: 'ip_or_name',
          options: [
            { value: 'ip', label: 'Primary IP Address' },
            { value: 'name', label: 'Device Name' },
            { value: 'ip_or_name', label: 'IP or Name' },
            { value: 'mac', label: 'MAC Address' },
            { value: 'serial', label: 'Serial Number' },
          ],
          help: 'How to identify if a device already exists in NetBox',
        },
        {
          id: 'create_interfaces',
          type: 'checkbox',
          label: 'Create Interfaces',
          default: true,
          help: 'Create device interfaces discovered via SNMP',
        },
        {
          id: 'create_ip_addresses',
          type: 'checkbox',
          label: 'Create IP Addresses',
          default: true,
          help: 'Create IP address records and assign to devices',
        },
        {
          id: 'create_services',
          type: 'checkbox',
          label: 'Create Services',
          default: false,
          help: 'Create service records for discovered open ports',
        },
        {
          id: 'add_discovery_tag',
          type: 'checkbox',
          label: 'Add Discovery Tag',
          default: true,
          help: 'Add "autodiscovered" tag to created devices',
        },
      ],
      
      advanced: [
        // ==================== PERFORMANCE ====================
        {
          id: 'ping_timeout',
          type: 'number',
          label: 'Ping Timeout (seconds)',
          default: 1,
          min: 0.5,
          max: 10,
        },
        {
          id: 'ping_count',
          type: 'number',
          label: 'Ping Count',
          default: 2,
          min: 1,
          max: 5,
        },
        {
          id: 'snmp_timeout',
          type: 'number',
          label: 'SNMP Timeout (seconds)',
          default: 5,
          min: 1,
          max: 30,
        },
        {
          id: 'snmp_retries',
          type: 'number',
          label: 'SNMP Retries',
          default: 2,
          min: 0,
          max: 5,
        },
        {
          id: 'concurrency',
          type: 'number',
          label: 'Concurrency',
          default: 50,
          min: 1,
          max: 500,
          help: 'Number of parallel operations',
        },
        {
          id: 'port_scan_timeout',
          type: 'number',
          label: 'Port Scan Timeout (seconds)',
          default: 2,
          min: 1,
          max: 30,
        },
        
        // ==================== ERROR HANDLING ====================
        {
          id: 'continue_on_error',
          type: 'checkbox',
          label: 'Continue on Error',
          default: true,
          help: 'Continue processing if individual hosts fail',
        },
        {
          id: 'skip_ping_failures',
          type: 'checkbox',
          label: 'Skip Ping Failures',
          default: true,
          help: 'Skip SNMP/SSH for hosts that do not respond to ping',
        },
        
        // ==================== VENDOR IDENTIFICATION ====================
        {
          id: 'auto_create_device_types',
          type: 'checkbox',
          label: 'Auto-Create Device Types',
          default: false,
          help: 'Automatically create new device types in NetBox for unrecognized models',
        },
        {
          id: 'auto_create_manufacturers',
          type: 'checkbox',
          label: 'Auto-Create Manufacturers',
          default: false,
          help: 'Automatically create new manufacturers in NetBox',
        },
        {
          id: 'use_mac_oui',
          type: 'checkbox',
          label: 'Use MAC OUI Lookup',
          default: true,
          help: 'Identify vendor from MAC address when SNMP fails',
        },
      ],
      
      execution: {
        type: 'composite',
        executor: 'netbox_autodiscovery',
        context: 'local',
        platform: 'any',
        timeout: 3600, // 1 hour max
        requirements: {
          tools: ['ping', 'nmap'],
          optional_tools: ['arp-scan', 'snmpwalk', 'snmpget'],
        },
        // Internal pipeline stages
        stages: [
          'expand_targets',      // Convert CIDR/ranges to IP list
          'ping_scan',           // Find online hosts
          'arp_scan',            // Get MAC addresses (if enabled)
          'port_scan',           // Find open ports
          'snmp_discovery',      // Get device info via SNMP
          'ssh_discovery',       // Get device info via SSH (if enabled)
          'dns_lookup',          // Reverse DNS lookup
          'identify_devices',    // Parse sysDescr, match vendors/models
          'netbox_sync',         // Create/update devices in NetBox
          'create_interfaces',   // Create interfaces (if enabled)
          'create_ips',          // Create IP addresses (if enabled)
          'create_services',     // Create services (if enabled)
          'generate_report',     // Generate discovery report
        ],
      },
    },
  },
};
