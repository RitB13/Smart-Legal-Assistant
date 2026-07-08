import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Scale, Clock, CheckCircle, Loader2, AlertCircle, ArrowRight, History } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import Layout from '@/components/Layout';
import type { UserDisputeListItem, DisputeStatus } from '@/types/mediation';
import { CASE_TYPE_LABELS } from '@/types/mediation';

const STATUS_CONFIG: Record<DisputeStatus, { label: string; color: string }> = {
  pending_party_b:           { label: 'Waiting for other party', color: 'text-amber-600 bg-amber-50 border-amber-200 dark:bg-amber-900/20 dark:border-amber-700/40 dark:text-amber-400' },
  pending_statements:        { label: 'Awaiting statements',     color: 'text-blue-600 bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-700/40 dark:text-blue-400' },
  pending_party_b_statement: { label: 'Your turn to submit',     color: 'text-blue-600 bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-700/40 dark:text-blue-400' },
  pending_party_a_statement: { label: 'Your turn to submit',     color: 'text-blue-600 bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-700/40 dark:text-blue-400' },
  analysis_running:          { label: 'AI analysing…',           color: 'text-purple-600 bg-purple-50 border-purple-200 dark:bg-purple-900/20 dark:border-purple-700/40 dark:text-purple-400' },
  completed:                 { label: 'Completed',               color: 'text-green-600 bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-700/40 dark:text-green-400' },
  failed:                    { label: 'Failed',                  color: 'text-red-600 bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-700/40 dark:text-red-400' },
};

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat('en-IN', {
      day: 'numeric', month: 'short', year: 'numeric',
    }).format(new Date(iso));
  } catch {
    return iso.slice(0, 10);
  }
}

export default function MediationHistory() {
  const navigate = useNavigate();
  const [disputes, setDisputes] = useState<UserDisputeListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    apiFetch<{ disputes: UserDisputeListItem[]; total: number }>('/mediation/my/disputes')
      .then(d => setDisputes(d.disputes))
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load disputes.'))
      .finally(() => setLoading(false));
  }, []);

  function goToDispute(d: UserDisputeListItem) {
    if (d.status === 'completed') {
      navigate(`/mediation/${d.dispute_id}/result`);
    } else {
      navigate(`/mediation/${d.dispute_id}/room`);
    }
  }

  const completed = disputes.filter(d => d.status === 'completed').length;
  const active    = disputes.filter(d => d.status !== 'completed' && d.status !== 'failed').length;

  return (
    <Layout>
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50 dark:from-[#060d1a] dark:via-[#060d1a] dark:to-[#060d1a] -mt-16 pt-24 pb-12">
        <div className="max-w-3xl mx-auto px-4">

          {/* Header */}
          <div className="flex items-start justify-between gap-4 mb-6">
            <div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">My Disputes</h1>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                Your mediation history, newest first.
              </p>
            </div>
            <div className="flex items-center gap-2 text-primary flex-shrink-0 mt-1">
              <Scale className="h-5 w-5" />
              <History className="h-4 w-4" />
            </div>
          </div>

          {/* Stats */}
          {!loading && disputes.length > 0 && (
            <div className="grid grid-cols-3 gap-3 mb-6">
              {[
                { label: 'Total',     value: disputes.length },
                { label: 'Completed', value: completed },
                { label: 'Active',    value: active },
              ].map(s => (
                <div key={s.label} className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-center">
                  <div className="text-2xl font-bold text-slate-900 dark:text-white tabular-nums">{s.value}</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{s.label}</div>
                </div>
              ))}
            </div>
          )}

          {/* Content */}
          {loading ? (
            <div className="flex justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
            </div>
          ) : error ? (
            <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400 py-8 justify-center">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {error}
            </div>
          ) : disputes.length === 0 ? (
            <div className="text-center py-16 border border-dashed border-slate-200 dark:border-slate-700 rounded-2xl">
              <Scale className="h-8 w-8 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
              <p className="text-sm text-slate-500 dark:text-slate-400">No disputes yet.</p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                Start one from the{' '}
                <button
                  onClick={() => navigate('/mediation')}
                  className="text-primary underline underline-offset-2"
                >
                  Mediation page
                </button>.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {disputes.map(d => {
                const cfg = STATUS_CONFIG[d.status];
                return (
                  <button
                    key={d.dispute_id}
                    onClick={() => goToDispute(d)}
                    className="w-full text-left border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 rounded-xl px-5 py-4 hover:border-slate-300 dark:hover:border-slate-600 hover:shadow-sm transition-all flex items-center justify-between gap-4"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                          {CASE_TYPE_LABELS[d.case_type] || d.case_type}
                        </span>
                        <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full border ${cfg.color}`}>
                          {cfg.label}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-slate-400 dark:text-slate-500 flex-wrap">
                        <span className="capitalize">{d.role.replace('_', ' ')}</span>
                        <span>·</span>
                        <span className="font-mono">{d.invite_code}</span>
                        <span>·</span>
                        <span className="flex items-center gap-1">
                          {d.status === 'completed'
                            ? <CheckCircle className="h-3 w-3 text-green-500" />
                            : <Clock className="h-3 w-3" />}
                          {formatDate(d.created_at)}
                        </span>
                      </div>
                    </div>
                    <ArrowRight className="h-4 w-4 text-slate-300 dark:text-slate-600 flex-shrink-0" />
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
