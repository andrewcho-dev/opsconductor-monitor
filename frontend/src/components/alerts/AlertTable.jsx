/**
 * Alert Table Component
 */

import { useState, useMemo, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ChevronLeft, ChevronRight, ChevronUp, ChevronDown, ChevronsUpDown, Filter } from 'lucide-react';
import { SEVERITY_CONFIG, CATEGORY_CONFIG, formatRelativeTime } from '../../lib/constants';

// Status configuration with colors and order
const STATUS_CONFIG = {
  active: { label: 'Active', color: 'red', bgClass: 'bg-red-100 text-red-700 border-red-300', selectedClass: 'bg-red-500 text-white border-red-500' },
  acknowledged: { label: 'Ack', color: 'blue', bgClass: 'bg-blue-100 text-blue-700 border-blue-300', selectedClass: 'bg-blue-500 text-white border-blue-500' },
  suppressed: { label: 'Supp', color: 'yellow', bgClass: 'bg-yellow-100 text-yellow-700 border-yellow-300', selectedClass: 'bg-yellow-500 text-white border-yellow-500' },
  resolved: { label: 'Resolved', color: 'green', bgClass: 'bg-green-100 text-green-700 border-green-300', selectedClass: 'bg-green-500 text-white border-green-500' },
};
const STATUS_ORDER = ['active', 'acknowledged', 'suppressed', 'resolved'];

