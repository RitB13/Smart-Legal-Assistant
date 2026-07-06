import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2, MessageCircle, Zap } from "lucide-react";
import Layout from "../components/Layout";

// ── Types ─────────────────────────────────────────────────────────────────────

type ChatMode = "chat" | "simulate";

interface Message {
  id: string;
  text: string;
  sender: "user" | "bot";
  timestamp: Date;
}

// ── Welcome messages per mode ─────────────────────────────────────────────────

const WELCOME: Record<ChatMode, string> = {
  chat:
    "Hello! I'm your Smart Legal Assistant. Ask me anything about legal situations, your rights, applicable laws, or any legal matter under Indian law. I'm here to help you understand your options.",
  simulate:
    "Consequence Simulator is active. Describe a planned action or situation and I'll analyse the potential legal consequences, applicable statutes, penalties, and safer alternatives — before you act.",
};

// ── Component ─────────────────────────────────────────────────────────────────

const ChatNewV2 = () => {
  useEffect(() => { window.scrollTo({ top: 0, behavior: "auto" }); }, []);

  const [mode, setMode]         = useState<ChatMode>("chat");
  const [messages, setMessages] = useState<Message[]>([
    {
      id:        "welcome",
      text:      WELCOME.chat,
      sender:    "bot",
      timestamp: new Date(),
    },
  ]);
  const [inputText, setInputText]   = useState("");
  const [isLoading, setIsLoading]   = useState(false);

  const messagesEndRef    = useRef<HTMLDivElement>(null);
  const inputRef          = useRef<HTMLInputElement>(null);

  const apiUrl    = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const authToken = localStorage.getItem("sla_token");
  const authHeader = authToken ? { Authorization: `Bearer ${authToken}` } : {};

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Switch mode — append a bot message announcing the switch
  const switchMode = (next: ChatMode) => {
    if (next === mode || isLoading) return;
    setMode(next);
    setInputText("");
    const switchMsg: Message = {
      id:        Date.now().toString(),
      text:      WELCOME[next],
      sender:    "bot",
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, switchMsg]);
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  // ── API calls ────────────────────────────────────────────────────────────

  const callChat = async (query: string) => {
    const controller = new AbortController();
    const tid = setTimeout(() => controller.abort(), 60000);
    try {
      const res = await fetch(`${apiUrl}/query`, {
        method:  "POST",
        headers: { "Content-Type": "application/json", ...authHeader },
        body:    JSON.stringify({ query }),
        signal:  controller.signal,
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
  };

  const callSimulate = async (query: string) => {
    const controller = new AbortController();
    const tid = setTimeout(() => controller.abort(), 60000);
    try {
      const res = await fetch(`${apiUrl}/consequence-simulator/simulate`, {
        method:  "POST",
        headers: { "Content-Type": "application/json", ...authHeader },
        body:    JSON.stringify({ action_description: query, jurisdiction: "India", language: "en" }),
        signal:  controller.signal,
      });
      clearTimeout(tid);
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const d = await res.json();

      let text = d.explanation || "Unable to generate analysis.";
      if (d.risk_level) {
        const pct = Math.round((d.confidence_score || 0) * 100);
        text += `\n\nRisk Level: ${d.risk_level}  (Confidence: ${pct}%)`;
      }
      if (d.applicable_laws?.length)
        text += `\n\nApplicable Laws:\n${d.applicable_laws.map((l: any) => `• ${l.name}${l.section ? ` — ${l.section}` : ""}`).join("\n")}`;
      if (d.penalties?.length)
        text += `\n\nPotential Penalties:\n${d.penalties.map((p: any) => `• ${p.description} (${p.severity})`).join("\n")}`;
      if (d.safer_alternatives?.length)
        text += `\n\nSafer Alternatives:\n${d.safer_alternatives.map((a: any) => `• ${a.alternative}: ${a.explanation}`).join("\n")}`;

      return text;
    } catch (e) {
      clearTimeout(tid);
      if (e instanceof Error && e.name === "AbortError")
        return "The analysis timed out. Please try again with a simpler query.";
      return "Sorry, the consequence analysis failed. Please try again.";
    }
  };

  // ── Send ─────────────────────────────────────────────────────────────────

  const handleSend = async () => {
    const text = inputText.trim();
    if (!text || isLoading) return;

    const userMsg: Message = {
      id:        Date.now().toString(),
      text,
      sender:    "user",
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInputText("");
    setIsLoading(true);

    const reply = mode === "simulate" ? await callSimulate(text) : await callChat(text);

    const botMsg: Message = {
      id:        (Date.now() + 1).toString(),
      text:      reply,
      sender:    "bot",
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, botMsg]);
    setIsLoading(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <Layout>
      <div className="min-h-screen flex flex-col bg-gradient-to-br from-blue-50 via-white to-purple-50 -mt-16 pt-24 pb-8">
        <div className="container mx-auto px-4 max-w-3xl flex-1 flex flex-col">

          {/* Header */}
          <div className="text-center mb-6 animate-fade-up">
            <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
              Legal Assistant
            </h1>
            <p className="text-muted-foreground text-sm">
              Ask legal questions or simulate the consequences of a planned action
            </p>
          </div>

          {/* Mode toggle */}
          <div className="flex justify-center mb-4 animate-fade-up">
            <div className="inline-flex bg-gray-100 rounded-xl p-1 gap-1">
              <button
                onClick={() => switchMode("chat")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  mode === "chat"
                    ? "bg-white shadow-sm text-blue-700 border border-blue-100"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                <MessageCircle className="w-4 h-4" />
                Legal Q&amp;A
              </button>
              <button
                onClick={() => switchMode("simulate")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  mode === "simulate"
                    ? "bg-white shadow-sm text-purple-700 border border-purple-100"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                <Zap className="w-4 h-4" />
                Consequence Simulator
              </button>
            </div>
          </div>

          {/* Chat window */}
          <div className="flex-1 flex flex-col rounded-2xl border-2 border-gray-200 bg-white shadow-xl hover:shadow-2xl transition-shadow duration-300 overflow-hidden">

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin scrollbar-thumb-blue-200 scrollbar-track-gray-100">
              {messages.map((msg, idx) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"} animate-fade-up`}
                  style={{ animationDelay: `${idx * 0.03}s` }}
                >
                  <div className={`flex max-w-[85%] ${msg.sender === "user" ? "flex-row-reverse" : "flex-row"} items-start gap-3`}>
                    {/* Avatar */}
                    <div
                      className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                        msg.sender === "user"
                          ? "bg-gradient-to-br from-blue-500 to-purple-500"
                          : mode === "simulate"
                          ? "bg-gradient-to-br from-purple-400 to-pink-500"
                          : "bg-gradient-to-br from-green-400 to-blue-500"
                      }`}
                    >
                      {msg.sender === "user"
                        ? <User className="h-4 w-4 text-white" />
                        : <Bot className="h-4 w-4 text-white" />
                      }
                    </div>

                    {/* Bubble */}
                    <div
                      className={`rounded-2xl px-4 py-3 ${
                        msg.sender === "user"
                          ? "bg-gradient-to-br from-blue-500 to-purple-600 text-white rounded-br-none shadow-md"
                          : "bg-gray-100 text-foreground rounded-bl-none shadow-sm"
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.text}</p>
                      <p className="text-xs mt-1.5 opacity-60">
                        {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </p>
                    </div>
                  </div>
                </div>
              ))}

              {/* Typing indicator */}
              {isLoading && (
                <div className="flex justify-start animate-fade-up">
                  <div className="flex items-start gap-3">
                    <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                      mode === "simulate"
                        ? "bg-gradient-to-br from-purple-400 to-pink-500"
                        : "bg-gradient-to-br from-green-400 to-blue-500"
                    }`}>
                      <Bot className="h-4 w-4 text-white" />
                    </div>
                    <div className="bg-gray-100 rounded-2xl rounded-bl-none px-4 py-3 shadow-sm">
                      <div className="flex space-x-1.5">
                        {[0, 150, 300].map(delay => (
                          <div
                            key={delay}
                            className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                            style={{ animationDelay: `${delay}ms` }}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input bar */}
            <div className="border-t border-gray-200 bg-gray-50 p-4 flex-shrink-0">
              <div className="flex gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputText}
                  onChange={e => setInputText(e.target.value)}
                  onKeyPress={handleKeyPress}
                  disabled={isLoading}
                  placeholder={
                    mode === "simulate"
                      ? "Describe your planned action or situation…"
                      : "Ask a legal question…"
                  }
                  className="flex-1 px-4 py-3 rounded-xl border-2 border-gray-200 bg-white text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent transition-all disabled:opacity-50"
                />
                <button
                  onClick={handleSend}
                  disabled={!inputText.trim() || isLoading}
                  className="inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-blue-500 to-purple-600 px-4 py-3 text-white hover:shadow-lg transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {isLoading
                    ? <Loader2 className="h-5 w-5 animate-spin" />
                    : <Send className="h-5 w-5" />
                  }
                </button>
              </div>

              {/* Mode hint */}
              <p className="text-xs text-gray-400 mt-2 text-center">
                {mode === "simulate"
                  ? "Describing a planned action? Switch to Consequence Simulator above for richer analysis."
                  : "Want to predict a case outcome? Visit the"
                }
                {mode === "chat" && (
                  <a href="/predict" className="text-blue-500 hover:underline ml-1">Case Outcome Predictor →</a>
                )}
              </p>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default ChatNewV2;
