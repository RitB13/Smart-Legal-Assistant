import { useEffect, useRef, useState } from "react";
import Layout from "@/components/Layout";

// ── Constellation canvas ────────────────────────────────────────────────────
function ConstellationCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let rafId: number;
    let W = 0, H = 0;

    interface Star { x: number; y: number; r: number; vx: number; vy: number; a: number; }
    let stars: Star[] = [];

    function resize() {
      W = canvas!.width  = canvas!.offsetWidth;
      H = canvas!.height = canvas!.offsetHeight;
      stars = Array.from({ length: 70 }, () => ({
        x:  Math.random() * W,
        y:  Math.random() * H,
        r:  Math.random() * 1.3 + 0.4,
        vx: (Math.random() - 0.5) * 0.18,
        vy: (Math.random() - 0.5) * 0.18,
        a:  Math.random(),
      }));
    }

    function draw() {
      ctx!.clearRect(0, 0, W, H);
      const isDark =
        document.documentElement.classList.contains("dark") ||
        document.documentElement.getAttribute("data-theme") === "dark";

      for (let i = 0; i < stars.length; i++) {
        for (let j = i + 1; j < stars.length; j++) {
          const dx = stars[i].x - stars[j].x;
          const dy = stars[i].y - stars[j].y;
          const d  = Math.sqrt(dx * dx + dy * dy);
          if (d < 120) {
            ctx!.beginPath();
            const alpha = (1 - d / 120) * (isDark ? 0.22 : 0.12);
            ctx!.strokeStyle = `rgba(99,102,241,${alpha})`;
            ctx!.lineWidth = 0.7;
            ctx!.moveTo(stars[i].x, stars[i].y);
            ctx!.lineTo(stars[j].x, stars[j].y);
            ctx!.stroke();
          }
        }
      }

      stars.forEach(s => {
        ctx!.beginPath();
        ctx!.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        const isDarkNow =
          document.documentElement.classList.contains("dark") ||
          document.documentElement.getAttribute("data-theme") === "dark";
        ctx!.fillStyle = isDarkNow
          ? `rgba(148,163,184,${0.3 + s.a * 0.4})`
          : `rgba(99,102,241,${0.2 + s.a * 0.25})`;
        ctx!.fill();
        s.x += s.vx; s.y += s.vy;
        if (s.x < 0 || s.x > W) s.vx *= -1;
        if (s.y < 0 || s.y > H) s.vy *= -1;
        s.a = 0.5 + 0.5 * Math.sin(Date.now() / 1300 + s.x);
      });
      rafId = requestAnimationFrame(draw);
    }

    const onResize = () => resize();
    window.addEventListener("resize", onResize);
    resize();
    draw();
    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className="absolute inset-0 w-full h-full opacity-60 pointer-events-none"
    />
  );
}

// ── Photo with initials fallback ────────────────────────────────────────────
interface PhotoProps {
  src: string;
  alt: string;
  initials: string;
  gradient: [string, string];
  fontSize?: string;
}

function Photo({ src, alt, initials, gradient, fontSize = "2.25rem" }: PhotoProps) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <div
        className="w-full h-full flex items-center justify-center font-extrabold text-white select-none"
        style={{
          background: `linear-gradient(160deg, ${gradient[0]}, ${gradient[1]})`,
          fontSize,
        }}
      >
        {initials}
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      className="w-full h-full object-cover object-top"
      onError={() => setFailed(true)}
    />
  );
}

// ── Static data ─────────────────────────────────────────────────────────────
const PILLARS = [
  {
    icon:  "⚖️",
    title: "Legal Assistant",
    desc:  "An AI chatbot grounded in real Indian court precedents and statutes — ask any legal question and get a clear, cited answer in your language.",
  },
  {
    icon:  "📊",
    title: "Case Predictor",
    desc:  "ML models trained on thousands of Indian court cases estimate bail, acquittal, and conviction likelihoods for a given situation.",
  },
  {
    icon:  "🤝",
    title: "AI Mediation",
    desc:  "Both parties submit their account privately. The AI reads both sides and proposes a fair, court-data-backed settlement — no lawyer required.",
  },
  {
    icon:  "📖",
    title: "Know Your Rights",
    desc:  "A plain-language guide to fundamental Indian rights — property, labour, consumer, and more — no login needed.",
  },
];

