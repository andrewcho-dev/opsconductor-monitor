/**
 * Generic API hook for data fetching.
 * 
 * Provides standardized loading, error, and data states.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Hook for fetching data from an API
 * @param {Function} fetchFn - Async function that fetches data
 * @param {Array} deps - Dependencies that trigger refetch
 * @param {Object} options - Options
 * @param {boolean} options.immediate - Fetch immediately on mount (default: true)
 * @param {any} options.initialData - Initial data value
 * @returns {Object} { data, loading, error, refetch, setData }
 */
export function useApi(fetchFn, deps = [], options = {}) {
  const { immediate = true, initialData = null } = options;
  
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);
  
  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await fetchFn();
      if (mountedRef.current) {
        setData(result);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err);
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [fetchFn]);
  
  useEffect(() => {
    mountedRef.current = true;
    if (immediate) {
      fetch();
    }
    return () => {
      mountedRef.current = false;
    };
  }, [...deps, immediate]);
  
  return { data, loading, error, refetch: fetch, setData };
}

/**
 * Hook for fetching list data with count
 * @param {Function} fetchFn - Async function that returns { data, count }
 * @param {Array} deps - Dependencies
 * @param {Object} options - Options
 * @returns {Object} { data, count, loading, error, refetch }
 */
export function useApiList(fetchFn, deps = [], options = {}) {
  const { immediate = true } = options;
  
  const [data, setData] = useState([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);
  
  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await fetchFn();
      if (mountedRef.current) {
        setData(result.data || []);
        setCount(result.count || result.data?.length || 0);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err);
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [fetchFn]);
  
  useEffect(() => {
    mountedRef.current = true;
    if (immediate) {
      fetch();
    }
    return () => {
      mountedRef.current = false;
    };
  }, [...deps, immediate]);
  
  return { data, count, loading, error, refetch: fetch, setData };
}

/**
 * Hook for mutations (create, update, delete)
 * @param {Function} mutationFn - Async function that performs mutation
 * @param {Object} options - Options
 * @param {Function} options.onSuccess - Callback on success
 * @param {Function} options.onError - Callback on error
 * @returns {Object} { mutate, loading, error, data }
 */
export function useMutation(mutationFn, options = {}) {
  const { onSuccess, onError } = options;
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  
  const mutate = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await mutationFn(...args);
      setData(result);
      if (onSuccess) {
        onSuccess(result);
      }
      return result;
    } catch (err) {
      setError(err);
      if (onError) {
        onError(err);
      }
      throw err;
    } finally {
      setLoading(false);
    }
  }, [mutationFn, onSuccess, onError]);
  
  return { mutate, loading, error, data };
}

export default { useApi, useApiList, useMutation };
