import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import {
  Copy, Check, Clock, Users, FileText, Loader2,
  ArrowRight, AlertCircle, Brain, ChevronRight, Mic, MicOff, Sparkles,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/api';
import Layout from '@/components/Layout';
import type { DisputeStatus, DisputeStatusResponse } from '@/types/mediation';
import { CASE_TYPE_LABELS } from '@/types/mediation';

const POLL_INTERVAL = 5000;

export default function DisputeRoom() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();

  const locationState = location.state as {
    invite_code?: string;
    is_party_a?: boolean;
  } | null;

  const [status, setStatus] = useState<DisputeStatusResponse | null>(null);
  const [inviteCode, setInviteCode] = useState(locationState?.invite_code || '');
  const [copied, setCopied] = useState(false);
  const [statement, setStatement] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loadError, setLoadError] = useState('');

  const pollRef        = useRef<ReturnType<typeof setInterval> | null>(null);
  const recognitionRef = useRef<any>(null);

  const [isListening,     setIsListening]     = useState(false);
  const [voiceSupported,  setVoiceSupported]  = useState(false);
  const [voiceError,      setVoiceError]      = useState('');
  const [interimText,     setInterimText]     = useState('');
  const [hasUsedVoice,    setHasUsedVoice]    = useState(false);
  const [correcting,      setCorrecting]      = useState(false);
  const [fixStatus,       setFixStatus]       = useState<'idle'|'fixed'|'error'>('idle');

  const fetchStatus = useCallback(async () => {
    if (!id) return;
    try {
      const data = await apiFetch<DisputeStatusResponse>(`/mediation/${id}/status`);
      setStatus(data);
      if (!inviteCode) {
        // Try to get invite code from my disputes
        const allDisputes = await apiFetch<{ disputes: Array<{ dispute_id: string; invite_code: string }> }>(
          '/mediation/my/disputes'
        );
        const mine = allDisputes.disputes.find(d => d.dispute_id === id);
        if (mine) setInviteCode(mine.invite_code);
      }
      if (data.status === 'completed') {
        navigate(`/mediation/${id}/result`, { replace: true });
      }
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Could not load dispute status.');
    }
  }, [id, inviteCode, navigate]);

  useEffect(() => {
    fetchStatus();
    pollRef.current = setInterval(fetchStatus, POLL_INTERVAL);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [fetchStatus]);

  useEffect(() => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    setVoiceSupported(!!SR);
    return () => { recognitionRef.current?.abort(); };
  }, []);

  function toggleVoice() {
    if (isListening) {
      recognitionRef.current?.stop();
      return;
    }

    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return;

    setVoiceError('');
    const recognition = new SR();
    recognition.continuous     = true;
    recognition.interimResults = true;
    recognition.lang           = 'en-IN';

    recognition.onresult = (event: any) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          setStatement(prev => prev + (prev.trim() ? ' ' : '') + transcript.trim());
          setInterimText('');
          setHasUsedVoice(true);
          setFixStatus('idle');
        } else {
          interim += transcript;
        }
      }
      if (interim) setInterimText(interim);
    };

    recognition.onerror = (event: any) => {
      const msgs: Record<string, string> = {
        'not-allowed':         'Microphone access denied. Please allow microphone in your browser settings.',
        'service-not-allowed': 'This browser blocks speech recognition. Please use Chrome or Edge instead of Brave.',
        'network':             'Brave browser blocks Google\'s speech service. Please use Chrome or Edge for voice input.',
        'no-speech':           'No speech detected. Please try again.',
        'aborted':             '',
      };
      const msg = msgs[event.error] ?? `Voice input is not supported in this browser (${event.error}). Please use Chrome or Edge.`;
      if (msg) setVoiceError(msg);
      setIsListening(false);
      setInterimText('');
    };

    recognition.onend = () => {
      setIsListening(false);
      setInterimText('');
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  }

  async function fixTranscript() {
    if (!statement.trim() || correcting) return;
    setCorrecting(true);
    setFixStatus('idle');
    try {
      const res = await apiFetch<{ corrected: string }>('/mediation/voice/correct', {
        method: 'POST',
        body: { text: statement },
      });
      setStatement(res.corrected);
      setFixStatus('fixed');
    } catch {
      setFixStatus('error');
    } finally {
      setCorrecting(false);
    }
  }

  async function handleSubmitStatement(e: React.FormEvent) {
    e.preventDefault();
    if (statement.trim().length < 50) {
      setSubmitError('Please write at least 50 characters.'); return;
    }
    setSubmitting(true); setSubmitError('');
    try {
      await apiFetch(`/mediation/${id}/submit`, {
        method: 'POST',
        body: { statement: statement.trim(), language: 'en' },
      });
      setSubmitted(true);
      await fetchStatus();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to submit. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  function copyCode() {
    navigator.clipboard.writeText(inviteCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (loadError) {
    return (
      <Layout>
        <div className="max-w-lg mx-auto px-4 py-24 text-center">
          <AlertCircle className="h-8 w-8 text-red-400 mx-auto mb-3" />
          <h2 className="font-semibold text-slate-800 mb-1">Dispute not found</h2>
          <p className="text-sm text-slate-500 mb-4">{loadError}</p>
          <button onClick={() => navigate('/mediation')} className="text-sm text-primary hover:underline">
            Back to Mediation
          </button>
        </div>
      </Layout>
    );
  }

  if (!status) {
    return (
      <Layout>
        <div className="flex justify-center py-24">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        </div>
      </Layout>
    );
  }

  const disputeStatus: DisputeStatus = status.status;
  const userIsPartyA = status.is_party_a;
  const iHaveSubmitted = userIsPartyA ? status.party_a_submitted : status.party_b_submitted;

  return (
    <Layout>
      <div className="max-w-2xl mx-auto px-4 py-10">
        {/* Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <p className="text-xs text-slate-400 font-mono mb-1">{id?.slice(0, 8)}…</p>
            <h1 className="text-2xl font-bold text-slate-900">
              {CASE_TYPE_LABELS[status.case_type] || status.case_type} Dispute
            </h1>
            <p className="text-sm text-slate-500 mt-1">{status.jurisdiction}</p>
          </div>
          <StatusBadge status={disputeStatus} />
        </div>

        {/* Progress tracker */}
        <div className="flex items-center gap-1 mb-8">
          {(['joined', 'statements', 'analysis', 'done'] as const).map((step, i) => {
            const stepDone = (
              (step === 'joined'     && status.party_b_joined) ||
              (step === 'statements' && status.party_a_submitted && status.party_b_submitted) ||
              (step === 'analysis'   && disputeStatus === 'completed') ||
              (step === 'done'       && disputeStatus === 'completed')
            );
            const stepActive = (
              (step === 'joined'     && !status.party_b_joined) ||
              (step === 'statements' && status.party_b_joined && !(status.party_a_submitted && status.party_b_submitted)) ||
              (step === 'analysis'   && disputeStatus === 'analysis_running') ||
              (step === 'done'       && disputeStatus === 'completed')
            );
            const labels = { joined: 'Other party joins', statements: 'Submit statements', analysis: 'AI analysis', done: 'View result' };
            return (
              <div key={step} className="flex items-center gap-1 flex-1">
                <div className={`flex-1 h-1.5 rounded-full transition-colors ${
                  stepDone ? 'bg-primary' : stepActive ? 'bg-primary/40' : 'bg-slate-100'
                }`} />
                {i < 3 && <ChevronRight className="h-3 w-3 text-slate-300 flex-shrink-0" />}
              </div>
            );
          })}
        </div>

        {/* ── State: Waiting for Party B ── */}
        {disputeStatus === 'pending_party_b' && (
          <div className="space-y-4">
            <div className="bg-white border border-slate-200 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Users className="h-5 w-5 text-amber-500" />
                <h2 className="font-semibold text-slate-800">Waiting for the other party to join</h2>
              </div>
              <p className="text-sm text-slate-500 mb-5">
                Share this invite code with the other party. They'll join and submit their side of the story separately — you won't see it until the final report.
              </p>
              {inviteCode && (
                <div className="flex items-center gap-3 bg-slate-50 border border-slate-200 rounded-lg px-4 py-3">
                  <span className="font-mono text-2xl font-bold text-slate-900 tracking-widest flex-1">{inviteCode}</span>
                  <button
                    onClick={copyCode}
                    className="flex items-center gap-1.5 text-sm text-primary hover:opacity-80 transition-opacity"
                  >
                    {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                    {copied ? 'Copied' : 'Copy'}
                  </button>
                </div>
              )}
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400 px-1">
              <Clock className="h-3.5 w-3.5" />
              <span>This page refreshes automatically every 5 seconds</span>
            </div>
          </div>
        )}

        {/* ── State: Submit Statement ── */}
        {(disputeStatus === 'pending_statements' ||
          disputeStatus === 'pending_party_b_statement' ||
          disputeStatus === 'pending_party_a_statement') && (
          <div className="space-y-4">
            {!iHaveSubmitted && !submitted ? (
              <div className="bg-white border border-slate-200 rounded-xl p-6">
                <div className="flex items-center gap-2 mb-2">
                  <FileText className="h-5 w-5 text-blue-500" />
                  <h2 className="font-semibold text-slate-800">Submit your statement</h2>
                </div>
                <p className="text-sm text-slate-500 mb-5">
                  Write your account of the dispute honestly and in detail. The other party cannot see this — only the AI mediator sees both sides. Include dates, amounts, and any evidence you have.
                </p>

                <form onSubmit={handleSubmitStatement} className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-xs font-medium text-slate-700">Your statement</label>
                      <div className="flex items-center gap-2">
                        {voiceSupported && (
                          <button
                            type="button"
                            onClick={toggleVoice}
                            title={isListening ? 'Stop recording' : 'Speak your statement'}
                            className={`flex items-center gap-1 text-xs px-2 py-1 rounded-md border transition-all ${
                              isListening
                                ? 'bg-red-50 text-red-600 border-red-300 animate-pulse'
                                : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                            }`}
                          >
                            {isListening
                              ? <><MicOff className="h-3 w-3" /> Stop</>
                              : <><Mic className="h-3 w-3" /> Speak</>
                            }
                          </button>
                        )}
                        <span className={`text-xs ${statement.trim().length >= 50 ? 'text-green-600' : 'text-slate-400'}`}>
                          {statement.trim().length} / 50+ chars
                        </span>
                      </div>
                    </div>
                    <textarea
                      value={statement}
                      onChange={e => { setStatement(e.target.value); setSubmitError(''); }}
                      rows={8}
                      placeholder="Describe the situation from your perspective. Include: what happened, when it happened, amounts involved, evidence you have (receipts, messages, agreements), and what you believe is a fair resolution."
                      className={`w-full px-3 py-3 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-slate-400 resize-none leading-relaxed ${
                        isListening ? 'border-red-300 ring-2 ring-red-100' : 'border-slate-200'
                      }`}
                    />
                    {isListening && (
                      <div className="mt-1.5 flex items-start gap-2 text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                        <span className="mt-0.5 flex-shrink-0 w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                        <span>
                          Listening… speak clearly in English
                          {interimText && (
                            <span className="text-slate-500 ml-1">
                              — <em>"{interimText.slice(0, 80)}{interimText.length > 80 ? '…' : ''}"</em>
                            </span>
                          )}
                        </span>
                      </div>
                    )}
                    {!isListening && hasUsedVoice && (
                      <div className="mt-1.5 flex items-center gap-2">
                        <button
                          type="button"
                          onClick={fixTranscript}
                          disabled={correcting}
                          className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md border transition-all disabled:opacity-60 ${
                            fixStatus === 'fixed'
                              ? 'border-green-200 bg-green-50 text-green-700'
                              : fixStatus === 'error'
                              ? 'border-red-200 bg-red-50 text-red-700'
                              : 'border-violet-200 bg-violet-50 text-violet-700 hover:bg-violet-100'
                          }`}
                        >
                          {correcting
                            ? <><Loader2 className="h-3 w-3 animate-spin" /> Fixing…</>
                            : fixStatus === 'fixed'
                            ? <><Check className="h-3 w-3" /> Fixed — fix again?</>
                            : fixStatus === 'error'
                            ? <><Sparkles className="h-3 w-3" /> Retry fix</>
                            : <><Sparkles className="h-3 w-3" /> Fix transcription errors</>
                          }
                        </button>
                        <span className="text-xs text-slate-400">
                          {fixStatus === 'error' ? 'Correction failed — check server logs' : 'AI corrects mishearings'}
                        </span>
                      </div>
                    )}
                  </div>

                  {voiceError && (
                    <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">{voiceError}</p>
                  )}
                  {submitError && (
                    <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">{submitError}</p>
                  )}

                  <button
                    type="submit"
                    disabled={submitting || statement.trim().length < 50}
                    className="w-full flex items-center justify-center gap-2 bg-primary text-white text-sm font-medium py-3 rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
                  >
                    {submitting ? (
                      <><Loader2 className="h-4 w-4 animate-spin" /> Submitting…</>
                    ) : (
                      <><span>Submit statement</span><ArrowRight className="h-4 w-4" /></>
                    )}
                  </button>
                </form>
              </div>
            ) : (
              <div className="bg-white border border-slate-200 rounded-xl p-6 text-center">
                <Check className="h-8 w-8 text-green-500 mx-auto mb-3" />
                <h2 className="font-semibold text-slate-800 mb-1">Statement submitted</h2>
                <p className="text-sm text-slate-500">Waiting for the other party to submit their statement. This page updates automatically.</p>
              </div>
            )}

            {/* Party status indicators */}
            <div className="flex gap-3">
              <div className={`flex-1 flex items-center gap-2 px-3 py-2 rounded-lg border text-xs ${
                status.party_a_submitted ? 'bg-green-50 border-green-200 text-green-700' : 'bg-slate-50 border-slate-200 text-slate-500'
              }`}>
                {status.party_a_submitted ? <Check className="h-3.5 w-3.5" /> : <Clock className="h-3.5 w-3.5" />}
                Party A {status.party_a_submitted ? 'submitted' : 'pending'}
              </div>
              <div className={`flex-1 flex items-center gap-2 px-3 py-2 rounded-lg border text-xs ${
                status.party_b_submitted ? 'bg-green-50 border-green-200 text-green-700' : 'bg-slate-50 border-slate-200 text-slate-500'
              }`}>
                {status.party_b_submitted ? <Check className="h-3.5 w-3.5" /> : <Clock className="h-3.5 w-3.5" />}
                Party B {status.party_b_submitted ? 'submitted' : 'pending'}
              </div>
            </div>
          </div>
        )}

        {/* ── State: Analysis Running ── */}
        {disputeStatus === 'analysis_running' && (
          <div className="bg-white border border-slate-200 rounded-xl p-8 text-center">
            <div className="w-14 h-14 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-5">
              <Brain className="h-7 w-7 text-primary" />
            </div>
            <h2 className="font-semibold text-slate-800 mb-2">AI analysis in progress</h2>
            <p className="text-sm text-slate-500 mb-6 max-w-sm mx-auto">
              Our system is extracting key claims, running a fairness audit, computing a data-driven settlement range, and generating the mediation report.
            </p>

            <div className="space-y-2 text-left max-w-xs mx-auto mb-6">
              {[
                'Extracting facts from both statements',
                'Running linguistic fairness audit',
                'Computing settlement range from court data',
                'Generating neutral mediation report',
              ].map((step, i) => (
                <div key={i} className="flex items-center gap-2 text-xs text-slate-500">
                  <Loader2 className="h-3 w-3 animate-spin text-primary flex-shrink-0" style={{ animationDelay: `${i * 0.2}s` }} />
                  {step}
                </div>
              ))}
            </div>

            <p className="text-xs text-slate-400">This typically takes 30–60 seconds. This page refreshes automatically.</p>
          </div>
        )}

        {/* ── State: Failed ── */}
        {disputeStatus === 'failed' && (
          <div className="bg-white border border-red-200 rounded-xl p-6 text-center">
            <AlertCircle className="h-8 w-8 text-red-400 mx-auto mb-3" />
            <h2 className="font-semibold text-slate-800 mb-1">Analysis failed</h2>
            <p className="text-sm text-slate-500 mb-4">Something went wrong during analysis. Please try creating a new dispute.</p>
            <button
              onClick={() => navigate('/mediation')}
              className="text-sm text-primary font-medium hover:underline"
            >
              Back to Mediation
            </button>
          </div>
        )}
      </div>
    </Layout>
  );
}

function StatusBadge({ status }: { status: DisputeStatus }) {
  const configs: Record<DisputeStatus, { label: string; className: string }> = {
    pending_party_b:           { label: 'Waiting to join',    className: 'bg-amber-50  text-amber-700  border-amber-200'  },
    pending_statements:        { label: 'Awaiting statements',className: 'bg-blue-50   text-blue-700   border-blue-200'   },
    pending_party_b_statement: { label: 'Awaiting statement', className: 'bg-blue-50   text-blue-700   border-blue-200'   },
    pending_party_a_statement: { label: 'Awaiting statement', className: 'bg-blue-50   text-blue-700   border-blue-200'   },
    analysis_running:          { label: 'Analysing…',         className: 'bg-purple-50 text-purple-700 border-purple-200' },
    completed:                 { label: 'Completed',          className: 'bg-green-50  text-green-700  border-green-200'  },
    failed:                    { label: 'Failed',             className: 'bg-red-50    text-red-700    border-red-200'    },
  };
  const cfg = configs[status];
  return (
    <span className={`text-xs font-medium px-2.5 py-1 rounded-full border flex-shrink-0 ${cfg.className}`}>
      {cfg.label}
    </span>
  );
}
