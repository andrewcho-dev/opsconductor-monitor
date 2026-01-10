import { useState, useEffect } from 'react'
import { Save, User, Key, Shield } from 'lucide-react'

export default function Settings() {
  const [settings, setSettings] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('system')

  const token = localStorage.getItem('access_token')
  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => {
    fetchData()
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

  const handleSettingChange = async (key, value) => {
    await fetch(`/api/v1/settings/${key}`, {
      method: 'PUT',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ value })
    })
    fetchData()
  }

  const tabs = [
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
