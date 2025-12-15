/**
 * Parser/Format Package
 * 
 * Nodes for parsing and formatting data:
 * - JSON Parse/Stringify
 * - CSV Parse/Generate
 * - XML Parse
 * - Regex Extract
 * - Template
 */

export default {
  id: 'parser-format',
  name: 'Parser / Format',
  description: 'Parse and format data between different formats',
  version: '1.0.0',
  icon: '📋',
  color: '#6366F1',
  
  nodes: {
    'parse:json': {
      name: 'JSON',
      description: 'Parse JSON string or stringify object to JSON',
      category: 'data',
      icon: '{ }',
      color: '#6366F1',
      
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
          default: 'parse',
          options: [
            { value: 'parse', label: 'Parse (String → Object)' },
            { value: 'stringify', label: 'Stringify (Object → String)' },
          ],
        },
        {
          id: 'source_field',
          type: 'text',
          label: 'Source Field',
          default: 'data',
          required: true,
        },
        {
          id: 'destination_field',
          type: 'text',
          label: 'Destination Field',
          default: 'parsed',
        },
        {
          id: 'pretty',
          type: 'checkbox',
          label: 'Pretty Print',
          default: false,
          showIf: { field: 'operation', value: 'stringify' },
        },
      ],
      
      execution: {
        type: 'transform',
        executor: 'json_parse',
      },
    },

    'parse:csv': {
      name: 'CSV',
      description: 'Parse CSV to objects or generate CSV from objects',
      category: 'data',
      icon: '📊',
      color: '#6366F1',
      
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
          default: 'parse',
          options: [
            { value: 'parse', label: 'Parse (CSV → Objects)' },
            { value: 'generate', label: 'Generate (Objects → CSV)' },
          ],
        },
        {
          id: 'source_field',
          type: 'text',
          label: 'Source Field',
          default: 'data',
          required: true,
        },
        {
          id: 'destination_field',
          type: 'text',
          label: 'Destination Field',
          default: 'rows',
        },
        {
          id: 'delimiter',
          type: 'text',
          label: 'Delimiter',
          default: ',',
        },
        {
          id: 'has_header',
          type: 'checkbox',
          label: 'First Row is Header',
          default: true,
          showIf: { field: 'operation', value: 'parse' },
        },
        {
          id: 'include_header',
          type: 'checkbox',
          label: 'Include Header Row',
          default: true,
          showIf: { field: 'operation', value: 'generate' },
        },
        {
          id: 'columns',
          type: 'text-list',
          label: 'Columns (optional)',
          default: [],
          help: 'Specify column order for generation',
          showIf: { field: 'operation', value: 'generate' },
        },
      ],
      
      execution: {
        type: 'transform',
        executor: 'csv_parse',
      },
    },

    'parse:xml': {
      name: 'XML',
      description: 'Parse XML to objects or generate XML from objects',
      category: 'data',
      icon: '📄',
      color: '#6366F1',
      
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
          default: 'parse',
          options: [
            { value: 'parse', label: 'Parse (XML → Object)' },
            { value: 'generate', label: 'Generate (Object → XML)' },
          ],
        },
        {
          id: 'source_field',
          type: 'text',
          label: 'Source Field',
          default: 'data',
          required: true,
        },
        {
          id: 'destination_field',
          type: 'text',
          label: 'Destination Field',
          default: 'parsed',
        },
        {
          id: 'attribute_prefix',
          type: 'text',
          label: 'Attribute Prefix',
          default: '@',
          showIf: { field: 'operation', value: 'parse' },
        },
        {
          id: 'text_node_name',
          type: 'text',
          label: 'Text Node Name',
          default: '#text',
          showIf: { field: 'operation', value: 'parse' },
        },
        {
          id: 'root_element',
          type: 'text',
          label: 'Root Element',
          default: 'root',
          showIf: { field: 'operation', value: 'generate' },
        },
      ],
      
      execution: {
        type: 'transform',
        executor: 'xml_parse',
      },
    },

    'parse:regex': {
      name: 'Regex Extract',
      description: 'Extract data using regular expressions',
      category: 'data',
      icon: '🔤',
      color: '#6366F1',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'matched', type: 'trigger', label: 'Matched' },
        { id: 'unmatched', type: 'trigger', label: 'Not Matched' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'source_field',
          type: 'text',
          label: 'Source Field',
          default: 'text',
          required: true,
        },
        {
          id: 'pattern',
          type: 'text',
          label: 'Regex Pattern',
          default: '',
          required: true,
          placeholder: '(\\d+)-(\\w+)',
        },
        {
          id: 'flags',
          type: 'text',
          label: 'Flags',
          default: 'g',
          help: 'g=global, i=case-insensitive, m=multiline',
        },
        {
          id: 'output_mode',
          type: 'select',
          label: 'Output Mode',
          default: 'groups',
          options: [
            { value: 'groups', label: 'Named/Numbered Groups' },
            { value: 'all_matches', label: 'All Matches (array)' },
            { value: 'first_match', label: 'First Match Only' },
            { value: 'boolean', label: 'Boolean (matched or not)' },
          ],
        },
        {
          id: 'group_names',
          type: 'text-list',
          label: 'Group Names',
          default: [],
          help: 'Names for captured groups (in order)',
          showIf: { field: 'output_mode', value: 'groups' },
        },
      ],
      
      execution: {
        type: 'transform',
        executor: 'regex_extract',
      },
    },

    'parse:template': {
      name: 'Template',
      description: 'Generate text using templates with variable substitution',
      category: 'data',
      icon: '📝',
      color: '#6366F1',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'output', type: 'trigger', label: 'Output' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'template',
          type: 'code',
          label: 'Template',
          default: 'Hello {{name}}, your order #{{order_id}} is ready.',
          language: 'handlebars',
          required: true,
        },
        {
          id: 'output_field',
          type: 'text',
          label: 'Output Field',
          default: 'result',
        },
        {
          id: 'syntax',
          type: 'select',
          label: 'Template Syntax',
          default: 'handlebars',
          options: [
            { value: 'handlebars', label: 'Handlebars ({{variable}})' },
            { value: 'dollar', label: 'Dollar (${variable})' },
          ],
        },
      ],
      
      execution: {
        type: 'transform',
        executor: 'template',
      },
    },

    'parse:html-extract': {
      name: 'HTML Extract',
      description: 'Extract data from HTML using CSS selectors',
      category: 'data',
      icon: '🌐',
      color: '#6366F1',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'success', type: 'trigger', label: 'On Success' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'source_field',
          type: 'text',
          label: 'HTML Source Field',
          default: 'html',
          required: true,
        },
        {
          id: 'extractions',
          type: 'extraction-list',
          label: 'Extractions',
          default: [
            { selector: 'h1', attribute: 'text', output_name: 'title' },
          ],
          help: 'Define CSS selectors and what to extract',
        },
      ],
      
      execution: {
        type: 'transform',
        executor: 'html_extract',
      },
    },

    'parse:markdown': {
      name: 'Markdown',
      description: 'Convert between Markdown and HTML',
      category: 'data',
      icon: '📑',
      color: '#6366F1',
      
      inputs: [
        { id: 'input', type: 'trigger', label: 'Input', required: true },
      ],
      outputs: [
        { id: 'output', type: 'trigger', label: 'Output' },
        { id: 'failure', type: 'trigger', label: 'On Error' },
      ],
      
      parameters: [
        {
          id: 'operation',
          type: 'select',
          label: 'Operation',
          default: 'to_html',
          options: [
            { value: 'to_html', label: 'Markdown → HTML' },
            { value: 'to_markdown', label: 'HTML → Markdown' },
          ],
        },
        {
          id: 'source_field',
          type: 'text',
          label: 'Source Field',
          default: 'content',
          required: true,
        },
        {
          id: 'destination_field',
          type: 'text',
          label: 'Destination Field',
          default: 'converted',
        },
      ],
      
      execution: {
        type: 'transform',
        executor: 'markdown',
      },
    },
  },
};
