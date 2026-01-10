/**
 * Notifications Package
 * 
 * Nodes for sending notifications:
 * - Email
 * - Slack
 * - Webhook
 * - Log
 */

import { PLATFORMS } from '../platforms';

// Notification nodes are platform-agnostic
const notifyPlatform = {
  platforms: [PLATFORMS.ANY],
  protocols: [],
};

export default {
  id: 'notifications',
  name: 'Notifications',
  description: 'Send notifications via email, Slack, webhooks, and logging',
  version: '1.0.0',
  icon: '📧',
  color: '#EC4899',
  
  nodes: {
    'notify:email': {
      name: 'Send Email',
      description: 'Send an email notification',
      category: 'output',
      subcategory: 'output',
      subcategory: 'notify',
      ...notifyPlatform,
      icon: '📧',
      color: '#EC4899',
      ...notifyPlatform,
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'data', type: 'any', label: 'Data for Template' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
      ],
      
      parameters: [
        {
          id: 'to',
          type: 'text',
          label: 'To',
          default: '',
          required: true,
          placeholder: 'user@example.com',
          help: 'Comma-separated email addresses',
        },
        {
          id: 'cc',
          type: 'text',
          label: 'CC',
          default: '',
        },
        {
          id: 'subject',
          type: 'text',
          label: 'Subject',
          default: 'OpsConductor Notification',
          required: true,
          help: 'Supports variables: {{workflow.name}}, {{status}}, etc.',
        },
        {
          id: 'body_type',
          type: 'select',
          label: 'Body Type',
          default: 'text',
          options: [
            { value: 'text', label: 'Plain Text' },
            { value: 'html', label: 'HTML' },
            { value: 'template', label: 'Template' },
          ],
        },
        {
          id: 'body',
          type: 'textarea',
          label: 'Body',
          default: 'Workflow {{workflow.name}} completed.\n\nStatus: {{status}}\nDuration: {{duration}}',
          showIf: { field: 'body_type', values: ['text', 'html'] },
        },
        {
          id: 'template_id',
          type: 'select',
          label: 'Email Template',
          default: '',
          showIf: { field: 'body_type', value: 'template' },
          options: [
            { value: 'job_success', label: 'Job Success' },
            { value: 'job_failure', label: 'Job Failure' },
            { value: 'alert', label: 'Alert' },
            { value: 'report', label: 'Report' },
          ],
        },
      ],
      
      advanced: [
        {
          id: 'from',
          type: 'text',
          label: 'From Address',
          default: '',
          help: 'Leave empty to use system default',
        },
        {
          id: 'priority',
          type: 'select',
          label: 'Priority',
          default: 'normal',
          options: [
            { value: 'low', label: 'Low' },
            { value: 'normal', label: 'Normal' },
            { value: 'high', label: 'High' },
          ],
        },
        {
          id: 'attach_data',
          type: 'checkbox',
          label: 'Attach Data as JSON',
          default: false,
        },
      ],
      
      execution: {
        type: 'notify',
        executor: 'email',
        context: 'local',
        platform: 'any',
        requirements: {
          network: true,
          credentials: ['smtp_credentials'],
        },
      },
    },

    'notify:slack': {
      name: 'Send Slack Message',
      description: 'Send a message to a Slack channel',
      category: 'output',
      subcategory: 'notify',
      ...notifyPlatform,
      icon: '💬',
      color: '#4A154B',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'data', type: 'any', label: 'Data for Message' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
      ],
      
      parameters: [
        {
          id: 'channel',
          type: 'text',
          label: 'Channel',
          default: '#general',
          required: true,
          help: 'Channel name (with #) or channel ID',
        },
        {
          id: 'message_type',
          type: 'select',
          label: 'Message Type',
          default: 'simple',
          options: [
            { value: 'simple', label: 'Simple Text' },
            { value: 'blocks', label: 'Block Kit' },
            { value: 'template', label: 'Template' },
          ],
        },
        {
          id: 'message',
          type: 'textarea',
          label: 'Message',
          default: '✅ Workflow *{{workflow.name}}* completed successfully',
          showIf: { field: 'message_type', value: 'simple' },
          help: 'Supports Slack markdown and variables',
        },
        {
          id: 'blocks',
          type: 'code',
          label: 'Block Kit JSON',
          default: '[]',
          language: 'json',
          showIf: { field: 'message_type', value: 'blocks' },
        },
        {
          id: 'template',
          type: 'select',
          label: 'Message Template',
          default: 'job_complete',
          showIf: { field: 'message_type', value: 'template' },
          options: [
            { value: 'job_complete', label: 'Job Complete' },
            { value: 'job_failed', label: 'Job Failed' },
            { value: 'alert', label: 'Alert' },
            { value: 'discovery_report', label: 'Discovery Report' },
          ],
        },
        {
          id: 'username',
          type: 'text',
          label: 'Bot Username',
          default: 'OpsConductor',
        },
        {
          id: 'icon_emoji',
          type: 'text',
          label: 'Icon Emoji',
          default: ':robot_face:',
        },
      ],
      
      advanced: [
        {
          id: 'thread_ts',
          type: 'text',
          label: 'Thread Timestamp',
          default: '',
          help: 'Reply to a specific thread',
        },
        {
          id: 'unfurl_links',
          type: 'checkbox',
          label: 'Unfurl Links',
          default: false,
        },
      ],
      
      execution: {
        type: 'notify',
        executor: 'slack',
        context: 'local',
        platform: 'any',
        requirements: {
          network: true,
          credentials: ['slack_credentials'],
        },
      },
    },

    'notify:webhook': {
      name: 'Send Webhook',
      description: 'Send an HTTP webhook to an external service',
      category: 'output',
      subcategory: 'notify',
      ...notifyPlatform,
      icon: '🔗',
      color: '#6366F1',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'data', type: 'any', label: 'Data to Send' },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Failure' },
        { id: 'response', type: 'object', label: 'Response' },
      ],
      
      parameters: [
        {
          id: 'url',
          type: 'text',
          label: 'Webhook URL',
          default: '',
          required: true,
          placeholder: 'https://example.com/webhook',
        },
        {
          id: 'method',
          type: 'select',
          label: 'HTTP Method',
          default: 'POST',
          options: [
            { value: 'GET', label: 'GET' },
            { value: 'POST', label: 'POST' },
            { value: 'PUT', label: 'PUT' },
            { value: 'PATCH', label: 'PATCH' },
          ],
        },
        {
          id: 'content_type',
          type: 'select',
          label: 'Content Type',
          default: 'application/json',
          options: [
            { value: 'application/json', label: 'JSON' },
            { value: 'application/x-www-form-urlencoded', label: 'Form URL Encoded' },
            { value: 'text/plain', label: 'Plain Text' },
          ],
        },
        {
          id: 'body_source',
          type: 'select',
          label: 'Body Source',
          default: 'from_input',
          options: [
            { value: 'from_input', label: 'From Input Data' },
            { value: 'custom', label: 'Custom Body' },
          ],
        },
        {
          id: 'body_expression',
          type: 'expression',
          label: 'Body Expression',
          default: '{{data}}',
          showIf: { field: 'body_source', value: 'from_input' },
        },
        {
          id: 'custom_body',
          type: 'code',
          label: 'Custom Body',
          default: '{\n  "workflow": "{{workflow.name}}",\n  "status": "{{status}}"\n}',
          language: 'json',
          showIf: { field: 'body_source', value: 'custom' },
        },
        {
          id: 'headers',
          type: 'key-value',
          label: 'Headers',
          default: {},
        },
        {
          id: 'timeout',
          type: 'number',
          label: 'Timeout (seconds)',
          default: 30,
          min: 1,
          max: 300,
        },
      ],
      
      advanced: [
        {
          id: 'auth_type',
          type: 'select',
          label: 'Authentication',
          default: 'none',
          options: [
            { value: 'none', label: 'None' },
            { value: 'basic', label: 'Basic Auth' },
            { value: 'bearer', label: 'Bearer Token' },
            { value: 'api_key', label: 'API Key' },
          ],
        },
        {
          id: 'auth_username',
          type: 'text',
          label: 'Username',
          default: '',
          showIf: { field: 'auth_type', value: 'basic' },
        },
        {
          id: 'auth_password',
          type: 'password',
          label: 'Password',
          default: '',
          showIf: { field: 'auth_type', value: 'basic' },
          sensitive: true,
        },
        {
          id: 'bearer_token',
          type: 'password',
          label: 'Bearer Token',
          default: '',
          showIf: { field: 'auth_type', value: 'bearer' },
          sensitive: true,
        },
        {
          id: 'api_key_header',
          type: 'text',
          label: 'API Key Header',
          default: 'X-API-Key',
          showIf: { field: 'auth_type', value: 'api_key' },
        },
        {
          id: 'api_key_value',
          type: 'password',
          label: 'API Key',
          default: '',
          showIf: { field: 'auth_type', value: 'api_key' },
          sensitive: true,
        },
        {
          id: 'retry_count',
          type: 'number',
          label: 'Retry Count',
          default: 0,
          min: 0,
          max: 5,
        },
      ],
      
      execution: {
        type: 'notify',
        executor: 'webhook',
        context: 'local',
        platform: 'any',
        requirements: {
          network: true,
        },
      },
    },

    'notify:log': {
      name: 'Log Message',
      description: 'Write a message to the workflow log',
      category: 'output',
      subcategory: 'notify',
      ...notifyPlatform,
      icon: '📝',
      color: '#6B7280',
      
      inputs: [
        { id: 'trigger', type: 'trigger', label: 'Trigger', required: true },
        { id: 'data', type: 'any', label: 'Data to Log' },
      ],
      outputs: [
        { id: 'trigger', type: 'trigger', label: 'Continue' },
      ],
      
      parameters: [
        {
          id: 'level',
          type: 'select',
          label: 'Log Level',
          default: 'info',
          options: [
            { value: 'debug', label: 'Debug' },
            { value: 'info', label: 'Info' },
            { value: 'warning', label: 'Warning' },
            { value: 'error', label: 'Error' },
          ],
        },
        {
          id: 'message',
          type: 'textarea',
          label: 'Message',
          default: 'Workflow checkpoint: {{workflow.name}}',
          help: 'Supports variables',
        },
        {
          id: 'include_data',
          type: 'checkbox',
          label: 'Include Input Data',
          default: true,
        },
        {
          id: 'data_expression',
          type: 'expression',
          label: 'Data to Include',
          default: '{{data}}',
          showIf: { field: 'include_data', value: true },
        },
      ],
      
      execution: {
        type: 'notify',
        executor: 'log',
        context: 'internal',
        platform: 'any',
        requirements: {},
      },
    },
  },
};
