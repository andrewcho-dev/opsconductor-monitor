/**
 * Alert Table Component
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, CheckCheck, ChevronLeft, ChevronRight, MoreHorizontal } from 'lucide-react';
import { SEVERITY_CONFIG, CATEGORY_CONFIG, formatRelativeTime } from '../../lib/constants';

export function AlertTable({
  alerts = [],
  loading = false,
  pagination = {},
  onPageChange,
  onAcknowledge,
  onResolve,
  selectedIds = [],
  onSelectChange,
}) {
  const [expandedId, setExpandedId] = useState(null);

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

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-500">Loading alerts...</span>
        </div>
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8">
        <div className="text-center text-gray-500">
          <p className="text-lg font-medium">No alerts found</p>
          <p className="text-sm">Try adjusting your filters</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-900">
            <tr>
              <th className="w-10 px-4 py-3">
                <input
                  type="checkbox"
                  checked={selectedIds.length === alerts.length && alerts.length > 0}
                  onChange={handleSelectAll}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Severity
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Alert
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Device
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Category
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Time
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {alerts.map((alert) => {
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
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(alert.id)}
                      onChange={() => handleSelectOne(alert.id)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${severityConfig.bgClass}`}></span>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${severityConfig.badgeClass}`}>
                        {severityConfig.label}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      to={`/alerts/${alert.id}`}
                      className="text-sm font-medium text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400"
                    >
                      {alert.title}
                    </Link>
                    {alert.occurrence_count > 1 && (
                      <span className="ml-2 text-xs text-gray-500">
                        ({alert.occurrence_count}x)
                      </span>
                    )}
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-md">
                      {alert.message}
                    </p>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm">
                      <p className="font-medium text-gray-900 dark:text-white">
                        {alert.device_name || alert.device_ip || '-'}
                      </p>
                      {alert.device_name && alert.device_ip && (
                        <p className="text-xs text-gray-500">{alert.device_ip}</p>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <CategoryIcon className="h-4 w-4 text-gray-400" />
                      <span className="text-sm text-gray-600 dark:text-gray-300">
                        {categoryConfig.label}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                    {formatRelativeTime(alert.occurred_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {alert.status === 'active' && (
                        <button
                          onClick={() => onAcknowledge?.(alert.id)}
                          className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
                          title="Acknowledge"
                        >
                          <Check className="h-4 w-4" />
                        </button>
                      )}
                      {(alert.status === 'active' || alert.status === 'acknowledged') && (
                        <button
                          onClick={() => onResolve?.(alert.id)}
                          className="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded"
                          title="Resolve"
                        >
                          <CheckCheck className="h-4 w-4" />
                        </button>
                      )}
                    </div>
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
