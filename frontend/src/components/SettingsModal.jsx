import { useState } from "react";
import { X, TestTube } from "lucide-react";

export function SettingsModal({ isOpen, onClose, onSave, onTest }) {
  const [settings, setSettings] = useState({
    pingTimeout: "1000",
    pingCount: "4",
    snmpVersion: "2c",
    snmpCommunity: "public",
    snmpPort: "161",
    snmpTimeout: "2000",
    sshPort: "22",
    sshTimeout: "5000",
    sshUsername: "",
    sshPassword: "",
    rdpPort: "3389",
    rdpTimeout: "5000",
    maxThreads: "10",
  });

  const [testStatus, setTestStatus] = useState("");

  const handleChange = (field, value) => {
    setSettings((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    onSave(settings);
  };

  const handleTest = async () => {
    setTestStatus("Testing settings...");
    await onTest(settings);
    setTestStatus("Settings test completed successfully");
    setTimeout(() => setTestStatus(""), 3000);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-800">Settings</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Ping Settings */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">Ping Settings</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Ping Timeout (ms)
                </label>
                <input
                  type="number"
                  value={settings.pingTimeout}
                  onChange={(e) => handleChange("pingTimeout", e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Ping Count
                </label>
                <input
                  type="number"
                  value={settings.pingCount}
                  onChange={(e) => handleChange("pingCount", e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* SNMP Settings */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">SNMP Settings</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  SNMP Version
                </label>
                <select
                  value={settings.snmpVersion}
                  onChange={(e) => handleChange("snmpVersion", e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="1">1</option>
                  <option value="2c">2c</option>
                  <option value="3">3</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  SNMP Community
                </label>
                <input
                  type="text"
                  value={settings.snmpCommunity}
                  onChange={(e) => handleChange("snmpCommunity", e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  SNMP Port
                </label>
                <input
                  type="number"
                  value={settings.snmpPort}
                  onChange={(e) => handleChange("snmpPort", e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  SNMP Timeout (ms)
                </label>
                <input
                  type="number"
                  value={settings.snmpTimeout}
                  onChange={(e) => handleChange("snmpTimeout", e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* SSH Settings */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">SSH Settings</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  SSH Port
                </label>
                <input
                  type="number"
                  value={settings.sshPort}
                  onChange={(e) => handleChange("sshPort", e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  SSH Timeout (ms)
                </label>
                <input
                  type="number"
                  value={settings.sshTimeout}
                  onChange={(e) => handleChange("sshTimeout", e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  SSH Username
                </label>
                <input
                  type="text"
                  value={settings.sshUsername}
                  onChange={(e) => handleChange("sshUsername", e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  SSH Password
                </label>
                <input
                  type="password"
                  value={settings.sshPassword}
                  onChange={(e) => handleChange("sshPassword", e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* RDP Settings */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">RDP Settings</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  RDP Port
                </label>
                <input
                  type="number"
                  value={settings.rdpPort}
                  onChange={(e) => handleChange("rdpPort", e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  RDP Timeout (ms)
                </label>
                <input
                  type="number"
                  value={settings.rdpTimeout}
                  onChange={(e) => handleChange("rdpTimeout", e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Performance Settings */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">Performance</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max Threads
                </label>
                <input
                  type="number"
                  value={settings.maxThreads}
                  onChange={(e) => handleChange("maxThreads", e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50">
          <div className="text-sm text-gray-600">{testStatus}</div>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 font-medium hover:bg-gray-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleTest}
              className="px-4 py-2 bg-gray-600 text-white font-medium rounded-lg hover:bg-gray-700 transition-colors flex items-center gap-2"
            >
              <TestTube className="w-4 h-4" />
              Test
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              Save Settings
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
