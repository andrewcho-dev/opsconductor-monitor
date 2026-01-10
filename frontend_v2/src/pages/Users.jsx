import { useState, useEffect } from 'react'
import { Plus, Edit2, Trash2, User, Shield, Key } from 'lucide-react'
import clsx from 'clsx'

const roleColors = {
  admin: 'bg-red-600',
  operator: 'bg-blue-600',
  viewer: 'bg-green-600',
  service: 'bg-purple-600',
}

export default function Users() {
  const [users, setUsers] = useState([])
  const [apiKeys, setApiKeys] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('users')
  const [showModal, setShowModal] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    role: 'viewer',
    is_active: true
  })

  const token = localStorage.getItem('access_token')
  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [usersRes, keysRes] = await Promise.all([
        fetch('/api/v1/users', { headers }),
        fetch('/api/v1/api-keys', { headers })
      ])
      if (usersRes.ok) {
        const data = await usersRes.json()
        setUsers(data.items || [])
      }
      if (keysRes.ok) {
        const data = await keysRes.json()
        setApiKeys(data.items || [])
      }
    } catch (e) {
      console.error('Failed to fetch data')
    }
    setLoading(false)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    const payload = { ...form }
    if (!payload.password) delete payload.password

    const url = editingUser 
      ? `/api/v1/users/${editingUser.id}`
      : '/api/v1/users'
    
    const method = editingUser ? 'PUT' : 'POST'

    const res = await fetch(url, {
      method,
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    if (res.ok) {
      setShowModal(false)
      setEditingUser(null)
      setForm({ username: '', email: '', password: '', role: 'viewer', is_active: true })
      fetchData()
    } else {
      const err = await res.json()
      alert(err.detail || 'Failed to save user')
    }
  }

  const handleEdit = (user) => {
    setEditingUser(user)
    setForm({
      username: user.username,
      email: user.email || '',
      password: '',
      role: user.role,
      is_active: user.is_active
    })
    setShowModal(true)
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this user?')) return
    await fetch(`/api/v1/users/${id}`, { method: 'DELETE', headers })
    fetchData()
  }

  const handleCreateApiKey = async () => {
    const name = prompt('API Key name:')
    if (!name) return

    const res = await fetch('/api/v1/api-keys', {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    })

    if (res.ok) {
      const data = await res.json()
      alert(`API Key created!\n\nKey: ${data.key}\n\nSave this key - it won't be shown again.`)
      fetchData()
    }
  }

  const handleDeleteApiKey = async (id) => {
    if (!confirm('Revoke this API key?')) return
    await fetch(`/api/v1/api-keys/${id}`, { method: 'DELETE', headers })
    fetchData()
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">User Management</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-gray-700">
        <button
          onClick={() => setActiveTab('users')}
          className={clsx(
            'flex items-center gap-2 px-4 py-2 -mb-px border-b-2 transition-colors',
            activeTab === 'users'
              ? 'border-blue-500 text-blue-500'
              : 'border-transparent text-gray-400 hover:text-white'
          )}
        >
          <User className="w-4 h-4" />
          Users
        </button>
        <button
          onClick={() => setActiveTab('apikeys')}
          className={clsx(
            'flex items-center gap-2 px-4 py-2 -mb-px border-b-2 transition-colors',
            activeTab === 'apikeys'
              ? 'border-blue-500 text-blue-500'
              : 'border-transparent text-gray-400 hover:text-white'
          )}
        >
          <Key className="w-4 h-4" />
          API Keys
        </button>
      </div>

      {/* Users Tab */}
      {activeTab === 'users' && (
        <>
          <div className="flex justify-end mb-4">
            <button
              onClick={() => {
                setEditingUser(null)
                setForm({ username: '', email: '', password: '', role: 'viewer', is_active: true })
                setShowModal(true)
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Add User
            </button>
          </div>

          <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-900">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Username</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Email</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Role</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Last Login</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-400">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {loading ? (
                  <tr>
                    <td colSpan="6" className="px-4 py-8 text-center text-gray-400">Loading...</td>
                  </tr>
                ) : users.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="px-4 py-8 text-center text-gray-400">No users found</td>
                  </tr>
                ) : (
                  users.map(user => (
                    <tr key={user.id} className={clsx(!user.is_active && 'opacity-50')}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <User className="w-4 h-4 text-gray-400" />
                          {user.username}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-400">{user.email || '-'}</td>
                      <td className="px-4 py-3">
                        <span className={clsx(
                          'px-2 py-0.5 rounded text-xs text-white',
                          roleColors[user.role] || 'bg-gray-600'
                        )}>
                          {user.role}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={clsx(
                          'px-2 py-0.5 rounded text-xs',
                          user.is_active ? 'bg-green-900 text-green-300' : 'bg-gray-700 text-gray-400'
                        )}>
                          {user.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-400">
                        {user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleEdit(user)}
                            className="p-1.5 hover:bg-gray-700 rounded"
                            title="Edit"
                          >
                            <Edit2 className="w-4 h-4 text-gray-400" />
                          </button>
                          <button
                            onClick={() => handleDelete(user.id)}
                            className="p-1.5 hover:bg-gray-700 rounded"
                            title="Delete"
                            disabled={user.username === 'admin'}
                          >
                            <Trash2 className={clsx(
                              'w-4 h-4',
                              user.username === 'admin' ? 'text-gray-600' : 'text-red-400'
                            )} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* API Keys Tab */}
      {activeTab === 'apikeys' && (
        <>
          <div className="flex justify-end mb-4">
            <button
              onClick={handleCreateApiKey}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Create API Key
            </button>
          </div>

          <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-900">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Name</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Key Prefix</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Created</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Last Used</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-400">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {loading ? (
                  <tr>
                    <td colSpan="5" className="px-4 py-8 text-center text-gray-400">Loading...</td>
                  </tr>
                ) : apiKeys.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="px-4 py-8 text-center text-gray-400">
                      No API keys. Click "Create API Key" to generate one.
                    </td>
                  </tr>
                ) : (
                  apiKeys.map(key => (
                    <tr key={key.id}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Key className="w-4 h-4 text-gray-400" />
                          {key.name}
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono text-sm text-gray-400">
                        {key.key_prefix}...
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-400">
                        {new Date(key.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-400">
                        {key.last_used_at ? new Date(key.last_used_at).toLocaleString() : 'Never'}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end">
                          <button
                            onClick={() => handleDeleteApiKey(key.id)}
                            className="p-1.5 hover:bg-gray-700 rounded text-red-400"
                            title="Revoke"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* User Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">
              {editingUser ? 'Edit User' : 'Add User'}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Username</label>
                <input
                  type="text"
                  value={form.username}
                  onChange={e => setForm({ ...form, username: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                  required
                  disabled={editingUser}
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={e => setForm({ ...form, email: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  Password {editingUser && '(leave blank to keep current)'}
                </label>
                <input
                  type="password"
                  value={form.password}
                  onChange={e => setForm({ ...form, password: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                  required={!editingUser}
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Role</label>
                <select
                  value={form.role}
                  onChange={e => setForm({ ...form, role: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                >
                  <option value="admin">Admin</option>
                  <option value="operator">Operator</option>
                  <option value="viewer">Viewer</option>
                  <option value="service">Service</option>
                </select>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={form.is_active}
                  onChange={e => setForm({ ...form, is_active: e.target.checked })}
                  className="w-4 h-4"
                />
                <label htmlFor="is_active" className="text-sm">Active</label>
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
                  {editingUser ? 'Save' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
