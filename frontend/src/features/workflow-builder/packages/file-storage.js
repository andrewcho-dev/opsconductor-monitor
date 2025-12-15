/**
 * File/Storage Package
 * 
 * Nodes for file operations and storage:
 * - Read File
 * - Write File
 * - FTP/SFTP
 * - S3/Cloud Storage
 */

export default {
  id: 'file-storage',
  name: 'File / Storage',
  description: 'Read, write, and transfer files',
  version: '1.0.0',
  icon: '📁',
  color: '#F59E0B',
  
  nodes: {
    'file:read': {
      name: 'Read File',
      description: 'Read content from a file',
      category: 'data',
      icon: '📖',
      color: '#F59E0B',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'file_path',
          type: 'text',
          label: 'File Path',
          default: '',
          required: true,
          placeholder: '/path/to/file.txt',
        },
        {
          id: 'read_as',
          type: 'select',
          label: 'Read As',
          default: 'text',
          options: [
            { value: 'text', label: 'Text' },
            { value: 'json', label: 'JSON' },
            { value: 'csv', label: 'CSV' },
            { value: 'binary', label: 'Binary (Base64)' },
            { value: 'lines', label: 'Lines (Array)' },
          ],
        },
        {
          id: 'encoding',
          type: 'select',
          label: 'Encoding',
          default: 'utf-8',
          options: [
            { value: 'utf-8', label: 'UTF-8' },
            { value: 'ascii', label: 'ASCII' },
            { value: 'latin1', label: 'Latin-1' },
          ],
          showIf: { field: 'read_as', value: ['text', 'lines'] },
        },
        {
          id: 'csv_delimiter',
          type: 'text',
          label: 'CSV Delimiter',
          default: ',',
          showIf: { field: 'read_as', value: 'csv' },
        },
        {
          id: 'csv_header',
          type: 'checkbox',
          label: 'First Row is Header',
          default: true,
          showIf: { field: 'read_as', value: 'csv' },
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'read_file',
        context: 'local',
        platform: 'linux',
        requirements: {
          filesystem: true,
        },
      },
    },

    'file:write': {
      name: 'Write File',
      description: 'Write content to a file',
      category: 'data',
      icon: '📝',
      color: '#F59E0B',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'file_path',
          type: 'text',
          label: 'File Path',
          default: '',
          required: true,
          placeholder: '/path/to/output.txt',
        },
        {
          id: 'content_source',
          type: 'select',
          label: 'Content Source',
          default: 'input',
          options: [
            { value: 'input', label: 'From Input Data' },
            { value: 'static', label: 'Static Content' },
            { value: 'expression', label: 'Expression' },
          ],
        },
        {
          id: 'input_field',
          type: 'text',
          label: 'Input Field',
          default: 'data',
          showIf: { field: 'content_source', value: 'input' },
        },
        {
          id: 'static_content',
          type: 'textarea',
          label: 'Content',
          default: '',
          showIf: { field: 'content_source', value: 'static' },
        },
        {
          id: 'expression',
          type: 'expression',
          label: 'Expression',
          default: '{{$json.content}}',
          showIf: { field: 'content_source', value: 'expression' },
        },
        {
          id: 'write_mode',
          type: 'select',
          label: 'Write Mode',
          default: 'overwrite',
          options: [
            { value: 'overwrite', label: 'Overwrite' },
            { value: 'append', label: 'Append' },
            { value: 'create_only', label: 'Create Only (fail if exists)' },
          ],
        },
        {
          id: 'format',
          type: 'select',
          label: 'Format',
          default: 'text',
          options: [
            { value: 'text', label: 'Text' },
            { value: 'json', label: 'JSON' },
            { value: 'csv', label: 'CSV' },
          ],
        },
        {
          id: 'json_pretty',
          type: 'checkbox',
          label: 'Pretty Print JSON',
          default: true,
          showIf: { field: 'format', value: 'json' },
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'write_file',
        context: 'local',
        platform: 'linux',
        requirements: {
          filesystem: true,
        },
      },
    },

    'file:sftp': {
      name: 'SFTP',
      description: 'Transfer files via SFTP',
      category: 'data',
      icon: '📤',
      color: '#F59E0B',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'operation',
          type: 'select',
          label: 'Operation',
          default: 'download',
          options: [
            { value: 'download', label: 'Download' },
            { value: 'upload', label: 'Upload' },
            { value: 'list', label: 'List Directory' },
            { value: 'delete', label: 'Delete' },
            { value: 'rename', label: 'Rename/Move' },
          ],
        },
        {
          id: 'host',
          type: 'text',
          label: 'Host',
          default: '',
          required: true,
        },
        {
          id: 'port',
          type: 'number',
          label: 'Port',
          default: 22,
          min: 1,
          max: 65535,
        },
        {
          id: 'username',
          type: 'text',
          label: 'Username',
          default: '',
          required: true,
        },
        {
          id: 'auth_type',
          type: 'select',
          label: 'Authentication',
          default: 'password',
          options: [
            { value: 'password', label: 'Password' },
            { value: 'key', label: 'Private Key' },
          ],
        },
        {
          id: 'password',
          type: 'password',
          label: 'Password',
          default: '',
          showIf: { field: 'auth_type', value: 'password' },
        },
        {
          id: 'private_key',
          type: 'textarea',
          label: 'Private Key',
          default: '',
          showIf: { field: 'auth_type', value: 'key' },
        },
        {
          id: 'remote_path',
          type: 'text',
          label: 'Remote Path',
          default: '/',
          required: true,
        },
        {
          id: 'local_path',
          type: 'text',
          label: 'Local Path',
          default: '',
          showIf: { field: 'operation', value: ['download', 'upload'] },
        },
        {
          id: 'new_path',
          type: 'text',
          label: 'New Path',
          default: '',
          showIf: { field: 'operation', value: 'rename' },
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'sftp',
        context: 'remote_ssh',
        platform: 'any',
        requirements: {
          connection: 'ssh',
          credentials: ['ssh_credentials'],
        },
      },
    },

    'file:ftp': {
      name: 'FTP',
      description: 'Transfer files via FTP',
      category: 'data',
      icon: '📂',
      color: '#F59E0B',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'operation',
          type: 'select',
          label: 'Operation',
          default: 'download',
          options: [
            { value: 'download', label: 'Download' },
            { value: 'upload', label: 'Upload' },
            { value: 'list', label: 'List Directory' },
            { value: 'delete', label: 'Delete' },
          ],
        },
        {
          id: 'host',
          type: 'text',
          label: 'Host',
          default: '',
          required: true,
        },
        {
          id: 'port',
          type: 'number',
          label: 'Port',
          default: 21,
          min: 1,
          max: 65535,
        },
        {
          id: 'username',
          type: 'text',
          label: 'Username',
          default: '',
        },
        {
          id: 'password',
          type: 'password',
          label: 'Password',
          default: '',
        },
        {
          id: 'secure',
          type: 'checkbox',
          label: 'Use FTPS (TLS)',
          default: false,
        },
        {
          id: 'remote_path',
          type: 'text',
          label: 'Remote Path',
          default: '/',
          required: true,
        },
        {
          id: 'local_path',
          type: 'text',
          label: 'Local Path',
          default: '',
          showIf: { field: 'operation', value: ['download', 'upload'] },
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'ftp',
        context: 'remote_api',
        platform: 'any',
        requirements: {
          network: true,
        },
      },
    },

    'file:s3': {
      name: 'AWS S3',
      description: 'Read and write files to AWS S3',
      category: 'data',
      icon: '☁️',
      color: '#FF9900',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'operation',
          type: 'select',
          label: 'Operation',
          default: 'get',
          options: [
            { value: 'get', label: 'Get Object' },
            { value: 'put', label: 'Put Object' },
            { value: 'list', label: 'List Objects' },
            { value: 'delete', label: 'Delete Object' },
            { value: 'copy', label: 'Copy Object' },
          ],
        },
        {
          id: 'bucket',
          type: 'text',
          label: 'Bucket',
          default: '',
          required: true,
        },
        {
          id: 'key',
          type: 'text',
          label: 'Object Key',
          default: '',
          showIf: { field: 'operation', value: ['get', 'put', 'delete', 'copy'] },
        },
        {
          id: 'prefix',
          type: 'text',
          label: 'Prefix',
          default: '',
          showIf: { field: 'operation', value: 'list' },
        },
        {
          id: 'destination_bucket',
          type: 'text',
          label: 'Destination Bucket',
          default: '',
          showIf: { field: 'operation', value: 'copy' },
        },
        {
          id: 'destination_key',
          type: 'text',
          label: 'Destination Key',
          default: '',
          showIf: { field: 'operation', value: 'copy' },
        },
        {
          id: 'region',
          type: 'text',
          label: 'Region',
          default: 'us-east-1',
        },
        {
          id: 'access_key_id',
          type: 'text',
          label: 'Access Key ID',
          default: '',
        },
        {
          id: 'secret_access_key',
          type: 'password',
          label: 'Secret Access Key',
          default: '',
        },
      ],
      
      execution: {
        type: 'action',
        executor: 's3',
        context: 'remote_api',
        platform: 'any',
        requirements: {
          network: true,
          credentials: ['aws_credentials'],
        },
      },
    },
  },
};
