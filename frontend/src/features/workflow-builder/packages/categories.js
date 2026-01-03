/**
 * Node Categories
 * 
 * Defines the hierarchical organization of workflow nodes.
 * Categories are action-based for intuitive user navigation.
 */

export const CATEGORIES = {
  triggers: {
    id: 'triggers',
    name: 'Triggers',
    icon: '🚀',
    color: '#8B5CF6',
    description: 'Start workflows manually, on schedule, or via events',
    order: 1,
  },
  discover: {
    id: 'discover',
    name: 'Discover',
    icon: '🔍',
    color: '#3B82F6',
    description: 'Find devices, collect information, query systems',
    order: 2,
    subcategories: {
      network: { name: 'Network Scanning', icon: '📡' },
      snmp: { name: 'SNMP', icon: '📊' },
      dns: { name: 'DNS & Hostname', icon: '🏷️' },
      inventory: { name: 'Inventory Queries', icon: '🗄️' },
    },
  },
  configure: {
    id: 'configure',
    name: 'Configure',
    icon: '⚙️',
    color: '#10B981',
    description: 'Execute commands, make changes, manage devices',
    order: 3,
    subcategories: {
      remote: { name: 'Remote Execution', icon: '🔐' },
      netbox: { name: 'NetBox Management', icon: '🗄️' },
      snmp: { name: 'SNMP Configuration', icon: '📊' },
      api: { name: 'API Calls', icon: '🔌' },
      templates: { name: 'Vendor Templates', icon: '📋' },
    },
  },
  logic: {
    id: 'logic',
    name: 'Logic',
    icon: '🔀',
    color: '#F59E0B',
    description: 'Control flow, conditions, loops, error handling',
    order: 4,
    subcategories: {
      conditional: { name: 'Conditions', icon: '❓' },
      flow: { name: 'Flow Control', icon: '🔄' },
      error: { name: 'Error Handling', icon: '⚠️' },
    },
  },
  data: {
    id: 'data',
    name: 'Data',
    icon: '📊',
    color: '#EC4899',
    description: 'Transform, parse, store, and manipulate data',
    order: 5,
    subcategories: {
      variables: { name: 'Variables', icon: '📝' },
      transform: { name: 'Transform', icon: '🔄' },
      parse: { name: 'Parse & Format', icon: '📄' },
      database: { name: 'Database', icon: '💾' },
      files: { name: 'Files', icon: '📁' },
    },
  },
  output: {
    id: 'output',
    name: 'Output',
    icon: '📣',
    color: '#EF4444',
    description: 'Send notifications, export data, log results',
    order: 6,
    subcategories: {
      notify: { name: 'Notifications', icon: '🔔' },
      export: { name: 'Export', icon: '📤' },
      log: { name: 'Logging', icon: '📝' },
    },
  },
};

/**
 * Get category by ID
 */
export function getCategory(categoryId) {
  return CATEGORIES[categoryId] || null;
}

/**
 * Get all categories sorted by order
 */
export function getSortedCategories() {
  return Object.values(CATEGORIES).sort((a, b) => a.order - b.order);
}

export default CATEGORIES;
