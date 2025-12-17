/**
 * DataMappingPanel Component
 * 
 * Shows available data from upstream nodes and allows users to map
 * outputs to inputs. Displays in the node editor sidebar.
 */

import React, { useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, Link2, Unlink, Info, Zap } from 'lucide-react';
import { getNodeDefinition } from '../packages';
import { getTypeInfo, areTypesCompatible } from '../dataTypes';
import { cn } from '../../../lib/utils';

const DataMappingPanel = ({
  currentNode,
  currentNodeDef,
  allNodes,
  edges,
  onMapInput,
  mappedInputs = {},
}) => {
  const [expandedNodes, setExpandedNodes] = useState({});
  const [selectedInput, setSelectedInput] = useState(null);

  // Find upstream nodes (nodes that connect TO this node)
  const upstreamNodes = useMemo(() => {
    if (!currentNode || !edges || !allNodes) return [];
    
    const incomingEdges = edges.filter(e => e.target === currentNode.id);
    const upstreamNodeIds = [...new Set(incomingEdges.map(e => e.source))];
    
    return upstreamNodeIds.map(nodeId => {
      const node = allNodes.find(n => n.id === nodeId);
      if (!node) return null;
      
      const nodeDef = getNodeDefinition(node.data?.nodeType);
      return {
        node,
        nodeDef,
        outputs: nodeDef?.outputs || [],
        label: node.data?.label || nodeDef?.name || node.data?.nodeType,
      };
    }).filter(Boolean);
  }, [currentNode, edges, allNodes]);

  // Get inputs for current node that can accept data
  const dataInputs = useMemo(() => {
    if (!currentNodeDef?.inputs) return [];
    return currentNodeDef.inputs.filter(input => input.type !== 'trigger');
  }, [currentNodeDef]);

  const toggleNode = (nodeId) => {
    setExpandedNodes(prev => ({
      ...prev,
      [nodeId]: !prev[nodeId],
    }));
  };

  const handleMapOutput = (upstreamNodeId, outputId, inputId) => {
    if (onMapInput) {
      onMapInput(inputId, {
        sourceNodeId: upstreamNodeId,
        sourceOutputId: outputId,
        expression: `{{${upstreamNodeId}.${outputId}}}`,
      });
    }
    setSelectedInput(null);
  };

  const handleUnmap = (inputId) => {
    if (onMapInput) {
      onMapInput(inputId, null);
    }
  };

  // Check if an output is compatible with an input
  const isCompatible = (outputType, inputType) => {
    return areTypesCompatible(outputType, inputType);
  };

  if (upstreamNodes.length === 0) {
    return (
      <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
        <div className="flex items-center gap-2 text-gray-500 text-sm">
          <Info className="w-4 h-4" />
          <span>Connect nodes to see available data</span>
        </div>
        <p className="text-xs text-gray-400 mt-2">
          Data from upstream nodes will appear here when you connect them.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Current Node Inputs */}
      {dataInputs.length > 0 && (
        <div className="bg-blue-50 rounded-lg border border-blue-200 p-3">
          <h4 className="text-sm font-medium text-blue-800 mb-2 flex items-center gap-2">
            <Zap className="w-4 h-4" />
            Data Inputs
          </h4>
          <div className="space-y-2">
            {dataInputs.map(input => {
              const mapping = mappedInputs[input.id];
              const typeInfo = getTypeInfo(input.type);
              
              return (
                <div
                  key={input.id}
                  className={cn(
                    'flex items-center justify-between p-2 rounded-md text-sm',
                    mapping ? 'bg-green-100 border border-green-300' : 'bg-white border border-gray-200',
                    selectedInput === input.id && 'ring-2 ring-blue-500'
                  )}
                >
                  <div className="flex items-center gap-2">
                    <span 
                      className="w-5 h-5 flex items-center justify-center rounded text-xs"
                      style={{ backgroundColor: `${typeInfo.color}20`, color: typeInfo.color }}
                      title={typeInfo.name}
                    >
                      {typeInfo.icon}
                    </span>
                    <div>
                      <div className="font-medium text-gray-900">{input.label}</div>
                      {input.description && (
                        <div className="text-xs text-gray-500">{input.description}</div>
                      )}
                    </div>
                  </div>
                  
                  {mapping ? (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-green-700 bg-green-200 px-2 py-0.5 rounded">
                        {mapping.expression}
                      </span>
                      <button
                        onClick={() => handleUnmap(input.id)}
                        className="p-1 text-red-500 hover:bg-red-100 rounded"
                        title="Remove mapping"
                      >
                        <Unlink className="w-3 h-3" />
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setSelectedInput(selectedInput === input.id ? null : input.id)}
                      className={cn(
                        'px-2 py-1 text-xs rounded transition-colors',
                        selectedInput === input.id
                          ? 'bg-blue-500 text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      )}
                    >
                      {selectedInput === input.id ? 'Cancel' : 'Map'}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Upstream Nodes */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
          <Link2 className="w-4 h-4" />
          Available Data from Upstream Nodes
        </h4>
        
        <div className="space-y-2">
          {upstreamNodes.map(({ node, nodeDef, outputs, label }) => {
            const isExpanded = expandedNodes[node.id] !== false;
            const dataOutputs = outputs.filter(o => o.type !== 'trigger');
            
            if (dataOutputs.length === 0) return null;
            
            return (
              <div 
                key={node.id}
                className="bg-white rounded-lg border border-gray-200 overflow-hidden"
              >
                {/* Node Header */}
                <button
                  onClick={() => toggleNode(node.id)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-900 hover:bg-gray-50 transition-colors"
                >
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-gray-400" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-gray-400" />
                  )}
                  <span 
                    className="w-6 h-6 flex items-center justify-center rounded text-sm"
                    style={{ backgroundColor: nodeDef?.color || '#6366F1' }}
                  >
                    {nodeDef?.icon || '📦'}
                  </span>
                  <span className="flex-1 text-left truncate">{label}</span>
                  <span className="text-xs text-gray-400">
                    {dataOutputs.length} output{dataOutputs.length !== 1 ? 's' : ''}
                  </span>
                </button>
                
                {/* Node Outputs */}
                {isExpanded && (
                  <div className="px-3 pb-2 space-y-1">
                    {dataOutputs.map(output => {
                      const typeInfo = getTypeInfo(output.type);
                      const selectedInputDef = selectedInput 
                        ? dataInputs.find(i => i.id === selectedInput)
                        : null;
                      const compatible = selectedInputDef 
                        ? isCompatible(output.type, selectedInputDef.type)
                        : true;
                      
                      return (
                        <div
                          key={output.id}
                          className={cn(
                            'flex items-center justify-between p-2 rounded-md text-sm',
                            selectedInput && !compatible && 'opacity-40',
                            selectedInput && compatible && 'bg-blue-50 border border-blue-200 cursor-pointer hover:bg-blue-100',
                            !selectedInput && 'bg-gray-50'
                          )}
                          onClick={() => {
                            if (selectedInput && compatible) {
                              handleMapOutput(node.id, output.id, selectedInput);
                            }
                          }}
                        >
                          <div className="flex items-center gap-2">
                            <span 
                              className="w-5 h-5 flex items-center justify-center rounded text-xs"
                              style={{ backgroundColor: `${typeInfo.color}20`, color: typeInfo.color }}
                              title={typeInfo.name}
                            >
                              {typeInfo.icon}
                            </span>
                            <div>
                              <div className="font-medium text-gray-800">{output.label}</div>
                              {output.description && (
                                <div className="text-xs text-gray-500">{output.description}</div>
                              )}
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-400 font-mono">
                              {`{{${node.id}.${output.id}}}`}
                            </span>
                            {selectedInput && compatible && (
                              <span className="text-xs text-blue-600">Click to map</span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                    
                    {/* Schema preview for object outputs */}
                    {dataOutputs.filter(o => o.schema).map(output => (
                      <div key={`${output.id}-schema`} className="ml-7 mt-1">
                        <details className="text-xs">
                          <summary className="text-gray-500 cursor-pointer hover:text-gray-700">
                            View {output.label} schema
                          </summary>
                          <div className="mt-1 p-2 bg-gray-100 rounded text-gray-600 font-mono">
                            {Object.entries(output.schema).map(([key, val]) => (
                              <div key={key} className="flex gap-2">
                                <span className="text-purple-600">{key}:</span>
                                <span className="text-gray-500">{val.type || val}</span>
                              </div>
                            ))}
                          </div>
                        </details>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Expression Help */}
      <div className="bg-amber-50 rounded-lg border border-amber-200 p-3">
        <h4 className="text-sm font-medium text-amber-800 mb-1">Expression Syntax</h4>
        <div className="text-xs text-amber-700 space-y-1">
          <p><code className="bg-amber-100 px-1 rounded">{`{{nodeId.outputId}}`}</code> - Reference an output</p>
          <p><code className="bg-amber-100 px-1 rounded">{`{{nodeId.results[0].field}}`}</code> - Access array/object</p>
          <p><code className="bg-amber-100 px-1 rounded">{`{{$input}}`}</code> - All data from trigger connection</p>
        </div>
      </div>
    </div>
  );
};

export default DataMappingPanel;
