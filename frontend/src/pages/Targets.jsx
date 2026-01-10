import { useState, useEffect } from 'react'
import { Plus, Edit2, Trash2, Server, Power, PowerOff } from 'lucide-react'
import clsx from 'clsx'

export default function Targets() {
  const [targets, setTargets] = useState([])
  const [addons, setAddons] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingTarget, setEditingTarget] = useState(null)
  const [form, setForm] = useState({
    name: '',
    ip_address: '',
    addon_id: '',
    poll_interval: 300,
    enabled: true,
    config: '{}'
  })

  const token = localStorage.getItem('access_token')
  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [targetsRes, addonsRes] = await Promise.all([
        fetch('/api/v1/targets', { headers }),
        fetch('/api/v1/addons?include_disabled=true', { headers })
      ])
      if (targetsRes.ok) {
        const data = await targetsRes.json()
        setTargets(data.items || [])
      }
      if (addonsRes.ok) {
        const data = await addonsRes.json()
        setAddons(data.items || [])
      }
    } catch (e) {
      console.error('Failed to fetch data')
    }
    setLoading(false)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    let configJson = {}
    try {
      configJson = JSON.parse(form.config)
    } catch {
      alert('Invalid JSON in config field')
      return
    }

    const payload = {
      ...form,
      poll_interval: parseInt(form.poll_interval),
      config: configJson
    }

    const url = editingTarget 
      ? `/api/v1/targets/${editingTarget.id}`
      : '/api/v1/targets'
    
    const method = editingTarget ? 'PUT' : 'POST'

    const res = await fetch(url, {
      method,
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    if (res.ok) {
      setShowModal(false)
      setEditingTarget(null)
      setForm({ name: '', ip_address: '', addon_id: '', poll_interval: 300, enabled: true, config: '{}' })
      fetchData()
    } else {
      const err = await res.json()
      alert(err.detail || 'Failed to save target')
    }
  }

  const handleEdit = (target) => {
    setEditingTarget(target)
    setForm({
      name: target.name,
      ip_address: target.ip_address,
      addon_id: target.addon_id || '',
      poll_interval: target.poll_interval || 300,
      enabled: target.enabled,
      config: JSON.stringify(target.config || {}, null, 2)
    })
    setShowModal(true)
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this target?')) return
    await fetch(`/api/v1/targets/${id}`, { method: 'DELETE', headers })
    fetchData()
  }

  const handleToggle = async (target) => {
    await fetch(`/api/v1/targets/${target.id}`, {
      method: 'PUT',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...target, enabled: !target.enabled })
    })
    fetchData()
  }

  const getAddonName = (addonId) => {
    const addon = addons.find(a => a.id === addonId)
    return addon?.name || addonId || 'None'
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Targets</h1>
        <button
          onClick={() => {
            setEditingTarget(null)
            setForm({ name: '', ip_address: '', addon_id: '', poll_interval: 300, enabled: true, config: '{}' })
            setShowModal(true)
          }}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Add Target
        </button>
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-lg">
            <h2 className="text-xl font-bold mb-4">
              {editingTarget ? 'Edit Target' : 'Add Target'}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">IP Address</label>
                <input
                  type="text"
                  value={form.ip_address}
                  onChange={e => setForm({ ...form, ip_address: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                  required
                  placeholder="192.168.1.1"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Addon</label>
                <select
                  value={form.addon_id}
                  onChange={e => setForm({ ...form, addon_id: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                >
                  <option value="">None (receive only)</option>
                  {addons.map(addon => (
                    <option key={addon.id} value={addon.id}>{addon.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Poll Interval (seconds)</label>
                <input
                  type="number"
                  value={form.poll_interval}
                  onChange={e => setForm({ ...form, poll_interval: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                  min="60"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Configuration (JSON)</label>
                <textarea
                  value={form.config}
                  onChange={e => setForm({ ...form, config: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500 font-mono text-sm h-32"
                  placeholder='{"api_key": "xxx", "community": "public"}'
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="enabled"
                  checked={form.enabled}
                  onChange={e => setForm({ ...form, enabled: e.target.checked })}
                  className="w-4 h-4"
                />
                <label htmlFor="enabled" className="text-sm">Enabled</label>
              </div>
              <div className="flex justify-end gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded"
                >
                  {editingTarget ? 'Save' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Targets Table */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-900">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Name</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">IP Address</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Addon</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Poll Interval</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Status</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Last Poll</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-400">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {loading ? (
              <tr>
                <td colSpan="7" className="px-4 py-8 text-center text-gray-400">Loading...</td>
              </tr>
            ) : targets.length === 0 ? (
              <tr>
                <td colSpan="7" className="px-4 py-8 text-center text-gray-400">
                  No targets configured. Click "Add Target" to create one.
                </td>
              </tr>
            ) : (
              targets.map(target => (
                <tr key={target.id} className={clsx(!target.enabled && 'opacity-50')}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Server className="w-4 h-4 text-gray-400" />
                      {target.name}
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-sm">{target.ip_address}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 bg-gray-700 rounded text-sm">
                      {getAddonName(target.addon_id)}
                    </span>
                  </td>
                  <td className="px-4 py-3">{target.poll_interval}s</td>
                  <td className="px-4 py-3">
                    <span className={clsx(
                      'px-2 py-0.5 rounded text-xs',
                      target.enabled ? 'bg-green-900 text-green-300' : 'bg-gray-700 text-gray-400'
                    )}>
                      {target.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-400">
                    {target.last_poll_at ? new Date(target.last_poll_at).toLocaleString() : 'Never'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleToggle(target)}
                        className="p-1.5 hover:bg-gray-700 rounded"
                        title={target.enabled ? 'Disable' : 'Enable'}
                      >
                        {target.enabled ? (
                          <PowerOff className="w-4 h-4 text-gray-400" />
                        ) : (
                          <Power className="w-4 h-4 text-green-500" />
                        )}
                      </button>
                      <button
                        onClick={() => handleEdit(target)}
                        className="p-1.5 hover:bg-gray-700 rounded"
                        title="Edit"
                      >
                        <Edit2 className="w-4 h-4 text-gray-400" />
                      </button>
                      <button
                        onClick={() => handleDelete(target.id)}
                        className="p-1.5 hover:bg-gray-700 rounded"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4 text-red-400" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
