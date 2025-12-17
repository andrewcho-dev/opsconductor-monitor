/**
 * NodePalette Component
 * 
 * Action-based node organization for intuitive workflow building.
 * Nodes are grouped by what they DO (Triggers, Discover, Configure, etc.)
 * with platform badges showing compatibility.
 */

import React, { useState, useMemo } from 'react';
import { ChevronDown, ChevronRight, Search, X, Key, Terminal, Wifi, Server, Layers, LayoutGrid } from 'lucide-react';
import { getAllPackages, getNodesByPackage } from '../packages';
import { CATEGORIES, getSortedCategories } from '../packages/categories';
import { PLATFORMS, PLATFORM_INFO, getPlatformInfo } from '../platforms';
import { cn } from '../../../lib/utils';
import { PlatformIndicator } from './PlatformBadge';

// Platform filter options - commonly used platforms for filtering
const FILTER_PLATFORMS = [
  { id: 'any', name: 'Universal', icon: '⚡', color: '#10B981' },
  { id: 'linux', name: 'Linux', icon: '🐧', color: '#FCC624' },
  { id: 'windows', name: 'Windows', icon: '🪟', color: '#00A4EF' },
  { id: 'network-device', name: 'Network', icon: '🌐', color: '#6366F1' },
  { id: 'ciena-saos', name: 'Ciena SAOS', icon: '📡', color: '#0EA5E9' },
  { id: 'cisco-ios', name: 'Cisco', icon: '🔷', color: '#1BA0D7' },
  { id: 'axis-camera', name: 'Axis Camera', icon: '📷', color: '#FFB800' },
];

