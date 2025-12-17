/**
 * PRTG Node Package
 * 
 * Nodes for integrating with PRTG Network Monitor:
 * - Get devices and sensors
 * - Query alerts
 * - Acknowledge/pause/resume objects
 * - Sync to NetBox
 */

const prtgPackage = {
  id: 'prtg',
  name: 'PRTG Network Monitor',
  description: 'Integration with PRTG Network Monitor for device monitoring and alerts',
  version: '1.0.0',
  icon: 'Activity',
  color: '#00a651',
  
  nodes: {
    // ========================================================================
    // Query Nodes
    // ========================================================================
    
    'prtg:get-devices': {
      id: 'prtg:get-devices',
      name: 'Get PRTG Devices',
      description: 'Retrieve devices from PRTG',
      category: 'query',
      icon: 'Server',
      color: '#00a651',
      
      parameters: [
        {
          id: 'group',
          label: 'Group Filter',
          type: 'string',
          required: false,
          placeholder: 'Network Devices',
          description: 'Filter by group name (partial match)'
        },
        {
          id: 'status',
          label: 'Status Filter',
          type: 'select',
          required: false,
          options: [
            { value: '', label: 'All Statuses' },
            { value: 'up', label: 'Up' },
            { value: 'down', label: 'Down' },
            { value: 'warning', label: 'Warning' },
            { value: 'paused', label: 'Paused' }
          ],
          description: 'Filter by device status'
        },
        {
          id: 'search',
          label: 'Search',
          type: 'string',
          required: false,
          placeholder: 'Search term',
          description: 'Search by device name or IP'
        }
      ],
      
      outputs: [
        { id: 'devices', label: 'Devices', type: 'array' },
        { id: 'count', label: 'Count', type: 'number' }
      ],
      
      executor: 'prtg.get_devices'
    },
    
    'prtg:get-sensors': {
      id: 'prtg:get-sensors',
      name: 'Get PRTG Sensors',
      description: 'Retrieve sensors from PRTG',
      category: 'query',
      icon: 'Gauge',
      color: '#00a651',
      
      parameters: [
        {
          id: 'device_id',
          label: 'Device ID',
          type: 'string',
          required: false,
          placeholder: '1234',
          description: 'Filter by PRTG device ID'
        },
        {
          id: 'status',
          label: 'Status Filter',
          type: 'select',
          required: false,
          options: [
            { value: '', label: 'All Statuses' },
            { value: 'up', label: 'Up' },
            { value: 'down', label: 'Down' },
            { value: 'warning', label: 'Warning' },
            { value: 'unusual', label: 'Unusual' },
            { value: 'paused', label: 'Paused' }
          ]
        },
        {
          id: 'sensor_type',
          label: 'Sensor Type',
          type: 'string',
          required: false,
          placeholder: 'ping',
          description: 'Filter by sensor type'
        }
      ],
      
      outputs: [
        { id: 'sensors', label: 'Sensors', type: 'array' },
        { id: 'count', label: 'Count', type: 'number' }
      ],
      
      executor: 'prtg.get_sensors'
    },
    
    'prtg:get-sensor-details': {
      id: 'prtg:get-sensor-details',
      name: 'Get Sensor Details',
      description: 'Get detailed information for a specific sensor',
      category: 'query',
      icon: 'Info',
      color: '#00a651',
      
      parameters: [
        {
          id: 'sensor_id',
          label: 'Sensor ID',
          type: 'string',
          required: true,
          placeholder: '1234',
          description: 'PRTG sensor ID'
        }
      ],
      
      inputs: [
        { id: 'sensor_id', label: 'Sensor ID', type: 'string' }
      ],
      
      outputs: [
        { id: 'sensor', label: 'Sensor Details', type: 'object' },
        { id: 'channels', label: 'Channels', type: 'array' }
      ],
      
      executor: 'prtg.get_sensor_details'
    },
    
    'prtg:get-alerts': {
      id: 'prtg:get-alerts',
      name: 'Get PRTG Alerts',
      description: 'Get current alerts from PRTG',
      category: 'query',
      icon: 'AlertTriangle',
      color: '#ef4444',
      
      parameters: [
        {
          id: 'status',
          label: 'Alert Status',
          type: 'select',
          required: false,
          options: [
            { value: '', label: 'All Alerts' },
            { value: 'down', label: 'Down' },
            { value: 'warning', label: 'Warning' },
            { value: 'unusual', label: 'Unusual' }
          ]
        }
      ],
      
      outputs: [
        { id: 'alerts', label: 'Alerts', type: 'array' },
        { id: 'count', label: 'Count', type: 'number' }
      ],
      
      executor: 'prtg.get_alerts'
    },
    
    'prtg:get-groups': {
      id: 'prtg:get-groups',
      name: 'Get PRTG Groups',
      description: 'Get device groups from PRTG',
      category: 'query',
      icon: 'Folder',
      color: '#00a651',
      
      parameters: [],
      
      outputs: [
        { id: 'groups', label: 'Groups', type: 'array' },
        { id: 'count', label: 'Count', type: 'number' }
      ],
      
      executor: 'prtg.get_groups'
    },
    
    'prtg:get-sensor-history': {
      id: 'prtg:get-sensor-history',
      name: 'Get Sensor History',
      description: 'Get historical data for a sensor',
      category: 'query',
      icon: 'TrendingUp',
      color: '#00a651',
      
      parameters: [
        {
          id: 'sensor_id',
          label: 'Sensor ID',
          type: 'string',
          required: true,
          placeholder: '1234'
        },
        {
          id: 'start_date',
          label: 'Start Date',
          type: 'string',
          required: false,
          placeholder: '2024-01-01-00-00-00',
          description: 'Format: YYYY-MM-DD-HH-MM-SS'
        },
        {
          id: 'end_date',
          label: 'End Date',
          type: 'string',
          required: false,
          placeholder: '2024-01-02-00-00-00'
        },
        {
          id: 'avg',
          label: 'Averaging (seconds)',
          type: 'number',
          required: false,
          default: 0,
          description: '0 = no averaging'
        }
      ],
      
      inputs: [
        { id: 'sensor_id', label: 'Sensor ID', type: 'string' }
      ],
      
      outputs: [
        { id: 'history', label: 'History Data', type: 'array' },
        { id: 'channels', label: 'Channels', type: 'array' }
      ],
      
      executor: 'prtg.get_sensor_history'
    },
    
    // ========================================================================
    // Action Nodes
    // ========================================================================
    
    'prtg:acknowledge-alarm': {
      id: 'prtg:acknowledge-alarm',
      name: 'Acknowledge Alarm',
      description: 'Acknowledge an alarm in PRTG',
      category: 'action',
      icon: 'CheckCircle',
      color: '#10b981',
      
      parameters: [
        {
          id: 'sensor_id',
          label: 'Sensor ID',
          type: 'string',
          required: true,
          placeholder: '1234'
        },
        {
          id: 'message',
          label: 'Acknowledgment Message',
          type: 'textarea',
          required: false,
          placeholder: 'Acknowledged by OpsConductor workflow'
        }
      ],
      
      inputs: [
        { id: 'sensor_id', label: 'Sensor ID', type: 'string' }
      ],
      
      outputs: [
        { id: 'success', label: 'Success', type: 'boolean' }
      ],
      
      executor: 'prtg.acknowledge_alarm'
    },
    
    'prtg:pause-object': {
      id: 'prtg:pause-object',
      name: 'Pause Object',
      description: 'Pause a sensor, device, or group in PRTG',
      category: 'action',
      icon: 'PauseCircle',
      color: '#f59e0b',
      
      parameters: [
        {
          id: 'object_id',
          label: 'Object ID',
          type: 'string',
          required: true,
          placeholder: '1234',
          description: 'Sensor, device, or group ID'
        },
        {
          id: 'duration',
          label: 'Duration (minutes)',
          type: 'number',
          required: false,
          placeholder: '60',
          description: 'Leave empty for indefinite pause'
        },
        {
          id: 'message',
          label: 'Pause Message',
          type: 'textarea',
          required: false,
          placeholder: 'Paused by OpsConductor workflow'
        }
      ],
      
      inputs: [
        { id: 'object_id', label: 'Object ID', type: 'string' }
      ],
      
      outputs: [
        { id: 'success', label: 'Success', type: 'boolean' }
      ],
      
      executor: 'prtg.pause_object'
    },
    
    'prtg:resume-object': {
      id: 'prtg:resume-object',
      name: 'Resume Object',
      description: 'Resume a paused sensor, device, or group',
      category: 'action',
      icon: 'PlayCircle',
      color: '#10b981',
      
      parameters: [
        {
          id: 'object_id',
          label: 'Object ID',
          type: 'string',
          required: true,
          placeholder: '1234'
        }
      ],
      
      inputs: [
        { id: 'object_id', label: 'Object ID', type: 'string' }
      ],
      
      outputs: [
        { id: 'success', label: 'Success', type: 'boolean' }
      ],
      
      executor: 'prtg.resume_object'
    },
    
    // ========================================================================
    // Sync Nodes
    // ========================================================================
    
    'prtg:sync-to-netbox': {
      id: 'prtg:sync-to-netbox',
      name: 'Sync to NetBox',
      description: 'Sync PRTG devices to NetBox',
      category: 'sync',
      icon: 'RefreshCw',
      color: '#3b82f6',
      
      parameters: [
        {
          id: 'dry_run',
          label: 'Dry Run',
          type: 'boolean',
          default: true,
          description: 'Preview changes without making them'
        },
        {
          id: 'create_missing',
          label: 'Create Missing Devices',
          type: 'boolean',
          default: true,
          description: 'Create devices in NetBox that exist in PRTG'
        },
        {
          id: 'update_existing',
          label: 'Update Existing Devices',
          type: 'boolean',
          default: false,
          description: 'Update devices that already exist in NetBox'
        },
        {
          id: 'default_site',
          label: 'Default Site ID',
          type: 'number',
          required: false,
          description: 'NetBox site ID for new devices'
        },
        {
          id: 'default_role',
          label: 'Default Role ID',
          type: 'number',
          required: false,
          description: 'NetBox device role ID for new devices'
        }
      ],
      
      outputs: [
        { id: 'processed', label: 'Processed', type: 'number' },
        { id: 'created', label: 'Created', type: 'number' },
        { id: 'updated', label: 'Updated', type: 'number' },
        { id: 'skipped', label: 'Skipped', type: 'number' },
        { id: 'errors', label: 'Errors', type: 'array' },
        { id: 'details', label: 'Details', type: 'array' }
      ],
      
      executor: 'prtg.sync_to_netbox'
    },
    
    'prtg:preview-sync': {
      id: 'prtg:preview-sync',
      name: 'Preview NetBox Sync',
      description: 'Preview what would be synced to NetBox',
      category: 'sync',
      icon: 'Eye',
      color: '#6366f1',
      
      parameters: [],
      
      outputs: [
        { id: 'total_prtg_devices', label: 'Total PRTG Devices', type: 'number' },
        { id: 'existing_in_netbox', label: 'Existing in NetBox', type: 'number' },
        { id: 'to_create', label: 'To Create', type: 'number' },
        { id: 'devices_to_create', label: 'Devices to Create', type: 'array' },
        { id: 'devices_existing', label: 'Existing Devices', type: 'array' }
      ],
      
      executor: 'prtg.preview_sync'
    },
    
    // ========================================================================
    // Trigger Nodes
    // ========================================================================
    
    'prtg:alert-trigger': {
      id: 'prtg:alert-trigger',
      name: 'PRTG Alert Trigger',
      description: 'Trigger workflow when PRTG alert is received via webhook',
      category: 'trigger',
      icon: 'Zap',
      color: '#ef4444',
      
      parameters: [
        {
          id: 'severity_filter',
          label: 'Severity Filter',
          type: 'multiselect',
          required: false,
          options: [
            { value: 'down', label: 'Down' },
            { value: 'warning', label: 'Warning' },
            { value: 'unusual', label: 'Unusual' }
          ],
          description: 'Only trigger for these severities (empty = all)'
        },
        {
          id: 'device_filter',
          label: 'Device Name Filter',
          type: 'string',
          required: false,
          placeholder: 'router-*',
          description: 'Glob pattern to match device names'
        },
        {
          id: 'sensor_filter',
          label: 'Sensor Name Filter',
          type: 'string',
          required: false,
          placeholder: '*ping*',
          description: 'Glob pattern to match sensor names'
        }
      ],
      
      outputs: [
        { id: 'alert', label: 'Alert Data', type: 'object' },
        { id: 'device_name', label: 'Device Name', type: 'string' },
        { id: 'sensor_name', label: 'Sensor Name', type: 'string' },
        { id: 'severity', label: 'Severity', type: 'string' },
        { id: 'message', label: 'Message', type: 'string' },
        { id: 'host', label: 'Host IP', type: 'string' }
      ],
      
      executor: 'prtg.alert_trigger'
    }
  },
  
  categories: {
    trigger: {
      label: 'Triggers',
      icon: 'Zap',
      order: 1
    },
    query: {
      label: 'Query',
      icon: 'Search',
      order: 2
    },
    action: {
      label: 'Actions',
      icon: 'Play',
      order: 3
    },
    sync: {
      label: 'Sync',
      icon: 'RefreshCw',
      order: 4
    }
  }
};

export default prtgPackage;
