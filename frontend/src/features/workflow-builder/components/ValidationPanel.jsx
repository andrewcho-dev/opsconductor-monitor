/**
 * ValidationPanel Component
 * 
 * Displays workflow validation issues including:
 * - Platform compatibility warnings
 * - Missing required parameters
 * - Disconnected nodes
 */

import React from 'react';
import { AlertTriangle, XCircle, Info, CheckCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '../../../lib/utils';
import { ValidationSeverity } from '../services/workflowValidator';

const ValidationPanel = ({ 
  validationResult, 
  isExpanded = false, 
  onToggle,
  onNodeClick 
}) => {
  const { isValid, hasWarnings, errorCount, warningCount, errors, warnings, infos } = validationResult;
  
  // Don't show if no issues
  if (isValid && !hasWarnings) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 bg-emerald-50 border-t border-emerald-200 text-emerald-700 text-sm">
        <CheckCircle className="w-4 h-4" />
        <span>Workflow is valid</span>
      </div>
    );
  }
  
  const getSeverityIcon = (severity) => {
    switch (severity) {
      case ValidationSeverity.ERROR:
        return <XCircle className="w-4 h-4 text-red-500" />;
      case ValidationSeverity.WARNING:
        return <AlertTriangle className="w-4 h-4 text-amber-500" />;
      case ValidationSeverity.INFO:
        return <Info className="w-4 h-4 text-blue-500" />;
      default:
        return null;
    }
  };
  
  const getSeverityClass = (severity) => {
    switch (severity) {
      case ValidationSeverity.ERROR:
        return 'bg-red-50 border-red-200 text-red-700';
      case ValidationSeverity.WARNING:
        return 'bg-amber-50 border-amber-200 text-amber-700';
      case ValidationSeverity.INFO:
        return 'bg-blue-50 border-blue-200 text-blue-700';
      default:
        return 'bg-gray-50 border-gray-200 text-gray-700';
    }
  };
  
  const handleIssueClick = (issue) => {
    if (onNodeClick) {
      const nodeId = issue.nodeId || issue.sourceNodeId || issue.targetNodeId;
      if (nodeId) {
        onNodeClick(nodeId);
      }
    }
  };
  
  return (
    <div className={cn(
      'border-t transition-all',
      errorCount > 0 ? 'border-red-200 bg-red-50' : 'border-amber-200 bg-amber-50'
    )}>
      {/* Header */}
      <button
        onClick={onToggle}
        className={cn(
          'w-full flex items-center justify-between px-3 py-2 text-sm font-medium',
          errorCount > 0 ? 'text-red-700' : 'text-amber-700'
        )}
      >
        <div className="flex items-center gap-2">
          {errorCount > 0 ? (
            <XCircle className="w-4 h-4" />
          ) : (
            <AlertTriangle className="w-4 h-4" />
          )}
          <span>
            {errorCount > 0 && `${errorCount} error${errorCount > 1 ? 's' : ''}`}
            {errorCount > 0 && warningCount > 0 && ', '}
            {warningCount > 0 && `${warningCount} warning${warningCount > 1 ? 's' : ''}`}
          </span>
        </div>
        {isExpanded ? (
          <ChevronDown className="w-4 h-4" />
        ) : (
          <ChevronUp className="w-4 h-4" />
        )}
      </button>
      
      {/* Issue List */}
      {isExpanded && (
        <div className="px-3 pb-3 space-y-2 max-h-48 overflow-y-auto">
          {errors.map((issue, idx) => (
            <div
              key={`error-${idx}`}
              onClick={() => handleIssueClick(issue)}
              className={cn(
                'flex items-start gap-2 p-2 rounded border cursor-pointer hover:opacity-80',
                getSeverityClass(ValidationSeverity.ERROR)
              )}
            >
              {getSeverityIcon(ValidationSeverity.ERROR)}
              <span className="text-xs flex-1">{issue.message}</span>
            </div>
          ))}
          {warnings.map((issue, idx) => (
            <div
              key={`warning-${idx}`}
              onClick={() => handleIssueClick(issue)}
              className={cn(
                'flex items-start gap-2 p-2 rounded border cursor-pointer hover:opacity-80',
                getSeverityClass(ValidationSeverity.WARNING)
              )}
            >
              {getSeverityIcon(ValidationSeverity.WARNING)}
              <span className="text-xs flex-1">{issue.message}</span>
            </div>
          ))}
          {infos.map((issue, idx) => (
            <div
              key={`info-${idx}`}
              onClick={() => handleIssueClick(issue)}
              className={cn(
                'flex items-start gap-2 p-2 rounded border cursor-pointer hover:opacity-80',
                getSeverityClass(ValidationSeverity.INFO)
              )}
            >
              {getSeverityIcon(ValidationSeverity.INFO)}
              <span className="text-xs flex-1">{issue.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ValidationPanel;
