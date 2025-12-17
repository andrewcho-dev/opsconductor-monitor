/**
 * Data Types for Workflow Node Inputs/Outputs
 * 
 * Defines the standard data types that can flow between nodes,
 * their schemas, and compatibility rules.
 */

// Primitive data types
export const DATA_TYPES = {
  // Primitives
  STRING: 'string',
  NUMBER: 'number',
  BOOLEAN: 'boolean',
  
  // Arrays
  STRING_ARRAY: 'string[]',
  NUMBER_ARRAY: 'number[]',
  OBJECT_ARRAY: 'object[]',
  
  // Objects
  OBJECT: 'object',
  
  // Special types
  TRIGGER: 'trigger',        // Flow control - no data, just execution signal
  ANY: 'any',                // Accepts any type
  
  // Domain-specific types
  IP_ADDRESS: 'ip',
  IP_ARRAY: 'ip[]',
  DEVICE: 'device',
  DEVICE_ARRAY: 'device[]',
  CREDENTIAL: 'credential',
  JSON: 'json',
};

// Type compatibility matrix - which types can connect to which
export const TYPE_COMPATIBILITY = {
  [DATA_TYPES.TRIGGER]: [DATA_TYPES.TRIGGER],
  [DATA_TYPES.STRING]: [DATA_TYPES.STRING, DATA_TYPES.ANY],
  [DATA_TYPES.NUMBER]: [DATA_TYPES.NUMBER, DATA_TYPES.STRING, DATA_TYPES.ANY],
  [DATA_TYPES.BOOLEAN]: [DATA_TYPES.BOOLEAN, DATA_TYPES.STRING, DATA_TYPES.ANY],
  [DATA_TYPES.STRING_ARRAY]: [DATA_TYPES.STRING_ARRAY, DATA_TYPES.OBJECT_ARRAY, DATA_TYPES.ANY],
  [DATA_TYPES.NUMBER_ARRAY]: [DATA_TYPES.NUMBER_ARRAY, DATA_TYPES.OBJECT_ARRAY, DATA_TYPES.ANY],
  [DATA_TYPES.OBJECT_ARRAY]: [DATA_TYPES.OBJECT_ARRAY, DATA_TYPES.ANY],
  [DATA_TYPES.OBJECT]: [DATA_TYPES.OBJECT, DATA_TYPES.ANY],
  [DATA_TYPES.IP_ADDRESS]: [DATA_TYPES.IP_ADDRESS, DATA_TYPES.STRING, DATA_TYPES.ANY],
  [DATA_TYPES.IP_ARRAY]: [DATA_TYPES.IP_ARRAY, DATA_TYPES.STRING_ARRAY, DATA_TYPES.ANY],
  [DATA_TYPES.DEVICE]: [DATA_TYPES.DEVICE, DATA_TYPES.OBJECT, DATA_TYPES.ANY],
  [DATA_TYPES.DEVICE_ARRAY]: [DATA_TYPES.DEVICE_ARRAY, DATA_TYPES.OBJECT_ARRAY, DATA_TYPES.ANY],
  [DATA_TYPES.ANY]: Object.values(DATA_TYPES),
};

