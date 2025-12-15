/**
 * NodePalette Component
 * 
 * n8n/Node-RED style sidebar showing available nodes.
 * Features search, categories, and drag-to-canvas.
 */

import React, { useState, useMemo } from 'react';
import { ChevronDown, ChevronRight, Search, X } from 'lucide-react';
import { getNodesByCategory, getAllPackages } from '../packages';
import { cn } from '../../../lib/utils';

const NodePalette = ({ enabledPackages, onDragStart }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedCategories, setExpandedCategories] = useState({
    triggers: true,
    discovery: true,
    query: true,
    configure: true,
    data: true,
    logic: true,
    notify: true,
  });

  const enabledIds = useMemo(() => {
    if (Array.isArray(enabledPackages) && enabledPackages.length > 0) {
      return enabledPackages;
    }
    return undefined;
  }, [enabledPackages]);

  // Get nodes organized by category
  const nodesByCategory = useMemo(() => {
    const byEnabled = getNodesByCategory(enabledIds);
    if (byEnabled && Object.keys(byEnabled).length > 0) {
      return byEnabled;
    }
    return getNodesByCategory(undefined);
  }, [enabledIds]);

  // Filter nodes by search term
  const filteredCategories = useMemo(() => {
    if (!searchTerm.trim()) return nodesByCategory;

    const term = searchTerm.toLowerCase();
    const filtered = {};

    for (const [catId, category] of Object.entries(nodesByCategory)) {
      const matchingNodes = category.nodes.filter(node =>
        node.name.toLowerCase().includes(term) ||
        node.description?.toLowerCase().includes(term) ||
        node.packageName?.toLowerCase().includes(term)
      );

      if (matchingNodes.length > 0) {
        filtered[catId] = {
          ...category,
          nodes: matchingNodes,
        };
      }
    }

    return filtered;
  }, [nodesByCategory, searchTerm]);

  const toggleCategory = (categoryId) => {
    setExpandedCategories(prev => ({
      ...prev,
      [categoryId]: !prev[categoryId],
    }));
  };

  const handleDragStart = (event, node) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify({
      nodeType: node.id,
      name: node.name,
    }));
    event.dataTransfer.effectAllowed = 'move';
    
    if (onDragStart) {
      onDragStart(node);
    }
  };

  const packages = getAllPackages();

  // n8n-style palette
  return (
    <div className="w-72 bg-gray-50 border-r border-gray-200 flex flex-col h-full">
      {/* Header with search - n8n style */}
      <div className="p-4 bg-white border-b border-gray-200">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-8 py-2.5 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent focus:bg-white transition-colors"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Node Categories - n8n style */}
      <div className="flex-1 overflow-y-auto">
        {Object.entries(filteredCategories).map(([categoryId, category]) => (
          <div key={categoryId} className="border-b border-gray-200 last:border-b-0">
            {/* Category Header */}
            <button
              onClick={() => toggleCategory(categoryId)}
              className="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium text-gray-700 hover:bg-white transition-colors"
            >
              <span className="text-lg">{category.icon}</span>
              <span className="flex-1 text-left">{category.name}</span>
              <span className="text-xs text-gray-400 bg-gray-200 px-2 py-0.5 rounded-full">
                {category.nodes.length}
              </span>
              {expandedCategories[categoryId] ? (
                <ChevronDown className="w-4 h-4 text-gray-400" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-400" />
              )}
            </button>

            {/* Category Nodes - n8n style cards */}
            {expandedCategories[categoryId] && (
              <div className="px-3 pb-3 space-y-2">
                {category.nodes.map(node => (
                  <div
                    key={node.id}
                    draggable
                    onDragStart={(e) => handleDragStart(e, node)}
                    className={cn(
                      'flex items-center gap-3 p-2.5 rounded-lg cursor-grab',
                      'bg-white border border-gray-200 shadow-sm',
                      'hover:shadow-md hover:border-gray-300 hover:scale-[1.02]',
                      'transition-all duration-150',
                      'active:cursor-grabbing active:scale-100 active:shadow-lg'
                    )}
                    title={node.description}
                  >
                    {/* Node icon with color */}
                    <div 
                      className="w-9 h-9 flex items-center justify-center rounded-lg flex-shrink-0"
                      style={{ backgroundColor: node.color || '#6366F1' }}
                    >
                      <span className="text-lg">{node.icon}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900 truncate">
                        {node.name}
                      </div>
                      <div className="text-xs text-gray-500 truncate">
                        {node.description?.substring(0, 35) || node.packageName}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {Object.keys(filteredCategories).length === 0 && (
          <div className="flex flex-col items-center justify-center text-gray-400 py-12">
            <Search className="w-8 h-8 mb-2 opacity-50" />
            <div className="text-sm">No nodes found</div>
            <div className="text-xs mt-1">Try a different search term</div>
          </div>
        )}
      </div>

      {/* Footer hint */}
      <div className="p-3 bg-white border-t border-gray-200 text-xs text-gray-500 text-center">
        💡 Drag nodes to canvas or double-click to add
      </div>
    </div>
  );
};

export default NodePalette;