const TEAM = [
  {
    src:      "/team/person1.jpg",
    name:     "Ritarshi Bandyopadhyay",
    initials: "RB",
    gradient: ["#3b82f6", "#6366f1"] as [string, string],
    accent:   "from-blue-500 to-indigo-500",
  },
  {
    src:      "/team/person2.jpg",
    name:     "Saini Guha Roy",
    initials: "SG",
    gradient: ["#10b981", "#0d9488"] as [string, string],
    accent:   "from-emerald-500 to-teal-500",
  },
  {
    src:      "/team/person3.jpg",
    name:     "Piyush Prasad",
    initials: "PP",
    gradient: ["#f43f5e", "#e11d48"] as [string, string],
    accent:   "from-rose-500 to-red-500",
  },
  {
    src:      "/team/person4.jpg",
    name:     "Anushreea De",
    initials: "AD",
    gradient: ["#8b5cf6", "#a78bfa"] as [string, string],
    accent:   "from-violet-500 to-purple-400",
  },
];

// ── Page ────────────────────────────────────────────────────────────────────
export default function AboutUs() {
  return (
    <Layout>
      {/* Outer wrapper: -mt-16 cancels Layout's pt-16, matching the Rights/CasePredictor pattern */}
      <div className="-mt-16">

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      {/* pt-36 = 144px ensures content clears the 56px sticky header with generous space */}
      <section className="relative overflow-hidden text-center pt-36 pb-20 bg-gradient-to-b from-blue-50 to-white dark:from-[#060d1a] dark:to-[#060d1a]">
        <ConstellationCanvas />
        <div className="relative z-10 max-w-2xl mx-auto px-6">

          {/* Badge */}
          <div className="inline-flex items-center gap-2 bg-blue-100 dark:bg-blue-500/15 border border-blue-200 dark:border-blue-500/30 rounded-full px-4 py-1.5 mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 dark:bg-blue-400 animate-pulse" />
            <span className="text-xs font-semibold text-blue-700 dark:text-blue-300 tracking-wide">
              Smart Legal Assistant
            </span>
          </div>

          <h1 className="text-5xl sm:text-6xl font-extrabold text-slate-900 dark:text-slate-100 leading-[1.1] mb-5 text-balance">
            Justice, made{" "}
            <span className="bg-gradient-to-r from-blue-500 to-violet-500 dark:from-blue-400 dark:to-violet-400 bg-clip-text text-transparent">
              accessible
            </span>{" "}
            for everyone.
          </h1>

          <p className="text-lg text-slate-600 dark:text-slate-400 leading-relaxed max-w-xl mx-auto">
            We built this because legal help in India shouldn't depend on how much money
            you have — one AI platform for legal advice, case prediction, and consequence
            awareness, in your language.
          </p>
        </div>
      </section>

      {/* ── Story ────────────────────────────────────────────────────────── */}
      <section className="py-20 bg-white dark:bg-[#060d1a]">
        <div className="max-w-5xl mx-auto px-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-16 items-start">

            {/* Narrative */}
            <div>
              <p className="text-xs font-bold tracking-widest uppercase text-blue-500 mb-3">
                Why We Built This
              </p>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white leading-tight text-balance">
                India has 1.4 billion people. Most can't afford legal advice.
              </h2>
              <div className="w-10 h-0.5 bg-gradient-to-r from-blue-500 to-indigo-500 rounded my-5" />
              <div className="space-y-4 text-slate-600 dark:text-slate-400 text-base leading-relaxed">
                <p>
                  Legal knowledge in India is locked behind jargon, court queues, and
                  consultation fees that most citizens can't afford. A tenant who doesn't
                  know their rights. A worker unaware of labour protections. A family
                  navigating divorce without any guidance.
                </p>
                <p>
                  <strong className="text-slate-800 dark:text-slate-200">Smart Legal Assistant</strong> is
                  an AI-powered legal platform trained on Indian law, built to give anyone a
                  clear, reliable first step toward understanding their rights.
                </p>
                <p>
                  From a casual question to a bail prediction to a consequence walkthrough —
                  Smart Legal Assistant meets you where you are, in the language you speak.
                </p>
              </div>
            </div>

            {/* Feature pillars */}
            <div className="flex flex-col gap-4">
              {PILLARS.map(p => (
                <div
                  key={p.title}
                  className="flex gap-4 items-start bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/50 rounded-xl p-4 shadow-sm"
                >
                  <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center text-base flex-shrink-0">
                    {p.icon}
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-800 dark:text-slate-200 mb-1">{p.title}</h4>
                    <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{p.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Team ─────────────────────────────────────────────────────────── */}
      <section className="py-20 bg-slate-50 dark:bg-[#0d1b2e]">
        <div className="max-w-5xl mx-auto px-6">

          {/* Header */}
          <div className="text-center mb-14">
            <p className="text-xs font-bold tracking-widest uppercase text-blue-500 mb-3">The People</p>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white">
              Built with purpose, by people who care.
            </h2>
            <div className="w-10 h-0.5 bg-gradient-to-r from-blue-500 to-indigo-500 rounded mx-auto mt-5" />
          </div>

          {/* ── Mentor card ─────────────────────────────────────────────── */}
          <div className="relative bg-white dark:bg-slate-800/60 border border-amber-300/50 dark:border-amber-500/20 rounded-2xl overflow-hidden shadow-sm mb-10 flex flex-col sm:flex-row">
            <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-amber-400 via-yellow-300 to-amber-400" />

            {/* Mentor photo */}
            <div className="sm:w-52 w-full h-60 sm:h-auto flex-shrink-0 overflow-hidden bg-slate-100 dark:bg-slate-700">
              <Photo
                src="/team/mentor.jpg"
                alt="Biman Roy"
                initials="BR"
                gradient={["#f59e0b", "#fbbf24"]}
                fontSize="3.25rem"
              />
            </div>

            {/* Mentor info */}
            <div className="flex flex-col justify-center px-8 py-8 sm:py-10">
              <span className="inline-block text-xs font-bold tracking-widest uppercase text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-full px-3 py-1 mb-3 w-fit">
                Mentor &amp; Guide
              </span>
              <h3 className="text-2xl font-extrabold text-slate-900 dark:text-white mb-2">Biman Roy</h3>
              <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed max-w-lg">
                Guided the team from ideation to deployment, shaping Smart Legal Assistant into a platform built for real social impact.
              </p>
            </div>
          </div>

          {/* ── Team grid (2×2 portrait cards) ──────────────────────────── */}
          <p className="text-xs font-bold tracking-widest uppercase text-slate-400 dark:text-slate-500 mb-5">
            Core Team
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-5">
            {TEAM.map(m => (
              <div
                key={m.name}
                className="group bg-white dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/50 rounded-2xl overflow-hidden shadow-sm hover:-translate-y-1.5 hover:shadow-md transition-all duration-200"
              >
                {/* Colour accent bar */}
                <div className={`h-0.5 bg-gradient-to-r ${m.accent}`} />

                {/* Portrait photo — 3:4 aspect ratio */}
                <div className="w-full overflow-hidden bg-slate-100 dark:bg-slate-700" style={{ aspectRatio: "3/4" }}>
                  <Photo
                    src={m.src}
                    alt={m.name}
                    initials={m.initials}
                    gradient={m.gradient}
                  />
                </div>

                {/* Name */}
                <div className="px-4 py-3 border-t border-slate-100 dark:border-slate-700/50">
                  <p className="text-sm font-bold text-slate-800 dark:text-slate-200 leading-snug">{m.name}</p>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Team Member</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Disclaimer ────────────────────────────────────────────────────── */}
      {/* Light: subtle slate. Dark: deep navy. No more jarring dark block in light mode. */}
      <section className="py-10 text-center px-6 bg-slate-100 dark:bg-[#060d1a] border-t border-slate-200 dark:border-slate-800">
        <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed max-w-xl mx-auto">
          <span className="text-blue-600 dark:text-blue-300 font-semibold">Smart Legal Assistant</span>{" "}
          is a student project built to make legal knowledge accessible across India. It does not
          constitute legal advice. Always consult a qualified legal professional for specific matters.
        </p>
      </section>

      </div>{/* end -mt-16 wrapper */}
    </Layout>
  );
}
