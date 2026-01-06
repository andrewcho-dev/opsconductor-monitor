/**
 * Metrics Hooks
 * 
 * React hooks for fetching time-series metrics from the OpsConductor API.
 * These hooks integrate with the new metrics tables for optical, interface,
 * and availability data.
 */

import { useState, useEffect, useCallback } from 'react';

const API_BASE = '/monitoring/v1/metrics';

/**
 * Fetch optical power metrics for a device/interface
 */
export function useOpticalMetrics(deviceIp, interfaceName = null, timeRange = '24h') {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMetrics = useCallback(async () => {
    if (!deviceIp) {
      setData([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      let url = `${API_BASE}/optical?device_ip=${encodeURIComponent(deviceIp)}&range=${timeRange}`;
      if (interfaceName) {
        url += `&interface=${encodeURIComponent(interfaceName)}`;
      }

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      setData(result.data || []);
    } catch (err) {
      setError(err.message);
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [deviceIp, interfaceName, timeRange]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  return { data, loading, error, refetch: fetchMetrics };
}

/**
 * Fetch interface traffic metrics for a device
 */
export function useInterfaceMetrics(deviceIp, interfaceName = null, timeRange = '24h') {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMetrics = useCallback(async () => {
    if (!deviceIp) {
      setData([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      let url = `${API_BASE}/interface?device_ip=${encodeURIComponent(deviceIp)}&range=${timeRange}`;
      if (interfaceName) {
        url += `&interface=${encodeURIComponent(interfaceName)}`;
      }

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      setData(result.data || []);
    } catch (err) {
      setError(err.message);
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [deviceIp, interfaceName, timeRange]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  return { data, loading, error, refetch: fetchMetrics };
}

/**
 * Fetch availability metrics for a device
 */
export function useAvailabilityMetrics(deviceIp, timeRange = '7d') {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMetrics = useCallback(async () => {
    if (!deviceIp) {
      setData([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const url = `${API_BASE}/availability?device_ip=${encodeURIComponent(deviceIp)}&range=${timeRange}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      setData(result.data || []);
    } catch (err) {
      setError(err.message);
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [deviceIp, timeRange]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  return { data, loading, error, refetch: fetchMetrics };
}

/**
 * Fetch metrics summary for a device
 */
export function useDeviceMetricsSummary(deviceIp) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchSummary = useCallback(async () => {
    if (!deviceIp) {
      setSummary(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const url = `${API_BASE}/device/${encodeURIComponent(deviceIp)}/summary`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      setSummary(result);
    } catch (err) {
      setError(err.message);
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, [deviceIp]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  return { summary, loading, error, refetch: fetchSummary };
}

/**
 * Fetch site-wide metrics summary
 */
export function useSiteMetricsSummary(siteName) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchSummary = useCallback(async () => {
    if (!siteName) {
      setSummary(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const url = `${API_BASE}/site/${encodeURIComponent(siteName)}/summary`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      setSummary(result);
    } catch (err) {
      setError(err.message);
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, [siteName]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  return { summary, loading, error, refetch: fetchSummary };
}

export default {
  useOpticalMetrics,
  useInterfaceMetrics,
  useAvailabilityMetrics,
  useDeviceMetricsSummary,
  useSiteMetricsSummary,
};
