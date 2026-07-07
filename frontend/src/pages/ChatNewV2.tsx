import { useState, useRef, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  Send, Bot, User, Loader2, Plus, Trash2, MessageSquare,
  Menu, X, Scale, Mic, MicOff, PhoneCall, Volume2, Wand2, Paperclip, FileText,
  PanelLeftClose, PanelLeftOpen, ChevronDown, Download, BookOpen, CheckCircle2,
  ThumbsUp, ThumbsDown, Copy, Check, Share2,
} from "lucide-react";
import Header from "../components/Header";

// ── Types ─────────────────────────────────────────────────────────────────────

interface SimilarCase {
  case_name:  string;
  case_type:  string;
  summary:    string;
  similarity: number;
}

interface ChatMessage {
  id:           string;
  role:         "user" | "assistant";
  content:      string;
  timestamp:    Date;
  laws?:         string[];
  suggestions?:  string[];
  similar_cases?: SimilarCase[];
  streaming?:    boolean;        // true while SSE stream is in progress
  request_id?:   string;        // API request ID, used for feedback submission
  feedback?:     "up" | "down"; // user's thumbs rating (set after clicking)
  follow_up_questions?: string[];
  risk_level?: string;
  detected_language?: string;
  response_type?: string; // "prediction_prompt" triggers a link to /predict
  source_query?: string;  // the user question that produced a prediction_prompt
}

interface ConvSummary {
  id: string;
  title: string;
  created_at: string;
  message_count: number;
}

type VoiceConvState = "listening" | "processing" | "speaking";

// ── Constants ─────────────────────────────────────────────────────────────────

const INDIAN_STATES = [
  { value: "Andhra Pradesh",    label: "Andhra Pradesh" },
  { value: "Arunachal Pradesh", label: "Arunachal Pradesh" },
  { value: "Assam",             label: "Assam" },
  { value: "Bihar",             label: "Bihar" },
  { value: "Chhattisgarh",      label: "Chhattisgarh" },
  { value: "Delhi",             label: "Delhi" },
  { value: "Goa",               label: "Goa" },
  { value: "Gujarat",           label: "Gujarat" },
  { value: "Haryana",           label: "Haryana" },
  { value: "Himachal Pradesh",  label: "Himachal Pradesh" },
  { value: "Jharkhand",         label: "Jharkhand" },
  { value: "Karnataka",         label: "Karnataka" },
  { value: "Kerala",            label: "Kerala" },
  { value: "Madhya Pradesh",    label: "Madhya Pradesh" },
  { value: "Maharashtra",       label: "Maharashtra" },
  { value: "Manipur",           label: "Manipur" },
  { value: "Meghalaya",         label: "Meghalaya" },
  { value: "Mizoram",           label: "Mizoram" },
  { value: "Nagaland",          label: "Nagaland" },
  { value: "Odisha",            label: "Odisha" },
  { value: "Punjab",            label: "Punjab" },
  { value: "Rajasthan",         label: "Rajasthan" },
  { value: "Sikkim",            label: "Sikkim" },
  { value: "Tamil Nadu",        label: "Tamil Nadu" },
  { value: "Telangana",         label: "Telangana" },
  { value: "Tripura",           label: "Tripura" },
  { value: "Uttar Pradesh",     label: "Uttar Pradesh" },
  { value: "Uttarakhand",       label: "Uttarakhand" },
  { value: "West Bengal",       label: "West Bengal" },
];

const LANGUAGE_NAMES: Record<string, string> = {
  hi: "Hindi", bn: "Bengali", ta: "Tamil", te: "Telugu",
  mr: "Marathi", gu: "Gujarati", kn: "Kannada", ml: "Malayalam", pa: "Punjabi",
};

const SUGGESTIONS = [
  "What are my rights as a tenant in India?",
  "Explain the RTI Act 2005 and how to file an application",
  "What is Section 498A of the IPC?",
  "How do I file a consumer complaint against a company?",
];

// ── Utility: best supported audio MIME type ───────────────────────────────────

