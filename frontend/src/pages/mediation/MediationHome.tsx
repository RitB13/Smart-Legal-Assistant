import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Users, ArrowRight, Loader2, Scale, AlertCircle } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import Layout from '@/components/Layout';

export default function MediationHome() {
  const navigate = useNavigate();
  const [joinCode, setJoinCode] = useState('');
  const [joining, setJoining] = useState(false);
  const [joinError, setJoinError] = useState('');

  async function handleJoin(e: React.FormEvent) {
    e.preventDefault();
    if (!joinCode.trim()) return;
    setJoining(true); setJoinError('');
    try {
      const data = await apiFetch<{ dispute_id: string }>('/mediation/join', {
        method: 'POST',
        body: { invite_code: joinCode.trim().toUpperCase() },
      });
      navigate(`/mediation/${data.dispute_id}/room`);
    } catch (err) {
      setJoinError(err instanceof Error ? err.message : 'Invalid or expired invite code.');
    } finally {
      setJoining(false);
    }
  }

  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 pb-12 pt-6">
        {/* Header */}
        <div className="mb-10">
          <div className="flex items-center gap-2 text-primary mb-3">
            <Scale className="h-5 w-5" />
            <span className="text-sm font-medium">AI Mediation</span>
          </div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">Resolve disputes fairly</h1>
          <p className="text-slate-500 dark:text-slate-400 max-w-xl">
            Both parties submit their account privately. The AI reads both sides, checks for language imbalance, and proposes a settlement backed by real Indian court data.
          </p>
        </div>

        {/* Action cards */}
        <div className="grid sm:grid-cols-2 gap-4 mb-10">
          <Link
            to="/mediation/create"
            className="group border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 rounded-xl p-6 hover:border-primary/40 hover:shadow-sm transition-all"
          >
            <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center mb-4 group-hover:bg-primary/15 transition-colors">
              <Plus className="h-5 w-5 text-primary" />
            </div>
            <h2 className="font-semibold text-slate-900 dark:text-slate-100 mb-1">Start a new dispute</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">You describe the issue. Get an invite code to share with the other party.</p>
            <span className="text-sm text-primary font-medium flex items-center gap-1 group-hover:gap-2 transition-all">
              Get started <ArrowRight className="h-4 w-4" />
            </span>
          </Link>

          <div className="border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 rounded-xl p-6">
            <div className="w-10 h-10 bg-slate-100 dark:bg-slate-700 rounded-lg flex items-center justify-center mb-4">
              <Users className="h-5 w-5 text-slate-600 dark:text-slate-400" />
            </div>
            <h2 className="font-semibold text-slate-900 dark:text-slate-100 mb-1">Join with invite code</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">The other party shared a code with you.</p>
            <form onSubmit={handleJoin} className="flex gap-2">
              <input
                value={joinCode}
                onChange={e => { setJoinCode(e.target.value.toUpperCase()); setJoinError(''); }}
                placeholder="XXXXXXXX"
                maxLength={8}
                className="flex-1 px-3 py-2 text-sm font-mono border border-slate-200 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary placeholder:text-slate-400 uppercase bg-white dark:bg-slate-700/60 dark:text-slate-100"
              />
              <button
                type="submit"
                disabled={joining || joinCode.length < 6}
                className="px-4 py-2 bg-primary text-white text-sm font-medium rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center gap-1"
              >
                {joining ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
              </button>
            </form>
            {joinError && (
              <p className="text-xs text-red-600 mt-2 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />{joinError}
              </p>
            )}
          </div>
        </div>

        {/* How it works */}
        <div className="bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-4">How it works</h3>
          <div className="grid sm:grid-cols-4 gap-4">
            {[
              { n: '1', label: 'Create', desc: 'Party A describes the dispute and shares an invite code' },
              { n: '2', label: 'Join',   desc: 'Party B joins and both submit their version privately' },
              { n: '3', label: 'Analyse',desc: 'The AI reads both accounts and checks for language advantage' },
              { n: '4', label: 'Resolve',desc: 'Both parties receive a neutral settlement proposal' },
            ].map(s => (
              <div key={s.n} className="text-center">
                <div className="w-7 h-7 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center mx-auto mb-2">{s.n}</div>
                <div className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">{s.label}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{s.desc}</div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </Layout>
  );
}
