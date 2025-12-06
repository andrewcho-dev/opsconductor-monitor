import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Play,
  Square,
  RefreshCw,
  Trash2,
  Save,
  TestTube,
  Activity,
  Network,
  Zap,
  Eye,
  Settings,
  CheckCircle,
  XCircle,
  AlertCircle,
} from "lucide-react";
import { cn } from "../lib/utils";

export function Poller() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({
    discovery: { active: false, next_run: null },
    interface: { active: false, next_run: null },
    optical: { active: false, next_run: null },
    scheduler_running: false,
    execution_log: [],
  });
  const [logs, setLogs] = useState([]);

  const [discoveryConfig, setDiscoveryConfig] = useState({
    enabled: false,
    interval: 3600,
    network: "10.127.0.0/24",
    retention: 30,
    ping: true,
    snmp: true,
    ssh: true,
    rdp: false,
  });

  const [interfaceConfig, setInterfaceConfig] = useState({
    enabled: false,
    interval: 1800,
    targets: "all",
    custom: "",
    retention: 7,
  });

  const [opticalConfig, setOpticalConfig] = useState({
    enabled: false,
    interval: 300,
    targets: "all",
    retention: 90,
    temperature_threshold: 70,
  });

  useEffect(() => {
    loadConfigurations();
    refreshStatus();
    addLog("info", "Poller administration page loaded");
  }, []);

  useEffect(() => {
    if (activeTab === "logs") {
      refreshLogs();
    } else if (activeTab === "overview") {
      refreshStatus();
    }
  }, [activeTab]);

  const loadConfigurations = async () => {
    try {
      const response = await fetch("/poller/config");
      const configs = await response.json();
      
      if (configs.discovery) {
        setDiscoveryConfig(configs.discovery);
      }
      if (configs.interface) {
        setInterfaceConfig(configs.interface);
      }
      if (configs.optical) {
        setOpticalConfig(configs.optical);
      }
    } catch (err) {
      addLog("error", "Error loading configurations: " + err.message);
    }
  };

  const refreshStatus = async () => {
    try {
      const response = await fetch("/poller/status");
      const statusData = await response.json();
      setStatus(statusData);
    } catch (err) {
      addLog("error", "Error refreshing status: " + err.message);
    }
  };

  const refreshLogs = async () => {
    try {
      const response = await fetch("/poller/logs");
      const logsData = await response.json();
      setLogs(logsData);
    } catch (err) {
      addLog("error", "Error refreshing logs: " + err.message);
    }
  };

  const addLog = (level, message) => {
    const timestamp = new Date().toLocaleString();
    setLogs(prev => [{ timestamp, level, message }, ...prev].slice(0, 100));
  };

  const startDiscoveryPoller = async () => {
    try {
      const response = await fetch("/poller/discovery/start", { method: "POST" });
      const result = await response.json();
      if (result.success) {
        addLog("success", "Discovery poller started successfully");
        refreshStatus();
      } else {
        addLog("error", "Failed to start discovery poller: " + result.error);
      }
    } catch (err) {
      addLog("error", "Error starting discovery poller: " + err.message);
    }
  };

  const stopDiscoveryPoller = async () => {
    try {
      const response = await fetch("/poller/discovery/stop", { method: "POST" });
      const result = await response.json();
      if (result.success) {
        addLog("warning", "Discovery poller stopped");
        refreshStatus();
      } else {
        addLog("error", "Failed to stop discovery poller: " + result.error);
      }
    } catch (err) {
      addLog("error", "Error stopping discovery poller: " + err.message);
    }
  };

  const startInterfacePoller = async () => {
    try {
      const response = await fetch("/poller/interface/start", { method: "POST" });
      const result = await response.json();
      if (result.success) {
        addLog("success", "Interface poller started successfully");
        refreshStatus();
      } else {
        addLog("error", "Failed to start interface poller: " + result.error);
      }
    } catch (err) {
      addLog("error", "Error starting interface poller: " + err.message);
    }
  };

  const stopInterfacePoller = async () => {
    try {
      const response = await fetch("/poller/interface/stop", { method: "POST" });
      const result = await response.json();
      if (result.success) {
        addLog("warning", "Interface poller stopped");
        refreshStatus();
      } else {
        addLog("error", "Failed to stop interface poller: " + result.error);
      }
    } catch (err) {
      addLog("error", "Error stopping interface poller: " + err.message);
    }
  };

  const startOpticalPoller = async () => {
    try {
      const response = await fetch("/poller/optical/start", { method: "POST" });
      const result = await response.json();
      if (result.success) {
        addLog("success", "Optical power poller started successfully");
        refreshStatus();
      } else {
        addLog("error", "Failed to start optical power poller: " + result.error);
      }
    } catch (err) {
      addLog("error", "Error starting optical power poller: " + err.message);
    }
  };

  const stopOpticalPoller = async () => {
    try {
      const response = await fetch("/poller/optical/stop", { method: "POST" });
      const result = await response.json();
      if (result.success) {
        addLog("warning", "Optical power poller stopped");
        refreshStatus();
      } else {
        addLog("error", "Failed to stop optical power poller: " + result.error);
      }
    } catch (err) {
      addLog("error", "Error stopping optical power poller: " + err.message);
    }
  };

  const startAllPollers = async () => {
    await startDiscoveryPoller();
    await startInterfacePoller();
    await startOpticalPoller();
  };

  const stopAllPollers = async () => {
    await stopDiscoveryPoller();
    await stopInterfacePoller();
    await stopOpticalPoller();
  };

  const runAllScansNow = async () => {
    try {
      addLog("info", "Running all scans manually...");
      const response = await fetch("/poller/run_all", { method: "POST" });
      const result = await response.json();
      if (result.success) {
        addLog("success", "All scans completed successfully");
      } else {
        addLog("error", "Scan execution failed: " + result.error);
      }
    } catch (err) {
      addLog("error", "Error running scans: " + err.message);
    }
  };

  const saveDiscoveryConfig = async () => {
    try {
      const response = await fetch("/poller/discovery/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(discoveryConfig),
      });
      const result = await response.json();
      if (result.success) {
        addLog("success", "Discovery configuration saved");
      } else {
        addLog("error", "Failed to save discovery config: " + result.error);
      }
    } catch (err) {
      addLog("error", "Error saving discovery config: " + err.message);
    }
  };

  const saveInterfaceConfig = async () => {
    try {
      const response = await fetch("/poller/interface/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(interfaceConfig),
      });
      const result = await response.json();
      if (result.success) {
        addLog("success", "Interface configuration saved");
      } else {
        addLog("error", "Failed to save interface config: " + result.error);
      }
    } catch (err) {
      addLog("error", "Error saving interface config: " + err.message);
    }
  };

  const saveOpticalConfig = async () => {
    try {
      const response = await fetch("/poller/optical/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(opticalConfig),
      });
      const result = await response.json();
      if (result.success) {
        addLog("success", "Optical power configuration saved");
      } else {
        addLog("error", "Failed to save optical power config: " + result.error);
      }
    } catch (err) {
      addLog("error", "Error saving optical power config: " + err.message);
    }
  };

  const clearLogs = async () => {
    try {
      const response = await fetch("/poller/logs/clear", { method: "POST" });
      const result = await response.json();
      if (result.success) {
        refreshLogs();
        addLog("info", "Logs cleared");
      }
    } catch (err) {
      addLog("error", "Error clearing logs: " + err.message);
    }
  };

  const testDiscoveryScan = () => addLog("info", "Testing discovery scan...");
  const testInterfaceScan = () => addLog("info", "Testing interface scan...");
  const testOpticalScan = () => addLog("info", "Testing optical power scan...");

  const getStatusIndicator = (active) => (
    <div
      className={cn(
        "w-3 h-3 rounded-full",
        active ? "bg-green-500" : "bg-red-500"
      )}
    />
  );

  const getLogColor = (level) => {
    switch (level) {
      case "success": return "text-green-600";
      case "error": return "text-red-600";
      case "warning": return "text-yellow-600";
      case "info": return "text-blue-600";
      default: return "text-gray-600";
    }
  };

  const tabs = [
    { id: "overview", label: "Overview", icon: Activity },
    { id: "discovery", label: "Discovery Polling", icon: Network },
    { id: "interface", label: "Interface Polling", icon: Settings },
    { id: "optical", label: "Optical Power Polling", icon: Zap },
    { id: "logs", label: "Activity Logs", icon: Eye },
  ];

  return (
    <div className="p-4 bg-gray-100 min-h-screen">
      {/* Header */}
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Main
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={runAllScansNow}
              className="flex items-center gap-2 px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <Play className="w-4 h-4" />
              Run All Now
            </button>
            <button
              onClick={stopAllPollers}
              className="flex items-center gap-2 px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              <Square className="w-4 h-4" />
              Stop All
            </button>
          </div>
        </div>
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-800 mb-2">🔧 Network Poller Administration</h1>
          <p className="text-gray-600">Configure and manage automatic polling schedules for network discovery and monitoring</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="flex border-b border-gray-200">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-2 px-4 py-3 font-medium transition-colors",
                  activeTab === tab.id
                    ? "text-blue-600 border-b-2 border-blue-600"
                    : "text-gray-600 hover:text-gray-800"
                )}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab Content */}
      <div className="bg-white rounded-lg shadow p-6">
        {/* Overview Tab */}
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Column - Job List */}
            <div>
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Poller Jobs</h3>
              <div className="space-y-2">
                {/* Discovery Job */}
                <div className="bg-gray-50 p-3 rounded-lg border-l-4 border-blue-500">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getStatusIndicator(status.discovery.active)}
                      <div>
                        <div className="font-medium text-gray-800">Discovery</div>
                        <div className="text-xs text-gray-600">
                          {status.discovery.active ? "Active" : "Inactive"} • Next: {status.discovery.next_run || "N/A"}
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <button
                        onClick={startDiscoveryPoller}
                        className="p-1 text-green-600 hover:bg-green-100 rounded"
                        title="Start Discovery"
                      >
                        <Play className="w-4 h-4" />
                      </button>
                      <button
                        onClick={stopDiscoveryPoller}
                        className="p-1 text-red-600 hover:bg-red-100 rounded"
                        title="Stop Discovery"
                      >
                        <Square className="w-4 h-4" />
                      </button>
                      <button
                        onClick={testDiscoveryScan}
                        className="p-1 text-blue-600 hover:bg-blue-100 rounded"
                        title="Run Discovery Now"
                      >
                        <RefreshCw className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Interface Job */}
                <div className="bg-gray-50 p-3 rounded-lg border-l-4 border-green-500">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getStatusIndicator(status.interface.active)}
                      <div>
                        <div className="font-medium text-gray-800">Interface</div>
                        <div className="text-xs text-gray-600">
                          {status.interface.active ? "Active" : "Inactive"} • Next: {status.interface.next_run || "N/A"}
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <button
                        onClick={startInterfacePoller}
                        className="p-1 text-green-600 hover:bg-green-100 rounded"
                        title="Start Interface"
                      >
                        <Play className="w-4 h-4" />
                      </button>
                      <button
                        onClick={stopInterfacePoller}
                        className="p-1 text-red-600 hover:bg-red-100 rounded"
                        title="Stop Interface"
                      >
                        <Square className="w-4 h-4" />
                      </button>
                      <button
                        onClick={testInterfaceScan}
                        className="p-1 text-blue-600 hover:bg-blue-100 rounded"
                        title="Run Interface Now"
                      >
                        <RefreshCw className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Optical Job */}
                <div className="bg-gray-50 p-3 rounded-lg border-l-4 border-purple-500">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getStatusIndicator(status.optical.active)}
                      <div>
                        <div className="font-medium text-gray-800">Optical</div>
                        <div className="text-xs text-gray-600">
                          {status.optical.active ? "Active" : "Inactive"} • Next: {status.optical.next_run || "N/A"}
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <button
                        onClick={startOpticalPoller}
                        className="p-1 text-green-600 hover:bg-green-100 rounded"
                        title="Start Optical"
                      >
                        <Play className="w-4 h-4" />
                      </button>
                      <button
                        onClick={stopOpticalPoller}
                        className="p-1 text-red-600 hover:bg-red-100 rounded"
                        title="Stop Optical"
                      >
                        <Square className="w-4 h-4" />
                      </button>
                      <button
                        onClick={testOpticalScan}
                        className="p-1 text-blue-600 hover:bg-blue-100 rounded"
                        title="Run Optical Now"
                      >
                        <RefreshCw className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Quick Actions */}
              <div className="mt-4 flex gap-2">
                <button
                  onClick={startAllPollers}
                  className="flex items-center gap-2 px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm"
                >
                  <Play className="w-4 h-4" />
                  Start All
                </button>
                <button
                  onClick={stopAllPollers}
                  className="flex items-center gap-2 px-3 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm"
                >
                  <Square className="w-4 h-4" />
                  Stop All
                </button>
                <button
                  onClick={runAllScansNow}
                  className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
                >
                  <RefreshCw className="w-4 h-4" />
                  Run All Now
                </button>
              </div>
            </div>

            {/* Right Column - Running Log */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-800">Job Execution Log</h3>
                <button
                  onClick={refreshStatus}
                  className="p-1 text-gray-600 hover:bg-gray-100 rounded"
                  title="Refresh Log"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>
              <div className="bg-black text-green-400 p-4 rounded-lg font-mono text-xs overflow-y-auto" style={{maxHeight: '500px'}}>
                {/* Header with fixed columns */}
                <div className="flex items-center gap-2 border-b border-gray-700 pb-2 mb-2 text-gray-400">
                  <span className="w-32">TIMESTAMP</span>
                  <span className="w-36">JOB TYPE</span>
                  <span className="w-16 text-center">STATUS</span>
                  <span className="w-16 text-right">DURATION</span>
                  <span className="flex-1">RESULT</span>
                </div>
                
                {/* Log entries with fixed columns */}
                {status.execution_log && status.execution_log.length > 0 ? (
                  status.execution_log.map((log, index) => (
                    <div key={index} className="flex items-center gap-2 border-b border-gray-800">
                      <span className="w-32 text-gray-500 truncate">{log.timestamp}</span>
                      <span className={cn(
                        "w-36 font-medium truncate",
                        log.status === 'Success' ? "text-green-400" :
                        log.status === 'Error' ? "text-red-400" :
                        "text-yellow-400"
                      )}>
                        {log.job_name}
                      </span>
                      <span className={cn(
                        "w-16 text-center text-xs px-2 py-0.5 rounded",
                        log.status === 'Success' ? "bg-green-900 text-green-300" :
                        log.status === 'Error' ? "bg-red-900 text-red-300" :
                        "bg-yellow-900 text-yellow-300"
                      )}>
                        {log.status === 'Success' ? 'SUCCESS' : 
                         log.status === 'Error' ? 'FAILED' : 'UNKNOWN'}
                      </span>
                      <span className="w-16 text-right text-gray-500">
                        {log.duration || '-'}
                      </span>
                      <span className="flex-1 text-cyan-300">
                        {log.brief_status || 'Completed'}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="text-gray-500">No job executions recorded</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Discovery Polling Tab */}
        {activeTab === "discovery" && (
          <div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="flex items-center gap-3 mb-4">
                {getStatusIndicator(status.discovery.active)}
                <h3 className="text-lg font-semibold text-gray-800">Network Discovery Polling</h3>
              </div>

              <div className="flex items-center gap-3 mb-6">
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={discoveryConfig.enabled}
                    onChange={(e) => setDiscoveryConfig(prev => ({ ...prev, enabled: e.target.checked }))}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
                <label className="text-gray-700 font-medium">Enable Discovery Polling</label>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Polling Interval</label>
                  <select
                    value={discoveryConfig.interval}
                    onChange={(e) => setDiscoveryConfig(prev => ({ ...prev, interval: parseInt(e.target.value) }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value={300}>Every 5 minutes</option>
                    <option value={600}>Every 10 minutes</option>
                    <option value={900}>Every 15 minutes</option>
                    <option value={1800}>Every 30 minutes</option>
                    <option value={3600}>Every hour</option>
                    <option value={7200}>Every 2 hours</option>
                    <option value={14400}>Every 4 hours</option>
                    <option value={28800}>Every 8 hours</option>
                    <option value={86400}>Daily</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Network Range</label>
                  <input
                    type="text"
                    value={discoveryConfig.network}
                    onChange={(e) => setDiscoveryConfig(prev => ({ ...prev, network: e.target.value }))}
                    placeholder="e.g., 10.127.0.0/24"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Data Retention (days)</label>
                  <input
                    type="number"
                    value={discoveryConfig.retention}
                    onChange={(e) => setDiscoveryConfig(prev => ({ ...prev, retention: parseInt(e.target.value) }))}
                    min="1"
                    max="365"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="space-y-2 mb-6">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={discoveryConfig.ping}
                    onChange={(e) => setDiscoveryConfig(prev => ({ ...prev, ping: e.target.checked }))}
                    className="rounded border-gray-300"
                  />
                  <span className="text-gray-700">Ping Scanning</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={discoveryConfig.snmp}
                    onChange={(e) => setDiscoveryConfig(prev => ({ ...prev, snmp: e.target.checked }))}
                    className="rounded border-gray-300"
                  />
                  <span className="text-gray-700">SNMP Discovery</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={discoveryConfig.ssh}
                    onChange={(e) => setDiscoveryConfig(prev => ({ ...prev, ssh: e.target.checked }))}
                    className="rounded border-gray-300"
                  />
                  <span className="text-gray-700">SSH Detection</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={discoveryConfig.rdp}
                    onChange={(e) => setDiscoveryConfig(prev => ({ ...prev, rdp: e.target.checked }))}
                    className="rounded border-gray-300"
                  />
                  <span className="text-gray-700">RDP Detection</span>
                </label>
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  onClick={startDiscoveryPoller}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  <Play className="w-4 h-4" />
                  Start
                </button>
                <button
                  onClick={stopDiscoveryPoller}
                  className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                >
                  <Square className="w-4 h-4" />
                  Stop
                </button>
                <button
                  onClick={testDiscoveryScan}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <TestTube className="w-4 h-4" />
                  Test Scan
                </button>
                <button
                  onClick={saveDiscoveryConfig}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                >
                  <Save className="w-4 h-4" />
                  Save Config
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Interface Polling Tab */}
        {activeTab === "interface" && (
          <div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="flex items-center gap-3 mb-4">
                {getStatusIndicator(status.interface.active)}
                <h3 className="text-lg font-semibold text-gray-800">SSH CLI Interface Polling</h3>
              </div>

              <div className="flex items-center gap-3 mb-6">
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={interfaceConfig.enabled}
                    onChange={(e) => setInterfaceConfig(prev => ({ ...prev, enabled: e.target.checked }))}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
                <label className="text-gray-700 font-medium">Enable Interface Polling</label>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Polling Interval</label>
                  <select
                    value={interfaceConfig.interval}
                    onChange={(e) => setInterfaceConfig(prev => ({ ...prev, interval: parseInt(e.target.value) }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value={300}>Every 5 minutes</option>
                    <option value={600}>Every 10 minutes</option>
                    <option value={900}>Every 15 minutes</option>
                    <option value={1800}>Every 30 minutes</option>
                    <option value={3600}>Every hour</option>
                    <option value={7200}>Every 2 hours</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Target Devices</label>
                  <select
                    value={interfaceConfig.targets}
                    onChange={(e) => setInterfaceConfig(prev => ({ ...prev, targets: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="all">All SSH-enabled devices</option>
                    <option value="optical">Optical interfaces only</option>
                    <option value="custom">Custom device list</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Data Retention (days)</label>
                  <input
                    type="number"
                    value={interfaceConfig.retention}
                    onChange={(e) => setInterfaceConfig(prev => ({ ...prev, retention: parseInt(e.target.value) }))}
                    min="1"
                    max="90"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">Custom IP Addresses (comma-separated)</label>
                <input
                  type="text"
                  value={interfaceConfig.custom}
                  onChange={(e) => setInterfaceConfig(prev => ({ ...prev, custom: e.target.value }))}
                  placeholder="e.g., 10.127.0.1,10.127.0.2"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  onClick={startInterfacePoller}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  <Play className="w-4 h-4" />
                  Start
                </button>
                <button
                  onClick={stopInterfacePoller}
                  className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                >
                  <Square className="w-4 h-4" />
                  Stop
                </button>
                <button
                  onClick={testInterfaceScan}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <TestTube className="w-4 h-4" />
                  Test Scan
                </button>
                <button
                  onClick={saveInterfaceConfig}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                >
                  <Save className="w-4 h-4" />
                  Save Config
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Optical Power Polling Tab */}
        {activeTab === "optical" && (
          <div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="flex items-center gap-3 mb-4">
                {getStatusIndicator(status.optical.active)}
                <h3 className="text-lg font-semibold text-gray-800">Optical Power History Polling</h3>
              </div>

              <div className="flex items-center gap-3 mb-6">
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={opticalConfig.enabled}
                    onChange={(e) => setOpticalConfig(prev => ({ ...prev, enabled: e.target.checked }))}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
                <label className="text-gray-700 font-medium">Enable Optical Power Polling</label>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Polling Interval</label>
                  <select
                    value={opticalConfig.interval}
                    onChange={(e) => setOpticalConfig(prev => ({ ...prev, interval: parseInt(e.target.value) }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value={60}>Every minute</option>
                    <option value={300}>Every 5 minutes</option>
                    <option value={600}>Every 10 minutes</option>
                    <option value={900}>Every 15 minutes</option>
                    <option value={1800}>Every 30 minutes</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Target Interfaces</label>
                  <select
                    value={opticalConfig.targets}
                    onChange={(e) => setOpticalConfig(prev => ({ ...prev, targets: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="all">All optical interfaces</option>
                    <option value="custom">Custom interface list</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">History Retention (days)</label>
                  <input
                    type="number"
                    value={opticalConfig.retention}
                    onChange={(e) => setOpticalConfig(prev => ({ ...prev, retention: parseInt(e.target.value) }))}
                    min="1"
                    max="365"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">Temperature Alert Threshold (°C)</label>
                <input
                  type="number"
                  value={opticalConfig.temperature_threshold}
                  onChange={(e) => setOpticalConfig(prev => ({ ...prev, temperature_threshold: parseInt(e.target.value) }))}
                  min="0"
                  max="100"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  onClick={startOpticalPoller}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  <Play className="w-4 h-4" />
                  Start
                </button>
                <button
                  onClick={stopOpticalPoller}
                  className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                >
                  <Square className="w-4 h-4" />
                  Stop
                </button>
                <button
                  onClick={testOpticalScan}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <TestTube className="w-4 h-4" />
                  Test Scan
                </button>
                <button
                  onClick={saveOpticalConfig}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                >
                  <Save className="w-4 h-4" />
                  Save Config
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Activity Logs Tab */}
        {activeTab === "logs" && (
          <div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-800">Recent Activity</h3>
                <div className="flex gap-2">
                  <button
                    onClick={refreshLogs}
                    className="flex items-center gap-2 px-3 py-1 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Refresh Logs
                  </button>
                  <button
                    onClick={clearLogs}
                    className="flex items-center gap-2 px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                    Clear Logs
                  </button>
                </div>
              </div>

              <div className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-sm max-h-96 overflow-y-auto">
                {logs.length === 0 ? (
                  <div className="text-gray-400">No recent activity</div>
                ) : (
                  logs.map((log, index) => (
                    <div key={index} className={cn("mb-1", getLogColor(log.level))}>
                      [{log.timestamp}] {log.message}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
