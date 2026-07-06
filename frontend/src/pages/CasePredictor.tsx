import { useState, useRef, useEffect } from "react";
import {
  Scale, ArrowRight, ArrowLeft, CheckCircle2, AlertTriangle,
  Loader2, TrendingUp, RotateCcw, Send,
  ShieldAlert, Home, Heart, Briefcase, FileText,
  BookOpen, RefreshCw, Gavel,
  Mic, MicOff, Sparkles, Check,
} from "lucide-react";
import { Link } from "react-router-dom";
import Layout from "../components/Layout";

// ── Relief / prayer options ───────────────────────────────────────────────────

interface ReliefOption {
  id:        string;
  label:     string;
  desc:      string;
  case_type: string;
  is_appeal: boolean;
  icon:      React.ElementType;
  accent:    string; // tailwind color key
}

const RELIEF_OPTIONS: ReliefOption[] = [
  {
    id:        "bail_acquittal",
    label:     "Bail / Release / Acquittal",
    desc:      "Seeking release from custody or clearing criminal charges",
    case_type: "criminal_complaint",
    is_appeal: false,
    icon:      ShieldAlert,
    accent:    "red",
  },
  {
    id:        "compensation",
    label:     "Compensation or Recovery of Dues",
    desc:      "Monetary recovery, damages, salary, or unpaid dues",
    case_type: "harassment_civil",
    is_appeal: false,
    icon:      Briefcase,
    accent:    "orange",
  },
  {
    id:        "injunction",
    label:     "Stop Someone from an Action",
    desc:      "Preventing the other party from doing something (injunction or stay)",
    case_type: "property_dispute",
    is_appeal: false,
    icon:      Gavel,
    accent:    "amber",
  },
  {
    id:        "property_rights",
    label:     "Property Rights or Possession",
    desc:      "Claiming ownership, possession, or rights over land or property",
    case_type: "property_dispute",
    is_appeal: false,
    icon:      Home,
    accent:    "yellow",
  },
  {
    id:        "divorce",
    label:     "Divorce or Family Settlement",
    desc:      "Ending a marriage or resolving family matters through the court",
    case_type: "divorce_contested",
    is_appeal: false,
    icon:      Heart,
    accent:    "pink",
  },
  {
    id:        "harassment_protection",
    label:     "Protection from Harassment",
    desc:      "Dowry harassment, domestic violence, or in-law abuse",
    case_type: "dowry_harassment",
    is_appeal: false,
    icon:      FileText,
    accent:    "rose",
  },
  {
    id:        "writ",
    label:     "Challenge a Government Order",
    desc:      "Challenging a government or administrative decision affecting your rights",
    case_type: "writ_petition",
    is_appeal: false,
    icon:      BookOpen,
    accent:    "teal",
  },
  {
    id:        "appeal",
    label:     "Overturn a Previous Verdict",
    desc:      "Appealing a judgment already delivered by a lower court",
    case_type: "appeal",
    is_appeal: true,
    icon:      RefreshCw,
    accent:    "purple",
  },
];

const ACCENT: Record<string, { border: string; hover: string; icon: string; badge: string }> = {
  red:    { border: "hover:border-red-400",    hover: "hover:bg-red-50",    icon: "text-red-400 group-hover:text-red-600",    badge: "bg-red-100 text-red-700" },
  orange: { border: "hover:border-orange-400", hover: "hover:bg-orange-50", icon: "text-orange-400 group-hover:text-orange-600", badge: "bg-orange-100 text-orange-700" },
  amber:  { border: "hover:border-amber-400",  hover: "hover:bg-amber-50",  icon: "text-amber-400 group-hover:text-amber-600",  badge: "bg-amber-100 text-amber-700" },
  yellow: { border: "hover:border-yellow-400", hover: "hover:bg-yellow-50", icon: "text-yellow-500 group-hover:text-yellow-600", badge: "bg-yellow-100 text-yellow-700" },
  pink:   { border: "hover:border-pink-400",   hover: "hover:bg-pink-50",   icon: "text-pink-400 group-hover:text-pink-600",   badge: "bg-pink-100 text-pink-700" },
  rose:   { border: "hover:border-rose-400",   hover: "hover:bg-rose-50",   icon: "text-rose-400 group-hover:text-rose-600",   badge: "bg-rose-100 text-rose-700" },
  teal:   { border: "hover:border-teal-400",   hover: "hover:bg-teal-50",   icon: "text-teal-400 group-hover:text-teal-600",   badge: "bg-teal-100 text-teal-700" },
  purple: { border: "hover:border-purple-400", hover: "hover:bg-purple-50", icon: "text-purple-400 group-hover:text-purple-600", badge: "bg-purple-100 text-purple-700" },
};

