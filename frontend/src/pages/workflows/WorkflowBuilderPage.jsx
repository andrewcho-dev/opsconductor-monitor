/**
 * WorkflowBuilderPage
 * 
 * Page wrapper for the visual workflow builder.
 * Handles routing, loading workflow data, and save/run operations.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { GlobalNav } from '../../components/layout';
import WorkflowBuilder from '../../features/workflow-builder/components/WorkflowBuilder';
import { serializeWorkflow, deserializeWorkflow } from '../../features/workflow-builder/utils/serialization';
import * as workflowsApi from '../../api/workflows';

const WorkflowBuilderPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [workflow, setWorkflow] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);

  // Load workflow if editing existing
  useEffect(() => {
    const loadWorkflow = async () => {
      if (!id || id === 'new') {
        // New workflow
        setWorkflow(null);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const response = await workflowsApi.getWorkflow(id);
        // API returns { success: true, data: {...} }
        const data = response.data || response;
        setWorkflow(deserializeWorkflow(data));
      } catch (err) {
        console.error('Failed to load workflow:', err);
        setError(err.message || 'Failed to load workflow');
      } finally {
        setLoading(false);
      }
    };

    loadWorkflow();
  }, [id]);

  // Handle save
  const handleSave = useCallback(async (workflowData) => {
    try {
      setSaving(true);
      const serialized = serializeWorkflow(workflowData);

      if (workflowData.id) {
        // Update existing
        await workflowsApi.updateWorkflow(workflowData.id, serialized);
      } else {
        // Create new
        const response = await workflowsApi.createWorkflow(serialized);
        const created = response.data || response;
        // Navigate to the new workflow's URL
        navigate(`/workflows/${created.id}`, { replace: true });
      }
    } catch (err) {
      console.error('Failed to save workflow:', err);
      throw err;
    } finally {
      setSaving(false);
    }
  }, [navigate]);

  // Handle run
  const handleRun = useCallback(async (workflowData) => {
    if (!workflowData.id) {
      alert('Please save the workflow before running');
      return null;
    }

    try {
      setRunning(true);
      const response = await workflowsApi.runWorkflow(workflowData.id);
      // Return the execution result for the debug view
      return response.data || response;
    } catch (err) {
      console.error('Failed to run workflow:', err);
      throw err;
    } finally {
      setRunning(false);
    }
  }, []);

  // Handle test
  const handleTest = useCallback(async (workflowData) => {
    if (!workflowData.id) {
      alert('Please save the workflow before testing');
      return null;
    }

    try {
      const response = await workflowsApi.testWorkflow(workflowData.id);
      // Return the test result for the debug view
      return response.data || response;
    } catch (err) {
      console.error('Failed to test workflow:', err);
      throw err;
    }
  }, []);

  // Handle back
  const handleBack = useCallback(() => {
    navigate('/workflows');
  }, [navigate]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <GlobalNav />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-gray-600">Loading workflow...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <GlobalNav />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-md">
            <div className="text-red-500 text-5xl mb-4">⚠️</div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Failed to Load Workflow</h2>
            <p className="text-gray-600 mb-4">{error}</p>
            <button
              onClick={() => navigate('/workflows')}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Back to Workflows
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <GlobalNav />
      <div className="flex-1 overflow-hidden">
        <WorkflowBuilder
          initialWorkflow={workflow}
          onSave={handleSave}
          onRun={handleRun}
          onTest={handleTest}
          onBack={handleBack}
        />
      </div>
    </div>
  );
};

export default WorkflowBuilderPage;
