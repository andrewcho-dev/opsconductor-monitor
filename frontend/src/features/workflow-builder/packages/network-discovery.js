/**
 * Network Discovery Package
 * 
 * Nodes for network discovery operations:
 * - Ping scan
 * - Port scan
 * - Traceroute
 * - ARP scan
 */

import { PLATFORMS, PROTOCOLS } from '../platforms';

// Network discovery nodes are platform-agnostic (run from the server)
const networkPlatform = {
  platforms: [PLATFORMS.ANY],
  protocols: [],
};

export default {
  id: 'network-discovery',
  name: 'Network Discovery',
  description: 'Ping, port scanning, traceroute, and network mapping',
  version: '1.0.0',
  icon: '📡',
  color: '#3B82F6',
  
  nodes: {
    'network:ping': {
      name: 'Ping Scan',
      description: 'Test network connectivity using ICMP ping',
      category: 'discover',
      subcategory: 'network',
      icon: '📡',
      color: '#3B82F6',
      ...networkPlatform,
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'targets', type: 'string[]', label: 'Targets (override)' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { 
          id: 'results', 
          type: 'object[]', 
          label: 'All Results',
          description: 'Complete ping results for all targets',
          schema: {
            ip_address: { type: 'string', description: 'Target IP address' },
            status: { type: 'string', description: 'online, offline, or timeout' },
            rtt_ms: { type: 'number', description: 'Round-trip time in milliseconds' },
            packets_sent: { type: 'number', description: 'Packets sent' },
            packets_received: { type: 'number', description: 'Packets received' },
          },
        },
        { 
          id: 'online', 
          type: 'ip[]', 
          label: 'Online Hosts',
          description: 'List of IP addresses that responded to ping',
        },
        { 
          id: 'offline', 
          type: 'ip[]', 
          label: 'Offline Hosts',
          description: 'List of IP addresses that did not respond',
        },
        { 
          id: 'count_online', 
          type: 'number', 
          label: 'Online Count',
          description: 'Number of hosts that responded',
        },
        { 
          id: 'count_offline', 
          type: 'number', 
          label: 'Offline Count',
          description: 'Number of hosts that did not respond',
        },
      ],
      
      parameters: [
        {
          id: 'target_type',
          type: 'select',
          label: 'Target Source',
          default: 'network_range',
          options: [
            { value: 'network_range', label: 'Network Range (CIDR)' },
            { value: 'ip_list', label: 'IP List' },
            { value: 'device_group', label: 'Device Group' },
            { value: 'netbox_devices', label: 'NetBox Devices' },
            { value: 'from_input', label: 'From Previous Node' },
            { value: 'database_query', label: 'Database Query' },
          ],
        },
        {
          id: 'network_range',
          type: 'text',
          label: 'Network Range',
          default: '10.127.0.0/24',
          placeholder: '192.168.1.0/24',
          showIf: { field: 'target_type', value: 'network_range' },
          help: 'CIDR notation (e.g., 192.168.1.0/24)',
        },
        {
          id: 'ip_list',
          type: 'textarea',
          label: 'IP Addresses',
          default: '',
          placeholder: '192.168.1.1\n192.168.1.2',
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
          id: 'netbox_filter',
          type: 'netbox-device-selector',
          label: 'NetBox Device Filter',
          default: { site: '', role: '', status: 'active' },
          showIf: { field: 'target_type', value: 'netbox_devices' },
          help: 'Select devices from NetBox by site, role, or status',
        },
        {
          id: 'input_expression',
          type: 'expression',
          label: 'Targets Expression',
          default: '{{targets}}',
          showIf: { field: 'target_type', value: 'from_input' },
          help: 'Expression that returns array of IPs',
        },
        {
          id: 'count',
          type: 'number',
          label: 'Ping Count',
          default: 3,
          min: 1,
          max: 10,
          help: 'Number of ping packets per host',
        },
        {
          id: 'timeout',
          type: 'number',
          label: 'Timeout (seconds)',
          default: 1,
          min: 0.1,
          max: 30,
          help: 'Time to wait for response',
        },
      ],
      
      advanced: [
        {
          id: 'retry_count',
          type: 'number',
          label: 'Retry Count',
          default: 0,
          min: 0,
          max: 5,
        },
        {
          id: 'retry_delay',
          type: 'number',
          label: 'Retry Delay (seconds)',
          default: 1,
          min: 0,
          max: 60,
        },
        {
          id: 'exclude_list',
          type: 'textarea',
          label: 'Exclude IPs',
          default: '',
          help: 'IPs to exclude from scan (one per line)',
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'ping',
        context: 'local',
        platform: 'linux',
        command_template: 'ping -c {count} -W {timeout} {target}',
        requirements: {
          tools: ['ping'],
        },
      },
    },

    'network:port-scan': {
      name: 'Port Scan',
      description: 'Scan for open TCP/UDP ports on target hosts',
      category: 'discover',
      subcategory: 'network',
      ...networkPlatform,
      icon: '🔌',
      color: '#3B82F6',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'targets', type: 'string[]', label: 'Targets (override)' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'results', type: 'object[]', label: 'All Results' },
        { id: 'open_ports', type: 'object[]', label: 'Open Ports' },
      ],
      
      parameters: [
        {
          id: 'target_type',
          type: 'select',
          label: 'Target Source',
          default: 'from_input',
          options: [
            { value: 'network_range', label: 'Network Range (CIDR)' },
            { value: 'ip_list', label: 'IP List' },
            { value: 'from_input', label: 'From Previous Node' },
          ],
        },
        {
          id: 'network_range',
          type: 'text',
          label: 'Network Range',
          default: '',
          showIf: { field: 'target_type', value: 'network_range' },
        },
        {
          id: 'ip_list',
          type: 'textarea',
          label: 'IP Addresses',
          default: '',
          showIf: { field: 'target_type', value: 'ip_list' },
        },
        {
          id: 'input_expression',
          type: 'expression',
          label: 'Targets Expression',
          default: '{{online}}',
          showIf: { field: 'target_type', value: 'from_input' },
        },
        {
          id: 'ports',
          type: 'text',
          label: 'Ports to Scan',
          default: '22,80,443,161,3389',
          help: 'Comma-separated ports or ranges (e.g., 22,80,443,1000-2000)',
        },
        {
          id: 'protocol',
          type: 'select',
          label: 'Protocol',
          default: 'tcp',
          options: [
            { value: 'tcp', label: 'TCP' },
            { value: 'udp', label: 'UDP' },
            { value: 'both', label: 'Both' },
          ],
        },
        {
          id: 'timeout',
          type: 'number',
          label: 'Timeout (seconds)',
          default: 3,
          min: 1,
          max: 30,
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'port_scan',
        context: 'local',
        platform: 'linux',
        requirements: {
          tools: ['nmap'],
        },
      },
    },

    'network:traceroute': {
      name: 'Traceroute',
      description: 'Trace network path to target hosts',
      category: 'discover',
      subcategory: 'network',
      ...networkPlatform,
      icon: '🛤️',
      color: '#3B82F6',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'targets', type: 'string[]', label: 'Targets (override)' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'results', type: 'object[]', label: 'Trace Results' },
        { id: 'hops', type: 'object[]', label: 'All Hops' },
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
          id: 'ip_list',
          type: 'textarea',
          label: 'Target IPs',
          default: '',
          showIf: { field: 'target_type', value: 'ip_list' },
        },
        {
          id: 'input_expression',
          type: 'expression',
          label: 'Targets Expression',
          default: '{{targets}}',
          showIf: { field: 'target_type', value: 'from_input' },
        },
        {
          id: 'max_hops',
          type: 'number',
          label: 'Max Hops',
          default: 30,
          min: 1,
          max: 64,
        },
        {
          id: 'timeout',
          type: 'number',
          label: 'Timeout per Hop (seconds)',
          default: 3,
          min: 1,
          max: 30,
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'traceroute',
        context: 'local',
        platform: 'linux',
        command_template: 'traceroute -n -w {timeout} -m {max_hops} {target}',
        requirements: {
          tools: ['traceroute'],
        },
      },
    },

    'network:arp-scan': {
      name: 'ARP Scan',
      description: 'Discover devices on local network using ARP',
      category: 'discover',
      subcategory: 'network',
      ...networkPlatform,
      icon: '📶',
      color: '#3B82F6',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'results', type: 'object[]', label: 'Discovered Devices' },
        { id: 'mac_addresses', type: 'string[]', label: 'MAC Addresses' },
      ],
      
      parameters: [
        {
          id: 'interface',
          type: 'text',
          label: 'Network Interface',
          default: 'eth0',
          help: 'Network interface to scan from',
        },
        {
          id: 'network_range',
          type: 'text',
          label: 'Network Range',
          default: '10.127.0.0/24',
          help: 'CIDR notation',
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'arp_scan',
        context: 'local',
        platform: 'linux',
        command_template: 'arp-scan -I {interface} {network_range}',
        requirements: {
          tools: ['arp-scan'],
          root: true,
        },
      },
    },
  },
};
