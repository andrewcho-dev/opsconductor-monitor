/**
 * ExpressionInput Component
 * 
 * A text input with autocomplete for workflow expressions.
 * Supports {{nodeId.outputId}} syntax with dropdown suggestions.
 */

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Code, ChevronDown, X } from 'lucide-react';
import { getNodeDefinition } from '../packages';
import { getTypeInfo } from '../dataTypes';
import { cn } from '../../../lib/utils';

const ExpressionInput = ({
  value,
  onChange,
  placeholder,
  currentNodeId,
  allNodes = [],
  edges = [],
  className,
  multiline = false,
  disabled = false,
}) => {
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [cursorPosition, setCursorPosition] = useState(0);
  const [filter, setFilter] = useState('');
  const inputRef = useRef(null);
  const suggestionsRef = useRef(null);

  // Find upstream nodes (nodes that connect TO current node)
  const upstreamData = useMemo(() => {
    if (!currentNodeId || !edges || !allNodes) return [];
    
    const incomingEdges = edges.filter(e => e.target === currentNodeId);
    const upstreamNodeIds = [...new Set(incomingEdges.map(e => e.source))];
    
    const data = [];
    
    upstreamNodeIds.forEach(nodeId => {
      const node = allNodes.find(n => n.id === nodeId);
      if (!node) return;
      
      const nodeDef = getNodeDefinition(node.data?.nodeType);
      const outputs = nodeDef?.outputs || [];
      const label = node.data?.label || nodeDef?.name || node.data?.nodeType;
      
      // Add each output as a suggestion
      outputs.forEach(output => {
        if (output.type === 'trigger') return; // Skip trigger outputs
        
        const typeInfo = getTypeInfo(output.type);
        data.push({
          nodeId,
          nodeLabel: label,
          nodeIcon: nodeDef?.icon || '📦',
          nodeColor: nodeDef?.color || '#6366F1',
          outputId: output.id,
          outputLabel: output.label,
          outputType: output.type,
          typeInfo,
          expression: `{{${nodeId}.${output.id}}}`,
          schema: output.schema,
        });
      });
    });
    
    // Also add special variables
    data.push({
      nodeId: '$input',
      nodeLabel: 'Input Data',
      nodeIcon: '📥',
      nodeColor: '#10B981',
      outputId: '',
      outputLabel: 'All input data from trigger',
      outputType: 'any',
      typeInfo: getTypeInfo('any'),
      expression: '{{$input}}',
    });
    
    data.push({
      nodeId: '$env',
      nodeLabel: 'Environment',
      nodeIcon: '🌍',
      nodeColor: '#6366F1',
      outputId: '',
      outputLabel: 'Environment variables',
      outputType: 'object',
      typeInfo: getTypeInfo('object'),
      expression: '{{$env.VARIABLE_NAME}}',
    });
    
    return data;
  }, [currentNodeId, edges, allNodes]);

  // Filter suggestions based on current input
  const filteredSuggestions = useMemo(() => {
    if (!filter) return upstreamData;
    
    const lowerFilter = filter.toLowerCase();
    return upstreamData.filter(item => 
      item.nodeLabel.toLowerCase().includes(lowerFilter) ||
      item.outputLabel.toLowerCase().includes(lowerFilter) ||
      item.outputId.toLowerCase().includes(lowerFilter) ||
      item.expression.toLowerCase().includes(lowerFilter)
    );
  }, [upstreamData, filter]);

  // Check if cursor is inside an expression
  const isInsideExpression = useMemo(() => {
    if (!value) return false;
    
    // Find {{ before cursor
    const beforeCursor = value.substring(0, cursorPosition);
    const lastOpen = beforeCursor.lastIndexOf('{{');
    const lastClose = beforeCursor.lastIndexOf('}}');
    
    return lastOpen > lastClose;
  }, [value, cursorPosition]);

  // Get the partial expression being typed
  const partialExpression = useMemo(() => {
    if (!isInsideExpression || !value) return '';
    
    const beforeCursor = value.substring(0, cursorPosition);
    const lastOpen = beforeCursor.lastIndexOf('{{');
    return beforeCursor.substring(lastOpen + 2);
  }, [value, cursorPosition, isInsideExpression]);

  useEffect(() => {
    if (isInsideExpression) {
      setFilter(partialExpression);
      setShowSuggestions(true);
    }
  }, [isInsideExpression, partialExpression]);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (
        suggestionsRef.current && 
        !suggestionsRef.current.contains(e.target) &&
        inputRef.current &&
        !inputRef.current.contains(e.target)
      ) {
        setShowSuggestions(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleInputChange = (e) => {
    const newValue = e.target.value;
    onChange(newValue);
    setCursorPosition(e.target.selectionStart);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      setShowSuggestions(false);
    }
    
    // Trigger suggestions on {{ 
    if (e.key === '{' && value && value[cursorPosition - 1] === '{') {
      setShowSuggestions(true);
      setFilter('');
    }
  };

  const handleSelect = (item) => {
    let newValue = value || '';
    
    if (isInsideExpression) {
      // Replace the partial expression
      const beforeCursor = newValue.substring(0, cursorPosition);
      const afterCursor = newValue.substring(cursorPosition);
      const lastOpen = beforeCursor.lastIndexOf('{{');
      
      // Find the closing }} if it exists
      const closingIndex = afterCursor.indexOf('}}');
      const afterExpression = closingIndex >= 0 
        ? afterCursor.substring(closingIndex + 2) 
        : afterCursor;
      
      newValue = beforeCursor.substring(0, lastOpen) + item.expression + afterExpression;
    } else {
      // Insert at cursor position
      const before = newValue.substring(0, cursorPosition);
      const after = newValue.substring(cursorPosition);
      newValue = before + item.expression + after;
    }
    
    onChange(newValue);
    setShowSuggestions(false);
    inputRef.current?.focus();
  };

  const handleFocus = () => {
    if (upstreamData.length > 0 && !value) {
      // Show suggestions on focus if empty
      setShowSuggestions(true);
    }
  };

  const insertExpression = () => {
    const newValue = (value || '') + '{{}}';
    onChange(newValue);
    setShowSuggestions(true);
    setFilter('');
    
    // Set cursor inside the braces
    setTimeout(() => {
      if (inputRef.current) {
        const pos = newValue.length - 2;
        inputRef.current.setSelectionRange(pos, pos);
        inputRef.current.focus();
        setCursorPosition(pos);
      }
    }, 0);
  };

  const InputComponent = multiline ? 'textarea' : 'input';

  return (
    <div className="relative">
      <div className="relative">
        <InputComponent
          ref={inputRef}
          type="text"
          value={value || ''}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={handleFocus}
          onClick={(e) => setCursorPosition(e.target.selectionStart)}
          placeholder={placeholder}
          disabled={disabled}
          className={cn(
            'w-full px-3 py-2 pr-10 bg-white border border-gray-200 rounded-lg text-sm',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'font-mono',
            multiline && 'min-h-[80px] resize-y',
            disabled && 'bg-gray-100 cursor-not-allowed',
            className
          )}
          rows={multiline ? 3 : undefined}
        />
        
        {/* Expression button */}
        <button
          type="button"
          onClick={insertExpression}
          disabled={disabled}
          className={cn(
            'absolute right-2 top-2 p-1 rounded text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors',
            disabled && 'opacity-50 cursor-not-allowed'
          )}
          title="Insert expression"
        >
          <Code className="w-4 h-4" />
        </button>
      </div>

      {/* Suggestions dropdown */}
      {showSuggestions && filteredSuggestions.length > 0 && (
        <div 
          ref={suggestionsRef}
          className="absolute z-50 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-64 overflow-y-auto"
        >
          <div className="p-2 border-b border-gray-100 bg-gray-50">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-500">Available Data</span>
              <button
                onClick={() => setShowSuggestions(false)}
                className="p-0.5 text-gray-400 hover:text-gray-600"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          </div>
          
          <div className="py-1">
            {filteredSuggestions.map((item, index) => (
              <button
                key={`${item.nodeId}-${item.outputId}-${index}`}
                onClick={() => handleSelect(item)}
                className="w-full px-3 py-2 text-left hover:bg-blue-50 flex items-start gap-2 transition-colors"
              >
                <span 
                  className="w-6 h-6 flex items-center justify-center rounded text-sm flex-shrink-0"
                  style={{ backgroundColor: item.nodeColor }}
                >
                  {item.nodeIcon}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900 truncate">
                      {item.nodeLabel}
                    </span>
                    {item.outputId && (
                      <>
                        <ChevronDown className="w-3 h-3 text-gray-400 rotate-[-90deg]" />
                        <span className="text-sm text-gray-600">{item.outputLabel}</span>
                      </>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <code className="text-xs text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded font-mono">
                      {item.expression}
                    </code>
                    <span 
                      className="text-xs px-1.5 py-0.5 rounded"
                      style={{ 
                        backgroundColor: `${item.typeInfo.color}15`,
                        color: item.typeInfo.color,
                      }}
                    >
                      {item.typeInfo.name}
                    </span>
                  </div>
                </div>
              </button>
            ))}
          </div>
          
          {/* Schema preview for object types */}
          {filteredSuggestions.some(s => s.schema) && (
            <div className="p-2 border-t border-gray-100 bg-gray-50">
              <details className="text-xs">
                <summary className="text-gray-500 cursor-pointer hover:text-gray-700">
                  View object schemas
                </summary>
                <div className="mt-2 space-y-2">
                  {filteredSuggestions.filter(s => s.schema).map((item, idx) => (
                    <div key={idx} className="p-2 bg-white rounded border border-gray-200">
                      <div className="font-medium text-gray-700 mb-1">
                        {item.nodeLabel}.{item.outputId}
                      </div>
                      <div className="font-mono text-gray-600 space-y-0.5">
                        {Object.entries(item.schema).map(([key, val]) => (
                          <div key={key}>
                            <span className="text-purple-600">{key}</span>
                            <span className="text-gray-400">: </span>
                            <span className="text-gray-500">{val.type || val}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </details>
            </div>
          )}
        </div>
      )}

      {/* Expression hint */}
      {!showSuggestions && upstreamData.length > 0 && !value && (
        <div className="mt-1 text-xs text-gray-400">
          Type <code className="bg-gray-100 px-1 rounded">{'{{'}</code> for suggestions
        </div>
      )}
    </div>
  );
};

export default ExpressionInput;
