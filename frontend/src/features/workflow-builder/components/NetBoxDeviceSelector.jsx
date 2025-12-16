/**
 * NetBoxDeviceSelector Component
 * 
 * Allows selecting devices from NetBox by site, role, or status
 * for use as workflow targets.
 */

import React, { useState, useEffect } from 'react';
import { Loader2, Server, RefreshCw } from 'lucide-react';
import { fetchApi } from '../../../lib/utils';

const NetBoxDeviceSelector = ({ value, onChange }) => {
  const [lookups, setLookups] = useState({
    sites: [],
    roles: [],
    loading: true,
    error: null,
  });
  const [deviceCount, setDeviceCount] = useState(null);
  const [loadingCount, setLoadingCount] = useState(false);

  // Load NetBox lookups on mount
  useEffect(() => {
    loadLookups();
  }, []);

  // Update device count when filters change
  useEffect(() => {
    if (!lookups.loading) {
      loadDeviceCount();
    }
  }, [value.site, value.role, value.status, lookups.loading]);

  const loadLookups = async () => {
    try {
      const [sitesRes, rolesRes] = await Promise.all([
        fetchApi('/api/netbox/sites').catch(() => ({ data: [] })),
        fetchApi('/api/netbox/device-roles').catch(() => ({ data: [] })),
      ]);

      setLookups({
        sites: sitesRes.data || [],
        roles: rolesRes.data || [],
        loading: false,
        error: null,
      });
    } catch (err) {
      setLookups(prev => ({
        ...prev,
        loading: false,
        error: 'Failed to load NetBox data. Check NetBox connection in Settings.',
      }));
    }
  };

  const loadDeviceCount = async () => {
    setLoadingCount(true);
    try {
      const params = new URLSearchParams();
      if (value.site) params.set('site', value.site);
      if (value.role) params.set('role', value.role);
      if (value.status) params.set('status', value.status);
      params.set('limit', '1'); // Just need count, not all devices

      const res = await fetchApi(`/api/netbox/devices?${params}`);
      setDeviceCount(res.count ?? res.data?.length ?? 0);
    } catch (err) {
      setDeviceCount(null);
    } finally {
      setLoadingCount(false);
    }
  };

  const handleChange = (field, newValue) => {
    onChange({ ...value, [field]: newValue });
  };

  if (lookups.loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500 py-2">
        <Loader2 className="w-4 h-4 animate-spin" />
        Loading NetBox data...
      </div>
    );
  }

  if (lookups.error) {
    return (
      <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
        <p className="text-sm text-amber-700">{lookups.error}</p>
        <button
          onClick={loadLookups}
          className="mt-2 text-xs text-amber-600 hover:text-amber-800 flex items-center gap-1"
        >
          <RefreshCw className="w-3 h-3" /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Site Filter */}
      <div>
        <label className="block text-xs text-gray-600 mb-1">Site</label>
        <select
          value={value.site || ''}
          onChange={(e) => handleChange('site', e.target.value)}
          className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-blue-500"
        >
          <option value="">All Sites</option>
          {lookups.sites.map(site => (
            <option key={site.id} value={site.slug || site.id}>
              {site.name}
            </option>
          ))}
        </select>
      </div>

      {/* Role Filter */}
      <div>
        <label className="block text-xs text-gray-600 mb-1">Device Role</label>
        <select
          value={value.role || ''}
          onChange={(e) => handleChange('role', e.target.value)}
          className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-blue-500"
        >
          <option value="">All Roles</option>
          {lookups.roles.map(role => (
            <option key={role.id} value={role.slug || role.id}>
              {role.name}
            </option>
          ))}
        </select>
      </div>

      {/* Status Filter */}
      <div>
        <label className="block text-xs text-gray-600 mb-1">Status</label>
        <select
          value={value.status || ''}
          onChange={(e) => handleChange('status', e.target.value)}
          className="w-full px-2.5 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-blue-500"
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="planned">Planned</option>
          <option value="staged">Staged</option>
          <option value="failed">Failed</option>
          <option value="offline">Offline</option>
          <option value="decommissioning">Decommissioning</option>
        </select>
      </div>

      {/* Device Count Preview */}
      <div className="flex items-center gap-2 p-2 bg-gray-50 border border-gray-200 rounded-md">
        <Server className="w-4 h-4 text-gray-400" />
        {loadingCount ? (
          <span className="text-sm text-gray-500 flex items-center gap-1">
            <Loader2 className="w-3 h-3 animate-spin" />
            Counting...
          </span>
        ) : deviceCount !== null ? (
          <span className="text-sm text-gray-700">
            <strong>{deviceCount}</strong> device{deviceCount !== 1 ? 's' : ''} match this filter
          </span>
        ) : (
          <span className="text-sm text-gray-500">
            Unable to count devices
          </span>
        )}
      </div>
    </div>
  );
};

export default NetBoxDeviceSelector;
