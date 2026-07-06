import { FileText, MessageSquare, Shield, ArrowRight, Scale, TrendingUp, Sparkles, CheckCircle, Star } from "lucide-react";
import { Link } from "react-router-dom";
import Layout from "../components/Layout";

const FEATURES = [
  {
    icon: MessageSquare,
    title: "Legal Chatbot",
    desc: "Chat with our AI to understand your legal situation and explore your options in plain English.",
    link: "/chat",
    iconBg: "bg-gradient-to-br from-blue-500 to-cyan-500",
    cardBg: "bg-gradient-to-br from-blue-50 to-cyan-50",
    border: "hover:border-blue-200",
  },
  {
    icon: TrendingUp,
    title: "Case Predictor",
    desc: "Predict your case outcome using AI trained on thousands of Indian High Court judgments.",
    link: "/predict",
    iconBg: "bg-gradient-to-br from-violet-500 to-indigo-500",
    cardBg: "bg-gradient-to-br from-violet-50 to-indigo-50",
    border: "hover:border-violet-200",
  },
  {
    icon: FileText,
    title: "Document Analysis",
    desc: "Upload legal documents and get instant plain-language explanations and risk scores.",
    link: "/upload",
    iconBg: "bg-gradient-to-br from-teal-500 to-emerald-500",
    cardBg: "bg-gradient-to-br from-teal-50 to-emerald-50",
    border: "hover:border-teal-200",
  },
  {
    icon: Shield,
    title: "Know Your Rights",
    desc: "Explore your constitutional and consumer rights under Indian law, clearly explained.",
    link: "/rights",
    iconBg: "bg-gradient-to-br from-orange-500 to-amber-400",
    cardBg: "bg-gradient-to-br from-orange-50 to-amber-50",
    border: "hover:border-orange-200",
  },
];

const STATS = [
  { value: "71,000+", label: "Indian Court Cases" },
  { value: "72.8%",   label: "Prediction Accuracy" },
  { value: "5+",      label: "AI Legal Tools" },
];

/* ── Faded SVG illustrations ─────────────────────────────────────────────── */

function ScalesOfJustice({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 260 320" fill="none" xmlns="http://www.w3.org/2000/svg" className={className} aria-hidden>
      {/* Base */}
      <rect x="120" y="278" width="20" height="32" rx="4" fill="currentColor" />
      <rect x="86" y="272" width="88" height="10" rx="5" fill="currentColor" />
      {/* Pillar */}
      <rect x="128" y="60" width="4" height="216" rx="2" fill="currentColor" />
      {/* Top star / ornament */}
      <circle cx="130" cy="52" r="10" fill="currentColor" />
      <circle cx="130" cy="52" r="5" fill="white" fillOpacity="0.5" />
      {/* Beam */}
      <rect x="22" y="96" width="216" height="5" rx="2.5" fill="currentColor" />
      {/* Left suspension lines */}
      <line x1="44" y1="101" x2="44" y2="150" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeDasharray="5 4" />
      <line x1="84" y1="101" x2="84" y2="150" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeDasharray="5 4" />
      {/* Right suspension lines */}
      <line x1="176" y1="101" x2="176" y2="150" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeDasharray="5 4" />
      <line x1="216" y1="101" x2="216" y2="150" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeDasharray="5 4" />
      {/* Left pan */}
      <path d="M24 150 Q64 178 104 150" stroke="currentColor" strokeWidth="3.5" fill="none" strokeLinecap="round" />
      <line x1="24" y1="150" x2="104" y2="150" stroke="currentColor" strokeWidth="1.5" strokeOpacity="0.4" />
      {/* Right pan (slightly higher = balanced / slightly tipped) */}
      <path d="M156 150 Q196 178 236 150" stroke="currentColor" strokeWidth="3.5" fill="none" strokeLinecap="round" />
      <line x1="156" y1="150" x2="236" y2="150" stroke="currentColor" strokeWidth="1.5" strokeOpacity="0.4" />
    </svg>
  );
}

function Gavel({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg" className={className} aria-hidden>
      {/* Handle */}
      <rect x="100" y="90" width="88" height="22" rx="11" fill="currentColor" transform="rotate(45 100 90)" />
      {/* Head */}
      <rect x="20" y="55" width="80" height="42" rx="10" fill="currentColor" />
      {/* Strike plate */}
      <rect x="20" y="55" width="14" height="42" rx="7" fill="currentColor" fillOpacity="0.5" />
      {/* Sound block */}
      <rect x="30" y="148" width="100" height="20" rx="6" fill="currentColor" />
    </svg>
  );
}

