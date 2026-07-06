import { useState, useRef, useEffect, useCallback } from "react";
import {
  Send, Bot, User, Loader2, Plus, Trash2, MessageSquare,
  Menu, X, Scale, Mic, MicOff, PhoneCall, Volume2, Wand2,
} from "lucide-react";
import Header from "../components/Header";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface ConvSummary {
  id: string;
  title: string;
  created_at: string;
  message_count: number;
}

type VoiceConvState = "listening" | "processing" | "speaking";

// ── Constants ─────────────────────────────────────────────────────────────────

const SUGGESTIONS = [
  "What are my rights as a tenant in India?",
  "Explain the RTI Act 2005 and how to file an application",
  "What is Section 498A of the IPC?",
  "How do I file a consumer complaint against a company?",
];

// ── Utility: best supported audio MIME type ───────────────────────────────────

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

function mimeToExt(mimeType: string): string {
  if (mimeType.includes("webm")) return "webm";
  if (mimeType.includes("ogg"))  return "ogg";
  return "mp4";
}

// ── Component ─────────────────────────────────────────────────────────────────

const ChatPage = () => {

  // ── Conversation state ──────────────────────────────────────────────────────
  const [conversations, setConversations] = useState<ConvSummary[]>([]);
  const [activeConvId, setActiveConvId]   = useState<string | null>(null);
  const [messages, setMessages]           = useState<ChatMessage[]>([]);
  const [inputText, setInputText]         = useState("");
  const [isLoading, setIsLoading]         = useState(false);
  const [sidebarOpen, setSidebarOpen]     = useState(false);

  // ── Voice dictation state ───────────────────────────────────────────────────
  const [isDictating, setIsDictating]       = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [hasUsedVoice, setHasUsedVoice]     = useState(false);
  const [fixStatus, setFixStatus]           = useState<"idle" | "fixing" | "fixed" | "error">("idle");
  const [dictError, setDictError]           = useState("");

  // ── Voice conversation state ────────────────────────────────────────────────
  const [isVoiceConvOpen, setIsVoiceConvOpen]           = useState(false);
  const [voiceConvStateUI, setVoiceConvStateUI]         = useState<VoiceConvState>("listening");
  const [voiceConvTranscript, setVoiceConvTranscript]   = useState("");
  const [voiceConvError, setVoiceConvError]             = useState("");

  // ── Core refs ────────────────────────────────────────────────────────────────
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef       = useRef<HTMLInputElement>(null);
  const activeConvRef  = useRef<string | null>(null);

  // ── Dictation refs ────────────────────────────────────────────────────────────
  const dictRecorderRef  = useRef<MediaRecorder | null>(null);
  const dictChunksRef    = useRef<Blob[]>([]);
  const dictStreamRef    = useRef<MediaStream | null>(null);
  const dictMimeRef      = useRef<string>("");

  // ── Voice conversation refs (avoids stale closures in async loops & RAF) ────
  const vcActiveRef      = useRef(false);                    // true while overlay is open
  const vcStateRef       = useRef<VoiceConvState>("listening"); // mirror of UI state
  const vcRecorderRef    = useRef<MediaRecorder | null>(null);
  const vcChunksRef      = useRef<Blob[]>([]);
  const vcStreamRef      = useRef<MediaStream | null>(null);
  const vcMimeRef        = useRef<string>("");
  const vcAudioCtxRef    = useRef<AudioContext | null>(null);
  const vcAnalyserRef    = useRef<AnalyserNode | null>(null);
  const vcSilenceTimer   = useRef<ReturnType<typeof setTimeout> | null>(null);
  const vcRafId          = useRef<number | null>(null);

  const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

  // ── Header factories ──────────────────────────────────────────────────────────

  // JSON requests — includes Content-Type
  const authHeaders = useCallback((): Record<string, string> => {
    const token = localStorage.getItem("sla_token");
    return token
      ? { "Content-Type": "application/json", Authorization: `Bearer ${token}` }
      : { "Content-Type": "application/json" };
  }, []);

  // FormData requests — browser sets Content-Type with boundary automatically
  const authOnlyHeaders = useCallback((): Record<string, string> => {
    const token = localStorage.getItem("sla_token");
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, []);

  // ── State sync helpers ────────────────────────────────────────────────────────

  // Keep conversation id ref in sync so async callbacks read the latest value
  useEffect(() => { activeConvRef.current = activeConvId; }, [activeConvId]);

  // Mirror voice conv UI state into ref so RAF/async callbacks read it without stale closure
  function setVoiceConvState(s: VoiceConvState) {
    vcStateRef.current = s;
    setVoiceConvStateUI(s);
  }

  // ── Lifecycle ─────────────────────────────────────────────────────────────────

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    fetchConversations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Clean up voice conv resources when component unmounts
  useEffect(() => {
    return () => { cleanupVoiceConv(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── MongoDB API helpers ───────────────────────────────────────────────────────

  async function fetchConversations() {
    try {
      const res = await fetch(`${apiUrl}/conversations?limit=50`, { headers: authOnlyHeaders() });
      if (!res.ok) return;
      const data: any[] = await res.json();
      setConversations(
        data.map(c => ({
          id: c._id ?? c.id,
          title: c.title,
          created_at: c.created_at,
          message_count: c.message_count ?? 0,
        }))
      );
    } catch { /* network error — sidebar stays empty, chat still works */ }
  }

  async function createConversation(title: string): Promise<string | null> {
    try {
      const res = await fetch(`${apiUrl}/conversations`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ title }),
      });
      if (!res.ok) return null;
      const data = await res.json();
      return data._id ?? data.id ?? null;
    } catch { return null; }
  }

  async function loadConversation(id: string) {
    try {
      const res = await fetch(`${apiUrl}/conversations/${id}`, { headers: authOnlyHeaders() });
      if (!res.ok) return;
      const data = await res.json();
      if (data.messages) {
        setMessages(
          data.messages.map((m: any, i: number) => ({
            id: `${id}-${i}`,
            role: m.role as "user" | "assistant",
            content: m.content,
            timestamp: new Date(m.timestamp),
          }))
        );
      }
    } catch { /* leave messages as-is */ }
  }

  async function appendMessage(convId: string, role: string, content: string) {
    try {
      await fetch(`${apiUrl}/conversations/${convId}/messages`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ role, content }),
      });
    } catch { /* fire-and-forget; UI already updated */ }
  }

  async function callQuery(query: string): Promise<string> {
    const controller = new AbortController();
    const tid = setTimeout(() => controller.abort(), 60_000);
    try {
      const res = await fetch(`${apiUrl}/query`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ query }),
        signal: controller.signal,
      });
      clearTimeout(tid);
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const data = await res.json();
      return data.summary || "I can help with that. Could you provide more details?";
    } catch (e) {
      clearTimeout(tid);
      if (e instanceof Error && e.name === "AbortError")
        return "The request timed out. Please try again.";
      return "Sorry, I couldn't reach the server. Please try again.";
    }
  }

  // ── Chat actions ──────────────────────────────────────────────────────────────

  async function handleSend() {
    const text = inputText.trim();
    if (!text || isLoading) return;
    setInputText("");
    setIsLoading(true);
    setHasUsedVoice(false);
    setFixStatus("idle");

    let convId = activeConvRef.current;
    if (!convId) {
      const shortTitle = text.length > 60 ? text.slice(0, 57) + "…" : text;
      const newId = await createConversation(shortTitle);
      if (newId) {
        convId = newId;
        setActiveConvId(newId);
        activeConvRef.current = newId;
        setConversations(prev => [
          { id: newId, title: shortTitle, created_at: new Date().toISOString(), message_count: 0 },
          ...prev,
        ]);
      }
    }

    const userMsg: ChatMessage = { id: Date.now().toString(), role: "user", content: text, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);

    const reply = await callQuery(text);
    const botMsg: ChatMessage = { id: (Date.now() + 1).toString(), role: "assistant", content: reply, timestamp: new Date() };
    setMessages(prev => [...prev, botMsg]);

    if (convId) {
      appendMessage(convId, "user", text);
      appendMessage(convId, "assistant", reply);
    }
    setIsLoading(false);
  }

  async function handleSelectConversation(id: string) {
    if (id === activeConvRef.current) { setSidebarOpen(false); return; }
    setActiveConvId(id);
    setMessages([]);
    setHasUsedVoice(false);
    setFixStatus("idle");
    setIsLoading(true);
    setSidebarOpen(false);
    await loadConversation(id);
    setIsLoading(false);
  }

  function handleNewChat() {
    setActiveConvId(null);
    setMessages([]);
    setSidebarOpen(false);
    setHasUsedVoice(false);
    setFixStatus("idle");
    setInputText("");
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  async function handleDeleteConv(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await fetch(`${apiUrl}/conversations/${id}`, { method: "DELETE", headers: authOnlyHeaders() });
    } catch { /* ignore */ }
    setConversations(prev => prev.filter(c => c.id !== id));
    if (activeConvRef.current === id) { setActiveConvId(null); setMessages([]); }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }

  // ── Voice Dictation ───────────────────────────────────────────────────────────

  async function startDictation() {
    setDictError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      dictStreamRef.current = stream;
      const mimeType = getBestMimeType();
      dictMimeRef.current = mimeType;
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
      dictChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) dictChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        const blob = new Blob(dictChunksRef.current, { type: dictMimeRef.current || "audio/webm" });
        stream.getTracks().forEach(t => t.stop());
        dictStreamRef.current = null;
        await transcribeDictation(blob, dictMimeRef.current || "audio/webm");
      };

      // 500 ms timeslice — fires ondataavailable every 500 ms for reliability
      // (enables recording up to Groq Whisper's ~25 min / 25 MB limit)
      recorder.start(500);
      dictRecorderRef.current = recorder;
      setIsDictating(true);
    } catch {
      setDictError("Microphone access denied. Please allow microphone permission and try again.");
    }
  }

  function stopDictation() {
    if (dictRecorderRef.current && dictRecorderRef.current.state !== "inactive") {
      dictRecorderRef.current.stop();
    }
    dictRecorderRef.current = null;
    setIsDictating(false);
  }

  function toggleDictation() {
    if (isDictating) stopDictation();
    else startDictation();
  }

  async function transcribeDictation(blob: Blob, mimeType: string) {
    setIsTranscribing(true);
    try {
      const formData = new FormData();
      formData.append("audio", blob, `recording.${mimeToExt(mimeType)}`);

      const res = await fetch(`${apiUrl}/mediation/voice/transcribe`, {
        method: "POST",
        headers: authOnlyHeaders(),   // NO Content-Type — browser sets multipart boundary
        body: formData,
      });
      if (!res.ok) throw new Error("Transcription failed");

      const data = await res.json();
      const transcript = (data.transcript || "").trim();
      if (transcript) {
        // Append to whatever is already in the input (allows sequential recordings)
        setInputText(prev => prev + (prev.trim() ? " " : "") + transcript);
        setHasUsedVoice(true);
        setFixStatus("idle");
      }
    } catch {
      setDictError("Transcription failed. Please check your connection and try again.");
    } finally {
      setIsTranscribing(false);
    }
  }

  async function fixTranscript() {
    if (!inputText.trim() || fixStatus === "fixing") return;
    setFixStatus("fixing");
    try {
      const res = await fetch(`${apiUrl}/mediation/voice/correct`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ text: inputText }),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setInputText(data.corrected);
      setFixStatus("fixed");
    } catch {
      setFixStatus("error");
    }
  }

  // ── Voice Conversation ────────────────────────────────────────────────────────

  function cleanupVoiceConv() {
    vcActiveRef.current = false;

    // Stop recorder
    if (vcRecorderRef.current && vcRecorderRef.current.state !== "inactive") {
      try { vcRecorderRef.current.stop(); } catch { /* ignore */ }
    }
    vcRecorderRef.current = null;
    vcChunksRef.current = [];

    // Stop audio stream
    vcStreamRef.current?.getTracks().forEach(t => t.stop());
    vcStreamRef.current = null;

    // Close AudioContext
    vcAudioCtxRef.current?.close().catch(() => {/* ignore */});
    vcAudioCtxRef.current = null;
    vcAnalyserRef.current = null;

    // Clear silence detection timer and animation frame
    if (vcSilenceTimer.current) { clearTimeout(vcSilenceTimer.current); vcSilenceTimer.current = null; }
    if (vcRafId.current) { cancelAnimationFrame(vcRafId.current); vcRafId.current = null; }

    // Cancel any in-flight speech synthesis
    window.speechSynthesis?.cancel();
  }

  async function startVoiceConversation() {
    setVoiceConvError("");
    setVoiceConvTranscript("");
    setIsVoiceConvOpen(true);
    vcActiveRef.current = true;
    await startVoiceConvListening();
  }

  function stopVoiceConversation() {
    cleanupVoiceConv();
    setIsVoiceConvOpen(false);
    setVoiceConvTranscript("");
    setVoiceConvError("");
  }

  async function startVoiceConvListening() {
    if (!vcActiveRef.current) return;
    setVoiceConvState("listening");
    setVoiceConvTranscript("");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      vcStreamRef.current = stream;

      const mimeType = getBestMimeType();
      vcMimeRef.current = mimeType;
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
      vcChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) vcChunksRef.current.push(e.data);
      };

      // onstop fires after silence detection stops the recorder
      recorder.onstop = async () => {
        if (!vcActiveRef.current) return;
        const blob = new Blob(vcChunksRef.current, { type: vcMimeRef.current || "audio/webm" });
        stream.getTracks().forEach(t => t.stop());
        vcStreamRef.current = null;
        await processVoiceConvAudio(blob);
      };

      // 500 ms timeslice for the same reliability benefit as dictation
      recorder.start(500);
      vcRecorderRef.current = recorder;

      // ── Silence detection via Web Audio AnalyserNode ──────────────────────
      const audioCtx = new AudioContext();
      vcAudioCtxRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);
      vcAnalyserRef.current = analyser;

      const freqBuffer = new Uint8Array(analyser.frequencyBinCount);
      const SILENCE_THRESHOLD = 15;   // 0–255 frequency magnitude
      const SILENCE_DURATION  = 1500; // ms of silence before auto-stop

      function checkSilence() {
        // Exit if conversation ended or state changed away from listening
        if (!vcActiveRef.current || vcStateRef.current !== "listening") return;
        if (!vcAnalyserRef.current) return;

        vcAnalyserRef.current.getByteFrequencyData(freqBuffer);
        const avg = freqBuffer.reduce((a, b) => a + b, 0) / freqBuffer.length;

        if (avg < SILENCE_THRESHOLD) {
          // Silence — start timer if not already running
          if (!vcSilenceTimer.current) {
            vcSilenceTimer.current = setTimeout(() => {
              vcSilenceTimer.current = null;
              // Cancel RAF before stopping recorder to avoid stale reads
              if (vcRafId.current) { cancelAnimationFrame(vcRafId.current); vcRafId.current = null; }
              if (vcActiveRef.current && vcRecorderRef.current?.state === "recording") {
                vcRecorderRef.current.stop();
                vcRecorderRef.current = null;
              }
              vcAudioCtxRef.current?.close().catch(() => {/* ignore */});
              vcAudioCtxRef.current = null;
              vcAnalyserRef.current = null;
            }, SILENCE_DURATION);
          }
        } else {
          // Voice detected — cancel any pending silence timer
          if (vcSilenceTimer.current) {
            clearTimeout(vcSilenceTimer.current);
            vcSilenceTimer.current = null;
          }
        }

        vcRafId.current = requestAnimationFrame(checkSilence);
      }

      vcRafId.current = requestAnimationFrame(checkSilence);

    } catch {
      setVoiceConvError("Microphone access denied. Please allow permission and try again.");
      vcActiveRef.current = false;
      setIsVoiceConvOpen(false);
    }
  }

  async function processVoiceConvAudio(blob: Blob) {
    if (!vcActiveRef.current) return;
    setVoiceConvState("processing");

    // ── Transcribe the recorded audio ─────────────────────────────────────────
    let transcript = "";
    try {
      const formData = new FormData();
      formData.append("audio", blob, `recording.${mimeToExt(vcMimeRef.current || "audio/webm")}`);
      const res = await fetch(`${apiUrl}/mediation/voice/transcribe`, {
        method: "POST",
        headers: authOnlyHeaders(),
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        transcript = (data.transcript || "").trim();
      }
    } catch { /* ignore — treat as empty */ }

    if (!vcActiveRef.current) return;

    // If nothing was heard, go straight back to listening
    if (!transcript) {
      await startVoiceConvListening();
      return;
    }

    setVoiceConvTranscript(transcript);

    // ── Add user message to chat (same as typed send) ──────────────────────────
    let convId = activeConvRef.current;
    if (!convId) {
      const shortTitle = transcript.length > 60 ? transcript.slice(0, 57) + "…" : transcript;
      const newId = await createConversation(shortTitle);
      if (newId) {
        convId = newId;
        setActiveConvId(newId);
        activeConvRef.current = newId;
        setConversations(prev => [
          { id: newId, title: shortTitle, created_at: new Date().toISOString(), message_count: 0 },
          ...prev,
        ]);
      }
    }

    const userMsg: ChatMessage = { id: Date.now().toString(), role: "user", content: transcript, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);

    // ── Get AI reply ──────────────────────────────────────────────────────────
    const reply = await callQuery(transcript);
    if (!vcActiveRef.current) return;

    const botMsg: ChatMessage = { id: (Date.now() + 1).toString(), role: "assistant", content: reply, timestamp: new Date() };
    setMessages(prev => [...prev, botMsg]);

    // Persist to MongoDB
    if (convId) {
      appendMessage(convId, "user", transcript);
      appendMessage(convId, "assistant", reply);
    }

    // ── Speak the reply via browser TTS ───────────────────────────────────────
    setVoiceConvState("speaking");
    // Show a preview of the reply in the overlay (truncated)
    setVoiceConvTranscript(reply.length > 140 ? reply.slice(0, 137) + "…" : reply);

    await new Promise<void>((resolve) => {
      if (!vcActiveRef.current) { resolve(); return; }
      const utterance = new SpeechSynthesisUtterance(reply);
      utterance.lang  = "en-IN";
      utterance.rate  = 0.95;
      utterance.onend   = () => resolve();
      // onerror fires with "interrupted" when speechSynthesis.cancel() is called
      utterance.onerror = () => resolve();
      window.speechSynthesis.speak(utterance);
    });

    // ── Loop — go back to listening ───────────────────────────────────────────
    if (vcActiveRef.current) {
      await startVoiceConvListening();
    }
  }

  // ── Derived UI labels ─────────────────────────────────────────────────────────

  const fixButtonLabel =
    fixStatus === "fixing" ? "Fixing…"           :
    fixStatus === "fixed"  ? "Fixed — fix again?":
    fixStatus === "error"  ? "Retry fix"         :
    "Fix transcription errors";

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-screen bg-white dark:bg-[#060d1a] overflow-hidden">

      {/* App header */}
      <Header />

      {/* ── Voice Conversation Overlay ────────────────────────────────────────── */}
      {isVoiceConvOpen && (
        <div className="fixed inset-0 z-50 bg-black/95 flex flex-col items-center justify-center select-none">

          {/* Animated orb */}
          <div className="relative w-52 h-52 flex items-center justify-center mb-8">

            {/* Outer pulsing rings */}
            {voiceConvStateUI === "listening" && (
              <>
                <div
                  className="absolute inset-0 rounded-full bg-blue-500/15 animate-ping"
                  style={{ animationDuration: "1.6s" }}
                />
                <div
                  className="absolute inset-8 rounded-full bg-blue-500/20 animate-ping"
                  style={{ animationDuration: "2s", animationDelay: "0.4s" }}
                />
              </>
            )}
            {voiceConvStateUI === "speaking" && (
              <>
                <div
                  className="absolute inset-0 rounded-full bg-green-500/15 animate-ping"
                  style={{ animationDuration: "1.2s" }}
                />
                <div
                  className="absolute inset-8 rounded-full bg-green-500/20 animate-ping"
                  style={{ animationDuration: "1.6s", animationDelay: "0.2s" }}
                />
              </>
            )}

            {/* Center orb */}
            <div
              className={`w-28 h-28 rounded-full flex items-center justify-center shadow-2xl transition-all duration-500 ${
                voiceConvStateUI === "listening"
                  ? "bg-gradient-to-br from-blue-500 to-indigo-600 shadow-blue-500/50"
                  : voiceConvStateUI === "processing"
                  ? "bg-gradient-to-br from-slate-600 to-slate-700 shadow-slate-700/50"
                  : "bg-gradient-to-br from-green-500 to-emerald-600 shadow-green-500/50"
              }`}
            >
              {voiceConvStateUI === "listening"  && <Mic       className="h-12 w-12 text-white" />}
              {voiceConvStateUI === "processing" && <Loader2   className="h-12 w-12 text-white animate-spin" />}
              {voiceConvStateUI === "speaking"   && <Volume2   className="h-12 w-12 text-white" />}
            </div>
          </div>

          {/* State label */}
          <p className="text-white text-xl font-semibold mb-3 tracking-tight">
            {voiceConvStateUI === "listening"  ? "Listening…"  :
             voiceConvStateUI === "processing" ? "Processing…" :
             "Speaking…"}
          </p>

          {/* Transcript preview */}
          {voiceConvTranscript ? (
            <p className="text-slate-400 text-sm max-w-xs text-center px-6 leading-relaxed mb-1">
              {voiceConvTranscript}
            </p>
          ) : null}

          {/* Hint text */}
          {voiceConvStateUI === "listening" && (
            <p className="text-slate-600 text-xs mt-1 mb-6">
              Stops automatically after ~1.5 s of silence
            </p>
          )}

          {/* Error */}
          {voiceConvError && (
            <p className="text-red-400 text-sm mt-2 mb-4">{voiceConvError}</p>
          )}

          {/* End button */}
          <button
            onClick={stopVoiceConversation}
            className="mt-6 flex items-center gap-2 px-5 py-2.5 rounded-full bg-white/10 hover:bg-white/20 text-white text-sm font-medium transition-colors border border-white/10"
          >
            <X className="h-4 w-4" />
            End conversation
          </button>
        </div>
      )}

      {/* Body: sidebar + main */}
      <div className="flex flex-1 min-h-0">

        {/* Mobile backdrop */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-20 bg-black/40 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* ── Sidebar ────────────────────────────────────────────────────────── */}
        <aside
          className={`
            flex flex-col w-64 flex-shrink-0
            border-r border-slate-200 dark:border-slate-700/50
            bg-slate-50 dark:bg-[#0a0f1e]
            fixed inset-y-0 left-0 z-30 transition-transform duration-300
            md:relative md:translate-x-0
            ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
          `}
          style={{ top: "56px" }}
        >
          {/* New chat button */}
          <div className="p-3 flex-shrink-0">
            <button
              onClick={handleNewChat}
              className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:border-blue-300 dark:hover:border-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-colors"
            >
              <Plus className="h-4 w-4" />
              New chat
            </button>
          </div>

          {/* Conversation list */}
          <div className="flex-1 overflow-y-auto px-2 pb-4">
            {conversations.length === 0 ? (
              <p className="text-xs text-slate-400 dark:text-slate-600 text-center mt-10 px-4 leading-relaxed">
                No conversations yet.<br />Start a new chat above.
              </p>
            ) : (
              <>
                <p className="text-[10px] font-semibold text-slate-400 dark:text-slate-600 uppercase tracking-wider px-2 mb-1 mt-1">
                  Recent
                </p>
                {conversations.map(conv => (
                  <div
                    key={conv.id}
                    onClick={() => handleSelectConversation(conv.id)}
                    className={`group relative flex items-center gap-2 px-3 py-2 mb-0.5 rounded-lg cursor-pointer text-sm transition-colors ${
                      activeConvId === conv.id
                        ? "bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                        : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-200"
                    }`}
                  >
                    <MessageSquare className="h-3.5 w-3.5 flex-shrink-0 opacity-50" />
                    <span className="flex-1 truncate min-w-0">{conv.title}</span>
                    <button
                      onClick={e => handleDeleteConv(conv.id, e)}
                      className="opacity-0 group-hover:opacity-100 flex-shrink-0 p-0.5 rounded transition-all hover:text-red-500 dark:hover:text-red-400"
                      aria-label="Delete conversation"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </>
            )}
          </div>
        </aside>

        {/* ── Main panel ─────────────────────────────────────────────────────── */}
        <main className="flex-1 flex flex-col min-w-0 bg-white dark:bg-[#060d1a]">

          {/* Mobile top bar */}
          <div className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-slate-200 dark:border-slate-700/50 flex-shrink-0">
            <button
              onClick={() => setSidebarOpen(o => !o)}
              className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800 transition-colors"
            >
              {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300 truncate">
              {activeConvId
                ? conversations.find(c => c.id === activeConvId)?.title ?? "Conversation"
                : "Legal Assistant"}
            </span>
          </div>

          {/* Messages — scrolls internally */}
          <div className="flex-1 overflow-y-auto">

            {messages.length === 0 ? (
              /* ── Empty / welcome state ───────────────────────────────────── */
              <div className="h-full flex flex-col items-center justify-center p-8 text-center">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center mb-4 shadow-lg">
                  <Scale className="h-7 w-7 text-white" />
                </div>
                <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
                  Smart Legal Assistant
                </h2>
                <p className="text-sm text-slate-500 dark:text-slate-400 mb-8 max-w-sm leading-relaxed">
                  Ask any legal question about Indian law — rights, disputes, procedures, or consequences.
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
                  {SUGGESTIONS.map(s => (
                    <button
                      key={s}
                      onClick={() => { setInputText(s); setTimeout(() => inputRef.current?.focus(), 50); }}
                      className="text-left px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 text-sm text-slate-700 dark:text-slate-300 hover:border-blue-300 dark:hover:border-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>

            ) : (
              /* ── Messages ────────────────────────────────────────────────── */
              <div className="max-w-3xl mx-auto w-full px-4 py-6 space-y-6">
                {messages.map(msg => (
                  <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
                    <div
                      className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                        msg.role === "user"
                          ? "bg-gradient-to-br from-blue-500 to-purple-500"
                          : "bg-gradient-to-br from-teal-400 to-blue-500"
                      }`}
                    >
                      {msg.role === "user"
                        ? <User className="h-4 w-4 text-white" />
                        : <Bot  className="h-4 w-4 text-white" />}
                    </div>
                    <div className={`max-w-[80%] flex flex-col gap-1 ${msg.role === "user" ? "items-end" : "items-start"}`}>
                      <div
                        className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                          msg.role === "user"
                            ? "bg-gradient-to-br from-blue-500 to-indigo-600 text-white rounded-br-sm"
                            : "bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-100 rounded-bl-sm"
                        }`}
                      >
                        {msg.content}
                      </div>
                      <span className="text-[10px] text-slate-400 dark:text-slate-600 px-1">
                        {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                  </div>
                ))}

                {/* Typing indicator */}
                {isLoading && (
                  <div className="flex gap-3">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-teal-400 to-blue-500 flex items-center justify-center">
                      <Bot className="h-4 w-4 text-white" />
                    </div>
                    <div className="bg-slate-100 dark:bg-slate-800 rounded-2xl rounded-bl-sm px-4 py-3">
                      <div className="flex gap-1.5 items-center h-4">
                        {[0, 150, 300].map(delay => (
                          <div
                            key={delay}
                            className="w-1.5 h-1.5 bg-slate-400 dark:bg-slate-500 rounded-full animate-bounce"
                            style={{ animationDelay: `${delay}ms` }}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* ── Input bar — always pinned at bottom ──────────────────────────── */}
          <div className="flex-shrink-0 border-t border-slate-200 dark:border-slate-700/50 bg-white dark:bg-[#060d1a] px-4 pt-3 pb-4">
            <div className="max-w-3xl mx-auto">

              {/* Status indicators above input */}
              {isDictating && (
                <div className="flex items-center gap-2 mb-2 px-1">
                  <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                  <span className="text-xs font-medium text-red-500">Recording…  click mic to stop</span>
                </div>
              )}
              {isTranscribing && !isDictating && (
                <div className="flex items-center gap-2 mb-2 px-1">
                  <Loader2 className="h-3 w-3 text-blue-500 animate-spin" />
                  <span className="text-xs text-blue-500">Transcribing…</span>
                </div>
              )}
              {dictError && (
                <p className="text-xs text-red-500 mb-2 px-1">{dictError}</p>
              )}

              {/* Input row */}
              <div className="flex gap-2 items-center">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputText}
                  onChange={e => { setInputText(e.target.value); if (hasUsedVoice) setFixStatus("idle"); }}
                  onKeyDown={handleKeyDown}
                  disabled={isLoading || isTranscribing}
                  placeholder={isDictating ? "Listening — speak now…" : "Ask a legal question…"}
                  className="flex-1 px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all disabled:opacity-50"
                />

                {/* Dictation (voice → text) */}
                <button
                  onClick={toggleDictation}
                  disabled={isTranscribing || isLoading}
                  title={isDictating ? "Stop recording" : "Dictate — voice to text"}
                  className={`flex-shrink-0 w-11 h-11 flex items-center justify-center rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                    isDictating
                      ? "bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/30"
                      : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700"
                  }`}
                >
                  {isDictating ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                </button>

                {/* Voice conversation mode */}
                <button
                  onClick={startVoiceConversation}
                  disabled={isLoading || isDictating || isVoiceConvOpen}
                  title="Voice conversation — speak and listen hands-free"
                  className="flex-shrink-0 w-11 h-11 flex items-center justify-center rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-violet-100 dark:hover:bg-violet-900/20 hover:text-violet-600 dark:hover:text-violet-400 border border-slate-200 dark:border-slate-700 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <PhoneCall className="h-4 w-4" />
                </button>

                {/* Send */}
                <button
                  onClick={handleSend}
                  disabled={!inputText.trim() || isLoading}
                  aria-label="Send"
                  className="flex-shrink-0 w-11 h-11 flex items-center justify-center rounded-xl bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  {isLoading
                    ? <Loader2 className="h-4 w-4 animate-spin" />
                    : <Send    className="h-4 w-4" />}
                </button>
              </div>

              {/* Fix transcription errors — visible only after voice input */}
              {hasUsedVoice && !isDictating && !isTranscribing && inputText.trim() && (
                <div className="mt-2 flex items-center gap-2">
                  <button
                    onClick={fixTranscript}
                    disabled={fixStatus === "fixing"}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-violet-200 dark:border-violet-700/50 bg-violet-50 dark:bg-violet-900/10 text-violet-700 dark:text-violet-300 hover:bg-violet-100 dark:hover:bg-violet-900/20 disabled:opacity-50 transition-colors"
                  >
                    <Wand2 className="h-3 w-3" />
                    {fixButtonLabel}
                  </button>
                  {fixStatus === "fixed" && (
                    <span className="text-[10px] text-green-600 dark:text-green-400">Errors corrected</span>
                  )}
                </div>
              )}

              <p className="text-center text-[11px] text-slate-400 dark:text-slate-600 mt-2">
                AI responses are informational only. Consult a licensed lawyer for legal advice.
              </p>
            </div>
          </div>

        </main>
      </div>
    </div>
  );
};

export default ChatPage;
