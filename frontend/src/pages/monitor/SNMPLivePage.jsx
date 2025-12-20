import React, { useState, useEffect, useCallback } from "react";
import { PageLayout, PageHeader } from "../../components/layout";
import { fetchApi } from "../../lib/utils";
import { 
  Activity, 
  RefreshCw, 
  Server,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Thermometer,
  Zap,
  Radio,
  Clock,
  ChevronDown,
  ChevronRight,
  Wifi,
  WifiOff
} from "lucide-react";

function SeverityBadge({ severity }) {
  const colors = {
    critical: 'bg-red-100 text-red-800 border-red-200',
    major: 'bg-orange-100 text-orange-800 border-orange-200',
    minor: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    warning: 'bg-amber-100 text-amber-800 border-amber-200',
    cleared: 'bg-green-100 text-green-800 border-green-200',
    unknown: 'bg-gray-100 text-gray-800 border-gray-200',
  };
  
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full border ${colors[severity] || colors.unknown}`}>
      {severity}
    </span>
  );
}

function StatCard({ title, value, icon: Icon, color, subtitle }) {
  const colors = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    red: 'bg-red-100 text-red-600',
    yellow: 'bg-yellow-100 text-yellow-600',
    purple: 'bg-purple-100 text-purple-600',
    orange: 'bg-orange-100 text-orange-600',
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
        </div>
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colors[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}

function TransceiverRow({ xcvr }) {
  const rxOk = xcvr.rx_power_dbm && xcvr.rx_power_dbm > -25;
  const txOk = xcvr.tx_power_dbm && xcvr.tx_power_dbm > -10;
  const tempOk = xcvr.temperature_c && xcvr.temperature_c < 70;
  
  return (
    <tr className="hover:bg-gray-50 text-sm">
      <td className="px-3 py-2 font-medium">{xcvr.port_id}</td>
      <td className="px-3 py-2">
        <span className={`px-1.5 py-0.5 text-xs rounded ${
          xcvr.oper_state === 'enabled' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
        }`}>
          {xcvr.sfp_type || 'SFP'}
        </span>
      </td>
      <td className="px-3 py-2 text-gray-600">{xcvr.vendor}</td>
      <td className="px-3 py-2 text-gray-500 text-xs">{xcvr.part_number}</td>
      <td className="px-3 py-2">
        <span className={rxOk ? 'text-green-700' : 'text-red-600 font-medium'}>
          {xcvr.rx_power_dbm != null ? `${xcvr.rx_power_dbm}` : '-'}
        </span>
      </td>
      <td className="px-3 py-2">
        <span className={txOk ? 'text-green-700' : 'text-red-600 font-medium'}>
          {xcvr.tx_power_dbm != null ? `${xcvr.tx_power_dbm}` : '-'}
        </span>
      </td>
      <td className="px-3 py-2">
        <span className={tempOk ? 'text-gray-700' : 'text-orange-600 font-medium'}>
          {xcvr.temperature_c != null ? `${xcvr.temperature_c}°` : '-'}
        </span>
      </td>
      <td className="px-3 py-2">
        {xcvr.los ? (
          <span className="text-red-600 font-medium">LOS</span>
        ) : (
          <span className="text-green-600">OK</span>
        )}
      </td>
    </tr>
  );
}

export function SNMPLivePage() {
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [snmpData, setSnmpData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [community, setCommunity] = useState('public');

  // Load MCP devices on mount
  useEffect(() => {
    loadDevices();
  }, []);

  // Auto-refresh timer
  useEffect(() => {
    let interval;
    if (autoRefresh && selectedDevice) {
      interval = setInterval(() => {
        pollDevice(selectedDevice);
      }, 30000); // 30 seconds
    }
    return () => clearInterval(interval);
  }, [autoRefresh, selectedDevice]);

  const loadDevices = async () => {
    try {
      const response = await fetchApi('/api/mcp/devices');
      const deviceList = response.data?.devices || [];
      setDevices(deviceList);
    } catch (err) {
      console.error('Failed to load devices:', err);
    }
  };

  const pollDevice = useCallback(async (device) => {
    if (!device) return;
    
    setPolling(true);
    setError(null);
    
    try {
      // Poll all data in parallel
      const [pollRes, portsRes, xcvrRes, statsRes, chassisRes, lagRes, mstpRes, ntpRes] = await Promise.all([
        fetchApi('/api/snmp/poll', {
          method: 'POST',
          body: JSON.stringify({ host: device.ip_address, community }),
        }),
        fetchApi(`/api/snmp/ports/${device.ip_address}?community=${community}`),
        fetchApi(`/api/snmp/transceivers/${device.ip_address}?community=${community}`),
        fetchApi(`/api/snmp/port-stats/${device.ip_address}?community=${community}`).catch(() => ({ data: { port_stats: [] } })),
        fetchApi(`/api/snmp/chassis/${device.ip_address}?community=${community}`).catch(() => ({ data: {} })),
        fetchApi(`/api/snmp/lag/${device.ip_address}?community=${community}`).catch(() => ({ data: { lags: [] } })),
        fetchApi(`/api/snmp/mstp/${device.ip_address}?community=${community}`).catch(() => ({ data: {} })),
        fetchApi(`/api/snmp/ntp/${device.ip_address}?community=${community}`).catch(() => ({ data: {} })),
      ]);
      
      setSnmpData({
        ...pollRes.data,
        ports: portsRes.data,
        transceivers: xcvrRes.data,
        port_stats: statsRes.data?.port_stats || [],
        chassis: chassisRes.data || {},
        lags: lagRes.data?.lags || [],
        mstp: mstpRes.data || {},
        ntp: ntpRes.data || {},
        timestamp: new Date().toISOString(),
      });
    } catch (err) {
      setError(err.message || 'Failed to poll device');
      setSnmpData(null);
    } finally {
      setPolling(false);
    }
  }, [community]);

  const handleDeviceSelect = (device) => {
    setSelectedDevice(device);
    setSnmpData(null);
    pollDevice(device);
  };

  return (
    <PageLayout module="monitor">
      <PageHeader
        title="SNMP Live Monitor"
        description="Real-time device monitoring via SNMP"
        icon={Activity}
        actions={
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-gray-300"
              />
              Auto-refresh (30s)
            </label>
            <button
              onClick={() => pollDevice(selectedDevice)}
              disabled={!selectedDevice || polling}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${polling ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        }
      />

      <div className="p-6 space-y-6">
        {/* Device Selector */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Select Device
              </label>
              <select
                value={selectedDevice?.ip_address || ''}
                onChange={(e) => {
                  const device = devices.find(d => d.ip_address === e.target.value);
                  if (device) handleDeviceSelect(device);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">-- Select a device --</option>
                {devices.map((device) => (
                  <option key={device.ip_address} value={device.ip_address}>
                    {device.name} ({device.ip_address})
                  </option>
                ))}
              </select>
            </div>
            <div className="w-48">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                SNMP Community
              </label>
              <input
                type="text"
                value={community}
                onChange={(e) => setCommunity(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="public"
              />
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
            <XCircle className="w-5 h-5 text-red-500" />
            <span className="text-red-700">{error}</span>
          </div>
        )}

        {snmpData && (
          <>
            {/* System Info */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
              <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                  System Information
                </h2>
                <span className="text-xs text-gray-400">
                  Last updated: {new Date(snmpData.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div className="p-4">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div>
                    <span className="text-xs text-gray-500">Name</span>
                    <p className="font-medium text-gray-900">{snmpData.system?.name || 'N/A'}</p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500">Model</span>
                    <p className="font-medium text-gray-900">{snmpData.system?.description || 'N/A'}</p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500">Uptime</span>
                    <p className="font-medium text-gray-900">
                      {snmpData.system?.uptime 
                        ? `${Math.floor(snmpData.system.uptime / 8640000)} days`
                        : 'N/A'}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500">Location</span>
                    <p className="font-medium text-gray-900">{snmpData.system?.location || 'N/A'}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Stats Overview */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                title="Active Alarms"
                value={snmpData.active_alarms?.length || 0}
                icon={AlertTriangle}
                color={snmpData.active_alarms?.length > 0 ? 'red' : 'green'}
              />
              <StatCard
                title="RAPS Rings"
                value={snmpData.raps_global?.num_rings || 0}
                icon={Radio}
                color="blue"
                subtitle={snmpData.raps_global?.state || 'unknown'}
              />
              <StatCard
                title="Ports Up"
                value={snmpData.ports?.up || 0}
                icon={Wifi}
                color="green"
                subtitle={`of ${snmpData.ports?.count || 0} total`}
              />
              <StatCard
                title="Transceivers"
                value={snmpData.transceivers?.count || 0}
                icon={Zap}
                color="purple"
              />
            </div>

            {/* Active Alarms */}
            {snmpData.active_alarms?.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
                <div className="px-4 py-3 border-b border-gray-200">
                  <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-red-500" />
                    Active Alarms ({snmpData.active_alarms.length})
                  </h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                      <tr>
                        <th className="px-3 py-2 w-20">Severity</th>
                        <th className="px-3 py-2">Description</th>
                        <th className="px-3 py-2">Affected</th>
                        <th className="px-3 py-2 w-44">Timestamp</th>
                        <th className="px-3 py-2 w-12">Ack</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {snmpData.active_alarms.map((alarm, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-3 py-2"><SeverityBadge severity={alarm.severity} /></td>
                          <td className="px-3 py-2 font-medium text-gray-900">{alarm.description}</td>
                          <td className="px-3 py-2">
                            <span className="text-blue-600 font-medium">
                              {alarm.object_type === 'Port ID' ? `Port ${alarm.object_instance}` :
                               alarm.object_type === 'Virt Ring' ? `Ring ${alarm.object_instance}` :
                               alarm.object_instance || '-'}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-gray-500 text-xs">{alarm.timestamp || '-'}</td>
                          <td className="px-3 py-2">
                            {alarm.acknowledged ? (
                              <CheckCircle className="w-4 h-4 text-green-500" />
                            ) : (
                              <span className="text-gray-300">-</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Transceivers / DOM - Compact Table */}
            {snmpData.transceivers?.transceivers?.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
                <div className="px-4 py-3 border-b border-gray-200">
                  <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide flex items-center gap-2">
                    <Zap className="w-4 h-4 text-purple-500" />
                    Optical Transceivers ({snmpData.transceivers.transceivers.length})
                  </h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                      <tr>
                        <th className="px-3 py-2">Port</th>
                        <th className="px-3 py-2">Type</th>
                        <th className="px-3 py-2">Vendor</th>
                        <th className="px-3 py-2">Part #</th>
                        <th className="px-3 py-2">Rx (dBm)</th>
                        <th className="px-3 py-2">Tx (dBm)</th>
                        <th className="px-3 py-2">Temp</th>
                        <th className="px-3 py-2">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {snmpData.transceivers.transceivers.map((xcvr, i) => (
                        <TransceiverRow key={i} xcvr={xcvr} />
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Port Statistics - All Ports */}
            {snmpData.port_stats?.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
                <div className="px-4 py-3 border-b border-gray-200">
                  <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide flex items-center gap-2">
                    <Activity className="w-4 h-4 text-blue-500" />
                    Port Statistics ({snmpData.port_stats.length} ports)
                  </h2>
                </div>
                <div className="overflow-x-auto max-h-96">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-gray-50 text-xs text-gray-500 uppercase sticky top-0">
                      <tr>
                        <th className="px-3 py-2">Port</th>
                        <th className="px-3 py-2">RX Bytes</th>
                        <th className="px-3 py-2">TX Bytes</th>
                        <th className="px-3 py-2">RX Pkts</th>
                        <th className="px-3 py-2">TX Pkts</th>
                        <th className="px-3 py-2">Errors</th>
                        <th className="px-3 py-2">Flaps</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {snmpData.port_stats
                        .sort((a, b) => a.port_id - b.port_id)
                        .map((stat, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-3 py-2 font-medium">{stat.port_id}</td>
                          <td className="px-3 py-2 font-mono text-xs">{(stat.rx_bytes / 1e9).toFixed(2)} GB</td>
                          <td className="px-3 py-2 font-mono text-xs">{(stat.tx_bytes / 1e9).toFixed(2)} GB</td>
                          <td className="px-3 py-2 font-mono text-xs">{(stat.rx_pkts / 1e6).toFixed(2)} M</td>
                          <td className="px-3 py-2 font-mono text-xs">{(stat.tx_pkts / 1e6).toFixed(2)} M</td>
                          <td className="px-3 py-2">
                            <span className={stat.rx_crc_errors > 0 ? 'text-red-600 font-medium' : 'text-gray-400'}>
                              {stat.rx_crc_errors || 0}
                            </span>
                          </td>
                          <td className="px-3 py-2">
                            <span className={stat.link_flaps > 0 ? 'text-orange-600 font-medium' : 'text-gray-400'}>
                              {stat.link_flaps || 0}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Protocol Status Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* NTP Status */}
              {snmpData.ntp && (
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
                  <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide flex items-center gap-2 mb-3">
                    <Clock className="w-4 h-4 text-indigo-500" />
                    NTP Status
                  </h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Admin:</span>
                      <span className={snmpData.ntp.admin_state === 'enabled' ? 'text-green-600' : 'text-gray-600'}>
                        {snmpData.ntp.admin_state}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Sync:</span>
                      <span className={snmpData.ntp.sync_status === 'synchronized' ? 'text-green-600 font-medium' : 'text-orange-600'}>
                        {snmpData.ntp.sync_status}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* MSTP Status */}
              {snmpData.mstp && (
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
                  <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide flex items-center gap-2 mb-3">
                    <Activity className="w-4 h-4 text-green-500" />
                    Spanning Tree
                  </h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Enabled:</span>
                      <span className={snmpData.mstp.enabled ? 'text-green-600' : 'text-gray-600'}>
                        {snmpData.mstp.enabled ? 'Yes' : 'No'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Version:</span>
                      <span className="text-gray-900 font-medium">{snmpData.mstp.version}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* LAG Summary */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
                <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide flex items-center gap-2 mb-3">
                  <Wifi className="w-4 h-4 text-purple-500" />
                  Link Aggregation
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">LAGs:</span>
                    <span className="text-gray-900 font-medium">{snmpData.lags?.length || 0}</span>
                  </div>
                  {snmpData.lags?.length > 0 && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Active:</span>
                      <span className="text-green-600 font-medium">
                        {snmpData.lags.filter(l => l.oper_state === 'up').length}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* LAG Details */}
            {snmpData.lags?.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
                <div className="px-4 py-3 border-b border-gray-200">
                  <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide flex items-center gap-2">
                    <Wifi className="w-4 h-4 text-purple-500" />
                    LAG Details
                  </h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                      <tr>
                        <th className="px-3 py-2">ID</th>
                        <th className="px-3 py-2">Name</th>
                        <th className="px-3 py-2">Mode</th>
                        <th className="px-3 py-2">Admin</th>
                        <th className="px-3 py-2">Oper</th>
                        <th className="px-3 py-2">Members</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {snmpData.lags.map((lag, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-3 py-2 font-medium">{lag.id}</td>
                          <td className="px-3 py-2">{lag.name}</td>
                          <td className="px-3 py-2 uppercase text-xs">{lag.mode}</td>
                          <td className="px-3 py-2">
                            <span className={`px-1.5 py-0.5 text-xs rounded ${
                              lag.admin_state === 'enabled' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                            }`}>{lag.admin_state}</span>
                          </td>
                          <td className="px-3 py-2">
                            <span className={`px-1.5 py-0.5 text-xs rounded ${
                              lag.oper_state === 'up' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                            }`}>{lag.oper_state}</span>
                          </td>
                          <td className="px-3 py-2">{lag.member_count || 0}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Virtual Rings */}
            {snmpData.virtual_rings?.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
                <div className="px-4 py-3 border-b border-gray-200">
                  <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide flex items-center gap-2">
                    <Radio className="w-4 h-4 text-blue-500" />
                    G.8032 RAPS Rings
                  </h2>
                </div>
                <div className="divide-y divide-gray-100">
                  {snmpData.virtual_rings.map((ring, i) => (
                    <div key={i} className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="font-medium text-gray-900">{ring.name}</span>
                          <span className="ml-2 text-sm text-gray-500">VID: {ring.vid}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`px-2 py-0.5 text-xs rounded-full ${
                            ring.state === 'ok' ? 'bg-green-100 text-green-700' :
                            ring.state === 'protecting' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-gray-100 text-gray-600'
                          }`}>
                            {ring.state}
                          </span>
                          {ring.alarm && ring.alarm !== 'clear' && (
                            <span className="px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700">
                              {ring.alarm}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {!snmpData && !error && !polling && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 text-center">
            <Server className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Select a Device</h3>
            <p className="text-gray-500">Choose a device from the dropdown to view real-time SNMP data.</p>
          </div>
        )}

        {polling && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 text-center">
            <RefreshCw className="w-16 h-16 text-blue-500 mx-auto mb-4 animate-spin" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Polling Device...</h3>
            <p className="text-gray-500">Fetching real-time data via SNMP.</p>
          </div>
        )}
      </div>
    </PageLayout>
  );
}

export default SNMPLivePage;
