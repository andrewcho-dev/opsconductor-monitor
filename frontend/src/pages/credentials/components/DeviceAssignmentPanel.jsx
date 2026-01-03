/**
 * DeviceAssignmentPanel Component
 * 
 * Right-side panel for managing device assignments for selected credential.
 * Shows a unified list of all devices with checkmarks for associated ones.
 */

import React, { useState, useEffect } from 'react';
import { Server, Search, RefreshCw, Save } from 'lucide-react';
import { fetchApi } from '../../../lib/utils';

export function DeviceAssignmentPanel({ selectedCredential, onUpdate }) {
  const [allDevices, setAllDevices] = useState([]);
  const [assignedIps, setAssignedIps] = useState(new Set());
  const [pendingChanges, setPendingChanges] = useState(new Set()); // IPs with pending state
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (selectedCredential) {
      loadDevices();
    } else {
      setAllDevices([]);
      setAssignedIps(new Set());
      setPendingChanges(new Set());
    }
  }, [selectedCredential?.id]);

  const loadDevices = async () => {
    if (!selectedCredential) return;
    setLoading(true);
    try {
      const [assignedRes, devicesRes] = await Promise.all([
        fetchApi(`/api/credentials/${selectedCredential.id}/devices`),
        fetchApi('/api/netbox/devices?limit=1000')
      ]);
      
      const assigned = new Set((assignedRes.data?.devices || []).map(d => d.ip_address));
      setAssignedIps(assigned);
      setPendingChanges(new Set(assigned)); // Start with current state
      
      const devices = (devicesRes.data || []).map(d => ({
        ip_address: d.primary_ip4?.address?.split('/')[0] || '',
        hostname: d.name,
        site: d.site?.name || '',
        id: d.id,
      })).filter(d => d.ip_address);
      setAllDevices(devices);
    } catch (err) {
      console.error('Error loading devices:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleDevice = (ip) => {
    setPendingChanges(prev => {
      const next = new Set(prev);
      if (next.has(ip)) {
        next.delete(ip);
      } else {
        next.add(ip);
      }
      return next;
    });
  };

  const hasChanges = () => {
    if (pendingChanges.size !== assignedIps.size) return true;
    for (const ip of pendingChanges) {
      if (!assignedIps.has(ip)) return true;
    }
    return false;
  };

  const saveChanges = async () => {
    if (!selectedCredential || !hasChanges()) return;
    setSaving(true);
    
    try {
      // Find IPs to add (in pending but not in assigned)
      const toAdd = [...pendingChanges].filter(ip => !assignedIps.has(ip));
      // Find IPs to remove (in assigned but not in pending)
      const toRemove = [...assignedIps].filter(ip => !pendingChanges.has(ip));
      
      // Process additions
      for (const ip of toAdd) {
        await fetchApi(`/api/credentials/devices/${ip}/assign`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ credential_id: selectedCredential.id }),
        });
      }
      
      // Process removals
      for (const ip of toRemove) {
        await fetchApi(`/api/credentials/devices/${ip}/unassign`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ credential_id: selectedCredential.id }),
        });
      }
      
      // Update state to reflect saved changes
      setAssignedIps(new Set(pendingChanges));
      onUpdate?.();
    } catch (err) {
      alert('Error saving changes: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const filteredDevices = allDevices.filter(d => 
    searchTerm === '' ||
    d.ip_address.includes(searchTerm) || 
    d.hostname?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    d.site?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Sort: associated devices first, then by IP
  const sortedDevices = [...filteredDevices].sort((a, b) => {
    const aAssigned = pendingChanges.has(a.ip_address);
    const bAssigned = pendingChanges.has(b.ip_address);
    if (aAssigned && !bAssigned) return -1;
    if (!aAssigned && bAssigned) return 1;
    return a.ip_address.localeCompare(b.ip_address);
  });

  const associatedCount = pendingChanges.size;
  const changesCount = hasChanges() ? 
    Math.abs(pendingChanges.size - assignedIps.size) + 
    [...pendingChanges].filter(ip => !assignedIps.has(ip)).length +
    [...assignedIps].filter(ip => !pendingChanges.has(ip)).length
    : 0;

  if (!selectedCredential) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-gray-400 p-6">
        <Server className="w-12 h-12 mb-3" />
        <p className="text-sm text-center">Select a credential to manage device assignments</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-2 py-1.5 border-b bg-gray-50 flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search..."
            className="w-full pl-7 pr-2 py-1 text-xs border rounded"
          />
        </div>
        <span className="text-xs text-gray-500 tabular-nums">{associatedCount}</span>
        <button
          onClick={saveChanges}
          disabled={!hasChanges() || saving}
          className={`p-1 rounded ${hasChanges() ? 'text-blue-600 hover:bg-blue-50' : 'text-gray-300'}`}
          title={saving ? 'Saving...' : 'Save changes'}
        >
          <Save className={`w-3.5 h-3.5 ${saving ? 'animate-pulse' : ''}`} />
        </button>
        <button
          onClick={loadDevices}
          className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded"
          title="Refresh"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Device List */}
      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <RefreshCw className="w-6 h-6 animate-spin text-blue-600" />
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          {sortedDevices.length === 0 ? (
            <div className="text-xs text-gray-400 text-center py-4">
              {searchTerm ? 'No match' : 'No devices'}
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {sortedDevices.map(device => {
                const isAssociated = pendingChanges.has(device.ip_address);
                const wasOriginallyAssigned = assignedIps.has(device.ip_address);
                const hasChanged = isAssociated !== wasOriginallyAssigned;
                
                return (
                  <label
                    key={device.ip_address}
                    className={`flex items-center gap-2 px-3 py-1 text-xs cursor-pointer ${
                      isAssociated ? 'bg-blue-50' : 'hover:bg-gray-50'
                    } ${hasChanged ? 'bg-amber-50' : ''}`}
                  >
                    <input
                      type="checkbox"
                      checked={isAssociated}
                      onChange={() => toggleDevice(device.ip_address)}
                      className="w-3.5 h-3.5 rounded border-gray-300 text-blue-600"
                    />
                    <span className="font-mono flex-shrink-0">{device.ip_address}</span>
                    <span className="text-gray-400 truncate">{device.hostname}</span>
                  </label>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
