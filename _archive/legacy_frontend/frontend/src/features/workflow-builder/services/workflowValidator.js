/**
 * Workflow Validator Service
 * 
 * Validates workflow configurations for:
 * - Platform compatibility between nodes
 * - Required connections
 * - Parameter validation
 * - Credential requirements
 */

import { getNodeDefinition } from '../packages';
import { checkPlatformCompatibility, PLATFORMS, getPlatformInfo } from '../platforms';

/**
 * Validation result types
 */
export const ValidationSeverity = {
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info',
};

/**
 * Validate a single node's configuration
 */
export function validateNode(node, nodeDefinition) {
  const issues = [];
  
  if (!nodeDefinition) {
    issues.push({
      nodeId: node.id,
      severity: ValidationSeverity.ERROR,
      message: `Unknown node type: ${node.data?.nodeType}`,
      field: null,
    });
    return issues;
  }
  
  // Check required parameters
  const parameters = nodeDefinition.parameters || [];
  const nodeParams = node.data?.parameters || {};
  
  for (const param of parameters) {
    if (param.required && !nodeParams[param.id]) {
      issues.push({
        nodeId: node.id,
        severity: ValidationSeverity.ERROR,
        message: `Required parameter "${param.label}" is missing`,
        field: param.id,
      });
    }
  }
  
  return issues;
}

/**
 * Check platform compatibility between connected nodes
 */
export function checkNodeCompatibility(sourceNode, targetNode, sourceDefinition, targetDefinition) {
  const issues = [];
  
  if (!sourceDefinition || !targetDefinition) {
    return issues;
  }
  
  const sourcePlatforms = sourceDefinition.platforms || [PLATFORMS.ANY];
  const targetPlatforms = targetDefinition.platforms || [PLATFORMS.ANY];
  
  // If either node is platform-agnostic, they're compatible
  if (sourcePlatforms.includes(PLATFORMS.ANY) || targetPlatforms.includes(PLATFORMS.ANY)) {
    return issues;
  }
  
  // Check if there's any overlap in platforms
  const compatibility = checkPlatformCompatibility(targetPlatforms, sourcePlatforms);
  
  if (!compatibility.compatible && !compatibility.partiallyCompatible) {
    const sourcePlatformNames = sourcePlatforms.map(p => getPlatformInfo(p).name).join(', ');
    const targetPlatformNames = targetPlatforms.map(p => getPlatformInfo(p).name).join(', ');
    
    issues.push({
      sourceNodeId: sourceNode.id,
      targetNodeId: targetNode.id,
      severity: ValidationSeverity.WARNING,
      message: `Platform mismatch: "${sourceDefinition.name}" outputs ${sourcePlatformNames} but "${targetDefinition.name}" requires ${targetPlatformNames}`,
      type: 'platform_mismatch',
    });
  }
  
  return issues;
}

/**
 * Validate an entire workflow
 */
export function validateWorkflow(nodes, edges) {
  const issues = [];
  const nodeMap = new Map(nodes.map(n => [n.id, n]));
  const definitionMap = new Map();
  
  // Get definitions for all nodes
  for (const node of nodes) {
    const definition = getNodeDefinition(node.data?.nodeType);
    definitionMap.set(node.id, definition);
    
    // Validate individual node
    const nodeIssues = validateNode(node, definition);
    issues.push(...nodeIssues);
  }
  
  // Check edge compatibility
  for (const edge of edges) {
    const sourceNode = nodeMap.get(edge.source);
    const targetNode = nodeMap.get(edge.target);
    
    if (!sourceNode || !targetNode) continue;
    
    const sourceDefinition = definitionMap.get(edge.source);
    const targetDefinition = definitionMap.get(edge.target);
    
    const edgeIssues = checkNodeCompatibility(
      sourceNode, 
      targetNode, 
      sourceDefinition, 
      targetDefinition
    );
    issues.push(...edgeIssues);
  }
  
  // Check for disconnected nodes (except triggers)
  for (const node of nodes) {
    const definition = definitionMap.get(node.id);
    if (!definition) continue;
    
    // Triggers don't need inputs
    if (definition.category === 'triggers') continue;
    
    // Check if node has any incoming edges
    const hasInput = edges.some(e => e.target === node.id);
    if (!hasInput) {
      issues.push({
        nodeId: node.id,
        severity: ValidationSeverity.WARNING,
        message: `Node "${definition.name}" has no input connection`,
        type: 'disconnected',
      });
    }
  }
  
  return issues;
}

/**
 * Get a summary of validation issues
 */
export function getValidationSummary(issues) {
  const errors = issues.filter(i => i.severity === ValidationSeverity.ERROR);
  const warnings = issues.filter(i => i.severity === ValidationSeverity.WARNING);
  const infos = issues.filter(i => i.severity === ValidationSeverity.INFO);
  
  return {
    isValid: errors.length === 0,
    hasWarnings: warnings.length > 0,
    errorCount: errors.length,
    warningCount: warnings.length,
    infoCount: infos.length,
    errors,
    warnings,
    infos,
    all: issues,
  };
}

/**
 * Check if a workflow can be saved (has no blocking errors)
 */
export function canSaveWorkflow(nodes, edges) {
  const issues = validateWorkflow(nodes, edges);
  const summary = getValidationSummary(issues);
  return {
    canSave: summary.isValid,
    issues: summary,
  };
}

/**
 * Get platform compatibility warnings for a specific edge
 */
export function getEdgeCompatibilityWarning(sourceNodeType, targetNodeType) {
  const sourceDefinition = getNodeDefinition(sourceNodeType);
  const targetDefinition = getNodeDefinition(targetNodeType);
  
  if (!sourceDefinition || !targetDefinition) {
    return null;
  }
  
  const sourcePlatforms = sourceDefinition.platforms || [PLATFORMS.ANY];
  const targetPlatforms = targetDefinition.platforms || [PLATFORMS.ANY];
  
  // If either node is platform-agnostic, they're compatible
  if (sourcePlatforms.includes(PLATFORMS.ANY) || targetPlatforms.includes(PLATFORMS.ANY)) {
    return null;
  }
  
  // Check compatibility
  const compatibility = checkPlatformCompatibility(targetPlatforms, sourcePlatforms);
  
  if (!compatibility.compatible) {
    return {
      compatible: false,
      partiallyCompatible: compatibility.partiallyCompatible,
      message: compatibility.partiallyCompatible
        ? `Some platforms may not be compatible`
        : `Platform mismatch between nodes`,
      sourcePlatforms: sourcePlatforms.map(p => getPlatformInfo(p)),
      targetPlatforms: targetPlatforms.map(p => getPlatformInfo(p)),
    };
  }
  
  return null;
}

export default {
  validateNode,
  validateWorkflow,
  getValidationSummary,
  canSaveWorkflow,
  checkNodeCompatibility,
  getEdgeCompatibilityWarning,
  ValidationSeverity,
};
