import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Users, ArrowRight, Clock, CheckCircle, Loader2, Scale, AlertCircle } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/api';
import Layout from '@/components/Layout';
import type { UserDisputeListItem, DisputeStatus } from '@/types/mediation';
import { CASE_TYPE_LABELS } from '@/types/mediation';

const STATUS_CONFIG: Record<DisputeStatus, { label: string; color: string }> = {
  pending_party_b:         { label: 'Waiting for other party', color: 'text-amber-600 bg-amber-50 border-amber-200' },
  pending_statements:      { label: 'Awaiting statements',     color: 'text-blue-600 bg-blue-50 border-blue-200' },
  pending_party_b_statement: { label: 'Your turn to submit',   color: 'text-blue-600 bg-blue-50 border-blue-200' },
  pending_party_a_statement: { label: 'Your turn to submit',   color: 'text-blue-600 bg-blue-50 border-blue-200' },
  analysis_running:        { label: 'AI analysing…',           color: 'text-purple-600 bg-purple-50 border-purple-200' },
  completed:               { label: 'Completed',               color: 'text-green-600 bg-green-50 border-green-200' },
  failed:                  { label: 'Failed',                  color: 'text-red-600 bg-red-50 border-red-200' },
};

export default function MediationHome() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [joinCode, setJoinCode] = useState('');
  const [disputes, setDisputes] = useState<UserDisputeListItem[]>([]);
  const [loadingDisputes, setLoadingDisputes] = useState(true);
  const [joining, setJoining] = useState(false);
  const [joinError, setJoinError] = useState('');

  useEffect(() => {
    apiFetch<{ disputes: UserDisputeListItem[]; total: number }>('/mediation/my/disputes')
      .then(d => setDisputes(d.disputes))
      .catch(() => {})
      .finally(() => setLoadingDisputes(false));
  }, []);

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

  function goToDispute(d: UserDisputeListItem) {
    if (d.status === 'completed') {
      navigate(`/mediation/${d.dispute_id}/result`);
    } else {
      navigate(`/mediation/${d.dispute_id}/room`);
    }
  }

  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="mb-10">
          <div className="flex items-center gap-2 text-primary mb-3">
            <Scale className="h-5 w-5" />
            <span className="text-sm font-medium">AI Mediation</span>
          </div>
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Resolve disputes fairly</h1>
          <p className="text-slate-500 max-w-xl">
            Both parties submit their perspective privately. Our AI analyses both sides, detects language bias, and proposes a fair settlement backed by real Indian court data.
          </p>
        </div>

        {/* Action cards */}
        <div className="grid sm:grid-cols-2 gap-4 mb-10">
          <Link
            to="/mediation/create"
            className="group border border-slate-200 bg-white rounded-xl p-6 hover:border-primary/40 hover:shadow-sm transition-all"
          >
            <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center mb-4 group-hover:bg-primary/15 transition-colors">
              <Plus className="h-5 w-5 text-primary" />
            </div>
            <h2 className="font-semibold text-slate-900 mb-1">Start a new dispute</h2>
            <p className="text-sm text-slate-500 mb-4">You describe the issue. Get an invite code to share with the other party.</p>
            <span className="text-sm text-primary font-medium flex items-center gap-1 group-hover:gap-2 transition-all">
              Get started <ArrowRight className="h-4 w-4" />
            </span>
          </Link>

          <div className="border border-slate-200 bg-white rounded-xl p-6">
            <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center mb-4">
              <Users className="h-5 w-5 text-slate-600" />
            </div>
            <h2 className="font-semibold text-slate-900 mb-1">Join with invite code</h2>
            <p className="text-sm text-slate-500 mb-4">The other party shared a code with you.</p>
            <form onSubmit={handleJoin} className="flex gap-2">
              <input
                value={joinCode}
                onChange={e => { setJoinCode(e.target.value.toUpperCase()); setJoinError(''); }}
                placeholder="XXXXXXXX"
                maxLength={8}
                className="flex-1 px-3 py-2 text-sm font-mono border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary placeholder:text-slate-400 uppercase"
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
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 mb-10">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">How it works</h3>
          <div className="grid sm:grid-cols-4 gap-4">
            {[
              { n: '1', label: 'Create', desc: 'Party A describes the dispute and shares an invite code' },
              { n: '2', label: 'Join',   desc: 'Party B joins and both submit their version privately' },
              { n: '3', label: 'Analyse',desc: 'AI analyses both sides with fairness correction' },
              { n: '4', label: 'Resolve',desc: 'Both parties receive a neutral settlement proposal' },
            ].map(s => (
              <div key={s.n} className="text-center">
                <div className="w-7 h-7 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center mx-auto mb-2">{s.n}</div>
                <div className="text-xs font-semibold text-slate-700 mb-1">{s.label}</div>
                <div className="text-xs text-slate-500 leading-relaxed">{s.desc}</div>
              </div>
            ))}
          </div>
        </div>

        {/* My disputes */}
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">
            {user?.name?.split(' ')[0]}'s disputes
          </h3>

          {loadingDisputes ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
            </div>
          ) : disputes.length === 0 ? (
            <div className="text-center py-8 border border-dashed border-slate-200 rounded-xl">
              <p className="text-sm text-slate-400">No disputes yet. Start one above.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {disputes.map(d => {
                const cfg = STATUS_CONFIG[d.status];
                return (
                  <button
                    key={d.dispute_id}
                    onClick={() => goToDispute(d)}
                    className="w-full text-left border border-slate-200 bg-white rounded-xl px-5 py-4 hover:border-slate-300 hover:shadow-sm transition-all flex items-center justify-between gap-4"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-slate-900 truncate">
                          {CASE_TYPE_LABELS[d.case_type] || d.case_type}
                        </span>
                        <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full border ${cfg.color}`}>
                          {cfg.label}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-slate-400">
                        <span className="capitalize">{d.role.replace('_', ' ')}</span>
                        <span>·</span>
                        <span className="font-mono">{d.invite_code}</span>
                        <span>·</span>
                        <span className="flex items-center gap-1">
                          {d.status === 'completed'
                            ? <CheckCircle className="h-3 w-3 text-green-500" />
                            : <Clock className="h-3 w-3" />}
                          {new Date(d.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                        </span>
                      </div>
                    </div>
                    <ArrowRight className="h-4 w-4 text-slate-300 flex-shrink-0" />
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
