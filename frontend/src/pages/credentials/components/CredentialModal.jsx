/**
 * CredentialModal Component
 * 
 * Modal for creating and editing credentials.
 */

import React, { useState, useEffect } from 'react';
import { XCircle, Eye, EyeOff, Server, Plus, X, Search } from 'lucide-react';
import { fetchApi } from '../../../lib/utils';
import { CREDENTIAL_TYPES } from './constants';

function DeviceAssignmentSection({ credentialId }) {
  const [assignedDevices, setAssignedDevices] = useState([]);
  const [availableDevices, setAvailableDevices] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [showDevicePicker, setShowDevicePicker] = useState(false);
  const [selectedToAdd, setSelectedToAdd] = useState(new Set());
  const [selectedToRemove, setSelectedToRemove] = useState(new Set());
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const assignedRes = await fetchApi(`/api/credentials/${credentialId}/devices`);
        setAssignedDevices(assignedRes.data?.devices || []);

        const devicesRes = await fetchApi('/api/netbox/devices?limit=1000');
        const devices = (devicesRes.data || []).map(d => ({
          ip_address: d.primary_ip4?.address?.split('/')[0] || '',
          hostname: d.name,
          site: d.site?.name || '',
          id: d.id,
        })).filter(d => d.ip_address);
        setAvailableDevices(devices);
      } catch (err) {
        console.error('Error fetching devices:', err);
      } finally {
        setLoading(false);
      }
    };
    if (credentialId) fetchData();
  }, [credentialId]);

  const handleAddSelected = async () => {
    if (selectedToAdd.size === 0) return;
    setProcessing(true);
    try {
      const devicesToAdd = availableDevices.filter(d => selectedToAdd.has(d.ip_address));
      for (const device of devicesToAdd) {
        await fetchApi(`/api/credentials/devices/${device.ip_address}/assign`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ credential_id: credentialId }),
        });
      }
      setAssignedDevices(prev => [
        ...prev,
        ...devicesToAdd.map(d => ({
          ip_address: d.ip_address,
          netbox_device: { hostname: d.hostname, site: d.site }
        }))
      ]);
      setSelectedToAdd(new Set());
      setShowDevicePicker(false);
    } catch (err) {
      alert('Error assigning devices: ' + err.message);
    } finally {
      setProcessing(false);
    }
  };

  const handleRemoveSelected = async () => {
    if (selectedToRemove.size === 0) return;
    setProcessing(true);
    try {
      for (const ip of selectedToRemove) {
        await fetchApi(`/api/credentials/devices/${ip}/unassign`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ credential_id: credentialId }),
        });
      }
      setAssignedDevices(prev => prev.filter(d => !selectedToRemove.has(d.ip_address)));
      setSelectedToRemove(new Set());
    } catch (err) {
      alert('Error removing devices: ' + err.message);
    } finally {
      setProcessing(false);
    }
  };

  const toggleAddSelection = (ip) => {
    setSelectedToAdd(prev => {
      const next = new Set(prev);
      if (next.has(ip)) next.delete(ip);
      else next.add(ip);
      return next;
    });
  };

  const toggleRemoveSelection = (ip) => {
    setSelectedToRemove(prev => {
      const next = new Set(prev);
      if (next.has(ip)) next.delete(ip);
      else next.add(ip);
      return next;
    });
  };

  const selectAllToAdd = () => {
    const allIps = filteredDevices.slice(0, 50).map(d => d.ip_address);
    setSelectedToAdd(new Set(allIps));
  };

  const selectAllToRemove = () => {
    const allIps = assignedDevices.map(d => d.ip_address);
    setSelectedToRemove(new Set(allIps));
  };

  const assignedIps = new Set(assignedDevices.map(d => d.ip_address));
  const filteredDevices = availableDevices.filter(d => 
    !assignedIps.has(d.ip_address) &&
    (d.ip_address.includes(searchTerm) || 
     d.hostname?.toLowerCase().includes(searchTerm.toLowerCase()) ||
     d.site?.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  if (loading) {
    return <div className="text-sm text-gray-500">Loading devices...</div>;
  }

  return (
    <div className="border rounded-lg p-4 bg-gray-50">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-700 flex items-center gap-2">
          <Server className="w-4 h-4" />
          Assigned Devices ({assignedDevices.length})
        </h3>
        <button
          type="button"
          onClick={() => { setShowDevicePicker(!showDevicePicker); setSelectedToAdd(new Set()); }}
          className="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center gap-1"
        >
          <Plus className="w-3 h-3" />
          Add Devices
        </button>
      </div>

      {showDevicePicker && (
        <div className="mb-3 p-3 bg-white border rounded-lg">
          <div className="relative mb-2">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by IP, hostname, or site..."
              className="w-full pl-8 pr-3 py-1.5 text-sm border rounded"
            />
          </div>
          <div className="flex items-center justify-between mb-2 text-xs">
            <button type="button" onClick={selectAllToAdd} className="text-blue-600 hover:underline">
              Select all ({Math.min(filteredDevices.length, 50)})
            </button>
            <span className="text-gray-500">{selectedToAdd.size} selected</span>
          </div>
          <div className="max-h-48 overflow-y-auto space-y-1 border rounded p-1">
            {filteredDevices.length === 0 ? (
              <div className="text-xs text-gray-500 py-2 text-center">No devices found</div>
            ) : (
              filteredDevices.slice(0, 50).map(device => (
                <label
                  key={device.ip_address}
                  className={`flex items-center gap-2 px-2 py-1.5 text-sm rounded cursor-pointer ${
                    selectedToAdd.has(device.ip_address) ? 'bg-blue-50' : 'hover:bg-gray-50'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedToAdd.has(device.ip_address)}
                    onChange={() => toggleAddSelection(device.ip_address)}
                    className="rounded text-blue-600"
                  />
                  <span className="font-mono text-xs flex-1">{device.ip_address}</span>
                  <span className="text-xs text-gray-500">{device.hostname || device.site}</span>
                </label>
              ))
            )}
          </div>
          {filteredDevices.length > 50 && (
            <div className="text-xs text-gray-500 py-1 text-center">
              Showing 50 of {filteredDevices.length} (refine search)
            </div>
          )}
          <div className="flex justify-end gap-2 mt-2">
            <button
              type="button"
              onClick={() => { setShowDevicePicker(false); setSelectedToAdd(new Set()); }}
              className="px-3 py-1 text-xs text-gray-600 hover:bg-gray-100 rounded"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleAddSelected}
              disabled={selectedToAdd.size === 0 || processing}
              className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {processing ? 'Adding...' : `Add ${selectedToAdd.size} Device${selectedToAdd.size !== 1 ? 's' : ''}`}
            </button>
          </div>
        </div>
      )}

      {assignedDevices.length === 0 ? (
        <div className="text-xs text-gray-500 py-2">No devices assigned to this credential</div>
      ) : (
        <>
          <div className="flex items-center justify-between mb-2 text-xs">
            <button type="button" onClick={selectAllToRemove} className="text-gray-600 hover:underline">
              Select all
            </button>
            {selectedToRemove.size > 0 && (
              <button
                type="button"
                onClick={handleRemoveSelected}
                disabled={processing}
                className="text-red-600 hover:underline"
              >
                {processing ? 'Removing...' : `Remove ${selectedToRemove.size} selected`}
              </button>
            )}
          </div>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {assignedDevices.map((device, idx) => (
              <label
                key={idx}
                className={`flex items-center gap-2 bg-white px-2 py-1.5 rounded border text-sm cursor-pointer ${
                  selectedToRemove.has(device.ip_address) ? 'border-red-300 bg-red-50' : ''
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedToRemove.has(device.ip_address)}
                  onChange={() => toggleRemoveSelection(device.ip_address)}
                  className="rounded text-red-600"
                />
                <span className="font-mono text-xs flex-1">{device.ip_address}</span>
                {device.netbox_device && (
                  <span className="text-xs text-gray-500">
                    {device.netbox_device.hostname || device.netbox_device.site}
                  </span>
                )}
              </label>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export function CredentialModal({ credential, onClose, onSave }) {
  const [formData, setFormData] = useState({
    name: credential?.name || '',
    description: credential?.description || '',
    credential_type: credential?.credential_type || 'ssh',
    username: credential?.username || '',
    password: '',
    private_key: '',
    passphrase: '',
    port: 22,
    community: '',
    snmp_version: '2c',
    security_name: '',
    auth_protocol: '',
    auth_password: '',
    priv_protocol: '',
    priv_password: '',
    api_key: '',
    api_secret: '',
    token: '',
    domain: '',
    winrm_transport: 'ntlm',
    winrm_port: 5985,
    certificate: '',
    ca_certificate: '',
    ldap_server: '',
    ldap_port: 389,
    ldap_use_ssl: false,
    bind_dn: '',
    bind_password: '',
    base_dn: '',
    user_search_filter: '(uid={username})',
    domain_controller: '',
    ad_domain: '',
    ad_port: 389,
    ad_use_ssl: false,
    tacacs_server: '',
    tacacs_port: 49,
    tacacs_secret: '',
    tacacs_timeout: 5,
    tacacs_auth_type: 'ascii',
    radius_server: '',
    radius_auth_port: 1812,
    radius_acct_port: 1813,
    radius_secret: '',
    radius_timeout: 5,
    radius_retries: 3,
    nas_identifier: '',
    valid_until: credential?.valid_until ? credential.valid_until.split('T')[0] : '',
    category: credential?.category || '',
    environment: credential?.environment || '',
    owner: credential?.owner || '',
    notes: credential?.notes || '',
  });
  const [saving, setSaving] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { ...formData };
      if (payload.valid_until) {
        payload.valid_until = new Date(payload.valid_until).toISOString();
      }
      
      if (credential) {
        await fetchApi(`/api/credentials/${credential.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        await fetchApi('/api/credentials', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }
      onSave();
    } catch (err) {
      alert('Error saving credential: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b sticky top-0 bg-white">
          <h2 className="text-lg font-semibold">{credential ? 'Edit Credential' : 'Add Credential'}</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <XCircle className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Basic Info */}
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="e.g., Production SSH Key"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
              <select
                value={formData.credential_type}
                onChange={(e) => setFormData(prev => ({ ...prev, credential_type: e.target.value }))}
                className="w-full px-3 py-2 border rounded-lg"
                disabled={!!credential}
              >
                {Object.entries(CREDENTIAL_TYPES).map(([key, { label }]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <select
                value={formData.category}
                onChange={(e) => setFormData(prev => ({ ...prev, category: e.target.value }))}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="">Select category</option>
                <option value="network">Network</option>
                <option value="server">Server</option>
                <option value="cloud">Cloud</option>
                <option value="database">Database</option>
                <option value="application">Application</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="Optional description"
            />
          </div>

          {/* SSH/Password fields */}
          {(formData.credential_type === 'ssh' || formData.credential_type === 'password') && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                  <input
                    type="text"
                    value={formData.username}
                    onChange={(e) => setFormData(prev => ({ ...prev, username: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={formData.password}
                      onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                      className="w-full px-3 py-2 border rounded-lg pr-10"
                      placeholder={credential ? '(unchanged)' : ''}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-400"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              </div>
              {formData.credential_type === 'ssh' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Private Key</label>
                  <textarea
                    value={formData.private_key}
                    onChange={(e) => setFormData(prev => ({ ...prev, private_key: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg font-mono text-sm h-24"
                    placeholder="-----BEGIN RSA PRIVATE KEY-----"
                  />
                </div>
              )}
            </>
          )}

          {/* SNMP fields */}
          {formData.credential_type === 'snmp' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">SNMP Version</label>
                <select
                  value={formData.snmp_version}
                  onChange={(e) => setFormData(prev => ({ ...prev, snmp_version: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                >
                  <option value="2c">v2c</option>
                  <option value="1">v1</option>
                  <option value="3">v3</option>
                </select>
              </div>
              {(formData.snmp_version === '1' || formData.snmp_version === '2c') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Community String</label>
                  <input
                    type="password"
                    value={formData.community}
                    onChange={(e) => setFormData(prev => ({ ...prev, community: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder={credential ? '(unchanged)' : 'e.g., public'}
                  />
                </div>
              )}
              {formData.snmp_version === '3' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Security Name (Username)</label>
                    <input
                      type="text"
                      value={formData.security_name}
                      onChange={(e) => setFormData(prev => ({ ...prev, security_name: e.target.value }))}
                      className="w-full px-3 py-2 border rounded-lg"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Auth Protocol</label>
                      <select
                        value={formData.auth_protocol}
                        onChange={(e) => setFormData(prev => ({ ...prev, auth_protocol: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-lg"
                      >
                        <option value="">None</option>
                        <option value="MD5">MD5</option>
                        <option value="SHA">SHA</option>
                        <option value="SHA256">SHA-256</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Auth Password</label>
                      <input
                        type="password"
                        value={formData.auth_password}
                        onChange={(e) => setFormData(prev => ({ ...prev, auth_password: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-lg"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Privacy Protocol</label>
                      <select
                        value={formData.priv_protocol}
                        onChange={(e) => setFormData(prev => ({ ...prev, priv_protocol: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-lg"
                      >
                        <option value="">None</option>
                        <option value="DES">DES</option>
                        <option value="AES">AES</option>
                        <option value="AES256">AES-256</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Privacy Password</label>
                      <input
                        type="password"
                        value={formData.priv_password}
                        onChange={(e) => setFormData(prev => ({ ...prev, priv_password: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-lg"
                      />
                    </div>
                  </div>
                </>
              )}
            </>
          )}

          {/* WinRM fields */}
          {formData.credential_type === 'winrm' && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                  <input
                    type="text"
                    value={formData.username}
                    onChange={(e) => setFormData(prev => ({ ...prev, username: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="Administrator"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Domain</label>
                  <input
                    type="text"
                    value={formData.domain}
                    onChange={(e) => setFormData(prev => ({ ...prev, domain: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="DOMAIN (optional)"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Transport</label>
                  <select
                    value={formData.winrm_transport}
                    onChange={(e) => setFormData(prev => ({ ...prev, winrm_transport: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  >
                    <option value="ntlm">NTLM</option>
                    <option value="kerberos">Kerberos</option>
                    <option value="basic">Basic</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
                  <select
                    value={formData.winrm_port}
                    onChange={(e) => setFormData(prev => ({ ...prev, winrm_port: parseInt(e.target.value) }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  >
                    <option value="5985">5985 (HTTP)</option>
                    <option value="5986">5986 (HTTPS)</option>
                  </select>
                </div>
              </div>
            </>
          )}

          {/* Certificate/PKI fields */}
          {(formData.credential_type === 'certificate' || formData.credential_type === 'pki') && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Certificate (PEM)</label>
                <textarea
                  value={formData.certificate}
                  onChange={(e) => setFormData(prev => ({ ...prev, certificate: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg font-mono text-sm h-32"
                  placeholder="-----BEGIN CERTIFICATE-----"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Private Key (PEM)</label>
                <textarea
                  value={formData.private_key}
                  onChange={(e) => setFormData(prev => ({ ...prev, private_key: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg font-mono text-sm h-32"
                  placeholder="-----BEGIN PRIVATE KEY-----"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Key Passphrase (optional)</label>
                <input
                  type="password"
                  value={formData.passphrase}
                  onChange={(e) => setFormData(prev => ({ ...prev, passphrase: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                />
              </div>
            </>
          )}

          {/* API Key fields */}
          {formData.credential_type === 'api_key' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                <input
                  type="password"
                  value={formData.api_key}
                  onChange={(e) => setFormData(prev => ({ ...prev, api_key: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">API Secret (optional)</label>
                <input
                  type="password"
                  value={formData.api_secret}
                  onChange={(e) => setFormData(prev => ({ ...prev, api_secret: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                />
              </div>
            </div>
          )}

          {/* LDAP fields */}
          {formData.credential_type === 'ldap' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">LDAP Server</label>
                  <input
                    type="text"
                    value={formData.ldap_server}
                    onChange={(e) => setFormData(prev => ({ ...prev, ldap_server: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="ldap.example.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
                  <input
                    type="number"
                    value={formData.ldap_port}
                    onChange={(e) => setFormData(prev => ({ ...prev, ldap_port: parseInt(e.target.value) }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="ldap_use_ssl"
                  checked={formData.ldap_use_ssl}
                  onChange={(e) => setFormData(prev => ({ ...prev, ldap_use_ssl: e.target.checked }))}
                  className="rounded"
                />
                <label htmlFor="ldap_use_ssl" className="text-sm text-gray-700">Use SSL/TLS (LDAPS)</label>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Bind DN</label>
                <input
                  type="text"
                  value={formData.bind_dn}
                  onChange={(e) => setFormData(prev => ({ ...prev, bind_dn: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="cn=admin,dc=example,dc=com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Bind Password</label>
                <input
                  type="password"
                  value={formData.bind_password}
                  onChange={(e) => setFormData(prev => ({ ...prev, bind_password: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Base DN</label>
                <input
                  type="text"
                  value={formData.base_dn}
                  onChange={(e) => setFormData(prev => ({ ...prev, base_dn: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="dc=example,dc=com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">User Search Filter</label>
                <input
                  type="text"
                  value={formData.user_search_filter}
                  onChange={(e) => setFormData(prev => ({ ...prev, user_search_filter: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg font-mono text-sm"
                  placeholder="(uid={username})"
                />
              </div>
            </div>
          )}

          {/* Active Directory fields */}
          {formData.credential_type === 'active_directory' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Domain Controller</label>
                  <input
                    type="text"
                    value={formData.domain_controller}
                    onChange={(e) => setFormData(prev => ({ ...prev, domain_controller: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="dc01.example.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Domain</label>
                  <input
                    type="text"
                    value={formData.ad_domain}
                    onChange={(e) => setFormData(prev => ({ ...prev, ad_domain: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="EXAMPLE.COM"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
                  <input
                    type="number"
                    value={formData.ad_port}
                    onChange={(e) => setFormData(prev => ({ ...prev, ad_port: parseInt(e.target.value) }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  />
                </div>
                <div className="flex items-center gap-2 pt-6">
                  <input
                    type="checkbox"
                    id="ad_use_ssl"
                    checked={formData.ad_use_ssl}
                    onChange={(e) => setFormData(prev => ({ ...prev, ad_use_ssl: e.target.checked }))}
                    className="rounded"
                  />
                  <label htmlFor="ad_use_ssl" className="text-sm text-gray-700">Use SSL/TLS</label>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                  <input
                    type="text"
                    value={formData.username}
                    onChange={(e) => setFormData(prev => ({ ...prev, username: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="admin@example.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                  <input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Base DN</label>
                <input
                  type="text"
                  value={formData.base_dn}
                  onChange={(e) => setFormData(prev => ({ ...prev, base_dn: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="DC=example,DC=com"
                />
              </div>
            </div>
          )}

          {/* TACACS+ fields */}
          {formData.credential_type === 'tacacs' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">TACACS+ Server</label>
                  <input
                    type="text"
                    value={formData.tacacs_server}
                    onChange={(e) => setFormData(prev => ({ ...prev, tacacs_server: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="tacacs.example.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
                  <input
                    type="number"
                    value={formData.tacacs_port}
                    onChange={(e) => setFormData(prev => ({ ...prev, tacacs_port: parseInt(e.target.value) }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Secret Key</label>
                <input
                  type="password"
                  value={formData.tacacs_secret}
                  onChange={(e) => setFormData(prev => ({ ...prev, tacacs_secret: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Authentication Type</label>
                  <select
                    value={formData.tacacs_auth_type}
                    onChange={(e) => setFormData(prev => ({ ...prev, tacacs_auth_type: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  >
                    <option value="ascii">ASCII</option>
                    <option value="pap">PAP</option>
                    <option value="chap">CHAP</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Timeout (seconds)</label>
                  <input
                    type="number"
                    value={formData.tacacs_timeout}
                    onChange={(e) => setFormData(prev => ({ ...prev, tacacs_timeout: parseInt(e.target.value) }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  />
                </div>
              </div>
            </div>
          )}

          {/* RADIUS fields */}
          {formData.credential_type === 'radius' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">RADIUS Server</label>
                  <input
                    type="text"
                    value={formData.radius_server}
                    onChange={(e) => setFormData(prev => ({ ...prev, radius_server: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="radius.example.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Secret Key</label>
                  <input
                    type="password"
                    value={formData.radius_secret}
                    onChange={(e) => setFormData(prev => ({ ...prev, radius_secret: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Auth Port</label>
                  <input
                    type="number"
                    value={formData.radius_auth_port}
                    onChange={(e) => setFormData(prev => ({ ...prev, radius_auth_port: parseInt(e.target.value) }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Accounting Port</label>
                  <input
                    type="number"
                    value={formData.radius_acct_port}
                    onChange={(e) => setFormData(prev => ({ ...prev, radius_acct_port: parseInt(e.target.value) }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Timeout (seconds)</label>
                  <input
                    type="number"
                    value={formData.radius_timeout}
                    onChange={(e) => setFormData(prev => ({ ...prev, radius_timeout: parseInt(e.target.value) }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Retries</label>
                  <input
                    type="number"
                    value={formData.radius_retries}
                    onChange={(e) => setFormData(prev => ({ ...prev, radius_retries: parseInt(e.target.value) }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">NAS Identifier (optional)</label>
                <input
                  type="text"
                  value={formData.nas_identifier}
                  onChange={(e) => setFormData(prev => ({ ...prev, nas_identifier: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="opsconductor"
                />
              </div>
            </div>
          )}

          {/* Metadata */}
          <div className="border-t pt-4 mt-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Metadata</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Environment</label>
                <select
                  value={formData.environment}
                  onChange={(e) => setFormData(prev => ({ ...prev, environment: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                >
                  <option value="">Select environment</option>
                  <option value="production">Production</option>
                  <option value="staging">Staging</option>
                  <option value="development">Development</option>
                  <option value="testing">Testing</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Expiration Date</label>
                <input
                  type="date"
                  value={formData.valid_until}
                  onChange={(e) => setFormData(prev => ({ ...prev, valid_until: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Owner</label>
                <input
                  type="text"
                  value={formData.owner}
                  onChange={(e) => setFormData(prev => ({ ...prev, owner: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="e.g., Network Team"
                />
              </div>
            </div>
            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                className="w-full px-3 py-2 border rounded-lg h-20"
                placeholder="Additional notes..."
              />
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : credential ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
