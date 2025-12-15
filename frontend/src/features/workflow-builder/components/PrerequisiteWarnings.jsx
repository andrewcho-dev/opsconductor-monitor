/**
 * PrerequisiteWarnings Component
 * 
 * Displays warnings about missing credentials and prerequisites
 * for nodes in the workflow.
 */

import React, { useMemo } from 'react';
import { AlertTriangle, Key, Terminal, CheckCircle, XCircle, ExternalLink } from 'lucide-react';
import { cn } from '../../../lib/utils';

export function PrerequisiteWarnings({ 
  credentialValidation, 
  prerequisiteResults,
  nodes,
  onNavigateToCredentials,
  className 
}) {
  // Compute warnings from credential validation
  const credentialWarnings = useMemo(() => {
    if (!credentialValidation || credentialValidation.valid) return [];
    
    const warnings = [];
    const missingTypes = new Set();
    
    for (const [nodeId, result] of Object.entries(credentialValidation.nodeResults || {})) {
      if (!result.valid && result.missing) {
        const node = nodes?.find(n => n.id === nodeId);
        result.missing.forEach(m => {
          if (!missingTypes.has(m.type)) {
            missingTypes.add(m.type);
            warnings.push({
              type: 'credential',
              credentialType: m.type,
              label: m.label,
              vaultType: m.vaultType,
              affectedNodes: [],
            });
          }
          const warning = warnings.find(w => w.credentialType === m.type);
          if (warning && node) {
            warning.affectedNodes.push(node.data?.label || node.name || nodeId);
          }
        });
      }
    }
    
    return warnings;
  }, [credentialValidation, nodes]);

  // Compute warnings from prerequisite checks
  const prereqWarnings = useMemo(() => {
    if (!prerequisiteResults || prerequisiteResults.valid) return [];
    
    const warnings = [];
    
    for (const [nodeId, result] of Object.entries(prerequisiteResults.nodeResults || {})) {
      if (!result.valid) {
        const failedChecks = result.checks.filter(c => c.available === false);
        failedChecks.forEach(check => {
          warnings.push({
            type: 'prerequisite',
            checkType: check.type,
            name: check.name,
            nodeName: result.nodeName,
            error: check.error,
          });
        });
      }
    }
    
    return warnings;
  }, [prerequisiteResults]);

  // Combine all warnings
  const allWarnings = [...credentialWarnings, ...prereqWarnings];
  
  if (allWarnings.length === 0) {
    return null;
  }

  return (
    <div className={cn(
      'bg-amber-50 border border-amber-200 rounded-lg p-3',
      className
    )}>
      <div className="flex items-start gap-2">
        <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-amber-800">
            Prerequisites Missing
          </h4>
          <p className="text-xs text-amber-700 mt-0.5">
            Some nodes require configuration before they can run.
          </p>
          
          {/* Credential Warnings */}
          {credentialWarnings.length > 0 && (
            <div className="mt-3 space-y-2">
              <div className="text-xs font-medium text-amber-800 flex items-center gap-1">
                <Key className="w-3 h-3" />
                Missing Credentials
              </div>
              {credentialWarnings.map((warning, idx) => (
                <div 
                  key={idx}
                  className="bg-white/50 rounded px-2 py-1.5 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-amber-900">
                      {warning.label}
                    </span>
                    <span className="text-amber-600 bg-amber-100 px-1.5 py-0.5 rounded text-[10px]">
                      {warning.vaultType}
                    </span>
                  </div>
                  {warning.affectedNodes.length > 0 && (
                    <div className="text-amber-700 mt-1">
                      Used by: {warning.affectedNodes.slice(0, 3).join(', ')}
                      {warning.affectedNodes.length > 3 && ` +${warning.affectedNodes.length - 3} more`}
                    </div>
                  )}
                </div>
              ))}
              {onNavigateToCredentials && (
                <button
                  onClick={onNavigateToCredentials}
                  className="flex items-center gap-1 text-xs text-amber-700 hover:text-amber-900 mt-2"
                >
                  <ExternalLink className="w-3 h-3" />
                  Configure credentials
                </button>
              )}
            </div>
          )}
          
          {/* Prerequisite Warnings */}
          {prereqWarnings.length > 0 && (
            <div className="mt-3 space-y-2">
              <div className="text-xs font-medium text-amber-800 flex items-center gap-1">
                <Terminal className="w-3 h-3" />
                Missing Prerequisites
              </div>
              {prereqWarnings.map((warning, idx) => (
                <div 
                  key={idx}
                  className="bg-white/50 rounded px-2 py-1.5 text-xs"
                >
                  <div className="flex items-center gap-2">
                    <XCircle className="w-3 h-3 text-red-500" />
                    <span className="font-medium text-amber-900">
                      {warning.name}
                    </span>
                  </div>
                  <div className="text-amber-700 mt-0.5">
                    Required by: {warning.nodeName}
                  </div>
                  {warning.error && (
                    <div className="text-red-600 mt-0.5 text-[10px]">
                      {warning.error}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Compact inline warning badge for individual nodes
 */
export function NodePrerequisiteBadge({ node, credentialValidation }) {
  const validation = credentialValidation?.nodeResults?.[node.id];
  
  if (!validation || validation.valid) {
    return null;
  }
  
  const missingCount = validation.missing?.length || 0;
  
  return (
    <div 
      className="absolute -top-1 -right-1 bg-amber-500 text-white rounded-full w-4 h-4 flex items-center justify-center text-[10px] font-bold shadow-sm"
      title={`Missing ${missingCount} credential${missingCount > 1 ? 's' : ''}`}
    >
      !
    </div>
  );
}

/**
 * Success indicator when all prerequisites are met
 */
export function PrerequisiteSuccess({ className }) {
  return (
    <div className={cn(
      'bg-green-50 border border-green-200 rounded-lg p-3 flex items-center gap-2',
      className
    )}>
      <CheckCircle className="w-5 h-5 text-green-500" />
      <div>
        <div className="text-sm font-medium text-green-800">
          All prerequisites met
        </div>
        <div className="text-xs text-green-600">
          Workflow is ready to execute
        </div>
      </div>
    </div>
  );
}

export default PrerequisiteWarnings;
