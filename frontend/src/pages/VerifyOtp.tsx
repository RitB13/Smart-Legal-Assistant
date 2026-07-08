import { useState, useRef, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Scale, Loader2, RefreshCw, ArrowRight } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/api';
import type { LoginResponse } from '@/types/auth';

type Mode = 'verify' | 'reset';

export default function VerifyOtp() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as { email?: string; mode?: Mode } | null;

  const email = state?.email || '';
  const mode: Mode = state?.mode || 'verify';

  const [digits, setDigits] = useState(['', '', '', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState('');
  const [resent, setResent] = useState(false);

  const [step, setStep] = useState<'otp' | 'newpass'>('otp');
  const [newPassword, setNewPassword] = useState('');
  const [verifiedOtp, setVerifiedOtp] = useState('');

  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    if (!email) navigate('/login', { replace: true });
    inputRefs.current[0]?.focus();
  }, [email, navigate]);

  const otp = digits.join('');

  function handleDigitChange(idx: number, val: string) {
    const char = val.replace(/\D/g, '').slice(-1);
    const next = [...digits];
    next[idx] = char;
    setDigits(next);
    setError('');
    if (char && idx < 5) inputRefs.current[idx + 1]?.focus();
  }

  function handleKeyDown(idx: number, e: React.KeyboardEvent) {
    if (e.key === 'Backspace' && !digits[idx] && idx > 0) {
      inputRefs.current[idx - 1]?.focus();
    }
  }

  function handlePaste(e: React.ClipboardEvent) {
    const text = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (text.length === 6) {
      setDigits(text.split(''));
      inputRefs.current[5]?.focus();
    }
    e.preventDefault();
  }

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault();
    if (otp.length < 6) { setError('Please enter the full 6-digit code.'); return; }
    setLoading(true); setError('');

    try {
      if (mode === 'verify') {
        const data = await apiFetch<LoginResponse>('/auth/verify-otp', {
          method: 'POST',
          body: { email, otp_code: otp },
          skipAuth: true,
        });
        login(data.access_token, { user_id: data.user_id, email: data.email, name: data.name });
        navigate('/', { replace: true });
      } else {
        await apiFetch('/auth/verify-otp', {
          method: 'POST',
          body: { email, otp_code: otp },
          skipAuth: true,
        }).catch(() => {});
        setVerifiedOtp(otp);
        setStep('newpass');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid code. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  async function handleReset(e: React.FormEvent) {
    e.preventDefault();
    if (newPassword.length < 8) { setError('Password must be at least 8 characters.'); return; }
    setLoading(true); setError('');
    try {
      await apiFetch('/auth/reset-password', {
        method: 'POST',
        body: { email, otp_code: verifiedOtp || otp, new_password: newPassword },
        skipAuth: true,
      });
      navigate('/login', { state: { message: 'Password updated. Please sign in.' } });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset password.');
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    setResending(true); setError(''); setResent(false);
    try {
      const endpoint = mode === 'verify' ? '/auth/resend-otp' : '/auth/forgot-password';
      await apiFetch(endpoint, {
        method: 'POST',
        body: { email },
        skipAuth: true,
      });
      setResent(true);
      setDigits(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resend. Try again.');
    } finally {
      setResending(false);
    }
  }

  if (!email) return null;

  const inputCls = "w-full px-3 py-2.5 text-sm border border-slate-200 dark:border-slate-600 rounded-lg bg-slate-50 dark:bg-slate-700/60 text-slate-900 dark:text-slate-100 focus:bg-white dark:focus:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-slate-400 dark:placeholder:text-slate-500";

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <Link to="/" className="flex items-center gap-2 mb-8 justify-center group">
          <Scale className="h-5 w-5 text-primary" />
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-200 group-hover:text-primary transition-colors">
            Smart Legal Assistant
          </span>
        </Link>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-8 shadow-sm">
          {step === 'otp' ? (
            <>
              <h1 className="text-xl font-bold text-slate-900 dark:text-white mb-1">
                {mode === 'verify' ? 'Verify your email' : 'Enter reset code'}
              </h1>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
                We sent a 6-digit code to{' '}
                <span className="font-medium text-slate-700 dark:text-slate-200">{email}</span>
              </p>

              <form onSubmit={handleVerify}>
                <div className="flex gap-2 justify-between mb-4" onPaste={handlePaste}>
                  {digits.map((d, i) => (
                    <input
                      key={i}
                      ref={el => { inputRefs.current[i] = el; }}
                      type="text"
                      inputMode="numeric"
                      maxLength={1}
                      value={d}
                      onChange={e => handleDigitChange(i, e.target.value)}
                      onKeyDown={e => handleKeyDown(i, e)}
                      className="w-11 h-12 text-center text-lg font-semibold border border-slate-200 dark:border-slate-600 rounded-lg bg-slate-50 dark:bg-slate-700/60 text-slate-900 dark:text-slate-100 focus:bg-white dark:focus:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                    />
                  ))}
                </div>

                {error && (
                  <p className="text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800/40 rounded-lg px-3 py-2 mb-4">{error}</p>
                )}
                {resent && (
                  <p className="text-xs text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/20 border border-green-100 dark:border-green-800/40 rounded-lg px-3 py-2 mb-4">
                    New code sent — check your inbox.
                  </p>
                )}

                <button
                  type="submit"
                  disabled={loading || otp.length < 6}
                  className="w-full flex items-center justify-center gap-2 bg-primary text-white text-sm font-medium py-2.5 rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : (
                    <><span>Verify code</span><ArrowRight className="h-4 w-4" /></>
                  )}
                </button>
              </form>

              <div className="flex items-center justify-center mt-4 gap-1">
                <span className="text-xs text-slate-500 dark:text-slate-400">Didn't receive it?</span>
                <button
                  onClick={handleResend}
                  disabled={resending}
                  className="text-xs text-primary font-medium hover:underline flex items-center gap-1 disabled:opacity-60"
                >
                  {resending && <RefreshCw className="h-3 w-3 animate-spin" />}
                  Resend code
                </button>
              </div>
            </>
          ) : (
            <>
              <h1 className="text-xl font-bold text-slate-900 dark:text-white mb-1">Set new password</h1>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">Choose a strong password for your account.</p>

              <form onSubmit={handleReset} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5">New password</label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={e => { setNewPassword(e.target.value); setError(''); }}
                    placeholder="Min. 8 characters"
                    className={inputCls}
                    autoFocus
                  />
                </div>

                {error && (
                  <p className="text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800/40 rounded-lg px-3 py-2">{error}</p>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 bg-primary text-white text-sm font-medium py-2.5 rounded-lg hover:opacity-90 disabled:opacity-60 transition-opacity"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Update password'}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
