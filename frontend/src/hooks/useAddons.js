/**
 * useAddons Hook
 * 
 * React hook for managing addons via the API.
 */

import { useState, useCallback } from 'react';
import { fetchApi } from '../lib/utils';

export function useAddons() {
  const [addons, setAddons] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAddons = useCallback(async (filters = {}) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (filters.category) params.append('category', filters.category);
      if (filters.enabled !== undefined) params.append('enabled', filters.enabled);
      // Always include uninstalled to show all built-in addons
      params.append('include_uninstalled', 'true');
      
      const queryString = params.toString();
      const url = `/api/v1/addons${queryString ? `?${queryString}` : ''}`;
      
      const response = await fetchApi(url);
      setAddons(response || []);
      return response || [];
    } catch (err) {
      setError(err.message || 'Failed to fetch addons');
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const getAddon = useCallback(async (addonId) => {
    try {
      const response = await fetchApi(`/api/v1/addons/${addonId}`);
      return response;
    } catch (err) {
      throw new Error(err.message || `Failed to get addon ${addonId}`);
    }
  }, []);

  const enableAddon = useCallback(async (addonId) => {
    try {
      const response = await fetchApi(`/api/v1/addons/${addonId}/enable`, {
        method: 'POST',
      });
      if (response.success) {
        setAddons(prev => prev.map(a => 
          a.id === addonId ? { ...a, enabled: true } : a
        ));
      }
      return response;
    } catch (err) {
      throw new Error(err.message || `Failed to enable addon ${addonId}`);
    }
  }, []);

  const disableAddon = useCallback(async (addonId) => {
    try {
      const response = await fetchApi(`/api/v1/addons/${addonId}/disable`, {
        method: 'POST',
      });
      if (response.success) {
        setAddons(prev => prev.map(a => 
          a.id === addonId ? { ...a, enabled: false } : a
        ));
      }
      return response;
    } catch (err) {
      throw new Error(err.message || `Failed to disable addon ${addonId}`);
    }
  }, []);

  const installAddon = useCallback(async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch('/api/v1/addons/install', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to install addon');
      }
      
      const result = await response.json();
      if (result.success) {
        await fetchAddons(); // Refresh list
      }
      return result;
    } catch (err) {
      throw new Error(err.message || 'Failed to install addon');
    }
  }, [fetchAddons]);

  const uninstallAddon = useCallback(async (addonId) => {
    try {
      const response = await fetchApi(`/api/v1/addons/${addonId}`, {
        method: 'DELETE',
      });
      if (response.success) {
        // For built-in addons, mark as uninstalled instead of removing
        setAddons(prev => prev.map(a => 
          a.id === addonId ? { ...a, installed: false, enabled: false } : a
        ));
      }
      return response;
    } catch (err) {
      throw new Error(err.message || `Failed to uninstall addon ${addonId}`);
    }
  }, []);

  const reinstallAddon = useCallback(async (addonId) => {
    try {
      const response = await fetchApi(`/api/v1/addons/${addonId}/reinstall`, {
        method: 'POST',
      });
      if (response.success) {
        setAddons(prev => prev.map(a => 
          a.id === addonId ? { ...a, installed: true, enabled: true } : a
        ));
      }
      return response;
    } catch (err) {
      throw new Error(err.message || `Failed to reinstall addon ${addonId}`);
    }
  }, []);

  const updateAddonConfig = useCallback(async (addonId, config) => {
    try {
      const response = await fetchApi(`/api/v1/addons/${addonId}/config`, {
        method: 'PUT',
        body: JSON.stringify({ config }),
      });
      return response;
    } catch (err) {
      throw new Error(err.message || `Failed to update addon config`);
    }
  }, []);

  const getAddonConfig = useCallback(async (addonId) => {
    try {
      const response = await fetchApi(`/api/v1/addons/${addonId}/config`);
      return response;
    } catch (err) {
      throw new Error(err.message || `Failed to get addon config`);
    }
  }, []);

  return {
    addons,
    loading,
    error,
    fetchAddons,
    getAddon,
    enableAddon,
    disableAddon,
    installAddon,
    uninstallAddon,
    reinstallAddon,
    updateAddonConfig,
    getAddonConfig,
  };
}
