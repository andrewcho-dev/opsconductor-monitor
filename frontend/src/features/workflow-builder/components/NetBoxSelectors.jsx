/**
 * NetBox Selector Components
 * 
 * Dropdown selectors that fetch options from NetBox API:
 * - NetBoxSiteSelector
 * - NetBoxRoleSelector
 * - NetBoxDeviceTypeSelector
 * - NetBoxTagsSelector
 */

import React, { useState, useEffect } from 'react';
import { Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { cn } from '../../../lib/utils';

// Generic NetBox selector component
const NetBoxSelector = ({
  value,
  onChange,
  endpoint,
  label,
  placeholder,
  displayField = 'name',
  valueField = 'id',
  disabled = false,
  required = false,
  className,
}) => {
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchOptions = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/netbox/${endpoint}`);
      const data = await response.json();
      
      // Handle various response formats from NetBox API
      if (data.success && data.data) {
        setOptions(data.data);
      } else if (data.data) {
        setOptions(data.data);
      } else if (data.success && data.results) {
        setOptions(data.results);
      } else if (data.results) {
        setOptions(data.results);
      } else if (Array.isArray(data)) {
        setOptions(data);
      } else {
        setError('Invalid response format');
      }
    } catch (err) {
      console.error(`Failed to fetch ${endpoint}:`, err);
      setError(`Failed to load ${label || endpoint}`);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchOptions();
  }, [endpoint]);

  if (loading) {
    return (
      <div className={cn('flex items-center gap-2 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-500', className)}>
        <Loader2 className="w-4 h-4 animate-spin" />
        Loading {label || 'options'}...
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn('flex items-center justify-between px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm', className)}>
        <div className="flex items-center gap-2 text-red-600">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
        <button
          onClick={fetchOptions}
          className="p-1 text-red-500 hover:text-red-700 hover:bg-red-100 rounded"
          title="Retry"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <select
      value={value || ''}
      onChange={(e) => onChange(e.target.value ? Number(e.target.value) : '')}
      disabled={disabled}
      required={required}
      className={cn(
        'w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm',
        'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
        disabled && 'bg-gray-100 cursor-not-allowed',
        className
      )}
    >
      <option value="">{placeholder || `Select ${label}...`}</option>
      {options.map((option) => (
        <option key={option[valueField]} value={option[valueField]}>
          {option[displayField]}
          {option.slug && option.slug !== option[displayField] && ` (${option.slug})`}
        </option>
      ))}
    </select>
  );
};

// Site Selector
export const NetBoxSiteSelector = ({ value, onChange, ...props }) => (
  <NetBoxSelector
    value={value}
    onChange={onChange}
    endpoint="sites"
    label="Site"
    placeholder="Select site..."
    {...props}
  />
);

// Device Role Selector
export const NetBoxRoleSelector = ({ value, onChange, ...props }) => (
  <NetBoxSelector
    value={value}
    onChange={onChange}
    endpoint="device-roles"
    label="Device Role"
    placeholder="Select device role..."
    {...props}
  />
);

// Device Type Selector (with manufacturer grouping)
export const NetBoxDeviceTypeSelector = ({ value, onChange, disabled, required, className }) => {
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchOptions = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/netbox/device-types');
      const data = await response.json();
      
      // Handle various response formats from NetBox API
      if (data.success && data.data) {
        setOptions(data.data);
      } else if (data.data) {
        setOptions(data.data);
      } else if (data.success && data.results) {
        setOptions(data.results);
      } else if (data.results) {
        setOptions(data.results);
      } else if (Array.isArray(data)) {
        setOptions(data);
      } else {
        setError('Invalid response format');
      }
    } catch (err) {
      console.error('Failed to fetch device types:', err);
      setError('Failed to load device types');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchOptions();
  }, []);

  // Group by manufacturer
  const groupedOptions = options.reduce((acc, dt) => {
    const manufacturer = dt.manufacturer?.name || 'Unknown';
    if (!acc[manufacturer]) acc[manufacturer] = [];
    acc[manufacturer].push(dt);
    return acc;
  }, {});

  // Filter by search term
  const filteredGroups = Object.entries(groupedOptions).reduce((acc, [mfr, types]) => {
    const filtered = types.filter(t => 
      t.model?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      mfr.toLowerCase().includes(searchTerm.toLowerCase())
    );
    if (filtered.length > 0) acc[mfr] = filtered;
    return acc;
  }, {});

  if (loading) {
    return (
      <div className={cn('flex items-center gap-2 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-500', className)}>
        <Loader2 className="w-4 h-4 animate-spin" />
        Loading device types...
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn('flex items-center justify-between px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm', className)}>
        <div className="flex items-center gap-2 text-red-600">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
        <button
          onClick={fetchOptions}
          className="p-1 text-red-500 hover:text-red-700 hover:bg-red-100 rounded"
          title="Retry"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {options.length > 10 && (
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search device types..."
          className="w-full px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      )}
      <select
        value={value || ''}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : '')}
        disabled={disabled}
        required={required}
        className={cn(
          'w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm',
          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
          disabled && 'bg-gray-100 cursor-not-allowed',
          className
        )}
      >
        <option value="">Select device type...</option>
        {Object.entries(filteredGroups).map(([manufacturer, types]) => (
          <optgroup key={manufacturer} label={manufacturer}>
            {types.map((dt) => (
              <option key={dt.id} value={dt.id}>
                {dt.model}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </div>
  );
};

// Tags Selector (multi-select)
export const NetBoxTagsSelector = ({ value, onChange, disabled, className }) => {
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchOptions = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/netbox/tags');
      const data = await response.json();
      
      // Handle various response formats from NetBox API
      if (data.success && data.data) {
        setOptions(data.data);
      } else if (data.data) {
        setOptions(data.data);
      } else if (data.success && data.results) {
        setOptions(data.results);
      } else if (data.results) {
        setOptions(data.results);
      } else if (Array.isArray(data)) {
        setOptions(data);
      }
    } catch (err) {
      console.error('Failed to fetch tags:', err);
      setError('Failed to load tags');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchOptions();
  }, []);

  const selectedTags = Array.isArray(value) ? value : [];

  const toggleTag = (tagId) => {
    if (selectedTags.includes(tagId)) {
      onChange(selectedTags.filter(id => id !== tagId));
    } else {
      onChange([...selectedTags, tagId]);
    }
  };

  if (loading) {
    return (
      <div className={cn('flex items-center gap-2 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-500', className)}>
        <Loader2 className="w-4 h-4 animate-spin" />
        Loading tags...
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn('text-sm text-red-600', className)}>
        {error}
      </div>
    );
  }

  return (
    <div className={cn('flex flex-wrap gap-1.5', className)}>
      {options.map((tag) => (
        <button
          key={tag.id}
          type="button"
          onClick={() => toggleTag(tag.id)}
          disabled={disabled}
          className={cn(
            'px-2 py-1 text-xs rounded-full border transition-colors',
            selectedTags.includes(tag.id)
              ? 'bg-blue-100 border-blue-300 text-blue-700'
              : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100',
            disabled && 'opacity-50 cursor-not-allowed'
          )}
          style={tag.color ? {
            backgroundColor: selectedTags.includes(tag.id) ? `${tag.color}20` : undefined,
            borderColor: selectedTags.includes(tag.id) ? tag.color : undefined,
            color: selectedTags.includes(tag.id) ? tag.color : undefined,
          } : undefined}
        >
          {tag.name}
        </button>
      ))}
      {options.length === 0 && (
        <span className="text-sm text-gray-400">No tags available</span>
      )}
    </div>
  );
};

export default {
  NetBoxSiteSelector,
  NetBoxRoleSelector,
  NetBoxDeviceTypeSelector,
  NetBoxTagsSelector,
};
