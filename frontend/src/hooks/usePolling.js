/**
 * Polling hook for periodic data fetching.
 * 
 * Useful for dashboards and real-time data displays.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Hook for polling data at regular intervals
 * @param {Function} fetchFn - Async function that fetches data
 * @param {number} interval - Polling interval in milliseconds
 * @param {Object} options - Options
 * @param {boolean} options.enabled - Whether polling is enabled (default: true)
 * @param {boolean} options.immediate - Fetch immediately on mount (default: true)
 * @param {any} options.initialData - Initial data value
 * @returns {Object} { data, loading, error, refetch, isPolling, startPolling, stopPolling }
 */
export function usePolling(fetchFn, interval = 5000, options = {}) {
  const { enabled = true, immediate = true, initialData = null } = options;
  
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState(null);
  const [isPolling, setIsPolling] = useState(enabled);
  
  const mountedRef = useRef(true);
  const intervalRef = useRef(null);
  const fetchFnRef = useRef(fetchFn);
  
  // Keep fetchFn ref updated
  useEffect(() => {
    fetchFnRef.current = fetchFn;
  }, [fetchFn]);
  
  const fetch = useCallback(async (showLoading = false) => {
    if (showLoading) {
      setLoading(true);
    }
    setError(null);
    
    try {
      const result = await fetchFnRef.current();
      if (mountedRef.current) {
        setData(result);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err);
      }
    } finally {
      if (mountedRef.current && showLoading) {
        setLoading(false);
      }
    }
  }, []);
  
  const startPolling = useCallback(() => {
    setIsPolling(true);
  }, []);
  
  const stopPolling = useCallback(() => {
    setIsPolling(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);
  
  // Initial fetch
  useEffect(() => {
    mountedRef.current = true;
    if (immediate) {
      fetch(true);
    }
    return () => {
      mountedRef.current = false;
    };
  }, [immediate, fetch]);
  
  // Polling effect
  useEffect(() => {
    if (isPolling && interval > 0) {
      intervalRef.current = setInterval(() => {
        fetch(false);
      }, interval);
      
      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      };
    }
  }, [isPolling, interval, fetch]);
  
  return {
    data,
    loading,
    error,
    refetch: () => fetch(true),
    isPolling,
    startPolling,
    stopPolling,
    setData,
  };
}

/**
 * Hook for polling list data
 * @param {Function} fetchFn - Async function that returns { data, count }
 * @param {number} interval - Polling interval in milliseconds
 * @param {Object} options - Options
 * @returns {Object} { data, count, loading, error, refetch, isPolling, startPolling, stopPolling }
 */
export function usePollingList(fetchFn, interval = 5000, options = {}) {
  const { enabled = true, immediate = true } = options;
  
  const [data, setData] = useState([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState(null);
  const [isPolling, setIsPolling] = useState(enabled);
  
  const mountedRef = useRef(true);
  const intervalRef = useRef(null);
  const fetchFnRef = useRef(fetchFn);
  
  useEffect(() => {
    fetchFnRef.current = fetchFn;
  }, [fetchFn]);
  
  const fetch = useCallback(async (showLoading = false) => {
    if (showLoading) {
      setLoading(true);
    }
    setError(null);
    
    try {
      const result = await fetchFnRef.current();
      if (mountedRef.current) {
        setData(result.data || []);
        setCount(result.count || result.data?.length || 0);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err);
      }
    } finally {
      if (mountedRef.current && showLoading) {
        setLoading(false);
      }
    }
  }, []);
  
  const startPolling = useCallback(() => {
    setIsPolling(true);
  }, []);
  
  const stopPolling = useCallback(() => {
    setIsPolling(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);
  
  useEffect(() => {
    mountedRef.current = true;
    if (immediate) {
      fetch(true);
    }
    return () => {
      mountedRef.current = false;
    };
  }, [immediate, fetch]);
  
  useEffect(() => {
    if (isPolling && interval > 0) {
      intervalRef.current = setInterval(() => {
        fetch(false);
      }, interval);
      
      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      };
    }
  }, [isPolling, interval, fetch]);
  
  return {
    data,
    count,
    loading,
    error,
    refetch: () => fetch(true),
    isPolling,
    startPolling,
    stopPolling,
    setData,
  };
}

export default { usePolling, usePollingList };
