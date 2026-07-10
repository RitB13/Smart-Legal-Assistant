import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  CheckCircle2, XCircle, ArrowLeft, Loader2,
  MapPin, Calendar, BarChart3, Scale, AlertTriangle, FileText,
} from 'lucide-react';
import Layout from '@/components/Layout';
import { apiFetch } from '@/lib/api';

interface PredictionRecord {
  id: string;
  _id?: string;
  case_type: string;
  description: string;
  jurisdiction: string;
  predicted_verdict: string | null;
  confidence_score: number | null;
  legal_references: string[];
  impact_score: number | null;
  analysis_details: Record<string, any>;
  created_at: string;
  updated_at: string;
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat('en-IN', {
      day: 'numeric', month: 'long', year: 'numeric',
    }).format(new Date(iso));
  } catch {
    return iso.slice(0, 10);
  }
}

function formatCaseType(raw: string): string {
  return raw.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

export default function PredictionDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [record, setRecord] = useState<PredictionRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    apiFetch<PredictionRecord>(`/predictions/${id}`)
      .then(data => setRecord(data))
      .catch(err => setError(err instanceof Error ? err.message : 'Failed to load prediction.'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return (
    <Layout>
      <div className="flex justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
      </div>
    </Layout>
  );

  if (error || !record) return (
    <Layout>
      <div className="max-w-lg mx-auto px-4 py-24 text-center">
        <p className="text-sm text-slate-500 dark:text-slate-400">{error || 'Prediction not found.'}</p>
        <button onClick={() => navigate('/predictions')} className="mt-4 text-sm text-primary hover:underline">
          ← Back to My Predictions
        </button>
      </div>
    </Layout>
  );

  const isAccepted = record.predicted_verdict === 'Accepted';
  const isRejected = record.predicted_verdict === 'Rejected';
  const confPct = record.confidence_score != null
    ? Math.round(record.confidence_score * 100)
    : null;
  const riskLevel: string = record.analysis_details?.risk_level ?? '';
  const reliefLabel: string = record.analysis_details?.relief_sought ?? '';
  const role: string = record.analysis_details?.role ?? '';

  const riskColor = riskLevel === 'very_high' || riskLevel === 'high'
    ? 'text-red-600 dark:text-red-400'
    : riskLevel === 'medium'
    ? 'text-amber-600 dark:text-amber-400'
    : 'text-green-600 dark:text-green-400';

  return (
    <Layout>
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50 dark:from-[#060d1a] dark:via-[#060d1a] dark:to-[#060d1a] -mt-16 pt-24 pb-12">
        <div className="max-w-2xl mx-auto px-4">

          {/* Back */}
          <Link
            to="/predictions"
            className="flex items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 mb-6 transition-colors w-fit"
          >
            <ArrowLeft className="h-4 w-4" /> My Predictions
          </Link>

          {/* Header */}
          <div className="flex items-start justify-between gap-4 mb-6">
            <div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
                {reliefLabel || formatCaseType(record.case_type)}
              </h1>
              <div className="flex flex-wrap items-center gap-3 mt-2">
                {record.jurisdiction && (
                  <span className="flex items-center gap-1 text-xs text-slate-400 dark:text-slate-500">
                    <MapPin className="w-3 h-3" /> {record.jurisdiction}
                  </span>
                )}
                <span className="flex items-center gap-1 text-xs text-slate-400 dark:text-slate-500">
                  <Calendar className="w-3 h-3" /> {formatDate(record.created_at)}
                </span>
              </div>
            </div>
            <Link
              to="/predict"
              className="flex items-center gap-1.5 px-4 py-2 bg-primary text-white text-sm font-medium rounded-xl hover:opacity-90 transition-opacity flex-shrink-0"
            >
              <Scale className="w-4 h-4" /> New Analysis
            </Link>
          </div>

          <div className="space-y-4">

            {/* Verdict card */}
            <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
              <div className="flex items-center gap-3 mb-4">
                {isAccepted
                  ? <CheckCircle2 className="h-8 w-8 text-green-500 flex-shrink-0" />
                  : isRejected
                  ? <XCircle className="h-8 w-8 text-red-500 flex-shrink-0" />
                  : <AlertTriangle className="h-8 w-8 text-amber-500 flex-shrink-0" />
                }
                <div>
                  <p className={`text-2xl font-extrabold ${
                    isAccepted ? 'text-green-600 dark:text-green-400'
                    : isRejected ? 'text-red-600 dark:text-red-400'
                    : 'text-amber-600 dark:text-amber-400'
                  }`}>
                    {record.predicted_verdict ?? 'Unknown'}
                  </p>
                  {confPct !== null && (
                    <p className="text-sm text-slate-500 dark:text-slate-400">{confPct}% confidence</p>
                  )}
                </div>
              </div>

              {/* Confidence bar */}
              {confPct !== null && (
                <div className="h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className={`h-2 rounded-full transition-all ${
                      isAccepted ? 'bg-green-500' : isRejected ? 'bg-red-500' : 'bg-amber-500'
                    }`}
                    style={{ width: `${confPct}%` }}
                  />
                </div>
              )}
            </div>

            {/* Meta row: risk + role */}
            {(riskLevel || role) && (
              <div className="grid grid-cols-2 gap-3">
                {riskLevel && (
                  <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
                    <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-1">Risk Level</p>
                    <p className={`text-sm font-bold capitalize ${riskColor}`}>
                      {riskLevel.replace(/_/g, ' ')} Risk
                    </p>
                  </div>
                )}
                {role && (
                  <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
                    <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-1">Your Role</p>
                    <p className="text-sm font-bold text-slate-700 dark:text-slate-200 capitalize">{role}</p>
                  </div>
                )}
              </div>
            )}

            {/* Case description */}
            <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-2 mb-3">
                <BarChart3 className="h-4 w-4 text-slate-400" /> Case Description
              </h2>
              <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">{record.description}</p>
            </div>

            {/* Legal references */}
            {record.legal_references.length > 0 && (
              <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-5">
                <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-2 mb-3">
                  <FileText className="h-4 w-4 text-slate-400" /> Applicable Laws
                </h2>
                <ul className="space-y-1.5">
                  {record.legal_references.map((law, i) => (
                    <li key={i} className="text-xs text-slate-600 dark:text-slate-300 flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-primary/50 mt-1.5 flex-shrink-0" />
                      {law}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Run again */}
            <div className="text-center pt-2">
              <Link
                to="/predict"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary text-white text-sm font-medium rounded-xl hover:opacity-90 transition-opacity"
              >
                <Scale className="w-4 h-4" /> Run a new analysis
              </Link>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
