/**
 * Alert Filters Component
 */

import { useState } from 'react';
import { Search, Filter, X } from 'lucide-react';
import { SEVERITY_CONFIG, CATEGORY_CONFIG, STATUS_CONFIG } from '../../lib/constants';

export function AlertFilters({ filters, onChange }) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [searchValue, setSearchValue] = useState(filters.search || '');

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    onChange({ search: searchValue || null });
  };

  const handleStatusChange = (status) => {
    onChange({ status });
  };

  const handleSeverityChange = (severity) => {
    const current = filters.severity ? filters.severity.split(',') : [];
    let newSeverities;
    
    if (current.includes(severity)) {
      newSeverities = current.filter(s => s !== severity);
    } else {
      newSeverities = [...current, severity];
    }
    
    onChange({ severity: newSeverities.length > 0 ? newSeverities.join(',') : null });
  };

  const handleCategoryChange = (category) => {
    const current = filters.category ? filters.category.split(',') : [];
    let newCategories;
    
    if (current.includes(category)) {
      newCategories = current.filter(c => c !== category);
    } else {
      newCategories = [...current, category];
    }
    
    onChange({ category: newCategories.length > 0 ? newCategories.join(',') : null });
  };

  const clearFilters = () => {
    setSearchValue('');
    onChange({
      status: 'active',
      severity: null,
      category: null,
      search: null,
      device_ip: null,
      source_system: null,
    });
  };

  const hasActiveFilters = filters.severity || filters.category || filters.search || filters.device_ip;

  return (
    <div className="space-y-4">
      {/* Top row: Search and Status tabs */}
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search alerts..."
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </form>

        {/* Status Tabs */}
        <div className="flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden">
          {['active', 'acknowledged', 'all'].map((status) => (
            <button
              key={status}
              onClick={() => handleStatusChange(status)}
              className={`px-4 py-2 text-sm font-medium capitalize ${
                filters.status === status
                  ? 'bg-blue-600 text-white'
                  : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              {status}
            </button>
          ))}
        </div>

        {/* Toggle Advanced */}
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
            hasActiveFilters
              ? 'border-blue-500 text-blue-600 bg-blue-50 dark:bg-blue-900/20'
              : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300'
          }`}
        >
          <Filter className="h-4 w-4" />
          Filters
          {hasActiveFilters && (
            <span className="bg-blue-600 text-white text-xs px-1.5 py-0.5 rounded-full">
              !
            </span>
          )}
        </button>
      </div>

      {/* Advanced Filters */}
      {showAdvanced && (
        <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-medium text-gray-900 dark:text-white">Advanced Filters</h3>
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
              >
                <X className="h-3 w-3" />
                Clear all
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Severity */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Severity
              </label>
              <div className="flex flex-wrap gap-2">
                {Object.entries(SEVERITY_CONFIG)
                  .filter(([key]) => key !== 'clear')
                  .map(([key, { label, badgeClass }]) => {
                    const isSelected = filters.severity?.includes(key);
                    return (
                      <button
                        key={key}
                        onClick={() => handleSeverityChange(key)}
                        className={`px-3 py-1 rounded-full text-sm font-medium ${
                          isSelected ? badgeClass : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                        }`}
                      >
                        {label}
                      </button>
                    );
                  })}
              </div>
            </div>

            {/* Category */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Category
              </label>
              <div className="flex flex-wrap gap-2">
                {Object.entries(CATEGORY_CONFIG)
                  .filter(([key]) => key !== 'unknown')
                  .map(([key, { label }]) => {
                    const isSelected = filters.category?.includes(key);
                    return (
                      <button
                        key={key}
                        onClick={() => handleCategoryChange(key)}
                        className={`px-3 py-1 rounded-full text-sm font-medium ${
                          isSelected
                            ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                            : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                        }`}
                      >
                        {label}
                      </button>
                    );
                  })}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AlertFilters;
