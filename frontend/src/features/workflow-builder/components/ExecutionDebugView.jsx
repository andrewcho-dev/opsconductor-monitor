/**
 * ExecutionDebugView Component
 * 
 * Shows workflow submission confirmation with link to Job History for monitoring.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  X,
  CheckCircle,
  ExternalLink,
  History,
} from 'lucide-react';

const ExecutionDebugView = ({
  isOpen,
  onClose,
  executionId,
  workflowName,
  isTestMode = false,
  executionResult = null,
  isRunning = false,
}) => {
  const navigate = useNavigate();

  if (!isOpen) return null;

  const handleViewHistory = () => {
    onClose();
    navigate('/job-history');
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-2xl w-[480px] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <CheckCircle className="w-6 h-6 text-green-500" />
            <h2 className="text-lg font-semibold text-gray-900">
              {isTestMode ? 'Test' : 'Workflow'} Submitted
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-6">
          <div className="text-center mb-6">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-8 h-8 text-green-600" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Successfully Queued
            </h3>
            <p className="text-sm text-gray-600">
              <span className="font-medium">{workflowName}</span> has been submitted for execution.
            </p>
          </div>

          {executionId && (
            <div className="bg-gray-50 rounded-lg p-4 mb-6">
              <div className="text-xs text-gray-500 mb-1">Task ID</div>
              <div className="font-mono text-sm text-gray-800 break-all">
                {executionId}
              </div>
            </div>
          )}

          {isTestMode && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-6">
              <p className="text-sm text-yellow-800">
                <strong>Test Mode:</strong> This is a test run. No permanent changes will be made.
              </p>
            </div>
          )}

          <p className="text-sm text-gray-500 text-center">
            Monitor execution progress and view results in Job History.
          </p>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
          >
            Close
          </button>
          <button
            onClick={handleViewHistory}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md"
          >
            <History className="w-4 h-4" />
            View Job History
            <ExternalLink className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExecutionDebugView;
