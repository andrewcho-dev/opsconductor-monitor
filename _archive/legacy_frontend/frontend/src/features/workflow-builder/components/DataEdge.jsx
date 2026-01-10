/**
 * DataEdge Component
 * 
 * Custom edge that displays data type information on connections.
 * Shows type badges and data flow direction.
 */

import React from 'react';
import { getBezierPath, EdgeLabelRenderer } from 'reactflow';
import { getNodeDefinition } from '../packages';
import { getTypeInfo } from '../dataTypes';

const DataEdge = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  source,
  target,
  sourceHandleId,
  targetHandleId,
  data,
  style = {},
  selected,
  markerEnd,
}) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  // Get source node definition and output type
  const sourceNodeDef = data?.sourceNodeDef;
  const sourceOutput = sourceNodeDef?.outputs?.find(o => o.id === sourceHandleId);
  const outputType = sourceOutput?.type || 'any';
  const typeInfo = getTypeInfo(outputType);
  
  // Determine edge color based on type
  const isFailure = sourceHandleId === 'failure' || sourceHandleId === 'false';
  const isTrigger = outputType === 'trigger';
  
  let strokeColor = '#6B7280'; // Default gray
  if (selected) {
    strokeColor = '#3B82F6'; // Blue when selected
  } else if (isFailure) {
    strokeColor = '#EF4444'; // Red for failure
  } else if (isTrigger) {
    strokeColor = '#22C55E'; // Green for trigger/success
  } else {
    strokeColor = typeInfo.color || '#F97316'; // Type color or orange for data
  }

  const strokeWidth = selected ? 3 : 2;

  // Only show label for data connections (not triggers)
  const showLabel = !isTrigger && sourceOutput;

  return (
    <>
      <path
        id={id}
        className="react-flow__edge-path"
        d={edgePath}
        style={{
          ...style,
          stroke: strokeColor,
          strokeWidth,
          cursor: 'pointer',
        }}
        markerEnd={markerEnd}
      />
      
      {/* Invisible wider path for easier selection */}
      <path
        d={edgePath}
        fill="none"
        strokeWidth={20}
        stroke="transparent"
        style={{ cursor: 'pointer' }}
      />

      {showLabel && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'all',
            }}
            className="nodrag nopan"
          >
            <div 
              className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium shadow-sm border"
              style={{
                backgroundColor: `${typeInfo.color}15`,
                borderColor: `${typeInfo.color}40`,
                color: typeInfo.color,
              }}
            >
              <span>{typeInfo.icon}</span>
              <span>{sourceOutput?.label || typeInfo.name}</span>
            </div>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
};

export default DataEdge;