// ── Result display ────────────────────────────────────────────────────────────

const PredictionResult = ({
  prediction,
  onReset,
}: {
  prediction: any;
  onReset: () => void;
}) => {
  const verdict    = prediction.verdict || "Unknown";
  const isAccepted = verdict === "Accepted";
  const confPct    =
    prediction.probability != null
      ? (prediction.probability * 100).toFixed(1)
      : prediction.confidence?.score != null
      ? (prediction.confidence.score * 100).toFixed(1)
      : "N/A";
  const riskLabel  = (prediction.risk_level || "").replace(/_/g, " ");
  const llm        = prediction.llm_analysis;
  const recs: string[] = llm?.recommendations?.length
    ? llm.recommendations
    : prediction.recommendations || [];

  const confNum            = parseFloat(confPct);
  const riskLevel          = prediction.risk_level || "";
  const showMediation      =
    !isAccepted ||
    confNum < 70 ||
    riskLevel === "high" ||
    riskLevel === "very_high";
  const mediationHeadline  = !isAccepted
    ? "The model predicts an unfavorable outcome"
    : "The model is uncertain about this outcome";
  const mediationBody      = !isAccepted
    ? "Going to court carries significant risk here. AI Mediation lets both parties reach a fair settlement privately — faster, cheaper, and without a judge."
    : "When confidence is below 70%, outcomes can go either way. AI Mediation may give you a faster, more certain resolution than litigation.";

  return (
    <div className="space-y-4 animate-fade-up">
      {/* Banner */}
      <div className="flex items-center gap-2 text-green-700 bg-green-50 border border-green-200 rounded-xl px-4 py-3">
        <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
        <span className="text-sm font-medium">
          Analysis complete — here is what the AI model predicts
        </span>
      </div>

      {/* Verdict card */}
      <div className={`rounded-2xl p-6 border-2 ${isAccepted ? "bg-green-50 border-green-300" : "bg-red-50 border-red-300"}`}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className={`text-xs font-semibold uppercase tracking-widest mb-2 ${isAccepted ? "text-green-600" : "text-red-600"}`}>
              Predicted Outcome
            </p>
            <p className={`text-4xl font-bold ${isAccepted ? "text-green-900" : "text-red-900"}`}>
              {verdict}
            </p>
            {riskLabel && (
              <span className={`mt-2 inline-block text-xs px-3 py-1 rounded-full font-medium capitalize ${
                isAccepted ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
              }`}>
                {riskLabel} risk
              </span>
            )}
          </div>
          <div className={`text-right flex-shrink-0 ${isAccepted ? "text-green-700" : "text-red-700"}`}>
            <p className="text-5xl font-bold">{confPct}%</p>
            <p className="text-xs text-gray-500 mt-1">model confidence</p>
          </div>
        </div>
        {llm?.verdict_summary && (
          <p className="mt-4 text-sm text-gray-700 border-t border-gray-200 pt-4 leading-relaxed">
            {llm.verdict_summary}
          </p>
        )}
      </div>

      {/* ── Mediation suggestion ─────────────────────────────────────────── */}
      {showMediation && (
        <div className="rounded-2xl border-2 border-indigo-200 bg-gradient-to-br from-indigo-50 to-purple-50 p-5">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0 shadow-md">
              <Scale className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-indigo-900 mb-1">
                {mediationHeadline} — consider AI Mediation
              </p>
              <p className="text-xs text-indigo-700 leading-relaxed mb-4">
                {mediationBody}
              </p>
              <div className="flex flex-col sm:flex-row gap-2">
                <Link
                  to="/mediation/create"
                  state={{ prediction_id: prediction.prediction_id }}
                  className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 text-xs font-bold text-white shadow hover:shadow-md hover:opacity-90 transition-all"
                >
                  <Scale className="w-3.5 h-3.5" />
                  Start AI Mediation
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
                <Link
                  to="/mediation"
                  className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl border border-indigo-200 bg-white text-xs font-medium text-indigo-700 hover:bg-indigo-50 transition-all"
                >
                  Learn how it works
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Legal reasoning */}
      {llm?.legal_reasoning && (
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">
            Legal Reasoning
          </p>
          <p className="text-sm text-gray-800 leading-relaxed">{llm.legal_reasoning}</p>
        </div>
      )}

      {/* Laws + Factors */}
      {(llm?.applicable_laws?.length > 0 || llm?.key_factors?.length > 0) && (
        <div className="grid grid-cols-2 gap-4">
          {llm?.applicable_laws?.length > 0 && (
            <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
              <p className="text-xs font-semibold text-blue-500 uppercase tracking-widest mb-3">
                Applicable Laws
              </p>
              <ul className="space-y-2">
                {llm.applicable_laws.slice(0, 4).map((law: string, i: number) => (
                  <li key={i} className="text-xs text-blue-900 flex items-start gap-2">
                    <Scale className="w-3 h-3 mt-0.5 flex-shrink-0 text-blue-400" />
                    <span>{law}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {llm?.key_factors?.length > 0 && (
            <div className="rounded-xl border border-purple-100 bg-purple-50 p-4">
              <p className="text-xs font-semibold text-purple-500 uppercase tracking-widest mb-3">
                Key Factors
              </p>
              <ul className="space-y-2">
                {llm.key_factors.slice(0, 4).map((factor: string, i: number) => (
                  <li key={i} className="text-xs text-purple-900 flex items-start gap-2">
                    <span className="text-purple-400 flex-shrink-0">▸</span>
                    <span>{factor}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Risk assessment */}
      {llm?.risk_assessment && (
        <div className="rounded-xl border border-amber-100 bg-amber-50 p-4 flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-semibold text-amber-600 uppercase tracking-widest mb-1">
              Risk Assessment
            </p>
            <p className="text-sm text-amber-900 leading-relaxed">{llm.risk_assessment}</p>
          </div>
        </div>
      )}

      {/* Recommendations */}
      {recs.length > 0 && (
        <div className="rounded-xl border border-green-100 bg-green-50 p-4">
          <p className="text-xs font-semibold text-green-600 uppercase tracking-widest mb-3">
            Recommended Next Steps
          </p>
          <ul className="space-y-2">
            {recs.slice(0, 5).map((rec: string, i: number) => (
              <li key={i} className="text-sm text-green-900 flex items-start gap-2.5 leading-relaxed">
                <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Confidence note */}
      {llm?.confidence_note && (
        <p className="text-xs text-gray-400 italic px-1">{llm.confidence_note}</p>
      )}

      {/* CTAs */}
      <div className="flex flex-col sm:flex-row gap-3 pt-2">
        <button
          onClick={onReset}
          className="flex items-center justify-center gap-2 px-5 py-3 rounded-xl border-2 border-gray-200 text-sm font-medium text-gray-700 hover:border-gray-300 hover:bg-gray-50 transition-all"
        >
          <RotateCcw className="w-4 h-4" />
          Analyse Another Case
        </button>
        <Link
          to="/mediation/create"
          className="flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-blue-500 to-purple-600 text-sm font-medium text-white hover:shadow-lg transition-all"
        >
          <Scale className="w-4 h-4" />
          Try AI Mediation
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
};

// ── Step labels for progress bar ──────────────────────────────────────────────

const STEP_LABELS = ["Your Statement", "What You Seek", "Your Role", "Location"];

// ── Main component ────────────────────────────────────────────────────────────

const CasePredictor = () => {
  useEffect(() => { window.scrollTo({ top: 0, behavior: "auto" }); }, []);

  type Phase = "form" | "loading" | "result";

  // ── State ────────────────────────────────────────────────────────────────
  const [phase, setPhase]             = useState<Phase>("form");
  const [step, setStep]               = useState(0);
  const [statement, setStatement]     = useState("");
  const [relief, setRelief]           = useState<ReliefOption | null>(null);
  const [role, setRole]               = useState<"petitioner" | "respondent" | null>(null);
  const [location, setLocation]       = useState("");
  const [prediction, setPrediction]   = useState<any>(null);
  const [error, setError]             = useState<string | null>(null);

  const textareaRef     = useRef<HTMLTextAreaElement>(null);
  const locationRef     = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef   = useRef<Blob[]>([]);
  const streamRef        = useRef<MediaStream | null>(null);
  const timerRef         = useRef<ReturnType<typeof setInterval> | null>(null);
  const statementRef     = useRef("");

  // Voice state
  const [isRecording,      setIsRecording]      = useState(false);
  const [isTranscribing,   setIsTranscribing]   = useState(false);
  const [voiceSupported,   setVoiceSupported]   = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [voiceError,       setVoiceError]       = useState("");
  const [hasUsedVoice,     setHasUsedVoice]     = useState(false);
  const [correcting,       setCorrecting]       = useState(false);
  const [fixStatus,        setFixStatus]        = useState<"idle" | "fixed" | "error">("idle");

  const apiUrl     = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const authToken  = localStorage.getItem("sla_token");
  const authHeader = authToken ? { Authorization: `Bearer ${authToken}` } : {};

  const progress = Math.round((step / STEP_LABELS.length) * 100);

  // Voice support detection + cleanup
  useEffect(() => {
    setVoiceSupported(
      typeof MediaRecorder !== "undefined" &&
      !!navigator.mediaDevices?.getUserMedia
    );
    return () => {
      if (mediaRecorderRef.current?.state !== "inactive") mediaRecorderRef.current?.stop();
      streamRef.current?.getTracks().forEach(t => t.stop());
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // Focus management
  useEffect(() => {
    if (phase !== "form") return;
    if (step === 0) setTimeout(() => textareaRef.current?.focus(), 60);
    if (step === 3) setTimeout(() => locationRef.current?.focus(), 60);
  }, [step, phase]);

  // Keep statementRef in sync so voice handler always sees current value
  const updateStatement = (value: string) => {
    statementRef.current = value;
    setStatement(value);
    setError(null);
    setFixStatus("idle");
  };

  // ── Voice helpers (MediaRecorder → Groq Whisper) ─────────────────────────

  function getBestMimeType(): string {
    const types = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
      "audio/ogg",
      "audio/mp4",
    ];
    for (const t of types) {
      if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(t)) return t;
    }
    return "";
  }

  function formatTime(s: number): string {
    const m   = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, "0")}`;
  }

  async function startRecording() {
    setVoiceError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType = getBestMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
      mediaRecorderRef.current = recorder;
      audioChunksRef.current   = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        const blob = new Blob(audioChunksRef.current, { type: mimeType || "audio/webm" });
        await transcribeAudio(blob, mimeType || "audio/webm");
      };

      recorder.start(500);
      setIsRecording(true);
      setRecordingSeconds(0);
      timerRef.current = setInterval(() => setRecordingSeconds(s => s + 1), 1000);
    } catch (err: any) {
      if (err.name === "NotAllowedError") {
        setVoiceError("Microphone access denied. Please allow microphone access in your browser settings.");
      } else {
        setVoiceError("Could not access microphone. Please check your device settings.");
      }
    }
  }

  function stopRecording() {
    setIsRecording(false);
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    if (mediaRecorderRef.current?.state !== "inactive") mediaRecorderRef.current?.stop();
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
  }

  async function transcribeAudio(blob: Blob, mimeType: string) {
    setIsTranscribing(true);
    try {
      const ext      = mimeType.includes("webm") ? "webm" : mimeType.includes("ogg") ? "ogg" : "mp4";
      const formData = new FormData();
      formData.append("audio", blob, `recording.${ext}`);

      const res = await fetch(`${apiUrl}/mediation/voice/transcribe`, {
        method:  "POST",
        headers: { ...authHeader },
        body:    formData,
      });
      if (!res.ok) throw new Error("Transcription failed");

      const data       = await res.json();
      const transcript = (data.transcript || "").trim();
      if (transcript) {
        const current = statementRef.current;
        updateStatement(current + (current.trim() ? " " : "") + transcript);
        setHasUsedVoice(true);
        setFixStatus("idle");
      }
    } catch {
      setVoiceError("Transcription failed. Please check your connection and try again.");
    } finally {
      setIsTranscribing(false);
    }
  }

  async function fixTranscript() {
    if (!statement.trim() || correcting) return;
    setCorrecting(true);
    setFixStatus("idle");
    try {
      const res = await fetch(`${apiUrl}/mediation/voice/correct`, {
        method:  "POST",
        headers: { "Content-Type": "application/json", ...authHeader },
        body:    JSON.stringify({ text: statement }),
      });
      if (!res.ok) throw new Error("Server error");
      const data = await res.json();
      updateStatement(data.corrected);
      setFixStatus("fixed");
    } catch {
      setFixStatus("error");
    } finally {
      setCorrecting(false);
    }
  }

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleStatementNext = () => {
    if (statement.trim().length < 40) {
      setError("Please describe your situation in a bit more detail (at least 40 characters).");
      return;
    }
    setError(null);
    setStep(1);
  };

  const handleReliefSelect = (opt: ReliefOption) => {
    setRelief(opt);
    setError(null);
    setStep(2);
  };

  const handleRoleSelect = (r: "petitioner" | "respondent") => {
    setRole(r);
    setError(null);
    setStep(3);
  };

  const handleLocationSubmit = async () => {
    if (!location.trim()) {
      setError("Please enter your state or union territory.");
      return;
    }
    setError(null);
    await callAPI();
  };

  const callAPI = async () => {
    if (!relief || !role) return;
    setPhase("loading");
    setError(null);
    try {
      const res = await fetch(`${apiUrl}/case-outcome/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader },
        body: JSON.stringify({
          case_name:          `${relief.label} — ${location.trim()}`,
          case_type:          relief.case_type,
          year:               new Date().getFullYear(),
          jurisdiction_state: location.trim(),
          description:        statement.trim(),
          role:               role,
          relief_sought:      relief.label,
          is_appeal:          relief.is_appeal,
          damages_awarded:    0,
          parties_count:      2,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Server error ${res.status}`);
      }
      setPrediction(await res.json());
      setPhase("result");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Prediction failed. Please try again.");
      setPhase("form");
    }
  };

  const reset = () => {
    setPhase("form");
    setStep(0);
    setStatement("");
    setRelief(null);
    setRole(null);
    setLocation("");
    setPrediction(null);
    setError(null);
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <Layout>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 -mt-16 pt-24 pb-8">
        <div className="container mx-auto px-4 max-w-2xl">

          {/* Page header */}
          <div className="text-center mb-8 animate-fade-up">
            <div className="inline-flex items-center gap-2 bg-blue-100 text-blue-700 text-xs font-semibold px-3 py-1.5 rounded-full mb-3">
              <TrendingUp className="w-3.5 h-3.5" />
              Powered by InLegalBERT
            </div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
              Case Outcome Predictor
            </h1>
            <p className="text-muted-foreground text-sm">
              AI analysis trained on thousands of Indian Supreme Court &amp; High Court judgments
            </p>
          </div>

          {/* ── Loading ─────────────────────────────────────────────────────── */}
          {phase === "loading" && (
            <div className="rounded-2xl border-2 border-gray-200 bg-white shadow-xl p-12 text-center animate-fade-up">
              <div className="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center mx-auto mb-5">
                <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
              </div>
              <h2 className="text-xl font-bold text-gray-800 mb-2">Analysing your case…</h2>
              <p className="text-sm text-muted-foreground max-w-sm mx-auto leading-relaxed">
                We're converting your statement into legal language and running it
                through InLegalBERT. This takes a few seconds.
              </p>
            </div>
          )}

          {/* ── Result ──────────────────────────────────────────────────────── */}
          {phase === "result" && prediction && (
            <PredictionResult prediction={prediction} onReset={reset} />
          )}

          {/* ── Form ────────────────────────────────────────────────────────── */}
          {phase === "form" && (
            <div className="rounded-2xl border-2 border-gray-200 bg-white shadow-xl overflow-hidden animate-fade-up">

              {/* Progress header */}
              <div className="px-6 pt-6 pb-4 border-b border-gray-100">
                <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
                  <span className="font-medium text-gray-600">
                    Step {step + 1} of {STEP_LABELS.length}
                  </span>
                  <span>{progress}% complete</span>
                </div>
                <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-purple-600 rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <div className="flex items-center gap-2 mt-3 flex-wrap">
                  {STEP_LABELS.map((label, i) => (
                    <div
                      key={i}
                      className={`text-xs px-2.5 py-0.5 rounded-full font-medium transition-all ${
                        i === step   ? "bg-blue-100 text-blue-700"
                        : i < step  ? "bg-green-100 text-green-700"
                        : "bg-gray-100 text-gray-400"
                      }`}
                    >
                      {i < step ? "✓ " : ""}{label}
                    </div>
                  ))}
                </div>
              </div>

              {/* Step content */}
              <div className="p-6">

                {/* ── Step 0: Statement ─────────────────────────────────────── */}
                {step === 0 && (
                  <div className="space-y-5">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h2 className="text-2xl font-bold text-gray-800 leading-snug mb-2">
                          Tell us what happened
                        </h2>
                        <p className="text-sm text-gray-500 leading-relaxed">
                          Describe the situation in your own words — who is involved, what
                          the dispute or complaint is about, and what has happened so far.
                          The more detail you give, the more accurate the analysis.
                        </p>
                      </div>

                      {/* Voice button */}
                      {voiceSupported && !isTranscribing && (
                        <button
                          type="button"
                          onClick={isRecording ? stopRecording : startRecording}
                          title={isRecording ? "Stop recording" : "Speak your statement"}
                          className={`flex-shrink-0 flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-all mt-1 ${
                            isRecording
                              ? "bg-red-50 text-red-600 border-red-300 animate-pulse"
                              : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
                          }`}
                        >
                          {isRecording
                            ? <><MicOff className="w-3.5 h-3.5" /> Stop · {formatTime(recordingSeconds)}</>
                            : <><Mic className="w-3.5 h-3.5" /> Speak</>
                          }
                        </button>
                      )}
                      {isTranscribing && (
                        <span className="flex-shrink-0 flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-violet-200 bg-violet-50 text-violet-600 mt-1">
                          <Loader2 className="w-3.5 h-3.5 animate-spin" /> Transcribing…
                        </span>
                      )}
                    </div>

                    {error && (
                      <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-sm">
                        <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                        {error}
                      </div>
                    )}

                    <div className="space-y-2">
                      <textarea
                        ref={textareaRef}
                        rows={7}
                        value={statement}
                        onChange={e => updateStatement(e.target.value)}
                        onKeyDown={e => {
                          if (e.key === "Enter" && !e.shiftKey && statement.trim().length >= 40) {
                            e.preventDefault();
                            handleStatementNext();
                          }
                        }}
                        placeholder={
                          `Example:\n\n"My employer of 5 years terminated me without any notice or valid reason. ` +
                          `They refused to settle my pending salary dues or provide a written explanation. ` +
                          `I have all salary slips and my employment contract as evidence. ` +
                          `I want to recover my dues and seek legal remedy for wrongful termination."`
                        }
                        className={`w-full px-4 py-3 rounded-xl border-2 bg-white text-sm text-gray-800 placeholder:text-gray-300 focus:outline-none transition-colors resize-none leading-relaxed ${
                          isRecording
                            ? "border-red-300 ring-2 ring-red-100 focus:border-red-400"
                            : "border-gray-200 focus:border-blue-400"
                        }`}
                      />

                      {/* Recording indicator */}
                      {isRecording && (
                        <div className="flex items-center gap-2 text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                          <span className="flex-shrink-0 w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                          <span>Recording… speak clearly — <strong>{formatTime(recordingSeconds)}</strong></span>
                          <span className="ml-auto text-red-400">Press Stop when done</span>
                        </div>
                      )}

                      {/* Fix transcription button — shown after voice use, when not recording */}
                      {!isRecording && !isTranscribing && hasUsedVoice && (
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={fixTranscript}
                            disabled={correcting}
                            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-all disabled:opacity-60 ${
                              fixStatus === "fixed" ? "border-green-200 bg-green-50 text-green-700"
                              : fixStatus === "error" ? "border-red-200 bg-red-50 text-red-700"
                              : "border-violet-200 bg-violet-50 text-violet-700 hover:bg-violet-100"
                            }`}
                          >
                            {correcting
                              ? <><Loader2 className="w-3 h-3 animate-spin" /> Fixing…</>
                              : fixStatus === "fixed"
                              ? <><Check className="w-3 h-3" /> Fixed — fix again?</>
                              : fixStatus === "error"
                              ? <><Sparkles className="w-3 h-3" /> Retry fix</>
                              : <><Sparkles className="w-3 h-3" /> Fix transcription errors</>
                            }
                          </button>
                          <span className="text-xs text-gray-400">
                            {fixStatus === "error"
                              ? "Correction failed — check server"
                              : "AI corrects mishearings automatically"}
                          </span>
                        </div>
                      )}

                      {/* Voice error */}
                      {voiceError && (
                        <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                          {voiceError}
                        </p>
                      )}

                      <div className="flex items-center justify-between">
                        <p className="text-xs text-gray-400">
                          {statement.length < 40
                            ? `${40 - statement.length} more characters needed`
                            : `${statement.length} characters · Shift+Enter for new line`}
                        </p>
                        <button
                          onClick={handleStatementNext}
                          disabled={statement.trim().length < 40}
                          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-500 to-purple-600 text-white text-sm font-medium disabled:opacity-40 hover:shadow-lg transition-all"
                        >
                          <Send className="w-3.5 h-3.5" />
                          Continue
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* ── Step 1: Relief (prayer) ───────────────────────────────── */}
                {step === 1 && (
                  <div className="space-y-5">
                    <div>
                      <h2 className="text-2xl font-bold text-gray-800 leading-snug mb-2">
                        What are you asking the court for?
                      </h2>
                      <p className="text-sm text-gray-500">
                        Select the outcome that best represents what you want. This helps
                        the model understand the nature of your petition.
                      </p>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      {RELIEF_OPTIONS.map(opt => {
                        const a   = ACCENT[opt.accent];
                        const Icon = opt.icon;
                        return (
                          <button
                            key={opt.id}
                            onClick={() => handleReliefSelect(opt)}
                            className={`group text-left px-4 py-4 rounded-xl border-2 border-gray-200 bg-white transition-all ${a.border} ${a.hover}`}
                          >
                            <Icon className={`w-5 h-5 mb-2 transition-colors ${a.icon}`} />
                            <p className="text-sm font-semibold text-gray-700 leading-tight mb-1 group-hover:text-gray-900 transition-colors">
                              {opt.label}
                            </p>
                            <p className="text-xs text-gray-400 leading-snug">{opt.desc}</p>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* ── Step 2: Role ──────────────────────────────────────────── */}
                {step === 2 && (
                  <div className="space-y-5">
                    <div>
                      <h2 className="text-2xl font-bold text-gray-800 leading-snug mb-2">
                        In this matter, you are the…
                      </h2>
                      <p className="text-sm text-gray-500">
                        This tells the AI how to frame your statement — whether you
                        initiated the case or are defending against it.
                      </p>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <button
                        onClick={() => handleRoleSelect("petitioner")}
                        className="group text-left px-5 py-5 rounded-xl border-2 border-gray-200 bg-white hover:border-blue-400 hover:bg-blue-50 transition-all"
                      >
                        <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center mb-3 group-hover:bg-blue-200 transition-colors">
                          <Scale className="w-5 h-5 text-blue-600" />
                        </div>
                        <p className="text-sm font-bold text-gray-800 group-hover:text-blue-700 mb-1 transition-colors">
                          Complainant / Petitioner
                        </p>
                        <p className="text-xs text-gray-400 leading-snug">
                          You have filed or are planning to file this case. You are seeking
                          justice or relief from the court.
                        </p>
                      </button>
                      <button
                        onClick={() => handleRoleSelect("respondent")}
                        className="group text-left px-5 py-5 rounded-xl border-2 border-gray-200 bg-white hover:border-orange-400 hover:bg-orange-50 transition-all"
                      >
                        <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center mb-3 group-hover:bg-orange-200 transition-colors">
                          <ShieldAlert className="w-5 h-5 text-orange-600" />
                        </div>
                        <p className="text-sm font-bold text-gray-800 group-hover:text-orange-700 mb-1 transition-colors">
                          Accused / Respondent
                        </p>
                        <p className="text-xs text-gray-400 leading-snug">
                          A case has been filed against you. You are defending yourself or
                          responding to a complaint.
                        </p>
                      </button>
                    </div>
                  </div>
                )}

                {/* ── Step 3: Location ─────────────────────────────────────── */}
                {step === 3 && (
                  <div className="space-y-5">
                    <div>
                      <h2 className="text-2xl font-bold text-gray-800 leading-snug mb-2">
                        Which state are you based in?
                      </h2>
                      <p className="text-sm text-gray-500 leading-relaxed">
                        Jurisdiction determines which laws apply and how courts in that
                        region typically handle similar matters.
                      </p>
                    </div>

                    {error && (
                      <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-sm">
                        <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                        {error}
                      </div>
                    )}

                    <div className="flex gap-2">
                      <input
                        ref={locationRef}
                        type="text"
                        value={location}
                        onChange={e => { setLocation(e.target.value); setError(null); }}
                        onKeyDown={e => e.key === "Enter" && handleLocationSubmit()}
                        placeholder="e.g., Delhi, Maharashtra, Karnataka, Tamil Nadu"
                        className="flex-1 px-4 py-3 rounded-xl border-2 border-gray-200 bg-white text-sm text-gray-800 placeholder:text-gray-300 focus:outline-none focus:border-blue-400 transition-colors"
                      />
                      <button
                        onClick={handleLocationSubmit}
                        disabled={!location.trim()}
                        className="px-5 py-3 rounded-xl bg-gradient-to-r from-blue-500 to-purple-600 text-white text-sm font-medium disabled:opacity-40 hover:shadow-lg transition-all flex items-center gap-2 whitespace-nowrap"
                      >
                        Analyse <ArrowRight className="w-4 h-4" />
                      </button>
                    </div>

                    {/* Summary of collected answers */}
                    <div className="bg-gray-50 rounded-xl border border-gray-200 p-4 space-y-2">
                      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                        Summary before prediction
                      </p>
                      <div className="text-xs text-gray-600 space-y-1.5">
                        <p>
                          <span className="font-medium text-gray-700">You are:</span>{" "}
                          {role === "petitioner" ? "Complainant / Petitioner" : "Accused / Respondent"}
                        </p>
                        <p>
                          <span className="font-medium text-gray-700">Seeking:</span>{" "}
                          {relief?.label}
                        </p>
                        <p className="leading-relaxed">
                          <span className="font-medium text-gray-700">Statement:</span>{" "}
                          {statement.length > 120
                            ? statement.slice(0, 120) + "…"
                            : statement}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Back button */}
              {step > 0 && (
                <div className="px-6 pb-5">
                  <button
                    onClick={() => { setStep(s => s - 1); setError(null); }}
                    className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" /> Back
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Disclaimer */}
          {phase !== "loading" && (
            <p className="text-center text-xs text-gray-400 mt-5 px-4 leading-relaxed">
              Predictions are based on statistical patterns in historical Indian court judgments
              and are not legal advice. Always consult a qualified legal professional before
              taking action.
            </p>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default CasePredictor;
