/**
 * Connector Hooks
 * 
 * React hooks for managing connectors.
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchApi } from '../lib/utils';

/**
 * Hook to fetch and manage connectors
 */
export function useConnectors() {
  const [connectors, setConnectors] = useState([]);
  const [connectorTypes, setConnectorTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchConnectors = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchApi('/api/v1/connectors');
      if (response.success) {
        setConnectors(response.data || []);
      } else {
        setError(response.error?.message || 'Failed to fetch connectors');
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch connectors');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchTypes = useCallback(async () => {
    try {
      const response = await fetchApi('/api/v1/connectors/types');
      if (response.success) {
        setConnectorTypes(response.data || []);
      }
    } catch (err) {
      console.error('Failed to fetch connector types:', err);
    }
  }, []);

  useEffect(() => {
    fetchConnectors();
    fetchTypes();
  }, [fetchConnectors, fetchTypes]);

  const refresh = useCallback(() => {
    fetchConnectors();
  }, [fetchConnectors]);

  return {
    connectors,
    connectorTypes,
    loading,
    error,
    refresh,
  };
}

/**
 * Hook to fetch a single connector
 */
export function useConnector(connectorId) {
  const [connector, setConnector] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchConnector = useCallback(async () => {
    if (!connectorId) return;
    
    setLoading(true);
    setError(null);

    try {
      const response = await fetchApi(`/api/v1/connectors/${connectorId}`);
      if (response.success) {
        setConnector(response.data);
      } else {
        setError(response.error?.message || 'Connector not found');
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch connector');
    } finally {
      setLoading(false);
    }
  }, [connectorId]);

  useEffect(() => {
    fetchConnector();
  }, [fetchConnector]);

  return { connector, loading, error, refresh: fetchConnector };
}

/**
 * Hook for connector actions
 */
export function useConnectorActions() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const testConnection = useCallback(async (connectorId) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchApi(`/api/v1/connectors/${connectorId}/test`, {
        method: 'POST',
        timeout: 30000, // 30 seconds for SSH-based connectors
      });

      return response;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const enableConnector = useCallback(async (connectorId) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchApi(`/api/v1/connectors/${connectorId}/enable`, {
        method: 'POST',
      });

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to enable');
      }

      return response;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const disableConnector = useCallback(async (connectorId) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchApi(`/api/v1/connectors/${connectorId}/disable`, {
        method: 'POST',
      });

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to disable');
      }

      return response;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateConnector = useCallback(async (connectorId, data) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchApi(`/api/v1/connectors/${connectorId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });

      if (!response.success) {
        throw new Error(response.error?.message || 'Failed to update');
      }

      return response.data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const pollConnector = useCallback(async (connectorId) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchApi(`/api/v1/connectors/${connectorId}/poll`, {
        method: 'POST',
        timeout: 60000, // 60 seconds for polling
      });

      return response;
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
    testConnection,
    enableConnector,
    disableConnector,
    updateConnector,
    pollConnector,
  };
}

export default useConnectors;