// Convert raw dataset filenames / IDs into readable case names
function formatCaseName(raw: string): string {
  const name = raw.replace(/\.txt$/i, "").trim();
  // Pure numeric ID → label it as a court case reference
  if (/^\d+$/.test(name)) return `Indian Court Case · ${name}`;
  // Sentence-case for short all-caps strings
  if (name === name.toUpperCase() && name.length < 40) {
    return name.charAt(0).toUpperCase() + name.slice(1).toLowerCase();
  }
  return name;
}

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
  const [isLoading, setIsLoading]             = useState(false);
  const [sidebarOpen, setSidebarOpen]         = useState(false);   // mobile overlay
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false); // desktop collapse

  // ── Jurisdiction state ─────────────────────────────────────────────────────
  const [selectedState, setSelectedState]   = useState("");

  // ── Expanded precedent summaries (Set of "${msgId}-${caseIdx}") ────────────
  const [expandedPrecedents, setExpandedPrecedents] = useState<Set<string>>(new Set());

  // ── Citation copy and share state ────────────────────────────────────────────
  const [copiedCitationKey, setCopiedCitationKey] = useState<string | null>(null);
  const [shareStatus, setShareStatus] = useState<"idle" | "loading" | "copied" | "error">("idle");

  function togglePrecedent(key: string) {
    setExpandedPrecedents(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

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

  // ── Document upload state ─────────────────────────────────────────────────────
  const [docFile, setDocFile]                 = useState<File | null>(null);
  const [extractedDocText, setExtractedDocText] = useState("");
  const [docLaws, setDocLaws]                 = useState<string[]>([]);
  const [isDocUploading, setIsDocUploading]   = useState(false);
  const [docUploadError, setDocUploadError]   = useState("");

  // ── Scroll state ──────────────────────────────────────────────────────────────
  const [showScrollDown, setShowScrollDown] = useState(false);

  // ── Core refs ────────────────────────────────────────────────────────────────
  const messagesEndRef       = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputRef             = useRef<HTMLTextAreaElement>(null);
  const activeConvRef        = useRef<string | null>(null);
  const docInputRef          = useRef<HTMLInputElement>(null);
  // true when the user themselves just sent — ensures we always scroll on send
  const userJustSentRef      = useRef(false);
  // Mirror of messages state — lets async callbacks (voice conv) read latest list without stale closure
  const messagesRef          = useRef<ChatMessage[]>([]);

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

  // Keep refs in sync with state so async callbacks always read the latest value
  useEffect(() => { activeConvRef.current  = activeConvId; }, [activeConvId]);
  useEffect(() => { messagesRef.current    = messages;     }, [messages]);

  // Mirror voice conv UI state into ref so RAF/async callbacks read it without stale closure
  function setVoiceConvState(s: VoiceConvState) {
    vcStateRef.current = s;
    setVoiceConvStateUI(s);
  }

  // ── Lifecycle ─────────────────────────────────────────────────────────────────

  useEffect(() => {
    const el = messagesContainerRef.current;
    if (!el) return;
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    // Always scroll when user just sent; otherwise only when already near bottom
    if (userJustSentRef.current || distFromBottom < 120) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
      userJustSentRef.current = false;
    }
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

  // Auto-grow textarea: expands line by line up to MAX_H, then shows scrollbar
  const MAX_TEXTAREA_H = 108; // ~4 lines with padding; adjust if needed
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";                          // shrink first so scrollHeight is accurate
    const h = Math.min(el.scrollHeight, MAX_TEXTAREA_H);
    el.style.height = `${h}px`;
    el.style.overflowY = el.scrollHeight > MAX_TEXTAREA_H ? "auto" : "hidden";
  }, [inputText]);

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

  async function appendMessage(
    convId: string,
    role: string,
    content: string,
    meta?: { laws?: string[]; suggestions?: string[]; risk_level?: string },
  ) {
    try {
      const body: Record<string, unknown> = { role, content };
      if (meta?.laws?.length)        body.laws        = meta.laws;
      if (meta?.suggestions?.length) body.suggestions = meta.suggestions;
      if (meta?.risk_level)          body.risk_level  = meta.risk_level;
      await fetch(`${apiUrl}/conversations/${convId}/messages`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(body),
      });
    } catch { /* fire-and-forget; UI already updated */ }
  }

  interface QueryResult {
    reply:               string;
    laws:                string[];
    suggestions:         string[];
    similar_cases:       SimilarCase[];
    request_id:          string;
    follow_up_questions: string[];
    risk_level:          string;
    detected_language:   string;
    response_type:       string;
  }

  // callQuery is used only by the voice conversation path (non-streaming)
  async function callQuery(
    query:   string,
    history: { role: string; content: string }[] = [],
    state:   string = "",
  ): Promise<QueryResult> {
    const controller = new AbortController();
    const tid = setTimeout(() => controller.abort(), 60_000);
    try {
      const body: Record<string, unknown> = { query };
      if (history.length > 0) body.conversation_history = history;
      if (state) body.state = state;

      const res = await fetch(`${apiUrl}/query`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      clearTimeout(tid);
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const data = await res.json();
      // Filter out the placeholder "Assessment not performed" value so the
      // risk gauge only renders when the LLM actually produced a risk level.
      const rawRisk = data.impact_score?.risk_level || "";
      const riskLevel = rawRisk === "Assessment not performed" ? "" : rawRisk;
      return {
        reply:               data.summary        || "I can help with that. Could you provide more details?",
        laws:                Array.isArray(data.laws)        ? data.laws        : [],
        suggestions:         Array.isArray(data.suggestions) ? data.suggestions : [],
        similar_cases:       Array.isArray(data.similar_cases) ? data.similar_cases : [],
        request_id:          data.request_id     || "",
        follow_up_questions: Array.isArray(data.follow_up_questions) ? data.follow_up_questions : [],
        risk_level:          riskLevel,
        detected_language:   data.language || "",
        response_type:       data.response_type || "",
      };
    } catch (e) {
      clearTimeout(tid);
      const msg =
        e instanceof Error && e.name === "AbortError"
          ? "The request timed out. Please try again."
          : "Sorry, I couldn't reach the server. Please try again.";
      return { reply: msg, laws: [], suggestions: [], similar_cases: [], request_id: "", follow_up_questions: [], risk_level: "", detected_language: "", response_type: "" };
    }
  }

  // callQueryStream — streaming path used by handleSend
  async function callQueryStream(
    query:    string,
    history:  { role: string; content: string }[],
    botMsgId: string,
    state:    string,
    onDone?:  (summary: string, meta?: { laws?: string[]; suggestions?: string[]; risk_level?: string }) => void,
  ): Promise<void> {
    let firstChunk = true;
    let acc = "";

    try {
      const body: Record<string, unknown> = { query };
      if (history.length > 0) body.conversation_history = history;
      if (state) body.state = state;

      const res = await fetch(`${apiUrl}/stream`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(body),
      });

      if (!res.ok || !res.body) {
        throw new Error(`Server error ${res.status}`);
      }

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let sseBuffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        sseBuffer += decoder.decode(value, { stream: true });

        // SSE events are delimited by double newlines
        const events = sseBuffer.split("\n\n");
        sseBuffer = events.pop() ?? "";

        for (const event of events) {
          for (const line of event.split("\n")) {
            if (!line.startsWith("data: ")) continue;
            const jsonStr = line.slice(6).trim();
            if (jsonStr === "[DONE]") continue;

            let data: Record<string, unknown>;
            try { data = JSON.parse(jsonStr); } catch { continue; }

            if (data.type === "chunk") {
              if (firstChunk) { firstChunk = false; setIsLoading(false); }
              acc += String(data.content ?? "");

              // Extract and display the summary portion of the accumulated text
              let display = acc;
              if (display.startsWith("SUMMARY: ")) display = display.slice(9);
              else if (display.startsWith("SUMMARY:")) display = display.slice(8).trimStart();
              const li = display.indexOf("\nLAWS:");
              if (li !== -1) display = display.slice(0, li);
              const si = display.indexOf("\nSTEPS:");
              if (si !== -1) display = display.slice(0, si);

              setMessages(prev => prev.map(m =>
                m.id === botMsgId ? { ...m, content: display.trimStart() } : m
              ));

            } else if (data.type === "done") {
              setIsLoading(false);
              const summary      = String(data.summary    ?? acc.trimStart().replace(/^SUMMARY:\s*/,""));
              const laws         = Array.isArray(data.laws)          ? (data.laws as string[])          : [];
              const sugg         = Array.isArray(data.suggestions)   ? (data.suggestions as string[])   : [];
              const cases        = Array.isArray(data.similar_cases) ? (data.similar_cases as SimilarCase[]) : [];
              const request_id   = String(data.request_id ?? "");
              const responseType = String(data.response_type ?? "") || undefined;
              const riskLvl      = String(data.risk_level ?? "") || undefined;

              setMessages(prev => prev.map(m =>
                m.id === botMsgId
                  ? {
                      ...m,
                      content:             summary,
                      streaming:           false,
                      request_id,
                      laws:                laws.length   > 0 ? laws  : undefined,
                      suggestions:         sugg.length   > 0 ? sugg  : undefined,
                      similar_cases:       cases.length  > 0 ? cases : undefined,
                      follow_up_questions: Array.isArray(data.follow_up_questions) && (data.follow_up_questions as string[]).length > 0
                        ? (data.follow_up_questions as string[]) : undefined,
                      risk_level:          riskLvl,
                      detected_language:   String(data.language ?? "") || undefined,
                      response_type:       responseType,
                      source_query:        responseType === "prediction_prompt" ? query : undefined,
                    }
                  : m
              ));

              if (onDone) onDone(summary, {
                laws:       laws.length > 0 ? laws : undefined,
                suggestions: sugg.length > 0 ? sugg : undefined,
                risk_level:  riskLvl,
              });

            } else if (data.type === "error") {
              setIsLoading(false);
              setMessages(prev => prev.map(m =>
                m.id === botMsgId
                  ? { ...m, content: String(data.message ?? "An error occurred."), streaming: false }
                  : m
              ));
            }
          }
        }
      }
    } catch {
      setIsLoading(false);
      setMessages(prev => prev.map(m =>
        m.id === botMsgId
          ? { ...m, content: "Sorry, I couldn't reach the server. Please try again.", streaming: false }
          : m
      ));
    }
  }

  // handleFeedback — submits 👍/👎 to /feedback/score
  async function handleFeedback(
    msgId:     string,
    requestId: string,
    direction: "up" | "down",
  ) {
    // Optimistic update — mark immediately
    setMessages(prev => prev.map(m =>
      m.id === msgId ? { ...m, feedback: direction } : m
    ));

    try {
      await fetch(`${apiUrl}/feedback/score`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          request_id:         requestId,
          overall_score_given: direction === "up" ? 100 : 0,
          user_rating:         direction === "up" ? 5   : 1,
          feedback_type:       direction === "up" ? "helpful" : "not_helpful",
        }),
      });
    } catch { /* feedback is non-critical — fail silently */ }
  }

  // ── Citation copy ─────────────────────────────────────────────────────────────

  async function copyPrecedentCitation(key: string, caseName: string, caseType: string) {
    const citation = `${formatCaseName(caseName)}. ${caseType || "Indian Court Case"}. Smart Legal Assistant Database.`;
    try {
      await navigator.clipboard.writeText(citation);
      setCopiedCitationKey(key);
      setTimeout(() => setCopiedCitationKey(null), 2000);
    } catch { /* clipboard not available */ }
  }

  // ── Share conversation ────────────────────────────────────────────────────────

  async function shareConversation(convId: string) {
    setShareStatus("loading");
    try {
      const res = await fetch(`${apiUrl}/conversations/${convId}/share`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      const shareUrl = `${window.location.origin}/shared/${data.share_token}`;
      await navigator.clipboard.writeText(shareUrl);
      setShareStatus("copied");
      setTimeout(() => setShareStatus("idle"), 3000);
    } catch {
      setShareStatus("error");
      setTimeout(() => setShareStatus("idle"), 2000);
    }
  }

  // ── Chat actions ──────────────────────────────────────────────────────────────

  async function handleSend() {
    const typedText = inputText.trim();
    // Allow send if there's typed text OR an extracted document
    if ((!typedText && !extractedDocText) || isLoading) return;

    // Combine typed text with extracted document text (same pattern as CasePredictor)
    const text = [typedText, extractedDocText.trim()]
      .filter(Boolean)
      .join("\n\n---\n");

    setInputText("");
    // Do NOT clear extractedDocText / docFile / docLaws here — they persist until
    // the user explicitly dismisses the document with the ✕ button. This lets the
    // user ask multiple questions about the same document in sequence.
    setDocUploadError("");
    setIsLoading(true);
    setHasUsedVoice(false);
    setFixStatus("idle");
    userJustSentRef.current = true;

    let convId = activeConvRef.current;
    if (!convId) {
      const shortTitle = typedText.length > 60 ? typedText.slice(0, 57) + "…" : typedText || "Document analysis";
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

    // Show the user-visible text (just what they typed, not the raw extracted blob)
    const displayText = typedText || `[Document: ${docFile?.name ?? "uploaded file"}]`;
    const userMsg: ChatMessage = { id: Date.now().toString(), role: "user", content: displayText, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);

    // Build conversation history from the last 10 messages for multi-turn memory
    const history = messagesRef.current
      .slice(-10)
      .map(m => ({ role: m.role, content: m.content }));

    // Add streaming placeholder bot message immediately so user sees something
    const botMsgId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, {
      id:        botMsgId,
      role:      "assistant" as const,
      content:   "",
      timestamp: new Date(),
      streaming: true,
    }]);

    // Stream the response; persist to MongoDB via onDone callback
    const persistConvId = convId;
    await callQueryStream(text, history, botMsgId, selectedState, (finalSummary, meta) => {
      if (persistConvId) {
        appendMessage(persistConvId, "user", displayText);
        appendMessage(persistConvId, "assistant", finalSummary, meta);
      }
    });

    setIsLoading(false);
  }

  async function handleSelectConversation(id: string) {
    if (id === activeConvRef.current) { setSidebarOpen(false); return; }
    setActiveConvId(id);
    setMessages([]);
    setHasUsedVoice(false);
    setFixStatus("idle");
    setDocFile(null);
    setExtractedDocText("");
    setDocLaws([]);
    setDocUploadError("");
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
    setDocFile(null);
    setExtractedDocText("");
    setDocLaws([]);
    setDocUploadError("");
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

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }

  function handleMessagesScroll() {
    const el = messagesContainerRef.current;
    if (!el) return;
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setShowScrollDown(distFromBottom > 120);
  }

  function scrollToBottom() {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    setShowScrollDown(false);
  }

  // ── Document Upload ───────────────────────────────────────────────────────────

  async function handleDocUpload(file: File) {
    setDocUploadError("");
    setIsDocUploading(true);
    setDocFile(file);
    setExtractedDocText("");
    setDocLaws([]);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${apiUrl}/document/extract-statement`, {
        method: "POST",
        headers: authOnlyHeaders(),
        body: formData,
      });
      if (!res.ok) throw new Error(`Upload failed (${res.status})`);
      const data = await res.json();
      if (data.statement) setExtractedDocText(data.statement);
      if (data.detected_laws?.length) setDocLaws(data.detected_laws);
    } catch {
      setDocUploadError("Document processing failed. Please try again.");
      setDocFile(null);
    } finally {
      setIsDocUploading(false);
    }
  }

  function removeDoc() {
    setDocFile(null);
    setExtractedDocText("");
    setDocLaws([]);
    setDocUploadError("");
    if (docInputRef.current) docInputRef.current.value = "";
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

    // ── Get AI reply with conversation history ────────────────────────────────
    // Use messagesRef (not messages state) to avoid stale closure in async chain
    const history = messagesRef.current
      .slice(-10)
      .map(m => ({ role: m.role, content: m.content }));

    const { reply, laws, suggestions, similar_cases, request_id, follow_up_questions, risk_level, detected_language, response_type } = await callQuery(transcript, history, selectedState);
    if (!vcActiveRef.current) return;

    const botMsg: ChatMessage = {
      id:                  (Date.now() + 1).toString(),
      role:                "assistant",
      content:             reply,
      timestamp:           new Date(),
      laws:                laws.length        > 0 ? laws        : undefined,
      suggestions:         suggestions.length > 0 ? suggestions : undefined,
      similar_cases:       similar_cases.length > 0 ? similar_cases : undefined,
      request_id:          request_id || undefined,
      follow_up_questions: follow_up_questions.length > 0 ? follow_up_questions : undefined,
      risk_level:          risk_level || undefined,
      detected_language:   detected_language || undefined,
      response_type:       response_type || undefined,
      source_query:        response_type === "prediction_prompt" ? transcript : undefined,
    };
    setMessages(prev => [...prev, botMsg]);

    // Persist to MongoDB (with structured data for assistant messages)
    if (convId) {
      appendMessage(convId, "user", transcript);
      appendMessage(convId, "assistant", reply, {
        laws:       laws.length > 0 ? laws : undefined,
        suggestions: suggestions.length > 0 ? suggestions : undefined,
        risk_level:  risk_level || undefined,
      });
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

  // ── PDF Export ────────────────────────────────────────────────────────────────

  function escapeHtml(str: string): string {
    return str
      .replace(/&/g,  "&amp;")
      .replace(/</g,  "&lt;")
      .replace(/>/g,  "&gt;")
      .replace(/"/g,  "&quot;")
      .replace(/'/g,  "&#39;");
  }

  function exportChatPdf() {
    if (messages.length === 0) return;

    const convTitle = conversations.find(c => c.id === activeConvId)?.title ?? "Legal Consultation";
    const dateStr   = new Date().toLocaleDateString("en-IN", { year: "numeric", month: "long", day: "numeric" });

    const messagesHtml = messages.map(m => {
      const isUser = m.role === "user";
      const bg     = isUser ? "#EFF6FF" : "#F8FAFC";
      const border = isUser ? "#BFDBFE" : "#E2E8F0";
      const label  = isUser ? "You" : "Legal AI";
      const labelColor = isUser ? "#1D4ED8" : "#0F766E";
      const align  = isUser ? "right" : "left";

      let lawsHtml = "";
      if (!isUser && m.laws && m.laws.length > 0) {
        const chips = m.laws.map(l =>
          `<span style="display:inline-block;margin:2px 3px 2px 0;padding:3px 8px;background:#EFF6FF;border:1px solid #BFDBFE;border-radius:99px;font-size:11px;color:#1D4ED8;font-weight:500;">${escapeHtml(l)}</span>`
        ).join("");
        lawsHtml = `
          <div style="margin-top:10px;padding-top:8px;border-top:1px dashed #DBEAFE;">
            <div style="font-size:9px;font-weight:700;color:#6B7280;text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px;">Applicable Laws</div>
            <div>${chips}</div>
          </div>`;
      }

      let suggestionsHtml = "";
      if (!isUser && m.suggestions && m.suggestions.length > 0) {
        const items = m.suggestions.map((s, i) =>
          `<div style="display:flex;gap:8px;margin:4px 0;">
            <span style="flex-shrink:0;font-weight:700;color:#15803D;font-size:12px;">${i + 1}.</span>
            <span style="font-size:12px;color:#374151;line-height:1.5;">${escapeHtml(s)}</span>
          </div>`
        ).join("");
        suggestionsHtml = `
          <div style="margin-top:10px;padding-top:8px;border-top:1px dashed #D1FAE5;">
            <div style="font-size:9px;font-weight:700;color:#6B7280;text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px;">Suggested Steps</div>
            ${items}
          </div>`;
      }

      return `
        <div style="margin-bottom:18px;text-align:${align};">
          <div style="display:inline-block;max-width:82%;background:${bg};border:1px solid ${border};border-radius:12px;padding:12px 16px;text-align:left;">
            <div style="font-size:9px;font-weight:700;color:${labelColor};text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">${label}</div>
            <div style="font-size:13px;color:#1E293B;white-space:pre-wrap;line-height:1.65;">${escapeHtml(m.content)}</div>
            ${lawsHtml}
            ${suggestionsHtml}
            <div style="font-size:10px;color:#9CA3AF;margin-top:8px;">${m.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</div>
          </div>
        </div>`;
    }).join("");

    const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Legal Consultation — ${escapeHtml(convTitle)}</title>
  <style>
    body{font-family:Georgia,serif;margin:0;padding:40px;background:#fff;color:#1E293B;font-size:14px;}
    @page{margin:20mm;}
    @media print{body{padding:0;}}
    h1{font-size:22px;color:#1E3A5F;margin-bottom:4px;}
    .meta{font-size:12px;color:#6B7280;margin-bottom:28px;padding-bottom:14px;border-bottom:2px solid #E5E7EB;}
    .disclaimer{margin-top:32px;padding:12px 16px;background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;font-size:11px;color:#92400E;}
  </style>
</head>
<body>
  <h1>&#9878; Smart Legal Assistant</h1>
  <div class="meta">
    <strong>${escapeHtml(convTitle)}</strong><br/>
    Exported on ${escapeHtml(dateStr)} &nbsp;·&nbsp; ${messages.length} messages
  </div>
  ${messagesHtml}
  <div class="disclaimer">
    <strong>Disclaimer:</strong> This document is generated by an AI legal assistant and is provided for informational purposes only.
    It does not constitute legal advice. Please consult a qualified legal professional before taking any legal action.
  </div>
</body>
</html>`;

    const win = window.open("", "_blank");
    if (!win) { alert("Please allow pop-ups to export the conversation as PDF."); return; }
    win.document.write(html);
    win.document.close();
    // Small delay so the browser finishes rendering before the print dialog opens
    setTimeout(() => { win.focus(); win.print(); }, 400);
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
            flex flex-col flex-shrink-0
            border-r border-slate-200 dark:border-slate-700/50
            bg-slate-50 dark:bg-[#0a0f1e]
            transition-all duration-300 ease-in-out
            fixed inset-y-0 left-0 z-30 top-14
            md:relative md:inset-y-auto md:left-auto md:top-auto
            ${sidebarOpen ? "translate-x-0 w-64" : "-translate-x-full w-64 md:translate-x-0"}
            ${sidebarCollapsed ? "md:w-0 md:border-r-0 md:overflow-hidden" : "md:w-64"}
          `}
        >
          {/* Sidebar header: collapse toggle + new chat */}
          <div className="flex items-center gap-2 p-3 flex-shrink-0">
            {/* Desktop collapse toggle */}
            <button
              onClick={() => setSidebarCollapsed(c => !c)}
              title="Toggle sidebar"
              className="hidden md:flex w-8 h-8 items-center justify-center rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors flex-shrink-0"
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>

            <button
              onClick={handleNewChat}
              className="flex-1 flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:border-blue-300 dark:hover:border-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-colors"
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
        <main className="flex-1 flex flex-col min-w-0 min-h-0 overflow-hidden bg-white dark:bg-[#060d1a]">

          {/* Desktop top bar — only visible when sidebar is collapsed */}
          {sidebarCollapsed && (
            <div className="hidden md:flex items-center gap-2 px-3 py-2 border-b border-slate-200 dark:border-slate-700/50 flex-shrink-0">
              <button
                onClick={() => setSidebarCollapsed(false)}
                title="Open sidebar"
                className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                <PanelLeftOpen className="h-4 w-4" />
              </button>
              <button
                onClick={handleNewChat}
                title="New chat"
                className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                <Plus className="h-4 w-4" />
              </button>
            </div>
          )}

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

          {/* Conversation toolbar — export button, only when there are messages */}
          {messages.length > 0 && (
            <div className="flex-shrink-0 flex items-center justify-between px-4 py-1.5 border-b border-slate-100 dark:border-slate-800/60 bg-white dark:bg-[#060d1a]">
              <span className="text-xs text-slate-400 dark:text-slate-600 truncate max-w-[60%]">
                {conversations.find(c => c.id === activeConvId)?.title ?? "Current conversation"}
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => activeConvId && shareConversation(activeConvId)}
                  disabled={!activeConvId || shareStatus === "loading"}
                  title={activeConvId ? "Share conversation" : "Send a message first to share"}
                  className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400 px-2.5 py-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {shareStatus === "loading" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> :
                   shareStatus === "copied" ? <Check className="h-3.5 w-3.5 text-green-500" /> :
                   shareStatus === "error"  ? <X className="h-3.5 w-3.5 text-red-500" /> :
                   <Share2 className="h-3.5 w-3.5" />}
                  {shareStatus === "copied" ? "Copied!" : shareStatus === "error" ? "Failed" : "Share"}
                </button>
                <button
                  onClick={exportChatPdf}
                  title="Export conversation as PDF"
                  className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-blue-600 dark:text-slate-400 dark:hover:text-blue-400 px-2.5 py-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                >
                  <Download className="h-3.5 w-3.5" />
                  Export PDF
                </button>
              </div>
            </div>
          )}

          {/* Messages — scrolls internally */}
          <div
            ref={messagesContainerRef}
            onScroll={handleMessagesScroll}
            className="flex-1 overflow-y-auto"
          >

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
                        {msg.streaming && (
                          <span className="inline-block w-0.5 h-4 bg-slate-500 dark:bg-slate-300 animate-pulse ml-0.5 align-middle" />
                        )}
                      </div>

                      {/* Applicable Laws — blue badge chips */}
                      {msg.role === "assistant" && msg.laws && msg.laws.length > 0 && (
                        <div className="w-full mt-2 rounded-xl border border-blue-200 dark:border-blue-800/50 bg-blue-50 dark:bg-blue-950/30 px-3 py-2.5">
                          <div className="flex items-center gap-1.5 mb-2">
                            <Scale className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400 flex-shrink-0" />
                            <span className="text-[11px] font-semibold text-blue-700 dark:text-blue-400 uppercase tracking-wider">
                              Applicable Laws
                            </span>
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            {msg.laws.map((law, i) => (
                              <span
                                key={i}
                                className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-medium bg-white dark:bg-blue-900/40 border border-blue-200 dark:border-blue-700/50 text-blue-700 dark:text-blue-300"
                              >
                                {law}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Suggested Steps — numbered action list */}
                      {msg.role === "assistant" && msg.suggestions && msg.suggestions.length > 0 && (
                        <div className="w-full mt-2 rounded-xl border border-emerald-200 dark:border-emerald-800/50 bg-emerald-50 dark:bg-emerald-950/30 px-3 py-2.5">
                          <div className="flex items-center gap-1.5 mb-2">
                            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
                            <span className="text-[11px] font-semibold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider">
                              Suggested Steps
                            </span>
                          </div>
                          <ol className="space-y-1.5">
                            {msg.suggestions.map((s, i) => (
                              <li key={i} className="flex gap-2.5 items-start">
                                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-emerald-100 dark:bg-emerald-900/50 border border-emerald-300 dark:border-emerald-700 text-[10px] font-bold text-emerald-700 dark:text-emerald-400 flex items-center justify-center mt-0.5">
                                  {i + 1}
                                </span>
                                <span className="text-[12px] text-slate-700 dark:text-slate-300 leading-relaxed">
                                  {s}
                                </span>
                              </li>
                            ))}
                          </ol>
                        </div>
                      )}

                      {/* Relevant Cases panel — only on assistant messages with RAG hits */}
                      {/* Court precedents panel intentionally hidden — RAG runs internally to improve answer quality but results are not surfaced in the UI */}

                      {/* Language indicator badge — non-English responses */}
                      {msg.role === "assistant" && msg.detected_language && msg.detected_language !== "en" && !msg.streaming && (
                        <div className="flex items-center gap-1">
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-700/50 text-indigo-600 dark:text-indigo-400">
                            🇮🇳 {LANGUAGE_NAMES[msg.detected_language] || msg.detected_language}
                          </span>
                        </div>
                      )}

                      {/* Legal risk gauge */}
                      {msg.role === "assistant" && msg.risk_level && !msg.streaming && (() => {
                        const clean = msg.risk_level.replace(/[^\w\s]/g, "").trim().toLowerCase();
                        const label = clean.includes("critical") ? "Critical" : clean.includes("high") ? "High" : clean.includes("medium") ? "Medium" : "Low";
                        const pct   = label === "Critical" ? 92 : label === "High" ? 68 : label === "Medium" ? 42 : 18;
                        const barCls = label === "Critical" ? "bg-red-500" : label === "High" ? "bg-orange-500" : label === "Medium" ? "bg-yellow-400" : "bg-green-500";
                        const txtCls = label === "Critical" ? "text-red-600 dark:text-red-400" : label === "High" ? "text-orange-600 dark:text-orange-400" : label === "Medium" ? "text-yellow-600 dark:text-yellow-400" : "text-green-600 dark:text-green-400";
                        return (
                          <div className="w-full mt-2 rounded-xl border border-slate-200 dark:border-slate-700/60 bg-white dark:bg-slate-800/50 px-3 py-2.5">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Legal Risk</span>
                              <span className={`text-[11px] font-bold ${txtCls}`}>{label}</span>
                            </div>
                            <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-700 overflow-hidden">
                              <div className={`h-full rounded-full transition-all duration-700 ${barCls}`} style={{ width: `${pct}%` }} />
                            </div>
                            <div className="flex justify-between mt-1">
                              <span className="text-[9px] text-slate-400">Low</span>
                              <span className="text-[9px] text-slate-400">Critical</span>
                            </div>
                          </div>
                        );
                      })()}

                      {/* Prediction bridge — shown when chatbot redirects to case predictor */}
                      {msg.role === "assistant" && msg.response_type === "prediction_prompt" && !msg.streaming && (
                        <div className="w-full mt-2 rounded-xl border border-violet-200 dark:border-violet-700/50 bg-violet-50 dark:bg-violet-900/10 px-3 py-2.5 flex items-center justify-between gap-3">
                          <p className="text-[12px] text-violet-700 dark:text-violet-300 leading-snug">
                            This looks like a case outcome question. Use the Case Predictor for an ML-based analysis.
                          </p>
                          <Link
                            to="/predict"
                            state={{ prefillQuery: msg.source_query || "" }}
                            className="flex-shrink-0 text-[11px] font-semibold px-3 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-700 text-white transition-colors"
                          >
                            Run Prediction →
                          </Link>
                        </div>
                      )}

                      {/* Follow-up question chips */}
                      {msg.role === "assistant" && msg.follow_up_questions && msg.follow_up_questions.length > 0 && !msg.streaming && (
                        <div className="w-full mt-2">
                          <p className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1.5 px-0.5">
                            Ask follow-up
                          </p>
                          <div className="flex flex-col gap-1.5">
                            {msg.follow_up_questions.map((q, qi) => (
                              <button
                                key={qi}
                                onClick={() => { setInputText(q); setTimeout(() => inputRef.current?.focus(), 50); }}
                                className="text-left text-[12px] px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 hover:border-blue-300 dark:hover:border-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/10 hover:text-blue-700 dark:hover:text-blue-300 transition-all"
                              >
                                {q}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Feedback buttons — 👍/👎 only on settled assistant messages */}
                      {msg.role === "assistant" && msg.request_id && !msg.streaming && (
                        <div className="flex items-center gap-0.5 px-1">
                          <button
                            onClick={() => handleFeedback(msg.id, msg.request_id!, "up")}
                            disabled={!!msg.feedback}
                            title="Helpful"
                            className={`w-6 h-6 flex items-center justify-center rounded-md transition-all disabled:cursor-default ${
                              msg.feedback === "up"
                                ? "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/30"
                                : msg.feedback === "down"
                                ? "text-slate-300 dark:text-slate-600"
                                : "text-slate-400 hover:text-green-600 dark:hover:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20"
                            }`}
                          >
                            <ThumbsUp className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => handleFeedback(msg.id, msg.request_id!, "down")}
                            disabled={!!msg.feedback}
                            title="Not helpful"
                            className={`w-6 h-6 flex items-center justify-center rounded-md transition-all disabled:cursor-default ${
                              msg.feedback === "down"
                                ? "text-red-500 dark:text-red-400 bg-red-50 dark:bg-red-900/30"
                                : msg.feedback === "up"
                                ? "text-slate-300 dark:text-slate-600"
                                : "text-slate-400 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
                            }`}
                          >
                            <ThumbsDown className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      )}

                      <span className="text-[10px] text-slate-400 dark:text-slate-600 px-1">
                        {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                  </div>
                ))}

                {/* Typing indicator — shown only before the first streaming chunk arrives */}
                {isLoading && !messages.some(m => m.streaming) && (
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

          {/* ── Scroll-to-bottom button ──────────────────────────────────────── */}
          {showScrollDown && (
            <div className="flex-shrink-0 flex justify-center py-1 bg-white dark:bg-[#060d1a]">
              <button
                onClick={scrollToBottom}
                title="Jump to latest message"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 shadow-md transition-all"
              >
                <ChevronDown className="h-3.5 w-3.5" />
                Latest message
              </button>
            </div>
          )}

          {/* ── Input area — always pinned at bottom ─────────────────────────── */}
          <div className="flex-shrink-0 bg-white dark:bg-[#060d1a] px-4 pt-3 pb-4">
            <div className="max-w-3xl mx-auto">

              {/* Hidden file input */}
              <input
                ref={docInputRef}
                type="file"
                accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                className="hidden"
                onChange={e => {
                  const f = e.target.files?.[0];
                  if (f) handleDocUpload(f);
                  e.target.value = "";
                }}
              />

              {/* ── ChatGPT-style input card ─────────────────────────────────── */}
              <div className={`rounded-2xl border bg-slate-50 dark:bg-slate-800/80 shadow-sm transition-all ${
                isDictating
                  ? "border-red-300 dark:border-red-700 ring-1 ring-red-200 dark:ring-red-800/60"
                  : "border-slate-200 dark:border-slate-700 focus-within:border-blue-400 dark:focus-within:border-blue-600 focus-within:ring-1 focus-within:ring-blue-300 dark:focus-within:ring-blue-700/50"
              }`}>

                {/* Document pill — inside card at top */}
                {docFile && (
                  <div className="flex items-center gap-2 px-4 pt-3 flex-wrap">
                    <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs border ${
                      isDocUploading
                        ? "border-blue-200 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-700/40 text-blue-600 dark:text-blue-300"
                        : extractedDocText
                        ? "border-green-200 bg-green-50 dark:bg-green-900/20 dark:border-green-700/40 text-green-700 dark:text-green-300"
                        : "border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-700/40 text-red-600 dark:text-red-300"
                    }`}>
                      {isDocUploading ? <Loader2 className="h-3 w-3 animate-spin" /> : <FileText className="h-3 w-3" />}
                      <span className="max-w-[200px] truncate">{docFile.name}</span>
                      <span className="text-[10px] opacity-60">
                        {isDocUploading ? "Processing…" : extractedDocText ? "Ready" : "Failed"}
                      </span>
                    </div>
                    {!isDocUploading && (
                      <button onClick={removeDoc} title="Remove" className="text-slate-400 hover:text-red-500 transition-colors">
                        <X className="h-3 w-3" />
                      </button>
                    )}
                    {docLaws.length > 0 && (
                      <span className="text-[10px] text-slate-400 dark:text-slate-500 truncate max-w-[260px]">
                        {docLaws.slice(0, 3).join(" · ")}
                      </span>
                    )}
                  </div>
                )}

                {/* Status banner inside card */}
                {isDictating && (
                  <div className="flex items-center gap-2 px-4 pt-3">
                    <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse flex-shrink-0" />
                    <span className="text-xs font-medium text-red-500">Recording… tap mic to stop</span>
                  </div>
                )}
                {isTranscribing && !isDictating && (
                  <div className="flex items-center gap-2 px-4 pt-3">
                    <Loader2 className="h-3 w-3 text-blue-500 animate-spin flex-shrink-0" />
                    <span className="text-xs text-blue-500">Transcribing…</span>
                  </div>
                )}
                {(dictError || docUploadError) && (
                  <p className="text-xs text-red-500 px-4 pt-3">{dictError || docUploadError}</p>
                )}

                {/* Textarea — auto-grows 1→max rows, then scrolls */}
                <textarea
                  ref={inputRef}
                  rows={1}
                  value={inputText}
                  onChange={e => { setInputText(e.target.value); if (hasUsedVoice) setFixStatus("idle"); }}
                  onKeyDown={handleKeyDown}
                  disabled={isLoading || isTranscribing}
                  placeholder={isDictating ? "Listening — speak now…" : "Ask a legal question…"}
                  className="w-full px-4 pt-3 pb-2 bg-transparent text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none resize-none leading-relaxed disabled:opacity-50"
                  style={{ overflowY: "hidden" }}
                />

                {/* Toolbar row — [left: attach + fix] [right: mic + phone + send] */}
                <div className="flex items-center justify-between px-3 pb-3">

                  {/* Left tools */}
                  <div className="flex items-center gap-1">
                    {/* State jurisdiction selector */}
                    <select
                      value={selectedState}
                      onChange={e => setSelectedState(e.target.value)}
                      title="Select state for jurisdiction-specific legal advice"
                      className={`text-[11px] rounded-lg px-2 py-1.5 border cursor-pointer transition-all focus:outline-none max-w-[128px] ${
                        selectedState
                          ? "border-blue-300 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                          : "border-slate-200 dark:border-slate-700 bg-transparent text-slate-500 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-600"
                      }`}
                    >
                      <option value="">📍 All India</option>
                      {INDIAN_STATES.map(s => (
                        <option key={s.value} value={s.value}>{s.label}</option>
                      ))}
                    </select>

                    {/* Document upload */}
                    <button
                      onClick={() => docInputRef.current?.click()}
                      disabled={isLoading || isDocUploading}
                      title="Attach document (PDF / DOCX / image)"
                      className={`w-8 h-8 flex items-center justify-center rounded-lg transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                        extractedDocText
                          ? "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20"
                          : "text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
                      }`}
                    >
                      {isDocUploading
                        ? <Loader2 className="h-4 w-4 animate-spin" />
                        : <Paperclip className="h-4 w-4" />}
                    </button>

                    {/* Fix transcription — only after voice input */}
                    {hasUsedVoice && !isDictating && !isTranscribing && inputText.trim() && (
                      <button
                        onClick={fixTranscript}
                        disabled={fixStatus === "fixing"}
                        title={fixButtonLabel}
                        className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors disabled:opacity-50 ${
                          fixStatus === "fixed"
                            ? "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20"
                            : "text-violet-600 dark:text-violet-400 hover:bg-violet-50 dark:hover:bg-violet-900/20"
                        }`}
                      >
                        <Wand2 className="h-3.5 w-3.5" />
                        <span>{fixStatus === "fixing" ? "Fixing…" : fixStatus === "fixed" ? "Fixed" : "Fix errors"}</span>
                      </button>
                    )}
                  </div>

                  {/* Right tools */}
                  <div className="flex items-center gap-1.5">
                    {/* Mic / dictation */}
                    <button
                      onClick={toggleDictation}
                      disabled={isTranscribing || isLoading}
                      title={isDictating ? "Stop recording" : "Voice to text"}
                      className={`w-8 h-8 flex items-center justify-center rounded-lg transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                        isDictating
                          ? "bg-red-500 text-white shadow-md shadow-red-500/40"
                          : "text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
                      }`}
                    >
                      {isDictating ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                    </button>

                    {/* Voice conversation */}
                    <button
                      onClick={startVoiceConversation}
                      disabled={isLoading || isDictating || isVoiceConvOpen}
                      title="Voice conversation"
                      className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-500 dark:text-slate-400 hover:bg-violet-100 dark:hover:bg-violet-900/20 hover:text-violet-600 dark:hover:text-violet-400 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <PhoneCall className="h-4 w-4" />
                    </button>

                    {/* Send — filled circle like ChatGPT */}
                    <button
                      onClick={handleSend}
                      disabled={(!inputText.trim() && !extractedDocText) || isLoading || isDocUploading}
                      aria-label="Send"
                      className="w-9 h-9 flex items-center justify-center rounded-full bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-sm"
                    >
                      {isLoading
                        ? <Loader2 className="h-4 w-4 animate-spin" />
                        : <Send    className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
              </div>

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
