/**
 * useWorkflowValidation Hook
 * 
 * Provides real-time validation of workflow configurations.
 * Tracks platform compatibility and other validation issues.
 */

import { useMemo, useCallback } from 'react';
import { 
  validateWorkflow, 
  getValidationSummary, 
  getEdgeCompatibilityWarning,
  ValidationSeverity 
} from '../services/workflowValidator';

/**
 * Hook for workflow validation
 */
export function useWorkflowValidation(nodes, edges) {
  // Validate the entire workflow
  const validationResult = useMemo(() => {
    if (!nodes || nodes.length === 0) {
      return {
        isValid: true,
        hasWarnings: false,
        errorCount: 0,
        warningCount: 0,
        infoCount: 0,
        errors: [],
        warnings: [],
        infos: [],
        all: [],
      };
    }
    
    const issues = validateWorkflow(nodes, edges || []);
    return getValidationSummary(issues);
  }, [nodes, edges]);
  
  // Get issues for a specific node
  const getNodeIssues = useCallback((nodeId) => {
    return validationResult.all.filter(
      issue => issue.nodeId === nodeId || 
               issue.sourceNodeId === nodeId || 
               issue.targetNodeId === nodeId
    );
  }, [validationResult]);
  
  // Get issues for a specific edge
  const getEdgeIssues = useCallback((sourceId, targetId) => {
    return validationResult.all.filter(
      issue => issue.sourceNodeId === sourceId && issue.targetNodeId === targetId
    );
  }, [validationResult]);
  
  // Check if a specific edge has compatibility warnings
  const hasEdgeWarning = useCallback((sourceId, targetId) => {
    const issues = getEdgeIssues(sourceId, targetId);
    return issues.some(i => i.type === 'platform_mismatch');
  }, [getEdgeIssues]);
  
  // Get edge style based on compatibility
  const getEdgeStyle = useCallback((sourceId, targetId) => {
    const issues = getEdgeIssues(sourceId, targetId);
    const hasPlatformMismatch = issues.some(i => i.type === 'platform_mismatch');
    
    if (hasPlatformMismatch) {
      return {
        stroke: '#F59E0B', // Amber for warning
        strokeWidth: 2,
        strokeDasharray: '5,5',
      };
    }
    
    return null;
  }, [getEdgeIssues]);
  
  return {
    ...validationResult,
    getNodeIssues,
    getEdgeIssues,
    hasEdgeWarning,
    getEdgeStyle,
  };
}

/**
 * Hook for checking edge compatibility before creating a connection
 */
export function useEdgeCompatibility() {
  const checkCompatibility = useCallback((sourceNodeType, targetNodeType) => {
    return getEdgeCompatibilityWarning(sourceNodeType, targetNodeType);
  }, []);
  
  return { checkCompatibility };
}

export default useWorkflowValidation;
