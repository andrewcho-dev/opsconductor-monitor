/**
 * Platform Definitions
 * 
 * Defines all supported platforms, their compatibility relationships,
 * and visual indicators for the workflow builder.
 */

// Platform identifiers
export const PLATFORMS = {
  // Operating Systems
  LINUX: 'linux',
  WINDOWS: 'windows',
  MACOS: 'macos',
  UNIX: 'unix',
  
  // Network Device Vendors
  CISCO_IOS: 'cisco-ios',
  CISCO_NXOS: 'cisco-nxos',
  CISCO_ASA: 'cisco-asa',
  JUNIPER_JUNOS: 'juniper-junos',
  ARISTA_EOS: 'arista-eos',
  CIENA_SAOS: 'ciena-saos',
  PALOALTO_PANOS: 'paloalto-panos',
  FORTINET_FORTIOS: 'fortinet-fortios',
  MIKROTIK_ROUTEROS: 'mikrotik-routeros',
  UBIQUITI_UNIFI: 'ubiquiti-unifi',
  HPE_ARUBA: 'hpe-aruba',
  DELL_OS10: 'dell-os10',
  
  // Device Types
  AXIS_CAMERA: 'axis-camera',
  GENERIC_CAMERA: 'generic-camera',
  
  // Generic/Abstract
  NETWORK_DEVICE: 'network-device',  // Any network device
  ANY: 'any',                         // Platform agnostic
};

// Platform metadata with display info
export const PLATFORM_INFO = {
  [PLATFORMS.LINUX]: {
    name: 'Linux',
    icon: '🐧',
    color: '#FCC624',
    category: 'os',
    compatibleWith: [PLATFORMS.UNIX],
  },
  [PLATFORMS.WINDOWS]: {
    name: 'Windows',
    icon: '🪟',
    color: '#00A4EF',
    category: 'os',
    compatibleWith: [],
  },
  [PLATFORMS.MACOS]: {
    name: 'macOS',
    icon: '🍎',
    color: '#A2AAAD',
    category: 'os',
    compatibleWith: [PLATFORMS.UNIX],
  },
  [PLATFORMS.UNIX]: {
    name: 'Unix',
    icon: '🖥️',
    color: '#4B0082',
    category: 'os',
    compatibleWith: [PLATFORMS.LINUX, PLATFORMS.MACOS],
  },
  [PLATFORMS.CISCO_IOS]: {
    name: 'Cisco IOS',
    icon: '🌐',
    color: '#1BA0D7',
    category: 'network',
    vendor: 'Cisco',
    compatibleWith: [PLATFORMS.NETWORK_DEVICE],
  },
  [PLATFORMS.CISCO_NXOS]: {
    name: 'Cisco NX-OS',
    icon: '🌐',
    color: '#1BA0D7',
    category: 'network',
    vendor: 'Cisco',
    compatibleWith: [PLATFORMS.NETWORK_DEVICE],
  },
  [PLATFORMS.CISCO_ASA]: {
    name: 'Cisco ASA',
    icon: '🛡️',
    color: '#1BA0D7',
    category: 'network',
    vendor: 'Cisco',
    compatibleWith: [PLATFORMS.NETWORK_DEVICE],
  },
  [PLATFORMS.JUNIPER_JUNOS]: {
    name: 'Juniper Junos',
    icon: '🌐',
    color: '#84B135',
    category: 'network',
    vendor: 'Juniper',
    compatibleWith: [PLATFORMS.NETWORK_DEVICE],
  },
  [PLATFORMS.ARISTA_EOS]: {
    name: 'Arista EOS',
    icon: '🌐',
    color: '#4C8BF5',
    category: 'network',
    vendor: 'Arista',
    compatibleWith: [PLATFORMS.NETWORK_DEVICE],
  },
  [PLATFORMS.CIENA_SAOS]: {
    name: 'Ciena SAOS',
    icon: '🏭',
    color: '#00629B',
    category: 'network',
    vendor: 'Ciena',
    compatibleWith: [PLATFORMS.NETWORK_DEVICE],
  },
  [PLATFORMS.PALOALTO_PANOS]: {
    name: 'Palo Alto PAN-OS',
    icon: '🛡️',
    color: '#FA582D',
    category: 'network',
    vendor: 'Palo Alto',
    compatibleWith: [PLATFORMS.NETWORK_DEVICE],
  },
  [PLATFORMS.FORTINET_FORTIOS]: {
    name: 'Fortinet FortiOS',
    icon: '🛡️',
    color: '#DA291C',
    category: 'network',
    vendor: 'Fortinet',
    compatibleWith: [PLATFORMS.NETWORK_DEVICE],
  },
  [PLATFORMS.MIKROTIK_ROUTEROS]: {
    name: 'MikroTik RouterOS',
    icon: '🌐',
    color: '#293239',
    category: 'network',
    vendor: 'MikroTik',
    compatibleWith: [PLATFORMS.NETWORK_DEVICE],
  },
  [PLATFORMS.UBIQUITI_UNIFI]: {
    name: 'Ubiquiti UniFi',
    icon: '📡',
    color: '#0559C9',
    category: 'network',
    vendor: 'Ubiquiti',
    compatibleWith: [PLATFORMS.NETWORK_DEVICE],
  },
  [PLATFORMS.HPE_ARUBA]: {
    name: 'HPE Aruba',
    icon: '🌐',
    color: '#FF8300',
    category: 'network',
    vendor: 'HPE',
    compatibleWith: [PLATFORMS.NETWORK_DEVICE],
  },
  [PLATFORMS.DELL_OS10]: {
    name: 'Dell OS10',
    icon: '🌐',
    color: '#007DB8',
    category: 'network',
    vendor: 'Dell',
    compatibleWith: [PLATFORMS.NETWORK_DEVICE],
  },
  [PLATFORMS.AXIS_CAMERA]: {
    name: 'Axis Camera',
    icon: '📷',
    color: '#FFD200',
    category: 'device',
    vendor: 'Axis',
    compatibleWith: [PLATFORMS.GENERIC_CAMERA],
  },
  [PLATFORMS.GENERIC_CAMERA]: {
    name: 'Camera',
    icon: '📷',
    color: '#6B7280',
    category: 'device',
    compatibleWith: [],
  },
  [PLATFORMS.NETWORK_DEVICE]: {
    name: 'Network Device',
    icon: '🌐',
    color: '#6B7280',
    category: 'network',
    compatibleWith: [],
  },
  [PLATFORMS.ANY]: {
    name: 'Any Platform',
    icon: '⚡',
    color: '#10B981',
    category: 'universal',
    compatibleWith: [],
  },
};

