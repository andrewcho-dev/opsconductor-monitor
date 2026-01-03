import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ExternalLink,
  RefreshCw,
  Server,
  MapPin,
  Tag,
  Activity,
  Zap,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { PageHeader } from "../components/layout";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";
import { cn, fetchApi } from "../lib/utils";

// Time range options for charts
const TIME_RANGES = [
  { label: "1h", hours: 1 },
  { label: "6h", hours: 6 },
  { label: "24h", hours: 24 },
  { label: "7d", hours: 168 },
  { label: "30d", hours: 720 },
];

export function DeviceDetail() {
  const { ip } = useParams();
  const navigate = useNavigate();
  
  // Device info from NetBox cache
  const [device, setDevice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Interfaces from NetBox
  const [interfaces, setInterfaces] = useState([]);
  const [interfacesLoading, setInterfacesLoading] = useState(false);
  
  // Metrics data
  const [opticalMetrics, setOpticalMetrics] = useState([]);
  const [availabilityMetrics, setAvailabilityMetrics] = useState([]);
  const [metricsLoading, setMetricsLoading] = useState(false);
  
  // UI state
  const [timeRange, setTimeRange] = useState(24);
  const [activeTab, setActiveTab] = useState("overview");
  const [selectedInterface, setSelectedInterface] = useState(null);

  // Load device from NetBox cache
  const loadDevice = useCallback(async () => {
    if (!ip) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const res = await fetchApi(`/api/netbox/devices/cached?q=${encodeURIComponent(ip)}`);
      
      if (res.success && res.data?.length > 0) {
        // Find exact IP match
        const found = res.data.find(d => {
          const deviceIp = d.primary_ip4?.address?.split('/')[0];
          return deviceIp === ip;
        });
        
        if (found) {
          setDevice({
            id: found.id,
            name: found.name,
            ip: found.primary_ip4?.address?.split('/')[0],
            site: found.site?.name,
            role: found.role?.name,
            deviceType: found.device_type?.model,
            manufacturer: found.device_type?.manufacturer?.name,
            status: found.status?.value || 'active',
            statusLabel: found.status?.label || 'Active',
          });
        } else {
          setError("Device not found in NetBox");
        }
      } else {
        setError("Device not found");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [ip]);

  // Load optical metrics
  const loadOpticalMetrics = useCallback(async () => {
    if (!ip) return;
    
    setMetricsLoading(true);
    try {
      const res = await fetchApi(`/api/metrics/optical?device_ip=${encodeURIComponent(ip)}&hours=${timeRange}`);
      // API returns { metrics: [...], count: N } not { success, data }
      const metrics = res.metrics || res.data || [];
      if (metrics.length > 0) {
        const data = metrics.map(m => ({
          timestamp: new Date(m.recorded_at).getTime(),
          time: new Date(m.recorded_at).toLocaleString(),
          txPower: parseFloat(m.tx_power) || null,
          rxPower: parseFloat(m.rx_power) || null,
          interface: m.interface_name,
        }));
        setOpticalMetrics(data);
      }
    } catch (err) {
      console.error("Failed to load optical metrics:", err);
    } finally {
      setMetricsLoading(false);
    }
  }, [ip, timeRange]);

  // Load availability metrics
  const loadAvailabilityMetrics = useCallback(async () => {
    if (!ip) return;
    
    try {
      const res = await fetchApi(`/api/metrics/availability?device_ip=${encodeURIComponent(ip)}&hours=${timeRange}`);
      // API returns { metrics: [...], count: N } not { success, data }
      const metrics = res.metrics || res.data || [];
      if (metrics.length > 0) {
        const data = metrics.map(m => ({
          timestamp: new Date(m.recorded_at).getTime(),
          time: new Date(m.recorded_at).toLocaleString(),
          status: m.ping_status === 'up' ? 1 : 0,
          latency: parseFloat(m.ping_latency_ms) || 0,
        }));
        setAvailabilityMetrics(data);
      }
    } catch (err) {
      console.error("Failed to load availability metrics:", err);
    }
  }, [ip, timeRange]);

  // Load interfaces from NetBox
  const loadInterfaces = useCallback(async () => {
    if (!device?.id) return;
    
    setInterfacesLoading(true);
    try {
      const res = await fetchApi(`/api/netbox/devices/${device.id}/interfaces`);
      if (res.success && res.data) {
        // Sort interfaces by name naturally
        const sorted = res.data.sort((a, b) => {
          const aNum = parseInt(a.name) || 0;
          const bNum = parseInt(b.name) || 0;
          if (aNum && bNum) return aNum - bNum;
          return a.name.localeCompare(b.name);
        });
        setInterfaces(sorted);
      }
    } catch (err) {
      console.error("Failed to load interfaces:", err);
    } finally {
      setInterfacesLoading(false);
    }
  }, [device?.id]);

  useEffect(() => {
    loadDevice();
  }, [loadDevice]);

  useEffect(() => {
    if (device) {
      loadOpticalMetrics();
      loadAvailabilityMetrics();
      loadInterfaces();
    }
  }, [device, timeRange, loadOpticalMetrics, loadAvailabilityMetrics, loadInterfaces]);

  const handleRefresh = () => {
    loadDevice();
    loadOpticalMetrics();
    loadAvailabilityMetrics();
    loadInterfaces();
  };

  const openInNetBox = () => {
    if (device?.id) {
      window.open(`http://192.168.10.51:8000/dcim/devices/${device.id}/`, '_blank');
    }
  };

  // Calculate availability percentage
  const availabilityPercent = availabilityMetrics.length > 0
    ? ((availabilityMetrics.filter(m => m.status === 1).length / availabilityMetrics.length) * 100).toFixed(1)
    : null;

  // Calculate average latency
  const avgLatency = availabilityMetrics.length > 0
    ? (availabilityMetrics.reduce((sum, m) => sum + (m.latency || 0), 0) / availabilityMetrics.filter(m => m.latency).length).toFixed(1)
    : null;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error || !device) {
    return (
      <div className="p-6">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-700">{error || "Device not found"}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="p-2 hover:bg-gray-100 rounded-lg"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{device.name}</h1>
            <p className="text-gray-500">{device.ip}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            className="flex items-center gap-2 px-3 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
          >
            <RefreshCw className={cn("w-4 h-4", metricsLoading && "animate-spin")} />
            Refresh
          </button>
          <button
            onClick={openInNetBox}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <ExternalLink className="w-4 h-4" />
            View in NetBox
          </button>
        </div>
      </div>

      {/* Device Identity Card */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Server className="w-5 h-5 text-gray-500" />
          Device Information
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <p className="text-sm text-gray-500">Site</p>
            <p className="font-medium flex items-center gap-1">
              <MapPin className="w-4 h-4 text-gray-400" />
              {device.site || "—"}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Role</p>
            <p className="font-medium flex items-center gap-1">
              <Tag className="w-4 h-4 text-gray-400" />
              {device.role || "—"}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Device Type</p>
            <p className="font-medium">{device.deviceType || "—"}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Manufacturer</p>
            <p className="font-medium">{device.manufacturer || "—"}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Status</p>
            <span className={cn(
              "inline-flex items-center gap-1 px-2 py-1 rounded-full text-sm font-medium",
              device.status === 'active' ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-700"
            )}>
              {device.status === 'active' ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
              {device.statusLabel}
            </span>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className={cn(
              "p-3 rounded-lg",
              availabilityPercent >= 99 ? "bg-green-100" : availabilityPercent >= 95 ? "bg-yellow-100" : "bg-red-100"
            )}>
              <Activity className={cn(
                "w-5 h-5",
                availabilityPercent >= 99 ? "text-green-600" : availabilityPercent >= 95 ? "text-yellow-600" : "text-red-600"
              )} />
            </div>
            <div>
              <p className="text-sm text-gray-500">Availability</p>
              <p className="text-xl font-bold">{availabilityPercent ? `${availabilityPercent}%` : "—"}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-blue-100">
              <Clock className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Avg Latency</p>
              <p className="text-xl font-bold">{avgLatency ? `${avgLatency} ms` : "—"}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-purple-100">
              <Zap className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Interfaces</p>
              <p className="text-xl font-bold">{interfaces.length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Interfaces Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Server className="w-5 h-5 text-gray-500" />
          Interfaces / Ports ({interfaces.length})
        </h2>
        {interfacesLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
          </div>
        ) : interfaces.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Name</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Type</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Status</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Speed</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Description</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Connected To</th>
                </tr>
              </thead>
              <tbody>
                {interfaces.map((iface, i) => (
                  <tr 
                    key={iface.id || i} 
                    className={cn(
                      "border-b border-gray-100 hover:bg-gray-50 cursor-pointer",
                      selectedInterface?.id === iface.id && "bg-blue-50"
                    )}
                    onClick={() => setSelectedInterface(iface)}
                  >
                    <td className="py-3 px-4 font-medium">{iface.name}</td>
                    <td className="py-3 px-4 text-gray-600">{iface.type?.label || iface.type?.value || '—'}</td>
                    <td className="py-3 px-4">
                      <span className={cn(
                        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
                        iface.enabled ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                      )}>
                        {iface.enabled ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                        {iface.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-600">
                      {iface.speed ? `${(iface.speed / 1000).toFixed(0)} Gbps` : '—'}
                    </td>
                    <td className="py-3 px-4 text-gray-500 max-w-xs truncate">
                      {iface.description || '—'}
                    </td>
                    <td className="py-3 px-4 text-gray-600">
                      {iface.connected_endpoints?.length > 0 
                        ? iface.connected_endpoints.map(e => e.device?.name || e.name).join(', ')
                        : iface.link_peers?.length > 0
                          ? iface.link_peers.map(p => p.device?.name || p.name).join(', ')
                          : '—'
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-center py-4">No interfaces found in NetBox</p>
        )}
      </div>

      {/* Time Range Selector */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-500">Time Range:</span>
        {TIME_RANGES.map(range => (
          <button
            key={range.hours}
            onClick={() => setTimeRange(range.hours)}
            className={cn(
              "px-3 py-1 rounded-lg text-sm font-medium transition-colors",
              timeRange === range.hours
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            )}
          >
            {range.label}
          </button>
        ))}
      </div>

      {/* Optical Power Chart */}
      {opticalMetrics.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-purple-500" />
            Optical Power Levels
          </h2>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={opticalMetrics}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis 
                  dataKey="timestamp" 
                  type="number"
                  domain={['dataMin', 'dataMax']}
                  tickFormatter={(ts) => new Date(ts).toLocaleTimeString()}
                  stroke="#9ca3af"
                  fontSize={12}
                />
                <YAxis 
                  stroke="#9ca3af"
                  fontSize={12}
                  tickFormatter={(v) => `${v} dBm`}
                />
                <Tooltip 
                  labelFormatter={(ts) => new Date(ts).toLocaleString()}
                  formatter={(value, name) => [`${value?.toFixed(2)} dBm`, name === 'txPower' ? 'TX Power' : 'RX Power']}
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="txPower" 
                  name="TX Power"
                  stroke="#8b5cf6" 
                  strokeWidth={2}
                  dot={false}
                />
                <Line 
                  type="monotone" 
                  dataKey="rxPower" 
                  name="RX Power"
                  stroke="#06b6d4" 
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Availability Chart */}
      {availabilityMetrics.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-green-500" />
            Response Latency
          </h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={availabilityMetrics}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis 
                  dataKey="timestamp" 
                  type="number"
                  domain={['dataMin', 'dataMax']}
                  tickFormatter={(ts) => new Date(ts).toLocaleTimeString()}
                  stroke="#9ca3af"
                  fontSize={12}
                />
                <YAxis 
                  stroke="#9ca3af"
                  fontSize={12}
                  tickFormatter={(v) => `${v} ms`}
                />
                <Tooltip 
                  labelFormatter={(ts) => new Date(ts).toLocaleString()}
                  formatter={(value) => [`${value?.toFixed(1)} ms`, 'Latency']}
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                />
                <Area 
                  type="monotone" 
                  dataKey="latency" 
                  stroke="#10b981" 
                  fill="#d1fae5"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Metrics Data Table */}
      {opticalMetrics.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Recent Optical Readings</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Time</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Interface</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">TX Power</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">RX Power</th>
                </tr>
              </thead>
              <tbody>
                {opticalMetrics.slice(-20).reverse().map((m, i) => (
                  <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4 text-gray-600">{m.time}</td>
                    <td className="py-3 px-4">{m.interface}</td>
                    <td className="py-3 px-4 text-right font-mono">
                      {m.txPower?.toFixed(2)} dBm
                    </td>
                    <td className={cn(
                      "py-3 px-4 text-right font-mono",
                      m.rxPower < -25 ? "text-red-600" : m.rxPower < -20 ? "text-yellow-600" : "text-green-600"
                    )}>
                      {m.rxPower?.toFixed(2)} dBm
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* No Data Message */}
      {opticalMetrics.length === 0 && availabilityMetrics.length === 0 && !metricsLoading && (
        <div className="bg-gray-50 rounded-xl border border-gray-200 p-8 text-center">
          <AlertTriangle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-700 mb-2">No Metrics Data</h3>
          <p className="text-gray-500">
            No optical or availability metrics found for this device in the selected time range.
          </p>
        </div>
      )}
    </div>
  );
}

export default DeviceDetail;
