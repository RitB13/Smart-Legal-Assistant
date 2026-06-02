import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Scale, Eye, EyeOff, ArrowRight, Loader2 } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/api';
import type { LoginResponse } from '@/types/auth';

type View = 'login' | 'forgot';

export default function Login() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string })?.from || '/';

  const [view, setView] = useState<View>('login');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [form, setForm] = useState({ email: '', password: '' });
  const [forgotEmail, setForgotEmail] = useState('');

  if (isAuthenticated) {
    navigate(from, { replace: true });
    return null;
  }

  function set(field: keyof typeof form, value: string) {
    setForm(f => ({ ...f, [field]: value }));
    setError('');
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!form.email || !form.password) { setError('Please fill in all fields.'); return; }
    setLoading(true); setError('');
    try {
      const data = await apiFetch<LoginResponse>('/auth/login', {
        method: 'POST',
        body: { email: form.email, password: form.password },
        skipAuth: true,
      });
      login(data.access_token, { user_id: data.user_id, email: data.email, name: data.name });
      navigate(from, { replace: true });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Login failed.';
      if (msg.includes('not verified')) {
        navigate('/verify-otp', { state: { email: form.email } });
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleForgot(e: React.FormEvent) {
    e.preventDefault();
    if (!forgotEmail) { setError('Please enter your email.'); return; }
    setLoading(true); setError(''); setSuccess('');
    try {
      await apiFetch('/auth/forgot-password', {
        method: 'POST',
        body: { email: forgotEmail },
        skipAuth: true,
      });
      setSuccess('If that email is registered, a reset code has been sent.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send reset email.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 mb-8 justify-center group">
          <Scale className="h-5 w-5 text-primary" />
          <span className="text-sm font-semibold text-slate-700 group-hover:text-primary transition-colors">
            Smart Legal Assistant
          </span>
        </Link>

        <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm">
          {view === 'login' ? (
            <>
              <h1 className="text-xl font-bold text-slate-900 mb-1">Welcome back</h1>
              <p className="text-sm text-slate-500 mb-6">Sign in to your account</p>

              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1.5">Email</label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={e => set('email', e.target.value)}
                    placeholder="you@example.com"
                    className="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-lg bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-slate-400"
                    autoComplete="email"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="block text-xs font-medium text-slate-700">Password</label>
                    <button
                      type="button"
                      onClick={() => { setView('forgot'); setError(''); setSuccess(''); }}
                      className="text-xs text-primary hover:underline"
                    >
                      Forgot password?
                    </button>
                  </div>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={form.password}
                      onChange={e => set('password', e.target.value)}
                      placeholder="••••••••"
                      className="w-full px-3 py-2.5 pr-10 text-sm border border-slate-200 rounded-lg bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-slate-400"
                      autoComplete="current-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(s => !s)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                {error && (
                  <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">{error}</p>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 bg-primary text-white text-sm font-medium py-2.5 rounded-lg hover:opacity-90 disabled:opacity-60 transition-opacity"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : (
                    <><span>Sign in</span><ArrowRight className="h-4 w-4" /></>
                  )}
                </button>
              </form>

              <p className="text-xs text-slate-500 text-center mt-5">
                No account?{' '}
                <Link to="/register" className="text-primary font-medium hover:underline">
                  Create one
                </Link>
              </p>
            </>
          ) : (
            <>
              <button
                onClick={() => { setView('login'); setError(''); setSuccess(''); }}
                className="text-xs text-slate-500 hover:text-slate-700 mb-4 flex items-center gap-1"
              >
                ← Back to sign in
              </button>
              <h1 className="text-xl font-bold text-slate-900 mb-1">Reset password</h1>
              <p className="text-sm text-slate-500 mb-6">We'll send a reset code to your email.</p>

              <form onSubmit={handleForgot} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1.5">Email</label>
                  <input
                    type="email"
                    value={forgotEmail}
                    onChange={e => { setForgotEmail(e.target.value); setError(''); setSuccess(''); }}
                    placeholder="you@example.com"
                    className="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-lg bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-slate-400"
                  />
                </div>

                {error && <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">{error}</p>}
                {success && <p className="text-xs text-green-700 bg-green-50 border border-green-100 rounded-lg px-3 py-2">{success}</p>}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 bg-primary text-white text-sm font-medium py-2.5 rounded-lg hover:opacity-90 disabled:opacity-60 transition-opacity"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Send reset code'}
                </button>
              </form>

              {success && (
                <p className="text-xs text-slate-500 text-center mt-4">
                  Have the code?{' '}
                  <Link
                    to="/verify-otp"
                    state={{ email: forgotEmail, mode: 'reset' }}
                    className="text-primary font-medium hover:underline"
                  >
                    Enter it here
                  </Link>
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