// Type display info
export const TYPE_INFO = {
  [DATA_TYPES.TRIGGER]: { 
    name: 'Trigger', 
    icon: '⚡', 
    color: '#22C55E',
    description: 'Execution flow signal',
  },
  [DATA_TYPES.STRING]: { 
    name: 'Text', 
    icon: '📝', 
    color: '#3B82F6',
    description: 'Single text value',
  },
  [DATA_TYPES.NUMBER]: { 
    name: 'Number', 
    icon: '#️⃣', 
    color: '#8B5CF6',
    description: 'Numeric value',
  },
  [DATA_TYPES.BOOLEAN]: { 
    name: 'Boolean', 
    icon: '✓', 
    color: '#F59E0B',
    description: 'True/False value',
  },
  [DATA_TYPES.STRING_ARRAY]: { 
    name: 'Text List', 
    icon: '📋', 
    color: '#3B82F6',
    description: 'List of text values',
  },
  [DATA_TYPES.NUMBER_ARRAY]: { 
    name: 'Number List', 
    icon: '🔢', 
    color: '#8B5CF6',
    description: 'List of numbers',
  },
  [DATA_TYPES.OBJECT_ARRAY]: { 
    name: 'Object List', 
    icon: '📦', 
    color: '#EC4899',
    description: 'List of objects/records',
  },
  [DATA_TYPES.OBJECT]: { 
    name: 'Object', 
    icon: '📦', 
    color: '#EC4899',
    description: 'Single object/record',
  },
  [DATA_TYPES.IP_ADDRESS]: { 
    name: 'IP Address', 
    icon: '🌐', 
    color: '#10B981',
    description: 'IP address string',
  },
  [DATA_TYPES.IP_ARRAY]: { 
    name: 'IP List', 
    icon: '🌐', 
    color: '#10B981',
    description: 'List of IP addresses',
  },
  [DATA_TYPES.DEVICE]: { 
    name: 'Device', 
    icon: '🖥️', 
    color: '#6366F1',
    description: 'Device object with name, IP, etc.',
  },
  [DATA_TYPES.DEVICE_ARRAY]: { 
    name: 'Device List', 
    icon: '🖥️', 
    color: '#6366F1',
    description: 'List of device objects',
  },
  [DATA_TYPES.ANY]: { 
    name: 'Any', 
    icon: '✱', 
    color: '#6B7280',
    description: 'Accepts any data type',
  },
  [DATA_TYPES.JSON]: { 
    name: 'JSON', 
    icon: '{ }', 
    color: '#F97316',
    description: 'JSON data structure',
  },
  [DATA_TYPES.CREDENTIAL]: { 
    name: 'Credential', 
    icon: '🔐', 
    color: '#EF4444',
    description: 'Authentication credentials',
  },
};

/**
 * Common output schemas for reuse across nodes
 */
export const COMMON_OUTPUTS = {
  // Standard success/failure triggers
  SUCCESS_FAILURE: [
    { id: 'success', type: DATA_TYPES.TRIGGER, label: 'On Success' },
    { id: 'failure', type: DATA_TYPES.TRIGGER, label: 'On Failure' },
  ],
  
  // Ping/discovery results
  PING_RESULTS: [
    { id: 'success', type: DATA_TYPES.TRIGGER, label: 'On Success' },
    { id: 'failure', type: DATA_TYPES.TRIGGER, label: 'On Failure' },
    { 
      id: 'results', 
      type: DATA_TYPES.OBJECT_ARRAY, 
      label: 'All Results',
      schema: {
        ip_address: 'string',
        status: 'string',  // online, offline, timeout
        rtt_ms: 'number',
        packets_sent: 'number',
        packets_received: 'number',
      },
    },
    { id: 'online', type: DATA_TYPES.IP_ARRAY, label: 'Online Hosts' },
    { id: 'offline', type: DATA_TYPES.IP_ARRAY, label: 'Offline Hosts' },
    { id: 'count_online', type: DATA_TYPES.NUMBER, label: 'Online Count' },
    { id: 'count_offline', type: DATA_TYPES.NUMBER, label: 'Offline Count' },
  ],
  
  // SSH command results
  SSH_RESULTS: [
    { id: 'success', type: DATA_TYPES.TRIGGER, label: 'On Success' },
    { id: 'failure', type: DATA_TYPES.TRIGGER, label: 'On Failure' },
    { 
      id: 'results', 
      type: DATA_TYPES.OBJECT_ARRAY, 
      label: 'All Results',
      schema: {
        host: 'string',
        stdout: 'string',
        stderr: 'string',
        exit_code: 'number',
        success: 'boolean',
      },
    },
    { id: 'stdout', type: DATA_TYPES.STRING, label: 'Standard Output' },
    { id: 'stderr', type: DATA_TYPES.STRING, label: 'Standard Error' },
    { id: 'exit_code', type: DATA_TYPES.NUMBER, label: 'Exit Code' },
  ],
  
  // SNMP results
  SNMP_RESULTS: [
    { id: 'success', type: DATA_TYPES.TRIGGER, label: 'On Success' },
    { id: 'failure', type: DATA_TYPES.TRIGGER, label: 'On Failure' },
    { 
      id: 'results', 
      type: DATA_TYPES.OBJECT_ARRAY, 
      label: 'All Results',
      schema: {
        host: 'string',
        oid: 'string',
        value: 'any',
        type: 'string',
      },
    },
    { id: 'value', type: DATA_TYPES.ANY, label: 'SNMP Value' },
  ],
  
  // NetBox device
  NETBOX_DEVICE: [
    { id: 'success', type: DATA_TYPES.TRIGGER, label: 'On Success' },
    { id: 'failure', type: DATA_TYPES.TRIGGER, label: 'On Failure' },
    { 
      id: 'device', 
      type: DATA_TYPES.DEVICE, 
      label: 'Device',
      schema: {
        id: 'number',
        name: 'string',
        primary_ip: 'string',
        site: 'string',
        role: 'string',
        status: 'string',
      },
    },
    { id: 'device_id', type: DATA_TYPES.NUMBER, label: 'Device ID' },
  ],
  
  // NetBox device list
  NETBOX_DEVICES: [
    { id: 'success', type: DATA_TYPES.TRIGGER, label: 'On Success' },
    { id: 'failure', type: DATA_TYPES.TRIGGER, label: 'On Failure' },
    { id: 'devices', type: DATA_TYPES.DEVICE_ARRAY, label: 'Devices' },
    { id: 'count', type: DATA_TYPES.NUMBER, label: 'Device Count' },
  ],
  
  // HTTP response
  HTTP_RESPONSE: [
    { id: 'success', type: DATA_TYPES.TRIGGER, label: 'On Success' },
    { id: 'failure', type: DATA_TYPES.TRIGGER, label: 'On Failure' },
    { id: 'response', type: DATA_TYPES.OBJECT, label: 'Response Body' },
    { id: 'status_code', type: DATA_TYPES.NUMBER, label: 'Status Code' },
    { id: 'headers', type: DATA_TYPES.OBJECT, label: 'Response Headers' },
  ],
  
  // Database query
  DB_QUERY: [
    { id: 'success', type: DATA_TYPES.TRIGGER, label: 'On Success' },
    { id: 'failure', type: DATA_TYPES.TRIGGER, label: 'On Failure' },
    { id: 'rows', type: DATA_TYPES.OBJECT_ARRAY, label: 'Result Rows' },
    { id: 'count', type: DATA_TYPES.NUMBER, label: 'Row Count' },
    { id: 'affected', type: DATA_TYPES.NUMBER, label: 'Affected Rows' },
  ],
};

