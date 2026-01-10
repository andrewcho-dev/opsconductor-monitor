import { useState, useEffect } from 'react'
import { Save, User, Key, Shield, Activity, RefreshCw, AlertTriangle, ExternalLink } from 'lucide-react'

export default function Settings() {
  const [settings, setSettings] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('polling')
  
  // Polling config state
  const [pollingConfig, setPollingConfig] = useState({
    worker_count: 1,
    worker_concurrency: 4,
    rate_limit: 100,
    poll_interval: 60,
    default_target_interval: 300
  })
  const [serviceStatus, setServiceStatus] = useState({})
  const [pollingDirty, setPollingDirty] = useState(false)
  const [restarting, setRestarting] = useState(false)
  const [saveMessage, setSaveMessage] = useState('')

  const token = localStorage.getItem('access_token')
  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => {
    fetchData()
    fetchPollingConfig()
    fetchServiceStatus()
  }, [])

  const fetchData = async () => {
    try {
      const settingsRes = await fetch('/api/v1/settings', { headers })
      if (settingsRes.ok) {
        const data = await settingsRes.json()
        setSettings(data.settings || [])
      }
    } catch (e) {
      console.error('Failed to fetch settings')
    }
    setLoading(false)
  }

  const fetchPollingConfig = async () => {
    try {
      const res = await fetch('/api/v1/polling/config', { headers })
      if (res.ok) {
        const data = await res.json()
        setPollingConfig(data.config)
      }
    } catch (e) {
      console.error('Failed to fetch polling config')
    }
  }

  const fetchServiceStatus = async () => {
    try {
      const res = await fetch('/api/v1/services/status', { headers })
      if (res.ok) {
        const data = await res.json()
        setServiceStatus(data)
      }
    } catch (e) {
      console.error('Failed to fetch service status')
    }
  }

  const handleSettingChange = async (key, value) => {
    await fetch(`/api/v1/settings/${key}`, {
      method: 'PUT',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ value })
    })
    fetchData()
  }

  const handlePollingConfigChange = (field, value) => {
    setPollingConfig(prev => ({ ...prev, [field]: parseInt(value) || 0 }))
    setPollingDirty(true)
    setSaveMessage('')
  }

  const savePollingConfig = async () => {
    try {
      const res = await fetch('/api/v1/polling/config', {
        method: 'PUT',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify(pollingConfig)
      })
      if (res.ok) {
        setPollingDirty(false)
        setSaveMessage('Configuration saved. Restart services to apply changes.')
      } else {
        const err = await res.json()
        setSaveMessage(`Error: ${err.detail}`)
      }
    } catch (e) {
      setSaveMessage('Failed to save configuration')
    }
  }

  const restartServices = async () => {
    if (!confirm('This will restart all services. The UI will be briefly unavailable. Continue?')) {
      return
    }
    setRestarting(true)
    setSaveMessage('Restarting services...')
    try {
      await fetch('/api/v1/services/restart', {
        method: 'POST',
        headers
      })
      // Wait and then refresh
      setTimeout(() => {
        window.location.reload()
      }, 5000)
    } catch (e) {
      setSaveMessage('Restart initiated. Refreshing...')
      setTimeout(() => {
        window.location.reload()
      }, 5000)
    }
  }

  const tabs = [
    { id: 'polling', label: 'Polling', icon: Activity },
    { id: 'system', label: 'System', icon: Shield },
    { id: 'users', label: 'Users', icon: User },
    { id: 'api', label: 'API Keys', icon: Key },
  ]

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-gray-700">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 -mb-px border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-blue-500 text-blue-500'
                : 'border-transparent text-gray-400 hover:text-white'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Polling Configuration */}
      {activeTab === 'polling' && (
        <div className="space-y-6">
          {/* Service Status */}
          <div className="bg-gray-800 rounded-lg border border-gray-700">
            <div className="p-4 border-b border-gray-700 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <h2 className="font-semibold">Service Status</h2>
                <a
                  href={`http://${window.location.hostname}:5555`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300"
                >
                  <ExternalLink className="w-3 h-3" />
                  Flower Monitor
                </a>
              </div>
              <button
                onClick={fetchServiceStatus}
                className="text-gray-400 hover:text-white"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
            <div className="p-4 grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(serviceStatus).map(([service, status]) => (
                <div key={service} className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${status === 'running' ? 'bg-green-500' : 'bg-red-500'}`} />
                  <span className="text-sm">
                    {service.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Polling Configuration */}
          <div className="bg-gray-800 rounded-lg border border-gray-700">
            <div className="p-4 border-b border-gray-700">
              <h2 className="font-semibold">Polling Configuration</h2>
              <p className="text-sm text-gray-400 mt-1">
                Configure how the system polls your devices. Changes require a service restart.
              </p>
            </div>
            <div className="p-4 space-y-6">
              {/* Worker Settings */}
              <div>
                <h3 className="text-sm font-medium text-gray-300 mb-3">Worker Settings</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Number of Workers</label>
                    <input
                      type="number"
                      min="1"
                      max="16"
                      value={pollingConfig.worker_count}
                      onChange={e => handlePollingConfigChange('worker_count', e.target.value)}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">Parallel worker processes (1-16)</p>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Concurrency per Worker</label>
                    <input
                      type="number"
                      min="1"
                      max="16"
                      value={pollingConfig.worker_concurrency}
                      onChange={e => handlePollingConfigChange('worker_concurrency', e.target.value)}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">Parallel tasks per worker (1-16)</p>
                  </div>
                </div>
                <div className="mt-3 p-3 bg-gray-700/50 rounded text-sm">
                  <span className="text-gray-400">Total parallel polls: </span>
                  <span className="text-white font-medium">
                    {pollingConfig.worker_count} × {pollingConfig.worker_concurrency} = {pollingConfig.worker_count * pollingConfig.worker_concurrency}
                  </span>
                </div>
              </div>

              {/* Rate Limiting */}
              <div>
                <h3 className="text-sm font-medium text-gray-300 mb-3">Rate Limiting</h3>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Max Polls per Second</label>
                  <input
                    type="number"
                    min="10"
                    max="1000"
                    value={pollingConfig.rate_limit}
                    onChange={e => handlePollingConfigChange('rate_limit', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Prevents overwhelming your network. Recommended: 100 for most networks.
                  </p>
                </div>
              </div>

              {/* Timing */}
              <div>
                <h3 className="text-sm font-medium text-gray-300 mb-3">Timing</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Dispatch Interval (seconds)</label>
                    <input
                      type="number"
                      min="10"
                      max="3600"
                      value={pollingConfig.poll_interval}
                      onChange={e => handlePollingConfigChange('poll_interval', e.target.value)}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">How often to check for due targets</p>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Default Target Interval (seconds)</label>
                    <input
                      type="number"
                      min="30"
                      max="86400"
                      value={pollingConfig.default_target_interval}
                      onChange={e => handlePollingConfigChange('default_target_interval', e.target.value)}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">Default polling interval for new targets</p>
                  </div>
                </div>
              </div>

              {/* Capacity Estimate */}
              <div className="p-4 bg-blue-900/30 border border-blue-700 rounded">
                <h3 className="text-sm font-medium text-blue-300 mb-2">Capacity Estimate</h3>
                <p className="text-sm text-gray-300">
                  With current settings, you can poll approximately{' '}
                  <span className="text-white font-medium">
                    {Math.floor((pollingConfig.worker_count * pollingConfig.worker_concurrency * pollingConfig.default_target_interval) / 0.5)}
                  </span>{' '}
                  devices at {pollingConfig.default_target_interval}s intervals (assuming 0.5s per poll).
                </p>
              </div>

              {/* Save Message */}
              {saveMessage && (
                <div className={`p-3 rounded flex items-center gap-2 ${
                  saveMessage.includes('Error') ? 'bg-red-900/30 border border-red-700 text-red-300' :
                  saveMessage.includes('Restart') ? 'bg-yellow-900/30 border border-yellow-700 text-yellow-300' :
                  'bg-green-900/30 border border-green-700 text-green-300'
                }`}>
                  <AlertTriangle className="w-4 h-4" />
                  {saveMessage}
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-4 border-t border-gray-700">
                <button
                  onClick={savePollingConfig}
                  disabled={!pollingDirty}
                  className={`flex items-center gap-2 px-4 py-2 rounded font-medium ${
                    pollingDirty
                      ? 'bg-blue-600 hover:bg-blue-700 text-white'
                      : 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  }`}
                >
                  <Save className="w-4 h-4" />
                  Save Configuration
                </button>
                <button
                  onClick={restartServices}
                  disabled={restarting}
                  className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded font-medium"
                >
                  <RefreshCw className={`w-4 h-4 ${restarting ? 'animate-spin' : ''}`} />
                  {restarting ? 'Restarting...' : 'Restart Services'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* System Settings */}
      {activeTab === 'system' && (
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <div className="p-4 border-b border-gray-700">
            <h2 className="font-semibold">System Settings</h2>
          </div>
          <div className="divide-y divide-gray-700">
            {loading ? (
              <div className="p-4 text-gray-400">Loading...</div>
            ) : settings.length === 0 ? (
              <div className="p-4 text-gray-400">No settings found</div>
            ) : (
              settings.map(setting => (
                <div key={setting.key} className="p-4 flex items-center justify-between">
                  <div>
                    <div className="font-medium">{setting.key}</div>
                    <div className="text-sm text-gray-400">
                      Last updated: {setting.updated_at ? new Date(setting.updated_at).toLocaleString() : 'Never'}
                    </div>
                  </div>
                  <input
                    type="text"
                    defaultValue={setting.value}
                    onBlur={e => {
                      if (e.target.value !== setting.value) {
                        handleSettingChange(setting.key, e.target.value)
                      }
                    }}
                    className="px-3 py-1.5 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                  />
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Users */}
      {activeTab === 'users' && (
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <div className="p-4 border-b border-gray-700">
            <h2 className="font-semibold">User Management</h2>
          </div>
          <div className="p-4">
            <p className="text-gray-400">User management coming soon.</p>
            <p className="text-sm text-gray-500 mt-2">
              Current roles: admin, operator, viewer, service
            </p>
          </div>
        </div>
      )}

      {/* API Keys */}
      {activeTab === 'api' && (
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <div className="p-4 border-b border-gray-700">
            <h2 className="font-semibold">API Keys</h2>
          </div>
          <div className="p-4">
            <p className="text-gray-400">API key management coming soon.</p>
            <p className="text-sm text-gray-500 mt-2">
              API keys can be used for service account authentication.
            </p>
          </div>
        </div>
      )}

      {/* System Info */}
      <div className="mt-6 bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h2 className="font-semibold mb-4">System Information</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Version:</span>
            <span className="ml-2">2.0.0</span>
          </div>
          <div>
            <span className="text-gray-400">API Endpoint:</span>
            <span className="ml-2">/api/v1</span>
          </div>
          <div>
            <span className="text-gray-400">WebSocket:</span>
            <span className="ml-2">/ws</span>
          </div>
          <div>
            <span className="text-gray-400">Webhooks:</span>
            <span className="ml-2">/webhooks/*</span>
          </div>
        </div>
      </div>
    </div>
  )
}
