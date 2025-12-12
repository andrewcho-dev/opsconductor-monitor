/**
 * SSH Package
 * 
 * Nodes for SSH operations:
 * - SSH Command
 * - SSH Script
 * - SCP Upload/Download
 */

export default {
  id: 'ssh',
  name: 'SSH',
  description: 'SSH command execution and file transfer operations',
  version: '1.0.0',
  icon: '🔐',
  color: '#8B5CF6',
  
  nodes: {
    'ssh:command': {
      name: 'SSH Command',
      description: 'Execute a command on remote hosts via SSH',
      category: 'query',
      icon: '💻',
      color: '#8B5CF6',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'targets', type: 'string[]', label: 'Targets (override)' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'results', type: 'object[]', label: 'All Results' },
        { id: 'stdout', type: 'string[]', label: 'Standard Output' },
        { id: 'stderr', type: 'string[]', label: 'Standard Error' },
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
          id: 'command',
          type: 'textarea',
          label: 'Command',
          default: '',
          required: true,
          placeholder: 'show version',
          help: 'Command to execute on remote hosts',
        },
        {
          id: 'auth_type',
          type: 'select',
          label: 'Authentication',
          default: 'key',
          options: [
            { value: 'key', label: 'SSH Key' },
            { value: 'password', label: 'Password' },
            { value: 'credential_store', label: 'From Credential Store' },
          ],
        },
        {
          id: 'username',
          type: 'text',
          label: 'Username',
          default: 'admin',
        },
        {
          id: 'password',
          type: 'password',
          label: 'Password',
          default: '',
          showIf: { field: 'auth_type', value: 'password' },
          sensitive: true,
        },
        {
          id: 'key_path',
          type: 'text',
          label: 'SSH Key Path',
          default: '~/.ssh/id_rsa',
          showIf: { field: 'auth_type', value: 'key' },
        },
        {
          id: 'credential_id',
          type: 'credential-selector',
          label: 'Credential',
          default: '',
          showIf: { field: 'auth_type', value: 'credential_store' },
        },
        {
          id: 'timeout',
          type: 'number',
          label: 'Timeout (seconds)',
          default: 30,
          min: 1,
          max: 600,
        },
        {
          id: 'concurrency',
          type: 'number',
          label: 'Concurrency',
          default: 10,
          min: 1,
          max: 50,
        },
      ],
      
      advanced: [
        {
          id: 'port',
          type: 'number',
          label: 'SSH Port',
          default: 22,
          min: 1,
          max: 65535,
        },
        {
          id: 'strict_host_key',
          type: 'checkbox',
          label: 'Strict Host Key Checking',
          default: false,
        },
        {
          id: 'sudo',
          type: 'checkbox',
          label: 'Run with sudo',
          default: false,
        },
        {
          id: 'sudo_password',
          type: 'password',
          label: 'Sudo Password',
          default: '',
          showIf: { field: 'sudo', value: true },
          sensitive: true,
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'ssh_command',
      },
    },

    'ssh:script': {
      name: 'SSH Script',
      description: 'Execute a multi-line script on remote hosts',
      category: 'configure',
      icon: '📜',
      color: '#8B5CF6',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'targets', type: 'string[]', label: 'Targets (override)' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'results', type: 'object[]', label: 'All Results' },
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
          default: '{{targets}}',
          showIf: { field: 'target_type', value: 'from_input' },
        },
        {
          id: 'script',
          type: 'code',
          label: 'Script',
          default: '#!/bin/bash\n\n# Your script here\necho "Hello World"',
          language: 'bash',
          required: true,
        },
        {
          id: 'interpreter',
          type: 'select',
          label: 'Interpreter',
          default: '/bin/bash',
          options: [
            { value: '/bin/bash', label: 'Bash' },
            { value: '/bin/sh', label: 'Shell' },
            { value: '/usr/bin/python3', label: 'Python 3' },
            { value: '/usr/bin/perl', label: 'Perl' },
          ],
        },
        {
          id: 'username',
          type: 'text',
          label: 'Username',
          default: 'admin',
        },
        {
          id: 'timeout',
          type: 'number',
          label: 'Timeout (seconds)',
          default: 300,
          min: 1,
          max: 3600,
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'ssh_script',
        requires_confirmation: true,
      },
    },

    'ssh:scp-download': {
      name: 'SCP Download',
      description: 'Download files from remote hosts via SCP',
      category: 'data',
      icon: '📥',
      color: '#8B5CF6',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'targets', type: 'string[]', label: 'Targets (override)' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'files', type: 'string[]', label: 'Downloaded Files' },
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
          id: 'remote_path',
          type: 'text',
          label: 'Remote File Path',
          default: '/var/log/syslog',
          required: true,
        },
        {
          id: 'local_path',
          type: 'text',
          label: 'Local Destination',
          default: '/tmp/downloads/',
          required: true,
        },
        {
          id: 'username',
          type: 'text',
          label: 'Username',
          default: 'admin',
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'scp_download',
      },
    },

    'ssh:scp-upload': {
      name: 'SCP Upload',
      description: 'Upload files to remote hosts via SCP',
      category: 'configure',
      icon: '📤',
      color: '#8B5CF6',
      
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
          id: 'local_path',
          type: 'text',
          label: 'Local File Path',
          default: '',
          required: true,
        },
        {
          id: 'remote_path',
          type: 'text',
          label: 'Remote Destination',
          default: '/tmp/',
          required: true,
        },
        {
          id: 'username',
          type: 'text',
          label: 'Username',
          default: 'admin',
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'scp_upload',
        requires_confirmation: true,
      },
    },
  },
};
