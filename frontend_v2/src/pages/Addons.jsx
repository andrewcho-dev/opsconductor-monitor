import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Puzzle, Power, PowerOff, Trash2, Upload, RefreshCw, FileArchive, FileJson, Settings, ChevronRight } from 'lucide-react'
import clsx from 'clsx'

const methodColors = {
  snmp_trap: 'bg-purple-600',
  webhook: 'bg-blue-600',
  api_poll: 'bg-green-600',
  snmp_poll: 'bg-indigo-600',
  ssh: 'bg-orange-600',
}

export default function Addons() {
  const navigate = useNavigate()
  const [addons, setAddons] = useState([])
  const [loading, setLoading] = useState(true)
  const [showInstall, setShowInstall] = useState(false)
  const [installMode, setInstallMode] = useState('zip') // 'zip' or 'json'
  const [manifest, setManifest] = useState('')
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef(null)

  const fetchAddons = async () => {
    const token = localStorage.getItem('access_token')
    const res = await fetch('/api/v1/addons?include_disabled=true', {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.ok) {
      const data = await res.json()
      setAddons(data.items || [])
    }
    setLoading(false)
  }

  useEffect(() => {
    fetchAddons()
  }, [])

  const handleEnable = async (addonId) => {
    const token = localStorage.getItem('access_token')
    await fetch(`/api/v1/addons/${addonId}/enable`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    })
    fetchAddons()
  }

  const handleDisable = async (addonId) => {
    const token = localStorage.getItem('access_token')
    await fetch(`/api/v1/addons/${addonId}/disable`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    })
    fetchAddons()
  }

  const handleUninstall = async (addonId) => {
    if (!confirm('Are you sure you want to uninstall this addon?')) return
    const token = localStorage.getItem('access_token')
    await fetch(`/api/v1/addons/${addonId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    })
    fetchAddons()
  }

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      setSelectedFile(file)
    }
  }

  const handleInstallZip = async () => {
    if (!selectedFile) {
      alert('Please select a ZIP file')
      return
    }

    setUploading(true)
    const token = localStorage.getItem('access_token')
    const formData = new FormData()
    formData.append('file', selectedFile)

    try {
      const res = await fetch('/api/v1/addons/upload', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      })

      if (res.ok) {
        setShowInstall(false)
        setSelectedFile(null)
        fetchAddons()
      } else {
        const err = await res.json()
        alert(err.detail || 'Install failed')
      }
    } catch (e) {
      alert('Upload failed: ' + e.message)
    }
    setUploading(false)
  }

  const handleInstallJson = async () => {
    try {
      const parsed = JSON.parse(manifest)
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/addons/install', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ manifest: parsed })
      })
      if (res.ok) {
        setShowInstall(false)
        setManifest('')
        fetchAddons()
      } else {
        const err = await res.json()
        alert(err.detail || 'Install failed')
      }
    } catch (e) {
      alert('Invalid JSON manifest')
    }
  }

  const handleInstall = () => {
    if (installMode === 'zip') {
      handleInstallZip()
    } else {
      handleInstallJson()
    }
  }

  const handleReload = async () => {
    const token = localStorage.getItem('access_token')
    await fetch('/api/v1/addons/reload', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    })
    fetchAddons()
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Addons</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={handleReload}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Reload
          </button>
          <button
            onClick={() => setShowInstall(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center gap-2"
          >
            <Upload className="w-4 h-4" />
            Install Addon
          </button>
        </div>
      </div>

      {/* Install Modal */}
      {showInstall && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-2xl">
            <h2 className="text-xl font-bold mb-4">Install Addon</h2>
            
            {/* Mode Toggle */}
            <div className="flex gap-2 mb-4">
              <button
                onClick={() => setInstallMode('zip')}
                className={clsx(
                  'flex items-center gap-2 px-4 py-2 rounded-lg',
                  installMode === 'zip' ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
                )}
              >
                <FileArchive className="w-4 h-4" />
                Upload ZIP
              </button>
              <button
                onClick={() => setInstallMode('json')}
                className={clsx(
                  'flex items-center gap-2 px-4 py-2 rounded-lg',
                  installMode === 'json' ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
                )}
              >
                <FileJson className="w-4 h-4" />
                Paste JSON
              </button>
            </div>

            {/* ZIP Upload */}
            {installMode === 'zip' && (
              <div className="space-y-4">
                <p className="text-gray-400">Upload an addon package (ZIP file containing manifest.json):</p>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center cursor-pointer hover:border-blue-500 transition-colors"
                >
                  <FileArchive className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                  {selectedFile ? (
                    <p className="text-white">{selectedFile.name}</p>
                  ) : (
                    <p className="text-gray-400">Click to select or drag & drop a ZIP file</p>
                  )}
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".zip"
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </div>
            )}

            {/* JSON Paste */}
            {installMode === 'json' && (
              <div className="space-y-4">
                <p className="text-gray-400">Paste the addon manifest.json content:</p>
                <textarea
                  value={manifest}
                  onChange={e => setManifest(e.target.value)}
                  className="w-full h-64 px-4 py-2 bg-gray-900 border border-gray-700 rounded-lg font-mono text-sm focus:outline-none focus:border-blue-500"
                  placeholder='{"id": "my-addon", "name": "My Addon", "method": "webhook", ...}'
                />
              </div>
            )}

            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => { setShowInstall(false); setManifest(''); setSelectedFile(null) }}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleInstall}
                disabled={uploading}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50"
              >
                {uploading ? 'Installing...' : 'Install'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Addons Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          <div className="col-span-full text-center py-8 text-gray-400">Loading...</div>
        ) : addons.length === 0 ? (
          <div className="col-span-full text-center py-8 text-gray-400">No addons installed</div>
        ) : (
          addons.map(addon => (
            <div
              key={addon.id}
              className={clsx(
                'bg-gray-800 rounded-lg border p-4',
                addon.enabled ? 'border-gray-700' : 'border-gray-700/50 opacity-60'
              )}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className={clsx('p-2 rounded-lg', methodColors[addon.method] || 'bg-gray-600')}>
                    <Puzzle className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold">{addon.name}</h3>
                    <p className="text-sm text-gray-400">v{addon.version}</p>
                  </div>
                </div>
                <span className={clsx(
                  'px-2 py-0.5 rounded text-xs',
                  addon.enabled ? 'bg-green-900 text-green-300' : 'bg-gray-700 text-gray-400'
                )}>
                  {addon.enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>

              <p className="text-sm text-gray-400 mb-3">{addon.description || 'No description'}</p>

              <div className="flex items-center gap-2 mb-4">
                <span className={clsx(
                  'px-2 py-0.5 rounded text-xs',
                  methodColors[addon.method] || 'bg-gray-600'
                )}>
                  {addon.method}
                </span>
                <span className="px-2 py-0.5 rounded text-xs bg-gray-700">
                  {addon.category}
                </span>
              </div>

              <div className="flex items-center gap-2 pt-3 border-t border-gray-700">
                <button
                  onClick={() => navigate(`/addons/${addon.id}`)}
                  className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded text-sm"
                >
                  <Settings className="w-4 h-4" />
                  Configure
                </button>
                {addon.enabled ? (
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDisable(addon.id) }}
                    className="flex items-center gap-1 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm"
                  >
                    <PowerOff className="w-4 h-4" />
                    Disable
                  </button>
                ) : (
                  <button
                    onClick={(e) => { e.stopPropagation(); handleEnable(addon.id) }}
                    className="flex items-center gap-1 px-3 py-1.5 bg-green-700 hover:bg-green-600 rounded text-sm"
                  >
                    <Power className="w-4 h-4" />
                    Enable
                  </button>
                )}
                <button
                  onClick={(e) => { e.stopPropagation(); handleUninstall(addon.id) }}
                  className="flex items-center gap-1 px-3 py-1.5 bg-red-700 hover:bg-red-600 rounded text-sm"
                >
                  <Trash2 className="w-4 h-4" />
                  Uninstall
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
