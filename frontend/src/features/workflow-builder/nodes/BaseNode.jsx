/**
 * BaseNode Component
 * 
 * Base component for all workflow nodes.
 * Provides consistent styling and handle rendering.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';
import { cn } from '../../../lib/utils';

const BaseNode = memo(({ 
  data, 
  selected,
  nodeDefinition,
  children,
  className,
}) => {
  const { label, description } = data;
  const { icon, color, inputs = [], outputs = [] } = nodeDefinition || {};

  return (
    <div
      className={cn(
        'relative bg-white rounded-lg shadow-md border-2 min-w-[180px] max-w-[280px]',
        'transition-shadow duration-200',
        selected ? 'shadow-lg ring-2 ring-blue-400' : 'hover:shadow-lg',
        className
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
            'w-3 h-3 rounded-full border-2 border-white',
            input.type === 'trigger' ? 'bg-green-500' : 'bg-blue-500'
          )}
          style={{
            top: `${((index + 1) / (inputs.length + 1)) * 100}%`,
          }}
          title={input.label}
        />
      ))}

      {/* Node Header */}
      <div
        className="px-3 py-2 rounded-t-md flex items-center gap-2"
        style={{ backgroundColor: `${color}15` || '#F3F4F6' }}
      >
        <span className="text-lg">{icon || '⚡'}</span>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm text-gray-900 truncate">
            {label}
          </div>
          {description && (
            <div className="text-xs text-gray-500 truncate">
              {description}
            </div>
          )}
        </div>
      </div>

      {/* Node Body */}
      {children && (
        <div className="px-3 py-2 text-xs text-gray-600 border-t border-gray-100">
          {children}
        </div>
      )}

      {/* Output Handles */}
      {outputs.map((output, index) => (
        <Handle
          key={output.id}
          type="source"
          position={Position.Right}
          id={output.id}
          className={cn(
            'w-3 h-3 rounded-full border-2 border-white',
            output.type === 'trigger' 
              ? output.id === 'failure' || output.id === 'false'
                ? 'bg-red-500'
                : 'bg-green-500'
              : 'bg-orange-500'
          )}
          style={{
            top: `${((index + 1) / (outputs.length + 1)) * 100}%`,
          }}
          title={output.label}
        />
      ))}

      {/* Output Labels (shown on right side) */}
      {outputs.length > 0 && (
        <div className="absolute right-0 top-0 h-full flex flex-col justify-around pr-5 pointer-events-none">
          {outputs.map((output) => (
            <div
              key={output.id}
              className="text-[10px] text-gray-400 text-right"
            >
              {output.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
});

BaseNode.displayName = 'BaseNode';

export default BaseNode;
