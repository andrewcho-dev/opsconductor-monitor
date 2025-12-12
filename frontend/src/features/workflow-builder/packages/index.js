/**
 * Node Package Registry
 * 
 * Central registry for all node packages and their definitions.
 * Packages can be enabled/disabled via settings.
 */

import corePackage from './core';
import networkDiscoveryPackage from './network-discovery';
import snmpPackage from './snmp';
import sshPackage from './ssh';
import databasePackage from './database';
import notificationsPackage from './notifications';
import cienaSaosPackage from './ciena-saos';

// All available packages
export const PACKAGES = {
  'core': corePackage,
  'network-discovery': networkDiscoveryPackage,
  'snmp': snmpPackage,
  'ssh': sshPackage,
  'database': databasePackage,
  'notifications': notificationsPackage,
  'ciena-saos': cienaSaosPackage,
};

// Default enabled packages
const DEFAULT_ENABLED = [
  'core',
  'network-discovery',
  'snmp',
  'ssh',
  'database',
  'notifications',
  'ciena-saos',
];

/**
 * Get list of enabled packages
 * @param {string[]} enabledIds - Array of enabled package IDs (from settings)
 * @returns {Object[]} Array of enabled package definitions
 */
export function getEnabledPackages(enabledIds = DEFAULT_ENABLED) {
  return enabledIds
    .filter(id => PACKAGES[id])
    .map(id => ({ id, ...PACKAGES[id] }));
}

/**
 * Get all available packages (for settings UI)
 * @returns {Object[]} Array of all package definitions with their IDs
 */
export function getAllPackages() {
  return Object.entries(PACKAGES).map(([id, pkg]) => ({
    id,
    ...pkg,
    isCore: id === 'core',
  }));
}

/**
 * Get a specific node definition by its full ID
 * @param {string} nodeId - Full node ID (e.g., 'network:ping', 'logic:if')
 * @returns {Object|null} Node definition or null if not found
 */
export function getNodeDefinition(nodeId) {
  for (const pkg of Object.values(PACKAGES)) {
    if (pkg.nodes && pkg.nodes[nodeId]) {
      return {
        ...pkg.nodes[nodeId],
        id: nodeId,
        packageId: pkg.id,
        packageName: pkg.name,
      };
    }
  }
  return null;
}

/**
 * Get all nodes from enabled packages, organized by category
 * @param {string[]} enabledIds - Array of enabled package IDs
 * @returns {Object} Nodes organized by category
 */
export function getNodesByCategory(enabledIds = DEFAULT_ENABLED) {
  const categories = {
    triggers: { name: 'Triggers', icon: '🚀', nodes: [] },
    discovery: { name: 'Discovery', icon: '📡', nodes: [] },
    query: { name: 'Query', icon: '🔍', nodes: [] },
    configure: { name: 'Configure', icon: '⚙️', nodes: [] },
    data: { name: 'Data', icon: '💾', nodes: [] },
    logic: { name: 'Logic', icon: '🔀', nodes: [] },
    notify: { name: 'Notify', icon: '📧', nodes: [] },
  };

  for (const pkgId of enabledIds) {
    const pkg = PACKAGES[pkgId];
    if (!pkg || !pkg.nodes) continue;

    for (const [nodeId, nodeDef] of Object.entries(pkg.nodes)) {
      const category = nodeDef.category || 'other';
      if (categories[category]) {
        categories[category].nodes.push({
          id: nodeId,
          ...nodeDef,
          packageId: pkgId,
          packageName: pkg.name,
        });
      }
    }
  }

  // Filter out empty categories
  return Object.fromEntries(
    Object.entries(categories).filter(([, cat]) => cat.nodes.length > 0)
  );
}

export default {
  PACKAGES,
  getEnabledPackages,
  getAllPackages,
  getNodeDefinition,
  getNodesByCategory,
};
