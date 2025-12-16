import React, { useState, useEffect } from 'react';
import { 
  Shield, Lock, Clock, History, AlertTriangle, Check, 
  Loader2, Save, RotateCcw, Info
} from 'lucide-react';
import { fetchApi, cn } from '../../../lib/utils';
import { useAuth } from '../../../contexts/AuthContext';

export function PasswordPolicySettings() {
  const { getAuthHeader, hasPermission } = useAuth();
  const [policy, setPolicy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [hasChanges, setHasChanges] = useState(false);
  const [originalPolicy, setOriginalPolicy] = useState(null);

  const canEdit = hasPermission('system.settings.edit');

  useEffect(() => {
    loadPolicy();
  }, []);

  const loadPolicy = async () => {
    setLoading(true);
    try {
      const res = await fetchApi('/api/auth/password-policy', {
        headers: getAuthHeader()
      });
      if (res.success) {
        setPolicy(res.data.policy);
        setOriginalPolicy(res.data.policy);
      }
    } catch (err) {
      setError('Failed to load password policy');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setPolicy(prev => ({ ...prev, [field]: value }));
    setHasChanges(true);
    setSuccess('');
  };

  const handleSave = async () => {
    setError('');
    setSuccess('');
    setSaving(true);

    try {
      const res = await fetchApi('/api/auth/password-policy', {
        method: 'PUT',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify(policy)
      });

      if (res.success) {
        setOriginalPolicy(res.data.policy);
        setPolicy(res.data.policy);
        setHasChanges(false);
        setSuccess('Password policy updated successfully');
      } else {
        setError(res.error?.message || 'Failed to save policy');
      }
    } catch (err) {
      setError(err.message || 'Failed to save policy');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setPolicy(originalPolicy);
    setHasChanges(false);
    setError('');
    setSuccess('');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Password Policy</h2>
          <p className="text-sm text-gray-500">Configure password requirements and security controls</p>
        </div>
        {canEdit && hasChanges && (
          <div className="flex items-center gap-2">
            <button
              onClick={handleReset}
              className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg flex items-center gap-1"
            >
              <RotateCcw className="w-4 h-4" />
              Reset
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Save Changes
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-500" />
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {success && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2">
          <Check className="w-4 h-4 text-green-500" />
          <p className="text-sm text-green-600">{success}</p>
        </div>
      )}

      {/* Complexity Requirements */}
      <div className="bg-white rounded-xl border p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Lock className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Complexity Requirements</h3>
            <p className="text-sm text-gray-500">Define password strength requirements</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Minimum Length
            </label>
            <input
              type="number"
              value={policy?.min_length || 8}
              onChange={(e) => handleChange('min_length', parseInt(e.target.value))}
              min={6}
              max={128}
              disabled={!canEdit}
              className="w-full px-3 py-2 border rounded-lg disabled:bg-gray-50"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Maximum Length
            </label>
            <input
              type="number"
              value={policy?.max_length || 128}
              onChange={(e) => handleChange('max_length', parseInt(e.target.value))}
              min={16}
              max={256}
              disabled={!canEdit}
              className="w-full px-3 py-2 border rounded-lg disabled:bg-gray-50"
            />
          </div>
        </div>

        <div className="mt-4 space-y-3">
          <label className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={policy?.require_uppercase || false}
                onChange={(e) => handleChange('require_uppercase', e.target.checked)}
                disabled={!canEdit}
                className="rounded"
              />
              <span className="text-sm text-gray-700">Require uppercase letters</span>
            </div>
            {policy?.require_uppercase && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">Minimum:</span>
                <input
                  type="number"
                  value={policy?.min_uppercase || 1}
                  onChange={(e) => handleChange('min_uppercase', parseInt(e.target.value))}
                  min={1}
                  max={10}
                  disabled={!canEdit}
                  className="w-16 px-2 py-1 text-sm border rounded"
                />
              </div>
            )}
          </label>

          <label className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={policy?.require_lowercase || false}
                onChange={(e) => handleChange('require_lowercase', e.target.checked)}
                disabled={!canEdit}
                className="rounded"
              />
              <span className="text-sm text-gray-700">Require lowercase letters</span>
            </div>
            {policy?.require_lowercase && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">Minimum:</span>
                <input
                  type="number"
                  value={policy?.min_lowercase || 1}
                  onChange={(e) => handleChange('min_lowercase', parseInt(e.target.value))}
                  min={1}
                  max={10}
                  disabled={!canEdit}
                  className="w-16 px-2 py-1 text-sm border rounded"
                />
              </div>
            )}
          </label>

          <label className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={policy?.require_numbers || false}
                onChange={(e) => handleChange('require_numbers', e.target.checked)}
                disabled={!canEdit}
                className="rounded"
              />
              <span className="text-sm text-gray-700">Require numbers</span>
            </div>
            {policy?.require_numbers && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">Minimum:</span>
                <input
                  type="number"
                  value={policy?.min_numbers || 1}
                  onChange={(e) => handleChange('min_numbers', parseInt(e.target.value))}
                  min={1}
                  max={10}
                  disabled={!canEdit}
                  className="w-16 px-2 py-1 text-sm border rounded"
                />
              </div>
            )}
          </label>

          <label className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={policy?.require_special_chars || false}
                onChange={(e) => handleChange('require_special_chars', e.target.checked)}
                disabled={!canEdit}
                className="rounded"
              />
              <span className="text-sm text-gray-700">Require special characters</span>
            </div>
            {policy?.require_special_chars && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">Minimum:</span>
                <input
                  type="number"
                  value={policy?.min_special || 1}
                  onChange={(e) => handleChange('min_special', parseInt(e.target.value))}
                  min={1}
                  max={10}
                  disabled={!canEdit}
                  className="w-16 px-2 py-1 text-sm border rounded"
                />
              </div>
            )}
          </label>
        </div>

        {policy?.require_special_chars && (
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Allowed Special Characters
            </label>
            <input
              type="text"
              value={policy?.special_chars_allowed || '!@#$%^&*()_+-=[]{}|;:,.<>?'}
              onChange={(e) => handleChange('special_chars_allowed', e.target.value)}
              disabled={!canEdit}
              className="w-full px-3 py-2 border rounded-lg font-mono text-sm disabled:bg-gray-50"
            />
          </div>
        )}
      </div>

      {/* Expiration Settings */}
      <div className="bg-white rounded-xl border p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-amber-100 rounded-lg">
            <Clock className="w-5 h-5 text-amber-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Password Expiration</h3>
            <p className="text-sm text-gray-500">Configure password aging and expiration</p>
          </div>
        </div>

        <div className="space-y-4">
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={policy?.password_expires || false}
              onChange={(e) => handleChange('password_expires', e.target.checked)}
              disabled={!canEdit}
              className="rounded"
            />
            <span className="text-sm text-gray-700">Enable password expiration</span>
          </label>

          {policy?.password_expires && (
            <div className="grid grid-cols-2 gap-6 pl-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Password expires after (days)
                </label>
                <input
                  type="number"
                  value={policy?.expiration_days || 90}
                  onChange={(e) => handleChange('expiration_days', parseInt(e.target.value))}
                  min={1}
                  max={365}
                  disabled={!canEdit}
                  className="w-full px-3 py-2 border rounded-lg disabled:bg-gray-50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Warning before expiration (days)
                </label>
                <input
                  type="number"
                  value={policy?.expiration_warning_days || 14}
                  onChange={(e) => handleChange('expiration_warning_days', parseInt(e.target.value))}
                  min={1}
                  max={30}
                  disabled={!canEdit}
                  className="w-full px-3 py-2 border rounded-lg disabled:bg-gray-50"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Minimum password age (hours)
            </label>
            <input
              type="number"
              value={policy?.min_password_age_hours || 0}
              onChange={(e) => handleChange('min_password_age_hours', parseInt(e.target.value))}
              min={0}
              max={168}
              disabled={!canEdit}
              className="w-full max-w-xs px-3 py-2 border rounded-lg disabled:bg-gray-50"
            />
            <p className="text-xs text-gray-500 mt-1">
              Prevents users from changing passwords too frequently. Set to 0 to disable.
            </p>
          </div>
        </div>
      </div>

      {/* History and Reuse */}
      <div className="bg-white rounded-xl border p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-purple-100 rounded-lg">
            <History className="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Password History</h3>
            <p className="text-sm text-gray-500">Prevent password reuse</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Remember last N passwords
          </label>
          <input
            type="number"
            value={policy?.password_history_count ?? 12}
            onChange={(e) => handleChange('password_history_count', parseInt(e.target.value) || 0)}
            min="0"
            max="24"
            disabled={!canEdit}
            className="w-full max-w-xs px-3 py-2 border rounded-lg disabled:bg-gray-50"
          />
          <p className="text-xs text-gray-500 mt-1">
            Users cannot reuse any of their last N passwords. Set to 0 to disable.
          </p>
        </div>
      </div>

      {/* Lockout Settings */}
      <div className="bg-white rounded-xl border p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-red-100 rounded-lg">
            <Shield className="w-5 h-5 text-red-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Account Lockout</h3>
            <p className="text-sm text-gray-500">Protect against brute force attacks</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Max failed login attempts
            </label>
            <input
              type="number"
              value={policy?.max_failed_attempts || 5}
              onChange={(e) => handleChange('max_failed_attempts', parseInt(e.target.value))}
              min={3}
              max={20}
              disabled={!canEdit}
              className="w-full px-3 py-2 border rounded-lg disabled:bg-gray-50"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Lockout duration (minutes)
            </label>
            <input
              type="number"
              value={policy?.lockout_duration_minutes || 30}
              onChange={(e) => handleChange('lockout_duration_minutes', parseInt(e.target.value))}
              min={5}
              max={1440}
              disabled={!canEdit}
              className="w-full px-3 py-2 border rounded-lg disabled:bg-gray-50"
            />
          </div>
        </div>
      </div>

      {/* Additional Controls */}
      <div className="bg-white rounded-xl border p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-green-100 rounded-lg">
            <Info className="w-5 h-5 text-green-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Additional Controls</h3>
            <p className="text-sm text-gray-500">Extra security measures</p>
          </div>
        </div>

        <div className="space-y-3">
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={policy?.prevent_username_in_password || false}
              onChange={(e) => handleChange('prevent_username_in_password', e.target.checked)}
              disabled={!canEdit}
              className="rounded"
            />
            <span className="text-sm text-gray-700">Prevent username in password</span>
          </label>

          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={policy?.prevent_email_in_password || false}
              onChange={(e) => handleChange('prevent_email_in_password', e.target.checked)}
              disabled={!canEdit}
              className="rounded"
            />
            <span className="text-sm text-gray-700">Prevent email address in password</span>
          </label>

          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={policy?.prevent_common_passwords || false}
              onChange={(e) => handleChange('prevent_common_passwords', e.target.checked)}
              disabled={!canEdit}
              className="rounded"
            />
            <span className="text-sm text-gray-700">Block common/weak passwords</span>
          </label>

          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={policy?.require_password_change_on_first_login || false}
              onChange={(e) => handleChange('require_password_change_on_first_login', e.target.checked)}
              disabled={!canEdit}
              className="rounded"
            />
            <span className="text-sm text-gray-700">Require password change on first login</span>
          </label>

          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={policy?.allow_password_reset || true}
              onChange={(e) => handleChange('allow_password_reset', e.target.checked)}
              disabled={!canEdit}
              className="rounded"
            />
            <span className="text-sm text-gray-700">Allow self-service password reset</span>
          </label>
        </div>
      </div>
    </div>
  );
}

export default PasswordPolicySettings;
