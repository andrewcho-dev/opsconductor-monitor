/**
 * Resolved Alerts Page
 * 
 * Shows historical resolved alerts using the same AlertTable component
 * as the main dashboard for consistency.
 */

import { useState, useEffect, useCallback } from 'react';
import { RefreshCw } from 'lucide-react';
import { PageLayout } from '../components/layout/PageLayout';
import { AlertTable } from '../components/alerts';
import { fetchApi } from '../lib/utils';
import { useAlertWebSocketRefresh } from '../hooks/useAlertWebSocket';

export function ResolvedAlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    status: 'resolved',
  });
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 50,
    total: 0,
    pages: 0,
  });

  const fetchResolvedAlerts = useCallback(async (isLoadMore = false) => {
    if (isLoadMore) {
      setLoadingMore(true);
    } else {
      setLoading(true);
    }
    try {
      const params = new URLSearchParams();
      params.set('status', 'resolved');
      params.set('page', pagination.page);
      params.set('per_page', pagination.per_page);
      
      if (filters.severity) params.set('severity', filters.severity);
      if (filters.category) params.set('category', filters.category);
      if (filters.device_name) params.set('device_name', filters.device_name);
      
      const response = await fetchApi(`/api/v1/alerts?${params.toString()}`);
      
      if (isLoadMore) {
        // Append for infinite scroll
        setAlerts(prev => [...prev, ...(response.data || [])]);
      } else {
        setAlerts(response.data || []);
      }
      
      setPagination(prev => ({
        ...prev,
        total: response.meta?.total || 0,
        pages: response.meta?.pages || 0,
      }));
      
      // Build stats for resolved alerts only
      const resolvedStats = {
        by_status: { resolved: response.meta?.total || 0 },
        by_severity_status: {},
      };
      setStats(resolvedStats);
      
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to fetch resolved alerts');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [pagination.page, pagination.per_page, filters.severity, filters.category, filters.device_name]);

  // Initial fetch
  useEffect(() => {
    if (pagination.page === 1) {
      fetchResolvedAlerts();
    }
  }, [filters.severity, filters.category, filters.device_name]);

  // Load more when page changes (for infinite scroll)
  useEffect(() => {
    if (pagination.page > 1) {
      fetchResolvedAlerts(true);
    }
  }, [pagination.page]);

  // WebSocket for real-time updates
  const { isConnected } = useAlertWebSocketRefresh(() => {
    setPagination(prev => ({ ...prev, page: 1 }));
    setAlerts([]);
    fetchResolvedAlerts();
  });

  const loadMore = useCallback(() => {
    if (!loadingMore && pagination.page < pagination.pages) {
      setPagination(prev => ({ ...prev, page: prev.page + 1 }));
    }
  }, [loadingMore, pagination.page, pagination.pages]);

  const handleFilterChange = (newFilters) => {
    // Keep status as resolved, merge other filters
    setFilters(prev => ({ ...prev, ...newFilters, status: 'resolved' }));
    setPagination(prev => ({ ...prev, page: 1 }));
    setAlerts([]);
  };

  return (
    <PageLayout module="alerts">
      <div className="p-6 h-full flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between mb-4 flex-shrink-0">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Resolved Alerts
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Historical record of cleared and resolved alerts
              {isConnected && (
                <span className="ml-2 inline-flex items-center text-green-600">
                  <span className="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse"></span>
                  Live
                </span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">
              {pagination.total} resolved alert{pagination.total !== 1 ? 's' : ''}
            </span>
            <button
              onClick={fetchResolvedAlerts}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded text-sm"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-800 dark:text-red-200 flex-shrink-0">
            {error}
          </div>
        )}

        {/* Alert Table - same component as main dashboard with resolved-specific options */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <AlertTable
            alerts={alerts}
            loading={loading}
            pagination={pagination}
            onLoadMore={loadMore}
            loadingMore={loadingMore}
            selectedIds={[]}
            onSelectChange={() => {}}
            filters={filters}
            onFilterChange={handleFilterChange}
            statusCounts={stats?.by_status || {}}
            severityStatusCounts={stats?.by_severity_status || {}}
            showResolvedTime={true}
            hideStatusPills={true}
          />
        </div>
      </div>
    </PageLayout>
  );
}

export default ResolvedAlertsPage;