function LegalDocument({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 160 200" fill="none" xmlns="http://www.w3.org/2000/svg" className={className} aria-hidden>
      {/* Paper */}
      <rect x="10" y="10" width="140" height="180" rx="10" fill="currentColor" fillOpacity="0.15" />
      <rect x="10" y="10" width="140" height="180" rx="10" stroke="currentColor" strokeWidth="3" />
      {/* Fold corner */}
      <path d="M110 10 L150 50 L110 50 Z" fill="currentColor" fillOpacity="0.25" />
      <path d="M110 10 L150 50 L110 50 Z" stroke="currentColor" strokeWidth="2" />
      {/* Lines of text */}
      <rect x="28" y="68" width="84" height="6" rx="3" fill="currentColor" />
      <rect x="28" y="84" width="104" height="6" rx="3" fill="currentColor" />
      <rect x="28" y="100" width="94" height="6" rx="3" fill="currentColor" />
      <rect x="28" y="116" width="74" height="6" rx="3" fill="currentColor" />
      <rect x="28" y="140" width="60" height="6" rx="3" fill="currentColor" fillOpacity="0.5" />
      {/* Seal */}
      <circle cx="110" cy="160" r="18" stroke="currentColor" strokeWidth="2.5" strokeDasharray="4 3" />
      <circle cx="110" cy="160" r="10" fill="currentColor" fillOpacity="0.2" />
    </svg>
  );
}

/* ─────────────────────────────────────────────────────────────────────────── */

