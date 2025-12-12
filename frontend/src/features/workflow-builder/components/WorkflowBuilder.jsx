/**
 * WorkflowBuilder Component
 * 
 * Main component that combines all workflow builder elements:
 * - Toolbar (save, run, undo/redo)
 * - Node Palette (sidebar)
 * - Canvas (React Flow)
 * - Node Editor (modal)
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useWorkflow } from '../hooks/useWorkflow';
import { useNodeEditor } from '../hooks/useNodeEditor';
import WorkflowToolbar from './WorkflowToolbar';
import WorkflowCanvas from './WorkflowCanvas';
import NodePalette from './NodePalette';
import NodeEditor from './NodeEditor';
import ExecutionDebugView from './ExecutionDebugView';
import { getNodeDefinition } from '../packages';
import { autoLayout } from '../utils/layout';

const DEFAULT_ENABLED_PACKAGES = [
  'core',
  'network-discovery',
  'snmp',
  'ssh',
  'database',
  'notifications',
  'ciena-saos',
];

const WorkflowBuilder = ({
  initialWorkflow,
  onSave,
  onRun,
  onTest,
  onBack,
  enabledPackages = DEFAULT_ENABLED_PACKAGES,
}) => {
  // Workflow state management
  const {
    workflow,
    nodes,
    edges,
    viewport,
    isDirty,
    selectedNodes,
    selectedEdges,
    canUndo,
    canRedo,
    undo,
    redo,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    updateNode,
    deleteSelected,
    duplicateSelected,
    updateWorkflowMeta,
    updateViewport,
    markClean,
    loadWorkflow,
  } = useWorkflow(initialWorkflow);

  // Node editor state
  const {
    isOpen: isEditorOpen,
    editingNode,
    nodeDefinition,
    formData,
    errors,
    openEditor,
    closeEditor,
    updateField,
    validate,
    getSaveData,
    shouldShowParameter,
  } = useNodeEditor();

  // Execution debug view state
  const [debugViewOpen, setDebugViewOpen] = useState(false);
  const [executionResult, setExecutionResult] = useState(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [isTestMode, setIsTestMode] = useState(false);

  // Load initial workflow
  useEffect(() => {
    if (initialWorkflow) {
      loadWorkflow(initialWorkflow);
    }
  }, [initialWorkflow, loadWorkflow]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Ignore if typing in an input
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return;
      }

      // Ctrl/Cmd + Z = Undo
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        undo();
      }
      // Ctrl/Cmd + Y or Ctrl/Cmd + Shift + Z = Redo
      if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault();
        redo();
      }
      // Ctrl/Cmd + S = Save
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        handleSave();
      }
      // Ctrl/Cmd + D = Duplicate
      if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
        e.preventDefault();
        duplicateSelected();
      }
      // Delete/Backspace = Delete selected
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedNodes.length > 0 || selectedEdges.length > 0) {
          e.preventDefault();
          deleteSelected();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [undo, redo, duplicateSelected, deleteSelected, selectedNodes, selectedEdges]);

  // Handle save
  const handleSave = useCallback(async () => {
    if (onSave) {
      try {
        await onSave(workflow);
        markClean();
      } catch (error) {
        console.error('Failed to save workflow:', error);
      }
    }
  }, [workflow, onSave, markClean]);

  // Handle run
  const handleRun = useCallback(async () => {
    if (onRun) {
      setIsTestMode(false);
      setExecutionResult(null);
      setIsExecuting(true);
      setDebugViewOpen(true);
      
      try {
        const result = await onRun(workflow);
        setExecutionResult(result);
      } catch (error) {
        console.error('Execution failed:', error);
        setExecutionResult({
          status: 'failure',
          error_message: error.message,
          node_results: {},
          variables: {},
        });
      } finally {
        setIsExecuting(false);
      }
    }
  }, [workflow, onRun]);

  // Handle test
  const handleTest = useCallback(async () => {
    if (onTest) {
      setIsTestMode(true);
      setExecutionResult(null);
      setIsExecuting(true);
      setDebugViewOpen(true);
      
      try {
        const result = await onTest(workflow);
        setExecutionResult(result);
      } catch (error) {
        console.error('Test run failed:', error);
        setExecutionResult({
          status: 'failure',
          error_message: error.message,
          node_results: {},
          variables: {},
        });
      } finally {
        setIsExecuting(false);
      }
    }
  }, [workflow, onTest]);

  // Handle node drop from palette
  const handleNodeDrop = useCallback((nodeDefinition, position) => {
    addNode(nodeDefinition, position);
  }, [addNode]);

  // Handle node double-click (open editor)
  const handleNodeDoubleClick = useCallback((node) => {
    openEditor(node);
  }, [openEditor]);

  // Handle node editor save
  const handleEditorSave = useCallback(() => {
    if (!validate()) return;

    const saveData = getSaveData();
    updateNode(editingNode.id, {
      label: saveData.label,
      description: saveData.description,
      parameters: saveData.parameters,
    });
    closeEditor();
  }, [validate, getSaveData, updateNode, editingNode, closeEditor]);

  // Handle node delete from editor
  const handleEditorDelete = useCallback(() => {
    if (editingNode) {
      // Select the node and delete it
      onNodesChange([{ type: 'select', id: editingNode.id, selected: true }]);
      setTimeout(() => {
        deleteSelected();
        closeEditor();
      }, 0);
    }
  }, [editingNode, onNodesChange, deleteSelected, closeEditor]);

  // Handle auto layout
  const handleAutoLayout = useCallback(() => {
    if (nodes.length === 0) return;
    
    const layoutedNodes = autoLayout(nodes, edges, {
      nodeWidth: 220,
      nodeHeight: 100,
      horizontalSpacing: 120,
      verticalSpacing: 80,
      startX: 100,
      startY: 100,
    });
    
    // Apply the new positions
    const changes = layoutedNodes.map(node => ({
      type: 'position',
      id: node.id,
      position: node.position,
    }));
    
    onNodesChange(changes);
  }, [nodes, edges, onNodesChange]);

  // Handle settings (placeholder)
  const handleOpenSettings = useCallback(() => {
    // TODO: Open settings modal
    console.log('Settings not yet implemented');
  }, []);

  // Handle schedule (placeholder)
  const handleOpenSchedule = useCallback(() => {
    // TODO: Open schedule modal
    console.log('Schedule not yet implemented');
  }, []);

  return (
    <div className="h-full w-full flex flex-col bg-gray-100">
      {/* Toolbar */}
      <WorkflowToolbar
        workflowName={workflow.name}
        isDirty={isDirty}
        canUndo={canUndo}
        canRedo={canRedo}
        hasSelection={selectedNodes.length > 0 || selectedEdges.length > 0}
        onBack={onBack}
        onSave={handleSave}
        onRun={handleRun}
        onTest={handleTest}
        onUndo={undo}
        onRedo={redo}
        onDelete={deleteSelected}
        onDuplicate={duplicateSelected}
        onAutoLayout={handleAutoLayout}
        onOpenSettings={handleOpenSettings}
        onOpenSchedule={handleOpenSchedule}
      />

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Node Palette */}
        <NodePalette
          enabledPackages={enabledPackages}
        />

        {/* Canvas */}
        <WorkflowCanvas
          nodes={nodes}
          edges={edges}
          viewport={viewport}
          selectedNodes={selectedNodes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeDoubleClick={handleNodeDoubleClick}
          onDrop={handleNodeDrop}
          onViewportChange={updateViewport}
        />
      </div>

      {/* Node Editor Modal */}
      <NodeEditor
        isOpen={isEditorOpen}
        node={editingNode}
        nodeDefinition={nodeDefinition}
        formData={formData}
        errors={errors}
        onClose={closeEditor}
        onSave={handleEditorSave}
        onDelete={handleEditorDelete}
        updateField={updateField}
        shouldShowParameter={shouldShowParameter}
      />

      {/* Execution Debug View */}
      <ExecutionDebugView
        isOpen={debugViewOpen}
        onClose={() => setDebugViewOpen(false)}
        executionId={executionResult?.execution_id}
        workflowName={workflow.name}
        isTestMode={isTestMode}
        executionResult={executionResult}
        isRunning={isExecuting}
      />
    </div>
  );
};

export default WorkflowBuilder;
