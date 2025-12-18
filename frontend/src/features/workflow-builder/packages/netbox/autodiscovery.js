/**
 * NetBox Autodiscovery Node
 * 
 * Comprehensive network discovery with automatic NetBox device creation.
 * Discovers hosts, identifies vendors/models via SNMP, and syncs to NetBox.
 */

import { PLATFORMS, PROTOCOLS } from '../../platforms';

const netboxPlatform = {
  platforms: [PLATFORMS.ANY],
  protocols: [PROTOCOLS.NETBOX],
};

export const autodiscoveryNodes = {
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
      // Target Selection
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

      // Discovery Options
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
          { value: 'winrm', label: 'WinRM (Windows)' },
          { value: 'dns', label: 'DNS Lookup' },
        ],
        help: 'Methods to use for discovering device information',
      },
      
      // SNMP Settings
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
      
      // SSH Settings
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
      
      // WinRM Settings (Windows)
      {
        id: 'winrm_enabled',
        type: 'checkbox',
        label: 'Enable WinRM Discovery',
        default: false,
        help: 'Try WinRM for Windows hosts (requires credentials). Detects Windows version, hostname, domain membership.',
      },
      {
        id: 'winrm_credential',
        type: 'credential-selector',
        label: 'WinRM Credential',
        showIf: { field: 'winrm_enabled', value: true },
        credentialType: 'winrm',
      },
      {
        id: 'winrm_use_ssl',
        type: 'checkbox',
        label: 'Use HTTPS (Port 5986)',
        default: true,
        showIf: { field: 'winrm_enabled', value: true },
        help: 'Use WinRM over HTTPS (port 5986) instead of HTTP (port 5985)',
      },
      
      // Port Scan Settings
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
        default: '22,23,80,135,139,161,443,445,3389,5985,5986,8080,8443',
        showIf: { field: 'port_scan_enabled', value: true },
        help: 'Comma-separated ports. Includes SSH(22), Telnet(23), HTTP(80,8080), HTTPS(443,8443), SNMP(161), RDP(3389), WinRM(5985,5986), SMB(445), RPC(135), NetBIOS(139)',
      },
      
      // NetBox Defaults
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
      
      // Naming Options
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
      
      // Sync Options
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
      // Performance
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
      
      // Error Handling
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
      
      // Vendor Identification
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
      timeout: 3600,
      requirements: {
        tools: ['ping', 'nmap'],
        optional_tools: ['arp-scan', 'snmpwalk', 'snmpget'],
      },
      stages: [
        'expand_targets',
        'ping_scan',
        'arp_scan',
        'port_scan',
        'snmp_discovery',
        'ssh_discovery',
        'dns_lookup',
        'identify_devices',
        'netbox_sync',
        'create_interfaces',
        'create_ips',
        'create_services',
        'generate_report',
      ],
    },
  },
};
