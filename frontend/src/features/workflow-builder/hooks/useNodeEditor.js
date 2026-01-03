/**
 * useNodeEditor Hook
 * 
 * Manages the node editor modal state and node parameter editing.
 */

import { useState, useCallback } from 'react';
import { getNodeDefinition } from '../packages';

/**
 * Hook for managing node editor state
 * @returns {Object} Node editor state and actions
 */
export function useNodeEditor() {
  const [isOpen, setIsOpen] = useState(false);
  const [editingNode, setEditingNode] = useState(null);
  const [nodeDefinition, setNodeDefinition] = useState(null);
  const [formData, setFormData] = useState({});
  const [errors, setErrors] = useState({});

  // Open editor for a node
  const openEditor = useCallback((node) => {
    const definition = getNodeDefinition(node.data.nodeType);
    
    // Build initial form data with defaults from definition
    const defaultValues = {};
    if (definition) {
      // Get defaults from parameters
      (definition.parameters || []).forEach(param => {
        if (param.default !== undefined) {
          defaultValues[param.id] = param.default;
        }
      });
      // Get defaults from advanced parameters
      (definition.advanced || []).forEach(param => {
        if (param.default !== undefined) {
          defaultValues[param.id] = param.default;
        }
      });
    }
    
    setEditingNode(node);
    setNodeDefinition(definition);
    setFormData({
      label: node.data.label || definition?.name || '',
      description: node.data.description || '',
      ...defaultValues,  // Apply defaults first
      ...node.data.parameters,  // Then override with saved values
    });
    setErrors({});
    setIsOpen(true);
  }, []);

  // Close editor
  const closeEditor = useCallback(() => {
    setIsOpen(false);
    setEditingNode(null);
    setNodeDefinition(null);
    setFormData({});
    setErrors({});
  }, []);

  // Update a form field
  const updateField = useCallback((fieldId, value) => {
    setFormData(prev => ({
      ...prev,
      [fieldId]: value,
    }));
    
    // Clear error for this field
    setErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[fieldId];
      return newErrors;
    });
  }, []);

  // Validate form data
  const validate = useCallback(() => {
    if (!nodeDefinition) return true;
    
    const newErrors = {};
    
    // Check required parameters
    const allParams = [
      ...(nodeDefinition.parameters || []),
      ...(nodeDefinition.advanced || []),
    ];
    
    for (const param of allParams) {
      if (param.required && !formData[param.id]) {
        newErrors[param.id] = `${param.label} is required`;
      }
      
      // Type-specific validation
      if (formData[param.id] !== undefined && formData[param.id] !== '') {
        if (param.type === 'number') {
          const num = Number(formData[param.id]);
          if (isNaN(num)) {
            newErrors[param.id] = `${param.label} must be a number`;
          } else if (param.min !== undefined && num < param.min) {
            newErrors[param.id] = `${param.label} must be at least ${param.min}`;
          } else if (param.max !== undefined && num > param.max) {
            newErrors[param.id] = `${param.label} must be at most ${param.max}`;
          }
        }
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [nodeDefinition, formData]);

  // Get the data to save
  const getSaveData = useCallback(() => {
    const { label, description, ...parameters } = formData;
    
    return {
      label,
      description,
      parameters,
    };
  }, [formData]);

  // Check if a parameter should be shown based on showIf conditions
  const shouldShowParameter = useCallback((param) => {
    if (!param.showIf) return true;
    
    const { field, value, values } = param.showIf;
    const currentValue = formData[field];
    
    if (values) {
      return values.includes(currentValue);
    }
    
    return currentValue === value;
  }, [formData]);

  return {
    // State
    isOpen,
    editingNode,
    nodeDefinition,
    formData,
    errors,
    
    // Actions
    openEditor,
    closeEditor,
    updateField,
    validate,
    getSaveData,
    shouldShowParameter,
  };
}

export default useNodeEditor;
