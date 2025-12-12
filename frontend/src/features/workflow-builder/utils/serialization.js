/**
 * Workflow Serialization Utilities
 * 
 * Functions for converting workflows to/from JSON format for API storage.
 */

/**
 * Serialize a workflow for saving to the backend
 * @param {Object} workflow - The workflow state
 * @returns {Object} Serialized workflow ready for API
 */
export function serializeWorkflow(workflow) {
  return {
    id: workflow.id,
    name: workflow.name,
    description: workflow.description,
    folder_id: workflow.folder_id,
    tags: workflow.tags || [],
    definition: {
      nodes: workflow.nodes.map(node => ({
        id: node.id,
        type: node.type,
        position: node.position,
        data: {
          nodeType: node.data.nodeType,
          label: node.data.label,
          description: node.data.description,
          parameters: node.data.parameters || {},
        },
      })),
      edges: workflow.edges.map(edge => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        sourceHandle: edge.sourceHandle,
        targetHandle: edge.targetHandle,
        type: edge.type,
      })),
      viewport: workflow.viewport,
    },
    schedule: workflow.schedule,
    settings: workflow.settings,
  };
}

/**
 * Deserialize a workflow from backend format to state format
 * @param {Object} data - The workflow data from API
 * @returns {Object} Workflow state
 */
export function deserializeWorkflow(data) {
  const definition = data.definition || {};
  
  return {
    id: data.id,
    name: data.name || 'Untitled Workflow',
    description: data.description || '',
    folder_id: data.folder_id,
    tags: data.tags || [],
    nodes: (definition.nodes || []).map(node => ({
      id: node.id,
      type: node.type || 'workflow',
      position: node.position || { x: 0, y: 0 },
      data: {
        nodeType: node.data?.nodeType || node.nodeType,
        label: node.data?.label || node.label,
        description: node.data?.description || '',
        parameters: node.data?.parameters || node.parameters || {},
      },
    })),
    edges: (definition.edges || []).map(edge => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      sourceHandle: edge.sourceHandle,
      targetHandle: edge.targetHandle,
      type: edge.type || 'smoothstep',
    })),
    viewport: definition.viewport || { x: 0, y: 0, zoom: 1 },
    schedule: data.schedule,
    settings: data.settings || {
      error_handling: 'continue',
      timeout: 300,
      notifications: {
        on_success: false,
        on_failure: true,
      },
    },
  };
}

/**
 * Convert old job format to new workflow format
 * Used for migrating existing jobs
 * @param {Object} oldJob - Job in old CompleteJobBuilder format
 * @returns {Object} Workflow in new format
 */
export function migrateOldJobToWorkflow(oldJob) {
  const nodes = [];
  const edges = [];
  let yPosition = 0;
  const xSpacing = 300;
  const ySpacing = 150;

  // Add start trigger node
  const startNode = {
    id: 'start',
    type: 'workflow',
    position: { x: 0, y: yPosition },
    data: {
      nodeType: 'trigger:manual',
      label: 'Start',
      description: '',
      parameters: {},
    },
  };
  nodes.push(startNode);

  let previousNodeId = 'start';

  // Convert each action to a node
  (oldJob.actions || []).forEach((action, index) => {
    const nodeId = `action-${index}`;
    
    // Map old action type to new node type
    let nodeType = 'ssh:command';
    if (action.type === 'ping' || action.type === 'ping_scan') {
      nodeType = 'network:ping';
    } else if (action.type === 'snmp_scan' || action.type === 'snmp') {
      nodeType = 'snmp:get';
    } else if (action.type === 'ssh_scan' || action.type === 'ssh_command') {
      nodeType = 'ssh:command';
    }

    const node = {
      id: nodeId,
      type: 'workflow',
      position: { x: xSpacing * (index + 1), y: yPosition },
      data: {
        nodeType,
        label: action.name || `Action ${index + 1}`,
        description: '',
        parameters: {
          target_type: action.targeting?.source || 'network_range',
          network_range: action.targeting?.network_range || '',
          ...action.execution,
        },
      },
    };
    nodes.push(node);

    // Add edge from previous node
    edges.push({
      id: `edge-${previousNodeId}-${nodeId}`,
      source: previousNodeId,
      target: nodeId,
      sourceHandle: previousNodeId === 'start' ? 'trigger' : 'success',
      targetHandle: 'trigger',
      type: 'smoothstep',
    });

    previousNodeId = nodeId;
  });

  // Add database save node if actions had database config
  const hasDbConfig = oldJob.actions?.some(a => a.database?.table);
  if (hasDbConfig) {
    const dbNodeId = 'db-save';
    nodes.push({
      id: dbNodeId,
      type: 'workflow',
      position: { x: xSpacing * (oldJob.actions.length + 1), y: yPosition },
      data: {
        nodeType: 'db:upsert',
        label: 'Save to Database',
        description: '',
        parameters: {
          table: oldJob.actions[0]?.database?.table || 'devices',
          key_columns: (oldJob.actions[0]?.database?.key_fields || ['ip_address']).join(','),
        },
      },
    });

    edges.push({
      id: `edge-${previousNodeId}-${dbNodeId}`,
      source: previousNodeId,
      target: dbNodeId,
      sourceHandle: 'success',
      targetHandle: 'trigger',
      type: 'smoothstep',
    });
  }

  return {
    id: oldJob.id || oldJob.job_id,
    name: oldJob.name || 'Migrated Job',
    description: oldJob.description || '',
    folder_id: null,
    tags: [],
    nodes,
    edges,
    viewport: { x: 0, y: 0, zoom: 1 },
    schedule: null,
    settings: {
      error_handling: oldJob.config?.error_handling || 'continue',
      timeout: oldJob.config?.global_timeout || 300,
      notifications: {
        on_success: false,
        on_failure: true,
      },
    },
  };
}

export default {
  serializeWorkflow,
  deserializeWorkflow,
  migrateOldJobToWorkflow,
};
