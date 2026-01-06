/**
 * DeviceSelectionModal
 * 
 * Reusable modal for selecting devices from NetBox.
 * Can be used anywhere device selection is needed (credentials, groups, workflows, etc.)
 * 
 * Features:
 * - Full sorting by any column (IP, name, role, platform, site, status)
 * - Column filters for role, platform, site, status
 * - Tag filtering with AND/OR logic
 * - Tags displayed on each device row
 * - Search across all fields
 * 
 * Props:
 * - isOpen: boolean - whether modal is visible
 * - onClose: () => void - called when modal is closed
 * - onSave: (selectedIps: string[]) => void - called with array of selected device IPs
 * - initialSelected: string[] - IPs that should be pre-selected
 * - title: string - modal title (default: "Select Devices")
 * - multiSelect: boolean - allow multiple selection (default: true)
 */

import React, { useState, useEffect, useMemo } from 'react';
import { 
  X, Search, RefreshCw, Check, ChevronUp, ChevronDown, 
  ChevronsUpDown, Filter, Tag
} from 'lucide-react';
import { fetchApi, cn } from '../../lib/utils';

// Helper to convert IP to number for sorting
function ipToNumber(ip) {
  if (!ip) return 0;
  const parts = ip.split('.').map(Number);
  return parts[0] * 16777216 + parts[1] * 65536 + parts[2] * 256 + parts[3];
}

