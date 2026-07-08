import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  MessageSquare, TrendingUp, Scale,
  ArrowRight, Loader2, Sparkles, RotateCcw,
  Mic, MicOff, Check,
} from "lucide-react";
import { triageAgent, BASE_URL, type TriageResult } from "@/lib/api";

// ── Tool metadata ──────────────────────────────────────────────────────────────

const TOOLS = {
  chat: {
    icon:    MessageSquare,
    label:   "Legal Assistant",
    route:   "/chat",
    iconBg:  "bg-gradient-to-br from-blue-500 to-cyan-500",
    badgeBg: "bg-blue-50 border-blue-200 text-blue-700 dark:bg-blue-900/20 dark:border-blue-700/50 dark:text-blue-300",
    btnBg:   "from-blue-600 to-cyan-500 shadow-blue-300/50",
  },
  predict: {
    icon:    TrendingUp,
    label:   "Case Predictor",
    route:   "/predict",
    iconBg:  "bg-gradient-to-br from-violet-500 to-indigo-500",
    badgeBg: "bg-violet-50 border-violet-200 text-violet-700 dark:bg-violet-900/20 dark:border-violet-700/50 dark:text-violet-300",
    btnBg:   "from-violet-600 to-indigo-500 shadow-violet-300/50",
  },
  mediation: {
    icon:    Scale,
    label:   "AI Mediation",
    route:   "/mediation/create",
    iconBg:  "bg-gradient-to-br from-blue-600 to-indigo-600",
    badgeBg: "bg-indigo-50 border-indigo-200 text-indigo-700 dark:bg-indigo-900/20 dark:border-indigo-700/50 dark:text-indigo-300",
    btnBg:   "from-blue-600 to-indigo-600 shadow-indigo-300/50",
  },
} as const;

// ── Component ──────────────────────────────────────────────────────────────────

