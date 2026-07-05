import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Loader2, Info, Mic, MicOff, Sparkles, Check } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import Layout from '@/components/Layout';
import type { CreateDisputeResponse } from '@/types/mediation';
import { CASE_TYPE_LABELS, INDIAN_STATES } from '@/types/mediation';

export default function CreateDispute() {
  const navigate = useNavigate();
  const location = useLocation();
  const priorPredictionId = (location.state as { prediction_id?: string } | null)?.prediction_id;

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const recognitionRef   = useRef<any>(null);
  const descriptionRef   = useRef('');   // tracks current case_description for voice handler
  const [isListening,     setIsListening]     = useState(false);
  const [voiceSupported,  setVoiceSupported]  = useState(false);
  const [voiceError,      setVoiceError]      = useState('');
  const [interimText,     setInterimText]     = useState('');
  const [hasUsedVoice,    setHasUsedVoice]    = useState(false);
  const [correcting,      setCorrecting]      = useState(false);
  const [fixStatus,       setFixStatus]       = useState<'idle'|'fixed'|'error'>('idle');

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
          const current = descriptionRef.current;
          set('case_description', current + (current.trim() ? ' ' : '') + transcript.trim());
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
      setVoiceError(
        event.error === 'not-allowed'
          ? 'Microphone access denied. Please allow microphone access in your browser settings.'
          : 'Voice input error. Please try again.'
      );
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
    if (!form.case_description.trim() || correcting) return;
    setCorrecting(true);
    setFixStatus('idle');
    try {
      const res = await apiFetch<{ corrected: string }>('/mediation/voice/correct', {
        method: 'POST',
        body: { text: form.case_description },
      });
      set('case_description', res.corrected);
      setFixStatus('fixed');
    } catch {
      setFixStatus('error');
    } finally {
      setCorrecting(false);
    }
  }

  const [form, setForm] = useState({
    case_description: '',
    case_type: '',
    state: '',
    language: 'en',
    prior_prediction_id: priorPredictionId || '',
  });

  function set(field: keyof typeof form, value: string) {
    if (field === 'case_description') descriptionRef.current = value;
    setForm(f => ({ ...f, [field]: value }));
    setError('');
  }

  const descWords = form.case_description.trim().length;
  const descValid = descWords >= 50;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.case_type) { setError('Please select a case type.'); return; }
    if (!descValid) { setError('Please describe the dispute in at least 50 characters.'); return; }
    if (!form.state) { setError('Please select a state.'); return; }

    setLoading(true); setError('');
    try {
      const payload: Record<string, string> = {
        case_description: form.case_description,
        case_type: form.case_type,
        jurisdiction: `India/${form.state}`,
        state: form.state,
        language: form.language,
      };
      if (form.prior_prediction_id) {
        payload.prior_prediction_id = form.prior_prediction_id;
      }

      const data = await apiFetch<CreateDisputeResponse>('/mediation/create', {
        method: 'POST',
        body: payload as Record<string, unknown>,
      });
      navigate(`/mediation/${data.dispute_id}/room`, {
        state: { invite_code: data.invite_code, is_party_a: true },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create dispute. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Layout>
      <div className="max-w-2xl mx-auto px-4 py-12">
        {/* Back */}
        <button
          onClick={() => navigate('/mediation')}
          className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-8 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Mediation
        </button>

        <h1 className="text-2xl font-bold text-slate-900 mb-2">Describe the dispute</h1>
        <p className="text-slate-500 text-sm mb-8">
          Only you can see this description. The other party will not see it — they submit their own version separately.
        </p>

        {priorPredictionId && (
          <div className="flex items-start gap-3 bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 mb-6">
            <Info className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-blue-700">
              Your case predictor results will be included as context for the mediator.
            </p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Case type */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Type of dispute</label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {Object.entries(CASE_TYPE_LABELS).map(([val, label]) => (
                <button
                  key={val}
                  type="button"
                  onClick={() => set('case_type', val)}
                  className={`py-2.5 px-3 text-sm rounded-lg border text-left transition-all ${
                    form.case_type === val
                      ? 'bg-primary text-white border-primary font-medium'
                      : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* State */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">State / jurisdiction</label>
            <select
              value={form.state}
              onChange={e => set('state', e.target.value)}
              className="w-full px-3 py-2.5 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-slate-700"
            >
              <option value="">Select state…</option>
              {INDIAN_STATES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          {/* Description */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-slate-700">Your account of the dispute</label>
              <div className="flex items-center gap-2">
                {voiceSupported && (
                  <button
                    type="button"
                    onClick={toggleVoice}
                    title={isListening ? 'Stop recording' : 'Speak your account'}
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
                <span className={`text-xs ${descValid ? 'text-green-600' : 'text-slate-400'}`}>
                  {form.case_description.length} / 50+ chars
                </span>
              </div>
            </div>
            <textarea
              value={form.case_description}
              onChange={e => set('case_description', e.target.value)}
              rows={6}
              placeholder="Describe the situation in your own words. Include dates, amounts, what happened, and what outcome you're looking for. Be specific — the more detail you provide, the more accurate the AI mediation will be."
              className={`w-full px-3 py-3 text-sm border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-slate-400 resize-none leading-relaxed ${
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
                    fixStatus === 'fixed' ? 'border-green-200 bg-green-50 text-green-700'
                    : fixStatus === 'error' ? 'border-red-200 bg-red-50 text-red-700'
                    : 'border-violet-200 bg-violet-50 text-violet-700 hover:bg-violet-100'
                  }`}
                >
                  {correcting
                    ? <><Loader2 className="h-3 w-3 animate-spin" /> Fixing…</>
                    : fixStatus === 'fixed' ? <><Check className="h-3 w-3" /> Fixed — fix again?</>
                    : fixStatus === 'error' ? <><Sparkles className="h-3 w-3" /> Retry fix</>
                    : <><Sparkles className="h-3 w-3" /> Fix transcription errors</>
                  }
                </button>
                <span className="text-xs text-slate-400">
                  {fixStatus === 'error' ? 'Correction failed — check server' : 'AI corrects mishearings'}
                </span>
              </div>
            )}
            {voiceError && (
              <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2 mt-1.5">{voiceError}</p>
            )}
            <p className="text-xs text-slate-400 mt-1.5">
              The other party will not see this. Only the AI mediator sees both sides.
            </p>
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !descValid}
            className="w-full flex items-center justify-center gap-2 bg-primary text-white text-sm font-medium py-3 rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {loading ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Creating dispute…</>
            ) : (
              <><span>Create dispute & get invite code</span><ArrowRight className="h-4 w-4" /></>
            )}
          </button>
        </form>
      </div>
    </Layout>
  );
}
