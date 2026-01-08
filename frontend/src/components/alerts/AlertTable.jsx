/**
 * Alert Table Component
 */

import { useState, useMemo } from 'react';
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
  selectedIds = [],
  onSelectChange,
  filters = {},
  onFilterChange,
  statusCounts = {},
  severityStatusCounts = {},
}) {
  const [sortConfig, setSortConfig] = useState({ key: 'occurred_at', direction: 'desc' });
  const [openFilter, setOpenFilter] = useState(null);

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
  };

  const FilterDropdown = ({ field, options, currentValue, label }) => {
    const isOpen = openFilter === field;
    const hasFilter = currentValue && currentValue !== 'all';
    
    return (
      <div className="relative">
        <button
          onClick={() => setOpenFilter(isOpen ? null : field)}
          className={`flex items-center gap-1 ${hasFilter ? 'text-blue-600' : ''}`}
        >
          {label}
          <Filter className={`w-3 h-3 ${hasFilter ? 'text-blue-600' : 'text-gray-400'}`} />
        </button>
        {isOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setOpenFilter(null)} />
            <div className="absolute top-full left-0 mt-1 w-40 bg-white dark:bg-gray-800 rounded shadow-lg border border-gray-200 dark:border-gray-700 z-20 py-1 max-h-48 overflow-y-auto">
              <button
                onClick={() => handleFilterSelect(field, null)}
                className={`w-full text-left px-3 py-1 text-xs hover:bg-gray-100 dark:hover:bg-gray-700 ${!currentValue ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600' : ''}`}
              >
                All
              </button>
              {options.map((opt) => (
                <button
                  key={opt}
                  onClick={() => handleFilterSelect(field, opt)}
                  className={`w-full text-left px-3 py-1 text-xs hover:bg-gray-100 dark:hover:bg-gray-700 truncate ${currentValue === opt ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600' : ''}`}
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
        <StatusFilterPills />
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
        <StatusFilterPills />
        <div className="text-center text-gray-500 p-8">
          <p className="text-lg font-medium">No alerts found</p>
          <p className="text-sm">Try adjusting your filters</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col h-full">
      <StatusFilterPills />
      
      {/* Table */}
      <div className="overflow-auto flex-1">
        <table className="w-full divide-y divide-gray-200 dark:divide-gray-700" style={{ tableLayout: 'fixed' }}>
          <colgroup>
            <col style={{ width: '40px' }} />
            <col style={{ width: '80px' }} />
            <col style={{ width: '50px' }} />
            <col style={{ width: '280px' }} />
            <col style={{ width: '200px' }} />
            <col style={{ width: '100px' }} />
            <col style={{ width: '160px' }} />
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
              <th style={{ width: '80px' }} className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                <FilterDropdown field="severity" options={uniqueSeverities} currentValue={filters.severity} label="Severity" />
              </th>
              <th
                style={{ width: '50px' }}
                className="px-2 py-2 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
                onClick={() => handleSort('occurrence_count')}
              >
                <div className="flex items-center justify-center gap-1">
                  #
                  <SortIcon columnKey="occurrence_count" />
                </div>
              </th>
              <th style={{ width: '250px' }} className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Alert
              </th>
              <th style={{ width: '180px' }} className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                <FilterDropdown field="device_name" options={uniqueDevices} currentValue={filters.device_name} label="Device" />
              </th>
              <th style={{ width: '100px' }} className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                <FilterDropdown field="category" options={uniqueCategories} currentValue={filters.category} label="Category" />
              </th>
              <th
                style={{ width: '160px' }}
                className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
                onClick={() => handleSort('occurred_at')}
              >
                <div className="flex items-center gap-1">
                  First Seen
                  <SortIcon columnKey="occurred_at" />
                </div>
              </th>
              <th
                style={{ width: '70px' }}
                className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
                onClick={() => handleSort('occurred_at')}
              >
                <div className="flex items-center gap-1">
                  Age
                  <SortIcon columnKey="occurred_at" />
                </div>
              </th>
              <th style={{ width: '90px' }} className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Status
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
                  <td className="px-3 py-2 font-mono text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                    {(() => {
                      const now = new Date();
                      const occurred = new Date(alert.occurred_at);
                      const diffMs = now - occurred;
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
      </div>

      {/* Pagination */}
      {pagination.pages > 1 && (
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
