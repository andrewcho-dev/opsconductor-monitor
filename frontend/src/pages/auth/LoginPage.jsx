import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Eye, EyeOff, Lock, User, Shield, Loader2, Building2 } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { fetchApi, cn } from '../../lib/utils';

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, verify2FA, error: authError } = useAuth();
  
  const [step, setStep] = useState('credentials'); // 'credentials' | '2fa'
  const [authMethod, setAuthMethod] = useState('local'); // 'local' | enterprise config id
  const [enterpriseConfigs, setEnterpriseConfigs] = useState([]);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [twoFactorCode, setTwoFactorCode] = useState('');
  const [twoFactorUserId, setTwoFactorUserId] = useState(null);
  const [twoFactorMethod, setTwoFactorMethod] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const from = location.state?.from?.pathname || '/';

  // Load enterprise auth configs on mount
  useEffect(() => {
    loadEnterpriseConfigs();
  }, []);

  const loadEnterpriseConfigs = async () => {
    try {
      const res = await fetchApi('/api/auth/enterprise-configs');
      if (res.success) {
        setEnterpriseConfigs(res.data.configs || []);
      }
    } catch (err) {
      console.error('Failed to load enterprise configs:', err);
    }
  };

  const handleCredentialsSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      let result;
      
      if (authMethod === 'local') {
        // Local authentication
        result = await login(username, password);
      } else {
        // Enterprise authentication
        const res = await fetchApi('/api/auth/login/enterprise', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username,
            password,
            config_id: parseInt(authMethod)
          })
        });
        
        if (res.success) {
          if (res.data.requires_2fa) {
            result = { success: true, requires_2fa: true, user_id: res.data.user_id, two_factor_method: res.data.two_factor_method };
          } else {
            // Store tokens and user
            localStorage.setItem('opsconductor_session_token', res.data.session_token);
            localStorage.setItem('opsconductor_refresh_token', res.data.refresh_token);
            localStorage.setItem('opsconductor_user', JSON.stringify(res.data.user));
            result = { success: true };
            // Force page reload to pick up new auth state
            window.location.href = from;
            return;
          }
        } else {
          result = { success: false, error: res.error?.message || 'Login failed' };
        }
      }
      
      if (result.success) {
        if (result.requires_2fa) {
          setTwoFactorUserId(result.user_id);
          setTwoFactorMethod(result.two_factor_method);
          setStep('2fa');
        } else {
          navigate(from, { replace: true });
        }
      } else {
        setError(result.error || 'Login failed');
      }
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handle2FASubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await verify2FA(twoFactorUserId, twoFactorCode);
      
      if (result.success) {
        navigate(from, { replace: true });
      } else {
        setError(result.error || 'Verification failed');
      }
    } catch (err) {
      setError(err.message || 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo/Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl mb-4">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">OpsConductor</h1>
          <p className="text-slate-400 mt-1">Network Automation Platform</p>
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          {step === 'credentials' ? (
            <>
              <h2 className="text-xl font-semibold text-gray-900 mb-6">Sign in to your account</h2>
              
              <form onSubmit={handleCredentialsSubmit} className="space-y-5">
                {/* Auth Method Selector - only show if enterprise configs exist */}
                {enterpriseConfigs.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Sign in with
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => setAuthMethod('local')}
                        className={cn(
                          "flex items-center justify-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium transition-colors",
                          authMethod === 'local'
                            ? "border-blue-600 bg-blue-50 text-blue-700"
                            : "border-gray-300 text-gray-600 hover:bg-gray-50"
                        )}
                      >
                        <User className="w-4 h-4" />
                        Local Account
                      </button>
                      {enterpriseConfigs.map((config) => (
                        <button
                          key={config.id}
                          type="button"
                          onClick={() => setAuthMethod(String(config.id))}
                          className={cn(
                            "flex items-center justify-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium transition-colors",
                            authMethod === String(config.id)
                              ? "border-blue-600 bg-blue-50 text-blue-700"
                              : "border-gray-300 text-gray-600 hover:bg-gray-50"
                          )}
                        >
                          <Building2 className="w-4 h-4" />
                          {config.name}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Username */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Username or Email
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                      placeholder="Enter your username"
                      required
                      autoFocus
                      autoComplete="username"
                    />
                  </div>
                </div>

                {/* Password */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full pl-10 pr-12 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                      placeholder="Enter your password"
                      required
                      autoComplete="current-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                </div>

                {/* Error Message */}
                {(error || authError) && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-600">{error || authError}</p>
                  </div>
                )}

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Signing in...
                    </>
                  ) : (
                    'Sign in'
                  )}
                </button>
              </form>
            </>
          ) : (
            <>
              <div className="text-center mb-6">
                <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-100 rounded-full mb-3">
                  <Shield className="w-6 h-6 text-blue-600" />
                </div>
                <h2 className="text-xl font-semibold text-gray-900">Two-Factor Authentication</h2>
                <p className="text-gray-500 text-sm mt-1">
                  {twoFactorMethod === 'totp' 
                    ? 'Enter the code from your authenticator app'
                    : 'Enter the verification code'}
                </p>
              </div>

              <form onSubmit={handle2FASubmit} className="space-y-5">
                {/* 2FA Code */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Verification Code
                  </label>
                  <input
                    type="text"
                    value={twoFactorCode}
                    onChange={(e) => setTwoFactorCode(e.target.value.replace(/\D/g, '').slice(0, 8))}
                    className="w-full px-4 py-3 text-center text-2xl tracking-widest border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    placeholder="000000"
                    required
                    autoFocus
                    autoComplete="one-time-code"
                  />
                  <p className="text-xs text-gray-500 mt-2 text-center">
                    You can also use a backup code
                  </p>
                </div>

                {/* Error Message */}
                {error && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-600">{error}</p>
                  </div>
                )}

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={loading || twoFactorCode.length < 6}
                  className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    'Verify'
                  )}
                </button>

                {/* Back Button */}
                <button
                  type="button"
                  onClick={() => {
                    setStep('credentials');
                    setTwoFactorCode('');
                    setError('');
                  }}
                  className="w-full py-2 text-gray-600 hover:text-gray-800 text-sm"
                >
                  ← Back to login
                </button>
              </form>
            </>
          )}
        </div>

        {/* Footer */}
        <p className="text-center text-slate-500 text-sm mt-6">
          © {new Date().getFullYear()} OpsConductor. All rights reserved.
        </p>
      </div>
    </div>
  );
}

export default LoginPage;