export default function AgentTriage() {
  const navigate = useNavigate();

  // ── Triage state ─────────────────────────────────────────────────────────
  const [text,    setText]    = useState("");
  const [loading, setLoading] = useState(false);
  const [result,  setResult]  = useState<TriageResult | null>(null);
  const [error,   setError]   = useState("");

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const textRef     = useRef("");   // mirror of `text` for async voice handlers

  // ── Voice state ───────────────────────────────────────────────────────────
  const [isRecording,      setIsRecording]      = useState(false);
  const [isTranscribing,   setIsTranscribing]   = useState(false);
  const [voiceSupported,   setVoiceSupported]   = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [voiceError,       setVoiceError]       = useState("");
  const [hasUsedVoice,     setHasUsedVoice]     = useState(false);
  const [correcting,       setCorrecting]       = useState(false);
  const [fixStatus,        setFixStatus]        = useState<"idle" | "fixed" | "error">("idle");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef   = useRef<Blob[]>([]);
  const streamRef        = useRef<MediaStream | null>(null);
  const timerRef         = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    setVoiceSupported(
      typeof MediaRecorder !== "undefined" &&
      !!navigator.mediaDevices?.getUserMedia,
    );
    return () => {
      if (mediaRecorderRef.current?.state !== "inactive")
        mediaRecorderRef.current?.stop();
      streamRef.current?.getTracks().forEach(t => t.stop());
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // ── Helpers ───────────────────────────────────────────────────────────────

  function updateText(value: string) {
    textRef.current = value;
    setText(value);
    setError("");
    setVoiceError("");
    setFixStatus("idle");
  }

  function getBestMimeType(): string {
    const candidates = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
      "audio/ogg",
      "audio/mp4",
    ];
    for (const t of candidates) {
      if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(t))
        return t;
    }
    return "";
  }

  function formatTime(s: number): string {
    const m = Math.floor(s / 60);
    return `${m}:${(s % 60).toString().padStart(2, "0")}`;
  }

  // ── Voice recording ───────────────────────────────────────────────────────

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
        const blob = new Blob(audioChunksRef.current, {
          type: mimeType || "audio/webm",
        });
        await transcribeAudio(blob, mimeType || "audio/webm");
      };

      recorder.start(500);
      setIsRecording(true);
      setRecordingSeconds(0);
      timerRef.current = setInterval(
        () => setRecordingSeconds(s => s + 1),
        1000,
      );
    } catch (err: any) {
      if (err.name === "NotAllowedError") {
        setVoiceError("Microphone access denied. Allow access in your browser settings.");
      } else {
        setVoiceError("Could not access microphone. Check your device settings.");
      }
    }
  }

  function stopRecording() {
    setIsRecording(false);
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    if (mediaRecorderRef.current?.state !== "inactive")
      mediaRecorderRef.current?.stop();
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
  }

  async function transcribeAudio(blob: Blob, mimeType: string) {
    setIsTranscribing(true);
    try {
      const ext = mimeType.includes("webm")
        ? "webm"
        : mimeType.includes("ogg") ? "ogg" : "mp4";

      const formData = new FormData();
      formData.append("audio", blob, `recording.${ext}`);

      const token = localStorage.getItem("sla_token");
      const res = await fetch(`${BASE_URL}/mediation/voice/transcribe`, {
        method:  "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body:    formData,
      });

      if (res.status === 401) {
        setVoiceError("Please sign in to use voice dictation.");
        return;
      }
      if (!res.ok) throw new Error("Transcription failed");

      const data = await res.json();
      const transcript = (data.transcript || "").trim();
      if (transcript) {
        const current = textRef.current;
        updateText(current + (current.trim() ? " " : "") + transcript);
        setHasUsedVoice(true);
        setFixStatus("idle");
      }
    } catch {
      setVoiceError("Transcription failed. Please check your connection and try again.");
    } finally {
      setIsTranscribing(false);
    }
  }

  // ── Fix transcription ─────────────────────────────────────────────────────

  async function fixTranscript() {
    if (!text.trim() || correcting) return;
    setCorrecting(true);
    setFixStatus("idle");
    try {
      const token = localStorage.getItem("sla_token");
      const res = await fetch(`${BASE_URL}/mediation/voice/correct`, {
        method:  "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ text: text }),
      });
      if (!res.ok) throw new Error("Server error");
      const data = await res.json();
      updateText(data.corrected);
      setFixStatus("fixed");
    } catch {
      setFixStatus("error");
    } finally {
      setCorrecting(false);
    }
  }

  // ── Submit ────────────────────────────────────────────────────────────────

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || loading || isRecording || isTranscribing) return;

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await triageAgent(trimmed);
      setResult(res);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  }

  function handleOpen() {
    if (!result) return;
    sessionStorage.setItem("agent_prefill", result.prefill_text);
    navigate(TOOLS[result.tool].route);
  }

  function handleReset() {
    setResult(null);
    setError("");
    setVoiceError("");
    setHasUsedVoice(false);
    setFixStatus("idle");
    setTimeout(() => textareaRef.current?.focus(), 60);
  }

  // ── Render ────────────────────────────────────────────────────────────────

  const tool     = result ? TOOLS[result.tool] : null;
  const ToolIcon = tool?.icon;

  return (
    <div className="w-full max-w-xl mx-auto">

      {/* ── Form state ──────────────────────────────────────────────────── */}
      {!result && (
        <form onSubmit={handleSubmit} className="space-y-2.5">

          {/* Textarea */}
          <div className="relative">
            <textarea
              ref={textareaRef}
              value={text}
              onChange={e => updateText(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={3}
              disabled={isRecording || isTranscribing}
              placeholder={
                'Describe your legal situation in plain language…\n' +
                'e.g. "My employer fired me without notice" or "Will I get bail?"'
              }
              className={`w-full px-4 py-3.5 text-sm rounded-2xl border bg-white/90 backdrop-blur-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-400/50 focus:border-blue-300 transition-all resize-none shadow-sm dark:bg-slate-800/80 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:border-blue-500/60 ${
                isRecording
                  ? "border-red-300 ring-2 ring-red-100 dark:border-red-500/60 dark:ring-red-500/20"
                  : "border-slate-200/80 dark:border-slate-600/80"
              }`}
            />

            {/* Recording pulse indicator */}
            {isRecording && (
              <div className="absolute bottom-2.5 left-3 flex items-center gap-1.5 text-xs text-red-500 pointer-events-none">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse flex-shrink-0" />
                Recording · {formatTime(recordingSeconds)}
              </div>
            )}

            {/* Transcribing indicator */}
            {isTranscribing && (
              <div className="absolute bottom-2.5 left-3 flex items-center gap-1.5 text-xs text-violet-500 pointer-events-none">
                <Loader2 className="h-3.5 w-3.5 animate-spin flex-shrink-0" />
                Transcribing…
              </div>
            )}

            {!isRecording && !isTranscribing && (
              <p className="absolute bottom-2.5 right-3 text-[10px] text-slate-300 dark:text-slate-600 pointer-events-none select-none">
                Enter ↵ to submit
              </p>
            )}
          </div>

          {/* Fix transcription button — shown after voice use, when not recording/transcribing */}
          {!isRecording && !isTranscribing && hasUsedVoice && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={fixTranscript}
                disabled={correcting}
                className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-all disabled:opacity-60 ${
                  fixStatus === "fixed"
                    ? "border-green-200 bg-green-50 text-green-700 dark:border-green-700/50 dark:bg-green-900/20 dark:text-green-400"
                    : fixStatus === "error"
                    ? "border-red-200 bg-red-50 text-red-700 dark:border-red-700/50 dark:bg-red-900/20 dark:text-red-400"
                    : "border-violet-200 bg-violet-50 text-violet-700 hover:bg-violet-100 dark:border-violet-700/50 dark:bg-violet-900/20 dark:text-violet-400 dark:hover:bg-violet-900/40"
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
              <span className="text-xs text-slate-400 dark:text-slate-500">
                {fixStatus === "error"
                  ? "Correction failed — check your connection"
                  : "AI corrects mishearings automatically"}
              </span>
            </div>
          )}

          {/* Error messages */}
          {(voiceError || error) && (
            <p className="text-xs text-red-500 px-1">{voiceError || error}</p>
          )}

          {/* Action row: mic + submit */}
          <div className="flex gap-2">

            {/* Voice button — shown if supported */}
            {voiceSupported && !isTranscribing && (
              <button
                type="button"
                onClick={isRecording ? stopRecording : startRecording}
                title={isRecording ? "Stop recording" : "Dictate your situation"}
                className={`flex-shrink-0 inline-flex items-center justify-center gap-1.5 rounded-full border px-3.5 py-2.5 text-xs font-semibold transition-all duration-200 ${
                  isRecording
                    ? "border-red-300 bg-red-50 text-red-600 hover:bg-red-100 dark:border-red-500/50 dark:bg-red-900/20 dark:text-red-400"
                    : "border-slate-200 bg-white text-slate-500 hover:border-slate-300 hover:text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800/60 dark:text-slate-400 dark:hover:bg-slate-700"
                }`}
              >
                {isRecording ? (
                  <>
                    <MicOff className="h-4 w-4" />
                    Stop · {formatTime(recordingSeconds)}
                  </>
                ) : (
                  <Mic className="h-4 w-4" />
                )}
              </button>
            )}

            {/* Transcribing pill (replaces mic button while transcribing) */}
            {isTranscribing && (
              <span className="flex-shrink-0 inline-flex items-center gap-1.5 rounded-full border border-violet-200 bg-violet-50 px-3.5 py-2.5 text-xs font-semibold text-violet-600 dark:border-violet-500/40 dark:bg-violet-900/20 dark:text-violet-400">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Transcribing
              </span>
            )}

            {/* Submit button */}
            <button
              type="submit"
              disabled={!text.trim() || loading || isRecording || isTranscribing}
              className="group flex-1 inline-flex items-center justify-center gap-2 rounded-full bg-gradient-to-r from-blue-600 to-cyan-500 px-6 py-3 text-sm font-bold text-white shadow-lg shadow-blue-300/50 hover:shadow-xl hover:shadow-blue-300/60 hover:scale-[1.02] hover:-translate-y-0.5 transition-all duration-300 disabled:opacity-50 disabled:pointer-events-none"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Finding…
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  Find the right tool
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </>
              )}
            </button>
          </div>
        </form>
      )}

      {/* ── Result state ─────────────────────────────────────────────────── */}
      {result && tool && ToolIcon && (
        <div className="rounded-2xl border border-slate-200/80 bg-white/90 backdrop-blur-sm shadow-lg p-5 space-y-4 dark:bg-slate-800/80 dark:border-slate-600/80">

          {/* Header */}
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-blue-500 flex-shrink-0" />
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest dark:text-slate-400">
              Based on your situation
            </p>
          </div>

          {/* Tool card */}
          <div className={`flex items-start gap-4 rounded-xl border p-4 ${tool.badgeBg}`}>
            <div className={`w-10 h-10 rounded-xl ${tool.iconBg} flex items-center justify-center flex-shrink-0 shadow-md`}>
              <ToolIcon className="h-5 w-5 text-white" />
            </div>
            <div className="min-w-0">
              <p className="font-bold text-sm text-slate-900 dark:text-white mb-0.5">{tool.label}</p>
              <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-300">{result.reason}</p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-2 pt-1">
            <button
              onClick={handleOpen}
              className={`group flex-1 inline-flex items-center justify-center gap-2 rounded-full bg-gradient-to-r ${tool.btnBg} px-5 py-3 text-sm font-bold text-white shadow-lg hover:shadow-xl hover:scale-[1.02] transition-all duration-200`}
            >
              Open {tool.label}
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </button>
            <button
              onClick={handleReset}
              className="inline-flex items-center justify-center gap-1.5 rounded-full border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-600 hover:border-slate-300 hover:bg-slate-50 transition-all dark:border-slate-600 dark:bg-slate-700/50 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Try again
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
