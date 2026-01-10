import React, { useState, useEffect, useRef } from 'react';
import { PageLayout } from '../../components/layout/PageLayout';
import { PageHeader } from '../../components/layout/PageHeader';
import { 
  Database, ChevronRight, ChevronDown, Plus, Edit, Trash2, 
  Play, Settings, RefreshCw, Search, X, Check, AlertCircle,
  Loader2, Copy, TestTube, Save, Zap, CheckSquare, Square,
  Upload, FileText, Download
} from 'lucide-react';
import { cn, fetchApi } from '../../lib/utils';

const API_BASE = '/monitoring/v1/mib';

// Import MIB Modal - for uploading and parsing MIB files
function ImportMibModal({ profiles, onClose, onImported }) {
  const [step, setStep] = useState('upload'); // upload, preview, import
  const [file, setFile] = useState(null);
  const [parsedMib, setParsedMib] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedGroups, setSelectedGroups] = useState([]);
  const [profileId, setProfileId] = useState('');
  const [newProfileName, setNewProfileName] = useState('');
  const [newVendor, setNewVendor] = useState('');
  const fileInputRef = useRef(null);

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError(null);
    }
  };

  const handleParse = async () => {
    if (!file) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const formData = new FormData();
      formData.append('file', file);
      
      const data = await fetchApi(`${API_BASE}/parse-mib`, {
        method: 'POST',
        body: formData,
        rawBody: true
      });
      
      if (data.success) {
        setParsedMib(data.data);
        setSelectedGroups(data.data.groups.map(g => g.name));
        setNewProfileName(data.data.mib_name?.toLowerCase().replace(/[^a-z0-9]/g, '_') || '');
        setStep('preview');
      } else {
        setError(data.message || 'Failed to parse MIB file');
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleImport = async () => {
    if (!parsedMib) return;
    
    const groupsToImport = parsedMib.groups.filter(g => selectedGroups.includes(g.name));
    if (groupsToImport.length === 0) {
      setError('Select at least one group to import');
      return;
    }
    
    if (!profileId && (!newProfileName || !newVendor)) {
      setError('Select an existing profile or provide name and vendor for a new one');
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      const data = await fetchApi(`${API_BASE}/import-mib`, {
        method: 'POST',
        body: JSON.stringify({
          profile_id: profileId || null,
          profile_name: newProfileName,
          vendor: newVendor,
          enterprise_oid: parsedMib.enterprise_oid,
          mib_name: parsedMib.mib_name,
          groups: groupsToImport
        })
      });
      
      if (data.success) {
        onImported(data.data);
      } else {
        setError(data.message || 'Failed to import MIB');
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleGroup = (groupName) => {
    setSelectedGroups(prev => 
      prev.includes(groupName) 
        ? prev.filter(g => g !== groupName)
        : [...prev, groupName]
    );
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Upload className="w-5 h-5" />
            Import MIB File
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="p-6 overflow-y-auto flex-1">
          {error && (
            <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}
          
          {step === 'upload' && (
            <div className="space-y-4">
              <div className="text-sm text-gray-600 mb-4">
                Upload a MIB file (.mib, .txt, .my) to parse and import OID definitions.
                The parser will extract OBJECT-TYPE definitions and organize them into logical groups.
              </div>
              
              <div 
                className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".mib,.txt,.my"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <FileText className="w-12 h-12 mx-auto text-gray-400 mb-3" />
                {file ? (
                  <div>
                    <div className="font-medium text-gray-900">{file.name}</div>
                    <div className="text-sm text-gray-500">{(file.size / 1024).toFixed(1)} KB</div>
                  </div>
                ) : (
                  <div>
                    <div className="font-medium text-gray-700">Click to select MIB file</div>
                    <div className="text-sm text-gray-500">or drag and drop</div>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {step === 'preview' && parsedMib && (
            <div className="space-y-4">
              {/* MIB Info */}
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="font-semibold text-gray-900">{parsedMib.mib_name}</div>
                {parsedMib.description && (
                  <div className="text-sm text-gray-600 mt-1">{parsedMib.description}</div>
                )}
                {parsedMib.enterprise_oid && (
                  <div className="text-xs font-mono text-gray-500 mt-2">
                    Enterprise OID: {parsedMib.enterprise_oid}
                  </div>
                )}
                <div className="text-sm text-gray-600 mt-2">
                  Found {parsedMib.total_objects} OIDs in {parsedMib.groups.length} groups
                </div>
              </div>
              
              {/* Target Profile */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-gray-700">Import to Profile</label>
                <select
                  value={profileId}
                  onChange={(e) => setProfileId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="">-- Create New Profile --</option>
                  {profiles.map(p => (
                    <option key={p.id} value={p.id}>{p.vendor} - {p.name}</option>
                  ))}
                </select>
                
                {!profileId && (
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Profile Name</label>
                      <input
                        type="text"
                        value={newProfileName}
                        onChange={(e) => setNewProfileName(e.target.value)}
                        placeholder="e.g., cisco_catalyst"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Vendor</label>
                      <input
                        type="text"
                        value={newVendor}
                        onChange={(e) => setNewVendor(e.target.value)}
                        placeholder="e.g., Cisco"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                      />
                    </div>
                  </div>
                )}
              </div>
              
              {/* Groups to Import */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-gray-700">Groups to Import</label>
                  <button
                    onClick={() => setSelectedGroups(
                      selectedGroups.length === parsedMib.groups.length ? [] : parsedMib.groups.map(g => g.name)
                    )}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    {selectedGroups.length === parsedMib.groups.length ? 'Deselect All' : 'Select All'}
                  </button>
                </div>
                <div className="max-h-64 overflow-y-auto border border-gray-200 rounded-lg divide-y divide-gray-100">
                  {parsedMib.groups.map(group => (
                    <div
                      key={group.name}
                      onClick={() => toggleGroup(group.name)}
                      className={cn(
                        "px-3 py-2 cursor-pointer hover:bg-gray-50 flex items-center gap-3",
                        selectedGroups.includes(group.name) && "bg-blue-50"
                      )}
                    >
                      {selectedGroups.includes(group.name) ? (
                        <CheckSquare className="w-4 h-4 text-blue-600" />
                      ) : (
                        <Square className="w-4 h-4 text-gray-300" />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-gray-900 text-sm">{group.name}</div>
                        <div className="text-xs text-gray-500">
                          {group.objects?.length || 0} OIDs
                          {group.is_table && <span className="ml-2 text-blue-600">(table)</span>}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
        
        <div className="px-6 py-4 border-t border-gray-200 flex justify-between">
          {step === 'preview' && (
            <button
              onClick={() => { setStep('upload'); setParsedMib(null); setFile(null); }}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              Back
            </button>
          )}
          <div className="flex gap-3 ml-auto">
            <button onClick={onClose} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">
              Cancel
            </button>
            {step === 'upload' && (
              <button
                onClick={handleParse}
                disabled={!file || loading}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                Parse MIB
              </button>
            )}
            {step === 'preview' && (
              <button
                onClick={handleImport}
                disabled={loading || selectedGroups.length === 0}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                Import {selectedGroups.length} Groups
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Create Poll Type Modal
function CreatePollTypeModal({ profile, selectedOids, onClose, onCreated }) {
  const [name, setName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [description, setDescription] = useState('');
  const [targetTable, setTargetTable] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleSave = async () => {
    if (!name || !displayName) {
      setError('Name and Display Name are required');
      return;
    }
    try {
      setSaving(true);
      const data = await fetchApi(`${API_BASE}/profiles/${profile.id}/poll-types`, {
        method: 'POST',
        body: JSON.stringify({
          name,
          display_name: displayName,
          description,
          target_table: targetTable || null,
          group_ids: [...new Set(selectedOids.map(o => o.groupId))],
          enabled: true
        })
      });
      if (data.success) {
        onCreated(data.data.poll_type);
      } else {
        setError(data.message || 'Failed to create poll type');
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Create Poll Type from Selected OIDs</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">{error}</div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Poll Type Name (code)</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_'))}
              placeholder="e.g., ciena_optical_power"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Display Name</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g., Ciena Optical Power"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What this poll type collects..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              rows={2}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Target Database Table (optional)</label>
            <input
              type="text"
              value={targetTable}
              onChange={(e) => setTargetTable(e.target.value)}
              placeholder="e.g., optical_metrics"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Selected OIDs ({selectedOids.length})</label>
            <div className="max-h-40 overflow-y-auto bg-gray-50 rounded-lg p-3 text-xs font-mono space-y-1">
              {selectedOids.map((oid, i) => (
                <div key={i} className="flex justify-between text-gray-600">
                  <span className="font-medium">{oid.name}</span>
                  <span className="text-gray-400">{oid.oid}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !name || !displayName}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Create Poll Type
          </button>
        </div>
      </div>
    </div>
  );
}

// Test Poll Modal
function TestPollModal({ oid, onClose }) {
  const [host, setHost] = useState('');
  const [community, setCommunity] = useState('public');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const runTest = async () => {
    try {
      setLoading(true);
      setResult(null);
      const data = await fetchApi(`${API_BASE}/test-poll`, {
        method: 'POST',
        body: JSON.stringify({ host, community, oid: oid.oid })
      });
      setResult(data);
    } catch (e) {
      setResult({ success: false, message: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Test OID Poll</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <div className="bg-gray-50 p-3 rounded-lg">
            <div className="text-sm font-medium text-gray-700">{oid.name}</div>
            <div className="text-xs font-mono text-gray-500">{oid.oid}</div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Device IP</label>
            <input
              type="text"
              value={host}
              onChange={(e) => setHost(e.target.value)}
              placeholder="e.g., 10.127.0.130"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Community</label>
            <input
              type="text"
              value={community}
              onChange={(e) => setCommunity(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>
          {result && (
            <div className={cn(
              "p-3 rounded-lg text-sm",
              result.success ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
            )}>
              {result.success ? (
                <div>
                  <div className="font-medium mb-1">Result:</div>
                  {result.data?.results?.map((r, i) => (
                    <div key={i} className="font-mono text-xs">
                      {r.value} ({r.type})
                    </div>
                  ))}
                </div>
              ) : (
                <div>{result.message}</div>
              )}
            </div>
          )}
        </div>
        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">
            Close
          </button>
          <button
            onClick={runTest}
            disabled={loading || !host}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Test Poll
          </button>
        </div>
      </div>
    </div>
  );
}

export default function MibMappingsPage() {
  const [profiles, setProfiles] = useState([]);
  const [selectedProfile, setSelectedProfile] = useState(null);
  const [expandedGroups, setExpandedGroups] = useState({});
  const [selectedOids, setSelectedOids] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCreatePollType, setShowCreatePollType] = useState(false);
  const [showImportMib, setShowImportMib] = useState(false);
  const [testOid, setTestOid] = useState(null);

  useEffect(() => {
    loadProfiles();
  }, []);

  const loadProfiles = async () => {
    try {
      setLoading(true);
      const data = await fetchApi(`${API_BASE}/profiles`);
      // Handle both {success, data} and direct response formats
      const profileList = data?.data?.profiles || data?.profiles || (Array.isArray(data) ? data : []);
      setProfiles(profileList);
      if (profileList.length > 0) {
        loadProfile(profileList[0].id);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const loadProfile = async (profileId) => {
    try {
      setLoading(true);
      setSelectedOids([]);
      const data = await fetchApi(`${API_BASE}/profiles/${profileId}`);
      // Handle both {success, data} and direct response formats
      const profile = data?.data?.profile || data?.profile || data;
      setSelectedProfile(profile);
      // Expand all groups by default
      const expanded = {};
      profile?.groups?.forEach(g => { expanded[g.id] = true; });
      setExpandedGroups(expanded);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleGroup = (groupId) => {
    setExpandedGroups(prev => ({ ...prev, [groupId]: !prev[groupId] }));
  };

  const toggleOidSelection = (mapping, groupId, groupName) => {
    const key = `${groupId}-${mapping.id}`;
    const exists = selectedOids.find(o => o.key === key);
    if (exists) {
      setSelectedOids(prev => prev.filter(o => o.key !== key));
    } else {
      setSelectedOids(prev => [...prev, {
        key,
        groupId,
        groupName,
        id: mapping.id,
        name: mapping.name,
        oid: mapping.oid,
        mib_object_name: mapping.mib_object_name,
        data_type: mapping.data_type,
        transform: mapping.transform,
        unit: mapping.unit
      }]);
    }
  };

  const selectAllInGroup = (group) => {
    const groupOids = group.mappings.map(m => ({
      key: `${group.id}-${m.id}`,
      groupId: group.id,
      groupName: group.name,
      id: m.id,
      name: m.name,
      oid: m.oid,
      mib_object_name: m.mib_object_name,
      data_type: m.data_type,
      transform: m.transform,
      unit: m.unit
    }));
    const allSelected = groupOids.every(o => selectedOids.find(s => s.key === o.key));
    if (allSelected) {
      setSelectedOids(prev => prev.filter(o => o.groupId !== group.id));
    } else {
      setSelectedOids(prev => {
        const filtered = prev.filter(o => o.groupId !== group.id);
        return [...filtered, ...groupOids];
      });
    }
  };

  const isOidSelected = (groupId, mappingId) => {
    return selectedOids.some(o => o.key === `${groupId}-${mappingId}`);
  };

  const isGroupFullySelected = (group) => {
    return group.mappings?.every(m => isOidSelected(group.id, m.id));
  };

  const copyOid = (oid) => {
    navigator.clipboard.writeText(oid);
  };

  const formatTransform = (transform) => {
    if (!transform) return '-';
    const [op, val] = transform.split(':');
    if (op === 'divide') return `÷ ${val}`;
    if (op === 'multiply') return `× ${val}`;
    return transform;
  };

  const handlePollTypeCreated = (pollType) => {
    setShowCreatePollType(false);
    setSelectedOids([]);
    loadProfile(selectedProfile.id);
  };

  return (
    <PageLayout module="monitor">
      <PageHeader
        title="MIB Mapping Tool"
        description="Map SNMP OIDs to create poll types for polling jobs"
      />

      <div className="p-6 space-y-6">
        {/* Action Bar */}
        {selectedOids.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CheckSquare className="w-5 h-5 text-blue-600" />
              <span className="font-medium text-blue-900">{selectedOids.length} OIDs selected</span>
              <button
                onClick={() => setSelectedOids([])}
                className="text-sm text-blue-600 hover:underline"
              >
                Clear selection
              </button>
            </div>
            <button
              onClick={() => setShowCreatePollType(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
            >
              <Zap className="w-4 h-4" />
              Create Poll Type
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Profile List */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-4 py-3 border-b border-gray-200">
              <div className="flex items-center justify-between mb-2">
                <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                  <Database className="w-4 h-4" />
                  Vendor Profiles
                </h2>
                <button
                  onClick={loadProfiles}
                  className="p-1.5 text-gray-500 hover:bg-gray-100 rounded"
                  title="Refresh"
                >
                  <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
                </button>
              </div>
              <button
                onClick={() => setShowImportMib(true)}
                className="w-full px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center justify-center gap-2 text-sm font-medium"
              >
                <Upload className="w-4 h-4" />
                Import MIB File
              </button>
            </div>
            <div className="divide-y divide-gray-100 max-h-[500px] overflow-y-auto">
              {profiles.map(profile => (
                <div
                  key={profile.id}
                  onClick={() => loadProfile(profile.id)}
                  className={cn(
                    "px-4 py-3 cursor-pointer hover:bg-gray-50 transition-colors",
                    selectedProfile?.id === profile.id && "bg-blue-50 border-l-4 border-blue-600"
                  )}
                >
                  <div className="font-medium text-gray-900">{profile.vendor}</div>
                  <div className="text-sm text-gray-500">{profile.name}</div>
                  <div className="mt-1 text-xs text-gray-400">
                    {profile.group_count} groups • {profile.poll_type_count} poll types
                  </div>
                </div>
              ))}
              {profiles.length === 0 && !loading && (
                <div className="px-4 py-8 text-center text-gray-400 text-sm">
                  No profiles defined
                </div>
              )}
            </div>
          </div>

          {/* OID Groups and Mappings */}
          <div className="lg:col-span-3 space-y-4">
            {selectedProfile ? (
              <>
                {/* Profile Header */}
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h2 className="text-xl font-bold text-gray-900">
                        {selectedProfile.vendor} - {selectedProfile.name}
                      </h2>
                      <p className="text-gray-500 mt-1">{selectedProfile.description}</p>
                      <div className="mt-2 text-sm text-gray-600">
                        <span className="font-mono bg-gray-100 px-2 py-1 rounded">
                          Enterprise OID: {selectedProfile.enterprise_oid}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Instructions */}
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
                  <strong>How to use:</strong> Select OIDs from the groups below, then click "Create Poll Type" to create a new poll type that can be used in Polling Management.
                </div>

                {/* OID Groups */}
                <div className="space-y-3">
                  {selectedProfile.groups?.map(group => (
                    <div key={group.id} className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                      {/* Group Header */}
                      <div
                        className="px-4 py-3 bg-gray-50 flex items-center justify-between cursor-pointer hover:bg-gray-100"
                        onClick={() => toggleGroup(group.id)}
                      >
                        <div className="flex items-center gap-3">
                          {expandedGroups[group.id] ? (
                            <ChevronDown className="w-4 h-4 text-gray-400" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-gray-400" />
                          )}
                          <div>
                            <div className="font-semibold text-gray-900 flex items-center gap-2">
                              {group.name}
                              {group.is_table && (
                                <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-normal">
                                  TABLE
                                </span>
                              )}
                            </div>
                            <div className="text-xs text-gray-500">
                              {group.mib_name} • {group.mappings?.length || 0} OIDs
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-mono text-gray-400">{group.base_oid}</span>
                          <button
                            onClick={(e) => { e.stopPropagation(); selectAllInGroup(group); }}
                            className={cn(
                              "px-2 py-1 text-xs rounded",
                              isGroupFullySelected(group)
                                ? "bg-blue-600 text-white"
                                : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                            )}
                          >
                            {isGroupFullySelected(group) ? 'Deselect All' : 'Select All'}
                          </button>
                        </div>
                      </div>

                      {/* Group Mappings */}
                      {expandedGroups[group.id] && (
                        <div className="border-t border-gray-200">
                          <table className="w-full text-sm">
                            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                              <tr>
                                <th className="px-3 py-2 text-left w-10"></th>
                                <th className="px-3 py-2 text-left">Name</th>
                                <th className="px-3 py-2 text-left">OID</th>
                                <th className="px-3 py-2 text-left">Type</th>
                                <th className="px-3 py-2 text-left">Transform</th>
                                <th className="px-3 py-2 text-left">Unit</th>
                                <th className="px-3 py-2 text-left">Actions</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                              {group.mappings?.map(mapping => (
                                <tr
                                  key={mapping.id}
                                  className={cn(
                                    "hover:bg-gray-50 cursor-pointer",
                                    isOidSelected(group.id, mapping.id) && "bg-blue-50"
                                  )}
                                  onClick={() => toggleOidSelection(mapping, group.id, group.name)}
                                >
                                  <td className="px-3 py-2">
                                    {isOidSelected(group.id, mapping.id) ? (
                                      <CheckSquare className="w-4 h-4 text-blue-600" />
                                    ) : (
                                      <Square className="w-4 h-4 text-gray-300" />
                                    )}
                                  </td>
                                  <td className="px-3 py-2">
                                    <div className="font-medium text-gray-900">
                                      {mapping.is_index && <span className="text-blue-600 mr-1">🔑</span>}
                                      {mapping.name}
                                    </div>
                                    <div className="text-xs text-gray-400">{mapping.mib_object_name}</div>
                                  </td>
                                  <td className="px-3 py-2">
                                    <code className="text-xs text-gray-600 font-mono">{mapping.oid}</code>
                                  </td>
                                  <td className="px-3 py-2 text-gray-600">{mapping.data_type}</td>
                                  <td className="px-3 py-2 text-gray-600">{formatTransform(mapping.transform)}</td>
                                  <td className="px-3 py-2 text-gray-600">{mapping.unit || '-'}</td>
                                  <td className="px-3 py-2">
                                    <div className="flex items-center gap-1">
                                      <button
                                        onClick={(e) => { e.stopPropagation(); copyOid(mapping.oid); }}
                                        className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded"
                                        title="Copy OID"
                                      >
                                        <Copy className="w-3.5 h-3.5" />
                                      </button>
                                      <button
                                        onClick={(e) => { e.stopPropagation(); setTestOid(mapping); }}
                                        className="p-1 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded"
                                        title="Test Poll"
                                      >
                                        <Play className="w-3.5 h-3.5" />
                                      </button>
                                    </div>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Existing Poll Types */}
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
                  <div className="px-4 py-3 border-b border-gray-200">
                    <h3 className="font-semibold text-gray-900">Existing Poll Types ({selectedProfile.poll_types?.length || 0})</h3>
                  </div>
                  {selectedProfile.poll_types?.length > 0 ? (
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                        <tr>
                          <th className="px-4 py-2 text-left">Name</th>
                          <th className="px-4 py-2 text-left">Display Name</th>
                          <th className="px-4 py-2 text-left">Description</th>
                          <th className="px-4 py-2 text-left">Target Table</th>
                          <th className="px-4 py-2 text-left">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {selectedProfile.poll_types?.map(pt => (
                          <tr key={pt.id} className="hover:bg-gray-50">
                            <td className="px-4 py-2 font-mono text-gray-900">{pt.name}</td>
                            <td className="px-4 py-2 font-medium text-gray-900">{pt.display_name}</td>
                            <td className="px-4 py-2 text-gray-600 max-w-xs truncate">{pt.description}</td>
                            <td className="px-4 py-2 font-mono text-gray-600">{pt.target_table || '-'}</td>
                            <td className="px-4 py-2">
                              <span className={cn(
                                "px-2 py-1 text-xs font-bold rounded",
                                pt.enabled ? "bg-green-600 text-white" : "bg-gray-300 text-gray-600"
                              )}>
                                {pt.enabled ? 'ENABLED' : 'DISABLED'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="px-4 py-8 text-center text-gray-400 text-sm">
                      No poll types defined. Select OIDs above to create one.
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 text-center text-gray-400">
                <Database className="w-16 h-16 mx-auto mb-4 opacity-30" />
                <p className="text-lg">Select a vendor profile to view MIB OID mappings</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modals */}
      {showCreatePollType && selectedProfile && (
        <CreatePollTypeModal
          profile={selectedProfile}
          selectedOids={selectedOids}
          onClose={() => setShowCreatePollType(false)}
          onCreated={handlePollTypeCreated}
        />
      )}

      {testOid && (
        <TestPollModal
          oid={testOid}
          onClose={() => setTestOid(null)}
        />
      )}

      {showImportMib && (
        <ImportMibModal
          profiles={profiles}
          onClose={() => setShowImportMib(false)}
          onImported={(result) => {
            setShowImportMib(false);
            loadProfiles();
            if (result.profile_id) {
              loadProfile(result.profile_id);
            }
          }}
        />
      )}
    </PageLayout>
  );
}
