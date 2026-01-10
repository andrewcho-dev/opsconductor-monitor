/**
 * Health Hooks
 * 
 * React hooks for fetching health scores and status from the OpsConductor API.
 * Health scores are calculated based on availability, performance, errors, and capacity.
 */

import { useState, useEffect, useCallback } from 'react';

const API_BASE = '/monitoring/v1/health';

/**
 * Fetch health score for a specific device
 */
export function useDeviceHealth(deviceIp) {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchHealth = useCallback(async () => {
    if (!deviceIp) {
      setHealth(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const url = `${API_BASE}/device/${encodeURIComponent(deviceIp)}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      setHealth(result);
    } catch (err) {
      setError(err.message);
      setHealth(null);
    } finally {
      setLoading(false);
    }
  }, [deviceIp]);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  return { health, loading, error, refetch: fetchHealth };
}

/**
 * Fetch health summary for a site
 */
export function useSiteHealth(siteName) {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchHealth = useCallback(async () => {
    if (!siteName) {
      setHealth(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const url = `${API_BASE}/site/${encodeURIComponent(siteName)}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      setHealth(result);
    } catch (err) {
      setError(err.message);
      setHealth(null);
    } finally {
      setLoading(false);
    }
  }, [siteName]);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  return { health, loading, error, refetch: fetchHealth };
}

/**
 * Fetch network-wide health summary
 */
export function useNetworkHealth() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchHealth = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const url = `${API_BASE}/network/summary`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      setHealth(result);
    } catch (err) {
      setError(err.message);
      setHealth(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  return { health, loading, error, refetch: fetchHealth };
}

/**
 * Trigger health calculation for a device
 */
export function useCalculateHealth() {
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState(null);

  const calculate = useCallback(async (deviceIp) => {
    if (!deviceIp) {
      return null;
    }

    setCalculating(true);
    setError(null);

    try {
      const url = `${API_BASE}/device/${encodeURIComponent(deviceIp)}/calculate`;
      const response = await fetch(url, { method: 'POST' });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      return result;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setCalculating(false);
    }
  }, []);

  return { calculate, calculating, error };
}

/**
 * Get health score color based on value
 */
export function getHealthColor(score) {
  if (score === null || score === undefined) return 'gray';
  if (score >= 90) return 'green';
  if (score >= 70) return 'yellow';
  if (score >= 50) return 'orange';
  return 'red';
}

/**
 * Get health status label based on score
 */
export function getHealthLabel(score) {
  if (score === null || score === undefined) return 'Unknown';
  if (score >= 90) return 'Healthy';
  if (score >= 70) return 'Warning';
  if (score >= 50) return 'Degraded';
  return 'Critical';
}

/**
 * Format health score for display
 */
export function formatHealthScore(score) {
  if (score === null || score === undefined) return '--';
  return Math.round(score);
}

export default {
  useDeviceHealth,
  useSiteHealth,
  useNetworkHealth,
  useCalculateHealth,
  getHealthColor,
  getHealthLabel,
  formatHealthScore,
};