export function DeviceSelectionModal({
  isOpen,
  onClose,
  onSave,
  initialSelected = [],
  title = "Select Devices",
  multiSelect = true,
}) {
  const [allDevices, setAllDevices] = useState([]);
  const [allTags, setAllTags] = useState([]);
  const [selected, setSelected] = useState(new Set(initialSelected));
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  
  // Sorting state
  const [sortConfig, setSortConfig] = useState({ key: 'ip_address', direction: 'asc' });
  
  // Filter state
  const [filters, setFilters] = useState({
    role: '',
    platform: '',
    site: '',
    status: '',
  });
  
  // Tag filter state
  const [selectedTags, setSelectedTags] = useState([]);
  const [tagLogic, setTagLogic] = useState('OR');
  const [showTagFilter, setShowTagFilter] = useState(false);

  // Load devices when modal opens
  useEffect(() => {
    if (isOpen) {
      loadDevices();
    }
  }, [isOpen]);

  // Update selected devices when initialSelected changes (handles async loading)
  useEffect(() => {
    if (isOpen) {
      setSelected(new Set(initialSelected));
    }
  }, [isOpen, JSON.stringify(initialSelected)]);

  const loadDevices = async () => {
    setLoading(true);
    try {
      const [devicesRes, tagsRes] = await Promise.all([
        fetchApi('/integrations/v1/netbox/devices?limit=1000'),
        fetchApi('/integrations/v1/netbox/tags')
      ]);
      
      const devices = (devicesRes.data || []).map(d => ({
        ip_address: d.primary_ip4?.address?.split('/')[0] || '',
        hostname: d.name,
        site: d.site?.name || '',
        role: d.role?.name || d.device_role?.name || '',
        platform: d.platform?.name || '',
        status: d.status?.value || d.status || '',
        tags: d.tags || [],
        id: d.id,
      })).filter(d => d.ip_address);
      
      setAllDevices(devices);
      setAllTags(tagsRes.data || []);
    } catch (err) {
      console.error('Error loading devices:', err);
    } finally {
      setLoading(false);
    }
  };

  // Get unique values for filter dropdowns
  const filterOptions = useMemo(() => {
    const roles = new Set();
    const platforms = new Set();
    const sites = new Set();
    const statuses = new Set();
    
    allDevices.forEach(d => {
      if (d.role) roles.add(d.role);
      if (d.platform) platforms.add(d.platform);
      if (d.site) sites.add(d.site);
      if (d.status) statuses.add(d.status);
    });
    
    return {
      roles: Array.from(roles).sort(),
      platforms: Array.from(platforms).sort(),
      sites: Array.from(sites).sort(),
      statuses: Array.from(statuses).sort(),
    };
  }, [allDevices]);

  // Filter devices
  const filteredDevices = useMemo(() => {
    let filtered = allDevices;
    
    // Filter by selected tags
    if (selectedTags.length > 0) {
      filtered = filtered.filter(d => {
        const deviceTagSlugs = (d.tags || []).map(t => t.slug);
        if (tagLogic === 'AND') {
          return selectedTags.every(tag => deviceTagSlugs.includes(tag));
        } else {
          return selectedTags.some(tag => deviceTagSlugs.includes(tag));
        }
      });
    }
    
    // Filter by search
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(d =>
        d.ip_address?.includes(term) ||
        d.hostname?.toLowerCase().includes(term) ||
        d.site?.toLowerCase().includes(term) ||
        d.role?.toLowerCase().includes(term) ||
        d.platform?.toLowerCase().includes(term) ||
        (d.tags || []).some(t => t.name?.toLowerCase().includes(term))
      );
    }
    
    // Apply column filters
    if (filters.role) {
      filtered = filtered.filter(d => d.role === filters.role);
    }
    if (filters.platform) {
      filtered = filtered.filter(d => d.platform === filters.platform);
    }
    if (filters.site) {
      filtered = filtered.filter(d => d.site === filters.site);
    }
    if (filters.status) {
      filtered = filtered.filter(d => d.status === filters.status);
    }
    
    return filtered;
  }, [allDevices, selectedTags, tagLogic, searchTerm, filters]);

  // Sort devices
  const sortedDevices = useMemo(() => {
    return [...filteredDevices].sort((a, b) => {
      // Always sort selected items first
      const aSelected = selected.has(a.ip_address);
      const bSelected = selected.has(b.ip_address);
      if (aSelected && !bSelected) return -1;
      if (!aSelected && bSelected) return 1;
      
      // Primary sort by IP address
      const aIp = ipToNumber(a.ip_address);
      const bIp = ipToNumber(b.ip_address);
      
      // If sorting by IP, use the sort direction
      if (sortConfig.key === 'ip_address') {
        if (aIp < bIp) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aIp > bIp) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      }
      
      // For other columns, sort by that column first, then by IP as secondary
      let aVal = (a[sortConfig.key] || '').toLowerCase();
      let bVal = (b[sortConfig.key] || '').toLowerCase();
      
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      
      // Secondary sort by IP address (always ascending)
      if (aIp < bIp) return -1;
      if (aIp > bIp) return 1;
      return 0;
    });
  }, [filteredDevices, selected, sortConfig]);

  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const toggleDevice = (ip) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(ip)) {
        next.delete(ip);
      } else {
        if (!multiSelect) next.clear();
        next.add(ip);
      }
      return next;
    });
  };

  const handleSelectAll = (checked) => {
    setSelected(prev => {
      const next = new Set(prev);
      sortedDevices.forEach(d => {
        if (checked) next.add(d.ip_address);
        else next.delete(d.ip_address);
      });
      return next;
    });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave([...selected]);
      onClose();
    } catch (err) {
      alert('Error saving: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = () => {
    if (selected.size !== initialSelected.length) return true;
    for (const ip of selected) {
      if (!initialSelected.includes(ip)) return true;
    }
    return false;
  };

  const clearFilters = () => {
    setFilters({ role: '', platform: '', site: '', status: '' });
    setSelectedTags([]);
    setSearchTerm('');
  };

  const hasActiveFilters = filters.role || filters.platform || filters.site || filters.status || selectedTags.length > 0;

  // Sort icon component
  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) {
      return <ChevronsUpDown className="w-3 h-3 text-gray-400" />;
    }
    return sortConfig.direction === 'asc' 
      ? <ChevronUp className="w-3 h-3 text-blue-600" />
      : <ChevronDown className="w-3 h-3 text-blue-600" />;
  };

  // Column header with sort and optional filter
  const ColumnHeader = ({ columnKey, label, filterKey, options, className = '' }) => {
    const [showFilter, setShowFilter] = useState(false);
    const hasFilter = filterKey && options && options.length > 0;
    const isFiltered = filterKey && filters[filterKey];
    
    return (
      <th className={cn("px-2 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase tracking-wider", className)}>
        <div className="flex items-center gap-0.5">
          <span 
            className="cursor-pointer hover:text-gray-900 flex items-center gap-0.5"
            onClick={() => handleSort(columnKey)}
          >
            {label}
            <SortIcon columnKey={columnKey} />
          </span>
          
          {hasFilter && (
            <div className="relative">
              <button
                onClick={(e) => { e.stopPropagation(); setShowFilter(!showFilter); }}
                className={cn(
                  "p-0.5 rounded hover:bg-gray-200",
                  isFiltered && "text-blue-600"
                )}
              >
                <Filter className={cn("w-2.5 h-2.5", isFiltered ? "text-blue-600" : "text-gray-400")} />
              </button>
              
              {showFilter && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setShowFilter(false)} />
                  <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 py-1 min-w-24 max-h-40 overflow-y-auto">
                    <button
                      onClick={() => { setFilters(prev => ({ ...prev, [filterKey]: '' })); setShowFilter(false); }}
                      className={cn(
                        "w-full text-left px-2 py-1 text-[10px] hover:bg-gray-50",
                        !filters[filterKey] && "bg-blue-50 text-blue-700"
                      )}
                    >
                      All
                    </button>
                    {options.map(opt => (
                      <button
                        key={opt}
                        onClick={() => { setFilters(prev => ({ ...prev, [filterKey]: opt })); setShowFilter(false); }}
                        className={cn(
                          "w-full text-left px-2 py-1 text-[10px] hover:bg-gray-50 truncate",
                          filters[filterKey] === opt && "bg-blue-50 text-blue-700"
                        )}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </th>
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4 flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <h2 className="text-sm font-semibold text-gray-900">{title}</h2>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600 rounded">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Toolbar */}
        <div className="px-3 py-2 border-b flex items-center gap-2 flex-wrap">
          {/* Search */}
          <div className="relative flex-1 min-w-48">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search devices..."
              className="w-full pl-7 pr-2 py-1.5 text-xs border rounded"
              autoFocus
            />
          </div>
          
          {/* Tag filter button */}
          {allTags.length > 0 && (
            <div className="relative">
              <button
                onClick={() => setShowTagFilter(!showTagFilter)}
                className={cn(
                  "flex items-center gap-1 px-2 py-1.5 text-xs border rounded",
                  selectedTags.length > 0 ? "bg-purple-50 border-purple-300 text-purple-700" : "hover:bg-gray-50"
                )}
              >
                <Tag className="w-3 h-3" />
                Tags
                {selectedTags.length > 0 && (
                  <span className="bg-purple-600 text-white text-[10px] px-1 rounded">{selectedTags.length}</span>
                )}
              </button>
              
              {showTagFilter && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setShowTagFilter(false)} />
                  <div className="absolute top-full right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 p-3 w-64">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-gray-700">Filter by Tags</span>
                      <button
                        onClick={() => setTagLogic(tagLogic === 'OR' ? 'AND' : 'OR')}
                        className={cn(
                          "text-[10px] px-1.5 py-0.5 rounded font-medium",
                          tagLogic === 'AND' ? "bg-purple-100 text-purple-700" : "bg-gray-100 text-gray-600"
                        )}
                      >
                        {tagLogic}
                      </button>
                    </div>
                    <div className="flex flex-wrap gap-1 max-h-32 overflow-y-auto">
                      {[...allTags].sort((a, b) => a.name.localeCompare(b.name)).map(tag => {
                        const isSelected = selectedTags.includes(tag.slug);
                        return (
                          <button
                            key={tag.id}
                            onClick={() => {
                              if (isSelected) {
                                setSelectedTags(selectedTags.filter(t => t !== tag.slug));
                              } else {
                                setSelectedTags([...selectedTags, tag.slug]);
                              }
                            }}
                            className={cn(
                              "px-1.5 py-0.5 text-[10px] rounded border transition-colors",
                              isSelected
                                ? "bg-purple-600 text-white border-purple-600"
                                : "bg-white text-gray-600 border-gray-300 hover:border-gray-400"
                            )}
                          >
                            {tag.name}
                          </button>
                        );
                      })}
                    </div>
                    {selectedTags.length > 0 && (
                      <button
                        onClick={() => setSelectedTags([])}
                        className="mt-2 text-[10px] text-purple-600 hover:text-purple-800"
                      >
                        Clear tags
                      </button>
                    )}
                  </div>
                </>
              )}
            </div>
          )}
          
          {/* Active filters indicator */}
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-[10px] text-blue-600 hover:text-blue-800"
            >
              Clear filters
            </button>
          )}
          
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-xs text-gray-500">
              {filteredDevices.length} of {allDevices.length}
            </span>
            <button
              onClick={loadDevices}
              className="p-1 text-gray-400 hover:text-gray-600 rounded"
              title="Refresh"
            >
              <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} />
            </button>
          </div>
        </div>

        {/* Device Table */}
        <div className="flex-1 overflow-auto min-h-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="w-5 h-5 animate-spin text-blue-600" />
            </div>
          ) : sortedDevices.length === 0 ? (
            <div className="text-xs text-gray-400 text-center py-12">
              {searchTerm || hasActiveFilters ? 'No matching devices' : 'No devices available'}
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-2 py-2 text-left w-8">
                    {multiSelect && (
                      <input
                        type="checkbox"
                        checked={sortedDevices.length > 0 && sortedDevices.every(d => selected.has(d.ip_address))}
                        onChange={(e) => handleSelectAll(e.target.checked)}
                        className="w-3.5 h-3.5 rounded border-gray-300 text-blue-600"
                      />
                    )}
                  </th>
                  <ColumnHeader columnKey="ip_address" label="IP Address" className="w-28" />
                  <ColumnHeader columnKey="hostname" label="Name" />
                  <ColumnHeader columnKey="role" label="Role" filterKey="role" options={filterOptions.roles} />
                  <ColumnHeader columnKey="platform" label="Platform" filterKey="platform" options={filterOptions.platforms} />
                  <ColumnHeader columnKey="site" label="Site" filterKey="site" options={filterOptions.sites} />
                  <ColumnHeader columnKey="status" label="Status" filterKey="status" options={filterOptions.statuses} className="w-20" />
                  <th className="px-2 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Tags</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {sortedDevices.map(device => {
                  const isSelected = selected.has(device.ip_address);
                  return (
                    <tr
                      key={device.ip_address}
                      onClick={() => toggleDevice(device.ip_address)}
                      className={cn(
                        "cursor-pointer transition-colors",
                        isSelected ? "bg-blue-50 hover:bg-blue-100" : "hover:bg-gray-50"
                      )}
                    >
                      <td className="px-2 py-1.5">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleDevice(device.ip_address)}
                          onClick={(e) => e.stopPropagation()}
                          className="w-3.5 h-3.5 rounded border-gray-300 text-blue-600"
                        />
                      </td>
                      <td className="px-2 py-1.5 font-mono text-xs text-gray-700">
                        {device.ip_address}
                      </td>
                      <td className="px-2 py-1.5 text-xs font-medium text-gray-900 truncate max-w-40">
                        {device.hostname || '—'}
                      </td>
                      <td className="px-2 py-1.5 text-xs text-gray-600 truncate max-w-24">
                        {device.role || '—'}
                      </td>
                      <td className="px-2 py-1.5 text-xs text-gray-600 truncate max-w-24">
                        {device.platform || '—'}
                      </td>
                      <td className="px-2 py-1.5 text-xs text-gray-600 truncate max-w-24">
                        {device.site || '—'}
                      </td>
                      <td className="px-2 py-1.5">
                        <span className={cn(
                          "inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium",
                          device.status === 'active' 
                            ? "bg-green-100 text-green-700" 
                            : "bg-gray-100 text-gray-600"
                        )}>
                          {device.status || '—'}
                        </span>
                      </td>
                      <td className="px-2 py-1.5">
                        <div className="flex flex-wrap gap-0.5 max-w-32">
                          {(device.tags || []).slice(0, 3).map(tag => (
                            <span
                              key={tag.id}
                              className="px-1 py-0.5 text-[9px] rounded bg-gray-100 text-gray-600 truncate max-w-16"
                              title={tag.name}
                            >
                              {tag.name}
                            </span>
                          ))}
                          {(device.tags || []).length > 3 && (
                            <span className="px-1 py-0.5 text-[9px] text-gray-400">
                              +{device.tags.length - 3}
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50">
          <span className="text-xs text-gray-500">
            {selected.size} selected
          </span>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 rounded"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!hasChanges() || saving}
              className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1"
            >
              <Check className="w-3.5 h-3.5" />
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
