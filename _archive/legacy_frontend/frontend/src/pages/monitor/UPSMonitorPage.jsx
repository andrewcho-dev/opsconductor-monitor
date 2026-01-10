import React, { useState, useEffect, useCallback } from "react";
import { PageLayout, PageHeader } from "../../components/layout";
import { fetchApi } from "../../lib/utils";
import { 
  Battery, 
  RefreshCw, 
  Zap,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Thermometer,
  Droplets,
  Activity,
  Clock,
  Server,
  Plug,
  BatteryCharging,
  BatteryWarning,
  BatteryFull,
  BatteryLow,
  BatteryMedium
} from "lucide-react";

function StatCard({ title, value, unit, icon: Icon, color, subtitle }) {
  const colors = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    red: 'bg-red-100 text-red-600',
    yellow: 'bg-yellow-100 text-yellow-600',
    purple: 'bg-purple-100 text-purple-600',
    orange: 'bg-orange-100 text-orange-600',
    cyan: 'bg-cyan-100 text-cyan-600',
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {value !== null && value !== undefined ? value : '--'}
            {unit && <span className="text-sm font-normal text-gray-500 ml-1">{unit}</span>}
          </p>
          {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
        </div>
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colors[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}

function BatteryGauge({ percent, status }) {
  const getColor = () => {
    if (percent >= 80) return 'bg-green-500';
    if (percent >= 50) return 'bg-yellow-500';
    if (percent >= 20) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const getIcon = () => {
    if (status === 'charging') return BatteryCharging;
    if (percent >= 80) return BatteryFull;
    if (percent >= 50) return BatteryMedium;
    if (percent >= 20) return BatteryLow;
    return BatteryWarning;
  };

  const Icon = getIcon();

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Battery Status</h3>
        <Icon className={`w-8 h-8 ${percent >= 50 ? 'text-green-500' : percent >= 20 ? 'text-orange-500' : 'text-red-500'}`} />
      </div>
      <div className="relative pt-1">
        <div className="flex mb-2 items-center justify-between">
          <div>
            <span className="text-4xl font-bold text-gray-900">{percent ?? '--'}%</span>
          </div>
          <div className="text-right">
            <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
              status === 'charging' ? 'bg-blue-100 text-blue-700' :
              status === 'floating' ? 'bg-green-100 text-green-700' :
              status === 'discharging' ? 'bg-orange-100 text-orange-700' :
              status === 'resting' ? 'bg-gray-100 text-gray-700' :
              'bg-gray-100 text-gray-600'
            }`}>
              {status || 'Unknown'}
            </span>
          </div>
        </div>
        <div className="overflow-hidden h-4 text-xs flex rounded-full bg-gray-200">
          <div
            style={{ width: `${percent || 0}%` }}
            className={`shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center ${getColor()} transition-all duration-500`}
          />
        </div>
      </div>
    </div>
  );
}

function OutputSourceBadge({ source }) {
  const sourceColors = {
    normal: 'bg-green-100 text-green-700 border-green-200',
    battery: 'bg-orange-100 text-orange-700 border-orange-200',
    bypass: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    none: 'bg-red-100 text-red-700 border-red-200',
    booster: 'bg-blue-100 text-blue-700 border-blue-200',
    reducer: 'bg-purple-100 text-purple-700 border-purple-200',
  };

  return (
    <span className={`px-3 py-1 text-sm font-medium rounded-full border ${sourceColors[source] || 'bg-gray-100 text-gray-600 border-gray-200'}`}>
      {source?.charAt(0).toUpperCase() + source?.slice(1) || 'Unknown'}
    </span>
  );
}

function AlarmCard({ alarms }) {
  if (!alarms || alarms.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
            <CheckCircle className="w-5 h-5 text-green-600" />
          </div>
          <div>
            <h3 className="font-medium text-gray-900">No Active Alarms</h3>
            <p className="text-sm text-gray-500">All systems operating normally</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-red-200 shadow-sm">
      <div className="px-4 py-3 border-b border-red-200 bg-red-50 rounded-t-xl">
        <h2 className="text-sm font-semibold text-red-700 uppercase tracking-wide flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          Active Alarms ({alarms.length})
        </h2>
      </div>
      <div className="divide-y divide-red-100">
        {alarms.map((alarm, i) => (
          <div key={i} className="p-3 flex items-center gap-3">
            <XCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
            <span className="text-sm font-medium text-gray-900">{alarm.description}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function UPSMonitorPage() {
  const [upsHost, setUpsHost] = useState('');
  const [community, setCommunity] = useState('public');
  const [upsData, setUpsData] = useState(null);
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [lastPoll, setLastPoll] = useState(null);

  // Auto-refresh timer
  useEffect(() => {
    let interval;
    if (autoRefresh && upsHost) {
      interval = setInterval(() => {
        pollUPS();
      }, 30000); // 30 seconds
    }
    return () => clearInterval(interval);
  }, [autoRefresh, upsHost, community]);

  const pollUPS = useCallback(async () => {
    if (!upsHost) return;
    
    setPolling(true);
    setError(null);
    
    try {
      const response = await fetchApi(`/monitoring/v1/ups/poll/${upsHost}?community=${community}`);
      if (response.success) {
        setUpsData(response.data);
        setLastPoll(new Date().toISOString());
      } else {
        setError(response.error || 'Failed to poll UPS');
        setUpsData(null);
      }
    } catch (err) {
      setError(err.message || 'Failed to poll UPS');
      setUpsData(null);
    } finally {
      setPolling(false);
    }
  }, [upsHost, community]);

  const handleSubmit = (e) => {
    e.preventDefault();
    pollUPS();
  };

  return (
    <PageLayout module="monitor">
      <PageHeader
        title="UPS Monitor"
        description="Real-time Eaton UPS monitoring via SNMP"
        icon={Battery}
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
              onClick={pollUPS}
              disabled={!upsHost || polling}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${polling ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        }
      />

      <div className="p-6 space-y-6">
        {/* UPS Connection Form */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
          <form onSubmit={handleSubmit} className="flex items-end gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                UPS IP Address
              </label>
              <input
                type="text"
                value={upsHost}
                onChange={(e) => setUpsHost(e.target.value)}
                placeholder="e.g., 192.168.1.100"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="w-48">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                SNMP Community
              </label>
              <input
                type="text"
                value={community}
                onChange={(e) => setCommunity(e.target.value)}
                placeholder="public"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <button
              type="submit"
              disabled={!upsHost || polling}
              className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              {polling ? 'Polling...' : 'Connect'}
            </button>
          </form>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
            <XCircle className="w-5 h-5 text-red-500" />
            <span className="text-red-700">{error}</span>
          </div>
        )}

        {/* UPS Data Display */}
        {upsData && (
          <>
            {/* Identity Header */}
            <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-6 text-white">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold">{upsData.identity?.model || 'Unknown UPS'}</h2>
                  <p className="text-blue-100 mt-1">
                    {upsData.identity?.manufacturer} • Firmware: {upsData.identity?.software_version}
                  </p>
                </div>
                <div className="text-right">
                  <div className="flex items-center gap-2">
                    <span className="text-blue-100">Output Source:</span>
                    <OutputSourceBadge source={upsData.output?.source} />
                  </div>
                  {lastPoll && (
                    <p className="text-xs text-blue-200 mt-2">
                      Last updated: {new Date(lastPoll).toLocaleTimeString()}
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Alarms */}
            <AlarmCard alarms={upsData.alarms?.alarms} />

            {/* Battery and Load Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <BatteryGauge 
                percent={upsData.battery?.capacity_percent} 
                status={upsData.battery?.status}
              />
              
              {/* Load Gauge */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Output Load</h3>
                  <Activity className={`w-8 h-8 ${
                    (upsData.output?.load_percent || 0) < 80 ? 'text-green-500' : 
                    (upsData.output?.load_percent || 0) < 90 ? 'text-orange-500' : 'text-red-500'
                  }`} />
                </div>
                <div className="relative pt-1">
                  <div className="flex mb-2 items-center justify-between">
                    <span className="text-4xl font-bold text-gray-900">
                      {upsData.output?.load_percent ?? '--'}%
                    </span>
                  </div>
                  <div className="overflow-hidden h-4 text-xs flex rounded-full bg-gray-200">
                    <div
                      style={{ width: `${upsData.output?.load_percent || 0}%` }}
                      className={`shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center transition-all duration-500 ${
                        (upsData.output?.load_percent || 0) < 80 ? 'bg-green-500' : 
                        (upsData.output?.load_percent || 0) < 90 ? 'bg-orange-500' : 'bg-red-500'
                      }`}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard
                title="Runtime Remaining"
                value={upsData.battery?.time_remaining_minutes}
                unit="min"
                icon={Clock}
                color="blue"
              />
              <StatCard
                title="Battery Voltage"
                value={upsData.battery?.voltage}
                unit="VDC"
                icon={Battery}
                color="green"
              />
              <StatCard
                title="Input Voltage"
                value={upsData.input?.phases?.[0]?.voltage}
                unit="VAC"
                icon={Plug}
                color="purple"
              />
              <StatCard
                title="Output Voltage"
                value={upsData.output?.phases?.[0]?.voltage}
                unit="VAC"
                icon={Zap}
                color="orange"
              />
            </div>

            {/* Power Details */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Input Power */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
                <div className="px-4 py-3 border-b border-gray-200">
                  <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide flex items-center gap-2">
                    <Plug className="w-4 h-4 text-purple-500" />
                    Input Power
                  </h2>
                </div>
                <div className="p-4 space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Frequency</span>
                    <span className="font-medium">{upsData.input?.frequency_hz?.toFixed(1) || '--'} Hz</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Line Faults</span>
                    <span className="font-medium">{upsData.input?.line_bads || 0}</span>
                  </div>
                  {upsData.input?.phases?.map((phase, i) => (
                    <div key={i} className="pt-2 border-t border-gray-100">
                      <div className="text-xs text-gray-400 mb-1">Phase {phase.phase}</div>
                      <div className="grid grid-cols-3 gap-2 text-sm">
                        <div>
                          <span className="text-gray-500">V: </span>
                          <span className="font-medium">{phase.voltage || '--'}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">A: </span>
                          <span className="font-medium">{phase.current || '--'}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">W: </span>
                          <span className="font-medium">{phase.watts || '--'}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Output Power */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
                <div className="px-4 py-3 border-b border-gray-200">
                  <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide flex items-center gap-2">
                    <Zap className="w-4 h-4 text-orange-500" />
                    Output Power
                  </h2>
                </div>
                <div className="p-4 space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Frequency</span>
                    <span className="font-medium">{upsData.output?.frequency_hz?.toFixed(1) || '--'} Hz</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Source</span>
                    <OutputSourceBadge source={upsData.output?.source} />
                  </div>
                  {upsData.output?.phases?.map((phase, i) => (
                    <div key={i} className="pt-2 border-t border-gray-100">
                      <div className="text-xs text-gray-400 mb-1">Phase {phase.phase}</div>
                      <div className="grid grid-cols-3 gap-2 text-sm">
                        <div>
                          <span className="text-gray-500">V: </span>
                          <span className="font-medium">{phase.voltage || '--'}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">A: </span>
                          <span className="font-medium">{phase.current || '--'}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">W: </span>
                          <span className="font-medium">{phase.watts || '--'}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Environment */}
            {(upsData.environment?.temperature_c || upsData.environment?.humidity_percent) && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {upsData.environment?.temperature_c && (
                  <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-lg bg-red-100 flex items-center justify-center">
                        <Thermometer className="w-6 h-6 text-red-600" />
                      </div>
                      <div>
                        <p className="text-sm text-gray-500">Temperature</p>
                        <p className="text-2xl font-bold text-gray-900">
                          {upsData.environment.temperature_c}°C
                        </p>
                        {upsData.environment.temperature_upper_limit && (
                          <p className="text-xs text-gray-400">
                            Limit: {upsData.environment.temperature_lower_limit}° - {upsData.environment.temperature_upper_limit}°C
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
                {upsData.environment?.humidity_percent && (
                  <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-lg bg-blue-100 flex items-center justify-center">
                        <Droplets className="w-6 h-6 text-blue-600" />
                      </div>
                      <div>
                        <p className="text-sm text-gray-500">Humidity</p>
                        <p className="text-2xl font-bold text-gray-900">
                          {upsData.environment.humidity_percent}%
                        </p>
                        {upsData.environment.humidity_upper_limit && (
                          <p className="text-xs text-gray-400">
                            Limit: {upsData.environment.humidity_lower_limit}% - {upsData.environment.humidity_upper_limit}%
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Configuration */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
              <div className="px-4 py-3 border-b border-gray-200">
                <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide flex items-center gap-2">
                  <Server className="w-4 h-4 text-gray-500" />
                  UPS Configuration
                </h2>
              </div>
              <div className="p-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Rated Output VA</span>
                  <p className="font-medium">{upsData.config?.output_va || '--'} VA</p>
                </div>
                <div>
                  <span className="text-gray-500">Rated Output Power</span>
                  <p className="font-medium">{upsData.config?.output_power || '--'} W</p>
                </div>
                <div>
                  <span className="text-gray-500">Nominal Input</span>
                  <p className="font-medium">{upsData.config?.input_voltage || '--'} V / {upsData.config?.input_freq || '--'} Hz</p>
                </div>
                <div>
                  <span className="text-gray-500">Low Battery Time</span>
                  <p className="font-medium">{upsData.config?.low_battery_time || '--'} sec</p>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Empty State */}
        {!upsData && !error && !polling && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 text-center">
            <Battery className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Connect to a UPS</h3>
            <p className="text-gray-500">Enter the IP address of an Eaton UPS with a network card to view real-time status.</p>
          </div>
        )}

        {/* Loading State */}
        {polling && !upsData && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 text-center">
            <RefreshCw className="w-16 h-16 text-blue-500 mx-auto mb-4 animate-spin" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Connecting to UPS...</h3>
            <p className="text-gray-500">Fetching data via SNMP.</p>
          </div>
        )}
      </div>
    </PageLayout>
  );
}
