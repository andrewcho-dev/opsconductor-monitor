import React, { useState, useMemo, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { PageLayout, PageHeader } from "../../components/layout";
import { useNetBoxDevices, useNetBoxStatus, useNetBoxTags } from "../../hooks/useNetBox";
import { fetchApi } from "../../lib/utils";
import { 
  Server, RefreshCw, Database, ExternalLink, ChevronDown, ChevronRight,
  Search, Monitor, HardDrive, Eye, CheckCircle, XCircle, Filter,
  ChevronUp, ChevronsUpDown, FolderOpen, FolderClosed, Network, Tag, Download
} from "lucide-react";
import { cn } from "../../lib/utils";

// Helper to check if IP is in range
function ipToNumber(ip) {
  if (!ip) return 0;
  const parts = ip.split('.').map(Number);
  return parts[0] * 16777216 + parts[1] * 65536 + parts[2] * 256 + parts[3];
}

function isIpInRange(ip, startIp, endIp) {
  const ipNum = ipToNumber(ip);
  const startNum = ipToNumber(startIp);
  const endNum = ipToNumber(endIp);
  return ipNum >= startNum && ipNum <= endNum;
}

// Helper to check if IP is in a CIDR prefix (e.g., 10.1.1.0/24)
function isIpInPrefix(ip, prefix) {
  if (!ip || !prefix) return false;
  const [network, bits] = prefix.split('/');
  if (!network || !bits) return false;
  
  const ipNum = ipToNumber(ip);
  const networkNum = ipToNumber(network);
  const mask = ~((1 << (32 - parseInt(bits))) - 1) >>> 0;
  
  return (ipNum & mask) === (networkNum & mask);
}

export function DevicesPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const viewMode = searchParams.get('view') || 'all'; // 'all', 'network', 'site', 'type'
  
  // Check NetBox status
  const netboxStatus = useNetBoxStatus();
  
  // NetBox devices and tags
  const { devices, loading: devicesLoading, refetch: refetchDevices } = useNetBoxDevices();
  const { tags: netboxTags, loading: tagsLoading, refetch: refetchTags } = useNetBoxTags();
  
  // UI state
  const [search, setSearch] = useState("");
  const [selectedTags, setSelectedTags] = useState([]); // array for multi-select
  const [tagLogic, setTagLogic] = useState('OR'); // 'OR' or 'AND'
  const [selectedDevices, setSelectedDevices] = useState(new Set());
  const [expandedGroups, setExpandedGroups] = useState(new Set());
  const [selectedGroup, setSelectedGroup] = useState(null); // for filtering by group
  
  // Sorting state
  const [sortConfig, setSortConfig] = useState({ key: 'ip_address', direction: 'asc' });
  
  // Filter state
  const [filters, setFilters] = useState({
    role: '',
    platform: '',
    site: '',
    status: '',
  });

  // Assign devices to IP prefixes and ranges
  const devicesWithRanges = useMemo(() => {
    return devices.map(device => {
      const ip = device.ip_address;
      
      // Find matching prefix (most specific match - longest prefix)
      const matchingPrefixes = ipPrefixes.filter(prefix => 
        isIpInPrefix(ip, prefix.prefix)
      );
      // Sort by prefix length descending to get most specific match
      matchingPrefixes.sort((a, b) => {
        const aLen = parseInt(a.prefix.split('/')[1] || 0);
        const bLen = parseInt(b.prefix.split('/')[1] || 0);
        return bLen - aLen;
      });
      const matchingPrefix = matchingPrefixes[0];
      
      // Find matching range
      const matchingRange = ipRanges.find(range => 
        isIpInRange(ip, range.start_address, range.end_address)
      );
      
      return {
        ...device,
        network_prefix: matchingPrefix?.prefix || null,
        network_prefix_id: matchingPrefix?.id || null,
        network_prefix_display: matchingPrefix?.display || "Unassigned",
        network_range: matchingRange?.display || "Unassigned",
        network_range_id: matchingRange?.id || null,
      };
    });
  }, [devices, ipPrefixes, ipRanges]);

  // Get unique values for filter dropdowns
  const filterOptions = useMemo(() => {
    const roles = new Set();
    const platforms = new Set();
    const sites = new Set();
    const statuses = new Set();
    
    devicesWithRanges.forEach(d => {
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
  }, [devicesWithRanges]);

  // Filter devices by search, selected prefix, selected range, and filters
  const filteredDevices = useMemo(() => {
    let filtered = devicesWithRanges;
    
    // Filter by selected prefix
    if (selectedPrefix !== null) {
      if (selectedPrefix === 'unassigned') {
        filtered = filtered.filter(d => d.network_prefix_id === null);
      } else {
        const prefixId = typeof selectedPrefix === 'string' ? parseInt(selectedPrefix) : selectedPrefix;
        filtered = filtered.filter(d => d.network_prefix_id === prefixId);
      }
    }
    
    // Filter by selected range
    if (selectedRange !== null) {
      if (selectedRange === 'unassigned') {
        filtered = filtered.filter(d => d.network_range_id === null);
      } else {
        const rangeId = typeof selectedRange === 'string' ? parseInt(selectedRange) : selectedRange;
        filtered = filtered.filter(d => d.network_range_id === rangeId);
      }
    }
    
    // Filter by selected tags (multi-select with AND/OR logic)
    if (selectedTags.length > 0) {
      filtered = filtered.filter(d => {
        const deviceTags = d._netbox?.tags || [];
        const deviceTagSlugs = deviceTags.map(t => t.slug);
        
        if (tagLogic === 'AND') {
          // Device must have ALL selected tags
          return selectedTags.every(tag => deviceTagSlugs.includes(tag));
        } else {
          // Device must have ANY of the selected tags (OR)
          return selectedTags.some(tag => deviceTagSlugs.includes(tag));
        }
      });
    }
    
    // Filter by search
    if (search) {
      const searchLower = search.toLowerCase();
      filtered = filtered.filter(d =>
        d.name?.toLowerCase().includes(searchLower) ||
        d.ip_address?.toLowerCase().includes(searchLower) ||
        d.role?.toLowerCase().includes(searchLower) ||
        d.platform?.toLowerCase().includes(searchLower) ||
        d.site?.toLowerCase().includes(searchLower)
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
  }, [devicesWithRanges, selectedPrefix, selectedRange, selectedTags, tagLogic, search, filters]);
  
  // Sort devices within groups
  const sortDevices = (deviceList) => {
    return [...deviceList].sort((a, b) => {
      let aVal = a[sortConfig.key];
      let bVal = b[sortConfig.key];
      
      // Handle IP address sorting numerically
      if (sortConfig.key === 'ip_address') {
        aVal = ipToNumber(aVal);
        bVal = ipToNumber(bVal);
      } else {
        // String comparison for other fields
        aVal = (aVal || '').toLowerCase();
        bVal = (bVal || '').toLowerCase();
      }
      
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
  };
  
  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };
  
  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) {
      return <ChevronsUpDown className="w-3 h-3 text-gray-400" />;
    }
    return sortConfig.direction === 'asc' 
      ? <ChevronUp className="w-3 h-3 text-blue-600" />
      : <ChevronDown className="w-3 h-3 text-blue-600" />;
  };
  
  // Column header with sort and optional filter
  const ColumnHeader = ({ columnKey, label, filterKey, filterOptions: options }) => {
    const [showFilter, setShowFilter] = useState(false);
    const hasFilter = filterKey && options && options.length > 0;
    const isFiltered = filterKey && filters[filterKey];
    
    return (
      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
        <div className="flex items-center gap-1">
          <span 
            className="cursor-pointer hover:text-gray-900 flex items-center gap-1"
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
                title={`Filter by ${label}`}
              >
                <Filter className={cn("w-3 h-3", isFiltered ? "text-blue-600" : "text-gray-400")} />
              </button>
              
              {showFilter && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setShowFilter(false)} />
                  <div className="absolute top-full left-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 py-1 min-w-32 max-h-48 overflow-y-auto">
                    <button
                      onClick={() => { setFilters(prev => ({ ...prev, [filterKey]: '' })); setShowFilter(false); }}
                      className={cn(
                        "w-full text-left px-3 py-1.5 text-xs hover:bg-gray-50",
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
                          "w-full text-left px-3 py-1.5 text-xs hover:bg-gray-50",
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

  // Group devices by IP range for hierarchical display
  const groupedByRange = useMemo(() => {
    const groups = {};
    
    // Initialize groups from IP ranges
    ipRanges.forEach(range => {
      groups[range.id] = {
        id: range.id,
        display: range.display,
        description: range.description,
        devices: [],
      };
    });
    
    // Add "Unassigned" group
    groups['unassigned'] = {
      id: 'unassigned',
      display: 'Unassigned',
      description: 'Devices not in any defined IP range',
      devices: [],
    };
    
    // Assign devices to groups
    filteredDevices.forEach(device => {
      const rangeId = device.network_range_id || 'unassigned';
      if (groups[rangeId]) {
        groups[rangeId].devices.push(device);
      }
    });
    
    // Convert to array and filter out empty groups
    return Object.values(groups).filter(g => g.devices.length > 0);
  }, [filteredDevices, ipRanges]);

  const toggleRange = (rangeId) => {
    setExpandedRanges(prev => {
      const next = new Set(prev);
      if (next.has(rangeId)) next.delete(rangeId);
      else next.add(rangeId);
      return next;
    });
  };

  const handleSelectDevice = (ip, checked) => {
    setSelectedDevices(prev => {
      const next = new Set(prev);
      if (checked) next.add(ip);
      else next.delete(ip);
      return next;
    });
  };

  const handleSelectAll = (deviceList, checked) => {
    setSelectedDevices(prev => {
      const next = new Set(prev);
      deviceList.forEach(d => {
        if (checked) next.add(d.ip_address);
        else next.delete(d.ip_address);
      });
      return next;
    });
  };

  const handleShowDetail = (device) => {
    const cleanIp = device.ip_address?.replace(/\/\d+$/, '');
    navigate(`/inventory/devices/${cleanIp}`);
  };

  const handleRefresh = () => {
    refetchDevices();
    refetchPrefixes();
    refetchRanges();
    refetchTags();
  };

  const loading = devicesLoading || prefixesLoading || rangesLoading || tagsLoading;

  // Device type icon
  const DeviceTypeIcon = ({ type }) => {
    if (type === 'virtual_machine') {
      return <Monitor className="w-4 h-4 text-purple-500" title="Virtual Machine" />;
    }
    return <HardDrive className="w-4 h-4 text-blue-500" title="Physical Device" />;
  };

  // Status badge
  const StatusBadge = ({ status }) => {
    const isActive = status === 'active';
    return (
      <span className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
        isActive ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
      )}>
        {isActive ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
        {status || 'unknown'}
      </span>
    );
  };

  // Count devices per prefix for sidebar
  const prefixDeviceCounts = useMemo(() => {
    const counts = {};
    devicesWithRanges.forEach(d => {
      const prefixId = d.network_prefix_id || 'unassigned';
      counts[prefixId] = (counts[prefixId] || 0) + 1;
    });
    return counts;
  }, [devicesWithRanges]);

  // Count devices per range for sidebar
  const rangeDeviceCounts = useMemo(() => {
    const counts = {};
    devicesWithRanges.forEach(d => {
      const rangeId = d.network_range_id || 'unassigned';
      counts[rangeId] = (counts[rangeId] || 0) + 1;
    });
    return counts;
  }, [devicesWithRanges]);

  // Sidebar content for IP prefixes, ranges, and tags
  const sidebarContent = (
    <>
      {/* IP Prefixes */}
      <div className="mb-4">
        <div className="px-4 py-1">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
            IP Prefixes
          </span>
        </div>
        <div className="mt-1 space-y-0.5 max-h-64 overflow-y-auto">
          {ipPrefixes.map(prefix => (
            <button
              key={prefix.id}
              onClick={() => {
                setSelectedPrefix(selectedPrefix === prefix.id ? null : prefix.id);
                setSelectedRange(null); // Clear range filter when selecting prefix
              }}
              className={cn(
                "w-full flex items-center gap-3 px-4 py-2 text-sm transition-colors",
                selectedPrefix === prefix.id
                  ? "bg-blue-50 text-blue-700 border-r-2 border-blue-600 font-medium"
                  : "text-gray-700 hover:bg-gray-50 hover:text-gray-900"
              )}
            >
              {selectedPrefix === prefix.id ? (
                <Network className="w-4 h-4" />
              ) : (
                <Network className="w-4 h-4 text-gray-400" />
              )}
              <span className="truncate font-mono text-xs">{prefix.prefix}</span>
              <span className="ml-auto text-xs text-gray-400">{prefixDeviceCounts[prefix.id] || 0}</span>
            </button>
          ))}
          {prefixDeviceCounts['unassigned'] > 0 && (
            <button
              onClick={() => {
                setSelectedPrefix(selectedPrefix === 'unassigned' ? null : 'unassigned');
                setSelectedRange(null);
              }}
              className={cn(
                "w-full flex items-center gap-3 px-4 py-2 text-sm transition-colors",
                selectedPrefix === 'unassigned'
                  ? "bg-blue-50 text-blue-700 border-r-2 border-blue-600 font-medium"
                  : "text-gray-700 hover:bg-gray-50 hover:text-gray-900"
              )}
            >
              <Network className="w-4 h-4 text-gray-400" />
              <span className="truncate">No Prefix</span>
              <span className="ml-auto text-xs text-gray-400">{prefixDeviceCounts['unassigned']}</span>
            </button>
          )}
        </div>
      </div>

      {/* IP Ranges */}
      <div className="mb-4">
        <div className="px-4 py-1">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
            IP Ranges
          </span>
        </div>
        <div className="mt-1 space-y-0.5">
          {ipRanges.map(range => (
            <button
              key={range.id}
              onClick={() => {
                setSelectedRange(selectedRange === range.id ? null : range.id);
                setSelectedPrefix(null); // Clear prefix filter when selecting range
              }}
              className={cn(
                "w-full flex items-center gap-3 px-4 py-2 text-sm transition-colors",
                selectedRange === range.id
                  ? "bg-blue-50 text-blue-700 border-r-2 border-blue-600 font-medium"
                  : "text-gray-700 hover:bg-gray-50 hover:text-gray-900"
              )}
            >
              {selectedRange === range.id ? (
                <FolderOpen className="w-4 h-4" />
              ) : (
                <FolderClosed className="w-4 h-4" />
              )}
              <span className="truncate font-mono text-xs">{range.display}</span>
              <span className="ml-auto text-xs text-gray-400">{rangeDeviceCounts[range.id] || 0}</span>
            </button>
          ))}
          {rangeDeviceCounts['unassigned'] > 0 && (
            <button
              onClick={() => setSelectedRange(selectedRange === 'unassigned' ? null : 'unassigned')}
              className={cn(
                "w-full flex items-center gap-3 px-4 py-2 text-sm transition-colors",
                selectedRange === 'unassigned'
                  ? "bg-blue-50 text-blue-700 border-r-2 border-blue-600 font-medium"
                  : "text-gray-700 hover:bg-gray-50 hover:text-gray-900"
              )}
            >
              <FolderClosed className="w-4 h-4 text-gray-400" />
              <span className="truncate">Unassigned</span>
              <span className="ml-auto text-xs text-gray-400">{rangeDeviceCounts['unassigned']}</span>
            </button>
          )}
        </div>
      </div>

      {/* Tags */}
      {netboxTags.length > 0 && (
        <div className="mb-4">
          <div className="px-4 py-1 flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Tags
            </span>
            <button
              onClick={() => setTagLogic(tagLogic === 'OR' ? 'AND' : 'OR')}
              className={cn(
                "text-[10px] px-1.5 py-0.5 rounded font-medium transition-colors",
                tagLogic === 'AND'
                  ? "bg-purple-100 text-purple-700"
                  : "bg-gray-100 text-gray-600"
              )}
              title={tagLogic === 'OR' ? 'Match ANY selected tag' : 'Match ALL selected tags'}
            >
              {tagLogic}
            </button>
          </div>
          <div className="mt-2 px-4 flex flex-wrap gap-1.5">
            {[...netboxTags].sort((a, b) => a.name.localeCompare(b.name)).map(tag => {
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
                    "px-2 py-0.5 text-xs rounded border transition-colors",
                    isSelected
                      ? "bg-blue-600 text-white border-blue-600 font-medium"
                      : "bg-white text-gray-600 border-gray-300 hover:border-gray-400 hover:text-gray-800"
                  )}
                >
                  {tag.name}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </>
  );

  return (
    <PageLayout module="inventory" sidebarContent={sidebarContent}>
      <PageHeader
        title="Device Inventory"
        description={
          netboxStatus.connected 
            ? `${filteredDevices.length} devices from NetBox`
            : "NetBox not connected"
        }
        actions={
          <button
            onClick={() => navigate('/inventory/prtg-import')}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            title="Import from PRTG to NetBox"
          >
            <Download className="w-5 h-5" />
          </button>
        }
      />

      <div className="p-4 space-y-4">
        {/* Connection status banner */}
        {!netboxStatus.loading && !netboxStatus.connected && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-center gap-3">
            <ExternalLink className="w-5 h-5 text-amber-600" />
            <div>
              <p className="text-sm font-medium text-amber-800">NetBox not connected</p>
              <p className="text-xs text-amber-600">Configure NetBox in Settings → NetBox to view devices.</p>
            </div>
          </div>
        )}

        {/* Toolbar */}
        <div className="bg-white rounded-lg border border-gray-200 p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search devices..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9 pr-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 w-64"
                />
              </div>
              
              {/* Active filters indicator */}
              {(selectedPrefix || selectedRange || selectedTags.length > 0 || filters.role || filters.platform || filters.site || filters.status) && (
                <>
                  <div className="h-5 w-px bg-gray-300" />
                  <div className="flex items-center gap-2 flex-wrap">
                    {selectedPrefix && (
                      <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                        Prefix: {selectedPrefix === 'unassigned' ? 'No Prefix' : ipPrefixes.find(p => p.id === parseInt(selectedPrefix))?.prefix || selectedPrefix}
                      </span>
                    )}
                    {selectedRange && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                        Range: {selectedRange === 'unassigned' ? 'Unassigned' : ipRanges.find(r => r.id === parseInt(selectedRange))?.display || selectedRange}
                      </span>
                    )}
                    {selectedTags.length > 0 && (
                      <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
                        Tags ({tagLogic}): {selectedTags.map(slug => netboxTags.find(t => t.slug === slug)?.name || slug).join(', ')}
                      </span>
                    )}
                    {filters.role && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                        Role: {filters.role}
                      </span>
                    )}
                    {filters.platform && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                        Platform: {filters.platform}
                      </span>
                    )}
                    {filters.site && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                        Site: {filters.site}
                      </span>
                    )}
                    {filters.status && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                        Status: {filters.status}
                      </span>
                    )}
                    <button
                      onClick={() => {
                        setSelectedPrefix(null);
                        setSelectedRange(null);
                        setSelectedTags([]);
                        setFilters({ role: '', platform: '', site: '', status: '' });
                      }}
                      className="text-xs text-blue-600 hover:text-blue-800"
                    >
                      Clear all
                    </button>
                  </div>
                </>
              )}
            </div>

            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">
                {filteredDevices.length} device{filteredDevices.length !== 1 ? 's' : ''}
              </span>
              <button
                onClick={handleRefresh}
                disabled={loading}
                className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
                Refresh
              </button>
            </div>
          </div>
        </div>

        {/* Device table */}
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : filteredDevices.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-gray-500">
              <Server className="w-12 h-12 mb-3 text-gray-300" />
              <p className="text-lg font-medium">No devices found</p>
              <p className="text-sm">Add devices in NetBox or adjust your filters.</p>
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider w-8">
                    <input
                      type="checkbox"
                      checked={filteredDevices.length > 0 && filteredDevices.every(d => selectedDevices.has(d.ip_address))}
                      onChange={(e) => handleSelectAll(filteredDevices, e.target.checked)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                  </th>
                  <ColumnHeader columnKey="ip_address" label="IP Address" />
                  <ColumnHeader columnKey="name" label="Name" />
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider w-10">Type</th>
                  <ColumnHeader columnKey="role" label="Role" filterKey="role" filterOptions={filterOptions.roles} />
                  <ColumnHeader columnKey="platform" label="Platform" filterKey="platform" filterOptions={filterOptions.platforms} />
                  <ColumnHeader columnKey="site" label="Site" filterKey="site" filterOptions={filterOptions.sites} />
                  <ColumnHeader columnKey="status" label="Status" filterKey="status" filterOptions={filterOptions.statuses} />
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {sortDevices(filteredDevices).map((device, index) => (
                  <tr 
                    key={`${device._type}-${device.id}-${index}`}
                    className="hover:bg-gray-50"
                  >
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedDevices.has(device.ip_address)}
                        onChange={(e) => handleSelectDevice(device.ip_address, e.target.checked)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                    </td>
                    <td className="px-4 py-3 font-mono text-sm text-gray-600">
                      {device.ip_address || '—'}
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {device.name || device.hostname || '—'}
                    </td>
                    <td className="px-4 py-3">
                      <DeviceTypeIcon type={device.device_type} />
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {device.role || '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {device.platform || '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {device.site || '—'}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={device.status} />
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleShowDetail(device)}
                        className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700"
                        title="View details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </PageLayout>
  );
}

export default DevicesPage;
