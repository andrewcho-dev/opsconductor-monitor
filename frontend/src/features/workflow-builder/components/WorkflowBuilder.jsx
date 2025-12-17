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
import { useWorkflowValidation } from '../hooks/useWorkflowValidation';
import WorkflowToolbar from './WorkflowToolbar';
import WorkflowCanvas from './WorkflowCanvas';
import NodePalette from './NodePalette';
import NodeEditor from './NodeEditor';
import ExecutionDebugView from './ExecutionDebugView';
import ValidationPanel from './ValidationPanel';
import SaveValidationDialog from './SaveValidationDialog';
import { getNodeDefinition, DEFAULT_ENABLED_PACKAGES } from '../packages';
import { autoLayout } from '../utils/layout';

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

  // Validation state
  const validationResult = useWorkflowValidation(nodes, edges);
  const [validationPanelExpanded, setValidationPanelExpanded] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);

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

  // Handle save with validation
  const handleSave = useCallback(async () => {
    // Check for validation issues
    if (!validationResult.isValid || validationResult.hasWarnings) {
      setShowSaveDialog(true);
      return;
    }
    
    // No issues, save directly
    await performSave();
  }, [validationResult]);

  // Perform the actual save
  const performSave = useCallback(async () => {
    if (onSave) {
      try {
        await onSave(workflow);
        markClean();
        setShowSaveDialog(false);
      } catch (error) {
        console.error('Failed to save workflow:', error);
      }
    }
  }, [workflow, onSave, markClean]);

  // Handle run - just submit and show confirmation
  const handleRun = useCallback(async () => {
    if (onRun) {
      setIsTestMode(false);
      setExecutionResult(null);
      setIsExecuting(true);
      
      try {
        const result = await onRun(workflow);
        if (result) {
          setExecutionResult(result);
          setDebugViewOpen(true);
        }
      } catch (error) {
        console.error('Execution failed:', error);
        alert(`Failed to submit workflow: ${error.message}`);
      } finally {
        setIsExecuting(false);
      }
    }
  }, [workflow, onRun]);

  // Handle test - just submit and show confirmation
  const handleTest = useCallback(async () => {
    if (onTest) {
      setIsTestMode(true);
      setExecutionResult(null);
      setIsExecuting(true);
      
      try {
        const result = await onTest(workflow);
        // Handle case where workflow wasn't saved (returns null)
        if (result === null) {
          setIsExecuting(false);
          return;
        }
        setExecutionResult(result);
        setDebugViewOpen(true);
      } catch (error) {
        console.error('Test run failed:', error);
        alert(`Failed to submit test: ${error.message}`);
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
        onNameChange={(name) => updateWorkflowMeta({ name })}
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

        {/* Canvas with Validation Panel */}
        <div className="flex-1 flex flex-col min-w-0">
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
            validationResult={validationResult}
          />
          
          {/* Validation Panel */}
          {nodes.length > 0 && (
            <ValidationPanel
              validationResult={validationResult}
              isExpanded={validationPanelExpanded}
              onToggle={() => setValidationPanelExpanded(!validationPanelExpanded)}
              onNodeClick={(nodeId) => {
                // Focus on the node - could implement zoom to node
                console.log('Focus node:', nodeId);
              }}
            />
          )}
        </div>
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
        allNodes={nodes}
        edges={edges}
        onMapInput={(inputId, mapping) => {
          updateField('_inputMappings', {
            ...formData._inputMappings,
            [inputId]: mapping,
          });
        }}
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

      {/* Save Validation Dialog */}
      <SaveValidationDialog
        isOpen={showSaveDialog}
        onClose={() => setShowSaveDialog(false)}
        onSave={performSave}
        onCancel={() => setShowSaveDialog(false)}
        validationResult={validationResult}
        workflowName={workflow.name}
      />
    </div>
  );
};

export default WorkflowBuilder;
