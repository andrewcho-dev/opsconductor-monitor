/**
 * useWorkflow Hook
 * 
 * Manages workflow state including nodes, edges, and undo/redo history.
 * Follows the same pattern as other hooks in the system.
 */

import { useState, useCallback, useRef } from 'react';
import { applyNodeChanges, applyEdgeChanges, addEdge } from 'reactflow';

const MAX_HISTORY = 50;

const DEFAULT_WORKFLOW = {
  id: null,
  name: 'Untitled Workflow',
  description: '',
  folder_id: null,
  tags: [],
  nodes: [],
  edges: [],
  viewport: { x: 0, y: 0, zoom: 1 },
  schedule: null,
  settings: {
    error_handling: 'continue',
    timeout: 300,
    notifications: {
      on_success: false,
      on_failure: true,
    },
  },
};

/**
 * Hook for managing workflow state
 * @param {Object} initialWorkflow - Initial workflow data
 * @returns {Object} Workflow state and actions
 */
export function useWorkflow(initialWorkflow = null) {
  // Core state
  const [workflow, setWorkflow] = useState(() => ({
    ...DEFAULT_WORKFLOW,
    ...initialWorkflow,
  }));
  
  const [isDirty, setIsDirty] = useState(false);
  const [selectedNodes, setSelectedNodes] = useState([]);
  const [selectedEdges, setSelectedEdges] = useState([]);
  
  // Undo/redo history
  const historyRef = useRef({
    past: [],
    future: [],
  });

  // Save current state to history before making changes
  const saveToHistory = useCallback(() => {
    const { past } = historyRef.current;
    const currentState = {
      nodes: workflow.nodes,
      edges: workflow.edges,
    };
    
    historyRef.current = {
      past: [...past.slice(-MAX_HISTORY + 1), currentState],
      future: [],
    };
  }, [workflow.nodes, workflow.edges]);

  // Undo last change
  const undo = useCallback(() => {
    const { past, future } = historyRef.current;
    if (past.length === 0) return;
    
    const previous = past[past.length - 1];
    const currentState = {
      nodes: workflow.nodes,
      edges: workflow.edges,
    };
    
    historyRef.current = {
      past: past.slice(0, -1),
      future: [currentState, ...future],
    };
    
    setWorkflow(prev => ({
      ...prev,
      nodes: previous.nodes,
      edges: previous.edges,
    }));
    setIsDirty(true);
  }, [workflow.nodes, workflow.edges]);

  // Redo last undone change
  const redo = useCallback(() => {
    const { past, future } = historyRef.current;
    if (future.length === 0) return;
    
    const next = future[0];
    const currentState = {
      nodes: workflow.nodes,
      edges: workflow.edges,
    };
    
    historyRef.current = {
      past: [...past, currentState],
      future: future.slice(1),
    };
    
    setWorkflow(prev => ({
      ...prev,
      nodes: next.nodes,
      edges: next.edges,
    }));
    setIsDirty(true);
  }, [workflow.nodes, workflow.edges]);

  // Check if undo/redo is available
  const canUndo = historyRef.current.past.length > 0;
  const canRedo = historyRef.current.future.length > 0;

  // Node changes (move, select, etc.)
  const onNodesChange = useCallback((changes) => {
    // Check if this is a position change (drag completed)
    const hasPositionChange = changes.some(
      change => change.type === 'position' && change.dragging === false
    );
    
    if (hasPositionChange) {
      saveToHistory();
    }
    
    setWorkflow(prev => ({
      ...prev,
      nodes: applyNodeChanges(changes, prev.nodes),
    }));
    
    // Update selection
    const selectionChanges = changes.filter(c => c.type === 'select');
    if (selectionChanges.length > 0) {
      setSelectedNodes(prev => {
        const newSelection = [...prev];
        selectionChanges.forEach(change => {
          if (change.selected) {
            if (!newSelection.includes(change.id)) {
              newSelection.push(change.id);
            }
          } else {
            const idx = newSelection.indexOf(change.id);
            if (idx > -1) newSelection.splice(idx, 1);
          }
        });
        return newSelection;
      });
    }
    
    // Only mark dirty for actual content changes (position, remove, add)
    // Not for selection or dimension changes from React Flow initialization
    const hasContentChange = changes.some(
      change => change.type === 'position' || change.type === 'remove' || change.type === 'add'
    );
    if (hasContentChange) {
      setIsDirty(true);
    }
  }, [saveToHistory]);

  // Edge changes
  const onEdgesChange = useCallback((changes) => {
    const hasRemoval = changes.some(c => c.type === 'remove');
    if (hasRemoval) {
      saveToHistory();
    }
    
    setWorkflow(prev => ({
      ...prev,
      edges: applyEdgeChanges(changes, prev.edges),
    }));
    
    // Update selection
    const selectionChanges = changes.filter(c => c.type === 'select');
    if (selectionChanges.length > 0) {
      setSelectedEdges(prev => {
        const newSelection = [...prev];
        selectionChanges.forEach(change => {
          if (change.selected) {
            if (!newSelection.includes(change.id)) {
              newSelection.push(change.id);
            }
          } else {
            const idx = newSelection.indexOf(change.id);
            if (idx > -1) newSelection.splice(idx, 1);
          }
        });
        return newSelection;
      });
    }
    
    // Only mark dirty for actual content changes (remove, add)
    // Not for selection changes
    const hasContentChange = changes.some(
      change => change.type === 'remove' || change.type === 'add'
    );
    if (hasContentChange) {
      setIsDirty(true);
    }
  }, [saveToHistory]);

  // Connect nodes
  const onConnect = useCallback((connection) => {
    saveToHistory();
    
    const newEdge = {
      ...connection,
      id: `edge-${connection.source}-${connection.sourceHandle}-${connection.target}-${connection.targetHandle}`,
      type: 'smoothstep',
      animated: false,
    };
    
    setWorkflow(prev => ({
      ...prev,
      edges: addEdge(newEdge, prev.edges),
    }));
    setIsDirty(true);
  }, [saveToHistory]);

  // Add a new node
  const addNode = useCallback((nodeDefinition, position) => {
    saveToHistory();
    
    const newNode = {
      id: `node-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type: nodeDefinition.type || 'default',
      position,
      data: {
        nodeType: nodeDefinition.id,
        label: nodeDefinition.name,
        description: '',
        parameters: {},
        // Initialize default parameter values
        ...Object.fromEntries(
          (nodeDefinition.parameters || []).map(p => [p.id, p.default])
        ),
      },
    };
    
    setWorkflow(prev => ({
      ...prev,
      nodes: [...prev.nodes, newNode],
    }));
    setIsDirty(true);
    
    return newNode.id;
  }, [saveToHistory]);

  // Update a node's data
  const updateNode = useCallback((nodeId, updates) => {
    saveToHistory();
    
    setWorkflow(prev => ({
      ...prev,
      nodes: prev.nodes.map(node =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...updates } }
          : node
      ),
    }));
    setIsDirty(true);
  }, [saveToHistory]);

  // Delete selected nodes and edges
  const deleteSelected = useCallback(() => {
    if (selectedNodes.length === 0 && selectedEdges.length === 0) return;
    
    saveToHistory();
    
    setWorkflow(prev => ({
      ...prev,
      nodes: prev.nodes.filter(node => !selectedNodes.includes(node.id)),
      edges: prev.edges.filter(edge => 
        !selectedEdges.includes(edge.id) &&
        !selectedNodes.includes(edge.source) &&
        !selectedNodes.includes(edge.target)
      ),
    }));
    
    setSelectedNodes([]);
    setSelectedEdges([]);
    setIsDirty(true);
  }, [selectedNodes, selectedEdges, saveToHistory]);

  // Duplicate selected nodes
  const duplicateSelected = useCallback(() => {
    if (selectedNodes.length === 0) return;
    
    saveToHistory();
    
    const nodesToDuplicate = workflow.nodes.filter(n => selectedNodes.includes(n.id));
    const idMap = {};
    
    const newNodes = nodesToDuplicate.map(node => {
      const newId = `node-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      idMap[node.id] = newId;
      
      return {
        ...node,
        id: newId,
        position: {
          x: node.position.x + 50,
          y: node.position.y + 50,
        },
        selected: true,
      };
    });
    
    // Duplicate edges between selected nodes
    const newEdges = workflow.edges
      .filter(edge => 
        selectedNodes.includes(edge.source) && 
        selectedNodes.includes(edge.target)
      )
      .map(edge => ({
        ...edge,
        id: `edge-${idMap[edge.source]}-${edge.sourceHandle}-${idMap[edge.target]}-${edge.targetHandle}`,
        source: idMap[edge.source],
        target: idMap[edge.target],
      }));
    
    setWorkflow(prev => ({
      ...prev,
      nodes: [
        ...prev.nodes.map(n => ({ ...n, selected: false })),
        ...newNodes,
      ],
      edges: [...prev.edges, ...newEdges],
    }));
    
    setSelectedNodes(newNodes.map(n => n.id));
    setIsDirty(true);
  }, [selectedNodes, workflow.nodes, workflow.edges, saveToHistory]);

  // Update workflow metadata
  const updateWorkflowMeta = useCallback((updates) => {
    setWorkflow(prev => ({
      ...prev,
      ...updates,
    }));
    setIsDirty(true);
  }, []);

  // Update viewport
  const updateViewport = useCallback((viewport) => {
    setWorkflow(prev => ({
      ...prev,
      viewport,
    }));
  }, []);

  // Reset dirty flag (after save)
  const markClean = useCallback(() => {
    setIsDirty(false);
  }, []);

  // Load a workflow
  const loadWorkflow = useCallback((workflowData) => {
    setWorkflow({
      ...DEFAULT_WORKFLOW,
      ...workflowData,
    });
    setIsDirty(false);
    setSelectedNodes([]);
    setSelectedEdges([]);
    historyRef.current = { past: [], future: [] };
  }, []);

  // Reset to empty workflow
  const resetWorkflow = useCallback(() => {
    setWorkflow(DEFAULT_WORKFLOW);
    setIsDirty(false);
    setSelectedNodes([]);
    setSelectedEdges([]);
    historyRef.current = { past: [], future: [] };
  }, []);

  return {
    // State
    workflow,
    nodes: workflow.nodes,
    edges: workflow.edges,
    viewport: workflow.viewport,
    isDirty,
    selectedNodes,
    selectedEdges,
    
    // History
    canUndo,
    canRedo,
    undo,
    redo,
    
    // Node/Edge actions
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    updateNode,
    deleteSelected,
    duplicateSelected,
    
    // Workflow actions
    updateWorkflowMeta,
    updateViewport,
    markClean,
    loadWorkflow,
    resetWorkflow,
  };
}

export default useWorkflow;