/**
 * Common input schemas for reuse across nodes
 */
export const COMMON_INPUTS = {
  // Standard trigger input
  TRIGGER: [
    { id: 'trigger', type: DATA_TYPES.TRIGGER, label: 'Trigger', required: true },
  ],
  
  // Trigger + targets override
  TRIGGER_WITH_TARGETS: [
    { id: 'trigger', type: DATA_TYPES.TRIGGER, label: 'Trigger', required: true },
    { id: 'targets', type: DATA_TYPES.IP_ARRAY, label: 'Targets (from previous node)' },
  ],
  
  // Trigger + device data
  TRIGGER_WITH_DEVICE: [
    { id: 'trigger', type: DATA_TYPES.TRIGGER, label: 'Trigger', required: true },
    { id: 'device', type: DATA_TYPES.DEVICE, label: 'Device (from previous node)' },
  ],
  
  // Trigger + devices list
  TRIGGER_WITH_DEVICES: [
    { id: 'trigger', type: DATA_TYPES.TRIGGER, label: 'Trigger', required: true },
    { id: 'devices', type: DATA_TYPES.DEVICE_ARRAY, label: 'Devices (from previous node)' },
  ],
  
  // Trigger + generic data
  TRIGGER_WITH_DATA: [
    { id: 'trigger', type: DATA_TYPES.TRIGGER, label: 'Trigger', required: true },
    { id: 'data', type: DATA_TYPES.ANY, label: 'Data (from previous node)' },
  ],
};

/**
 * Check if two types are compatible for connection
 */
export function areTypesCompatible(sourceType, targetType) {
  if (targetType === DATA_TYPES.ANY) return true;
  if (sourceType === targetType) return true;
  
  const compatible = TYPE_COMPATIBILITY[sourceType];
  return compatible ? compatible.includes(targetType) : false;
}

/**
 * Get type info for display
 */
export function getTypeInfo(type) {
  return TYPE_INFO[type] || TYPE_INFO[DATA_TYPES.ANY];
}

/**
 * Get color for a data type (for edge coloring)
 */
export function getTypeColor(type) {
  const info = getTypeInfo(type);
  return info.color;
}

export default {
  DATA_TYPES,
  TYPE_COMPATIBILITY,
  TYPE_INFO,
  COMMON_OUTPUTS,
  COMMON_INPUTS,
  areTypesCompatible,
  getTypeInfo,
  getTypeColor,
};
