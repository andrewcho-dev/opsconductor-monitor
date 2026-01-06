import React, { useState, useEffect } from 'react';
import { 
  Shield, Lock, Clock, History, AlertTriangle, Check, 
  Loader2, Save, RotateCcw
} from 'lucide-react';
import { fetchApi, cn } from '../../../lib/utils';
import { useAuth } from '../../../contexts/AuthContext';

export function PasswordPolicySettings() {
  const { getAuthHeader, hasPermission } = useAuth();
  const [policy, setPolicy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [originalPolicy, setOriginalPolicy] = useState(null);

  const canEdit = hasPermission('system.settings.edit');

  useEffect(() => { loadPolicy(); }, []);

  const loadPolicy = async () => {
    setLoading(true);
    try {
      const res = await fetchApi('/identity/v1/password-policy', { headers: getAuthHeader() });
      if (res.success) {
        setPolicy(res.data.policy);
        setOriginalPolicy(res.data.policy);
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to load password policy' });
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setPolicy(prev => ({ ...prev, [field]: value }));
    setHasChanges(true);
    setMessage(null);
  };

  const handleSave = async () => {
    setMessage(null);
    setSaving(true);
    try {
      const res = await fetchApi('/identity/v1/password-policy', {
        method: 'PUT',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify(policy)
      });
      if (res.success) {
        setOriginalPolicy(res.data.policy);
        setPolicy(res.data.policy);
        setHasChanges(false);
        setMessage({ type: 'success', text: 'Password policy updated' });
      } else {
        setMessage({ type: 'error', text: res.error?.message || 'Failed to save' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.message || 'Failed to save' });
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setPolicy(originalPolicy);
    setHasChanges(false);
    setMessage(null);
  };

  if (loading) {
    return <div className="flex items-center justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-gray-400" /></div>;
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="px-5 py-3 border-b border-gray-200 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Security Settings</h2>
          <p className="text-xs text-gray-500">Password policy and account lockout</p>
        </div>
        <div className="flex items-center gap-2">
          {message && (
            <span className={cn("text-xs px-2 py-1 rounded", message.type === 'success' ? "bg-green-50 text-green-600" : "bg-red-50 text-red-600")}>
              {message.text}
            </span>
          )}
          {canEdit && hasChanges && (
            <>
              <button onClick={handleReset} className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
                <RotateCcw className="w-3.5 h-3.5" />Reset
              </button>
              <button onClick={handleSave} disabled={saving} className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}Save
              </button>
            </>
          )}
        </div>
      </div>

      <div className="p-5 grid grid-cols-2 gap-5">
        {/* Complexity */}
        <div className="border rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <Lock className="w-4 h-4 text-blue-600" />
            <span className="text-xs font-semibold text-gray-900">Password Complexity</span>
          </div>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-xs text-gray-600 mb-1">Min Length</label>
              <input type="number" value={policy?.min_length || 8} onChange={(e) => handleChange('min_length', parseInt(e.target.value))} min={6} max={128} disabled={!canEdit} className="w-full px-2 py-1 text-sm border rounded disabled:bg-gray-50" />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">Max Length</label>
              <input type="number" value={policy?.max_length || 128} onChange={(e) => handleChange('max_length', parseInt(e.target.value))} min={16} max={256} disabled={!canEdit} className="w-full px-2 py-1 text-sm border rounded disabled:bg-gray-50" />
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="flex items-center gap-2 text-xs text-gray-700">
              <input type="checkbox" checked={policy?.require_uppercase || false} onChange={(e) => handleChange('require_uppercase', e.target.checked)} disabled={!canEdit} className="rounded w-3.5 h-3.5" />
              Uppercase
            </label>
            <label className="flex items-center gap-2 text-xs text-gray-700">
              <input type="checkbox" checked={policy?.require_lowercase || false} onChange={(e) => handleChange('require_lowercase', e.target.checked)} disabled={!canEdit} className="rounded w-3.5 h-3.5" />
              Lowercase
            </label>
            <label className="flex items-center gap-2 text-xs text-gray-700">
              <input type="checkbox" checked={policy?.require_numbers || false} onChange={(e) => handleChange('require_numbers', e.target.checked)} disabled={!canEdit} className="rounded w-3.5 h-3.5" />
              Numbers
            </label>
            <label className="flex items-center gap-2 text-xs text-gray-700">
              <input type="checkbox" checked={policy?.require_special_chars || false} onChange={(e) => handleChange('require_special_chars', e.target.checked)} disabled={!canEdit} className="rounded w-3.5 h-3.5" />
              Special chars
            </label>
          </div>
        </div>

        {/* Expiration */}
        <div className="border rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <Clock className="w-4 h-4 text-amber-600" />
            <span className="text-xs font-semibold text-gray-900">Expiration</span>
          </div>
          <label className="flex items-center gap-2 text-xs text-gray-700 mb-3">
            <input type="checkbox" checked={policy?.password_expires || false} onChange={(e) => handleChange('password_expires', e.target.checked)} disabled={!canEdit} className="rounded w-3.5 h-3.5" />
            Enable expiration
          </label>
          {policy?.password_expires && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-600 mb-1">Expires (days)</label>
                <input type="number" value={policy?.expiration_days || 90} onChange={(e) => handleChange('expiration_days', parseInt(e.target.value))} min={1} max={365} disabled={!canEdit} className="w-full px-2 py-1 text-sm border rounded disabled:bg-gray-50" />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Warning (days)</label>
                <input type="number" value={policy?.expiration_warning_days || 14} onChange={(e) => handleChange('expiration_warning_days', parseInt(e.target.value))} min={1} max={30} disabled={!canEdit} className="w-full px-2 py-1 text-sm border rounded disabled:bg-gray-50" />
              </div>
            </div>
          )}
        </div>

        {/* History */}
        <div className="border rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <History className="w-4 h-4 text-purple-600" />
            <span className="text-xs font-semibold text-gray-900">Password History</span>
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Remember last N passwords</label>
            <input type="number" value={policy?.password_history_count ?? 12} onChange={(e) => handleChange('password_history_count', parseInt(e.target.value) || 0)} min="0" max="24" disabled={!canEdit} className="w-full px-2 py-1 text-sm border rounded disabled:bg-gray-50" />
            <p className="text-xs text-gray-400 mt-1">0 = disabled</p>
          </div>
        </div>

        {/* Lockout */}
        <div className="border rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="w-4 h-4 text-red-600" />
            <span className="text-xs font-semibold text-gray-900">Account Lockout</span>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-600 mb-1">Max attempts</label>
              <input type="number" value={policy?.max_failed_attempts || 5} onChange={(e) => handleChange('max_failed_attempts', parseInt(e.target.value))} min={3} max={20} disabled={!canEdit} className="w-full px-2 py-1 text-sm border rounded disabled:bg-gray-50" />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">Lockout (min)</label>
              <input type="number" value={policy?.lockout_duration_minutes || 30} onChange={(e) => handleChange('lockout_duration_minutes', parseInt(e.target.value))} min={5} max={1440} disabled={!canEdit} className="w-full px-2 py-1 text-sm border rounded disabled:bg-gray-50" />
            </div>
          </div>
        </div>

        {/* Additional Controls */}
        <div className="col-span-2 border rounded-lg p-4">
          <span className="text-xs font-semibold text-gray-900 mb-2 block">Additional Controls</span>
          <div className="flex flex-wrap gap-x-6 gap-y-1.5">
            <label className="flex items-center gap-2 text-xs text-gray-700">
              <input type="checkbox" checked={policy?.prevent_username_in_password || false} onChange={(e) => handleChange('prevent_username_in_password', e.target.checked)} disabled={!canEdit} className="rounded w-3.5 h-3.5" />
              No username in password
            </label>
            <label className="flex items-center gap-2 text-xs text-gray-700">
              <input type="checkbox" checked={policy?.prevent_email_in_password || false} onChange={(e) => handleChange('prevent_email_in_password', e.target.checked)} disabled={!canEdit} className="rounded w-3.5 h-3.5" />
              No email in password
            </label>
            <label className="flex items-center gap-2 text-xs text-gray-700">
              <input type="checkbox" checked={policy?.prevent_common_passwords || false} onChange={(e) => handleChange('prevent_common_passwords', e.target.checked)} disabled={!canEdit} className="rounded w-3.5 h-3.5" />
              Block common passwords
            </label>
            <label className="flex items-center gap-2 text-xs text-gray-700">
              <input type="checkbox" checked={policy?.require_password_change_on_first_login || false} onChange={(e) => handleChange('require_password_change_on_first_login', e.target.checked)} disabled={!canEdit} className="rounded w-3.5 h-3.5" />
              Change on first login
            </label>
            <label className="flex items-center gap-2 text-xs text-gray-700">
              <input type="checkbox" checked={policy?.allow_password_reset || true} onChange={(e) => handleChange('allow_password_reset', e.target.checked)} disabled={!canEdit} className="rounded w-3.5 h-3.5" />
              Allow self-service reset
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PasswordPolicySettings;
