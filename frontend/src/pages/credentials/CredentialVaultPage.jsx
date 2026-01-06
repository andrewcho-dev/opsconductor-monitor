/**
 * CredentialVaultPage
 * 
 * Main page for managing credentials, groups, audit logs, and enterprise auth.
 * Components are extracted to ./components/ for maintainability.
 */

import React, { useState, useEffect } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';
import { 
  Plus, Search, RefreshCw, KeyRound, Clock,
  AlertTriangle, CheckCircle, XCircle, Activity
} from 'lucide-react';
import { PageLayout } from '../../components/layout/PageLayout';
import { fetchApi, cn } from '../../lib/utils';
import {
  CREDENTIAL_TYPES,
  StatCard,
  CredentialsList,
  GroupsList,
  AuditLogView,
  CredentialModal,
  CredentialHistoryModal,
  EnterpriseAuthConfigsList,
  EnterpriseAuthUsersList,
} from './components';
import { DeviceSelectionModal } from '../../components/common/DeviceSelectionModal';

export function CredentialVaultPage() {
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  
  const getActiveView = () => {
    if (location.pathname.includes('/enterprise/users')) return 'enterprise-users';
    if (location.pathname.includes('/enterprise')) return 'enterprise';
    if (location.pathname.includes('/groups')) return 'groups';
    if (location.pathname.includes('/expiring')) return 'expiring';
    if (location.pathname.includes('/audit')) return 'audit';
    return 'credentials';
  };
  
  const [activeView, setActiveView] = useState(getActiveView());
  const [credentials, setCredentials] = useState([]);
  const [groups, setGroups] = useState([]);
  const [auditLog, setAuditLog] = useState([]);
  const [enterpriseConfigs, setEnterpriseConfigs] = useState([]);
  const [enterpriseUsers, setEnterpriseUsers] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState(searchParams.get('type') || '');
  const [statusFilter, setStatusFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingCredential, setEditingCredential] = useState(null);
  const [selectedCredential, setSelectedCredential] = useState(null);
  const [deviceModalCredential, setDeviceModalCredential] = useState(null);
  const [assignedDeviceIps, setAssignedDeviceIps] = useState([]);

  useEffect(() => {
    setActiveView(getActiveView());
  }, [location.pathname]);

  useEffect(() => {
    const urlType = searchParams.get('type') || '';
    if (urlType !== typeFilter) {
      setTypeFilter(urlType);
    }
  }, [searchParams]);

  useEffect(() => {
    loadData();
  }, [activeView, typeFilter, statusFilter]);

  const loadData = async () => {
    setLoading(true);
    try {
      const statsRes = await fetchApi('/credentials/v1/credentials/statistics');
      // Handle both {success, data} and direct response formats
      const statsData = statsRes?.data || statsRes;
      if (statsData?.statistics) {
        setStatistics(statsData.statistics);
      }

      if (activeView === 'credentials' || activeView === 'expiring') {
        let url = '/credentials/v1/credentials';
        const params = new URLSearchParams();
        if (typeFilter) params.append('type', typeFilter);
        if (statusFilter) params.append('status', statusFilter);
        if (activeView === 'expiring') {
          url = '/credentials/v1/credentials/expiring?days=30';
        } else if (params.toString()) {
          url += '?' + params.toString();
        }
        
        const res = await fetchApi(url);
        const resData = res?.data || res;
        const credList = activeView === 'expiring' ? (resData?.expiring || resData?.items || []) : (resData?.credentials || resData?.items || []);
        setCredentials(credList);
      } else if (activeView === 'groups') {
        const res = await fetchApi('/credentials/v1/credentials/groups');
        const resData = res?.data || res;
        setGroups(resData?.groups || resData || []);
      } else if (activeView === 'audit') {
        const res = await fetchApi('/credentials/v1/credentials/audit?limit=100');
        const resData = res?.data || res;
        setAuditLog(resData?.entries || resData || []);
      } else if (activeView === 'enterprise') {
        const [configsRes, credsRes] = await Promise.all([
          fetchApi('/credentials/v1/credentials/enterprise/configs'),
          fetchApi('/credentials/v1/credentials')
        ]);
        const configsData = configsRes?.data || configsRes;
        setEnterpriseConfigs(configsData?.configs || []);
        const credsData = credsRes?.data || credsRes;
        setCredentials(credsData?.credentials || credsData?.items || []);
      } else if (activeView === 'enterprise-users') {
        const [usersRes, configsRes] = await Promise.all([
          fetchApi('/credentials/v1/credentials/enterprise/users'),
          fetchApi('/credentials/v1/credentials/enterprise/configs')
        ]);
        const usersData = usersRes?.data || usersRes;
        setEnterpriseUsers(usersData?.users || []);
        const configsData = configsRes?.data || configsRes;
        setEnterpriseConfigs(configsData?.configs || []);
      }
    } catch (err) {
      // Error loading data
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this credential?')) return;
    try {
      await fetchApi(`/credentials/v1/credentials/${id}`, { method: 'DELETE' });
      loadData();
    } catch (err) {
      alert('Error deleting credential: ' + err.message);
    }
  };

  const openDeviceModal = async (credential) => {
    setDeviceModalCredential(credential);
    try {
      const res = await fetchApi(`/credentials/v1/credentials/${credential.id}/devices`);
      const ips = (res.data?.devices || []).map(d => d.ip_address);
      setAssignedDeviceIps(ips);
    } catch (err) {
      console.error('Error loading assigned devices:', err);
      setAssignedDeviceIps([]);
    }
  };

  const handleDeviceSave = async (selectedIps) => {
    if (!deviceModalCredential) return;
    
    const currentIps = new Set(assignedDeviceIps);
    const newIps = new Set(selectedIps);
    
    // Find IPs to add and remove
    const toAdd = selectedIps.filter(ip => !currentIps.has(ip));
    const toRemove = assignedDeviceIps.filter(ip => !newIps.has(ip));
    
    // Process additions
    for (const ip of toAdd) {
      await fetchApi(`/credentials/v1/credentials/devices/${ip}/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential_id: deviceModalCredential.id }),
      });
    }
    
    // Process removals
    for (const ip of toRemove) {
      await fetchApi(`/credentials/v1/credentials/devices/${ip}/unassign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential_id: deviceModalCredential.id }),
      });
    }
    
    loadData();
  };

  const filteredCredentials = credentials.filter(cred => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      cred.name?.toLowerCase().includes(query) ||
      cred.description?.toLowerCase().includes(query) ||
      cred.username?.toLowerCase().includes(query) ||
      cred.owner?.toLowerCase().includes(query)
    );
  });

  return (
    <PageLayout module="credentials">
      <div className="p-6 space-y-6">
        {/* Header with Stats */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Credential Vault</h1>
            <p className="text-sm text-gray-500 mt-1">
              Secure storage for all authentication credentials
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadData}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
              title="Refresh"
            >
              <RefreshCw className={cn("w-5 h-5", loading && "animate-spin")} />
            </button>
            <button
              onClick={() => { setEditingCredential(null); setShowModal(true); }}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" />
              Add Credential
            </button>
          </div>
        </div>

        {/* Statistics Cards */}
        {statistics && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <StatCard
              label="Total"
              value={statistics.total}
              icon={KeyRound}
              color="blue"
            />
            <StatCard
              label="Active"
              value={statistics.by_status?.active || 0}
              icon={CheckCircle}
              color="green"
            />
            <StatCard
              label="Expiring Soon"
              value={statistics.expiration?.expiring_30_days || 0}
              icon={Clock}
              color="amber"
            />
            <StatCard
              label="Expired"
              value={statistics.expiration?.expired || 0}
              icon={XCircle}
              color="red"
            />
            <StatCard
              label="Used (30d)"
              value={statistics.usage?.used_last_30_days || 0}
              icon={Activity}
              color="purple"
            />
            <StatCard
              label="Unused (90d)"
              value={statistics.usage?.unused_90_days || 0}
              icon={AlertTriangle}
              color="gray"
            />
          </div>
        )}

        {/* Filters */}
        {activeView === 'credentials' && (
          <div className="flex flex-wrap items-center gap-4 bg-white p-4 rounded-lg border">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search credentials..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border rounded-lg"
                />
              </div>
            </div>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="px-3 py-2 border rounded-lg"
            >
              <option value="">All Types</option>
              {Object.entries(CREDENTIAL_TYPES).map(([key, { label }]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 border rounded-lg"
            >
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="expired">Expired</option>
              <option value="disabled">Disabled</option>
            </select>
          </div>
        )}

        {/* Main Content */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        ) : activeView === 'credentials' || activeView === 'expiring' ? (
          <CredentialsList
            credentials={filteredCredentials}
            onEdit={(cred) => { setEditingCredential(cred); setShowModal(true); }}
            onDelete={handleDelete}
            onViewHistory={(cred) => setSelectedCredential(cred)}
            onManageDevices={openDeviceModal}
            isExpiring={activeView === 'expiring'}
          />
        ) : activeView === 'groups' ? (
          <GroupsList groups={groups} onRefresh={loadData} />
        ) : activeView === 'audit' ? (
          <AuditLogView entries={auditLog} />
        ) : activeView === 'enterprise' ? (
          <EnterpriseAuthConfigsList configs={enterpriseConfigs} credentials={credentials} onRefresh={loadData} />
        ) : activeView === 'enterprise-users' ? (
          <EnterpriseAuthUsersList users={enterpriseUsers} configs={enterpriseConfigs} onRefresh={loadData} />
        ) : null}
      </div>

      {/* Credential Modal */}
      {showModal && (
        <CredentialModal
          credential={editingCredential}
          onClose={() => setShowModal(false)}
          onSave={() => { setShowModal(false); loadData(); }}
        />
      )}

      {/* History Modal */}
      {selectedCredential && (
        <CredentialHistoryModal
          credential={selectedCredential}
          onClose={() => setSelectedCredential(null)}
        />
      )}

      {/* Device Selection Modal */}
      <DeviceSelectionModal
        isOpen={!!deviceModalCredential}
        onClose={() => setDeviceModalCredential(null)}
        onSave={handleDeviceSave}
        initialSelected={assignedDeviceIps}
        title={deviceModalCredential ? `Devices for ${deviceModalCredential.name}` : 'Select Devices'}
      />
    </PageLayout>
  );
}

export default CredentialVaultPage;