const NodePalette = ({ enabledPackages, onDragStart }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [viewMode, setViewMode] = useState('categories'); // 'categories' or 'packages'
  const [expandedCategories, setExpandedCategories] = useState({ triggers: true }); // Start with triggers open
  const [expandedSubcategories, setExpandedSubcategories] = useState({});
  const [selectedPlatforms, setSelectedPlatforms] = useState([]); // Multi-select platform filter

  // Get all enabled packages
  const enabledIds = useMemo(() => {
    if (Array.isArray(enabledPackages) && enabledPackages.length > 0) {
      return enabledPackages;
    }
    return undefined;
  }, [enabledPackages]);

  // Get all nodes from all enabled packages
  const allNodes = useMemo(() => {
    const packages = getAllPackages();
    const nodes = [];
    
    packages.forEach(pkg => {
      if (enabledIds && !enabledIds.includes(pkg.id)) return;
      
      const pkgNodes = getNodesByPackage(pkg.id);
      nodes.push(...pkgNodes);
    });
    
    return nodes;
  }, [enabledIds]);

  // Organize nodes by action category
  const nodesByCategory = useMemo(() => {
    const categories = {};
    const sortedCats = getSortedCategories();
    
    // Initialize all categories
    sortedCats.forEach(cat => {
      categories[cat.id] = {
        ...cat,
        subcategories: {},
        nodes: [],
        totalNodes: 0,
      };
      
      // Initialize subcategories if defined
      if (cat.subcategories) {
        Object.entries(cat.subcategories).forEach(([subId, sub]) => {
          categories[cat.id].subcategories[subId] = {
            ...sub,
            id: subId,
            nodes: [],
          };
        });
      }
    });
    
    // Sort nodes into categories
    allNodes.forEach(node => {
      const catId = node.category || 'logic';
      const subCatId = node.subcategory;
      
      if (!categories[catId]) {
        // Unknown category - put in logic
        categories.logic.nodes.push(node);
        categories.logic.totalNodes++;
        return;
      }
      
      // If node has subcategory and it exists, add there
      if (subCatId && categories[catId].subcategories[subCatId]) {
        categories[catId].subcategories[subCatId].nodes.push(node);
      } else {
        // Add to main category nodes
        categories[catId].nodes.push(node);
      }
      categories[catId].totalNodes++;
    });
    
    return categories;
  }, [allNodes]);

  // Check if node matches platform filter
  const nodeMatchesPlatformFilter = (node) => {
    if (selectedPlatforms.length === 0) return true;
    
    const nodePlatforms = node.platforms || [];
    
    // If node supports 'any' platform, it matches all filters
    if (nodePlatforms.includes('any') || nodePlatforms.includes(PLATFORMS.ANY)) {
      return true;
    }
    
    // Check if any of the node's platforms match any selected filter
    return selectedPlatforms.some(filterPlatform => {
      // Direct match
      if (nodePlatforms.includes(filterPlatform)) return true;
      
      // Network device matches any network vendor
      if (filterPlatform === 'network-device') {
        return nodePlatforms.some(p => 
          p.includes('cisco') || p.includes('juniper') || p.includes('arista') ||
          p.includes('ciena') || p.includes('paloalto') || p.includes('fortinet') ||
          p.includes('mikrotik') || p.includes('ubiquiti') || p.includes('hpe') ||
          p.includes('dell') || p === 'network-device'
        );
      }
      
      // Cisco filter matches all Cisco variants
      if (filterPlatform === 'cisco-ios') {
        return nodePlatforms.some(p => p.includes('cisco'));
      }
      
      return false;
    });
  };

  // Filter nodes by search term and platform
  const filteredCategories = useMemo(() => {
    const hasSearchFilter = searchTerm.trim();
    const hasPlatformFilter = selectedPlatforms.length > 0;
    
    if (!hasSearchFilter && !hasPlatformFilter) return nodesByCategory;

    const term = searchTerm.toLowerCase();
    const filtered = {};

    for (const [catId, cat] of Object.entries(nodesByCategory)) {
      const matchingNodes = cat.nodes.filter(node => {
        const matchesSearch = !hasSearchFilter || 
          node.name.toLowerCase().includes(term) ||
          node.description?.toLowerCase().includes(term) ||
          node.id.toLowerCase().includes(term);
        const matchesPlatform = nodeMatchesPlatformFilter(node);
        return matchesSearch && matchesPlatform;
      });
      
      const matchingSubcats = {};
      let subMatches = 0;
      
      for (const [subId, sub] of Object.entries(cat.subcategories)) {
        const subMatchingNodes = sub.nodes.filter(node => {
          const matchesSearch = !hasSearchFilter ||
            node.name.toLowerCase().includes(term) ||
            node.description?.toLowerCase().includes(term) ||
            node.id.toLowerCase().includes(term);
          const matchesPlatform = nodeMatchesPlatformFilter(node);
          return matchesSearch && matchesPlatform;
        });
        
        if (subMatchingNodes.length > 0) {
          matchingSubcats[subId] = { ...sub, nodes: subMatchingNodes };
          subMatches += subMatchingNodes.length;
        }
      }
      
      const totalMatches = matchingNodes.length + subMatches;
      
      if (totalMatches > 0) {
        filtered[catId] = {
          ...cat,
          nodes: matchingNodes,
          subcategories: matchingSubcats,
          totalNodes: totalMatches,
        };
      }
    }

    return filtered;
  }, [nodesByCategory, searchTerm, selectedPlatforms]);

  // Toggle platform filter selection
  const togglePlatformFilter = (platformId) => {
    setSelectedPlatforms(prev => {
      if (prev.includes(platformId)) {
        return prev.filter(p => p !== platformId);
      } else {
        return [...prev, platformId];
      }
    });
  };

  // Clear all platform filters
  const clearPlatformFilters = () => {
    setSelectedPlatforms([]);
  };

  // Get context icon
  function getContextIcon(context) {
    switch (context) {
      case 'remote_ssh': return <Terminal className="w-3 h-3" />;
      case 'remote_snmp': return <Wifi className="w-3 h-3" />;
      case 'remote_api': return <Server className="w-3 h-3" />;
      case 'local': return <Server className="w-3 h-3" />;
      default: return null;
    }
  }

  // Check if node has credential requirements
  function hasCredentialRequirements(node) {
    const requirements = node.execution?.requirements;
    return requirements?.credentials && requirements.credentials.length > 0;
  }

  const toggleCategory = (catId) => {
    setExpandedCategories(prev => ({
      ...prev,
      [catId]: !prev[catId],
    }));
  };

  const toggleSubcategory = (catId, subId) => {
    const key = `${catId}:${subId}`;
    setExpandedSubcategories(prev => ({
      ...prev,
      [key]: prev[key] === undefined ? false : !prev[key],
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

  // Render a single node card
  const renderNodeCard = (node) => {
    const execution = node.execution || {};
    const platforms = node.platforms || [];
    const context = execution.context;
    const needsCredentials = hasCredentialRequirements(node);
    const contextIcon = getContextIcon(context);
    
    return (
      <div
        key={node.id}
        draggable
        onDragStart={(e) => handleDragStart(e, node)}
        className={cn(
          'flex items-center gap-2 p-2 rounded-lg cursor-grab',
          'bg-white border border-gray-200 shadow-sm',
          'hover:shadow-md hover:border-gray-300 hover:scale-[1.02]',
          'transition-all duration-150',
          'active:cursor-grabbing active:scale-100 active:shadow-lg'
        )}
        title={node.description || node.name}
      >
        <div 
          className="w-9 h-9 flex items-center justify-center rounded-lg flex-shrink-0 text-white"
          style={{ backgroundColor: node.color || '#6366F1' }}
        >
          <span className="text-lg">{node.icon}</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-900 truncate">
            {node.name}
          </div>
          <div className="flex items-center gap-1.5 mt-0.5">
            {platforms.length > 0 && (
              <PlatformIndicator platforms={platforms} />
            )}
            {contextIcon && (
              <span className="text-gray-400" title={`Runs ${context}`}>
                {contextIcon}
              </span>
            )}
            {needsCredentials && (
              <span className="text-amber-500" title="Requires credentials">
                <Key className="w-3 h-3" />
              </span>
            )}
          </div>
        </div>
      </div>
    );
  };

  // Render nodes list
  const renderNodes = (nodes) => {
    if (!nodes || nodes.length === 0) return null;
    return (
      <div className="space-y-1.5 py-2">
        {nodes.map(renderNodeCard)}
      </div>
    );
  };

  return (
    <div className="w-80 bg-gray-50 border-r border-gray-200 flex flex-col h-full">
      {/* Header */}
      <div className="p-3 bg-white border-b border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold text-gray-900 text-sm">Node Library</h3>
          <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('categories')}
              className={cn(
                'p-1.5 rounded-md transition-colors',
                viewMode === 'categories' ? 'bg-white shadow-sm text-blue-600' : 'text-gray-500 hover:text-gray-700'
              )}
              title="View by action"
            >
              <Layers className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('packages')}
              className={cn(
                'p-1.5 rounded-md transition-colors',
                viewMode === 'packages' ? 'bg-white shadow-sm text-blue-600' : 'text-gray-500 hover:text-gray-700'
              )}
              title="View by package"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
          </div>
        </div>
        
        {/* Search */}
        <div className="relative mb-2">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-8 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent focus:bg-white transition-colors"
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

        {/* Platform Filter Badges - Always visible, compact inline */}
        <div className="flex flex-wrap gap-1">
          {FILTER_PLATFORMS.map(platform => {
            const isSelected = selectedPlatforms.includes(platform.id);
            return (
              <button
                key={platform.id}
                onClick={() => togglePlatformFilter(platform.id)}
                className={cn(
                  'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium transition-all border',
                  isSelected
                    ? 'border-current shadow-sm'
                    : 'border-transparent opacity-60 hover:opacity-100'
                )}
                style={{
                  backgroundColor: isSelected ? `${platform.color}25` : `${platform.color}10`,
                  color: platform.color,
                }}
                title={`Filter: ${platform.name}`}
              >
                <span className="text-xs">{platform.icon}</span>
                <span>{platform.name}</span>
              </button>
            );
          })}
          {selectedPlatforms.length > 0 && (
            <button
              onClick={clearPlatformFilters}
              className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
              title="Clear all filters"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* Category List */}
      <div className="flex-1 overflow-y-auto">
        {Object.entries(filteredCategories).map(([catId, cat]) => {
          if (cat.totalNodes === 0) return null;
          
          const isExpanded = expandedCategories[catId] || searchTerm.trim();
          const hasSubcategories = Object.keys(cat.subcategories).length > 0;
          
          return (
            <div key={catId} className="border-b border-gray-200">
              {/* Category Header */}
              <button
                onClick={() => toggleCategory(catId)}
                className={cn(
                  'w-full flex items-center gap-3 px-3 py-3 text-sm font-semibold transition-all',
                  isExpanded 
                    ? 'bg-white text-gray-900 border-l-3' 
                    : 'text-gray-700 hover:bg-white'
                )}
                style={isExpanded ? { borderLeftColor: cat.color } : {}}
              >
                <span 
                  className="w-8 h-8 flex items-center justify-center rounded-lg text-white text-lg"
                  style={{ backgroundColor: cat.color }}
                >
                  {cat.icon}
                </span>
                <div className="flex-1 text-left">
                  <div>{cat.name}</div>
                  <div className="text-xs font-normal text-gray-500">{cat.description}</div>
                </div>
                <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded-full">
                  {cat.totalNodes}
                </span>
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-gray-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                )}
              </button>

              {/* Category Contents */}
              {isExpanded && (
                <div className="bg-gray-50/80 px-3 pb-2">
                  {/* Direct nodes (no subcategory) */}
                  {cat.nodes.length > 0 && renderNodes(cat.nodes)}
                  
                  {/* Subcategories */}
                  {hasSubcategories && Object.entries(cat.subcategories).map(([subId, sub]) => {
                    if (sub.nodes.length === 0) return null;
                    
                    const subKey = `${catId}:${subId}`;
                    const isSubExpanded = expandedSubcategories[subKey] !== false;
                    
                    return (
                      <div key={subId} className="mt-2">
                        <button
                          onClick={() => toggleSubcategory(catId, subId)}
                          className="w-full flex items-center gap-2 px-2 py-1.5 text-xs font-medium text-gray-600 hover:bg-white rounded-md transition-colors"
                        >
                          {isSubExpanded ? (
                            <ChevronDown className="w-3 h-3 text-gray-400" />
                          ) : (
                            <ChevronRight className="w-3 h-3 text-gray-400" />
                          )}
                          <span>{sub.icon}</span>
                          <span className="flex-1 text-left">{sub.name}</span>
                          <span className="text-xs text-gray-400">
                            {sub.nodes.length}
                          </span>
                        </button>
                        
                        {isSubExpanded && (
                          <div className="pl-4">
                            {renderNodes(sub.nodes)}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}

        {Object.keys(filteredCategories).length === 0 && (
          <div className="flex flex-col items-center justify-center text-gray-400 py-12">
            <Search className="w-8 h-8 mb-2 opacity-50" />
            <div className="text-sm">No nodes found</div>
            <div className="text-xs mt-1">Try a different search term</div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-2 bg-white border-t border-gray-200 text-xs text-gray-500 text-center">
        🎯 Drag nodes to canvas to build your workflow
      </div>
    </div>
  );
};

export default NodePalette;
