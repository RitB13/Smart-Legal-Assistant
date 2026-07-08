import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Scale, Eye, EyeOff, ArrowRight, Loader2 } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import type { RegisterResponse } from '@/types/auth';

export default function Register() {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    preferred_language: 'en',
    jurisdiction: 'india',
  });

  function set(field: keyof typeof form, value: string) {
    setForm(f => ({ ...f, [field]: value }));
    setError('');
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim() || !form.email || !form.password) {
      setError('Please fill in all required fields.'); return;
    }
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters.'); return;
    }

    setLoading(true); setError('');
    try {
      const data = await apiFetch<RegisterResponse>('/auth/register', {
        method: 'POST',
        body: form,
        skipAuth: true,
      });
      navigate('/verify-otp', { state: { email: data.email, mode: 'verify' } });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  const pwStrength = form.password.length === 0 ? null
    : form.password.length < 8 ? 'weak'
    : form.password.length < 12 ? 'fair'
    : 'strong';

  const inputCls = "w-full px-3 py-2.5 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-slate-50 dark:bg-slate-700/60 text-slate-900 dark:text-slate-100 focus:bg-white dark:focus:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-slate-400 dark:placeholder:text-slate-500";

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <Link to="/" className="flex items-center gap-2 mb-8 justify-center group">
          <Scale className="h-5 w-5 text-primary" />
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-200 group-hover:text-primary transition-colors">
            Smart Legal Assistant
          </span>
        </Link>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-8 shadow-sm">
          <h1 className="text-xl font-bold text-slate-900 dark:text-white mb-1">Create an account</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">Free to get started. No credit card needed.</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5">Full name</label>
              <input
                type="text"
                value={form.name}
                onChange={e => set('name', e.target.value)}
                placeholder="Rahul Sharma"
                className={inputCls}
                autoComplete="name"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5">Email</label>
              <input
                type="email"
                value={form.email}
                onChange={e => set('email', e.target.value)}
                placeholder="you@example.com"
                className={inputCls}
                autoComplete="email"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={form.password}
                  onChange={e => set('password', e.target.value)}
                  placeholder="Min. 8 characters"
                  className={inputCls + ' pr-10'}
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(s => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>

              {/* Password strength indicator */}
              {pwStrength && (
                <div className="mt-2 space-y-1">
                  <div className="flex gap-1">
                    {(['weak', 'fair', 'strong'] as const).map((level, i) => {
                      const reached = pwStrength === 'strong' ? true : pwStrength === 'fair' ? i < 2 : i < 1;
                      return (
                        <div key={level} className={`flex-1 h-1 rounded-full transition-colors ${
                          reached
                            ? level === 'weak' ? 'bg-red-400' : level === 'fair' ? 'bg-amber-400' : 'bg-green-500'
                            : 'bg-slate-200 dark:bg-slate-600'
                        }`} />
                      );
                    })}
                  </div>
                  <p className={`text-[10px] font-medium ${
                    pwStrength === 'weak' ? 'text-red-500' : pwStrength === 'fair' ? 'text-amber-500' : 'text-green-600 dark:text-green-400'
                  }`}>
                    {pwStrength === 'weak' ? 'Weak — at least 8 characters needed' : pwStrength === 'fair' ? 'Fair — try adding numbers or symbols' : 'Strong password'}
                  </p>
                </div>
              )}
            </div>

            {error && (
              <p className="text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800/40 rounded-lg px-3 py-2">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-primary text-white text-sm font-medium py-2.5 rounded-lg hover:opacity-90 disabled:opacity-60 transition-opacity"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : (
                <><span>Create account</span><ArrowRight className="h-4 w-4" /></>
              )}
            </button>
          </form>

          <p className="text-xs text-slate-500 dark:text-slate-400 text-center mt-5">
            Already have an account?{' '}
            <Link to="/login" className="text-primary font-medium hover:underline">Sign in</Link>
          </p>
        </div>

        <p className="text-xs text-slate-400 dark:text-slate-500 text-center mt-4 px-4">
          By creating an account, you agree to our Terms of Service. This platform provides legal information, not legal advice.
        </p>
      </div>
    </div>
  );
}
