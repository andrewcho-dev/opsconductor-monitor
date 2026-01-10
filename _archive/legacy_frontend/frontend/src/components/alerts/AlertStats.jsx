/**
 * Alert Statistics Cards
 * 
 * Clickable cards that filter alerts by severity.
 * Shows active/ack/supp counts per severity in red/blue/orange.
 */

import { SEVERITY_CONFIG } from '../../lib/constants';

export function AlertStats({ stats = {}, activeFilter, onFilterChange }) {
  const {
    total_active = 0,
    by_severity = {},
    by_severity_status = {},
    by_status = {},
  } = stats;

  const severityCounts = [
    { 
      key: 'critical', 
      ...SEVERITY_CONFIG.critical, 
      total: by_severity.critical || 0,
      active: by_severity_status.critical?.active || 0,
      acknowledged: by_severity_status.critical?.acknowledged || 0,
      suppressed: by_severity_status.critical?.suppressed || 0,
    },
    { 
      key: 'major', 
      ...SEVERITY_CONFIG.major, 
      total: by_severity.major || 0,
      active: by_severity_status.major?.active || 0,
      acknowledged: by_severity_status.major?.acknowledged || 0,
      suppressed: by_severity_status.major?.suppressed || 0,
    },
    { 
      key: 'minor', 
      ...SEVERITY_CONFIG.minor, 
      total: by_severity.minor || 0,
      active: by_severity_status.minor?.active || 0,
      acknowledged: by_severity_status.minor?.acknowledged || 0,
      suppressed: by_severity_status.minor?.suppressed || 0,
    },
    { 
      key: 'warning', 
      ...SEVERITY_CONFIG.warning, 
      total: by_severity.warning || 0,
      active: by_severity_status.warning?.active || 0,
      acknowledged: by_severity_status.warning?.acknowledged || 0,
      suppressed: by_severity_status.warning?.suppressed || 0,
    },
    { 
      key: 'info', 
      ...SEVERITY_CONFIG.info, 
      total: by_severity.info || 0,
      active: by_severity_status.info?.active || 0,
      acknowledged: by_severity_status.info?.acknowledged || 0,
      suppressed: by_severity_status.info?.suppressed || 0,
    },
  ];

  // Parse active filters (comma-separated string or null)
  const activeFilters = activeFilter ? activeFilter.split(',') : [];

  const handleClick = (severity) => {
    if (!onFilterChange) return;
    
    if (severity === null) {
      // "All Active" clicked - clear all filters
      onFilterChange(null);
      return;
    }

    // Toggle this severity in the filter list
    let newFilters;
    if (activeFilters.includes(severity)) {
      // Remove it
      newFilters = activeFilters.filter(s => s !== severity);
    } else {
      // Add it
      newFilters = [...activeFilters, severity];
    }

    // If empty, set to null; otherwise join with comma
    onFilterChange(newFilters.length > 0 ? newFilters.join(',') : null);
  };

  const isActive = (severity) => activeFilters.includes(severity);

  return (
    <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
      {severityCounts.map(({ key, label, bgClass, textClass, total, active, acknowledged, suppressed }) => {
        const cardActive = activeFilters.includes(key);
        // Background colors for each severity
        const severityBg = key === 'critical' ? 'bg-red-100 dark:bg-red-900/30' 
          : key === 'major' ? 'bg-orange-100 dark:bg-orange-900/30' 
          : key === 'minor' ? 'bg-yellow-100 dark:bg-yellow-900/30' 
          : key === 'warning' ? 'bg-blue-100 dark:bg-blue-900/30' 
          : 'bg-gray-100 dark:bg-gray-800';
        const borderColor = key === 'critical' ? 'border-l-red-500' 
          : key === 'major' ? 'border-l-orange-500' 
          : key === 'minor' ? 'border-l-yellow-500' 
          : key === 'warning' ? 'border-l-blue-500' 
          : 'border-l-gray-400';
        // Lighter status colors
        const activeColor = active > 0 ? 'text-red-400' : 'text-gray-300';
        const ackColor = acknowledged > 0 ? 'text-blue-400' : 'text-gray-300';
        const suppColor = suppressed > 0 ? 'text-orange-400' : 'text-gray-300';
        
        return (
          <button
            key={key}
            onClick={() => handleClick(key)}
            className={`rounded-lg border border-l-4 ${borderColor} px-3 py-2 text-left transition-all ${severityBg} ${
              cardActive 
                ? 'ring-2 ring-offset-1 ring-blue-500' 
                : 'hover:opacity-80'
            }`}
          >
            <div className="min-w-0">
              <p className={`text-xs font-semibold truncate ${textClass}`}>
                {label}
              </p>
              <div className="flex items-baseline gap-1">
                <span className={`text-xl font-bold ${activeColor}`}>
                  {active}
                </span>
                <span className="text-xl font-bold text-gray-300">/</span>
                <span className={`text-xl font-bold ${ackColor}`}>
                  {acknowledged}
                </span>
                <span className="text-xl font-bold text-gray-300">/</span>
                <span className={`text-xl font-bold ${suppColor}`}>
                  {suppressed}
                </span>
              </div>
            </div>
          </button>
        );
      })}
      
      {/* All */}
      <button
        onClick={() => handleClick(null)}
        className={`rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2 text-left transition-all ${
          activeFilters.length === 0 
            ? 'ring-2 ring-offset-1 ring-blue-500 bg-gray-100 dark:bg-gray-700' 
            : 'bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700'
        }`}
      >
        <div className="min-w-0">
          <p className="text-xs font-semibold text-gray-600 dark:text-gray-300 truncate">
            All
          </p>
          <div className="flex items-baseline gap-1">
            <span className={`text-xl font-bold ${(by_status.active || 0) > 0 ? 'text-red-400' : 'text-gray-300'}`}>
              {by_status.active || 0}
            </span>
            <span className="text-xl font-bold text-gray-300">/</span>
            <span className={`text-xl font-bold ${(by_status.acknowledged || 0) > 0 ? 'text-blue-400' : 'text-gray-300'}`}>
              {by_status.acknowledged || 0}
            </span>
            <span className="text-xl font-bold text-gray-300">/</span>
            <span className={`text-xl font-bold ${(by_status.suppressed || 0) > 0 ? 'text-orange-400' : 'text-gray-300'}`}>
              {by_status.suppressed || 0}
            </span>
          </div>
        </div>
      </button>
    </div>
  );
}

export default AlertStats;