const Home = () => {
  return (
    <Layout>
      <div className="relative overflow-hidden -mt-16">

        {/* ── Hero ──────────────────────────────────────────────────────────── */}
        <div className="relative overflow-hidden bg-gradient-to-b from-sky-50 via-blue-50 to-white dark:from-[#060d1a] dark:via-[#080f20] dark:to-[#060d1a] pt-16 min-h-screen flex items-center">

          {/* Soft blobs */}
          <div className="absolute -top-24 -left-24 w-[500px] h-[500px] bg-blue-200/40 dark:bg-blue-500/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute top-1/2 -right-32 w-[400px] h-[400px] bg-cyan-200/30 dark:bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[700px] h-[300px] bg-indigo-100/40 dark:bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />

          {/* ── Faded legal illustrations ── */}
          {/* Scales — right side, large */}
          <ScalesOfJustice className="absolute right-[-40px] top-1/2 -translate-y-1/2 w-[340px] h-[340px] text-blue-400 opacity-[0.10] pointer-events-none select-none" />
          {/* Gavel — bottom left */}
          <Gavel className="absolute left-8 bottom-28 w-[180px] h-[180px] text-blue-500 opacity-[0.09] pointer-events-none select-none" />
          {/* Document — top left */}
          <LegalDocument className="absolute left-[-20px] top-24 w-[140px] h-[160px] text-blue-400 opacity-[0.08] pointer-events-none select-none" />
          {/* Small scales — far right top */}
          <ScalesOfJustice className="absolute right-1/4 top-10 w-[80px] h-[80px] text-indigo-400 opacity-[0.07] pointer-events-none select-none" />

          <div className="container mx-auto px-4 py-12 relative z-10 w-full">
            <div className="mx-auto max-w-3xl text-center">

              {/* Badge */}
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-blue-200 bg-white/80 backdrop-blur-sm text-blue-700 text-sm font-semibold mb-7 shadow-sm dark:border-blue-500/30 dark:bg-slate-800/80 dark:text-blue-300">
                <Sparkles className="h-3.5 w-3.5 text-blue-500" />
                AI-Powered Legal Platform for India
                <span className="flex h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
              </div>

              {/* Heading */}
              <h1 className="text-5xl md:text-7xl font-black tracking-tighter mb-6 leading-[0.95]">
                <span className="text-slate-900 dark:text-white">Smart Legal</span>
                <br />
                <span className="bg-gradient-to-r from-blue-600 via-cyan-500 to-blue-500 bg-clip-text text-transparent">
                  Assistant
                </span>
              </h1>

              {/* Subtitle */}
              <p className="text-lg md:text-xl text-slate-500 dark:text-slate-300 font-medium leading-relaxed max-w-2xl mx-auto mb-10">
                Your AI-powered guide to legal documents, queries, and rights.
                Making law accessible for every Indian citizen.
              </p>

              {/* CTAs */}
              <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
                <Link
                  to="/chat"
                  className="group inline-flex items-center justify-center rounded-full bg-gradient-to-r from-blue-600 to-cyan-500 px-8 py-4 text-base font-bold text-white shadow-lg shadow-blue-300/50 hover:shadow-xl hover:shadow-blue-300/60 hover:scale-105 hover:-translate-y-0.5 transition-all duration-300"
                >
                  Get Started Free
                  <ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" />
                </Link>
                <Link
                  to="/rights"
                  className="inline-flex items-center justify-center rounded-full border-2 border-slate-200 bg-white px-8 py-4 text-base font-bold text-slate-700 hover:border-blue-300 hover:text-blue-600 hover:bg-blue-50 hover:scale-105 hover:-translate-y-0.5 transition-all duration-300 shadow-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:border-blue-400 dark:hover:text-blue-300 dark:hover:bg-blue-900/20"
                >
                  Know Your Rights
                </Link>
              </div>

              {/* Stats pill */}
              <div className="inline-flex flex-col sm:flex-row items-center gap-6 sm:gap-10 bg-white/70 backdrop-blur-sm border border-slate-100 rounded-2xl px-8 py-5 shadow-sm dark:bg-slate-800/60 dark:border-slate-700">
                {STATS.map((s, i) => (
                  <div key={i} className={`text-center ${i < STATS.length - 1 ? "sm:pr-10 sm:border-r sm:border-slate-200 dark:sm:border-slate-700" : ""}`}>
                    <div className="text-2xl font-black text-slate-900 dark:text-white tabular-nums">{s.value}</div>
                    <div className="text-xs text-slate-400 dark:text-slate-500 font-semibold uppercase tracking-widest mt-0.5">{s.label}</div>
                  </div>
                ))}
              </div>

            </div>
          </div>

          {/* Bottom wave into white */}
          <div className="absolute bottom-0 left-0 right-0 h-16 overflow-hidden pointer-events-none">
            <svg viewBox="0 0 1440 64" preserveAspectRatio="none" className="w-full h-full fill-white dark:fill-[#060d1a]">
              <path d="M0,32 C360,64 1080,0 1440,32 L1440,64 L0,64 Z" />
            </svg>
          </div>
        </div>

        {/* ── Features ──────────────────────────────────────────────────────── */}
        <div className="bg-white dark:bg-[#060d1a]">
          <div className="container mx-auto px-4 py-20 max-w-5xl">

            <div className="text-center mb-14">
              <p className="text-xs font-bold text-blue-600 dark:text-blue-400 uppercase tracking-[0.2em] mb-3">What We Offer</p>
              <h2 className="text-4xl md:text-5xl font-black text-slate-900 dark:text-white mb-4 tracking-tight">
                Everything you need, legally
              </h2>
              <p className="text-lg text-slate-400 max-w-xl mx-auto">
                From understanding your rights to resolving disputes — our AI handles it all.
              </p>
            </div>

            {/* Mediation — featured card */}
            <div className="mb-5">
              <Link
                to="/mediation"
                className="group relative flex flex-col sm:flex-row items-start sm:items-center gap-6 rounded-2xl border border-blue-100 bg-gradient-to-r from-blue-50 via-indigo-50/50 to-cyan-50 px-7 py-6 hover:border-blue-200 hover:shadow-xl hover:shadow-blue-100/60 transition-all duration-300 overflow-hidden dark:border-blue-800/40 dark:from-blue-900/20 dark:via-indigo-900/10 dark:to-blue-900/10 dark:hover:border-blue-700/60 dark:hover:shadow-blue-900/20"
              >
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 bg-gradient-to-r from-blue-500/[0.03] to-cyan-500/[0.03] transition-opacity duration-300 pointer-events-none rounded-2xl" />
                <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-200/60 group-hover:scale-105 transition-transform">
                  <Scale className="h-7 w-7 text-white" />
                </div>
                <div className="flex-1 min-w-0 relative z-10">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-bold text-slate-900 dark:text-white text-lg">AI-Mediated Dispute Resolution</h3>
                    <span className="text-[10px] font-bold bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-2.5 py-0.5 rounded-full">NEW</span>
                  </div>
                  <p className="text-sm text-slate-500 leading-relaxed">
                    Both parties submit their side privately. Our AI mediates, detects bias, and proposes a fair settlement backed by 71,000+ Indian court cases.
                  </p>
                </div>
                <div className="flex items-center gap-1.5 text-blue-600 font-semibold text-sm flex-shrink-0 relative z-10 group-hover:gap-3 transition-all">
                  Try mediation <ArrowRight className="h-4 w-4" />
                </div>
              </Link>
            </div>

            {/* 4 feature cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              {FEATURES.map((f) => {
                const Icon = f.icon;
                return (
                  <Link
                    key={f.link}
                    to={f.link}
                    className={`group flex flex-col p-5 rounded-2xl border border-slate-100 ${f.cardBg} ${f.border} hover:shadow-lg transition-all duration-300 hover:-translate-y-1 dark:border-slate-700/60 dark:bg-slate-800/40 dark:hover:bg-slate-800/70 dark:hover:border-slate-600`}
                  >
                    <div className={`w-10 h-10 rounded-xl ${f.iconBg} flex items-center justify-center mb-4 shadow-md group-hover:scale-110 transition-transform duration-300`}>
                      <Icon className="h-5 w-5 text-white" />
                    </div>
                    <h3 className="font-bold text-slate-900 dark:text-white mb-2 text-sm">{f.title}</h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed flex-1">{f.desc}</p>
                    <div className="mt-4 flex items-center gap-1 text-xs font-semibold text-slate-300 group-hover:text-slate-600 dark:text-slate-600 dark:group-hover:text-blue-400 transition-colors">
                      Open <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>

        {/* ── Trust strip ───────────────────────────────────────────────────── */}
        <div className="bg-slate-50 border-y border-slate-100 py-8 dark:bg-[#06101f] dark:border-slate-800/60">
          <div className="container mx-auto px-4 max-w-4xl">
            <div className="flex flex-col sm:flex-row items-center justify-center gap-6 sm:gap-12 text-center">
              {[
                { icon: Star,        text: "Trained on real Indian court data" },
                { icon: CheckCircle, text: "InLegalBERT — purpose-built legal AI" },
                { icon: Shield,      text: "Private & secure — data never shared" },
              ].map(({ icon: Icon, text }, i) => (
                <div key={i} className="flex items-center gap-2 text-slate-500 text-sm font-medium">
                  <Icon className="h-4 w-4 text-blue-500 flex-shrink-0" />
                  {text}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── CTA ───────────────────────────────────────────────────────────── */}
        <div className="relative overflow-hidden bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-700 py-28">
          {/* Faded scales in CTA background */}
          <ScalesOfJustice className="absolute right-12 top-1/2 -translate-y-1/2 w-[240px] h-[240px] text-white opacity-[0.06] pointer-events-none select-none" />
          <Gavel className="absolute left-12 top-1/2 -translate-y-1/2 w-[160px] h-[160px] text-white opacity-[0.06] pointer-events-none select-none" />

          <div className="absolute top-0 left-1/4 w-96 h-96 bg-white/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-cyan-300/10 rounded-full blur-3xl pointer-events-none" />

          <div className="container mx-auto px-4 text-center relative z-10">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/15 border border-white/25 text-white/90 text-xs font-semibold mb-6">
              <CheckCircle className="h-3.5 w-3.5" />
              Free for all citizens
            </div>
            <h2 className="text-4xl md:text-5xl font-black text-white mb-5 tracking-tight">
              Ready to get legal help?
            </h2>
            <p className="text-lg text-blue-100/80 mb-10 max-w-lg mx-auto leading-relaxed">
              Join thousands of Indians who have simplified their legal journey with our AI assistant.
            </p>
            <Link
              to="/chat"
              className="inline-flex items-center justify-center rounded-full bg-white px-10 py-4 text-base font-bold text-blue-700 shadow-xl shadow-blue-900/30 hover:shadow-2xl hover:bg-blue-50 hover:scale-105 transition-all duration-300"
            >
              Start Free Consultation
              <ArrowRight className="ml-2 h-5 w-5" />
            </Link>
          </div>
        </div>

      </div>
    </Layout>
  );
};

export default Home;
