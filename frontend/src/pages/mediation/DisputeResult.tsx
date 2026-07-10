import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  CheckCircle, XCircle, Scale, AlertTriangle, FileText,
  Star, ChevronDown, ChevronUp, ArrowLeft, Loader2, Library, BarChart2,
} from 'lucide-react';
import { apiFetch } from '@/lib/api';
import Layout from '@/components/Layout';
import type { DisputeResultResponse, MediationReport, ConflictPoint, SimilarPrecedent, StatementStructure } from '@/types/mediation';

export default function DisputeResult() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [report, setReport] = useState<MediationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [showFullFairness, setShowFullFairness] = useState(false);
  const [expandedPrecedents, setExpandedPrecedents] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!id) return;
    apiFetch<DisputeResultResponse>(`/mediation/${id}/result`)
      .then(data => {
        if (data.status !== 'completed' || !data.report) {
          navigate(`/mediation/${id}/room`, { replace: true });
        } else {
          setReport(data.report);
        }
      })
      .catch(err => setError(err instanceof Error ? err.message : 'Failed to load report.'))
      .finally(() => setLoading(false));
  }, [id, navigate]);

  async function submitFeedback(stars: number) {
    setRating(stars);
    try {
      await apiFetch(`/mediation/${id}/feedback`, {
        method: 'POST',
        body: { rating: stars, accepted_settlement: stars >= 4 },
      });
      setFeedbackSent(true);
    } catch { /* silently ignore */ }
  }

  if (loading) return (
    <Layout>
      <div className="flex justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
      </div>
    </Layout>
  );

  if (error || !report) return (
    <Layout>
      <div className="max-w-lg mx-auto px-4 py-24 text-center">
        <p className="text-sm text-slate-500">{error || 'Report not available.'}</p>
        <button onClick={() => navigate('/mediation')} className="mt-4 text-sm text-primary hover:underline">
          Back to Mediation
        </button>
      </div>
    </Layout>
  );

  const { settlement_range: sr, fairness_audit: fa, points_of_agreement: poa, points_of_conflict: poc } = report;
  const hasRange = sr.low != null && sr.high != null;
  const rangeSpan = hasRange ? sr.high! - sr.low! : 0;
  const medianPct = hasRange && rangeSpan > 0 ? ((sr.median! - sr.low!) / rangeSpan) * 100 : 50;

  return (
    <Layout>
      <div className="max-w-2xl mx-auto px-4 py-10">
        {/* Back */}
        <button onClick={() => navigate('/mediation')} className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-6 transition-colors">
          <ArrowLeft className="h-4 w-4" /> All disputes
        </button>

        {/* Title */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle className="h-5 w-5 text-green-500" />
              <span className="text-sm font-medium text-green-700">Mediation complete</span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Settlement Report</h1>
            <p className="text-xs text-slate-400 mt-1 font-mono">{id?.slice(0, 8)}</p>
          </div>
          <span className="text-[10px] text-slate-400 dark:text-slate-500 bg-slate-100 dark:bg-slate-700 rounded px-2 py-1 font-mono">
            {report.model_version}
          </span>
        </div>

        <div className="space-y-4">
          {/* Proposed settlement — hero card */}
          <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-3">
              <Scale className="h-4 w-4 text-primary" />
              <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Proposed settlement</h2>
            </div>
            <p className="text-base text-slate-900 dark:text-slate-100 leading-relaxed font-medium mb-3">{report.proposed_settlement}</p>
            <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">{report.proposed_settlement_rationale}</p>
          </div>

          {/* Settlement range */}
          {hasRange && (
            <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Settlement range</h2>
                <span className="text-xs text-slate-400">
                  Confidence {Math.round(sr.confidence * 100)}% · {sr.basis.replace(/_/g, ' ')}
                </span>
              </div>

              {/* Range bar */}
              <div className="relative mb-4">
                <div className="h-2 bg-slate-100 rounded-full">
                  <div
                    className="h-2 bg-primary/20 rounded-full relative"
                    style={{ width: '100%' }}
                  >
                    {/* Median marker */}
                    <div
                      className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-primary rounded-full shadow-sm border-2 border-white"
                      style={{ left: `${medianPct}%`, transform: `translate(-50%, -50%)` }}
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
                  <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Conservative</div>
                  <div className="font-semibold text-slate-800 dark:text-slate-100">₹{sr.low!.toLocaleString('en-IN')}</div>
                </div>
                <div className="bg-primary/5 dark:bg-primary/10 border border-primary/20 rounded-lg p-3">
                  <div className="text-xs text-primary mb-1">Recommended</div>
                  <div className="font-bold text-primary text-lg">₹{sr.median!.toLocaleString('en-IN')}</div>
                </div>
                <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
                  <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Optimistic</div>
                  <div className="font-semibold text-slate-800 dark:text-slate-100">₹{sr.high!.toLocaleString('en-IN')}</div>
                </div>
              </div>
            </div>
          )}

          {/* Statement structure (rhetorical role breakdown) */}
          {(report.statement_structure_a || report.statement_structure_b) && (
            <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <BarChart2 className="h-4 w-4 text-primary" />
                <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Statement structure</h2>
                <span className="text-xs text-slate-400 ml-1">— InLegalBERT rhetorical role analysis</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {[
                  { label: 'Party A', data: report.statement_structure_a },
                  { label: 'Party B', data: report.statement_structure_b },
                ].map(({ label, data }) =>
                  data ? (
                    <div key={label} className="bg-slate-50 dark:bg-slate-800/40 rounded-lg p-4 border border-slate-100 dark:border-slate-700">
                      <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-3">{label}</p>
                      <div className="space-y-2 mb-3">
                        <StructureBar label="Narrative" pct={data.groups.narrative_pct} color="bg-blue-400" />
                        <StructureBar label="Legal argument" pct={data.groups.legal_argument_pct} color="bg-purple-500" />
                        <StructureBar label="Legal authority" pct={data.groups.legal_authority_pct} color="bg-indigo-500" />
                        <StructureBar label="Issue / ratio" pct={data.groups.issue_core_pct} color="bg-amber-400" />
                        <StructureBar label="Rulings" pct={data.groups.rulings_pct} color="bg-emerald-400" />
                      </div>
                      <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed italic">{data.summary}</p>
                      <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">{data.total_sentences} sentences analysed</p>
                    </div>
                  ) : null
                )}
              </div>
            </div>
          )}

          {/* Fairness audit */}
          <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                {fa.bias_detected
                  ? <AlertTriangle className="h-4 w-4 text-amber-500" />
                  : <CheckCircle className="h-4 w-4 text-green-500" />}
                <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Fairness audit</h2>
              </div>
              <button
                onClick={() => setShowFullFairness(s => !s)}
                className="text-xs text-slate-400 hover:text-slate-600 flex items-center gap-1"
              >
                {showFullFairness ? <><ChevronUp className="h-3 w-3" /> Less</> : <><ChevronDown className="h-3 w-3" /> Details</>}
              </button>
            </div>

            <div className="flex gap-4 mb-3">
              <PrivilegeBar label="Party A" score={fa.party_a_privilege_score} highlight={fa.bias_direction === 'party_a'} />
              <PrivilegeBar label="Party B" score={fa.party_b_privilege_score} highlight={fa.bias_direction === 'party_b'} />
            </div>

            <p className={`text-xs font-medium px-2.5 py-1.5 rounded-lg inline-flex items-center gap-1 ${
              fa.bias_detected
                ? 'bg-amber-50 text-amber-700 border border-amber-200'
                : 'bg-green-50 text-green-700 border border-green-200'
            }`}>
              {fa.bias_detected
                ? `${fa.bias_direction === 'party_a' ? 'Party A' : 'Party B'}'s statement had a language advantage — the settlement was adjusted to account for this`
                : 'Both sides used language of similar strength — no adjustment needed'}
            </p>

            {showFullFairness && (
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-3 leading-relaxed border-t border-slate-100 dark:border-slate-700 pt-3">{fa.note}</p>
            )}
          </div>

          {/* Points of agreement */}
          {poa.length > 0 && (
            <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
              <h2 className="text-sm font-semibold text-slate-700 mb-3">Points of agreement</h2>
              <div className="space-y-2">
                {poa.map((p, i) => (
                  <div key={i} className="flex items-start gap-2.5 text-sm text-slate-700 dark:text-slate-300">
                    <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                    <span>{p.point}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Points of conflict */}
          {poc.length > 0 && (
            <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
              <h2 className="text-sm font-semibold text-slate-700 mb-3">Points of conflict</h2>
              <div className="space-y-3">
                {poc.map((c, i) => <ConflictCard key={i} conflict={c} />)}
              </div>
            </div>
          )}

          {/* Applicable laws */}
          {report.applicable_laws.length > 0 && (
            <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3 flex items-center gap-2">
                <FileText className="h-4 w-4 text-slate-400" /> Applicable laws
              </h2>
              <ul className="space-y-1.5">
                {report.applicable_laws.map((law, i) => (
                  <li key={i} className="text-xs text-slate-600 dark:text-slate-300 flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary/40 mt-1.5 flex-shrink-0" />
                    {law}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Similar precedent cases — expandable cards, LLM-enriched like CasePredictor */}
          {report.similar_precedents.length > 0 && (
            <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Library className="w-4 h-4 text-blue-500" />
                <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Similar past cases</h2>
              </div>
              <div className="space-y-2">
                {report.similar_precedents.map((p: SimilarPrecedent, i: number) => {
                  const isExpanded = expandedPrecedents.has(i);

                  // Prefer LLM title; fall back to first sentence of summary
                  const rawSummary = (p.summary || "").trim()
                    .replace(/^[\w\s.]+,\s+J\.?\s+/i, "")
                    .replace(/^\d+\.\s+/, "")
                    .trim();

                  const heading: string = p.llm_title || (() => {
                    const end = rawSummary.indexOf(". ", 40);
                    if (end > 0 && end < 220) return rawSummary.slice(0, end + 1);
                    if (rawSummary.length <= 160) return rawSummary;
                    return rawSummary.slice(0, rawSummary.lastIndexOf(" ", 160)) + "…";
                  })();

                  const body: string = p.llm_description || (() => {
                    const end = rawSummary.indexOf(". ", 40);
                    return end > 0 && end < 220 ? rawSummary.slice(end + 2).trim() : "";
                  })();

                  const hasExpandContent = !!(p.llm_laws_cited?.length || p.llm_decision);

                  return (
                    <div
                      key={i}
                      className="rounded-lg bg-slate-50 border border-slate-100 overflow-hidden dark:bg-slate-800/40 dark:border-slate-700"
                    >
                      <button
                        type="button"
                        onClick={() => {
                          if (!hasExpandContent) return;
                          setExpandedPrecedents(prev => {
                            const next = new Set(prev);
                            isExpanded ? next.delete(i) : next.add(i);
                            return next;
                          });
                        }}
                        className={`w-full flex items-start gap-3 p-3 text-left transition-colors dark:hover:bg-slate-700/50 ${hasExpandContent ? "hover:bg-slate-100 cursor-pointer" : "cursor-default"}`}
                      >
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold text-slate-800 dark:text-slate-200 leading-snug">{heading}</p>
                          {body && (
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">{body}</p>
                          )}
                        </div>
                        <div className="flex-shrink-0 flex flex-col items-end gap-1 ml-2 pt-0.5">
                          <span className="text-xs text-slate-400 font-mono whitespace-nowrap">
                            {Math.round(p.similarity * 100)}% match
                          </span>
                          {hasExpandContent && (
                            <span className="text-xs text-blue-500 whitespace-nowrap">
                              {isExpanded ? "Less ▲" : "More ▼"}
                            </span>
                          )}
                        </div>
                      </button>

                      {isExpanded && hasExpandContent && (
                        <div className="px-3 pb-3 border-t border-slate-200 dark:border-slate-700 pt-2 space-y-2">
                          {p.llm_laws_cited && p.llm_laws_cited.length > 0 && (
                            <div>
                              <p className="text-xs font-medium text-slate-400 uppercase tracking-widest mb-1.5">Laws &amp; Acts</p>
                              <div className="flex flex-wrap gap-1.5">
                                {p.llm_laws_cited.map((law, li) => (
                                  <span key={li} className="inline-block text-xs bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-800/40">
                                    {law}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                          {p.llm_decision && (
                            <div>
                              <p className="text-xs font-medium text-slate-400 uppercase tracking-widest mb-1">Court's Decision</p>
                              <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">{p.llm_decision}</p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Next steps */}
          {report.next_steps.length > 0 && (
            <div className="bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
              <h2 className="text-sm font-semibold text-slate-700 mb-3">Next steps</h2>
              <ol className="space-y-2">
                {report.next_steps.map((step, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-slate-600 dark:text-slate-300">
                    <span className="w-5 h-5 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    {step}
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Feedback */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 text-center">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-1">Was this mediation helpful?</h2>
            <p className="text-xs text-slate-400 dark:text-slate-500 mb-4">Your feedback helps us improve mediation quality.</p>
            {feedbackSent ? (
              <p className="text-sm text-green-600 dark:text-green-400 font-medium">Thank you for your feedback!</p>
            ) : (
              <div className="flex justify-center gap-1">
                {[1, 2, 3, 4, 5].map(s => (
                  <button
                    key={s}
                    onMouseEnter={() => setHoverRating(s)}
                    onMouseLeave={() => setHoverRating(0)}
                    onClick={() => submitFeedback(s)}
                    className="p-1 transition-transform hover:scale-110"
                  >
                    <Star
                      className={`h-7 w-7 transition-colors ${
                        s <= (hoverRating || rating)
                          ? 'text-amber-400 fill-amber-400'
                          : 'text-slate-200'
                      }`}
                    />
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}

function StructureBar({ label, pct, color }: { label: string; pct: number; color: string }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-0.5">
        <span className="text-[11px] text-slate-500 dark:text-slate-400">{label}</span>
        <span className="text-[11px] text-slate-400 tabular-nums">{pct.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 bg-slate-100 dark:bg-slate-700 rounded-full">
        <div
          className={`h-1.5 rounded-full transition-all ${color}`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  );
}

function PrivilegeBar({ label, score, highlight }: { label: string; score: number; highlight: boolean }) {
  return (
    <div className="flex-1">
      <div className="flex items-center justify-between mb-1">
        <span className={`text-xs font-medium ${highlight ? 'text-amber-700' : 'text-slate-500'}`}>{label}</span>
        <span className="text-xs text-slate-400">{(score * 100).toFixed(0)}%</span>
      </div>
      <div className="h-1.5 bg-slate-100 dark:bg-slate-700 rounded-full">
        <div
          className={`h-1.5 rounded-full transition-all ${highlight ? 'bg-amber-400' : 'bg-primary/40'}`}
          style={{ width: `${score * 100}%` }}
        />
      </div>
    </div>
  );
}

const SEVERITY_CONFIG = {
  critical: { label: 'Critical', className: 'bg-red-50 text-red-700 border-red-200' },
  major:    { label: 'Major',    className: 'bg-amber-50 text-amber-700 border-amber-200' },
  minor:    { label: 'Minor',    className: 'bg-slate-50 text-slate-600 border-slate-200' },
};

function ConflictCard({ conflict }: { conflict: ConflictPoint }) {
  const sev = SEVERITY_CONFIG[conflict.severity];
  return (
    <div className="border border-slate-100 dark:border-slate-700 rounded-lg p-4 bg-slate-50/30 dark:bg-slate-900/20">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex items-start gap-2">
          <XCircle className="h-4 w-4 text-slate-400 mt-0.5 flex-shrink-0" />
          <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{conflict.point}</p>
        </div>
        <span className={`text-[11px] font-medium px-1.5 py-0.5 rounded border flex-shrink-0 ${sev.className}`}>
          {sev.label}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-slate-50 dark:bg-slate-800/50 rounded p-2.5">
          <p className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-1">Party A</p>
          <p className="text-xs text-slate-700 dark:text-slate-300">{conflict.party_a_position}</p>
        </div>
        <div className="bg-slate-50 dark:bg-slate-800/50 rounded p-2.5">
          <p className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-1">Party B</p>
          <p className="text-xs text-slate-700 dark:text-slate-300">{conflict.party_b_position}</p>
        </div>
      </div>
    </div>
  );
}
