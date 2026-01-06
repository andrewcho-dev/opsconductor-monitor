/**
 * usePrerequisiteCheck Hook
 * 
 * Provides runtime prerequisite checking for workflow nodes.
 * Validates tools, network access, and other requirements before execution.
 */

import { useState, useCallback } from 'react';
import { fetchApi } from '../../../lib/api';

export function usePrerequisiteCheck() {
  const [checking, setChecking] = useState(false);
  const [results, setResults] = useState(null);

  // Check if a tool is available on the server
  const checkTool = useCallback(async (toolName) => {
    try {
      const response = await fetchApi(`/system/v1/check-tool?tool=${encodeURIComponent(toolName)}`);
      return {
        tool: toolName,
        available: response.data?.available ?? false,
        version: response.data?.version,
        path: response.data?.path,
      };
    } catch (err) {
      return {
        tool: toolName,
        available: false,
        error: err.message,
      };
    }
  }, []);

  // Check network connectivity
  const checkNetwork = useCallback(async () => {
    try {
      const response = await fetchApi('/system/v1/check-network');
      return {
        available: response.data?.available ?? true,
        internet: response.data?.internet ?? true,
      };
    } catch (err) {
      // If we can reach the API, network is available
      return { available: true, internet: false };
    }
  }, []);

  // Check database connectivity
  const checkDatabase = useCallback(async () => {
    try {
      const response = await fetchApi('/system/v1/check-database');
      return {
        available: response.data?.available ?? false,
        type: response.data?.type,
      };
    } catch (err) {
      return {
        available: false,
        error: err.message,
      };
    }
  }, []);

  // Check all prerequisites for a node
  const checkNodePrerequisites = useCallback(async (node) => {
    const requirements = node.execution?.requirements || {};
    const results = {
      nodeId: node.id,
      nodeName: node.name,
      valid: true,
      checks: [],
    };

    // Check tools
    if (requirements.tools && requirements.tools.length > 0) {
      for (const tool of requirements.tools) {
        const toolResult = await checkTool(tool);
        results.checks.push({
          type: 'tool',
          name: tool,
          ...toolResult,
        });
        if (!toolResult.available) {
          results.valid = false;
        }
      }
    }

    // Check network
    if (requirements.network) {
      const networkResult = await checkNetwork();
      results.checks.push({
        type: 'network',
        name: 'Network Access',
        ...networkResult,
      });
      if (!networkResult.available) {
        results.valid = false;
      }
    }

    // Check database
    if (requirements.database) {
      const dbResult = await checkDatabase();
      results.checks.push({
        type: 'database',
        name: 'Database Connection',
        ...dbResult,
      });
      if (!dbResult.available) {
        results.valid = false;
      }
    }

    // Check root requirement (just flag it, can't verify from frontend)
    if (requirements.root) {
      results.checks.push({
        type: 'permission',
        name: 'Root/Admin Access',
        available: null, // Unknown from frontend
        warning: 'This node requires elevated privileges',
      });
    }

    return results;
  }, [checkTool, checkNetwork, checkDatabase]);

  // Check prerequisites for all nodes in a workflow
  const checkWorkflowPrerequisites = useCallback(async (nodes) => {
    setChecking(true);
    
    try {
      const nodeResults = {};
      let allValid = true;
      const toolsNeeded = new Set();
      const warnings = [];

      for (const node of nodes) {
        const requirements = node.execution?.requirements;
        if (!requirements || Object.keys(requirements).length === 0) {
          nodeResults[node.id] = { valid: true, checks: [] };
          continue;
        }

        const result = await checkNodePrerequisites(node);
        nodeResults[node.id] = result;
        
        if (!result.valid) {
          allValid = false;
        }

        // Collect tools needed
        if (requirements.tools) {
          requirements.tools.forEach(t => toolsNeeded.add(t));
        }

        // Collect warnings
        result.checks
          .filter(c => c.warning)
          .forEach(c => warnings.push({ node: node.name, ...c }));
      }

      const finalResults = {
        valid: allValid,
        nodeResults,
        toolsNeeded: Array.from(toolsNeeded),
        warnings,
        checkedAt: new Date().toISOString(),
      };

      setResults(finalResults);
      return finalResults;
    } finally {
      setChecking(false);
    }
  }, [checkNodePrerequisites]);

  // Quick check - just validates without detailed results
  const quickCheck = useCallback((nodes) => {
    const issues = [];
    
    for (const node of nodes) {
      const requirements = node.execution?.requirements || {};
      
      // Flag nodes that need tools (we can't verify without API call)
      if (requirements.tools && requirements.tools.length > 0) {
        issues.push({
          nodeId: node.id,
          nodeName: node.name,
          type: 'tools',
          message: `Requires tools: ${requirements.tools.join(', ')}`,
        });
      }
      
      // Flag nodes that need root
      if (requirements.root) {
        issues.push({
          nodeId: node.id,
          nodeName: node.name,
          type: 'permission',
          message: 'Requires root/admin privileges',
        });
      }
    }
    
    return {
      hasIssues: issues.length > 0,
      issues,
    };
  }, []);

  return {
    checking,
    results,
    checkNodePrerequisites,
    checkWorkflowPrerequisites,
    quickCheck,
    checkTool,
    checkNetwork,
    checkDatabase,
  };
}

export default usePrerequisiteCheck;
