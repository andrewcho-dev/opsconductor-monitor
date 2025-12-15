/**
 * WorkflowCanvas Component
 * 
 * Main React Flow canvas for the workflow builder.
 * Handles node rendering, connections, and canvas interactions.
 */

import React, { useCallback, useRef, useMemo, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useReactFlow,
  ReactFlowProvider,
  ConnectionLineType,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';

import WorkflowNode from '../nodes/WorkflowNode';
import { getNodeDefinition } from '../packages';
import { cn } from '../../../lib/utils';

// Custom node types
const nodeTypes = {
  workflow: WorkflowNode,
};

// Custom edge options - Node-RED style bezier curves
const defaultEdgeOptions = {
  type: 'default', // bezier curve like Node-RED
  animated: false,
  style: { 
    strokeWidth: 2, 
    stroke: '#999',
  },
  focusable: true,
  interactionWidth: 20, // Wider click area
};

// Connection line style (while dragging)
const connectionLineStyle = {
  strokeWidth: 2,
  stroke: '#ff7f50',
};

// Get edge style based on source handle type
const getEdgeStyle = (sourceNode, sourceHandleId) => {
  if (!sourceNode) return { stroke: '#6B7280' };
  
  const nodeDef = getNodeDefinition(sourceNode.data?.nodeType);
  const output = nodeDef?.outputs?.find(o => o.id === sourceHandleId);
  
  if (!output) return { stroke: '#6B7280' };
  
  // Color based on output type
  if (output.type === 'trigger') {
    if (output.id === 'failure' || output.id === 'false') {
      return { stroke: '#EF4444', strokeWidth: 2 }; // Red for failure
    }
    return { stroke: '#22C55E', strokeWidth: 2 }; // Green for success
  }
  
  return { stroke: '#F97316', strokeWidth: 2 }; // Orange for data
};

const WorkflowCanvasInner = ({
  nodes,
  edges,
  viewport,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onNodeDoubleClick,
  onDrop,
  onDragOver,
  onViewportChange,
  selectedNodes,
  className,
}) => {
  const reactFlowWrapper = useRef(null);
  const { screenToFlowPosition, fitView } = useReactFlow();

  // Handle drop from palette
  const handleDrop = useCallback((event) => {
    event.preventDefault();

    const data = event.dataTransfer.getData('application/reactflow');
    if (!data) return;

    const { nodeType, name } = JSON.parse(data);
    const nodeDefinition = getNodeDefinition(nodeType);
    
    if (!nodeDefinition) {
      console.warn('Unknown node type:', nodeType);
      return;
    }

    // Get drop position in flow coordinates
    const position = screenToFlowPosition({
      x: event.clientX,
      y: event.clientY,
    });

    if (onDrop) {
      onDrop(nodeDefinition, position);
    }
  }, [screenToFlowPosition, onDrop]);

  const handleDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    if (onDragOver) {
      onDragOver(event);
    }
  }, [onDragOver]);

  // Validate connections
  const isValidConnection = useCallback((connection) => {
    // Prevent self-connections
    if (connection.source === connection.target) return false;

    // Get source and target node definitions
    const sourceNode = nodes.find(n => n.id === connection.source);
    const targetNode = nodes.find(n => n.id === connection.target);
    
    if (!sourceNode || !targetNode) return false;

    const sourceDef = getNodeDefinition(sourceNode.data.nodeType);
    const targetDef = getNodeDefinition(targetNode.data.nodeType);

    if (!sourceDef || !targetDef) return false;

    // Get handle types
    const sourceOutput = sourceDef.outputs?.find(o => o.id === connection.sourceHandle);
    const targetInput = targetDef.inputs?.find(i => i.id === connection.targetHandle);

    if (!sourceOutput || !targetInput) return false;

    // Type compatibility check
    // Trigger can connect to trigger
    // Data can connect to data or any
    // Any can connect to anything
    if (sourceOutput.type === 'trigger' && targetInput.type !== 'trigger') return false;
    if (targetInput.type === 'trigger' && sourceOutput.type !== 'trigger') return false;

    return true;
  }, [nodes]);

  // Handle node double-click for editing
  const handleNodeDoubleClick = useCallback((event, node) => {
    if (onNodeDoubleClick) {
      onNodeDoubleClick(node);
    }
  }, [onNodeDoubleClick]);

  // Handle viewport changes
  const handleMoveEnd = useCallback((event, viewport) => {
    if (onViewportChange) {
      onViewportChange(viewport);
    }
  }, [onViewportChange]);

  // Handle edge click - select the edge
  const handleEdgeClick = useCallback((event, edge) => {
    event.stopPropagation();
    // Edge selection is handled by React Flow's onEdgesChange
  }, []);

  // Convert nodes to React Flow format
  const flowNodes = useMemo(() => 
    nodes.map(node => ({
      ...node,
      type: 'workflow',
      selected: selectedNodes?.includes(node.id),
    })),
    [nodes, selectedNodes]
  );

  // Style edges - Node-RED style (simple gray lines, selectable)
  const styledEdges = useMemo(() => 
    edges.map(edge => {
      const isFailurePath = edge.sourceHandle === 'failure' || edge.sourceHandle === 'false';
      const isSelected = edge.selected;
      return {
        ...edge,
        type: 'default', // bezier curve
        style: { 
          strokeWidth: isSelected ? 3 : 2, 
          stroke: isSelected ? '#3B82F6' : (isFailurePath ? '#EF4444' : '#999'),
          cursor: 'pointer',
        },
        // Wider click area for easier selection
        interactionWidth: 20,
        className: isSelected ? 'selected-edge' : '',
      };
    }),
    [edges]
  );

  // MiniMap node color
  const nodeColor = useCallback((node) => {
    const def = getNodeDefinition(node.data?.nodeType);
    return def?.color || '#6B7280';
  }, []);

  return (
    <div 
      ref={reactFlowWrapper} 
      className={cn('flex-1 h-full w-full', className)}
      style={{ minHeight: '400px' }}
    >
      <ReactFlow
        nodes={flowNodes}
        edges={styledEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeDoubleClick={handleNodeDoubleClick}
        onEdgeClick={handleEdgeClick}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onMoveEnd={handleMoveEnd}
        isValidConnection={isValidConnection}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        connectionLineStyle={connectionLineStyle}
        defaultViewport={viewport}
        fitView={nodes.length === 0}
        snapToGrid
        snapGrid={[15, 15]}
        deleteKeyCode={['Backspace', 'Delete']}
        multiSelectionKeyCode="Shift"
        selectionOnDrag
        panOnDrag={[1, 2]} // Middle and right mouse button
        selectNodesOnDrag={false}
        edgesUpdatable={true}
        edgesFocusable={true}
        elementsSelectable={true}
        minZoom={0.1}
        maxZoom={4}
        attributionPosition="bottom-left"
      >
        <Background 
          variant="dots" 
          gap={20} 
          size={1} 
          color="#E5E7EB"
        />
        
        <Controls 
          position="bottom-right"
          showZoom
          showFitView
          showInteractive={false}
        />
        
        <MiniMap
          position="bottom-left"
          nodeColor={nodeColor}
          nodeStrokeWidth={3}
          zoomable
          pannable
          maskColor="rgba(59, 130, 246, 0.15)"
          style={{
            backgroundColor: '#F9FAFB',
            border: '1px solid #E5E7EB',
            borderRadius: '8px',
          }}
        />
      </ReactFlow>
    </div>
  );
};

// Wrap with ReactFlowProvider
const WorkflowCanvas = (props) => (
  <ReactFlowProvider>
    <WorkflowCanvasInner {...props} />
  </ReactFlowProvider>
);

export default WorkflowCanvas;
