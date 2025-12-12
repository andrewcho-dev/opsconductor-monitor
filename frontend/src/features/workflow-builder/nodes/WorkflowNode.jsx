/**
 * WorkflowNode Component
 * 
 * Generic workflow node that renders based on node definition.
 * Used for all node types in the workflow builder.
 */

import React, { memo, useMemo } from 'react';
import { Handle, Position } from 'reactflow';
import { getNodeDefinition } from '../packages';
import { cn } from '../../../lib/utils';

const WorkflowNode = memo(({ id, data, selected }) => {
  const nodeDefinition = useMemo(() => 
    getNodeDefinition(data.nodeType),
    [data.nodeType]
  );

  if (!nodeDefinition) {
    return (
      <div className="bg-red-100 border-2 border-red-400 rounded-lg p-3 min-w-[150px]">
        <div className="text-red-700 text-sm font-medium">Unknown Node</div>
        <div className="text-red-500 text-xs">{data.nodeType}</div>
      </div>
    );
  }

  const { 
    name, 
    icon, 
    color, 
    inputs = [], 
    outputs = [],
    category,
  } = nodeDefinition;

  const label = data.label || name;
  const description = data.description || '';

  // Get category-based styling
  const getCategoryStyle = () => {
    switch (category) {
      case 'triggers':
        return 'border-green-500 bg-green-50';
      case 'logic':
        return 'border-purple-500 bg-purple-50';
      case 'data':
        return 'border-orange-500 bg-orange-50';
      case 'notify':
        return 'border-pink-500 bg-pink-50';
      default:
        return 'border-blue-500 bg-blue-50';
    }
  };

  // Format parameter preview
  const getParameterPreview = () => {
    const params = data.parameters || {};
    const previews = [];

    // Show key parameters based on node type
    if (params.target_type) {
      if (params.target_type === 'network_range' && params.network_range) {
        previews.push(`Target: ${params.network_range}`);
      } else if (params.target_type === 'from_input') {
        previews.push('Target: From previous');
      } else if (params.target_type === 'device_group' && params.device_group) {
        previews.push(`Group: ${params.device_group}`);
      }
    }

    if (params.schedule_type === 'interval' && params.interval_minutes) {
      previews.push(`Every ${params.interval_minutes} min`);
    } else if (params.schedule_type === 'cron' && params.cron_expression) {
      previews.push(`Cron: ${params.cron_expression}`);
    }

    if (params.command) {
      const cmd = params.command.length > 30 
        ? params.command.substring(0, 30) + '...' 
        : params.command;
      previews.push(`Cmd: ${cmd}`);
    }

    if (params.table) {
      previews.push(`Table: ${params.table}`);
    }

    if (params.channel) {
      previews.push(`Channel: ${params.channel}`);
    }

    if (params.condition_type && params.condition_type !== 'expression') {
      previews.push(`Condition: ${params.condition_type}`);
    }

    return previews.slice(0, 2); // Max 2 preview lines
  };

  const parameterPreviews = getParameterPreview();

  return (
    <div
      className={cn(
        'relative bg-white rounded-lg shadow-md border-2 min-w-[200px] max-w-[300px]',
        'transition-all duration-200',
        selected ? 'shadow-xl ring-2 ring-blue-400 ring-offset-2' : 'hover:shadow-lg',
      )}
      style={{ borderColor: color || '#6B7280' }}
    >
      {/* Input Handles */}
      {inputs.map((input, index) => (
        <Handle
          key={input.id}
          type="target"
          position={Position.Left}
          id={input.id}
          className={cn(
            'w-3 h-3 rounded-full border-2 border-white transition-transform hover:scale-125',
            input.type === 'trigger' ? 'bg-green-500' : 'bg-blue-500'
          )}
          style={{
            top: inputs.length === 1 
              ? '50%' 
              : `${((index + 1) / (inputs.length + 1)) * 100}%`,
            transform: 'translateY(-50%)',
          }}
          title={input.label}
        />
      ))}

      {/* Node Header */}
      <div
        className="px-3 py-2 rounded-t-md flex items-center gap-2"
        style={{ backgroundColor: `${color}20` || '#F3F4F6' }}
      >
        <span className="text-base flex-shrink-0">{icon || '⚡'}</span>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-sm text-gray-900 truncate">
            {label}
          </div>
        </div>
      </div>

      {/* Node Body - Parameter Preview */}
      {(description || parameterPreviews.length > 0) && (
        <div className="px-3 py-2 text-xs border-t border-gray-100 space-y-1">
          {description && (
            <div className="text-gray-500 italic truncate">{description}</div>
          )}
          {parameterPreviews.map((preview, idx) => (
            <div key={idx} className="text-gray-600 truncate font-mono">
              {preview}
            </div>
          ))}
        </div>
      )}

      {/* Output Labels Footer - only show if multiple outputs */}
      {outputs.length > 1 && (
        <div className="px-3 py-1.5 border-t border-gray-100 flex flex-col gap-0.5">
          {outputs.map((output) => (
            <div 
              key={output.id}
              className="flex items-center justify-end gap-1.5 text-xs"
            >
              <span className="text-gray-500">{output.label}</span>
              <span 
                className={cn(
                  'w-2 h-2 rounded-full',
                  output.type === 'trigger'
                    ? output.id === 'failure' || output.id === 'false'
                      ? 'bg-red-500'
                      : 'bg-green-500'
                    : 'bg-orange-500'
                )}
              />
            </div>
          ))}
        </div>
      )}

      {/* Output Handles - positioned on main container */}
      {outputs.map((output, index) => (
        <Handle
          key={output.id}
          type="source"
          position={Position.Right}
          id={output.id}
          className={cn(
            'w-3 h-3 rounded-full border-2 border-white transition-transform hover:scale-125',
            output.type === 'trigger'
              ? output.id === 'failure' || output.id === 'false'
                ? 'bg-red-500'
                : 'bg-green-500'
              : 'bg-orange-500'
          )}
          style={{
            top: outputs.length === 1 
              ? '50%' 
              : `${((index + 1) / (outputs.length + 1)) * 100}%`,
            transform: 'translateY(-50%)',
          }}
          title={output.label}
        />
      ))}

      {/* Execution status indicator (shown during execution) */}
      {data.executionStatus && (
        <div className={cn(
          'absolute -top-2 -right-2 w-5 h-5 rounded-full flex items-center justify-center text-white text-xs font-bold',
          data.executionStatus === 'running' && 'bg-blue-500 animate-pulse',
          data.executionStatus === 'success' && 'bg-green-500',
          data.executionStatus === 'error' && 'bg-red-500',
          data.executionStatus === 'pending' && 'bg-gray-400',
        )}>
          {data.executionStatus === 'running' && '▶'}
          {data.executionStatus === 'success' && '✓'}
          {data.executionStatus === 'error' && '✗'}
          {data.executionStatus === 'pending' && '○'}
        </div>
      )}
    </div>
  );
});

WorkflowNode.displayName = 'WorkflowNode';

export default WorkflowNode;
