/**
 * ExecutionDebugView Component
 * 
 * Shows step-by-step execution progress with logs and variable state.
 * Used for both live execution monitoring and test run mode.
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Play,
  Square,
  CheckCircle,
  XCircle,
  Clock,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { cn } from '../../../lib/utils';

const ExecutionDebugView = ({
  isOpen,
  onClose,
  executionId,
  workflowName,
  isTestMode = false,
  executionResult = null,
  isRunning = false,
  onStop,
}) => {
  const [expandedNodes, setExpandedNodes] = useState(new Set());
  const [activeTab, setActiveTab] = useState('log'); // 'log' | 'variables'
  const logEndRef = useRef(null);

  // Auto-scroll to bottom of log
  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [executionResult?.node_results]);

  if (!isOpen) return null;

  const nodeResults = executionResult?.node_results || {};
  const variables = executionResult?.variables || {};
  const sortedNodes = Object.entries(nodeResults).sort((a, b) => {
    const aTime = a[1].started_at || '';
    const bTime = b[1].started_at || '';
    return aTime.localeCompare(bTime);
  });

  const toggleNode = (nodeId) => {
    setExpandedNodes(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failure':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'running':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'pending':
        return <Clock className="w-4 h-4 text-gray-400" />;
      default:
        return <AlertCircle className="w-4 h-4 text-yellow-500" />;
    }
  };

  const formatDuration = (ms) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
    return `${(ms / 60000).toFixed(2)}m`;
  };

  const formatTime = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit',
      fractionalSecondDigits: 3
    });
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-2xl w-[900px] max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            {isRunning ? (
              <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
            ) : executionResult?.status === 'success' ? (
              <CheckCircle className="w-5 h-5 text-green-500" />
            ) : executionResult?.status === 'failure' ? (
              <XCircle className="w-5 h-5 text-red-500" />
            ) : (
              <Play className="w-5 h-5 text-gray-500" />
            )}
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {isTestMode ? 'Test Run' : 'Execution'}: {workflowName}
              </h2>
              <p className="text-sm text-gray-500">
                {executionId ? `ID: ${executionId.slice(0, 8)}...` : 'Starting...'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isRunning && onStop && (
              <button
                onClick={onStop}
                className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-md"
              >
                <Square className="w-4 h-4" />
                Stop
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Summary Bar */}
        {executionResult && (
          <div className="px-6 py-3 bg-gray-50 border-b border-gray-200 flex items-center gap-6 text-sm">
            <div>
              <span className="text-gray-500">Status:</span>{' '}
              <span className={cn(
                'font-medium',
                executionResult.status === 'success' ? 'text-green-600' : 'text-red-600'
              )}>
                {executionResult.status?.toUpperCase()}
              </span>
            </div>
            <div>
              <span className="text-gray-500">Duration:</span>{' '}
              <span className="font-medium">{formatDuration(executionResult.duration_ms || 0)}</span>
            </div>
            <div>
              <span className="text-gray-500">Nodes:</span>{' '}
              <span className="font-medium text-green-600">{executionResult.nodes_completed || 0}</span>
              {executionResult.nodes_failed > 0 && (
                <span className="font-medium text-red-600"> / {executionResult.nodes_failed} failed</span>
              )}
            </div>
            {isTestMode && (
              <div className="ml-auto px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded text-xs font-medium">
                TEST MODE - No side effects
              </div>
            )}
          </div>
        )}

        {/* Tabs */}
        <div className="flex border-b border-gray-200">
          <button
            onClick={() => setActiveTab('log')}
            className={cn(
              'px-6 py-3 text-sm font-medium border-b-2 -mb-px',
              activeTab === 'log'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            )}
          >
            Execution Log
          </button>
          <button
            onClick={() => setActiveTab('variables')}
            className={cn(
              'px-6 py-3 text-sm font-medium border-b-2 -mb-px',
              activeTab === 'variables'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            )}
          >
            Variables
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {activeTab === 'log' ? (
            <div className="space-y-2">
              {sortedNodes.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  {isRunning ? 'Waiting for execution to start...' : 'No execution data'}
                </div>
              ) : (
                sortedNodes.map(([nodeId, result]) => (
                  <div
                    key={nodeId}
                    className="border border-gray-200 rounded-lg overflow-hidden"
                  >
                    {/* Node Header */}
                    <button
                      onClick={() => toggleNode(nodeId)}
                      className="w-full flex items-center gap-3 px-4 py-3 bg-gray-50 hover:bg-gray-100 text-left"
                    >
                      {expandedNodes.has(nodeId) ? (
                        <ChevronDown className="w-4 h-4 text-gray-400" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-gray-400" />
                      )}
                      {getStatusIcon(result.status)}
                      <div className="flex-1 min-w-0">
                        <span className="font-medium text-gray-900">
                          {result.node_type || nodeId}
                        </span>
                        <span className="ml-2 text-sm text-gray-500">
                          {nodeId}
                        </span>
                      </div>
                      <span className="text-xs text-gray-400">
                        {formatTime(result.started_at)}
                      </span>
                      <span className="text-xs text-gray-500 font-mono">
                        {formatDuration(result.duration_ms || 0)}
                      </span>
                    </button>

                    {/* Node Details */}
                    {expandedNodes.has(nodeId) && (
                      <div className="px-4 py-3 border-t border-gray-200 bg-white">
                        {result.error_message && (
                          <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-md">
                            <p className="text-sm text-red-700 font-medium">Error</p>
                            <p className="text-sm text-red-600 mt-1">{result.error_message}</p>
                          </div>
                        )}
                        
                        <div>
                          <p className="text-xs font-medium text-gray-500 uppercase mb-2">Output</p>
                          <pre className="text-xs bg-gray-900 text-gray-100 p-3 rounded-md overflow-x-auto max-h-48">
                            {JSON.stringify(result.output_data, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
              <div ref={logEndRef} />
            </div>
          ) : (
            <div className="space-y-4">
              {Object.keys(variables).length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  No variables set
                </div>
              ) : (
                Object.entries(variables).map(([key, value]) => (
                  <div key={key} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-sm font-medium text-blue-600">
                        {key}
                      </span>
                      <span className="text-xs text-gray-400">
                        {typeof value}
                      </span>
                    </div>
                    <pre className="text-xs bg-gray-100 p-3 rounded-md overflow-x-auto max-h-32">
                      {typeof value === 'object' 
                        ? JSON.stringify(value, null, 2)
                        : String(value)
                      }
                    </pre>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExecutionDebugView;
