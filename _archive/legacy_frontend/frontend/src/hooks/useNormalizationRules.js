/**
 * Normalization Rules Hooks
 * 
 * Hooks for managing severity mappings, category mappings, and priority rules.
 */

import { useState, useEffect, useCallback } from 'react';

const API_BASE = '/api/v1';

/**
 * Hook for managing severity mappings
 */
export function useSeverityMappings(connectorType) {
  const [mappings, setMappings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMappings = useCallback(async () => {
    if (!connectorType) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/normalization/severity-mappings?connector_type=${connectorType}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setMappings(data.data || data.mappings || data || []);
    } catch (err) {
      setError(err.message);
      setMappings([]);
    } finally {
      setLoading(false);
    }
  }, [connectorType]);

  useEffect(() => {
    fetchMappings();
  }, [fetchMappings]);

  const createMapping = async (mapping) => {
    const response = await fetch(`${API_BASE}/normalization/severity-mappings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(mapping),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    await fetchMappings();
  };

  const updateMapping = async (id, updates) => {
    const response = await fetch(`${API_BASE}/normalization/severity-mappings/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    await fetchMappings();
  };

  const deleteMapping = async (id) => {
    const response = await fetch(`${API_BASE}/normalization/severity-mappings/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    await fetchMappings();
  };

  return {
    mappings,
    loading,
    error,
    refresh: fetchMappings,
    createMapping,
    updateMapping,
    deleteMapping,
  };
}

/**
 * Hook for managing category mappings
 */
export function useCategoryMappings(connectorType) {
  const [mappings, setMappings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMappings = useCallback(async () => {
    if (!connectorType) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/normalization/category-mappings?connector_type=${connectorType}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setMappings(data.data || data.mappings || data || []);
    } catch (err) {
      setError(err.message);
      setMappings([]);
    } finally {
      setLoading(false);
    }
  }, [connectorType]);

  useEffect(() => {
    fetchMappings();
  }, [fetchMappings]);

  const createMapping = async (mapping) => {
    const response = await fetch(`${API_BASE}/normalization/category-mappings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(mapping),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    await fetchMappings();
  };

  const updateMapping = async (id, updates) => {
    const response = await fetch(`${API_BASE}/normalization/category-mappings/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    await fetchMappings();
  };

  const deleteMapping = async (id) => {
    const response = await fetch(`${API_BASE}/normalization/category-mappings/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    await fetchMappings();
  };

  return {
    mappings,
    loading,
    error,
    refresh: fetchMappings,
    createMapping,
    updateMapping,
    deleteMapping,
  };
}

/**
 * Hook for managing priority rules
 */
export function usePriorityRules(connectorType) {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchRules = useCallback(async () => {
    if (!connectorType) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/normalization/priority-rules?connector_type=${connectorType}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setRules(data.data || data.rules || data || []);
    } catch (err) {
      setError(err.message);
      setRules([]);
    } finally {
      setLoading(false);
    }
  }, [connectorType]);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  const createRule = async (rule) => {
    const response = await fetch(`${API_BASE}/normalization/priority-rules`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(rule),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    await fetchRules();
  };

  const updateRule = async (id, updates) => {
    const response = await fetch(`${API_BASE}/normalization/priority-rules/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    await fetchRules();
  };

  const deleteRule = async (id) => {
    const response = await fetch(`${API_BASE}/normalization/priority-rules/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    await fetchRules();
  };

  return {
    rules,
    loading,
    error,
    refresh: fetchRules,
    createRule,
    updateRule,
    deleteRule,
  };
}

/**
 * Hook for managing alert type templates
 */
export function useAlertTypeTemplates(connectorType) {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchTemplates = useCallback(async () => {
    if (!connectorType) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/normalization/alert-type-templates?connector_type=${connectorType}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setTemplates(data.data || data.templates || data || []);
    } catch (err) {
      setError(err.message);
      setTemplates([]);
    } finally {
      setLoading(false);
    }
  }, [connectorType]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  return {
    templates,
    loading,
    error,
    refresh: fetchTemplates,
  };
}
