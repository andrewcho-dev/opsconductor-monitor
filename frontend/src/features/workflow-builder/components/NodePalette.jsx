/**
 * NodePalette Component
 * 
 * Sidebar showing available nodes organized by category.
 * Nodes can be dragged onto the canvas.
 */

import React, { useState, useMemo } from 'react';
import { ChevronDown, ChevronRight, Search, Package } from 'lucide-react';
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
  const [showPackageFilter, setShowPackageFilter] = useState(false);

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

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b border-gray-200">
        <h2 className="font-semibold text-gray-900 mb-2">Nodes</h2>
        
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Package Filter Toggle */}
        <button
          onClick={() => setShowPackageFilter(!showPackageFilter)}
          className="mt-2 flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
        >
          <Package className="w-3 h-3" />
          Filter by package
          {showPackageFilter ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        </button>

        {/* Package Filter */}
        {showPackageFilter && (
          <div className="mt-2 p-2 bg-gray-50 rounded-md text-xs space-y-1 max-h-32 overflow-y-auto">
            {packages.map(pkg => (
              <label key={pkg.id} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enabledIds?.includes(pkg.id) ?? true}
                  onChange={() => {/* TODO: Toggle package */}}
                  className="rounded text-blue-500"
                  disabled={pkg.isCore}
                />
                <span className={cn(pkg.isCore && 'text-gray-400')}>
                  {pkg.icon} {pkg.name}
                </span>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Node Categories */}
      <div className="flex-1 overflow-y-auto p-2">
        {Object.entries(filteredCategories).map(([categoryId, category]) => (
          <div key={categoryId} className="mb-2">
            {/* Category Header */}
            <button
              onClick={() => toggleCategory(categoryId)}
              className="w-full flex items-center gap-2 px-2 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-md"
            >
              {expandedCategories[categoryId] ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
              <span>{category.icon}</span>
              <span>{category.name}</span>
              <span className="ml-auto text-xs text-gray-400">
                {category.nodes.length}
              </span>
            </button>

            {/* Category Nodes */}
            {expandedCategories[categoryId] && (
              <div className="ml-2 mt-1 space-y-1">
                {category.nodes.map(node => (
                  <div
                    key={node.id}
                    draggable
                    onDragStart={(e) => handleDragStart(e, node)}
                    className={cn(
                      'flex items-center gap-2 px-2 py-1.5 rounded-md cursor-grab',
                      'bg-gray-50 hover:bg-gray-100 border border-transparent hover:border-gray-200',
                      'transition-colors duration-150',
                      'active:cursor-grabbing active:bg-gray-200'
                    )}
                    title={node.description}
                  >
                    <span 
                      className="w-6 h-6 flex items-center justify-center rounded text-sm"
                      style={{ backgroundColor: `${node.color}20` }}
                    >
                      {node.icon}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-gray-900 truncate">
                        {node.name}
                      </div>
                      {node.packageName && node.packageName !== 'Core' && (
                        <div className="text-[10px] text-gray-400 truncate">
                          {node.packageName}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {Object.keys(filteredCategories).length === 0 && (
          <div className="text-center text-gray-400 text-sm py-8">
            No nodes found
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-2 border-t border-gray-200 text-xs text-gray-400 text-center">
        Drag nodes onto canvas
      </div>
    </div>
  );
};

export default NodePalette;
