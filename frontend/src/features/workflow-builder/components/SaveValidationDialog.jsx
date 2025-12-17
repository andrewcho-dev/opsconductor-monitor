/**
 * SaveValidationDialog Component
 * 
 * Modal dialog shown before saving a workflow that has validation issues.
 * Allows users to review warnings and decide whether to proceed.
 */

import React from 'react';
import { AlertTriangle, XCircle, CheckCircle, X } from 'lucide-react';
import { cn } from '../../../lib/utils';
import { ValidationSeverity } from '../services/workflowValidator';

const SaveValidationDialog = ({ 
  isOpen, 
  onClose, 
  onSave, 
  onCancel,
  validationResult,
  workflowName 
}) => {
  if (!isOpen) return null;
  
  const { isValid, hasWarnings, errorCount, warningCount, errors, warnings } = validationResult;
  
  // If valid with no warnings, don't show dialog
  if (isValid && !hasWarnings) {
    return null;
  }
  
  const hasBlockingErrors = errorCount > 0;
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />
      
      {/* Dialog */}
      <div className="relative bg-white rounded-xl shadow-2xl max-w-lg w-full mx-4 overflow-hidden">
        {/* Header */}
        <div className={cn(
          'flex items-center justify-between px-6 py-4',
          hasBlockingErrors ? 'bg-red-50' : 'bg-amber-50'
        )}>
          <div className="flex items-center gap-3">
            {hasBlockingErrors ? (
              <XCircle className="w-6 h-6 text-red-500" />
            ) : (
              <AlertTriangle className="w-6 h-6 text-amber-500" />
            )}
            <div>
              <h3 className={cn(
                'font-semibold',
                hasBlockingErrors ? 'text-red-900' : 'text-amber-900'
              )}>
                {hasBlockingErrors ? 'Cannot Save Workflow' : 'Save with Warnings?'}
              </h3>
              <p className={cn(
                'text-sm',
                hasBlockingErrors ? 'text-red-700' : 'text-amber-700'
              )}>
                {workflowName || 'Untitled Workflow'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-black/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Content */}
        <div className="px-6 py-4 max-h-80 overflow-y-auto">
          {/* Errors */}
          {errors.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-medium text-red-700 mb-2 flex items-center gap-2">
                <XCircle className="w-4 h-4" />
                Errors ({errors.length})
              </h4>
              <div className="space-y-2">
                {errors.map((issue, idx) => (
                  <div
                    key={`error-${idx}`}
                    className="flex items-start gap-2 p-3 rounded-lg bg-red-50 border border-red-200"
                  >
                    <span className="text-sm text-red-700">{issue.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Warnings */}
          {warnings.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-amber-700 mb-2 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Warnings ({warnings.length})
              </h4>
              <div className="space-y-2">
                {warnings.map((issue, idx) => (
                  <div
                    key={`warning-${idx}`}
                    className="flex items-start gap-2 p-3 rounded-lg bg-amber-50 border border-amber-200"
                  >
                    <span className="text-sm text-amber-700">{issue.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Platform mismatch explanation */}
          {warnings.some(w => w.type === 'platform_mismatch') && (
            <div className="mt-4 p-3 rounded-lg bg-blue-50 border border-blue-200">
              <p className="text-sm text-blue-700">
                <strong>Platform Mismatch:</strong> Some nodes in your workflow target different 
                platforms. When the workflow runs, incompatible devices will be skipped with a 
                clear log message.
              </p>
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div className={cn(
          'flex items-center justify-end gap-3 px-6 py-4 border-t',
          hasBlockingErrors ? 'bg-gray-50' : 'bg-white'
        )}>
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          {!hasBlockingErrors && (
            <button
              onClick={onSave}
              className="px-4 py-2 text-sm font-medium text-white bg-amber-500 rounded-lg hover:bg-amber-600 transition-colors flex items-center gap-2"
            >
              <AlertTriangle className="w-4 h-4" />
              Save Anyway
            </button>
          )}
          {hasBlockingErrors && (
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-500 rounded-lg hover:bg-blue-600 transition-colors"
            >
              Fix Issues
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default SaveValidationDialog;
