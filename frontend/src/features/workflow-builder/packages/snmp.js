/**
 * SNMP Package
 * 
 * Nodes for SNMP operations:
 * - SNMP Get
 * - SNMP Walk
 * - SNMP Set
 */

import { PLATFORMS, PROTOCOLS } from '../platforms';

// Common platform config for SNMP nodes (works on any SNMP-enabled device)
const snmpPlatform = {
  platforms: [PLATFORMS.NETWORK_DEVICE, PLATFORMS.LINUX, PLATFORMS.WINDOWS],
  protocols: [PROTOCOLS.SNMP],
};

export default {
  id: 'snmp',
  name: 'SNMP',
  description: 'SNMP get, walk, and set operations for network device management',
  version: '1.0.0',
  icon: '🔍',
  color: '#10B981',
  
  nodes: {
    'snmp:get': {
      name: 'SNMP Get',
      description: 'Get specific OID values from devices via SNMP',
      category: 'discover',
      subcategory: 'snmp',
      icon: '🔍',
      color: '#10B981',
      ...snmpPlatform,
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { 
          id: 'targets', 
          type: 'ip[]', 
          label: 'Target Hosts',
          description: 'List of hosts to query via SNMP',
          acceptsFrom: ['network:ping.online', 'network:port-scan.hosts'],
        },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { 
          id: 'results', 
          type: 'object[]', 
          label: 'All Results',
          description: 'SNMP results from all hosts',
          schema: {
            host: { type: 'string', description: 'Target hostname/IP' },
            oid: { type: 'string', description: 'OID queried' },
            value: { type: 'any', description: 'SNMP value returned' },
            type: { type: 'string', description: 'SNMP value type' },
            success: { type: 'boolean', description: 'Whether query succeeded' },
          },
        },
        { id: 'values', type: 'object', label: 'OID Values', description: 'Map of OID to value' },
        { id: 'successful_hosts', type: 'ip[]', label: 'Successful Hosts', description: 'Hosts that responded' },
        { id: 'failed_hosts', type: 'ip[]', label: 'Failed Hosts', description: 'Hosts that failed/timed out' },
      ],
      
      parameters: [
        {
          id: 'target_type',
          type: 'select',
          label: 'Target Source',
          default: 'from_input',
          options: [
            { value: 'ip_list', label: 'IP List' },
            { value: 'device_group', label: 'Device Group' },
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
          default: '{{online}}',
          showIf: { field: 'target_type', value: 'from_input' },
        },
        {
          id: 'version',
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
          id: 'community',
          type: 'text',
          label: 'Community String',
          default: 'public',
          showIf: { field: 'version', values: ['1', '2c'] },
          sensitive: true,
        },
        {
          id: 'oids',
          type: 'oid-selector',
          label: 'OIDs to Query',
          default: ['1.3.6.1.2.1.1.1.0', '1.3.6.1.2.1.1.5.0'],
          help: 'Select or enter OIDs to query',
          presets: [
            { label: 'System Description', value: '1.3.6.1.2.1.1.1.0' },
            { label: 'System Name', value: '1.3.6.1.2.1.1.5.0' },
            { label: 'System Location', value: '1.3.6.1.2.1.1.6.0' },
            { label: 'System Uptime', value: '1.3.6.1.2.1.1.3.0' },
            { label: 'System Contact', value: '1.3.6.1.2.1.1.4.0' },
          ],
        },
        {
          id: 'timeout',
          type: 'number',
          label: 'Timeout (seconds)',
          default: 5,
          min: 1,
          max: 60,
        },
        {
          id: 'retries',
          type: 'number',
          label: 'Retries',
          default: 2,
          min: 0,
          max: 5,
        },
        {
          id: 'concurrency',
          type: 'number',
          label: 'Concurrency',
          default: 20,
          min: 1,
          max: 100,
        },
      ],
      
      advanced: [
        {
          id: 'port',
          type: 'number',
          label: 'SNMP Port',
          default: 161,
          min: 1,
          max: 65535,
        },
        // SNMPv3 parameters
        {
          id: 'security_level',
          type: 'select',
          label: 'Security Level',
          default: 'authPriv',
          showIf: { field: 'version', value: '3' },
          options: [
            { value: 'noAuthNoPriv', label: 'No Auth, No Privacy' },
            { value: 'authNoPriv', label: 'Auth, No Privacy' },
            { value: 'authPriv', label: 'Auth and Privacy' },
          ],
        },
        {
          id: 'username',
          type: 'text',
          label: 'Username',
          default: '',
          showIf: { field: 'version', value: '3' },
        },
        {
          id: 'auth_protocol',
          type: 'select',
          label: 'Auth Protocol',
          default: 'SHA',
          showIf: { field: 'version', value: '3' },
          options: [
            { value: 'MD5', label: 'MD5' },
            { value: 'SHA', label: 'SHA' },
          ],
        },
        {
          id: 'auth_password',
          type: 'password',
          label: 'Auth Password',
          default: '',
          showIf: { field: 'version', value: '3' },
          sensitive: true,
        },
        {
          id: 'priv_protocol',
          type: 'select',
          label: 'Privacy Protocol',
          default: 'AES',
          showIf: { field: 'version', value: '3' },
          options: [
            { value: 'DES', label: 'DES' },
            { value: 'AES', label: 'AES' },
          ],
        },
        {
          id: 'priv_password',
          type: 'password',
          label: 'Privacy Password',
          default: '',
          showIf: { field: 'version', value: '3' },
          sensitive: true,
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'snmp_get',
        context: 'remote_snmp',
      },
    },

    'snmp:walk': {
      name: 'SNMP Walk',
      description: 'Walk an OID tree to get all values under a branch',
      category: 'discover',
      subcategory: 'snmp',
      icon: '🌳',
      color: '#10B981',
      ...snmpPlatform,
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'targets', type: 'string[]', label: 'Targets (override)' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'results', type: 'object[]', label: 'All Results' },
        { id: 'tree', type: 'object', label: 'OID Tree' },
      ],
      
      parameters: [
        {
          id: 'target_type',
          type: 'select',
          label: 'Target Source',
          default: 'from_input',
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
          default: '{{online}}',
          showIf: { field: 'target_type', value: 'from_input' },
        },
        {
          id: 'version',
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
          id: 'community',
          type: 'text',
          label: 'Community String',
          default: 'public',
          showIf: { field: 'version', values: ['1', '2c'] },
          sensitive: true,
        },
        {
          id: 'root_oid',
          type: 'oid-selector',
          label: 'Root OID',
          default: '1.3.6.1.2.1.1',
          help: 'OID branch to walk',
          presets: [
            { label: 'System (1.3.6.1.2.1.1)', value: '1.3.6.1.2.1.1' },
            { label: 'Interfaces (1.3.6.1.2.1.2)', value: '1.3.6.1.2.1.2' },
            { label: 'IP (1.3.6.1.2.1.4)', value: '1.3.6.1.2.1.4' },
            { label: 'Entity (1.3.6.1.2.1.47)', value: '1.3.6.1.2.1.47' },
          ],
        },
        {
          id: 'timeout',
          type: 'number',
          label: 'Timeout (seconds)',
          default: 30,
          min: 1,
          max: 300,
        },
        {
          id: 'max_repetitions',
          type: 'number',
          label: 'Max Repetitions',
          default: 50,
          min: 1,
          max: 100,
          help: 'Number of OIDs to fetch per request',
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'snmp_walk',
        context: 'remote_snmp',
      },
    },

    'snmp:set': {
      name: 'SNMP Set',
      description: 'Set OID values on devices via SNMP',
      category: 'configure',
      subcategory: 'snmp',
      icon: '✏️',
      color: '#10B981',
      ...snmpPlatform,
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'targets', type: 'string[]', label: 'Targets (override)' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'results', type: 'object[]', label: 'Results' },
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
          id: 'version',
          type: 'select',
          label: 'SNMP Version',
          default: '2c',
          options: [
            { value: '2c', label: 'SNMPv2c' },
            { value: '3', label: 'SNMPv3' },
          ],
        },
        {
          id: 'community',
          type: 'text',
          label: 'Community String',
          default: 'private',
          showIf: { field: 'version', value: '2c' },
          sensitive: true,
        },
        {
          id: 'oid',
          type: 'text',
          label: 'OID',
          default: '',
          required: true,
        },
        {
          id: 'value_type',
          type: 'select',
          label: 'Value Type',
          default: 's',
          options: [
            { value: 's', label: 'String' },
            { value: 'i', label: 'Integer' },
            { value: 'u', label: 'Unsigned Integer' },
            { value: 'x', label: 'Hex String' },
            { value: 'a', label: 'IP Address' },
          ],
        },
        {
          id: 'value',
          type: 'text',
          label: 'Value',
          default: '',
          required: true,
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'snmp_set',
        context: 'remote_snmp',
        requires_confirmation: true,
      },
    },
  },
};
