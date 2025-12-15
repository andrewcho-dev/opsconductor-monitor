/**
 * NodePalette Component
 * 
 * n8n/Node-RED style sidebar showing available nodes.
 * Features search, collapsible package libraries, and drag-to-canvas.
 */

import React, { useState, useMemo } from 'react';
import { ChevronDown, ChevronRight, Search, X, Folder, FolderOpen, AlertTriangle, Key, Wifi, Server, Terminal } from 'lucide-react';
import { getNodesByCategory, getAllPackages, getNodesByPackage } from '../packages';
import { cn } from '../../../lib/utils';

const NodePalette = ({ enabledPackages, onDragStart }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [viewMode, setViewMode] = useState('packages'); // 'packages' or 'categories'
  const [expandedPackages, setExpandedPackages] = useState({});
  const [expandedSubgroups, setExpandedSubgroups] = useState({});

  const enabledIds = useMemo(() => {
    if (Array.isArray(enabledPackages) && enabledPackages.length > 0) {
      return enabledPackages;
    }
    return undefined;
  }, [enabledPackages]);

  // Get all packages
  const packages = getAllPackages();

  // Get nodes organized by package with subgroups
  const nodesByPackage = useMemo(() => {
    const result = {};
    
    packages.forEach(pkg => {
      if (enabledIds && !enabledIds.includes(pkg.id)) return;
      
      const pkgNodes = getNodesByPackage(pkg.id);
      if (!pkgNodes || pkgNodes.length === 0) return;
      
      // Group nodes by their category within the package
      const subgroups = {};
      pkgNodes.forEach(node => {
        const category = node.category || 'other';
        if (!subgroups[category]) {
          subgroups[category] = {
            name: getCategoryName(category),
            icon: getCategoryIcon(category),
            nodes: [],
          };
        }
        subgroups[category].nodes.push(node);
      });
      
      result[pkg.id] = {
        ...pkg,
        subgroups,
        totalNodes: pkgNodes.length,
      };
    });
    
    return result;
  }, [packages, enabledIds]);

  // Filter nodes by search term
  const filteredPackages = useMemo(() => {
    if (!searchTerm.trim()) return nodesByPackage;

    const term = searchTerm.toLowerCase();
    const filtered = {};

    for (const [pkgId, pkg] of Object.entries(nodesByPackage)) {
      const filteredSubgroups = {};
      let totalMatches = 0;
      
      for (const [subId, subgroup] of Object.entries(pkg.subgroups)) {
        const matchingNodes = subgroup.nodes.filter(node =>
          node.name.toLowerCase().includes(term) ||
          node.description?.toLowerCase().includes(term)
        );
        
        if (matchingNodes.length > 0) {
          filteredSubgroups[subId] = {
            ...subgroup,
            nodes: matchingNodes,
          };
          totalMatches += matchingNodes.length;
        }
      }
      
      if (totalMatches > 0) {
        filtered[pkgId] = {
          ...pkg,
          subgroups: filteredSubgroups,
          totalNodes: totalMatches,
        };
      }
    }

    return filtered;
  }, [nodesByPackage, searchTerm]);

  // Helper functions for category display
  function getCategoryName(category) {
    const names = {
      triggers: 'Triggers',
      discovery: 'Discovery',
      query: 'Query / Show',
      configure: 'Configure',
      data: 'Data',
      logic: 'Logic',
      notify: 'Notifications',
      other: 'Other',
    };
    return names[category] || category.charAt(0).toUpperCase() + category.slice(1);
  }

  function getCategoryIcon(category) {
    const icons = {
      triggers: '⚡',
      discovery: '🔍',
      query: '📋',
      configure: '⚙️',
      data: '💾',
      logic: '🔀',
      notify: '🔔',
      other: '📦',
    };
    return icons[category] || '📦';
  }

  // Get platform badge info
  function getPlatformBadge(platform) {
    const badges = {
      'any': null, // No badge needed for universal nodes
      'linux': { label: 'Linux', color: 'bg-orange-100 text-orange-700 border-orange-200' },
      'ciena-saos-8': { label: 'SAOS', color: 'bg-blue-100 text-blue-700 border-blue-200' },
      'windows': { label: 'Win', color: 'bg-cyan-100 text-cyan-700 border-cyan-200' },
    };
    return badges[platform] || (platform && platform !== 'any' ? { label: platform, color: 'bg-gray-100 text-gray-700 border-gray-200' } : null);
  }

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

  const togglePackage = (pkgId) => {
    setExpandedPackages(prev => ({
      ...prev,
      [pkgId]: !prev[pkgId],
    }));
  };

  const toggleSubgroup = (pkgId, subId) => {
    const key = `${pkgId}:${subId}`;
    setExpandedSubgroups(prev => ({
      ...prev,
      [key]: !prev[key],
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
    const platform = execution.platform;
    const context = execution.context;
    const platformBadge = getPlatformBadge(platform);
    const needsCredentials = hasCredentialRequirements(node);
    const contextIcon = getContextIcon(context);
    
    // Build tooltip with requirements info
    let tooltip = node.description || '';
    if (execution.requirements) {
      const reqs = [];
      if (execution.requirements.credentials) {
        reqs.push(`Credentials: ${execution.requirements.credentials.join(', ')}`);
      }
      if (execution.requirements.tools) {
        reqs.push(`Tools: ${execution.requirements.tools.join(', ')}`);
      }
      if (execution.requirements.network) {
        reqs.push('Requires network access');
      }
      if (execution.requirements.database) {
        reqs.push('Requires database connection');
      }
      if (reqs.length > 0) {
        tooltip += `\n\nRequirements:\n• ${reqs.join('\n• ')}`;
      }
    }
    if (platform && platform !== 'any') {
      tooltip += `\n\nPlatform: ${platform}`;
    }
    if (context) {
      tooltip += `\nContext: ${context}`;
    }
    
    return (
      <div
        key={node.id}
        draggable
        onDragStart={(e) => handleDragStart(e, node)}
        className={cn(
          'flex items-center gap-2 p-2 rounded-lg cursor-grab',
          'bg-white border border-gray-200 shadow-sm',
          'hover:shadow-md hover:border-gray-300 hover:scale-[1.01]',
          'transition-all duration-150',
          'active:cursor-grabbing active:scale-100 active:shadow-lg'
        )}
        title={tooltip}
      >
        <div 
          className="w-8 h-8 flex items-center justify-center rounded-md flex-shrink-0"
          style={{ backgroundColor: node.color || '#6366F1' }}
        >
          <span className="text-base">{node.icon}</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-900 truncate">
            {node.name}
          </div>
          {/* Platform and requirements badges */}
          <div className="flex items-center gap-1 mt-0.5">
            {platformBadge && (
              <span className={cn(
                'text-[10px] px-1 py-0 rounded border font-medium',
                platformBadge.color
              )}>
                {platformBadge.label}
              </span>
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

  return (
    <div className="w-72 bg-gray-50 border-r border-gray-200 flex flex-col h-full">
      {/* Header with search */}
      <div className="p-3 bg-white border-b border-gray-200">
        <div className="relative">
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
      </div>

      {/* Package Libraries - Folder Structure */}
      <div className="flex-1 overflow-y-auto">
        {Object.entries(filteredPackages).map(([pkgId, pkg]) => (
          <div key={pkgId} className="border-b border-gray-200 last:border-b-0">
            {/* Package Header (Top-level folder) */}
            <button
              onClick={() => togglePackage(pkgId)}
              className={cn(
                "w-full flex items-center gap-2 px-3 py-2.5 text-sm font-medium transition-colors",
                expandedPackages[pkgId] 
                  ? "bg-white text-gray-900 border-l-2 border-l-blue-500" 
                  : "text-gray-700 hover:bg-white"
              )}
            >
              {expandedPackages[pkgId] ? (
                <FolderOpen className="w-4 h-4 text-blue-500" />
              ) : (
                <Folder className="w-4 h-4 text-gray-400" />
              )}
              <span className="text-base">{pkg.icon}</span>
              <span className="flex-1 text-left truncate">{pkg.name}</span>
              <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                {pkg.totalNodes}
              </span>
              {expandedPackages[pkgId] ? (
                <ChevronDown className="w-4 h-4 text-gray-400" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-400" />
              )}
            </button>

            {/* Package Contents */}
            {expandedPackages[pkgId] && (
              <div className="bg-gray-50/50">
                {Object.entries(pkg.subgroups).map(([subId, subgroup]) => {
                  const subKey = `${pkgId}:${subId}`;
                  const isSubExpanded = expandedSubgroups[subKey] !== false; // Default open
                  
                  return (
                    <div key={subId}>
                      {/* Subgroup Header (Sub-folder) */}
                      <button
                        onClick={() => toggleSubgroup(pkgId, subId)}
                        className="w-full flex items-center gap-2 pl-8 pr-3 py-2 text-xs font-medium text-gray-600 hover:bg-white transition-colors"
                      >
                        {isSubExpanded ? (
                          <ChevronDown className="w-3 h-3 text-gray-400" />
                        ) : (
                          <ChevronRight className="w-3 h-3 text-gray-400" />
                        )}
                        <span>{subgroup.icon}</span>
                        <span className="flex-1 text-left">{subgroup.name}</span>
                        <span className="text-xs text-gray-400">
                          {subgroup.nodes.length}
                        </span>
                      </button>

                      {/* Subgroup Nodes */}
                      {isSubExpanded && (
                        <div className="pl-10 pr-2 pb-2 space-y-1">
                          {subgroup.nodes.map(renderNodeCard)}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}

        {Object.keys(filteredPackages).length === 0 && (
          <div className="flex flex-col items-center justify-center text-gray-400 py-12">
            <Search className="w-8 h-8 mb-2 opacity-50" />
            <div className="text-sm">No nodes found</div>
            <div className="text-xs mt-1">Try a different search term</div>
          </div>
        )}
      </div>

      {/* Footer hint */}
      <div className="p-2 bg-white border-t border-gray-200 text-xs text-gray-500 text-center">
        📁 Click folders to expand • Drag nodes to canvas
      </div>
    </div>
  );
};

export default NodePalette;
