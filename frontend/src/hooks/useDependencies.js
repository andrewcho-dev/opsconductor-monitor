/**
 * Dependencies Hooks
 * 
 * React hooks for managing device dependencies.
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchApi } from '../lib/utils';

/**
 * Hook to fetch and manage dependencies
 */
export function useDependencies(initialFilters = {}) {
  const [dependencies, setDependencies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    device_ip: null,
    depends_on_ip: null,
    type: null,
    ...initialFilters,
  });
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 100,
    total: 0,
    pages: 0,
  });

  const fetchDependencies = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      
      if (filters.device_ip) {
        params.set('device_ip', filters.device_ip);
      }
      if (filters.depends_on_ip) {
        params.set('depends_on_ip', filters.depends_on_ip);
      }
      if (filters.type) {
        params.set('type', filters.type);
      }
      
      params.set('page', pagination.page.toString());
      params.set('per_page', pagination.per_page.toString());

      const response = await fetchApi(`/api/v1/dependencies?${params.toString()}`);
      
      if (response.success) {
        setDependencies(response.data || []);
        setPagination(prev => ({
          ...prev,
          total: response.meta?.total || 0,
          pages: response.meta?.pages || 0,
        }));
      } else {
        setError(response.error?.message || 'Failed to fetch dependencies');
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch dependencies');
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.page, pagination.per_page]);

  useEffect(() => {
    fetchDependencies();
  }, [fetchDependencies]);

  const refresh = useCallback(() => {
    fetchDependencies();
  }, [fetchDependencies]);

  const setPage = useCallback((page) => {
    setPagination(prev => ({ ...prev, page }));
  }, []);

  const updateFilters = useCallback((newFilters) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
    setPagination(prev => ({ ...prev, page: 1 }));
  }, []);

  return {
    dependencies,
    loading,
    error,
    filters,
    setFilters: updateFilters,
    pagination,
    setPage,
    refresh,
  };
}

/**
 * Hook to get dependencies for a specific device
 */
export function useDeviceDependencies(deviceIp) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    if (!deviceIp) return;
    
    setLoading(true);
    setError(null);

    try {
      const response = await fetchApi(`/api/v1/dependencies/device/${encodeURIComponent(deviceIp)}`);
      if (response.success) {
        setData(response.data);
      } else {
        setError(response.error?.message || 'Failed to fetch');
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch');
    } finally {
      setLoading(false);
    }
  }, [deviceIp]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refresh: fetchData };
}

/**
 * Hook for dependency actions
 */
export function useDependencyActions() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const createDependency = useCallback(async (data) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchApi('/api/v1/dependencies', {
        method: 'POST',
        body: JSON.stringify(data),
      });

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to create');
      }

      return response.data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteDependency = useCallback(async (dependencyId) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchApi(`/api/v1/dependencies/${dependencyId}`, {
        method: 'DELETE',
      });

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to delete');
      }

      return true;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const bulkCreate = useCallback(async (dependencies) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchApi('/api/v1/dependencies/bulk', {
        method: 'POST',
        body: JSON.stringify({ dependencies }),
      });

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to create');
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
    createDependency,
    deleteDependency,
    bulkCreate,
  };
}

export default useDependencies;
