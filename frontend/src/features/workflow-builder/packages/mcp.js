/**
 * Ciena MCP Node Package
 * 
 * Nodes for integrating with Ciena MCP:
 * - Get devices and equipment
 * - Query network links/topology
 * - Sync to NetBox
 */

const mcpPackage = {
  id: 'mcp',
  name: 'Ciena MCP',
  description: 'Integration with Ciena MCP for device inventory and equipment tracking',
  version: '1.0.0',
  icon: 'Network',
  color: '#6366f1',
  
  nodes: {
    // ========================================================================
    // Query Nodes
    // ========================================================================
    
    'mcp:get-devices': {
      id: 'mcp:get-devices',
      name: 'Get MCP Devices',
      description: 'Retrieve devices from Ciena MCP',
      category: 'query',
      icon: 'Server',
      color: '#6366f1',
      
      parameters: [
        {
          id: 'limit',
          label: 'Limit',
          type: 'number',
          required: false,
          default: 100,
          description: 'Maximum number of devices to retrieve'
        }
      ],
      
      outputs: [
        { id: 'devices', label: 'Devices', type: 'array' },
        { id: 'device_count', label: 'Device Count', type: 'number' }
      ],
      
      executor: 'mcp_device_sync'
    },
    
    'mcp:get-equipment': {
      id: 'mcp:get-equipment',
      name: 'Get MCP Equipment',
      description: 'Retrieve equipment (SFPs, cards) from Ciena MCP',
      category: 'query',
      icon: 'Cpu',
      color: '#8b5cf6',
      
      parameters: [
        {
          id: 'device_id',
          label: 'Device ID',
          type: 'string',
          required: false,
          placeholder: 'MCP device ID',
          description: 'Filter equipment by device (optional)'
        }
      ],
      
      outputs: [
        { id: 'equipment', label: 'Equipment', type: 'array' },
        { id: 'equipment_count', label: 'Equipment Count', type: 'number' }
      ],
      
      executor: 'mcp_equipment_sync'
    },
    
    'mcp:get-links': {
      id: 'mcp:get-links',
      name: 'Get Network Links',
      description: 'Retrieve network topology links from MCP',
      category: 'query',
      icon: 'Cable',
      color: '#3b82f6',
      
      parameters: [],
      
      outputs: [
        { id: 'links', label: 'Network Links', type: 'array' },
        { id: 'link_count', label: 'Link Count', type: 'number' }
      ],
      
      executor: 'mcp_topology_sync'
    },
    
    'mcp:get-summary': {
      id: 'mcp:get-summary',
      name: 'Get MCP Summary',
      description: 'Get inventory summary from MCP',
      category: 'query',
      icon: 'BarChart3',
      color: '#6366f1',
      
      parameters: [],
      
      outputs: [
        { id: 'devices', label: 'Device Count', type: 'number' },
        { id: 'equipment', label: 'Equipment Count', type: 'number' },
        { id: 'links', label: 'Link Count', type: 'number' }
      ],
      
      executor: 'mcp_inventory_summary'
    },
    
    // ========================================================================
    // Sync Nodes
    // ========================================================================
    
    'mcp:sync-devices': {
      id: 'mcp:sync-devices',
      name: 'Sync Devices to NetBox',
      description: 'Sync MCP devices to NetBox',
      category: 'sync',
      icon: 'RefreshCw',
      color: '#10b981',
      
      parameters: [
        {
          id: 'sync_to_netbox',
          label: 'Sync to NetBox',
          type: 'boolean',
          default: true,
          description: 'Enable syncing to NetBox'
        },
        {
          id: 'create_missing',
          label: 'Create Missing Devices',
          type: 'boolean',
          default: false,
          description: 'Create devices in NetBox that do not exist'
        },
        {
          id: 'site_id',
          label: 'Site ID',
          type: 'number',
          required: false,
          description: 'NetBox site ID for new devices'
        },
        {
          id: 'device_role_id',
          label: 'Device Role ID',
          type: 'number',
          required: false,
          description: 'NetBox device role ID for new devices'
        }
      ],
      
      outputs: [
        { id: 'total', label: 'Total Devices', type: 'number' },
        { id: 'created', label: 'Created', type: 'number' },
        { id: 'updated', label: 'Updated', type: 'number' },
        { id: 'skipped', label: 'Skipped', type: 'number' },
        { id: 'errors', label: 'Errors', type: 'array' }
      ],
      
      executor: 'mcp_device_sync'
    },
    
    'mcp:sync-equipment': {
      id: 'mcp:sync-equipment',
      name: 'Sync Equipment to NetBox',
      description: 'Sync MCP equipment (SFPs, cards) to NetBox as inventory items',
      category: 'sync',
      icon: 'HardDrive',
      color: '#8b5cf6',
      
      parameters: [
        {
          id: 'sync_to_netbox',
          label: 'Sync to NetBox',
          type: 'boolean',
          default: true,
          description: 'Enable syncing to NetBox inventory items'
        }
      ],
      
      outputs: [
        { id: 'total', label: 'Total Equipment', type: 'number' },
        { id: 'created', label: 'Created', type: 'number' },
        { id: 'updated', label: 'Updated', type: 'number' },
        { id: 'skipped', label: 'Skipped', type: 'number' },
        { id: 'errors', label: 'Errors', type: 'array' }
      ],
      
      executor: 'mcp_equipment_sync'
    },
    
    // ========================================================================
    // Combined Workflow Nodes
    // ========================================================================
    
    'mcp:full-discovery': {
      id: 'mcp:full-discovery',
      name: 'MCP Full Discovery',
      description: 'Complete MCP discovery: devices, equipment, and topology',
      category: 'workflow',
      icon: 'Workflow',
      color: '#6366f1',
      
      parameters: [
        {
          id: 'sync_to_netbox',
          label: 'Sync to NetBox',
          type: 'boolean',
          default: true,
          description: 'Sync all discovered data to NetBox'
        },
        {
          id: 'include_snmp',
          label: 'Include SNMP Walk',
          type: 'boolean',
          default: false,
          description: 'Also perform SNMP walk on discovered devices'
        },
        {
          id: 'snmp_community',
          label: 'SNMP Community',
          type: 'string',
          default: 'public',
          description: 'SNMP community string for interface discovery'
        }
      ],
      
      outputs: [
        { id: 'devices', label: 'Devices', type: 'array' },
        { id: 'equipment', label: 'Equipment', type: 'array' },
        { id: 'links', label: 'Links', type: 'array' },
        { id: 'netbox_sync', label: 'NetBox Sync Results', type: 'object' }
      ],
      
      executor: 'mcp_full_discovery'
    }
  },
  
  categories: {
    query: {
      label: 'Query',
      icon: 'Search',
      order: 1
    },
    sync: {
      label: 'Sync',
      icon: 'RefreshCw',
      order: 2
    },
    workflow: {
      label: 'Workflows',
      icon: 'Workflow',
      order: 3
    }
  }
};

export default mcpPackage;
