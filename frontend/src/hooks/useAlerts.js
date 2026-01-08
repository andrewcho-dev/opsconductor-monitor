/**
 * Alert Hooks
 * 
 * React hooks for fetching and managing alerts.
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchApi } from '../lib/utils';

/**
 * Hook to fetch alerts with filtering, pagination, and real-time updates
 */
export function useAlerts(initialFilters = {}, { infiniteScroll = false } = {}) {
  const [alerts, setAlerts] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    status: 'active,acknowledged,suppressed',  // Default: show all non-resolved
    severity: null,
    category: null,
    device_ip: null,
    source_system: null,
    search: null,
    ...initialFilters,
  });
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 50,
    total: 0,
    pages: 0,
  });

  const fetchAlerts = useCallback(async (isLoadMore = false) => {
    if (isLoadMore) {
      setLoadingMore(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      // Build query params
      const params = new URLSearchParams();
      
      if (filters.status && filters.status !== 'all') {
        params.set('status', filters.status);
      }
      if (filters.severity) {
        params.set('severity', Array.isArray(filters.severity) ? filters.severity.join(',') : filters.severity);
      }
      if (filters.category) {
        params.set('category', Array.isArray(filters.category) ? filters.category.join(',') : filters.category);
      }
      if (filters.device_ip) {
        params.set('device_ip', filters.device_ip);
      }
      if (filters.source_system) {
        params.set('source_system', filters.source_system);
      }
      if (filters.search) {
        params.set('search', filters.search);
      }
      
      params.set('page', pagination.page.toString());
      params.set('per_page', pagination.per_page.toString());

      const response = await fetchApi(`/api/v1/alerts?${params.toString()}`);
      
      if (response.success) {
        if (infiniteScroll && isLoadMore) {
          // Append to existing alerts for infinite scroll
          setAlerts(prev => [...prev, ...(response.data || [])]);
        } else {
          // Replace alerts
          setAlerts(response.data || []);
        }
        setPagination(prev => ({
          ...prev,
          total: response.meta?.total || 0,
          pages: response.meta?.pages || 0,
        }));
      } else {
        setError(response.error?.message || 'Failed to fetch alerts');
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch alerts');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [filters, pagination.page, pagination.per_page, infiniteScroll]);

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetchApi('/api/v1/alerts/stats');
      if (response.success) {
        setStats(response.data || {});
      }
    } catch (err) {
      console.error('Failed to fetch alert stats:', err);
    }
  }, []);

  // Fetch alerts when filters or pagination changes
  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  // Fetch stats on mount and periodically
  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000); // Every 30 seconds
    return () => clearInterval(interval);
  }, [fetchStats]);

  const refresh = useCallback(() => {
    if (infiniteScroll) {
      // For infinite scroll, reset to page 1 and clear alerts
      setPagination(prev => ({ ...prev, page: 1 }));
      setAlerts([]);
    }
    fetchAlerts();
    fetchStats();
  }, [fetchAlerts, fetchStats, infiniteScroll]);

  const setPage = useCallback((page) => {
    setPagination(prev => ({ ...prev, page }));
  }, []);

  const loadMore = useCallback(() => {
    if (!loadingMore && pagination.page < pagination.pages) {
      setPagination(prev => ({ ...prev, page: prev.page + 1 }));
    }
  }, [loadingMore, pagination.page, pagination.pages]);

  // For infinite scroll, fetch more when page changes (except page 1)
  useEffect(() => {
    if (infiniteScroll && pagination.page > 1) {
      fetchAlerts(true);
    }
  }, [pagination.page, infiniteScroll]);

  const updateFilters = useCallback((newFilters) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
    setPagination(prev => ({ ...prev, page: 1 })); // Reset to first page
  }, []);

  return {
    alerts,
    stats,
    loading,
    loadingMore,
    error,
    filters,
    setFilters: updateFilters,
    pagination,
    setPage,
    loadMore,
    refresh,
  };
}

/**
 * Hook to fetch a single alert by ID
 */
export function useAlert(alertId) {
  const [alert, setAlert] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAlert = useCallback(async () => {
    if (!alertId) return;
    
    setLoading(true);
    setError(null);

    try {
      const [alertResponse, historyResponse] = await Promise.all([
        fetchApi(`/api/v1/alerts/${alertId}`),
        fetchApi(`/api/v1/alerts/${alertId}/history`),
      ]);

      if (alertResponse.success) {
        setAlert(alertResponse.data);
      } else {
        setError(alertResponse.error?.message || 'Alert not found');
      }

      if (historyResponse.success) {
        setHistory(historyResponse.data || []);
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch alert');
    } finally {
      setLoading(false);
    }
  }, [alertId]);

  useEffect(() => {
    fetchAlert();
  }, [fetchAlert]);

  return { alert, history, loading, error, refresh: fetchAlert };
}

/**
 * Hook for alert actions (acknowledge, resolve, etc.)
 */
export function useAlertActions() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const acknowledgeAlert = useCallback(async (alertId, notes = '') => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchApi(`/api/v1/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        body: JSON.stringify({ notes }),
      });

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to acknowledge');
      }

      return response.data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const resolveAlert = useCallback(async (alertId, notes = '') => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchApi(`/api/v1/alerts/${alertId}/resolve`, {
        method: 'POST',
        body: JSON.stringify({ notes }),
      });

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to resolve');
      }

      return response.data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const addNote = useCallback(async (alertId, notes) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchApi(`/api/v1/alerts/${alertId}/notes`, {
        method: 'POST',
        body: JSON.stringify({ notes }),
      });

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to add note');
      }

      return response.data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const bulkAcknowledge = useCallback(async (alertIds, notes = '') => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchApi('/api/v1/alerts/bulk/acknowledge', {
        method: 'POST',
        body: JSON.stringify({ alert_ids: alertIds, notes }),
      });

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to acknowledge');
      }

      return response.data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const bulkResolve = useCallback(async (alertIds, notes = '') => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchApi('/api/v1/alerts/bulk/resolve', {
        method: 'POST',
        body: JSON.stringify({ alert_ids: alertIds, notes }),
      });

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to resolve');
      }

      return response.data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    acknowledgeAlert,
    resolveAlert,
    addNote,
    bulkAcknowledge,
    bulkResolve,
  };
}

export default useAlerts;
