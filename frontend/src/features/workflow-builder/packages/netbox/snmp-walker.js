/**
 * SNMP Walker Discovery Node
 * 
 * Performs comprehensive SNMP walks on targets that have SNMP active.
 * Designed to run after autodiscovery to collect detailed device information.
 */

import { PLATFORMS, PROTOCOLS } from '../../platforms';

const netboxPlatform = {
  platforms: [PLATFORMS.ANY],
  protocols: [PROTOCOLS.NETBOX],
};

export const snmpWalkerNodes = {
  'netbox:snmp-walker': {
    name: 'SNMP Walker Discovery',
    description: 'Perform comprehensive SNMP walks on targets with active SNMP. Collects interfaces, routing tables, ARP, and system information.',
    category: 'discover',
    subcategory: 'netbox',
    ...netboxPlatform,
    icon: '🔍',
    color: '#10B981',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { 
        id: 'targets', 
        type: 'object[]', 
        label: 'SNMP Targets',
        description: 'Targets from autodiscovery with SNMP info (created_devices or snmp_active_hosts)',
        acceptsFrom: ['netbox:autodiscovery.created_devices', 'netbox:autodiscovery.updated_devices'],
      },
      {
        id: 'snmp_hosts',
        type: 'string[]',
        label: 'SNMP Active Hosts',
        description: 'List of IP addresses with active SNMP',
      },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Complete' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'each_device', type: 'trigger', label: 'For Each Device', description: 'Fires for each device walked' },
      { 
        id: 'walk_results', 
        type: 'object[]', 
        label: 'Walk Results',
        description: 'Complete SNMP walk results for all targets',
        schema: {
          ip_address: { type: 'string', description: 'Target IP address' },
          hostname: { type: 'string', description: 'Discovered hostname' },
          system_info: { type: 'object', description: 'System MIB information' },
          interfaces: { type: 'object[]', description: 'Interface table data' },
          ip_addresses: { type: 'object[]', description: 'IP address table' },
          arp_table: { type: 'object[]', description: 'ARP/neighbor table' },
          routing_table: { type: 'object[]', description: 'IP routing table' },
          vlans: { type: 'object[]', description: 'VLAN information' },
          lldp_neighbors: { type: 'object[]', description: 'LLDP neighbor data' },
          cdp_neighbors: { type: 'object[]', description: 'CDP neighbor data' },
        },
      },
      { 
        id: 'interfaces_discovered', 
        type: 'object[]', 
        label: 'All Interfaces',
        description: 'Aggregated interface data from all targets',
      },
      { 
        id: 'neighbors_discovered', 
        type: 'object[]', 
        label: 'All Neighbors',
        description: 'Aggregated LLDP/CDP neighbor data',
      },
      { 
        id: 'failed_hosts', 
        type: 'string[]', 
        label: 'Failed Hosts',
        description: 'Hosts where SNMP walk failed',
      },
      { 
        id: 'current_result', 
        type: 'object', 
        label: 'Current Result',
        description: 'Current device result in loop (for each_device trigger)',
      },
      {
        id: 'summary',
        type: 'object',
        label: 'Walk Summary',
        description: 'Summary statistics of the walk operation',
        schema: {
          total_targets: { type: 'number', description: 'Total targets attempted' },
          successful: { type: 'number', description: 'Successful walks' },
          failed: { type: 'number', description: 'Failed walks' },
          total_interfaces: { type: 'number', description: 'Total interfaces discovered' },
          total_neighbors: { type: 'number', description: 'Total neighbors discovered' },
          duration_seconds: { type: 'number', description: 'Total execution time' },
        },
      },
    ],
    
    parameters: [
      // Target Source
      {
        id: 'target_source',
        type: 'select',
        label: 'Target Source',
        default: 'from_autodiscovery',
        options: [
          { value: 'from_autodiscovery', label: 'From Autodiscovery Node' },
          { value: 'from_input', label: 'From Input Connection' },
          { value: 'ip_list', label: 'Manual IP List' },
        ],
        help: 'Where to get the list of SNMP targets',
      },
      {
        id: 'ip_list',
        type: 'textarea',
        label: 'Target IPs',
        placeholder: '192.168.1.1\n192.168.1.2\n10.0.0.1',
        showIf: { field: 'target_source', value: 'ip_list' },
        help: 'One IP per line',
      },
      {
        id: 'input_expression',
        type: 'expression',
        label: 'Targets Expression',
        default: '{{targets}}',
        showIf: { field: 'target_source', value: 'from_input' },
        help: 'Expression returning array of targets or IPs',
      },
      
      // SNMP Settings
      {
        id: 'snmp_version',
        type: 'select',
        label: 'SNMP Version',
        default: '2c',
        options: [
          { value: '1', label: 'SNMPv1' },
          { value: '2c', label: 'SNMPv2c' },
          { value: '3', label: 'SNMPv3' },
        ],
      },
      {
        id: 'snmp_community',
        type: 'text',
        label: 'Community String',
        default: 'public',
        showIf: { field: 'snmp_version', values: ['1', '2c'] },
        help: 'SNMP community string (or use from autodiscovery)',
      },
      {
        id: 'use_discovered_community',
        type: 'checkbox',
        label: 'Use Discovered Community',
        default: true,
        showIf: { field: 'snmp_version', values: ['1', '2c'] },
        help: 'Use the community string that worked during autodiscovery',
      },
      {
        id: 'snmp_credential',
        type: 'credential-selector',
        label: 'SNMPv3 Credential',
        showIf: { field: 'snmp_version', value: '3' },
        credentialType: 'snmpv3',
      },
      
      // Walk Options
      {
        id: 'walk_tables',
        type: 'multi-select',
        label: 'Tables to Walk',
        default: ['system', 'interfaces', 'ip_addresses', 'arp'],
        options: [
          { value: 'system', label: 'System Info (sysDescr, sysName, sysUpTime, etc.)' },
          { value: 'interfaces', label: 'Interface Table (ifTable, ifXTable)' },
          { value: 'ip_addresses', label: 'IP Address Table (ipAddrTable)' },
          { value: 'arp', label: 'ARP/Neighbor Table (ipNetToMediaTable)' },
          { value: 'routing', label: 'IP Routing Table (ipRouteTable)' },
          { value: 'vlans', label: 'VLAN Table (dot1qVlanStaticTable)' },
          { value: 'lldp', label: 'LLDP Neighbors (lldpRemTable)' },
          { value: 'cdp', label: 'CDP Neighbors (cdpCacheTable)' },
          { value: 'entity', label: 'Entity MIB (entPhysicalTable)' },
          { value: 'bgp', label: 'BGP Peers (bgpPeerTable)' },
          { value: 'ospf', label: 'OSPF Neighbors (ospfNbrTable)' },
        ],
        help: 'Select which SNMP tables to walk',
      },
      
      // Performance Settings
      {
        id: 'timeout_seconds',
        type: 'number',
        label: 'Timeout per Host (seconds)',
        default: 30,
        min: 5,
        max: 300,
        help: 'Maximum time to spend walking each host',
      },
      {
        id: 'max_results_per_table',
        type: 'number',
        label: 'Max Results per Table',
        default: 500,
        min: 10,
        max: 10000,
        help: 'Maximum entries to collect per table',
      },
      {
        id: 'retry_count',
        type: 'number',
        label: 'Retry Count',
        default: 2,
        min: 0,
        max: 5,
        help: 'Number of retries on timeout',
      },
      
      // NetBox Integration
      {
        id: 'update_netbox',
        type: 'checkbox',
        label: 'Update NetBox',
        default: true,
        help: 'Update NetBox devices with discovered information',
      },
      {
        id: 'sync_interfaces',
        type: 'checkbox',
        label: 'Sync Interfaces to NetBox',
        default: true,
        showIf: { field: 'update_netbox', value: true },
        help: 'Create/update interfaces in NetBox',
      },
      {
        id: 'sync_ip_addresses',
        type: 'checkbox',
        label: 'Sync IP Addresses to NetBox',
        default: true,
        showIf: { field: 'update_netbox', value: true },
        help: 'Create/update IP addresses in NetBox',
      },
      {
        id: 'sync_neighbors',
        type: 'checkbox',
        label: 'Sync Neighbors (Cables)',
        default: false,
        showIf: { field: 'update_netbox', value: true },
        help: 'Create cable connections based on LLDP/CDP neighbors',
      },
      
      // Output Options
      {
        id: 'include_raw_data',
        type: 'checkbox',
        label: 'Include Raw SNMP Data',
        default: false,
        help: 'Include raw OID/value pairs in output (increases data size)',
      },
    ],
    
    advanced: [
      {
        id: 'custom_oids',
        type: 'textarea',
        label: 'Custom OIDs to Walk',
        placeholder: '1.3.6.1.4.1.9.9.46 # Cisco VLAN\n1.3.6.1.4.1.2636 # Juniper',
        help: 'Additional OIDs to walk (one per line, # for comments)',
      },
      {
        id: 'snmp_port',
        type: 'number',
        label: 'SNMP Port',
        default: 161,
      },
      {
        id: 'bulk_get_size',
        type: 'number',
        label: 'Bulk GET Size',
        default: 25,
        min: 1,
        max: 100,
        help: 'Number of OIDs to request per GETBULK (v2c/v3 only)',
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'snmp_walker',
      command: 'walk.comprehensive',
    },
  },

  'netbox:snmp-interface-sync': {
    name: 'SNMP Interface Sync',
    description: 'Walk interface tables and sync to NetBox. Lightweight alternative to full walker.',
    category: 'discover',
    subcategory: 'netbox',
    ...netboxPlatform,
    icon: '🔌',
    color: '#10B981',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'targets', type: 'object[]', label: 'Targets' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Complete' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'interfaces', type: 'object[]', label: 'Discovered Interfaces' },
      { id: 'synced_count', type: 'number', label: 'Synced Count' },
    ],
    
    parameters: [
      {
        id: 'target_source',
        type: 'select',
        label: 'Target Source',
        default: 'from_input',
        options: [
          { value: 'from_input', label: 'From Input Connection' },
          { value: 'ip_list', label: 'Manual IP List' },
        ],
      },
      {
        id: 'ip_list',
        type: 'textarea',
        label: 'Target IPs',
        showIf: { field: 'target_source', value: 'ip_list' },
      },
      {
        id: 'snmp_community',
        type: 'text',
        label: 'Community String',
        default: 'public',
      },
      {
        id: 'sync_to_netbox',
        type: 'checkbox',
        label: 'Sync to NetBox',
        default: true,
      },
      {
        id: 'interface_filter',
        type: 'text',
        label: 'Interface Name Filter',
        placeholder: 'eth*,Gi*,Te*',
        help: 'Comma-separated patterns to include (empty = all)',
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'snmp_walker',
      command: 'walk.interfaces',
    },
  },

  'netbox:snmp-neighbor-discovery': {
    name: 'SNMP Neighbor Discovery',
    description: 'Discover network neighbors via LLDP/CDP and optionally create cables in NetBox.',
    category: 'discover',
    subcategory: 'netbox',
    ...netboxPlatform,
    icon: '🔗',
    color: '#10B981',
    
    inputs: [
      { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
      { id: 'targets', type: 'object[]', label: 'Targets' },
    ],
    outputs: [
      { id: 'success', type: 'trigger', label: 'On Complete' },
      { id: 'failure', type: 'trigger', label: 'On Failure' },
      { id: 'neighbors', type: 'object[]', label: 'Discovered Neighbors' },
      { id: 'topology', type: 'object', label: 'Network Topology' },
      { id: 'cables_created', type: 'number', label: 'Cables Created' },
    ],
    
    parameters: [
      {
        id: 'target_source',
        type: 'select',
        label: 'Target Source',
        default: 'from_input',
        options: [
          { value: 'from_input', label: 'From Input Connection' },
          { value: 'ip_list', label: 'Manual IP List' },
        ],
      },
      {
        id: 'ip_list',
        type: 'textarea',
        label: 'Target IPs',
        showIf: { field: 'target_source', value: 'ip_list' },
      },
      {
        id: 'snmp_community',
        type: 'text',
        label: 'Community String',
        default: 'public',
      },
      {
        id: 'protocols',
        type: 'multi-select',
        label: 'Discovery Protocols',
        default: ['lldp', 'cdp'],
        options: [
          { value: 'lldp', label: 'LLDP' },
          { value: 'cdp', label: 'CDP (Cisco)' },
        ],
      },
      {
        id: 'create_cables',
        type: 'checkbox',
        label: 'Create Cables in NetBox',
        default: false,
        help: 'Automatically create cable connections between devices',
      },
      {
        id: 'build_topology',
        type: 'checkbox',
        label: 'Build Topology Map',
        default: true,
        help: 'Generate a topology structure from neighbor data',
      },
    ],
    
    execution: {
      type: 'action',
      executor: 'snmp_walker',
      command: 'walk.neighbors',
    },
  },
};
