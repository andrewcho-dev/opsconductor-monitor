/**
 * Workflow Validation Utilities
 * 
 * Functions for validating workflow structure and configuration.
 */

import { getNodeDefinition } from '../packages';

/**
 * Validate a complete workflow
 * @param {Object} workflow - The workflow to validate
 * @returns {Object} Validation result with isValid and errors array
 */
export function validateWorkflow(workflow) {
  const errors = [];
  const warnings = [];

  // Check for nodes
  if (!workflow.nodes || workflow.nodes.length === 0) {
    errors.push({
      type: 'structure',
      message: 'Workflow must have at least one node',
    });
    return { isValid: false, errors, warnings };
  }

  // Check for trigger node
  const triggerNodes = workflow.nodes.filter(node => {
    const def = getNodeDefinition(node.data?.nodeType);
    return def?.category === 'triggers';
  });

  if (triggerNodes.length === 0) {
    errors.push({
      type: 'structure',
      message: 'Workflow must have at least one trigger node (Start, Schedule, or Webhook)',
    });
  }

  if (triggerNodes.length > 1) {
    warnings.push({
      type: 'structure',
      message: 'Workflow has multiple trigger nodes. Only one will be used as the entry point.',
    });
  }

  // Check for disconnected nodes
  const connectedNodeIds = new Set();
  workflow.edges.forEach(edge => {
    connectedNodeIds.add(edge.source);
    connectedNodeIds.add(edge.target);
  });

  const disconnectedNodes = workflow.nodes.filter(node => {
    // Trigger nodes don't need incoming connections
    const def = getNodeDefinition(node.data?.nodeType);
    if (def?.category === 'triggers') {
      return !workflow.edges.some(e => e.source === node.id);
    }
    return !connectedNodeIds.has(node.id);
  });

  if (disconnectedNodes.length > 0) {
    warnings.push({
      type: 'structure',
      message: `${disconnectedNodes.length} node(s) are not connected to the workflow`,
      nodeIds: disconnectedNodes.map(n => n.id),
    });
  }

  // Check for circular dependencies (except in loops)
  const circularCheck = detectCircularDependencies(workflow.nodes, workflow.edges);
  if (circularCheck.hasCircular) {
    errors.push({
      type: 'structure',
      message: 'Workflow contains circular dependencies',
      details: circularCheck.cycles,
    });
  }

  // Validate each node
  workflow.nodes.forEach(node => {
    const nodeErrors = validateNode(node);
    errors.push(...nodeErrors.map(e => ({
      ...e,
      nodeId: node.id,
      nodeName: node.data?.label,
    })));
  });

  // Validate edges
  workflow.edges.forEach(edge => {
    const edgeErrors = validateEdge(edge, workflow.nodes);
    errors.push(...edgeErrors.map(e => ({
      ...e,
      edgeId: edge.id,
    })));
  });

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

/**
 * Validate a single node
 * @param {Object} node - The node to validate
 * @returns {Array} Array of error objects
 */
export function validateNode(node) {
  const errors = [];
  const nodeDefinition = getNodeDefinition(node.data?.nodeType);

  if (!nodeDefinition) {
    errors.push({
      type: 'node',
      message: `Unknown node type: ${node.data?.nodeType}`,
    });
    return errors;
  }

  // Check required parameters
  const allParams = [
    ...(nodeDefinition.parameters || []),
    ...(nodeDefinition.advanced || []),
  ];

  allParams.forEach(param => {
    if (param.required) {
      const value = node.data?.parameters?.[param.id];
      if (value === undefined || value === null || value === '') {
        errors.push({
          type: 'parameter',
          field: param.id,
          message: `${param.label} is required`,
        });
      }
    }

    // Type-specific validation
    if (param.type === 'number' && node.data?.parameters?.[param.id] !== undefined) {
      const value = Number(node.data.parameters[param.id]);
      if (isNaN(value)) {
        errors.push({
          type: 'parameter',
          field: param.id,
          message: `${param.label} must be a number`,
        });
      } else {
        if (param.min !== undefined && value < param.min) {
          errors.push({
            type: 'parameter',
            field: param.id,
            message: `${param.label} must be at least ${param.min}`,
          });
        }
        if (param.max !== undefined && value > param.max) {
          errors.push({
            type: 'parameter',
            field: param.id,
            message: `${param.label} must be at most ${param.max}`,
          });
        }
      }
    }
  });

  return errors;
}

/**
 * Validate an edge connection
 * @param {Object} edge - The edge to validate
 * @param {Array} nodes - All nodes in the workflow
 * @returns {Array} Array of error objects
 */
export function validateEdge(edge, nodes) {
  const errors = [];

  const sourceNode = nodes.find(n => n.id === edge.source);
  const targetNode = nodes.find(n => n.id === edge.target);

  if (!sourceNode) {
    errors.push({
      type: 'edge',
      message: `Source node not found: ${edge.source}`,
    });
  }

  if (!targetNode) {
    errors.push({
      type: 'edge',
      message: `Target node not found: ${edge.target}`,
    });
  }

  if (sourceNode && targetNode) {
    const sourceDef = getNodeDefinition(sourceNode.data?.nodeType);
    const targetDef = getNodeDefinition(targetNode.data?.nodeType);

    if (sourceDef && targetDef) {
      const sourceOutput = sourceDef.outputs?.find(o => o.id === edge.sourceHandle);
      const targetInput = targetDef.inputs?.find(i => i.id === edge.targetHandle);

      if (!sourceOutput) {
        errors.push({
          type: 'edge',
          message: `Invalid source handle: ${edge.sourceHandle}`,
        });
      }

      if (!targetInput) {
        errors.push({
          type: 'edge',
          message: `Invalid target handle: ${edge.targetHandle}`,
        });
      }

      // Type compatibility
      if (sourceOutput && targetInput) {
        if (sourceOutput.type === 'trigger' && targetInput.type !== 'trigger') {
          errors.push({
            type: 'edge',
            message: 'Cannot connect trigger output to data input',
          });
        }
      }
    }
  }

  return errors;
}

/**
 * Detect circular dependencies in the workflow graph
 * @param {Array} nodes - All nodes
 * @param {Array} edges - All edges
 * @returns {Object} Result with hasCircular and cycles
 */
function detectCircularDependencies(nodes, edges) {
  const graph = new Map();
  
  // Build adjacency list
  nodes.forEach(node => {
    graph.set(node.id, []);
  });
  
  edges.forEach(edge => {
    const neighbors = graph.get(edge.source);
    if (neighbors) {
      neighbors.push(edge.target);
    }
  });

  const visited = new Set();
  const recursionStack = new Set();
  const cycles = [];

  function dfs(nodeId, path) {
    visited.add(nodeId);
    recursionStack.add(nodeId);
    path.push(nodeId);

    const neighbors = graph.get(nodeId) || [];
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        const result = dfs(neighbor, [...path]);
        if (result) return result;
      } else if (recursionStack.has(neighbor)) {
        // Found a cycle
        const cycleStart = path.indexOf(neighbor);
        cycles.push(path.slice(cycleStart));
        return true;
      }
    }

    recursionStack.delete(nodeId);
    return false;
  }

  for (const node of nodes) {
    if (!visited.has(node.id)) {
      dfs(node.id, []);
    }
  }

  return {
    hasCircular: cycles.length > 0,
    cycles,
  };
}

/**
 * Get validation summary for display
 * @param {Object} validationResult - Result from validateWorkflow
 * @returns {Object} Summary with counts and messages
 */
export function getValidationSummary(validationResult) {
  const { isValid, errors, warnings } = validationResult;

  return {
    isValid,
    errorCount: errors.length,
    warningCount: warnings.length,
    summary: isValid
      ? warnings.length > 0
        ? `Valid with ${warnings.length} warning(s)`
        : 'Valid'
      : `${errors.length} error(s) found`,
    errors: errors.map(e => ({
      message: e.message,
      location: e.nodeName || e.nodeId || e.edgeId || 'Workflow',
    })),
    warnings: warnings.map(w => ({
      message: w.message,
      location: w.nodeIds?.join(', ') || 'Workflow',
    })),
  };
}

export default {
  validateWorkflow,
  validateNode,
  validateEdge,
  getValidationSummary,
};