// Protocol/access requirements
export const PROTOCOLS = {
  SSH: 'ssh',
  WINRM: 'winrm',
  SNMP: 'snmp',
  HTTP: 'http',
  HTTPS: 'https',
  TELNET: 'telnet',
  API: 'api',
  NETBOX: 'netbox',
};

export const PROTOCOL_INFO = {
  [PROTOCOLS.SSH]: {
    name: 'SSH',
    icon: '🔐',
    defaultPort: 22,
  },
  [PROTOCOLS.WINRM]: {
    name: 'WinRM',
    icon: '🪟',
    defaultPort: 5985,
  },
  [PROTOCOLS.SNMP]: {
    name: 'SNMP',
    icon: '📊',
    defaultPort: 161,
  },
  [PROTOCOLS.HTTP]: {
    name: 'HTTP',
    icon: '🌐',
    defaultPort: 80,
  },
  [PROTOCOLS.HTTPS]: {
    name: 'HTTPS',
    icon: '🔒',
    defaultPort: 443,
  },
  [PROTOCOLS.TELNET]: {
    name: 'Telnet',
    icon: '📟',
    defaultPort: 23,
  },
  [PROTOCOLS.API]: {
    name: 'API',
    icon: '🔌',
    defaultPort: null,
  },
  [PROTOCOLS.NETBOX]: {
    name: 'NetBox API',
    icon: '🗄️',
    defaultPort: 443,
  },
};

/**
 * Check if a node's platforms are compatible with target device platforms
 * @param {string[]} nodePlatforms - Platforms the node supports
 * @param {string[]} targetPlatforms - Platforms of target devices
 * @returns {Object} Compatibility result
 */
export function checkPlatformCompatibility(nodePlatforms, targetPlatforms) {
  // If node supports ANY platform, always compatible
  if (nodePlatforms.includes(PLATFORMS.ANY)) {
    return {
      compatible: true,
      compatibleTargets: targetPlatforms,
      incompatibleTargets: [],
      warnings: [],
    };
  }
  
  const compatible = [];
  const incompatible = [];
  
  for (const target of targetPlatforms) {
    const isDirectMatch = nodePlatforms.includes(target);
    const isCompatibleMatch = nodePlatforms.some(nodePlatform => {
      const info = PLATFORM_INFO[nodePlatform];
      return info?.compatibleWith?.includes(target);
    });
    const targetIsCompatible = (() => {
      const targetInfo = PLATFORM_INFO[target];
      return targetInfo?.compatibleWith?.some(p => nodePlatforms.includes(p));
    })();
    
    if (isDirectMatch || isCompatibleMatch || targetIsCompatible) {
      compatible.push(target);
    } else {
      incompatible.push(target);
    }
  }
  
  const warnings = [];
  if (incompatible.length > 0 && compatible.length > 0) {
    warnings.push(`${incompatible.length} of ${targetPlatforms.length} targets are incompatible`);
  }
  
  return {
    compatible: incompatible.length === 0,
    partiallyCompatible: compatible.length > 0 && incompatible.length > 0,
    compatibleTargets: compatible,
    incompatibleTargets: incompatible,
    warnings,
  };
}

/**
 * Get display info for a platform
 * @param {string} platform - Platform identifier
 * @returns {Object} Platform display info
 */
export function getPlatformInfo(platform) {
  return PLATFORM_INFO[platform] || {
    name: platform,
    icon: '❓',
    color: '#6B7280',
    category: 'unknown',
  };
}

/**
 * Get platforms grouped by category
 * @returns {Object} Platforms grouped by category
 */
export function getPlatformsByCategory() {
  const categories = {
    os: { name: 'Operating Systems', platforms: [] },
    network: { name: 'Network Devices', platforms: [] },
    device: { name: 'Devices', platforms: [] },
    universal: { name: 'Universal', platforms: [] },
  };
  
  for (const [id, info] of Object.entries(PLATFORM_INFO)) {
    if (categories[info.category]) {
      categories[info.category].platforms.push({ id, ...info });
    }
  }
  
  return categories;
}

export default {
  PLATFORMS,
  PLATFORM_INFO,
  PROTOCOLS,
  PROTOCOL_INFO,
  checkPlatformCompatibility,
  getPlatformInfo,
  getPlatformsByCategory,
};
