/**
 * Workflow Builder Module
 * 
 * Visual workflow editor for creating and managing automation jobs.
 * Uses React Flow for the canvas-based node editor.
 * 
 * This module follows the same modular architecture as the rest of the system:
 * - components/ - React UI components
 * - nodes/ - Custom node type components
 * - packages/ - Node package definitions (commands, actions)
 * - hooks/ - React hooks for state management
 * - utils/ - Utility functions
 */

export { default as WorkflowBuilder } from './components/WorkflowBuilder';
export { default as WorkflowCanvas } from './components/WorkflowCanvas';
export { default as NodePalette } from './components/NodePalette';
export { default as NodeEditor } from './components/NodeEditor';

// Hooks
export { useWorkflow } from './hooks/useWorkflow';
export { useNodeEditor } from './hooks/useNodeEditor';

// Utils
export { serializeWorkflow, deserializeWorkflow } from './utils/serialization';
export { validateWorkflow } from './utils/validation';

// Package registry
export { getEnabledPackages, getNodeDefinition } from './packages';
