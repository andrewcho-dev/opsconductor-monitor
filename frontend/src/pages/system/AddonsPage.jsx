/**
 * Addons Management Page
 * 
 * UI for managing connector/normalizer addons.
 * Supports viewing, enabling/disabling, installing, and uninstalling addons.
 */

import { useState, useEffect, useRef } from 'react';
import { 
  Package, Power, PowerOff, Upload, Trash2, Download,
  RefreshCw, Server, Radio, AlertCircle, Plus, Loader2
} from 'lucide-react';
import { PageLayout, PageHeader } from '../../components/layout';
import { useAddons } from '../../hooks/useAddons';

const categoryIcons = {
  nms: Server,
  device: Radio,
};

const categoryLabels = {
  nms: 'NMS Connectors',
  device: 'Device Connectors',
};

export default function AddonsPage() {
  const { 
    addons, 
    loading, 
    error, 
    fetchAddons, 
    enableAddon, 
    disableAddon, 
    installAddon, 
    uninstallAddon,
    reinstallAddon 
  } = useAddons();
  
  const [activeTab, setActiveTab] = useState('all');
  const [uploading, setUploading] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const fileInputRef = useRef(null);
  
  useEffect(() => {
    fetchAddons();
  }, [fetchAddons]);
  
  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setUploading(true);
    try {
      await installAddon(file);
      alert('Addon installed successfully');
    } catch (err) {
      alert('Error installing addon: ' + err.message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };
  
  const handleToggle = async (addon) => {
    setActionLoading(addon.id);
    try {
      if (addon.enabled) {
        await disableAddon(addon.id);
      } else {
        await enableAddon(addon.id);
      }
      fetchAddons();
    } catch (err) {
      alert('Error: ' + err.message);
    } finally {
      setActionLoading(null);
    }
  };
  
  const handleUninstall = async (addon) => {
    const msg = addon.is_builtin 
      ? `Uninstall "${addon.name}"? This will remove all DB mappings but you can reinstall it later.`
      : `Are you sure you want to uninstall "${addon.name}"? This will permanently delete all addon files.`;
    if (!confirm(msg)) return;
    setActionLoading(addon.id);
    try {
      await uninstallAddon(addon.id);
      fetchAddons();
    } catch (err) {
      alert('Error: ' + err.message);
    } finally {
      setActionLoading(null);
    }
  };
  
  const handleReinstall = async (addon) => {
    if (!confirm(`Reinstall "${addon.name}"? This will restore all DB mappings.`)) return;
    setActionLoading(addon.id);
    try {
      await reinstallAddon(addon.id);
      fetchAddons();
    } catch (err) {
      alert('Error: ' + err.message);
    } finally {
      setActionLoading(null);
    }
  };
  
  const filteredAddons = activeTab === 'all' 
    ? addons 
    : addons.filter(a => a.category === activeTab);

  const tabs = [
    { id: 'all', label: 'All', count: addons.length },
    { id: 'nms', label: 'NMS', count: addons.filter(a => a.category === 'nms').length },
    { id: 'device', label: 'Device', count: addons.filter(a => a.category === 'device').length },
  ];

  if (loading) {
    return (
      <PageLayout module="connectors">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout module="connectors">
      <PageHeader
        title="Addons"
        description="Manage connector and normalizer plugins"
        icon={Package}
        actions={
          <>
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip"
              onChange={handleFileSelect}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
            >
              {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Install Addon
            </button>
          </>
        }
      />

      {/* Tabs */}
      <div className="px-6 pt-4">
        <div className="flex gap-1 border-b border-gray-200">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
              <span className="ml-2 px-1.5 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600">
                {tab.count}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="p-6">
        {error && (
          <div className="mb-4 flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            <AlertCircle className="w-5 h-5" />
            {error}
          </div>
        )}

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="px-4 py-3 border-b border-gray-200">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              {activeTab === 'all' ? 'All Connectors' : categoryLabels[activeTab]}
            </h2>
          </div>

          {filteredAddons.length === 0 ? (
            <div className="p-8 text-center">
              <Package className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">No addons found</p>
              <button 
                onClick={() => fileInputRef.current?.click()}
                className="mt-3 text-sm text-blue-600 hover:underline"
              >
                Install your first addon
              </button>
            </div>
          ) : (
            <div className="p-4 space-y-3">
              {filteredAddons.map((addon) => {
                const Icon = categoryIcons[addon.category] || Package;
                const isInstalled = addon.installed !== false;
                return (
                  <div key={addon.id} className={`border rounded-lg p-4 ${
                    isInstalled ? 'border-gray-200' : 'border-dashed border-gray-300 bg-gray-50'
                  }`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          !isInstalled ? 'bg-gray-200' : addon.enabled ? 'bg-blue-100' : 'bg-gray-100'
                        }`}>
                          <Icon className={`w-5 h-5 ${
                            !isInstalled ? 'text-gray-400' : addon.enabled ? 'text-blue-600' : 'text-gray-400'
                          }`} />
                        </div>
                        <div>
                          <div className={`font-medium ${isInstalled ? 'text-gray-900' : 'text-gray-500'}`}>
                            {addon.name}
                          </div>
                          <div className="text-xs text-gray-400">
                            v{addon.version} • {categoryLabels[addon.category]}
                            {addon.is_builtin && (
                              <span className="ml-2 px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
                                Built-in
                              </span>
                            )}
                            {!isInstalled && (
                              <span className="ml-2 px-1.5 py-0.5 bg-orange-100 text-orange-700 rounded text-xs">
                                Not Installed
                              </span>
                            )}
                          </div>
                          <div className="text-sm text-gray-500 mt-1">{addon.description}</div>
                          {addon.capabilities && addon.capabilities.length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              {addon.capabilities.map(cap => (
                                <span key={cap} className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">
                                  {cap}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {isInstalled ? (
                          <>
                            <button
                              onClick={() => handleToggle(addon)}
                              disabled={actionLoading === addon.id}
                              className={`px-2 py-1 text-xs font-medium rounded-full cursor-pointer ${
                                addon.enabled 
                                  ? 'bg-green-100 text-green-700 hover:bg-green-200' 
                                  : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                              }`}
                            >
                              {actionLoading === addon.id ? '...' : (addon.enabled ? 'ON' : 'OFF')}
                            </button>
                            <button 
                              onClick={() => handleUninstall(addon)}
                              disabled={actionLoading === addon.id}
                              className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg"
                              title="Uninstall"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </>
                        ) : (
                          <button 
                            onClick={() => handleReinstall(addon)}
                            disabled={actionLoading === addon.id}
                            className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                          >
                            {actionLoading === addon.id ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Download className="w-4 h-4" />
                            )}
                            Reinstall
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  );
}
