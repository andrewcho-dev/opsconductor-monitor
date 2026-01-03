/**
 * HTTP/API Package
 * 
 * Nodes for making HTTP requests and handling webhooks:
 * - HTTP Request
 * - Webhook Trigger
 * - GraphQL
 * - Respond to Webhook
 */

import { PLATFORMS, PROTOCOLS } from '../platforms';

// HTTP nodes are platform-agnostic
const httpPlatform = {
  platforms: [PLATFORMS.ANY],
  protocols: [PROTOCOLS.HTTP, PROTOCOLS.HTTPS],
};

export default {
  id: 'http-api',
  name: 'HTTP / API',
  description: 'Make HTTP requests and handle webhooks',
  version: '1.0.0',
  icon: '🌐',
  color: '#3B82F6',
  
  nodes: {
    'http:request': {
      name: 'HTTP Request',
      description: 'Make HTTP requests to external APIs',
      category: 'data',
      subcategory: 'api',
      ...httpPlatform,
      subcategory: 'api',
      icon: '🌐',
      color: '#3B82F6',
      ...httpPlatform,
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'method',
          type: 'select',
          label: 'Method',
          default: 'GET',
          options: [
            { value: 'GET', label: 'GET' },
            { value: 'POST', label: 'POST' },
            { value: 'PUT', label: 'PUT' },
            { value: 'PATCH', label: 'PATCH' },
            { value: 'DELETE', label: 'DELETE' },
            { value: 'HEAD', label: 'HEAD' },
            { value: 'OPTIONS', label: 'OPTIONS' },
          ],
        },
        {
          id: 'url',
          type: 'text',
          label: 'URL',
          default: '',
          required: true,
          placeholder: 'https://api.example.com/endpoint',
        },
        {
          id: 'authentication',
          type: 'select',
          label: 'Authentication',
          default: 'none',
          options: [
            { value: 'none', label: 'None' },
            { value: 'basic', label: 'Basic Auth' },
            { value: 'bearer', label: 'Bearer Token' },
            { value: 'api_key', label: 'API Key' },
            { value: 'oauth2', label: 'OAuth2' },
          ],
        },
        {
          id: 'username',
          type: 'text',
          label: 'Username',
          default: '',
          showIf: { field: 'authentication', value: 'basic' },
        },
        {
          id: 'password',
          type: 'password',
          label: 'Password',
          default: '',
          showIf: { field: 'authentication', value: 'basic' },
        },
        {
          id: 'bearer_token',
          type: 'password',
          label: 'Bearer Token',
          default: '',
          showIf: { field: 'authentication', value: 'bearer' },
        },
        {
          id: 'api_key_name',
          type: 'text',
          label: 'API Key Header Name',
          default: 'X-API-Key',
          showIf: { field: 'authentication', value: 'api_key' },
        },
        {
          id: 'api_key_value',
          type: 'password',
          label: 'API Key Value',
          default: '',
          showIf: { field: 'authentication', value: 'api_key' },
        },
        {
          id: 'headers',
          type: 'key-value-list',
          label: 'Headers',
          default: [],
        },
        {
          id: 'query_params',
          type: 'key-value-list',
          label: 'Query Parameters',
          default: [],
        },
        {
          id: 'body_type',
          type: 'select',
          label: 'Body Type',
          default: 'none',
          options: [
            { value: 'none', label: 'None' },
            { value: 'json', label: 'JSON' },
            { value: 'form', label: 'Form Data' },
            { value: 'raw', label: 'Raw' },
          ],
          showIf: { field: 'method', value: ['POST', 'PUT', 'PATCH'] },
        },
        {
          id: 'body_json',
          type: 'code',
          label: 'JSON Body',
          default: '{}',
          language: 'json',
          showIf: { field: 'body_type', value: 'json' },
        },
        {
          id: 'body_form',
          type: 'key-value-list',
          label: 'Form Data',
          default: [],
          showIf: { field: 'body_type', value: 'form' },
        },
        {
          id: 'body_raw',
          type: 'textarea',
          label: 'Raw Body',
          default: '',
          showIf: { field: 'body_type', value: 'raw' },
        },
      ],
      
      advanced: [
        {
          id: 'timeout',
          type: 'number',
          label: 'Timeout (seconds)',
          default: 30,
          min: 1,
          max: 300,
        },
        {
          id: 'follow_redirects',
          type: 'checkbox',
          label: 'Follow Redirects',
          default: true,
        },
        {
          id: 'ignore_ssl',
          type: 'checkbox',
          label: 'Ignore SSL Errors',
          default: false,
        },
        {
          id: 'response_format',
          type: 'select',
          label: 'Response Format',
          default: 'auto',
          options: [
            { value: 'auto', label: 'Auto-detect' },
            { value: 'json', label: 'JSON' },
            { value: 'text', label: 'Text' },
            { value: 'binary', label: 'Binary' },
          ],
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'http_request',
        context: 'local',
        platform: 'any',
        requirements: {
          network: true,
        },
      },
    },

    'http:webhook-trigger': {
      name: 'Webhook Trigger',
      description: 'Trigger workflow when a webhook is received',
      category: 'triggers',
      ...httpPlatform,
      icon: '🪝',
      color: '#3B82F6',
      
      inputs: [],
      outputs: [
        { id: 'output', type: 'trigger', label: 'On Webhook' },
      ],
      
      parameters: [
        {
          id: 'http_method',
          type: 'select',
          label: 'HTTP Method',
          default: 'POST',
          options: [
            { value: 'GET', label: 'GET' },
            { value: 'POST', label: 'POST' },
            { value: 'PUT', label: 'PUT' },
            { value: 'DELETE', label: 'DELETE' },
            { value: 'ANY', label: 'Any Method' },
          ],
        },
        {
          id: 'path',
          type: 'text',
          label: 'Webhook Path',
          default: '/webhook',
          required: true,
          help: 'Path for the webhook endpoint',
        },
        {
          id: 'authentication',
          type: 'select',
          label: 'Authentication',
          default: 'none',
          options: [
            { value: 'none', label: 'None' },
            { value: 'basic', label: 'Basic Auth' },
            { value: 'header', label: 'Header Auth' },
          ],
        },
        {
          id: 'auth_header_name',
          type: 'text',
          label: 'Auth Header Name',
          default: 'X-Webhook-Secret',
          showIf: { field: 'authentication', value: 'header' },
        },
        {
          id: 'auth_header_value',
          type: 'password',
          label: 'Auth Header Value',
          default: '',
          showIf: { field: 'authentication', value: 'header' },
        },
        {
          id: 'response_mode',
          type: 'select',
          label: 'Response Mode',
          default: 'immediately',
          options: [
            { value: 'immediately', label: 'Respond Immediately' },
            { value: 'last_node', label: 'Respond with Last Node Data' },
            { value: 'respond_node', label: 'Use Respond to Webhook Node' },
          ],
        },
        {
          id: 'response_code',
          type: 'number',
          label: 'Response Code',
          default: 200,
          showIf: { field: 'response_mode', value: 'immediately' },
        },
        {
          id: 'response_data',
          type: 'code',
          label: 'Response Data',
          default: '{ "success": true }',
          language: 'json',
          showIf: { field: 'response_mode', value: 'immediately' },
        },
      ],
      
      execution: {
        type: 'trigger',
        executor: 'webhook_trigger',
        context: 'local',
        platform: 'any',
        requirements: {
          network: true,
        },
      },
    },

    'http:respond-webhook': {
      name: 'Respond to Webhook',
      description: 'Send a response back to the webhook caller',
      category: 'data',
      subcategory: 'api',
      ...httpPlatform,
      icon: '↩️',
      color: '#3B82F6',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'output', type: 'trigger', label: 'Output' },
      ],
      
      parameters: [
        {
          id: 'response_code',
          type: 'number',
          label: 'Response Code',
          default: 200,
          min: 100,
          max: 599,
        },
        {
          id: 'response_type',
          type: 'select',
          label: 'Response Type',
          default: 'json',
          options: [
            { value: 'json', label: 'JSON' },
            { value: 'text', label: 'Text' },
            { value: 'html', label: 'HTML' },
            { value: 'redirect', label: 'Redirect' },
          ],
        },
        {
          id: 'response_body',
          type: 'code',
          label: 'Response Body',
          default: '{ "success": true }',
          language: 'json',
          showIf: { field: 'response_type', value: ['json', 'text', 'html'] },
        },
        {
          id: 'redirect_url',
          type: 'text',
          label: 'Redirect URL',
          default: '',
          showIf: { field: 'response_type', value: 'redirect' },
        },
        {
          id: 'headers',
          type: 'key-value-list',
          label: 'Response Headers',
          default: [],
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'respond_webhook',
        context: 'local',
        platform: 'any',
        requirements: {},
      },
    },

    'http:graphql': {
      name: 'GraphQL',
      description: 'Execute GraphQL queries and mutations',
      category: 'data',
      subcategory: 'api',
      ...httpPlatform,
      icon: '◈',
      color: '#E10098',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'endpoint',
          type: 'text',
          label: 'GraphQL Endpoint',
          default: '',
          required: true,
          placeholder: 'https://api.example.com/graphql',
        },
        {
          id: 'operation',
          type: 'select',
          label: 'Operation',
          default: 'query',
          options: [
            { value: 'query', label: 'Query' },
            { value: 'mutation', label: 'Mutation' },
          ],
        },
        {
          id: 'query',
          type: 'code',
          label: 'Query',
          default: `query {
  users {
    id
    name
  }
}`,
          language: 'graphql',
          required: true,
        },
        {
          id: 'variables',
          type: 'code',
          label: 'Variables',
          default: '{}',
          language: 'json',
        },
        {
          id: 'authentication',
          type: 'select',
          label: 'Authentication',
          default: 'none',
          options: [
            { value: 'none', label: 'None' },
            { value: 'bearer', label: 'Bearer Token' },
            { value: 'api_key', label: 'API Key' },
          ],
        },
        {
          id: 'bearer_token',
          type: 'password',
          label: 'Bearer Token',
          default: '',
          showIf: { field: 'authentication', value: 'bearer' },
        },
        {
          id: 'headers',
          type: 'key-value-list',
          label: 'Additional Headers',
          default: [],
        },
      ],
      
      execution: {
        type: 'action',
        executor: 'graphql',
        context: 'local',
        platform: 'any',
        requirements: {
          network: true,
        },
      },
    },
  },
};