export function AlertTable({
  alerts = [],
  loading = false,
  pagination = {},
  onPageChange,
  onLoadMore,  // For infinite scroll - called when user scrolls near bottom
  loadingMore = false,  // Show loading indicator at bottom during infinite scroll
  selectedIds = [],
  onSelectChange,
  filters = {},
  onFilterChange,
  statusCounts = {},
  severityStatusCounts = {},
  showResolvedTime = false,  // Show resolved time column instead of age from now
  hideStatusPills = false,   // Hide the status filter pills
}) {
  const [sortConfig, setSortConfig] = useState({ key: 'occurred_at', direction: 'desc' });
  const [openFilter, setOpenFilter] = useState(null);
  const [filterSearch, setFilterSearch] = useState('');
  const [pendingSelections, setPendingSelections] = useState({});
  
  // Cache dropdown options when filter is open to prevent scroll reset on data refresh
  const cachedOptionsRef = useRef({});
  const dropdownRef = useRef(null);
  const tableContainerRef = useRef(null);
  const loadMoreTriggerRef = useRef(null);
  
  // Infinite scroll - observe when user scrolls near bottom
  useEffect(() => {
    if (!onLoadMore || !loadMoreTriggerRef.current) return;
    
    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting && !loading && !loadingMore && pagination.page < pagination.pages) {
          onLoadMore();
        }
      },
      { threshold: 0.1, root: tableContainerRef.current }
    );
    
    observer.observe(loadMoreTriggerRef.current);
    return () => observer.disconnect();
  }, [onLoadMore, loading, loadingMore, pagination.page, pagination.pages]);

  // Severity order for sorting
  const SEVERITY_ORDER = { critical: 0, major: 1, minor: 2, warning: 3, info: 4, clear: 5 };

  // Sort alerts
  const sortedAlerts = useMemo(() => {
    if (!alerts || alerts.length === 0) return alerts;
    
    const sorted = [...alerts].sort((a, b) => {
      let aVal, bVal;
      
      switch (sortConfig.key) {
        case 'occurrence_count':
          aVal = a.occurrence_count || 1;
          bVal = b.occurrence_count || 1;
          break;
        case 'device_name':
          aVal = (a.device_name || a.device_ip || '').toLowerCase();
          bVal = (b.device_name || b.device_ip || '').toLowerCase();
          break;
        case 'occurred_at':
          aVal = new Date(a.occurred_at).getTime();
          bVal = new Date(b.occurred_at).getTime();
          break;
        default:
          aVal = a[sortConfig.key] || '';
          bVal = b[sortConfig.key] || '';
      }
      
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
    
    return sorted;
  }, [alerts, sortConfig]);

  const handleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) {
      return <ChevronsUpDown className="w-3 h-3 text-gray-400" />;
    }
    return sortConfig.direction === 'asc' ? (
      <ChevronUp className="w-3 h-3 text-blue-600" />
    ) : (
      <ChevronDown className="w-3 h-3 text-blue-600" />
    );
  };

  // Get unique values for filter dropdowns
  const uniqueSeverities = useMemo(() => 
    [...new Set(alerts.map(a => a.severity))].filter(Boolean).sort((a, b) => (SEVERITY_ORDER[a] || 99) - (SEVERITY_ORDER[b] || 99)),
    [alerts]
  );
  const uniqueCategories = useMemo(() => 
    [...new Set(alerts.map(a => a.category))].filter(Boolean).sort(),
    [alerts]
  );
  const uniqueDevices = useMemo(() => 
    [...new Set(alerts.map(a => a.device_name || a.device_ip))].filter(Boolean).sort(),
    [alerts]
  );
  const uniqueStatuses = useMemo(() => 
    [...new Set(alerts.map(a => a.status))].filter(Boolean).sort(),
    [alerts]
  );

  // Parse selected statuses from filters (comma-separated string)
  const selectedStatuses = useMemo(() => {
    if (!filters.status) return ['active', 'acknowledged', 'suppressed']; // Default: show non-resolved
    return filters.status.split(',');
  }, [filters.status]);

  const handleStatusToggle = (status) => {
    let newStatuses;
    if (selectedStatuses.includes(status)) {
      // Remove it (but don't allow empty selection)
      newStatuses = selectedStatuses.filter(s => s !== status);
      if (newStatuses.length === 0) return; // Don't allow deselecting all
    } else {
      // Add it
      newStatuses = [...selectedStatuses, status];
    }
    onFilterChange?.({ status: newStatuses.join(',') });
  };

  const handleFilterSelect = (field, value) => {
    onFilterChange?.({ [field]: value || null });
    setOpenFilter(null);
    setFilterSearch('');
  };

  // Multi-select filter for device_name field
  const handleMultiFilterToggle = (field, value) => {
    setPendingSelections(prev => {
      const current = prev[field] || (filters[field] ? filters[field].split(',') : []);
      if (current.includes(value)) {
        return { ...prev, [field]: current.filter(v => v !== value) };
      } else {
        return { ...prev, [field]: [...current, value] };
      }
    });
  };

  const applyMultiFilter = (field) => {
    const selections = pendingSelections[field] || [];
    onFilterChange?.({ [field]: selections.length > 0 ? selections.join(',') : null });
    setOpenFilter(null);
    setFilterSearch('');
    setPendingSelections(prev => ({ ...prev, [field]: undefined }));
  };

  const clearMultiFilter = (field) => {
    onFilterChange?.({ [field]: null });
    setOpenFilter(null);
    setFilterSearch('');
    setPendingSelections(prev => ({ ...prev, [field]: undefined }));
  };

  // Simple single-select dropdown for severity/category
  const FilterDropdown = ({ field, options, currentValue, label }) => {
    const isOpen = openFilter === field;
    const hasFilter = currentValue && currentValue !== 'all';
    
    return (
      <div className="relative">
        <button
          onClick={(e) => {
            e.stopPropagation();
            setOpenFilter(isOpen ? null : field);
            setFilterSearch('');
          }}
          className={`flex items-center gap-1 ${hasFilter ? 'text-blue-600' : ''}`}
        >
          <span className="uppercase font-semibold">{label}</span>
          <Filter className={`w-3 h-3 ${hasFilter ? 'text-blue-600' : 'text-gray-400'}`} />
        </button>
        {isOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setOpenFilter(null)} />
            <div 
              className="absolute top-full left-0 mt-1 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-20 py-1"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                onClick={() => handleFilterSelect(field, null)}
                className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 ${!currentValue ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 font-medium' : ''}`}
              >
                All
              </button>
              {options.map((opt) => (
                <button
                  key={opt}
                  onClick={() => handleFilterSelect(field, opt)}
                  className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 truncate ${currentValue === opt ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 font-medium' : ''}`}
                >
                  {field === 'severity' ? (SEVERITY_CONFIG[opt]?.label || opt) : 
                   field === 'category' ? (CATEGORY_CONFIG[opt]?.label || opt) : opt}
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    );
  };

  // Multi-select dropdown with search for device_name
  const DeviceFilterDropdown = ({ options, currentValue, label }) => {
    const field = 'device_name';
    const isOpen = openFilter === field;
    const hasFilter = currentValue && currentValue !== 'all';
    
    // Cache options when opening
    useEffect(() => {
      if (isOpen && options.length > 0 && !cachedOptionsRef.current[field]) {
        cachedOptionsRef.current[field] = options;
      }
    }, [isOpen, options]);
    
    // Clear cache when closing
    useEffect(() => {
      if (!isOpen) {
        cachedOptionsRef.current[field] = null;
      }
    }, [isOpen]);
    
    const displayOptions = cachedOptionsRef.current[field] || options;
    
    // Get current selections (from pending or from filters)
    const currentSelections = pendingSelections[field] || (currentValue ? currentValue.split(',') : []);
    
    // Filter options by search
    const filteredOptions = displayOptions.filter(opt => 
      opt.toLowerCase().includes(filterSearch.toLowerCase())
    );
    
    return (
      <div className="relative">
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (!isOpen) {
              cachedOptionsRef.current[field] = options;
              setPendingSelections(prev => ({ ...prev, [field]: currentValue ? currentValue.split(',') : [] }));
            }
            setOpenFilter(isOpen ? null : field);
            setFilterSearch('');
          }}
          className={`flex items-center gap-1 ${hasFilter ? 'text-blue-600' : ''}`}
        >
          <span className="uppercase font-semibold">{label}</span>
          {hasFilter && <span className="text-xs bg-blue-100 text-blue-600 px-1 rounded">{currentValue.split(',').length}</span>}
          <Filter className={`w-3 h-3 ${hasFilter ? 'text-blue-600' : 'text-gray-400'}`} />
        </button>
        {isOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => { setOpenFilter(null); setFilterSearch(''); }} />
            <div 
              ref={dropdownRef}
              className="absolute top-full left-0 mt-1 w-72 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-20 flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Search input */}
              <div className="p-2 border-b border-gray-200 dark:border-gray-700">
                <input
                  type="text"
                  placeholder="Search devices..."
                  value={filterSearch}
                  onChange={(e) => setFilterSearch(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  autoFocus
                />
              </div>
              
              {/* Options list */}
              <div className="max-h-64 overflow-y-auto">
                {filteredOptions.length === 0 ? (
                  <div className="px-4 py-3 text-sm text-gray-500">No devices found</div>
                ) : (
                  filteredOptions.map((opt) => (
                    <label
                      key={opt}
                      className="flex items-center gap-2 px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={currentSelections.includes(opt)}
                        onChange={() => handleMultiFilterToggle(field, opt)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="truncate">{opt}</span>
                    </label>
                  ))
                )}
              </div>
              
              {/* Action buttons */}
              <div className="p-2 border-t border-gray-200 dark:border-gray-700 flex gap-2">
                <button
                  onClick={() => clearMultiFilter(field)}
                  className="flex-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                >
                  Clear
                </button>
                <button
                  onClick={() => applyMultiFilter(field)}
                  className="flex-1 px-3 py-1.5 text-sm bg-blue-600 text-white hover:bg-blue-700 rounded font-medium"
                >
                  Apply ({currentSelections.length})
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    );
  };

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      onSelectChange?.(alerts.map(a => a.id));
    } else {
      onSelectChange?.([]);
    }
  };

  const handleSelectOne = (id) => {
    if (selectedIds.includes(id)) {
      onSelectChange?.(selectedIds.filter(i => i !== id));
    } else {
      onSelectChange?.([...selectedIds, id]);
    }
  };

  // Compute status counts based on selected severity filter
  const filteredStatusCounts = useMemo(() => {
    // If no severity filter, use total status counts
    if (!filters.severity) {
      return statusCounts;
    }
    
    // Parse selected severities (comma-separated)
    const selectedSeverities = filters.severity.split(',');
    
    // Sum up counts for selected severities
    const counts = { active: 0, acknowledged: 0, suppressed: 0, resolved: 0 };
    selectedSeverities.forEach(sev => {
      const sevCounts = severityStatusCounts[sev] || {};
      counts.active += sevCounts.active || 0;
      counts.acknowledged += sevCounts.acknowledged || 0;
      counts.suppressed += sevCounts.suppressed || 0;
      counts.resolved += sevCounts.resolved || 0;
    });
    
    return counts;
  }, [filters.severity, statusCounts, severityStatusCounts]);

  // Status filter pills component - always visible
  const StatusFilterPills = () => (
    <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 flex items-center gap-2">
      <span className="text-xs font-medium text-gray-500 dark:text-gray-400 mr-1">Status:</span>
      {STATUS_ORDER.map((status) => {
        const config = STATUS_CONFIG[status];
        const count = filteredStatusCounts[status] || 0;
        const isSelected = selectedStatuses.includes(status);
        
        return (
          <button
            key={status}
            onClick={() => handleStatusToggle(status)}
            className={`px-2 py-0.5 text-xs font-medium rounded border transition-all ${
              isSelected ? config.selectedClass : 'bg-white dark:bg-gray-800 text-gray-500 border-gray-300 dark:border-gray-600 hover:border-gray-400'
            }`}
          >
            {config.label} {count > 0 && <span className="ml-1 opacity-75">({count})</span>}
          </button>
        );
      })}
    </div>
  );

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col h-full">
        {!hideStatusPills && <StatusFilterPills />}
        <div className="flex items-center justify-center p-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-500">Loading alerts...</span>
        </div>
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col h-full">
        {!hideStatusPills && <StatusFilterPills />}
        <div className="text-center text-gray-500 p-8">
          <p className="text-lg font-medium">No alerts found</p>
          <p className="text-sm">Try adjusting your filters</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col h-full">
      {!hideStatusPills && <StatusFilterPills />}
      
      {/* Table */}
      <div ref={tableContainerRef} className="overflow-auto flex-1">
        <table className="w-full divide-y divide-gray-200 dark:divide-gray-700" style={{ tableLayout: 'fixed' }}>
          <colgroup>
            <col style={{ width: '40px' }} />
            <col style={{ width: '80px' }} />
            <col style={{ width: '50px' }} />
            <col style={{ width: '280px' }} />
            <col style={{ width: '200px' }} />
            <col style={{ width: '100px' }} />
            <col style={{ width: '140px' }} />
            {showResolvedTime && <col style={{ width: '140px' }} />}
            <col style={{ width: '70px' }} />
            <col style={{ width: '90px' }} />
          </colgroup>
          <thead className="bg-gray-50 dark:bg-gray-900">
            <tr>
              <th style={{ width: '40px' }} className="px-3 py-2">
                <input
                  type="checkbox"
                  checked={selectedIds.length === alerts.length && alerts.length > 0}
                  onChange={handleSelectAll}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
              </th>
              <th style={{ width: '80px' }} className="px-3 py-2 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                SEVERITY
              </th>
              <th
                style={{ width: '50px' }}
                className="px-2 py-2 text-center text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase"
              >
                #
              </th>
              <th style={{ width: '250px' }} className="px-3 py-2 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                ALERT
              </th>
              <th style={{ width: '180px' }} className="px-4 py-2 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                DEVICE
              </th>
              <th style={{ width: '100px' }} className="px-3 py-2 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                <FilterDropdown field="category" options={uniqueCategories} currentValue={filters.category} label="Category" />
              </th>
              <th
                style={{ width: '140px' }}
                className="px-3 py-2 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
                onClick={() => handleSort('occurred_at')}
              >
                <div className="flex items-center gap-1">
                  FIRST SEEN
                  <SortIcon columnKey="occurred_at" />
                </div>
              </th>
              {showResolvedTime && (
                <th
                  style={{ width: '140px' }}
                  className="px-3 py-2 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
                  onClick={() => handleSort('resolved_at')}
                >
                  <div className="flex items-center gap-1">
                    RESOLVED
                    <SortIcon columnKey="resolved_at" />
                  </div>
                </th>
              )}
              <th
                style={{ width: '70px' }}
                className="px-3 py-2 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
                onClick={() => handleSort('occurred_at')}
              >
                <div className="flex items-center gap-1">
                  {showResolvedTime ? 'DURATION' : 'AGE'}
                  <SortIcon columnKey="occurred_at" />
                </div>
              </th>
              <th style={{ width: '90px' }} className="px-3 py-2 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                STATUS
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {sortedAlerts.map((alert) => {
              const severityConfig = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.info;
              const categoryConfig = CATEGORY_CONFIG[alert.category] || CATEGORY_CONFIG.unknown;
              const SeverityIcon = severityConfig.icon;
              const CategoryIcon = categoryConfig.icon;

              return (
                <tr
                  key={alert.id}
                  className={`hover:bg-gray-50 dark:hover:bg-gray-700/50 ${
                    selectedIds.includes(alert.id) ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                  }`}
                >
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(alert.id)}
                      onChange={() => handleSelectOne(alert.id)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <span className={`font-mono text-xs ${severityConfig.textClass}`}>
                      {severityConfig.label}
                    </span>
                  </td>
                  <td className="px-2 py-2 text-center">
                    <span className="font-mono text-xs text-gray-500">
                      {alert.occurrence_count > 1 ? alert.occurrence_count : ''}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <Link
                      to={`/alerts/${alert.id}`}
                      className="font-mono text-xs text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 truncate block max-w-[280px]"
                      title={alert.title}
                    >
                      {alert.title}
                    </Link>
                  </td>
                  <td className="px-3 py-2">
                    <span className="font-mono text-xs text-gray-900 dark:text-white truncate block" title={alert.device_name || alert.device_ip}>
                      {alert.device_name || alert.device_ip || '-'}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <span className="font-mono text-xs text-gray-600 dark:text-gray-300">
                      {categoryConfig.label}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                    {(() => {
                      const d = new Date(alert.occurred_at);
                      const mm = String(d.getMonth() + 1).padStart(2, '0');
                      const dd = String(d.getDate()).padStart(2, '0');
                      const yy = String(d.getFullYear()).slice(-2);
                      const hh = String(d.getHours()).padStart(2, '0');
                      const min = String(d.getMinutes()).padStart(2, '0');
                      const tz = d.toLocaleTimeString('en-US', { timeZoneName: 'short' }).split(' ').pop();
                      return `${mm}/${dd}/${yy} ${hh}:${min} ${tz}`;
                    })()}
                  </td>
                  {showResolvedTime && (
                    <td className="px-3 py-2 font-mono text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                      {(() => {
                        const d = new Date(alert.resolved_at || alert.updated_at);
                        const mm = String(d.getMonth() + 1).padStart(2, '0');
                        const dd = String(d.getDate()).padStart(2, '0');
                        const yy = String(d.getFullYear()).slice(-2);
                        const hh = String(d.getHours()).padStart(2, '0');
                        const min = String(d.getMinutes()).padStart(2, '0');
                        const tz = d.toLocaleTimeString('en-US', { timeZoneName: 'short' }).split(' ').pop();
                        return `${mm}/${dd}/${yy} ${hh}:${min} ${tz}`;
                      })()}
                    </td>
                  )}
                  <td className="px-3 py-2 font-mono text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                    {(() => {
                      // For resolved alerts, show duration between occurred and resolved
                      // For active alerts, show age from occurred to now
                      const endTime = showResolvedTime ? new Date(alert.resolved_at || alert.updated_at) : new Date();
                      const occurred = new Date(alert.occurred_at);
                      const diffMs = endTime - occurred;
                      const diffMins = Math.floor(diffMs / 60000);
                      const diffHrs = Math.floor(diffMins / 60);
                      const diffDays = Math.floor(diffHrs / 24);
                      if (diffDays > 0) return `${diffDays}d ${diffHrs % 24}h`;
                      if (diffHrs > 0) return `${diffHrs}h ${diffMins % 60}m`;
                      return `${diffMins}m`;
                    })()}
                  </td>
                  <td className="px-3 py-2">
                    <span className={`font-mono text-xs capitalize ${
                      alert.status === 'active' ? 'text-red-600' : 
                      alert.status === 'acknowledged' ? 'text-blue-600' : 
                      alert.status === 'suppressed' ? 'text-yellow-600' : 
                      'text-green-600'
                    }`}>
                      {alert.status}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        
        {/* Infinite scroll trigger and loading indicator */}
        {onLoadMore && (
          <div ref={loadMoreTriggerRef} className="py-4 text-center">
            {loadingMore ? (
              <div className="flex items-center justify-center gap-2 text-gray-500">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                <span className="text-sm">Loading more...</span>
              </div>
            ) : pagination.page < pagination.pages ? (
              <span className="text-sm text-gray-400">Scroll for more</span>
            ) : alerts.length > 0 ? (
              <span className="text-sm text-gray-400">All {pagination.total} alerts loaded</span>
            ) : null}
          </div>
        )}
      </div>

      {/* Pagination - only show if not using infinite scroll */}
      {!onLoadMore && pagination.pages > 1 && (
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div className="text-sm text-gray-500">
            Showing {((pagination.page - 1) * pagination.per_page) + 1} to{' '}
            {Math.min(pagination.page * pagination.per_page, pagination.total)} of{' '}
            {pagination.total} alerts
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onPageChange?.(pagination.page - 1)}
              disabled={pagination.page <= 1}
              className="p-2 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="text-sm text-gray-700 dark:text-gray-300">
              Page {pagination.page} of {pagination.pages}
            </span>
            <button
              onClick={() => onPageChange?.(pagination.page + 1)}
              disabled={pagination.page >= pagination.pages}
              className="p-2 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default AlertTable;
