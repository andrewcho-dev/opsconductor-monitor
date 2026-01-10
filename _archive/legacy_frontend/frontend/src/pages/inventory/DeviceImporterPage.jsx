import React, { useState, useEffect, useCallback } from "react";
import { PageLayout, PageHeader } from "../../components/layout";
import { fetchApi } from "../../lib/utils";
import {
  Download,
  RefreshCw,
  Server,
  Network,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Search,
  Filter,
  Upload,
  Database,
  Globe,
  Eye,
  Play,
} from "lucide-react";

function StatCard({ title, value, icon: Icon, color, subtitle }) {
  const colors = {
    blue: "bg-blue-100 text-blue-600",
    green: "bg-green-100 text-green-600",
    red: "bg-red-100 text-red-600",
    yellow: "bg-yellow-100 text-yellow-600",
    purple: "bg-purple-100 text-purple-600",
    orange: "bg-orange-100 text-orange-600",
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value ?? "--"}</p>
          {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
        </div>
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colors[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}

function DeviceTable({ devices, selectedIds, onSelectChange, title, showStatus = true }) {
  const [expanded, setExpanded] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  const filteredDevices = devices.filter(
    (d) =>
      d.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      d.host?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      d.group?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const allSelected = filteredDevices.length > 0 && filteredDevices.every((d) => selectedIds.has(d.prtg_id));

  const toggleAll = () => {
    if (allSelected) {
      const newSet = new Set(selectedIds);
      filteredDevices.forEach((d) => newSet.delete(d.prtg_id));
      onSelectChange(newSet);
    } else {
      const newSet = new Set(selectedIds);
      filteredDevices.forEach((d) => newSet.add(d.prtg_id));
      onSelectChange(newSet);
    }
  };

  const toggleOne = (id) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    onSelectChange(newSet);
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <div
        className="px-4 py-3 border-b border-gray-200 flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide flex items-center gap-2">
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          {title} ({devices.length})
        </h2>
        {expanded && (
          <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <div className="relative">
              <Search className="w-4 h-4 absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8 pr-3 py-1 text-sm border border-gray-300 rounded-lg w-48"
              />
            </div>
          </div>
        )}
      </div>
      {expanded && (
        <div className="overflow-x-auto max-h-96">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase sticky top-0">
              <tr>
                <th className="px-3 py-2 w-10">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleAll}
                    className="rounded border-gray-300"
                  />
                </th>
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">IP Address</th>
                <th className="px-3 py-2">Group</th>
                {showStatus && <th className="px-3 py-2">Status</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredDevices.map((device) => (
                <tr key={device.prtg_id} className="hover:bg-gray-50">
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(device.prtg_id)}
                      onChange={() => toggleOne(device.prtg_id)}
                      className="rounded border-gray-300"
                    />
                  </td>
                  <td className="px-3 py-2 font-medium">{device.name}</td>
                  <td className="px-3 py-2 font-mono text-xs">{device.host}</td>
                  <td className="px-3 py-2 text-gray-500">{device.group}</td>
                  {showStatus && (
                    <td className="px-3 py-2">
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded-full ${
                          device.status === "new"
                            ? "bg-green-100 text-green-700"
                            : device.status === "exists"
                            ? "bg-gray-100 text-gray-600"
                            : device.status === "update"
                            ? "bg-blue-100 text-blue-700"
                            : "bg-yellow-100 text-yellow-700"
                        }`}
                      >
                        {device.status}
                      </span>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          {filteredDevices.length === 0 && (
            <div className="p-8 text-center text-gray-500">No devices found</div>
          )}
        </div>
      )}
    </div>
  );
}

function ImportResults({ results, title }) {
  if (!results) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="px-4 py-3 border-b border-gray-200">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">{title}</h2>
      </div>
      <div className="p-4">
        <div className="grid grid-cols-4 gap-4 mb-4">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-gray-900">{results.processed || 0}</div>
            <div className="text-xs text-gray-500">Processed</div>
          </div>
          <div className="text-center p-3 bg-green-50 rounded-lg">
            <div className="text-2xl font-bold text-green-600">{results.created || 0}</div>
            <div className="text-xs text-gray-500">Created</div>
          </div>
          <div className="text-center p-3 bg-blue-50 rounded-lg">
            <div className="text-2xl font-bold text-blue-600">{results.updated || 0}</div>
            <div className="text-xs text-gray-500">Updated</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-gray-500">{results.skipped || 0}</div>
            <div className="text-xs text-gray-500">Skipped</div>
          </div>
        </div>

        {results.errors?.length > 0 && (
          <div className="mt-4">
            <h3 className="text-sm font-medium text-red-600 mb-2">Errors ({results.errors.length})</h3>
            <div className="bg-red-50 rounded-lg p-3 max-h-32 overflow-y-auto">
              {results.errors.map((err, i) => (
                <div key={i} className="text-sm text-red-700">
                  {err.device || err.name}: {err.error}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function DeviceImporterPage() {
  const [loading, setLoading] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState(null);

  const [prtgDevices, setPrtgDevices] = useState([]);
  const [preview, setPreview] = useState(null);
  const [importResults, setImportResults] = useState(null);

  const [selectedIds, setSelectedIds] = useState(new Set());
  const [importTarget, setImportTarget] = useState("opsconductor");
  const [updateExisting, setUpdateExisting] = useState(false);
  const [dryRun, setDryRun] = useState(true);

  // NetBox settings
  const [netboxSiteId, setNetboxSiteId] = useState("");
  const [netboxRoleId, setNetboxRoleId] = useState("");
  const [netboxDeviceTypeId, setNetboxDeviceTypeId] = useState("");

  const discoverDevices = useCallback(async () => {
    setDiscovering(true);
    setError(null);
    try {
      const response = await fetchApi("/integrations/v1/import/discover?include_sensors=true");
      if (response.success) {
        setPrtgDevices(response.devices || []);
        // Auto-select all new devices
        const newIds = new Set(response.devices?.map((d) => d.objid) || []);
        setSelectedIds(newIds);
      } else {
        setError(response.error || "Failed to discover devices");
      }
    } catch (err) {
      setError(err.message || "Failed to discover devices");
    } finally {
      setDiscovering(false);
    }
  }, []);

  const previewImport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchApi(`/integrations/v1/import/preview?target=${importTarget}`);
      if (response.success) {
        setPreview(response);
      } else {
        setError(response.error || "Failed to preview import");
      }
    } catch (err) {
      setError(err.message || "Failed to preview import");
    } finally {
      setLoading(false);
    }
  }, [importTarget]);

  const runImport = useCallback(async () => {
    setImporting(true);
    setError(null);
    setImportResults(null);

    try {
      const deviceIds = selectedIds.size > 0 ? Array.from(selectedIds) : null;

      let endpoint = "/integrations/v1/import/opsconductor";
      let body = {
        device_ids: deviceIds,
        update_existing: updateExisting,
        create_missing: true,
        dry_run: dryRun,
      };

      if (importTarget === "netbox") {
        endpoint = "/integrations/v1/import/netbox";
        body = {
          ...body,
          site_id: netboxSiteId ? parseInt(netboxSiteId) : null,
          role_id: netboxRoleId ? parseInt(netboxRoleId) : null,
          device_type_id: netboxDeviceTypeId ? parseInt(netboxDeviceTypeId) : null,
        };
      } else if (importTarget === "all") {
        endpoint = "/integrations/v1/import/all";
        body = {
          device_ids: deviceIds,
          update_existing: updateExisting,
          dry_run: dryRun,
          netbox_site_id: netboxSiteId ? parseInt(netboxSiteId) : null,
          netbox_role_id: netboxRoleId ? parseInt(netboxRoleId) : null,
          netbox_device_type_id: netboxDeviceTypeId ? parseInt(netboxDeviceTypeId) : null,
        };
      }

      const response = await fetchApi(endpoint, {
        method: "POST",
        body: JSON.stringify(body),
      });

      setImportResults(response);

      if (!dryRun && response.success) {
        // Refresh preview after actual import
        await previewImport();
      }
    } catch (err) {
      setError(err.message || "Import failed");
    } finally {
      setImporting(false);
    }
  }, [selectedIds, importTarget, updateExisting, dryRun, netboxSiteId, netboxRoleId, netboxDeviceTypeId, previewImport]);

  // Initial load
  useEffect(() => {
    discoverDevices();
  }, []);

  // Get preview data for display
  const netboxPreview = preview?.netbox_preview;
  const opsPreview = preview?.opsconductor_preview;

  return (
    <PageLayout module="inventory">
      <PageHeader
        title="Device Importer"
        description="Import devices from PRTG to NetBox and OpsConductor"
        icon={Download}
        actions={
          <div className="flex items-center gap-3">
            <button
              onClick={discoverDevices}
              disabled={discovering}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${discovering ? "animate-spin" : ""}`} />
              Refresh
            </button>
            <button
              onClick={previewImport}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              <Eye className="w-4 h-4" />
              Preview
            </button>
          </div>
        }
      />

      <div className="p-6 space-y-6">
        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
            <XCircle className="w-5 h-5 text-red-500" />
            <span className="text-red-700">{error}</span>
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            title="PRTG Devices"
            value={prtgDevices.length}
            icon={Server}
            color="blue"
          />
          <StatCard
            title="Selected"
            value={selectedIds.size}
            icon={CheckCircle}
            color="green"
          />
          <StatCard
            title="New to OpsConductor"
            value={opsPreview?.new_count ?? "--"}
            icon={Database}
            color="purple"
          />
          <StatCard
            title="New to NetBox"
            value={netboxPreview?.new_count ?? "--"}
            icon={Globe}
            color="orange"
          />
        </div>

        {/* Import Controls */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">Import Settings</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Target</label>
              <select
                value={importTarget}
                onChange={(e) => setImportTarget(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="opsconductor">OpsConductor Only</option>
                <option value="netbox">NetBox Only</option>
                <option value="all">Both</option>
              </select>
            </div>

            {(importTarget === "netbox" || importTarget === "all") && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">NetBox Site ID</label>
                  <input
                    type="number"
                    value={netboxSiteId}
                    onChange={(e) => setNetboxSiteId(e.target.value)}
                    placeholder="Default site"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">NetBox Role ID</label>
                  <input
                    type="number"
                    value={netboxRoleId}
                    onChange={(e) => setNetboxRoleId(e.target.value)}
                    placeholder="Default role"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
              </>
            )}

            <div className="flex items-end gap-4">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={updateExisting}
                  onChange={(e) => setUpdateExisting(e.target.checked)}
                  className="rounded border-gray-300"
                />
                <span className="text-sm text-gray-700">Update existing</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={dryRun}
                  onChange={(e) => setDryRun(e.target.checked)}
                  className="rounded border-gray-300"
                />
                <span className="text-sm text-gray-700">Dry run</span>
              </label>
            </div>
          </div>

          <div className="mt-4 flex justify-end">
            <button
              onClick={runImport}
              disabled={importing || selectedIds.size === 0}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg disabled:opacity-50 ${
                dryRun
                  ? "text-gray-700 bg-gray-100 hover:bg-gray-200"
                  : "text-white bg-green-600 hover:bg-green-700"
              }`}
            >
              {importing ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              {dryRun ? "Preview Import" : "Run Import"}
            </button>
          </div>
        </div>

        {/* Import Results */}
        {importResults && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {importResults.opsconductor && (
              <ImportResults results={importResults.opsconductor} title="OpsConductor Results" />
            )}
            {importResults.netbox && (
              <ImportResults results={importResults.netbox} title="NetBox Results" />
            )}
            {!importResults.opsconductor && !importResults.netbox && (
              <ImportResults results={importResults} title="Import Results" />
            )}
          </div>
        )}

        {/* Device Tables */}
        {preview && (
          <div className="space-y-6">
            {/* New devices to create */}
            {opsPreview?.to_create?.length > 0 && (
              <DeviceTable
                devices={opsPreview.to_create}
                selectedIds={selectedIds}
                onSelectChange={setSelectedIds}
                title="New Devices (will be created)"
              />
            )}

            {/* Existing devices */}
            {opsPreview?.to_update?.length > 0 && (
              <DeviceTable
                devices={opsPreview.to_update}
                selectedIds={selectedIds}
                onSelectChange={setSelectedIds}
                title="Existing Devices (can be updated)"
              />
            )}
          </div>
        )}

        {/* PRTG Devices (if no preview yet) */}
        {!preview && prtgDevices.length > 0 && (
          <DeviceTable
            devices={prtgDevices.map((d) => ({
              prtg_id: d.objid,
              name: d.device,
              host: d.host,
              group: d.group,
              status: d.status_text,
            }))}
            selectedIds={selectedIds}
            onSelectChange={setSelectedIds}
            title="PRTG Devices"
            showStatus={true}
          />
        )}

        {/* Empty State */}
        {!discovering && prtgDevices.length === 0 && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 text-center">
            <Server className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Devices Found</h3>
            <p className="text-gray-500 mb-4">
              Make sure PRTG is configured in System Settings and has devices to import.
            </p>
            <button
              onClick={discoverDevices}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Loading State */}
        {discovering && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 text-center">
            <RefreshCw className="w-16 h-16 text-blue-500 mx-auto mb-4 animate-spin" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Discovering Devices...</h3>
            <p className="text-gray-500">Fetching devices from PRTG.</p>
          </div>
        )}
      </div>
    </PageLayout>
  );
}
