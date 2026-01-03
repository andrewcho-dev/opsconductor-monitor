/**
 * WorkflowNode Component
 * 
 * n8n/Node-RED style workflow node with:
 * - Large icon on left side
 * - Node name prominently displayed
 * - Color-coded by category
 * - Clean, modern design
 */

import React, { memo, useMemo } from 'react';
import { Handle, Position } from 'reactflow';
import { getNodeDefinition } from '../packages';
import { cn } from '../../../lib/utils';
import { PlatformIndicator } from '../components/PlatformBadge';

const WorkflowNode = memo(({ id, data, selected }) => {
  const nodeDefinition = useMemo(() => 
    getNodeDefinition(data.nodeType),
    [data.nodeType]
  );

  if (!nodeDefinition) {
    return (
      <div className="flex items-center bg-red-50 border border-red-300 rounded-lg p-2 min-w-[180px] shadow-sm">
        <div className="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center text-red-500 mr-3">
          ❓
        </div>
        <div>
          <div className="text-red-700 text-sm font-medium">Unknown</div>
          <div className="text-red-400 text-xs">{data.nodeType}</div>
        </div>
      </div>
    );
  }

  const { 
    name, 
    icon, 
    color = '#6366F1', 
    inputs = [], 
    outputs = [],
    category,
    platforms = [],
  } = nodeDefinition;

  const label = data.label || name;
  const subtitle = data.description || nodeDefinition.description || '';

  // n8n-style category colors
  const getCategoryColor = () => {
    switch (category) {
      case 'triggers':
        return { bg: '#10B981', light: '#D1FAE5' }; // Green
      case 'logic':
        return { bg: '#8B5CF6', light: '#EDE9FE' }; // Purple
      case 'data':
        return { bg: '#F59E0B', light: '#FEF3C7' }; // Amber
      case 'notify':
        return { bg: '#EC4899', light: '#FCE7F3' }; // Pink
      case 'network':
        return { bg: '#3B82F6', light: '#DBEAFE' }; // Blue
      default:
        return { bg: color, light: `${color}20` };
    }
  };

  const categoryColor = getCategoryColor();

  // Get a short parameter summary
  const getParamSummary = () => {
    const params = data.parameters || {};
    if (params.network_range) return params.network_range;
    if (params.table) return params.table;
    if (params.channel) return params.channel;
    if (params.target_type === 'from_input') return 'From input';
    return null;
  };

  const paramSummary = getParamSummary();

  return (
    <div
      className={cn(
        'relative flex items-stretch bg-white rounded-xl shadow-lg min-w-[200px] max-w-[280px]',
        'transition-all duration-150 cursor-pointer',
        selected 
          ? 'shadow-xl ring-2 ring-offset-2' 
          : 'hover:shadow-xl hover:scale-[1.02]',
      )}
      style={{ 
        borderColor: selected ? categoryColor.bg : 'transparent',
        '--tw-ring-color': categoryColor.bg,
      }}
    >
      {/* Single Input Handle - Node-RED style */}
      {inputs.length > 0 && (
        <Handle
          type="target"
          position={Position.Left}
          id={inputs[0]?.id || 'input'}
          className="!w-2.5 !h-2.5 !rounded-sm !border-0 !bg-gray-400 hover:!bg-gray-600 transition-colors"
          style={{
            top: '50%',
            transform: 'translateY(-50%)',
            left: '-5px',
          }}
          title="Input"
        />
      )}

      {/* Icon Section - n8n style large icon on left */}
      <div 
        className="flex items-center justify-center w-14 rounded-l-xl flex-shrink-0"
        style={{ backgroundColor: categoryColor.bg }}
      >
        <span className="text-2xl filter drop-shadow-sm">{icon || '⚡'}</span>
      </div>

      {/* Content Section */}
      <div className="flex-1 py-3 px-3 min-w-0">
        <div className="flex items-center gap-1.5">
          <div className="font-semibold text-sm text-gray-900 truncate leading-tight flex-1">
            {label}
          </div>
          {platforms && platforms.length > 0 && (
            <PlatformIndicator platforms={platforms} className="flex-shrink-0" />
          )}
        </div>
        {(subtitle || paramSummary) && (
          <div className="text-xs text-gray-500 truncate mt-0.5">
            {paramSummary || subtitle.substring(0, 40)}
          </div>
        )}
      </div>

      {/* Output Handles - Node-RED style: 1 or 2 outputs max */}
      {outputs.length > 0 && (
        <>
          {/* Primary output (success/main) */}
          <Handle
            type="source"
            position={Position.Right}
            id={outputs.find(o => o.id !== 'failure' && o.id !== 'false')?.id || outputs[0]?.id || 'output'}
            className="!w-2.5 !h-2.5 !rounded-sm !border-0 !bg-gray-400 hover:!bg-gray-600 transition-colors"
            style={{
              top: outputs.some(o => o.id === 'failure' || o.id === 'false') ? '35%' : '50%',
              transform: 'translateY(-50%)',
              right: '-5px',
            }}
            title="Output"
          />
          {/* Secondary output (failure) - only if node has failure path */}
          {outputs.some(o => o.id === 'failure' || o.id === 'false') && (
            <Handle
              type="source"
              position={Position.Right}
              id={outputs.find(o => o.id === 'failure' || o.id === 'false')?.id || 'failure'}
              className="!w-2.5 !h-2.5 !rounded-sm !border-0 !bg-red-400 hover:!bg-red-600 transition-colors"
              style={{
                top: '65%',
                transform: 'translateY(-50%)',
                right: '-5px',
              }}
              title="On Error"
            />
          )}
        </>
      )}

      {/* Execution status badge */}
      {data.executionStatus && (
        <div className={cn(
          'absolute -top-2 -right-2 w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-md',
          data.executionStatus === 'running' && 'bg-blue-500 animate-pulse',
          data.executionStatus === 'success' && 'bg-green-500',
          data.executionStatus === 'error' && 'bg-red-500',
          data.executionStatus === 'pending' && 'bg-gray-400',
        )}>
          {data.executionStatus === 'running' && '⟳'}
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
