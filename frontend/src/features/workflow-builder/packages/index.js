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
import dataTransformPackage from './data-transform';
import flowControlPackage from './flow-control';
import httpApiPackage from './http-api';
import fileStoragePackage from './file-storage';
import schedulingPackage from './scheduling';
import parserFormatPackage from './parser-format';
import debugUtilityPackage from './debug-utility';
import axisCamerasPackage from './axis-cameras';
import windowsSystemsPackage from './windows-systems';

// All available packages
export const PACKAGES = {
  'core': corePackage,
  'network-discovery': networkDiscoveryPackage,
  'snmp': snmpPackage,
  'ssh': sshPackage,
  'database': databasePackage,
  'notifications': notificationsPackage,
  'ciena-saos': cienaSaosPackage,
  'data-transform': dataTransformPackage,
  'flow-control': flowControlPackage,
  'http-api': httpApiPackage,
  'file-storage': fileStoragePackage,
  'scheduling': schedulingPackage,
  'parser-format': parserFormatPackage,
  'debug-utility': debugUtilityPackage,
  'axis-cameras': axisCamerasPackage,
  'windows-systems': windowsSystemsPackage,
};

// Default enabled packages - export this so other components can use it
export const DEFAULT_ENABLED_PACKAGES = [
  'core',
  'network-discovery',
  'snmp',
  'ssh',
  'database',
  'notifications',
  'ciena-saos',
  'data-transform',
  'flow-control',
  'http-api',
  'file-storage',
  'scheduling',
  'parser-format',
  'debug-utility',
  'axis-cameras',
  'windows-systems',
];

/**
 * Get list of enabled packages
 * @param {string[]} enabledIds - Array of enabled package IDs (from settings)
 * @returns {Object[]} Array of enabled package definitions
 */
export function getEnabledPackages(enabledIds = DEFAULT_ENABLED_PACKAGES) {
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
 * Get all nodes from a specific package
 * @param {string} packageId - Package ID
 * @returns {Object[]} Array of node definitions from that package
 */
export function getNodesByPackage(packageId) {
  const pkg = PACKAGES[packageId];
  if (!pkg || !pkg.nodes) return [];
  
  return Object.entries(pkg.nodes).map(([nodeId, nodeDef]) => ({
    id: nodeId,
    ...nodeDef,
    packageId,
    packageName: pkg.name,
  }));
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
  getNodesByPackage,
};
