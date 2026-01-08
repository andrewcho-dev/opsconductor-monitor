/**
 * Alert Dashboard Page
 * 
 * Main alert monitoring interface.
 */

import { useState, useEffect } from 'react';
import { RefreshCw, Wifi, WifiOff } from 'lucide-react';
import { useAlerts } from '../hooks/useAlerts';
import { AlertStats, AlertTable } from '../components/alerts';
import { PageLayout } from '../components/layout/PageLayout';
import { useAlertWebSocketRefresh } from '../hooks/useAlertWebSocket';

export function AlertDashboard() {
  const {
    alerts,
    stats,
    loading,
    loadingMore,
    error,
    filters,
    setFilters,
    pagination,
    loadMore,
    refresh,
  } = useAlerts({}, { infiniteScroll: true });

  // Real-time WebSocket updates - automatically refreshes when alerts change
  const { isConnected } = useAlertWebSocketRefresh(refresh);
  
  const [selectedIds, setSelectedIds] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [secondsAgo, setSecondsAgo] = useState(0);

  // Update lastUpdated when alerts change
  useEffect(() => {
    if (alerts?.length >= 0) {
      setLastUpdated(new Date());
    }
  }, [alerts]);

  // Update seconds ago counter
  useEffect(() => {
    const interval = setInterval(() => {
      setSecondsAgo(Math.floor((Date.now() - lastUpdated.getTime()) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [lastUpdated]);

  return (
    <PageLayout module="alerts">
      <div className="p-6 h-full flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between mb-4 flex-shrink-0">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Alert Dashboard
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Monitor and manage alerts from all connected systems
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* Real-time connection status and last updated */}
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${
              isConnected 
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' 
                : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
            }`}>
              {isConnected ? (
                <Wifi className="h-3.5 w-3.5" />
              ) : (
                <WifiOff className="h-3.5 w-3.5" />
              )}
              <span>
                {secondsAgo < 5 ? 'Just now' : `${secondsAgo}s ago`}
              </span>
              <button
                onClick={refresh}
                disabled={loading}
                className="p-0.5 hover:bg-green-200 dark:hover:bg-green-800 rounded transition-colors"
                title="Refresh now"
              >
                <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>

        {/* Stats - clickable to filter by severity */}
        <div className="mb-4 flex-shrink-0">
          <AlertStats 
            stats={stats} 
            activeFilter={filters.severity}
            onFilterChange={(severity) => setFilters({ severity })}
          />
        </div>

        {/* Selection info */}
        {selectedIds.length > 0 && (
          <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg flex items-center justify-between flex-shrink-0">
            <span className="text-sm text-blue-800 dark:text-blue-200">
              {selectedIds.length} alert{selectedIds.length !== 1 ? 's' : ''} selected
            </span>
            <button
              onClick={() => setSelectedIds([])}
              className="px-3 py-1.5 text-gray-600 dark:text-gray-300 text-sm hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
            >
              Clear Selection
            </button>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-800 dark:text-red-200 flex-shrink-0">
            {error}
          </div>
        )}

        {/* Alert Table */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <AlertTable
            alerts={alerts}
            loading={loading}
            pagination={pagination}
            onLoadMore={loadMore}
            loadingMore={loadingMore}
            selectedIds={selectedIds}
            onSelectChange={setSelectedIds}
            filters={filters}
            onFilterChange={setFilters}
            statusCounts={stats?.by_status || {}}
            severityStatusCounts={stats?.by_severity_status || {}}
          />
        </div>
      </div>
    </PageLayout>
  );
}

export default AlertDashboard;
