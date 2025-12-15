/**
 * Axis Cameras Package
 * 
 * Nodes for Axis IP camera operations via VAPIX API:
 * - PTZ Control (home, presets, move)
 * - Snapshot capture
 * - Camera reboot
 * - Auto-focus
 * - Time settings
 * - Device info
 */

// Common target parameters used by all nodes
const targetParams = [
  {
    id: 'target_type',
    type: 'select',
    label: 'Target Source',
    default: 'device_group',
    options: [
      { value: 'ip_list', label: 'IP List' },
      { value: 'device_group', label: 'Device Group' },
      { value: 'from_input', label: 'From Previous Node' },
    ],
  },
  {
    id: 'ip_list',
    type: 'textarea',
    label: 'Camera IPs',
    default: '',
    showIf: { field: 'target_type', value: 'ip_list' },
    help: 'One IP per line',
  },
  {
    id: 'device_group',
    type: 'device-group-selector',
    label: 'Device Group',
    default: '',
    showIf: { field: 'target_type', value: 'device_group' },
  },
  {
    id: 'input_expression',
    type: 'expression',
    label: 'Targets Expression',
    default: '{{targets}}',
    showIf: { field: 'target_type', value: 'from_input' },
  },
];

// Common inputs/outputs
const standardInputs = [
  { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
  { id: 'targets', type: 'string[]', label: 'Targets (override)' },
];

const standardOutputs = [
  { id: 'success', type: 'trigger', label: 'On Success' },
  { id: 'failure', type: 'trigger', label: 'On Failure' },
  { id: 'results', type: 'object[]', label: 'Results' },
];

const advancedTimeout = [
  { id: 'timeout', type: 'number', label: 'Timeout (seconds)', default: 30, min: 5, max: 120 },
];

// Base execution config
const baseExecution = {
  context: 'remote_api',
  platform: 'axis-camera',
  requirements: { network: true, credentials: ['axis_credentials'] },
};

export default {
  id: 'axis-cameras',
  name: 'Axis Cameras',
  description: 'Axis IP camera control and management via VAPIX API',
  version: '1.0.0',
  icon: '📹',
  color: '#FFD200',
  vendor: 'Axis Communications',
  
  nodes: {
    // PTZ Go Home
    'axis:ptz-home': {
      name: 'PTZ Go Home',
      description: 'Move PTZ camera to its home position',
      category: 'configure',
      icon: '🏠',
      color: '#FFD200',
      inputs: standardInputs,
      outputs: standardOutputs,
      parameters: [
        ...targetParams,
        { id: 'channel', type: 'number', label: 'Video Channel', default: 1, min: 1, max: 16 },
        { id: 'speed', type: 'number', label: 'Movement Speed', default: 100, min: 1, max: 100 },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'action', executor: 'axis_vapix', api_endpoint: '/axis-cgi/com/ptz.cgi', api_params: 'move=home&camera={channel}&speed={speed}' },
    },

    // PTZ Go to Preset
    'axis:ptz-preset': {
      name: 'PTZ Go to Preset',
      description: 'Move PTZ camera to a saved preset position',
      category: 'configure',
      icon: '📍',
      color: '#FFD200',
      inputs: standardInputs,
      outputs: standardOutputs,
      parameters: [
        ...targetParams,
        { id: 'preset_name', type: 'text', label: 'Preset Name', default: '', help: 'Name of the preset position' },
        { id: 'preset_number', type: 'number', label: 'Preset Number', default: 1, min: 1, max: 100 },
        { id: 'use_number', type: 'checkbox', label: 'Use Preset Number', default: false },
        { id: 'channel', type: 'number', label: 'Video Channel', default: 1, min: 1, max: 16 },
        { id: 'speed', type: 'number', label: 'Movement Speed', default: 100, min: 1, max: 100 },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'action', executor: 'axis_vapix', api_endpoint: '/axis-cgi/com/ptz.cgi', api_params: 'gotoserverpresetname={preset_name}&camera={channel}&speed={speed}' },
    },

    // PTZ Move
    'axis:ptz-move': {
      name: 'PTZ Move',
      description: 'Move PTZ camera in a specific direction or to position',
      category: 'configure',
      icon: '🕹️',
      color: '#FFD200',
      inputs: standardInputs,
      outputs: standardOutputs,
      parameters: [
        ...targetParams,
        { id: 'move_type', type: 'select', label: 'Movement Type', default: 'continuous', options: [
          { value: 'continuous', label: 'Continuous (direction)' },
          { value: 'absolute', label: 'Absolute Position' },
          { value: 'relative', label: 'Relative Move' },
        ]},
        { id: 'direction', type: 'select', label: 'Direction', default: 'stop', showIf: { field: 'move_type', value: 'continuous' }, options: [
          { value: 'up', label: 'Up' }, { value: 'down', label: 'Down' },
          { value: 'left', label: 'Left' }, { value: 'right', label: 'Right' },
          { value: 'upleft', label: 'Up-Left' }, { value: 'upright', label: 'Up-Right' },
          { value: 'downleft', label: 'Down-Left' }, { value: 'downright', label: 'Down-Right' },
          { value: 'stop', label: 'Stop' },
        ]},
        { id: 'pan', type: 'number', label: 'Pan', default: 0, min: -180, max: 180 },
        { id: 'tilt', type: 'number', label: 'Tilt', default: 0, min: -90, max: 90 },
        { id: 'zoom', type: 'number', label: 'Zoom', default: 1, min: 1, max: 9999 },
        { id: 'channel', type: 'number', label: 'Video Channel', default: 1, min: 1, max: 16 },
        { id: 'speed', type: 'number', label: 'Speed', default: 50, min: 1, max: 100 },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'action', executor: 'axis_vapix', api_endpoint: '/axis-cgi/com/ptz.cgi' },
    },

    // List PTZ Presets
    'axis:ptz-list-presets': {
      name: 'List PTZ Presets',
      description: 'Get list of saved PTZ preset positions',
      category: 'query',
      icon: '📋',
      color: '#FFD200',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'presets', type: 'object[]', label: 'Preset List' }],
      parameters: [...targetParams, { id: 'channel', type: 'number', label: 'Video Channel', default: 1, min: 1, max: 16 }],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'axis_vapix', api_endpoint: '/axis-cgi/com/ptz.cgi', api_params: 'query=presetposall&camera={channel}' },
    },

    // Take Snapshot
    'axis:snapshot': {
      name: 'Take Snapshot',
      description: 'Capture a still image from the camera',
      category: 'query',
      icon: '📸',
      color: '#FFD200',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'images', type: 'object[]', label: 'Image Data' }],
      parameters: [
        ...targetParams,
        { id: 'resolution', type: 'select', label: 'Resolution', default: '1920x1080', options: [
          { value: '640x480', label: 'VGA' }, { value: '1280x720', label: '720p' },
          { value: '1920x1080', label: '1080p' }, { value: '3840x2160', label: '4K' },
        ]},
        { id: 'compression', type: 'number', label: 'JPEG Compression', default: 25, min: 0, max: 100 },
        { id: 'channel', type: 'number', label: 'Video Channel', default: 1, min: 1, max: 16 },
        { id: 'save_to_disk', type: 'checkbox', label: 'Save to Disk', default: true },
        { id: 'save_path', type: 'text', label: 'Save Directory', default: '/tmp/snapshots', showIf: { field: 'save_to_disk', value: true } },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'axis_vapix', api_endpoint: '/axis-cgi/jpg/image.cgi', api_params: 'resolution={resolution}&compression={compression}&camera={channel}' },
    },

    // Auto Focus
    'axis:auto-focus': {
      name: 'Auto Focus',
      description: 'Trigger auto-focus on the camera',
      category: 'configure',
      icon: '🎯',
      color: '#FFD200',
      inputs: standardInputs,
      outputs: standardOutputs,
      parameters: [
        ...targetParams,
        { id: 'focus_mode', type: 'select', label: 'Focus Mode', default: 'auto', options: [
          { value: 'auto', label: 'One-shot Auto Focus' },
          { value: 'continuous', label: 'Continuous Auto Focus' },
          { value: 'manual', label: 'Manual Focus' },
        ]},
        { id: 'channel', type: 'number', label: 'Video Channel', default: 1, min: 1, max: 16 },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'action', executor: 'axis_vapix', api_endpoint: '/axis-cgi/com/ptz.cgi', api_params: 'autofocus=on&camera={channel}' },
    },

    // Reboot Camera
    'axis:reboot': {
      name: 'Reboot Camera',
      description: 'Restart the camera (requires admin privileges)',
      category: 'configure',
      icon: '🔄',
      color: '#FFD200',
      inputs: standardInputs,
      outputs: standardOutputs,
      parameters: [
        ...targetParams,
        { id: 'confirm', type: 'checkbox', label: 'Confirm Reboot', default: false, help: 'Must be checked to execute' },
        { id: 'wait_for_recovery', type: 'checkbox', label: 'Wait for Recovery', default: true },
        { id: 'recovery_timeout', type: 'number', label: 'Recovery Timeout (s)', default: 120, min: 30, max: 600, showIf: { field: 'wait_for_recovery', value: true } },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'action', executor: 'axis_vapix', api_endpoint: '/axis-cgi/restart.cgi' },
    },

    // Get Device Info
    'axis:device-info': {
      name: 'Get Device Info',
      description: 'Retrieve camera device information (model, firmware, serial)',
      category: 'query',
      icon: 'ℹ️',
      color: '#FFD200',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'devices', type: 'object[]', label: 'Device Info' }],
      parameters: [
        ...targetParams,
        { id: 'info_type', type: 'select', label: 'Information Type', default: 'all', options: [
          { value: 'all', label: 'All Information' },
          { value: 'basic', label: 'Basic (model, serial)' },
          { value: 'firmware', label: 'Firmware Version' },
          { value: 'network', label: 'Network Settings' },
        ]},
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'axis_vapix', api_endpoint: '/axis-cgi/basicdeviceinfo.cgi' },
    },

    // Get Stream Config
    'axis:stream-config': {
      name: 'Get Stream Config',
      description: 'Retrieve video stream configuration and profiles',
      category: 'query',
      icon: '📺',
      color: '#FFD200',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'streams', type: 'object[]', label: 'Stream Profiles' }],
      parameters: [...targetParams, { id: 'channel', type: 'number', label: 'Video Channel', default: 1, min: 1, max: 16 }],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'axis_vapix', api_endpoint: '/axis-cgi/streamprofile.cgi', api_params: 'action=list' },
    },

    // Get Time Settings
    'axis:get-time': {
      name: 'Get Time Settings',
      description: 'Retrieve camera date/time and NTP configuration',
      category: 'query',
      icon: '🕐',
      color: '#FFD200',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'time_settings', type: 'object[]', label: 'Time Settings' }],
      parameters: targetParams,
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'axis_vapix', api_endpoint: '/axis-cgi/date.cgi', api_params: 'action=get' },
    },

    // Set Time Settings
    'axis:set-time': {
      name: 'Set Time Settings',
      description: 'Configure camera date/time and NTP settings',
      category: 'configure',
      icon: '⏰',
      color: '#FFD200',
      inputs: standardInputs,
      outputs: standardOutputs,
      parameters: [
        ...targetParams,
        { id: 'time_source', type: 'select', label: 'Time Source', default: 'ntp', options: [
          { value: 'ntp', label: 'NTP Server' },
          { value: 'manual', label: 'Manual' },
          { value: 'sync_now', label: 'Sync with Server Now' },
        ]},
        { id: 'ntp_server', type: 'text', label: 'NTP Server', default: 'pool.ntp.org', showIf: { field: 'time_source', value: 'ntp' } },
        { id: 'timezone', type: 'select', label: 'Timezone', default: 'America/Los_Angeles', options: [
          { value: 'America/New_York', label: 'Eastern (US)' },
          { value: 'America/Chicago', label: 'Central (US)' },
          { value: 'America/Denver', label: 'Mountain (US)' },
          { value: 'America/Los_Angeles', label: 'Pacific (US)' },
          { value: 'UTC', label: 'UTC' },
        ]},
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'action', executor: 'axis_vapix', api_endpoint: '/axis-cgi/param.cgi' },
    },

    // Get Image Settings
    'axis:image-settings': {
      name: 'Get Image Settings',
      description: 'Retrieve camera image settings (brightness, contrast, etc.)',
      category: 'query',
      icon: '🖼️',
      color: '#FFD200',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'settings', type: 'object[]', label: 'Image Settings' }],
      parameters: [...targetParams, { id: 'channel', type: 'number', label: 'Video Channel', default: 1, min: 1, max: 16 }],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'axis_vapix', api_endpoint: '/axis-cgi/param.cgi', api_params: 'action=list&group=ImageSource.I{channel}.Sensor' },
    },

    // Set Image Settings
    'axis:set-image': {
      name: 'Set Image Settings',
      description: 'Configure camera image settings',
      category: 'configure',
      icon: '🎨',
      color: '#FFD200',
      inputs: standardInputs,
      outputs: standardOutputs,
      parameters: [
        ...targetParams,
        { id: 'brightness', type: 'number', label: 'Brightness', default: 50, min: 0, max: 100 },
        { id: 'contrast', type: 'number', label: 'Contrast', default: 50, min: 0, max: 100 },
        { id: 'saturation', type: 'number', label: 'Saturation', default: 50, min: 0, max: 100 },
        { id: 'sharpness', type: 'number', label: 'Sharpness', default: 50, min: 0, max: 100 },
        { id: 'ir_cut_filter', type: 'select', label: 'IR Cut Filter', default: 'auto', options: [
          { value: 'auto', label: 'Auto' },
          { value: 'on', label: 'On (Day Mode)' },
          { value: 'off', label: 'Off (Night Mode)' },
        ]},
        { id: 'channel', type: 'number', label: 'Video Channel', default: 1, min: 1, max: 16 },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'action', executor: 'axis_vapix', api_endpoint: '/axis-cgi/param.cgi' },
    },

    // Get Event Log
    'axis:get-events': {
      name: 'Get Event Log',
      description: 'Retrieve camera event/alarm log',
      category: 'query',
      icon: '📜',
      color: '#FFD200',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'events', type: 'object[]', label: 'Event Log' }],
      parameters: [...targetParams, { id: 'max_events', type: 'number', label: 'Max Events', default: 100, min: 1, max: 1000 }],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'axis_vapix', api_endpoint: '/axis-cgi/systemlog.cgi' },
    },

    // Trigger I/O Port
    'axis:trigger-io': {
      name: 'Trigger I/O Port',
      description: 'Activate or deactivate camera I/O port (for external devices)',
      category: 'configure',
      icon: '🔌',
      color: '#FFD200',
      inputs: standardInputs,
      outputs: standardOutputs,
      parameters: [
        ...targetParams,
        { id: 'port', type: 'number', label: 'I/O Port', default: 1, min: 1, max: 4 },
        { id: 'action', type: 'select', label: 'Action', default: 'pulse', options: [
          { value: 'pulse', label: 'Pulse (momentary)' },
          { value: 'active', label: 'Activate (on)' },
          { value: 'inactive', label: 'Deactivate (off)' },
        ]},
        { id: 'duration', type: 'number', label: 'Pulse Duration (ms)', default: 500, min: 100, max: 10000, showIf: { field: 'action', value: 'pulse' } },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'action', executor: 'axis_vapix', api_endpoint: '/axis-cgi/io/port.cgi' },
    },

    // Get Storage Info
    'axis:storage-info': {
      name: 'Get Storage Info',
      description: 'Retrieve SD card/edge storage status and capacity',
      category: 'query',
      icon: '💾',
      color: '#FFD200',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'storage', type: 'object[]', label: 'Storage Info' }],
      parameters: targetParams,
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'axis_vapix', api_endpoint: '/axis-cgi/disks/list.cgi' },
    },

    // Recording Control
    'axis:recording-control': {
      name: 'Recording Control',
      description: 'Start or stop edge recording on the camera',
      category: 'configure',
      icon: '⏺️',
      color: '#FFD200',
      inputs: standardInputs,
      outputs: standardOutputs,
      parameters: [
        ...targetParams,
        { id: 'action', type: 'select', label: 'Action', default: 'start', options: [
          { value: 'start', label: 'Start Recording' },
          { value: 'stop', label: 'Stop Recording' },
          { value: 'status', label: 'Get Status' },
        ]},
        { id: 'profile', type: 'text', label: 'Recording Profile', default: '', help: 'Leave empty for default' },
      ],
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'action', executor: 'axis_vapix', api_endpoint: '/axis-cgi/record/record.cgi' },
    },

    // Get Network Settings
    'axis:network-settings': {
      name: 'Get Network Settings',
      description: 'Retrieve camera network configuration',
      category: 'query',
      icon: '🌐',
      color: '#FFD200',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'network', type: 'object[]', label: 'Network Settings' }],
      parameters: targetParams,
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'axis_vapix', api_endpoint: '/axis-cgi/param.cgi', api_params: 'action=list&group=Network' },
    },

    // Firmware Check
    'axis:firmware-check': {
      name: 'Check Firmware',
      description: 'Check current firmware version and update availability',
      category: 'query',
      icon: '🔧',
      color: '#FFD200',
      inputs: standardInputs,
      outputs: [...standardOutputs, { id: 'firmware', type: 'object[]', label: 'Firmware Info' }],
      parameters: targetParams,
      advanced: advancedTimeout,
      execution: { ...baseExecution, type: 'query', executor: 'axis_vapix', api_endpoint: '/axis-cgi/firmwaremanagement.cgi', api_params: 'action=status' },
    },
  },
};
