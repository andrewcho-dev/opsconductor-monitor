/**
 * Alert Dashboard Page
 * 
 * Main alert monitoring interface.
 */

import { useState, useCallback } from 'react';
import { RefreshCw, Check, CheckCheck } from 'lucide-react';
import { useAlerts, useAlertActions } from '../hooks/useAlerts';
import { AlertStats, AlertFilters, AlertTable } from '../components/alerts';

export function AlertDashboard() {
  const {
    alerts,
    stats,
    loading,
    error,
    filters,
    setFilters,
    pagination,
    setPage,
    refresh,
  } = useAlerts();

  const { acknowledgeAlert, resolveAlert, bulkAcknowledge, bulkResolve, loading: actionLoading } = useAlertActions();
  
  const [selectedIds, setSelectedIds] = useState([]);

  const handleAcknowledge = useCallback(async (alertId) => {
    try {
      await acknowledgeAlert(alertId);
      refresh();
    } catch (err) {
      console.error('Failed to acknowledge:', err);
    }
  }, [acknowledgeAlert, refresh]);

  const handleResolve = useCallback(async (alertId) => {
    try {
      await resolveAlert(alertId);
      refresh();
    } catch (err) {
      console.error('Failed to resolve:', err);
    }
  }, [resolveAlert, refresh]);

  const handleBulkAcknowledge = useCallback(async () => {
    if (selectedIds.length === 0) return;
    try {
      await bulkAcknowledge(selectedIds);
      setSelectedIds([]);
      refresh();
    } catch (err) {
      console.error('Failed to bulk acknowledge:', err);
    }
  }, [selectedIds, bulkAcknowledge, refresh]);

  const handleBulkResolve = useCallback(async () => {
    if (selectedIds.length === 0) return;
    try {
      await bulkResolve(selectedIds);
      setSelectedIds([]);
      refresh();
    } catch (err) {
      console.error('Failed to bulk resolve:', err);
    }
  }, [selectedIds, bulkResolve, refresh]);

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Alert Dashboard
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Monitor and manage alerts from all connected systems
            </p>
          </div>
          <button
            onClick={refresh}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Stats */}
        <div className="mb-6">
          <AlertStats stats={stats} />
        </div>

        {/* Filters */}
        <div className="mb-6">
          <AlertFilters filters={filters} onChange={setFilters} />
        </div>

        {/* Bulk Actions */}
        {selectedIds.length > 0 && (
          <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg flex items-center justify-between">
            <span className="text-sm text-blue-800 dark:text-blue-200">
              {selectedIds.length} alert{selectedIds.length !== 1 ? 's' : ''} selected
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={handleBulkAcknowledge}
                disabled={actionLoading}
                className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
              >
                <Check className="h-4 w-4" />
                Acknowledge
              </button>
              <button
                onClick={handleBulkResolve}
                disabled={actionLoading}
                className="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50"
              >
                <CheckCheck className="h-4 w-4" />
                Resolve
              </button>
              <button
                onClick={() => setSelectedIds([])}
                className="px-3 py-1.5 text-gray-600 dark:text-gray-300 text-sm hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
              >
                Clear
              </button>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-800 dark:text-red-200">
            {error}
          </div>
        )}

        {/* Alert Table */}
        <AlertTable
          alerts={alerts}
          loading={loading}
          pagination={pagination}
          onPageChange={setPage}
          onAcknowledge={handleAcknowledge}
          onResolve={handleResolve}
          selectedIds={selectedIds}
          onSelectChange={setSelectedIds}
        />
      </div>
    </div>
  );
}

export default AlertDashboard;
