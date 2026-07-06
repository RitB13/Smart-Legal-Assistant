import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Bot, User, Loader2, Plus, Trash2, MessageSquare, Menu, X, Scale } from "lucide-react";
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

// ── Constants ─────────────────────────────────────────────────────────────────

const SUGGESTIONS = [
  "What are my rights as a tenant in India?",
  "Explain the RTI Act 2005 and how to file an application",
  "What is Section 498A of the IPC?",
  "How do I file a consumer complaint against a company?",
];

// ── Component ─────────────────────────────────────────────────────────────────

const ChatPage = () => {
  const [conversations, setConversations] = useState<ConvSummary[]>([]);
  const [activeConvId, setActiveConvId]   = useState<string | null>(null);
  const [messages, setMessages]           = useState<ChatMessage[]>([]);
  const [inputText, setInputText]         = useState("");
  const [isLoading, setIsLoading]         = useState(false);
  const [sidebarOpen, setSidebarOpen]     = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef       = useRef<HTMLInputElement>(null);
  const activeConvRef  = useRef<string | null>(null);

  const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

  const authHeaders = useCallback((): Record<string, string> => {
    const token = localStorage.getItem("sla_token");
    return token
      ? { "Content-Type": "application/json", Authorization: `Bearer ${token}` }
      : { "Content-Type": "application/json" };
  }, []);

  // Keep ref in sync so async callbacks always have the latest id
  useEffect(() => { activeConvRef.current = activeConvId; }, [activeConvId]);

  // Scroll to bottom whenever messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Load conversation list on mount
  useEffect(() => {
    fetchConversations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── API helpers ──────────────────────────────────────────────────────────────

  async function fetchConversations() {
    try {
      const res = await fetch(`${apiUrl}/conversations?limit=50`, { headers: authHeaders() });
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
    } catch {
      // network error — sidebar stays empty, chat still works
    }
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
    } catch {
      return null;
    }
  }

  async function loadConversation(id: string) {
    try {
      const res = await fetch(`${apiUrl}/conversations/${id}`, { headers: authHeaders() });
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
    } catch {
      // leave messages as-is
    }
  }

  async function appendMessage(convId: string, role: string, content: string) {
    try {
      await fetch(`${apiUrl}/conversations/${convId}/messages`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ role, content }),
      });
    } catch {
      // fire-and-forget; UI already updated
    }
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

  // ── Actions ──────────────────────────────────────────────────────────────────

  async function handleSend() {
    const text = inputText.trim();
    if (!text || isLoading) return;
    setInputText("");
    setIsLoading(true);

    // Ensure there's an active conversation
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

    // Optimistically add user message to UI
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);

    // Get AI reply
    const reply = await callQuery(text);

    const botMsg: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      content: reply,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, botMsg]);

    // Persist to MongoDB (fire-and-forget)
    if (convId) {
      appendMessage(convId, "user", text);
      appendMessage(convId, "assistant", reply);
    }

    setIsLoading(false);
  }

  async function handleSelectConversation(id: string) {
    if (id === activeConvRef.current) {
      setSidebarOpen(false);
      return;
    }
    setActiveConvId(id);
    setMessages([]);
    setIsLoading(true);
    setSidebarOpen(false);
    await loadConversation(id);
    setIsLoading(false);
  }

  function handleNewChat() {
    setActiveConvId(null);
    setMessages([]);
    setSidebarOpen(false);
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  async function handleDelete(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await fetch(`${apiUrl}/conversations/${id}`, {
        method: "DELETE",
        headers: authHeaders(),
      });
    } catch {
      // ignore
    }
    setConversations(prev => prev.filter(c => c.id !== id));
    if (activeConvRef.current === id) {
      setActiveConvId(null);
      setMessages([]);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-screen bg-white dark:bg-[#060d1a] overflow-hidden">

      {/* App header */}
      <Header />

      {/* Body: sidebar + main — fills remaining height */}
      <div className="flex flex-1 min-h-0">

        {/* ── Sidebar ──────────────────────────────────────────────────────── */}

        {/* Mobile overlay backdrop */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-20 bg-black/40 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        <aside
          className={`
            flex flex-col w-64 flex-shrink-0 border-r border-slate-200 dark:border-slate-700/50
            bg-slate-50 dark:bg-[#0a0f1e]
            md:relative md:flex md:translate-x-0
            fixed inset-y-0 left-0 z-30 transition-transform duration-300
            ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
          `}
          style={{ top: "56px" }}
        >
          {/* New chat */}
          <div className="p-3 flex-shrink-0">
            <button
              onClick={handleNewChat}
              className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:border-blue-300 dark:hover:border-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-colors"
            >
              <Plus className="h-4 w-4" />
              New chat
            </button>
          </div>

          {/* Conversations list */}
          <div className="flex-1 overflow-y-auto px-2 pb-4">
            {conversations.length === 0 ? (
              <p className="text-xs text-slate-400 dark:text-slate-600 text-center mt-10 px-4">
                No conversations yet.
                <br />Start a new chat above.
              </p>
            ) : (
              <>
                <p className="text-[10px] font-semibold text-slate-400 dark:text-slate-600 uppercase tracking-wider px-2 mb-1">
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
                      onClick={e => handleDelete(conv.id, e)}
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

        {/* ── Main panel ───────────────────────────────────────────────────── */}

        <main className="flex-1 flex flex-col min-w-0 bg-white dark:bg-[#060d1a]">

          {/* Mobile top bar — hamburger + current chat title */}
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

          {/* Messages area — scrolls internally */}
          <div className="flex-1 overflow-y-auto">
            {messages.length === 0 ? (

              /* ── Welcome / empty state ─────────────────────────────────── */
              <div className="h-full flex flex-col items-center justify-center p-8 text-center">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center mb-4 shadow-lg">
                  <Scale className="h-7 w-7 text-white" />
                </div>
                <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
                  Smart Legal Assistant
                </h2>
                <p className="text-sm text-slate-500 dark:text-slate-400 mb-8 max-w-sm leading-relaxed">
                  Ask any legal question about Indian law — rights, disputes,
                  procedures, or consequences.
                </p>

                {/* Suggestion chips */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
                  {SUGGESTIONS.map(s => (
                    <button
                      key={s}
                      onClick={() => {
                        setInputText(s);
                        setTimeout(() => inputRef.current?.focus(), 50);
                      }}
                      className="text-left px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 text-sm text-slate-700 dark:text-slate-300 hover:border-blue-300 dark:hover:border-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>

            ) : (

              /* ── Conversation messages ──────────────────────────────────── */
              <div className="max-w-3xl mx-auto w-full px-4 py-6 space-y-6">
                {messages.map(msg => (
                  <div
                    key={msg.id}
                    className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
                  >
                    {/* Avatar */}
                    <div
                      className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                        msg.role === "user"
                          ? "bg-gradient-to-br from-blue-500 to-purple-500"
                          : "bg-gradient-to-br from-teal-400 to-blue-500"
                      }`}
                    >
                      {msg.role === "user"
                        ? <User className="h-4 w-4 text-white" />
                        : <Bot className="h-4 w-4 text-white" />
                      }
                    </div>

                    {/* Bubble */}
                    <div className={`max-w-[80%] ${msg.role === "user" ? "items-end" : "items-start"} flex flex-col gap-1`}>
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

          {/* ── Input bar — always pinned at bottom ─────────────────────── */}
          <div className="flex-shrink-0 border-t border-slate-200 dark:border-slate-700/50 bg-white dark:bg-[#060d1a] p-4">
            <div className="max-w-3xl mx-auto">
              <div className="flex gap-2 items-center">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputText}
                  onChange={e => setInputText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={isLoading}
                  placeholder="Ask a legal question…"
                  className="flex-1 px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-800 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all disabled:opacity-50"
                />
                <button
                  onClick={handleSend}
                  disabled={!inputText.trim() || isLoading}
                  className="flex-shrink-0 w-11 h-11 flex items-center justify-center rounded-xl bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  aria-label="Send"
                >
                  {isLoading
                    ? <Loader2 className="h-4 w-4 animate-spin" />
                    : <Send className="h-4 w-4" />
                  }
                </button>
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
