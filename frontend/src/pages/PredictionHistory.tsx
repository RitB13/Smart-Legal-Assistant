import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Scale, CheckCircle2, XCircle, Loader2, RotateCcw,
  Calendar, MapPin, Trash2, ChevronRight, BarChart3,
} from 'lucide-react';
import Layout from '@/components/Layout';
import { apiFetch, ApiError } from '@/lib/api';

interface PredictionRecord {
  id: string;
  _id?: string;
  case_type: string;
  description: string;
  jurisdiction: string;
  predicted_verdict: string | null;
  confidence_score: number | null;
  legal_references: string[];
  analysis_details: Record<string, any>;
  created_at: string;
  updated_at: string;
}

function formatCaseType(raw: string): string {
  return raw
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat('en-IN', {
      day: 'numeric', month: 'short', year: 'numeric',
    }).format(new Date(iso));
  } catch {
    return iso.slice(0, 10);
  }
}

export default function PredictionHistory() {
  const [items, setItems]         = useState<PredictionRecord[]>([]);
  const [loading, setLoading]     = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError]         = useState('');
  const [hasMore, setHasMore]     = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const PAGE = 20;

  const fetchPage = useCallback(async (skip: number, append = false) => {
    if (append) setLoadingMore(true); else setLoading(true);
    setError('');
    try {
      const data = await apiFetch<PredictionRecord[]>(
        `/predictions?skip=${skip}&limit=${PAGE}`
      );
      setItems(prev => append ? [...prev, ...data] : data);
      setHasMore(data.length === PAGE);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setError('Please log in to view your prediction history.');
      } else {
        setError(e instanceof Error ? e.message : 'Failed to load predictions.');
      }
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => { fetchPage(0); }, [fetchPage]);

  async function handleDelete(record: PredictionRecord) {
    const id = record._id ?? record.id;
    if (!id) return;
    setDeletingId(id);
    try {
      await apiFetch(`/predictions/${id}`, { method: 'DELETE' });
      setItems(prev => prev.filter(r => (r._id ?? r.id) !== id));
    } catch {
      // silently ignore delete errors — don't disrupt the page
    } finally {
      setDeletingId(null);
    }
  }

  const accepted = items.filter(r => r.predicted_verdict === 'Accepted').length;
  const rejected = items.filter(r => r.predicted_verdict === 'Rejected').length;
  const avgConf  = items.filter(r => r.confidence_score != null).length
    ? (
        items
          .filter(r => r.confidence_score != null)
          .reduce((s, r) => s + r.confidence_score!, 0) /
        items.filter(r => r.confidence_score != null).length *
        100
      ).toFixed(0)
    : null;

  return (
    <Layout>
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50 -mt-16 pt-24 pb-12">
        <div className="max-w-3xl mx-auto px-4">

          {/* Header */}
          <div className="flex items-start justify-between gap-4 mb-6">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">My Predictions</h1>
              <p className="text-sm text-slate-500 mt-1">
                Your past case outcome analyses, most recent first.
              </p>
            </div>
            <Link
              to="/predict"
              className="flex items-center gap-1.5 px-4 py-2 bg-primary text-white text-sm font-medium rounded-xl hover:opacity-90 transition-opacity flex-shrink-0"
            >
              <Scale className="w-4 h-4" />
              New Analysis
            </Link>
          </div>

          {/* Stats strip */}
          {!loading && items.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              <div className="rounded-xl border border-slate-200 bg-white dark:bg-slate-800 dark:border-slate-700 px-4 py-3 flex items-center gap-3">
                <BarChart3 className="w-5 h-5 text-slate-400 flex-shrink-0" />
                <div>
                  <p className="text-xl font-bold text-slate-900 dark:text-white">{items.length}{hasMore ? '+' : ''}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Total</p>
                </div>
              </div>
              <div className="rounded-xl border border-green-100 dark:border-green-800/40 bg-green-50 dark:bg-green-900/15 px-4 py-3 flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
                <div>
                  <p className="text-xl font-bold text-green-800 dark:text-green-300">{accepted}</p>
                  <p className="text-xs text-green-600 dark:text-green-500">Accepted</p>
                </div>
              </div>
              <div className="rounded-xl border border-red-100 dark:border-red-800/40 bg-red-50 dark:bg-red-900/15 px-4 py-3 flex items-center gap-3">
                <XCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
                <div>
                  <p className="text-xl font-bold text-red-800 dark:text-red-300">{rejected}</p>
                  <p className="text-xs text-red-600 dark:text-red-500">Rejected</p>
                </div>
              </div>
              {avgConf !== null && (
                <div className="rounded-xl border border-blue-100 dark:border-blue-800/40 bg-blue-50 dark:bg-blue-900/15 px-4 py-3 flex items-center gap-3">
                  <BarChart3 className="w-5 h-5 text-blue-400 flex-shrink-0" />
                  <div>
                    <p className="text-xl font-bold text-blue-800 dark:text-blue-300">{avgConf}%</p>
                    <p className="text-xs text-blue-600 dark:text-blue-500">Avg. confidence</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Loading */}
          {loading && (
            <div className="flex items-center justify-center gap-2 py-20 text-slate-400">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="text-sm">Loading predictions…</span>
            </div>
          )}

          {/* Error */}
          {!loading && error && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-4 text-sm text-red-700 flex items-start gap-3">
              <XCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">{error}</p>
                {error.includes('log in') && (
                  <Link to="/login" className="underline mt-1 inline-block">Sign in →</Link>
                )}
              </div>
            </div>
          )}

          {/* Empty state */}
          {!loading && !error && items.length === 0 && (
            <div className="rounded-2xl border-2 border-dashed border-slate-200 bg-white py-16 px-8 text-center">
              <Scale className="w-10 h-10 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-600 font-medium mb-1">No predictions yet</p>
              <p className="text-sm text-slate-400 mb-5">
                Run your first case analysis to see it here.
              </p>
              <Link
                to="/predict"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary text-white text-sm font-medium rounded-xl hover:opacity-90 transition-opacity"
              >
                Analyse a case <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
          )}

          {/* Prediction cards */}
          {!loading && items.length > 0 && (
            <div className="space-y-3">
              {items.map(record => {
                const id          = record._id ?? record.id;
                const isAccepted  = record.predicted_verdict === 'Accepted';
                const isRejected  = record.predicted_verdict === 'Rejected';
                const confPct     = record.confidence_score != null
                  ? (record.confidence_score * 100).toFixed(0)
                  : null;
                const riskLevel   = record.analysis_details?.risk_level ?? '';
                const reliefLabel = record.analysis_details?.relief_sought;

                return (
                  <div
                    key={id}
                    className="rounded-xl border border-slate-200 bg-white p-4 hover:shadow-sm transition-shadow"
                  >
                    <div className="flex items-start gap-3">
                      {/* Verdict badge */}
                      <span className={`flex-shrink-0 mt-0.5 text-xs font-bold px-2.5 py-1 rounded-full ${
                        isAccepted ? 'bg-green-100 text-green-700'
                        : isRejected ? 'bg-red-100 text-red-700'
                        : 'bg-slate-100 text-slate-600'
                      }`}>
                        {record.predicted_verdict ?? 'Unknown'}
                      </span>

                      <div className="flex-1 min-w-0">
                        {/* Case type + relief */}
                        <p className="text-sm font-semibold text-slate-800 truncate">
                          {reliefLabel || formatCaseType(record.case_type)}
                        </p>

                        {/* Description preview */}
                        <p className="text-xs text-slate-500 mt-0.5 line-clamp-2 leading-relaxed">
                          {record.description}
                        </p>

                        {/* Meta row */}
                        <div className="flex flex-wrap items-center gap-3 mt-2">
                          {confPct && (
                            <span className={`text-xs font-medium ${
                              isAccepted ? 'text-green-600' : isRejected ? 'text-red-600' : 'text-slate-500'
                            }`}>
                              {confPct}% confidence
                            </span>
                          )}
                          {riskLevel && (
                            <span className={`text-xs capitalize ${
                              riskLevel === 'very_high' || riskLevel === 'high'
                                ? 'text-red-500'
                                : riskLevel === 'medium' ? 'text-amber-600' : 'text-green-600'
                            }`}>
                              {riskLevel.replace(/_/g, ' ')} risk
                            </span>
                          )}
                          {record.jurisdiction && (
                            <span className="flex items-center gap-1 text-xs text-slate-400">
                              <MapPin className="w-3 h-3" />
                              {record.jurisdiction}
                            </span>
                          )}
                          <span className="flex items-center gap-1 text-xs text-slate-400">
                            <Calendar className="w-3 h-3" />
                            {formatDate(record.created_at)}
                          </span>
                        </div>
                      </div>

                      {/* Delete button */}
                      <button
                        onClick={() => handleDelete(record)}
                        disabled={deletingId === id}
                        title="Delete prediction"
                        className="flex-shrink-0 p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-40"
                      >
                        {deletingId === id
                          ? <Loader2 className="w-4 h-4 animate-spin" />
                          : <Trash2 className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                );
              })}

              {/* Load more */}
              {hasMore && (
                <button
                  onClick={() => fetchPage(items.length, true)}
                  disabled={loadingMore}
                  className="w-full flex items-center justify-center gap-2 py-3 text-sm text-slate-500 hover:text-slate-700 border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors disabled:opacity-60"
                >
                  {loadingMore
                    ? <><Loader2 className="w-4 h-4 animate-spin" /> Loading…</>
                    : <><RotateCcw className="w-4 h-4" /> Load more</>}
                </button>
              )}
            </div>
          )}

          <p className="text-xs text-slate-300 text-center mt-8">
            Predictions are stored for your reference only and are not legal advice.
          </p>
        </div>
      </div>
    </Layout>
  );
}
