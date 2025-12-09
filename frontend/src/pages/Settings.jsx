import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Save,
  RotateCcw,
  TestTube,
  Download,
  Upload,
  ArrowLeft,
  Settings as SettingsIcon,
  Network,
  Shield,
  Monitor,
  Key,
  Bell,
} from "lucide-react";
import { cn } from "../lib/utils";
import { fetchApi } from "../lib/utils";

export function Settings() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [status, setStatus] = useState({ message: "", type: "" });

  const [settings, setSettings] = useState({
    // Ping Settings
    ping_command: "ping",
    ping_count: "1",
    ping_timeout: "0.3",
    online_status: "online",
    offline_status: "offline",

    // SNMP Settings
    snmp_version: "2c",
    snmp_community: "public",
    snmp_port: "161",
    snmp_timeout: "1",
    snmp_success_status: "YES",
    snmp_fail_status: "NO",

    // SSH Settings
    ssh_port: "22",
    ssh_timeout: "3",
    ssh_username: "admin",
    ssh_password: "admin",
    ssh_success_status: "YES",
    ssh_fail_status: "NO",

    // RDP Settings
    rdp_port: "3389",
    rdp_timeout: "3",
    rdp_success_status: "YES",
    rdp_fail_status: "NO",

    // General Settings
    max_threads: "100",
    completion_message: "Capability scan completed: {online}/{total} hosts online",

    // Notification Settings (Apprise)
    notifications_enabled: false,
    notification_targets: "",
    notify_discovery_on_success: false,
    notify_discovery_on_error: true,
    notify_interface_on_success: false,
    notify_interface_on_error: true,
    notify_optical_on_success: false,
    notify_optical_on_error: true,
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const response = await fetch("/get_settings");
      const data = await response.json();
      
      setSettings({
        ping_command: data.ping_command || "ping",
        ping_count: data.ping_count || "1",
        ping_timeout: data.ping_timeout || "0.3",
        online_status: data.online_status || "online",
        offline_status: data.offline_status || "offline",
        
        snmp_version: data.snmp_version || "2c",
        snmp_community: data.snmp_community || "public",
        snmp_port: data.snmp_port || "161",
        snmp_timeout: data.snmp_timeout || "1",
        snmp_success_status: data.snmp_success_status || "YES",
        snmp_fail_status: data.snmp_fail_status || "NO",
        
        ssh_port: data.ssh_port || "22",
        ssh_timeout: data.ssh_timeout || "3",
        ssh_username: data.ssh_username || "admin",
        ssh_password: data.ssh_password || "admin",
        ssh_success_status: data.ssh_success_status || "YES",
        ssh_fail_status: data.ssh_fail_status || "NO",
        
        rdp_port: data.rdp_port || "3389",
        rdp_timeout: data.rdp_timeout || "3",
        rdp_success_status: data.rdp_success_status || "YES",
        rdp_fail_status: data.rdp_fail_status || "NO",
        
        max_threads: data.max_threads || "100",
        completion_message: data.completion_message || "Capability scan completed: {online}/{total} hosts online",

        notifications_enabled: data.notifications_enabled ?? false,
        notification_targets: data.notification_targets || "",
        notify_discovery_on_success: data.notify_discovery_on_success ?? false,
        notify_discovery_on_error: data.notify_discovery_on_error ?? true,
        notify_interface_on_success: data.notify_interface_on_success ?? false,
        notify_interface_on_error: data.notify_interface_on_error ?? true,
        notify_optical_on_success: data.notify_optical_on_success ?? false,
        notify_optical_on_error: data.notify_optical_on_error ?? true,
      });
    } catch (err) {
      showStatus("Error loading settings: " + err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    try {
      setSaving(true);
      const response = await fetch("/save_settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      
      const result = await response.json();
      if (result.status === "success") {
        showStatus("Settings saved successfully!", "success");
      } else {
        showStatus("Error saving settings: " + result.message, "error");
      }
    } catch (err) {
      showStatus("Error saving settings: " + err.message, "error");
    } finally {
      setSaving(false);
    }
  };

  const resetToDefaults = () => {
    if (confirm("Reset all settings to default values?")) {
      setSettings({
        ping_command: "ping",
        ping_count: "1",
        ping_timeout: "0.3",
        online_status: "online",
        offline_status: "offline",
        
        snmp_version: "2c",
        snmp_community: "public",
        snmp_port: "161",
        snmp_timeout: "1",
        snmp_success_status: "YES",
        snmp_fail_status: "NO",
        
        ssh_port: "22",
        ssh_timeout: "3",
        ssh_username: "admin",
        ssh_password: "admin",
        ssh_success_status: "YES",
        ssh_fail_status: "NO",
        
        rdp_port: "3389",
        rdp_timeout: "3",
        rdp_success_status: "YES",
        rdp_fail_status: "NO",
        
        max_threads: "100",
        completion_message: "Capability scan completed: {online}/{total} hosts online",

        notifications_enabled: false,
        notification_targets: "",
        notify_discovery_on_success: false,
        notify_discovery_on_error: true,
        notify_interface_on_success: false,
        notify_interface_on_error: true,
        notify_optical_on_success: false,
        notify_optical_on_error: true,
      });
      
      showStatus("Settings reset to defaults. Click \"Save\" to apply.", "success");
    }
  };

  const testSettings = async () => {
    try {
      setTesting(true);
      showStatus("Testing settings...", "success");
      
      const response = await fetch("/test_settings", { method: "POST" });
      const result = await response.json();
      
      if (result.status === "success") {
        showStatus("Settings test passed! All tools are accessible.", "success");
      } else {
        showStatus("Settings test failed: " + result.message, "error");
      }
    } catch (err) {
      showStatus("Error testing settings: " + err.message, "error");
    } finally {
      setTesting(false);
    }
  };

  const exportSettings = () => {
    const blob = new Blob([JSON.stringify(settings, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "scan_settings.json";
    a.click();
    URL.revokeObjectURL(url);
    
    showStatus("Settings exported successfully!", "success");
  };

  const importSettings = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = function(event) {
      const file = event.target.files[0];
      const reader = new FileReader();
      reader.onload = function(e) {
        try {
          const importedSettings = JSON.parse(e.target.result);
          setSettings({
            ping_command: importedSettings.ping_command || "ping",
            ping_count: importedSettings.ping_count || "1",
            ping_timeout: importedSettings.ping_timeout || "0.3",
            online_status: importedSettings.online_status || "online",
            offline_status: importedSettings.offline_status || "offline",
            
            snmp_version: importedSettings.snmp_version || "2c",
            snmp_community: importedSettings.snmp_community || "public",
            snmp_port: importedSettings.snmp_port || "161",
            snmp_timeout: importedSettings.snmp_timeout || "1",
            snmp_success_status: importedSettings.snmp_success_status || "YES",
            snmp_fail_status: importedSettings.snmp_fail_status || "NO",
            
            ssh_port: importedSettings.ssh_port || "22",
            ssh_timeout: importedSettings.ssh_timeout || "3",
            ssh_username: importedSettings.ssh_username || "admin",
            ssh_password: importedSettings.ssh_password || "admin",
            ssh_success_status: importedSettings.ssh_success_status || "YES",
            ssh_fail_status: importedSettings.ssh_fail_status || "NO",
            
            rdp_port: importedSettings.rdp_port || "3389",
            rdp_timeout: importedSettings.rdp_timeout || "3",
            rdp_success_status: importedSettings.rdp_success_status || "YES",
            rdp_fail_status: importedSettings.rdp_fail_status || "NO",
            
            max_threads: importedSettings.max_threads || "100",
            completion_message: importedSettings.completion_message || "Capability scan completed: {online}/{total} hosts online",

            notifications_enabled: importedSettings.notifications_enabled ?? false,
            notification_targets: importedSettings.notification_targets || "",
            notify_discovery_on_success: importedSettings.notify_discovery_on_success ?? false,
            notify_discovery_on_error: importedSettings.notify_discovery_on_error ?? true,
            notify_interface_on_success: importedSettings.notify_interface_on_success ?? false,
            notify_interface_on_error: importedSettings.notify_interface_on_error ?? true,
            notify_optical_on_success: importedSettings.notify_optical_on_success ?? false,
            notify_optical_on_error: importedSettings.notify_optical_on_error ?? true,
          });
          
          showStatus("Settings imported successfully! Click \"Save\" to apply.", "success");
        } catch (err) {
          showStatus("Error importing settings: " + err.message, "error");
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  const showStatus = (message, type) => {
    setStatus({ message, type });
    setTimeout(() => setStatus({ message: "", type: "" }), 3000);
  };

  const updateSetting = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="p-4 bg-gray-100 min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 bg-white p-4 rounded-lg shadow">
        <div className="flex items-center gap-3">
          <SettingsIcon className="w-6 h-6 text-gray-600" />
          <h1 className="text-xl font-bold text-gray-800">Scan Settings</h1>
        </div>
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2 px-3 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Scan Results
        </button>
      </div>

      {/* Settings Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        {/* Ping Settings */}
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center gap-2 mb-4">
            <Network className="w-5 h-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-800">Ping</h3>
          </div>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Command</label>
              <input
                type="text"
                value={settings.ping_command}
                onChange={(e) => updateSetting("ping_command", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Count</label>
              <input
                type="number"
                value={settings.ping_count}
                onChange={(e) => updateSetting("ping_count", e.target.value)}
                min="1"
                max="10"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Timeout (s)</label>
              <input
                type="number"
                value={settings.ping_timeout}
                onChange={(e) => updateSetting("ping_timeout", e.target.value)}
                min="0.1"
                max="10"
                step="0.1"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Online Status</label>
              <input
                type="text"
                value={settings.online_status}
                onChange={(e) => updateSetting("online_status", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Offline Status</label>
              <input
                type="text"
                value={settings.offline_status}
                onChange={(e) => updateSetting("offline_status", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* SNMP Settings */}
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-5 h-5 text-green-600" />
            <h3 className="text-lg font-semibold text-gray-800">SNMP</h3>
          </div>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Version</label>
              <select
                value={settings.snmp_version}
                onChange={(e) => updateSetting("snmp_version", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="1">v1</option>
                <option value="2c">v2c</option>
                <option value="3">v3</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Community</label>
              <input
                type="text"
                value={settings.snmp_community}
                onChange={(e) => updateSetting("snmp_community", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
              <input
                type="number"
                value={settings.snmp_port}
                onChange={(e) => updateSetting("snmp_port", e.target.value)}
                min="1"
                max="65535"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Timeout (s)</label>
              <input
                type="number"
                value={settings.snmp_timeout}
                onChange={(e) => updateSetting("snmp_timeout", e.target.value)}
                min="0.1"
                max="10"
                step="0.1"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Success Status</label>
              <input
                type="text"
                value={settings.snmp_success_status}
                onChange={(e) => updateSetting("snmp_success_status", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Fail Status</label>
              <input
                type="text"
                value={settings.snmp_fail_status}
                onChange={(e) => updateSetting("snmp_fail_status", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* SSH Settings */}
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center gap-2 mb-4">
            <Key className="w-5 h-5 text-purple-600" />
            <h3 className="text-lg font-semibold text-gray-800">SSH</h3>
          </div>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
              <input
                type="number"
                value={settings.ssh_port}
                onChange={(e) => updateSetting("ssh_port", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Timeout (s)</label>
              <input
                type="number"
                value={settings.ssh_timeout}
                onChange={(e) => updateSetting("ssh_timeout", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
              <input
                type="text"
                value={settings.ssh_username}
                onChange={(e) => updateSetting("ssh_username", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <input
                type="password"
                value={settings.ssh_password}
                onChange={(e) => updateSetting("ssh_password", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Success Status</label>
              <input
                type="text"
                value={settings.ssh_success_status}
                onChange={(e) => updateSetting("ssh_success_status", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Fail Status</label>
              <input
                type="text"
                value={settings.ssh_fail_status}
                onChange={(e) => updateSetting("ssh_fail_status", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* RDP Settings */}
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center gap-2 mb-4">
            <Monitor className="w-5 h-5 text-orange-600" />
            <h3 className="text-lg font-semibold text-gray-800">RDP</h3>
          </div>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
              <input
                type="number"
                value={settings.rdp_port}
                onChange={(e) => updateSetting("rdp_port", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Timeout (s)</label>
              <input
                type="number"
                value={settings.rdp_timeout}
                onChange={(e) => updateSetting("rdp_timeout", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Success Status</label>
              <input
                type="text"
                value={settings.rdp_success_status}
                onChange={(e) => updateSetting("rdp_success_status", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Fail Status</label>
              <input
                type="text"
                value={settings.rdp_fail_status}
                onChange={(e) => updateSetting("rdp_fail_status", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Notification Settings */}
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Bell className="w-5 h-5 text-yellow-600" />
          <h3 className="text-lg font-semibold text-gray-800">Notifications</h3>
        </div>
        <div className="space-y-3">
          <label className="flex items-center gap-2 text-sm text-gray-800">
            <input
              type="checkbox"
              checked={!!settings.notifications_enabled}
              onChange={(e) => updateSetting("notifications_enabled", e.target.checked)}
            />
            <span>Enable notifications for poller jobs</span>
          </label>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Apprise target URLs (one per line)
            </label>
            <textarea
              className="w-full min-h-[80px] px-3 py-2 border border-gray-300 rounded-lg font-mono text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={settings.notification_targets}
              onChange={(e) => updateSetting("notification_targets", e.target.value)}
              placeholder={"mailtos://user:pass@smtp.example.com?from=you@example.com&to=dest@example.com\nslack://...\nmsteams://..."}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs text-gray-800">
            <div className="space-y-1">
              <div className="font-semibold">Discovery job</div>
              <label className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={!!settings.notify_discovery_on_success}
                  onChange={(e) => updateSetting("notify_discovery_on_success", e.target.checked)}
                />
                <span>On success</span>
              </label>
              <label className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={!!settings.notify_discovery_on_error}
                  onChange={(e) => updateSetting("notify_discovery_on_error", e.target.checked)}
                />
                <span>On error</span>
              </label>
            </div>

            <div className="space-y-1">
              <div className="font-semibold">Interface job</div>
              <label className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={!!settings.notify_interface_on_success}
                  onChange={(e) => updateSetting("notify_interface_on_success", e.target.checked)}
                />
                <span>On success</span>
              </label>
              <label className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={!!settings.notify_interface_on_error}
                  onChange={(e) => updateSetting("notify_interface_on_error", e.target.checked)}
                />
                <span>On error</span>
              </label>
            </div>

            <div className="space-y-1">
              <div className="font-semibold">Optical job</div>
              <label className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={!!settings.notify_optical_on_success}
                  onChange={(e) => updateSetting("notify_optical_on_success", e.target.checked)}
                />
                <span>On success</span>
              </label>
              <label className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={!!settings.notify_optical_on_error}
                  onChange={(e) => updateSetting("notify_optical_on_error", e.target.checked)}
                />
                <span>On error</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* General Settings */}
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <div className="flex items-center gap-2 mb-4">
          <SettingsIcon className="w-5 h-5 text-gray-600" />
          <h3 className="text-lg font-semibold text-gray-800">General</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Max Threads</label>
            <input
              type="number"
              value={settings.max_threads}
              onChange={(e) => updateSetting("max_threads", e.target.value)}
              min="1"
              max="1000"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Completion Message</label>
            <input
              type="text"
              value={settings.completion_message}
              onChange={(e) => updateSetting("completion_message", e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={saveSettings}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Save className="w-4 h-4" />
            {saving ? "Saving..." : "Save"}
          </button>
          <button
            onClick={resetToDefaults}
            className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>
          <button
            onClick={testSettings}
            disabled={testing}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <TestTube className="w-4 h-4" />
            {testing ? "Testing..." : "Test"}
          </button>
          <button
            onClick={exportSettings}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
          >
            <Download className="w-4 h-4" />
            Export
          </button>
          <button
            onClick={importSettings}
            className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors"
          >
            <Upload className="w-4 h-4" />
            Import
          </button>
        </div>
      </div>

      {/* Status Message */}
      {status.message && (
        <div className={cn(
          "mt-4 p-4 rounded-lg text-sm font-medium",
          status.type === "success" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
        )}>
          {status.message}
        </div>
      )}
    </div>
  );
}
