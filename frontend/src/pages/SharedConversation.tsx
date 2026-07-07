import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { Bot, User, Scale, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";

interface SharedMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  language?: string;
  laws?: string[];
  suggestions?: string[];
  risk_level?: string;
}

interface SharedConv {
  id: string;
  title: string;
  language: string;
  messages: SharedMessage[];
  created_at: string;
}

const SharedConversation = () => {
  const { token } = useParams<{ token: string }>();
  const [conv, setConv] = useState<SharedConv | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${apiUrl}/shared/${token}`);
        if (!res.ok) throw new Error(res.status === 404 ? "This link has expired or does not exist." : "Failed to load conversation.");
        const data = await res.json();
        setConv(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load conversation.");
      } finally {
        setLoading(false);
      }
    }
    if (token) load();
  }, [token, apiUrl]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-white dark:bg-slate-900">
      <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
    </div>
  );

  if (error || !conv) return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-white dark:bg-slate-900 p-8 text-center">
      <AlertCircle className="h-12 w-12 text-red-400" />
      <p className="text-slate-600 dark:text-slate-400">{error || "Conversation not found."}</p>
      <Link to="/" className="text-blue-600 hover:underline text-sm">← Go to Smart Legal Assistant</Link>
    </div>
  );

  const dateStr = new Date(conv.created_at).toLocaleDateString("en-IN", { year: "numeric", month: "long", day: "numeric" });

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#060d1a]">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700/50 px-4 py-3">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
              <Scale className="h-4 w-4 text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">Smart Legal Assistant</p>
              <p className="text-[11px] text-slate-400">Shared conversation · {dateStr}</p>
            </div>
          </div>
          <Link
            to="/chat"
            className="text-xs font-medium px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors"
          >
            Ask your own question →
          </Link>
        </div>
      </div>

      {/* Conversation title */}
      <div className="max-w-3xl mx-auto px-4 pt-6 pb-2">
        <h1 className="text-lg font-bold text-slate-900 dark:text-white">{conv.title}</h1>
        <p className="text-xs text-slate-400 mt-0.5">{conv.messages.length} messages</p>
      </div>

      {/* Messages */}
      <div className="max-w-3xl mx-auto px-4 py-4 space-y-6 pb-16">
        {conv.messages.map((msg, idx) => (
          <div key={idx} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
            <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
              msg.role === "user"
                ? "bg-gradient-to-br from-blue-500 to-purple-500"
                : "bg-gradient-to-br from-teal-400 to-blue-500"
            }`}>
              {msg.role === "user" ? <User className="h-4 w-4 text-white" /> : <Bot className="h-4 w-4 text-white" />}
            </div>
            <div className={`max-w-[80%] flex flex-col gap-1 ${msg.role === "user" ? "items-end" : "items-start"}`}>
              <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-gradient-to-br from-blue-500 to-indigo-600 text-white rounded-br-sm"
                  : "bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 rounded-bl-sm border border-slate-100 dark:border-slate-700"
              }`}>
                {msg.content}
              </div>

              {/* Applicable Laws */}
              {msg.role === "assistant" && msg.laws && msg.laws.length > 0 && (
                <div className="w-full mt-1 rounded-xl border border-blue-200 dark:border-blue-800/50 bg-blue-50 dark:bg-blue-950/30 px-3 py-2.5">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <Scale className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400 flex-shrink-0" />
                    <span className="text-[11px] font-semibold text-blue-700 dark:text-blue-400 uppercase tracking-wider">Applicable Laws</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {msg.laws.map((law, i) => (
                      <span key={i} className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-medium bg-white dark:bg-blue-900/40 border border-blue-200 dark:border-blue-700/50 text-blue-700 dark:text-blue-300">
                        {law}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Suggested Steps */}
              {msg.role === "assistant" && msg.suggestions && msg.suggestions.length > 0 && (
                <div className="w-full mt-1 rounded-xl border border-emerald-200 dark:border-emerald-800/50 bg-emerald-50 dark:bg-emerald-950/30 px-3 py-2.5">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
                    <span className="text-[11px] font-semibold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider">Suggested Steps</span>
                  </div>
                  <ol className="space-y-1.5">
                    {msg.suggestions.map((s, i) => (
                      <li key={i} className="flex gap-2.5 items-start">
                        <span className="flex-shrink-0 w-5 h-5 rounded-full bg-emerald-100 dark:bg-emerald-900/50 border border-emerald-300 dark:border-emerald-700 text-[10px] font-bold text-emerald-700 dark:text-emerald-400 flex items-center justify-center mt-0.5">
                          {i + 1}
                        </span>
                        <span className="text-[12px] text-slate-700 dark:text-slate-300 leading-relaxed">{s}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {/* Legal risk gauge */}
              {msg.role === "assistant" && msg.risk_level && (() => {
                const clean = msg.risk_level.replace(/[^\w\s]/g, "").trim().toLowerCase();
                const label = clean.includes("critical") ? "Critical" : clean.includes("high") ? "High" : clean.includes("medium") ? "Medium" : "Low";
                const pct   = label === "Critical" ? 92 : label === "High" ? 68 : label === "Medium" ? 42 : 18;
                const barCls = label === "Critical" ? "bg-red-500" : label === "High" ? "bg-orange-500" : label === "Medium" ? "bg-yellow-400" : "bg-green-500";
                const txtCls = label === "Critical" ? "text-red-600" : label === "High" ? "text-orange-600" : label === "Medium" ? "text-yellow-600" : "text-green-600";
                return (
                  <div className="w-full mt-1 rounded-xl border border-slate-200 dark:border-slate-700/60 bg-white dark:bg-slate-800/50 px-3 py-2.5">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Legal Risk</span>
                      <span className={`text-[11px] font-bold ${txtCls}`}>{label}</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-700 overflow-hidden">
                      <div className={`h-full rounded-full ${barCls}`} style={{ width: `${pct}%` }} />
                    </div>
                    <div className="flex justify-between mt-1">
                      <span className="text-[9px] text-slate-400">Low</span>
                      <span className="text-[9px] text-slate-400">Critical</span>
                    </div>
                  </div>
                );
              })()}

              <span className="text-[10px] text-slate-400 px-1">
                {new Date(msg.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Disclaimer */}
      <div className="max-w-3xl mx-auto px-4 pb-8">
        <div className="rounded-xl border border-amber-200 dark:border-amber-700/40 bg-amber-50 dark:bg-amber-900/10 px-4 py-3 text-[11px] text-amber-700 dark:text-amber-400 leading-relaxed">
          <strong>Disclaimer:</strong> This is a shared AI-generated legal consultation. It is for informational purposes only and does not constitute legal advice. Please consult a qualified legal professional before taking any action.
        </div>
      </div>
    </div>
  );
};

export default SharedConversation;
