import React, { useState, useEffect } from 'react';
import { 
  User, Mail, Shield, Key, Lock, Eye, EyeOff, Smartphone,
  Check, X, Copy, Loader2, AlertTriangle, LogOut, Monitor
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { PageLayout, PageHeader } from '../../components/layout';
import { fetchApi, cn } from '../../lib/utils';
import { useAuth } from '../../contexts/AuthContext';

export function ProfilePage() {
  const { user, getAuthHeader, logout } = useAuth();
  const [profile, setProfile] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('profile');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [profileRes, sessionsRes] = await Promise.all([
        fetchApi('/api/auth/me', { headers: getAuthHeader() }),
        fetchApi('/api/auth/sessions', { headers: getAuthHeader() })
      ]);

      if (profileRes.success) {
        setProfile(profileRes.data.user);
      }
      if (sessionsRes.success) {
        setSessions(sessionsRes.data.sessions || []);
      }
    } catch (err) {
      console.error('Error loading profile:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <PageLayout module="system">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout module="system">
      <PageHeader
        title="My Profile"
        description="Manage your account settings and security"
      />
      <div className="p-6 max-w-4xl mx-auto space-y-6">
        {/* Profile Header */}
        <div className="bg-white rounded-xl border p-6">
          <div className="flex items-center gap-6">
            <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-3xl font-bold">
              {(profile?.display_name || profile?.username || '?')[0].toUpperCase()}
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-gray-900">{profile?.display_name || profile?.username}</h2>
              <p className="text-gray-500">@{profile?.username}</p>
              <div className="flex items-center gap-4 mt-2">
                <span className="flex items-center gap-1 text-sm text-gray-600">
                  <Mail className="w-4 h-4" />
                  {profile?.email}
                </span>
                {profile?.two_factor_enabled && (
                  <span className="flex items-center gap-1 text-sm text-green-600">
                    <Shield className="w-4 h-4" />
                    2FA Enabled
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b">
          <nav className="flex gap-6">
            {[
              { id: 'profile', label: 'Profile', icon: User },
              { id: 'security', label: 'Security', icon: Shield },
              { id: 'sessions', label: 'Sessions', icon: Monitor },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-2 px-1 py-3 border-b-2 text-sm font-medium transition-colors",
                  activeTab === tab.id
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                )}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'profile' && (
          <ProfileTab profile={profile} onUpdate={loadData} getAuthHeader={getAuthHeader} />
        )}
        {activeTab === 'security' && (
          <SecurityTab profile={profile} onUpdate={loadData} getAuthHeader={getAuthHeader} />
        )}
        {activeTab === 'sessions' && (
          <SessionsTab sessions={sessions} onUpdate={loadData} getAuthHeader={getAuthHeader} />
        )}
      </div>
    </PageLayout>
  );
}

function ProfileTab({ profile, onUpdate, getAuthHeader }) {
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState({
    first_name: profile?.first_name || '',
    last_name: profile?.last_name || '',
    email: profile?.email || '',
    timezone: profile?.timezone || 'UTC',
  });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetchApi('/api/auth/me', {
        method: 'PUT',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      setEditing(false);
      onUpdate();
    } catch (err) {
      console.error('Error updating profile:', err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Profile Information</h3>
        {!editing ? (
          <button
            onClick={() => setEditing(true)}
            className="px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg"
          >
            Edit
          </button>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={() => setEditing(false)}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">First Name</label>
          {editing ? (
            <input
              type="text"
              value={formData.first_name}
              onChange={(e) => setFormData(prev => ({ ...prev, first_name: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg"
            />
          ) : (
            <p className="text-gray-900">{profile?.first_name || '-'}</p>
          )}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
          {editing ? (
            <input
              type="text"
              value={formData.last_name}
              onChange={(e) => setFormData(prev => ({ ...prev, last_name: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg"
            />
          ) : (
            <p className="text-gray-900">{profile?.last_name || '-'}</p>
          )}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          {editing ? (
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg"
            />
          ) : (
            <p className="text-gray-900">{profile?.email}</p>
          )}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
          {editing ? (
            <select
              value={formData.timezone}
              onChange={(e) => setFormData(prev => ({ ...prev, timezone: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg"
            >
              <option value="UTC">UTC</option>
              <option value="America/New_York">Eastern Time</option>
              <option value="America/Chicago">Central Time</option>
              <option value="America/Denver">Mountain Time</option>
              <option value="America/Los_Angeles">Pacific Time</option>
            </select>
          ) : (
            <p className="text-gray-900">{profile?.timezone || 'UTC'}</p>
          )}
        </div>
      </div>

      <div className="pt-4 border-t">
        <p className="text-sm text-gray-500">
          Member since {new Date(profile?.created_at).toLocaleDateString()}
        </p>
      </div>
    </div>
  );
}

function SecurityTab({ profile, onUpdate, getAuthHeader }) {
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [show2FASetup, setShow2FASetup] = useState(false);
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [showPasswords, setShowPasswords] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setError('New passwords do not match');
      return;
    }

    if (passwordForm.new_password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setSaving(true);
    try {
      const res = await fetchApi('/api/auth/me/password', {
        method: 'PUT',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_password: passwordForm.current_password,
          new_password: passwordForm.new_password
        })
      });

      if (res.success) {
        setSuccess('Password changed successfully');
        setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
        setShowPasswordForm(false);
      } else {
        setError(res.error?.message || 'Failed to change password');
      }
    } catch (err) {
      setError(err.message || 'Failed to change password');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Password Section */}
      <div className="bg-white rounded-xl border p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold">Password</h3>
            <p className="text-sm text-gray-500">Change your account password</p>
          </div>
          {!showPasswordForm && (
            <button
              onClick={() => setShowPasswordForm(true)}
              className="px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg"
            >
              Change Password
            </button>
          )}
        </div>

        {showPasswordForm && (
          <form onSubmit={handleChangePassword} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Current Password</label>
              <div className="relative">
                <input
                  type={showPasswords.current ? 'text' : 'password'}
                  value={passwordForm.current_password}
                  onChange={(e) => setPasswordForm(prev => ({ ...prev, current_password: e.target.value }))}
                  className="w-full px-3 py-2 pr-10 border rounded-lg"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPasswords(prev => ({ ...prev, current: !prev.current }))}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                >
                  {showPasswords.current ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
              <div className="relative">
                <input
                  type={showPasswords.new ? 'text' : 'password'}
                  value={passwordForm.new_password}
                  onChange={(e) => setPasswordForm(prev => ({ ...prev, new_password: e.target.value }))}
                  className="w-full px-3 py-2 pr-10 border rounded-lg"
                  required
                  minLength={8}
                />
                <button
                  type="button"
                  onClick={() => setShowPasswords(prev => ({ ...prev, new: !prev.new }))}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                >
                  {showPasswords.new ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Confirm New Password</label>
              <input
                type="password"
                value={passwordForm.confirm_password}
                onChange={(e) => setPasswordForm(prev => ({ ...prev, confirm_password: e.target.value }))}
                className="w-full px-3 py-2 border rounded-lg"
                required
              />
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => { setShowPasswordForm(false); setError(''); }}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? 'Changing...' : 'Change Password'}
              </button>
            </div>
          </form>
        )}

        {success && (
          <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-sm text-green-600">{success}</p>
          </div>
        )}
      </div>

      {/* 2FA Section */}
      <div className="bg-white rounded-xl border p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={cn(
              "p-2 rounded-lg",
              profile?.two_factor_enabled ? "bg-green-100" : "bg-gray-100"
            )}>
              <Shield className={cn(
                "w-5 h-5",
                profile?.two_factor_enabled ? "text-green-600" : "text-gray-400"
              )} />
            </div>
            <div>
              <h3 className="text-lg font-semibold">Two-Factor Authentication</h3>
              <p className="text-sm text-gray-500">
                {profile?.two_factor_enabled 
                  ? 'Your account is protected with 2FA'
                  : 'Add an extra layer of security to your account'}
              </p>
            </div>
          </div>
          {!profile?.two_factor_enabled ? (
            <button
              onClick={() => setShow2FASetup(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Enable 2FA
            </button>
          ) : (
            <Disable2FAButton onDisabled={onUpdate} getAuthHeader={getAuthHeader} />
          )}
        </div>

        {show2FASetup && (
          <Setup2FA 
            onComplete={() => { setShow2FASetup(false); onUpdate(); }} 
            onCancel={() => setShow2FASetup(false)}
            getAuthHeader={getAuthHeader}
          />
        )}
      </div>
    </div>
  );
}

function Setup2FA({ onComplete, onCancel, getAuthHeader }) {
  const [step, setStep] = useState(1);
  const [setupData, setSetupData] = useState(null);
  const [verifyCode, setVerifyCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copiedSecret, setCopiedSecret] = useState(false);

  useEffect(() => {
    initSetup();
  }, []);

  const initSetup = async () => {
    setLoading(true);
    try {
      const res = await fetchApi('/api/auth/2fa/setup', {
        method: 'POST',
        headers: getAuthHeader()
      });

      if (res.success) {
        setSetupData(res.data);
      } else {
        setError(res.error?.message || 'Failed to initialize 2FA setup');
      }
    } catch (err) {
      setError(err.message || 'Failed to initialize 2FA setup');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    setError('');
    setLoading(true);

    try {
      const res = await fetchApi('/api/auth/2fa/verify', {
        method: 'POST',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: verifyCode })
      });

      if (res.success) {
        setStep(3);
      } else {
        setError(res.error?.message || 'Invalid verification code');
      }
    } catch (err) {
      setError(err.message || 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  const copySecret = () => {
    navigator.clipboard.writeText(setupData?.secret);
    setCopiedSecret(true);
    setTimeout(() => setCopiedSecret(false), 2000);
  };

  if (loading && !setupData) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="border-t pt-6 mt-4">
      {/* Step Indicator */}
      <div className="flex items-center gap-2 mb-6">
        {[1, 2, 3].map((s) => (
          <React.Fragment key={s}>
            <div className={cn(
              "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium",
              step >= s ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-500"
            )}>
              {step > s ? <Check className="w-4 h-4" /> : s}
            </div>
            {s < 3 && <div className={cn("flex-1 h-1 rounded", step > s ? "bg-blue-600" : "bg-gray-200")} />}
          </React.Fragment>
        ))}
      </div>

      {step === 1 && (
        <div className="space-y-4">
          <h4 className="font-medium">Step 1: Scan QR Code</h4>
          <p className="text-sm text-gray-600">
            Scan this QR code with your authenticator app (Google Authenticator, Microsoft Authenticator, etc.)
          </p>
          
          <div className="flex justify-center py-4">
            <div className="p-4 bg-white border-2 rounded-lg">
              {setupData?.provisioning_uri ? (
                <QRCodeSVG 
                  value={setupData.provisioning_uri} 
                  size={192}
                  level="M"
                  includeMargin={true}
                />
              ) : (
                <div className="w-48 h-48 bg-gray-100 flex items-center justify-center">
                  <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                </div>
              )}
            </div>
          </div>

          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-2">Can't scan? Enter this secret manually:</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 px-3 py-2 bg-white border rounded font-mono text-sm">
                {setupData?.secret}
              </code>
              <button
                onClick={copySecret}
                className="p-2 hover:bg-gray-200 rounded"
                title="Copy"
              >
                {copiedSecret ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="flex justify-end gap-3">
            <button onClick={onCancel} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">
              Cancel
            </button>
            <button
              onClick={() => setStep(2)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-4">
          <h4 className="font-medium">Step 2: Verify Setup</h4>
          <p className="text-sm text-gray-600">
            Enter the 6-digit code from your authenticator app to verify the setup.
          </p>

          <div>
            <input
              type="text"
              value={verifyCode}
              onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              className="w-full px-4 py-3 text-center text-2xl tracking-widest border rounded-lg"
              placeholder="000000"
              maxLength={6}
            />
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <div className="flex justify-end gap-3">
            <button onClick={() => setStep(1)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">
              Back
            </button>
            <button
              onClick={handleVerify}
              disabled={loading || verifyCode.length !== 6}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Verifying...' : 'Verify'}
            </button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-4">
          <div className="text-center py-4">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Check className="w-8 h-8 text-green-600" />
            </div>
            <h4 className="font-medium text-lg">2FA Enabled Successfully!</h4>
            <p className="text-sm text-gray-600 mt-1">
              Your account is now protected with two-factor authentication.
            </p>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-amber-800">Save your backup codes</p>
                <p className="text-sm text-amber-700 mt-1">
                  Store these codes in a safe place. You can use them to access your account if you lose your authenticator device.
                </p>
                <div className="grid grid-cols-2 gap-2 mt-3">
                  {setupData?.backup_codes?.map((code, idx) => (
                    <code key={idx} className="px-2 py-1 bg-white border rounded text-sm font-mono">
                      {code}
                    </code>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              onClick={onComplete}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Disable2FAButton({ onDisabled, getAuthHeader }) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleDisable = async () => {
    setError('');
    setLoading(true);

    try {
      const res = await fetchApi('/api/auth/2fa/disable', {
        method: 'POST',
        headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });

      if (res.success) {
        setShowConfirm(false);
        onDisabled();
      } else {
        setError(res.error?.message || 'Failed to disable 2FA');
      }
    } catch (err) {
      setError(err.message || 'Failed to disable 2FA');
    } finally {
      setLoading(false);
    }
  };

  if (!showConfirm) {
    return (
      <button
        onClick={() => setShowConfirm(true)}
        className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg"
      >
        Disable 2FA
      </button>
    );
  }

  return (
    <div className="border-t pt-4 mt-4 space-y-4">
      <p className="text-sm text-gray-600">
        Enter your password to confirm disabling two-factor authentication.
      </p>
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        className="w-full px-3 py-2 border rounded-lg"
        placeholder="Enter your password"
      />
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}
      <div className="flex gap-3">
        <button
          onClick={() => { setShowConfirm(false); setPassword(''); setError(''); }}
          className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
        >
          Cancel
        </button>
        <button
          onClick={handleDisable}
          disabled={loading || !password}
          className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
        >
          {loading ? 'Disabling...' : 'Disable 2FA'}
        </button>
      </div>
    </div>
  );
}

function SessionsTab({ sessions, onUpdate, getAuthHeader }) {
  const [revoking, setRevoking] = useState(false);

  const handleRevokeAll = async () => {
    if (!confirm('Revoke all other sessions? You will remain logged in on this device.')) return;
    
    setRevoking(true);
    try {
      await fetchApi('/api/auth/sessions/revoke-all', {
        method: 'POST',
        headers: getAuthHeader()
      });
      onUpdate();
    } catch (err) {
      console.error('Error revoking sessions:', err);
    } finally {
      setRevoking(false);
    }
  };

  return (
    <div className="bg-white rounded-xl border p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Active Sessions</h3>
          <p className="text-sm text-gray-500">Manage your active login sessions</p>
        </div>
        {sessions.length > 1 && (
          <button
            onClick={handleRevokeAll}
            disabled={revoking}
            className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg disabled:opacity-50"
          >
            {revoking ? 'Revoking...' : 'Revoke All Others'}
          </button>
        )}
      </div>

      <div className="space-y-3">
        {sessions.map((session, idx) => (
          <div key={session.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-3">
              <Monitor className="w-5 h-5 text-gray-400" />
              <div>
                <p className="font-medium text-sm">
                  {session.user_agent?.includes('Chrome') ? 'Chrome' :
                   session.user_agent?.includes('Firefox') ? 'Firefox' :
                   session.user_agent?.includes('Safari') ? 'Safari' : 'Unknown Browser'}
                  {idx === 0 && <span className="ml-2 text-xs text-green-600">(Current)</span>}
                </p>
                <p className="text-xs text-gray-500">
                  {session.ip_address} • Last active {new Date(session.last_activity_at).toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ProfilePage;
