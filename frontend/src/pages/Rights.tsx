import { useState } from "react";
import { ChevronDown, ChevronUp, Shield, Book, Users, Heart, Briefcase, Home as HomeIcon, ArrowRight, CheckCircle } from "lucide-react";
import { Link } from "react-router-dom";
import { type LucideIcon } from "lucide-react";
import Layout from "../components/Layout";

interface RightSection {
  id: string;
  title: string;
  Icon: LucideIcon;
  rights: string[];
  description: string;
  stripClass: string;
  iconGradient: string;
  cardBorder: string;
  expandedBg: string;
  expandedBorderClass: string;
  bulletClass: string;
  badgeClass: string;
}

/* ── Faded scales SVG for CTA background ─────────────────────────────────── */
function ScalesWatermark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 260 320" fill="none" xmlns="http://www.w3.org/2000/svg" className={className} aria-hidden>
      <rect x="120" y="278" width="20" height="32" rx="4" fill="currentColor" />
      <rect x="86" y="272" width="88" height="10" rx="5" fill="currentColor" />
      <rect x="128" y="60" width="4" height="216" rx="2" fill="currentColor" />
      <circle cx="130" cy="52" r="10" fill="currentColor" />
      <circle cx="130" cy="52" r="5" fill="white" fillOpacity="0.5" />
      <rect x="22" y="96" width="216" height="5" rx="2.5" fill="currentColor" />
      <line x1="44" y1="101" x2="44" y2="150" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeDasharray="5 4" />
      <line x1="84" y1="101" x2="84" y2="150" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeDasharray="5 4" />
      <line x1="176" y1="101" x2="176" y2="150" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeDasharray="5 4" />
      <line x1="216" y1="101" x2="216" y2="150" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeDasharray="5 4" />
      <path d="M24 150 Q64 178 104 150" stroke="currentColor" strokeWidth="3.5" fill="none" strokeLinecap="round" />
      <line x1="24" y1="150" x2="104" y2="150" stroke="currentColor" strokeWidth="1.5" strokeOpacity="0.4" />
      <path d="M156 150 Q196 178 236 150" stroke="currentColor" strokeWidth="3.5" fill="none" strokeLinecap="round" />
      <line x1="156" y1="150" x2="236" y2="150" stroke="currentColor" strokeWidth="1.5" strokeOpacity="0.4" />
    </svg>
  );
}

/* ─────────────────────────────────────────────────────────────────────────── */

const RightsPage = () => {
  const [expandedSections, setExpandedSections] = useState<string[]>(["fundamental"]);

  const rightsSections: RightSection[] = [
    {
      id: "fundamental",
      title: "Fundamental Rights",
      Icon: Shield,
      description: "Basic human rights guaranteed by the Constitution of India (Articles 12–35)",
      rights: [
        "Right to Equality (Articles 14–18): Equal treatment before law, prohibition of discrimination, equal opportunity in employment",
        "Right to Freedom (Articles 19–22): Freedom of speech, assembly, movement, residence, profession, protection against arbitrary arrest",
        "Right Against Exploitation (Articles 23–24): Prohibition of human trafficking, forced labor, and child labor",
        "Right to Freedom of Religion (Articles 25–28): Freedom to practice, profess and propagate any religion",
        "Cultural and Educational Rights (Articles 29–30): Protection of minority interests, right to establish educational institutions",
        "Right to Constitutional Remedies (Article 32): Right to approach Supreme Court for enforcement of fundamental rights",
      ],
      stripClass: "bg-gradient-to-r from-blue-500 to-indigo-600",
      iconGradient: "bg-gradient-to-br from-blue-500 to-indigo-600",
      cardBorder: "border border-blue-100 dark:border-slate-700",
      expandedBg: "bg-blue-50/50 dark:bg-blue-900/10",
      expandedBorderClass: "border-t border-blue-100 dark:border-slate-700",
      bulletClass: "bg-blue-500",
      badgeClass: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
    },
    {
      id: "legal",
      title: "Legal Rights",
      Icon: Book,
      description: "Rights provided by various laws and statutes",
      rights: [
        "Right to Free Legal Aid: Free legal services for poor and marginalized sections",
        "Right to Fair Trial: Presumption of innocence, right to defense lawyer, right to appeal",
        "Right Against Self-Incrimination: Cannot be forced to testify against oneself",
        "Right to Information (RTI Act 2005): Access to government information and records",
        "Right to Privacy: Protection of personal information and data",
        "Right to Bail: Bail is rule, jail is exception (except in serious offenses)",
        "Right to Speedy Trial: Cases must be decided within reasonable time",
      ],
      stripClass: "bg-gradient-to-r from-teal-500 to-cyan-600",
      iconGradient: "bg-gradient-to-br from-teal-500 to-cyan-600",
      cardBorder: "border border-teal-100 dark:border-slate-700",
      expandedBg: "bg-teal-50/50 dark:bg-teal-900/10",
      expandedBorderClass: "border-t border-teal-100 dark:border-slate-700",
      bulletClass: "bg-teal-500",
      badgeClass: "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300",
    },
    {
      id: "consumer",
      title: "Consumer Rights",
      Icon: Users,
      description: "Protection under Consumer Protection Act 2019",
      rights: [
        "Right to Safety: Protection against hazardous goods and services",
        "Right to Information: Complete information about quality, quantity, price, purity",
        "Right to Choose: Access to variety of goods at competitive prices",
        "Right to be Heard: Grievances to be heard at appropriate forums",
        "Right to Redressal: Compensation for unfair trade practices or defective goods",
        "Right to Consumer Education: Awareness about consumer rights and remedies",
      ],
      stripClass: "bg-gradient-to-r from-purple-500 to-violet-600",
      iconGradient: "bg-gradient-to-br from-purple-500 to-violet-600",
      cardBorder: "border border-purple-100 dark:border-slate-700",
      expandedBg: "bg-purple-50/50 dark:bg-purple-900/10",
      expandedBorderClass: "border-t border-purple-100 dark:border-slate-700",
      bulletClass: "bg-purple-500",
      badgeClass: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
    },
    {
      id: "women",
      title: "Women's Rights",
      Icon: Heart,
      description: "Special protections and rights for women under Indian law",
      rights: [
        "Right to Equal Pay: Equal remuneration for equal work",
        "Right Against Domestic Violence: Protection from physical, mental, economic abuse",
        "Right to Maternity Benefits: Paid maternity leave up to 26 weeks",
        "Right Against Sexual Harassment: Safe workplace environment, complaint mechanisms",
        "Right to Property: Equal inheritance and property rights",
        "Right to Dignity: Protection against indecent representation and objectification",
        "Right to Free Legal Aid: Priority in legal aid services",
      ],
      stripClass: "bg-gradient-to-r from-rose-500 to-pink-600",
      iconGradient: "bg-gradient-to-br from-rose-500 to-pink-600",
      cardBorder: "border border-rose-100 dark:border-slate-700",
      expandedBg: "bg-rose-50/50 dark:bg-rose-900/10",
      expandedBorderClass: "border-t border-rose-100 dark:border-slate-700",
      bulletClass: "bg-rose-500",
      badgeClass: "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300",
    },
    {
      id: "worker",
      title: "Worker's Rights",
      Icon: Briefcase,
      description: "Labor laws and employment protections",
      rights: [
        "Right to Minimum Wages: Guaranteed minimum wage as per government regulations",
        "Right to Safe Working Conditions: Workplace safety, health measures, accident compensation",
        "Right to Form Unions: Freedom to form and join trade unions",
        "Right to Regulated Working Hours: Maximum 48 hours per week, overtime compensation",
        "Right to Leave: Weekly holidays, casual leave, sick leave, earned leave",
        "Right to Gratuity: Payment after 5 years of continuous service",
        "Right to Provident Fund: Retirement savings scheme with employer contribution",
      ],
      stripClass: "bg-gradient-to-r from-orange-500 to-amber-500",
      iconGradient: "bg-gradient-to-br from-orange-500 to-amber-500",
      cardBorder: "border border-orange-100 dark:border-slate-700",
      expandedBg: "bg-orange-50/50 dark:bg-orange-900/10",
      expandedBorderClass: "border-t border-orange-100 dark:border-slate-700",
      bulletClass: "bg-orange-500",
      badgeClass: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
    },
    {
      id: "property",
      title: "Property Rights",
      Icon: HomeIcon,
      description: "Rights related to property ownership and tenancy",
      rights: [
        "Right to Own Property: Buy, sell, inherit property regardless of gender or religion",
        "Right to Peaceful Possession: Protection against illegal eviction or trespassing",
        "Tenant Rights: Fair rent, maintenance, protection against arbitrary eviction",
        "Right to Compensation: Fair compensation for land acquisition by government",
        "Right to Transfer Property: Freedom to sell, gift, or mortgage property",
        "Right Against Encroachment: Legal remedies against illegal occupation",
      ],
      stripClass: "bg-gradient-to-r from-green-500 to-emerald-600",
      iconGradient: "bg-gradient-to-br from-green-500 to-emerald-600",
      cardBorder: "border border-green-100 dark:border-slate-700",
      expandedBg: "bg-green-50/50 dark:bg-green-900/10",
      expandedBorderClass: "border-t border-green-100 dark:border-slate-700",
      bulletClass: "bg-green-500",
      badgeClass: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
    },
  ];

  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev =>
      prev.includes(sectionId) ? [] : [sectionId]
    );
  };

  return (
    <Layout>
      <div className="-mt-16">

        {/* ── Hero ──────────────────────────────────────────────────────────── */}
        <div className="relative overflow-hidden min-h-[280px] bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-700 dark:from-[#060d1a] dark:via-[#0a0f2e] dark:to-[#0d0a2a] pt-24 pb-12 flex items-center">
          {/* Soft blobs */}
          <div className="absolute -top-16 -left-16 w-[360px] h-[360px] bg-white/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 right-0 w-[280px] h-[280px] bg-purple-400/10 rounded-full blur-3xl pointer-events-none" />

          <div className="container mx-auto px-4 text-center relative z-10 w-full">
            {/* Badge chip */}
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/15 border border-white/25 text-white/90 text-xs font-semibold mb-4">
              <Shield className="h-3.5 w-3.5" />
              Know Your Rights
            </div>

            <h1 className="text-4xl md:text-5xl font-black text-white tracking-tight mb-4 leading-tight">
              Know Your Rights
            </h1>

            <p className="text-lg text-blue-100/80 max-w-xl mx-auto leading-relaxed">
              Every Indian citizen has legal protections. Understand them — and use them.
            </p>
          </div>
        </div>

        {/* ── Cards Grid ────────────────────────────────────────────────────── */}
        <section className="bg-white dark:bg-[#060d1a] py-12">
          <div className="container mx-auto px-4 max-w-5xl">

            <div className="text-center mb-10">
              <p className="text-xs font-bold text-blue-600 dark:text-blue-400 uppercase tracking-[0.2em] mb-2">6 Categories</p>
              <h2 className="text-2xl md:text-3xl font-black text-slate-900 dark:text-white tracking-tight">
                Your rights at a glance
              </h2>
              <p className="text-sm text-slate-400 dark:text-slate-500 mt-2 max-w-md mx-auto">
                Click any card to expand and explore individual rights in that category.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {rightsSections.map(section => {
                const isOpen = expandedSections.includes(section.id);
                const { Icon } = section;

                return (
                  <div
                    key={section.id}
                    onClick={() => toggleSection(section.id)}
                    className={`rounded-2xl ${section.cardBorder} overflow-hidden transition-all duration-300 hover:shadow-xl hover:-translate-y-1 cursor-pointer`}
                  >
                    {/* Colored top strip */}
                    <div className={`h-2 ${section.stripClass}`} />

                    {/* Card body */}
                    <div className="bg-white dark:bg-[#0d1a2e] p-5">
                      {/* Icon + title row */}
                      <div className="flex items-start gap-3">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 shadow-md ${section.iconGradient}`}>
                          <Icon className="h-5 w-5 text-white" />
                        </div>
                        <div className="flex-1 min-w-0 pt-0.5">
                          <h3 className="font-bold text-slate-900 dark:text-white text-base leading-tight">
                            {section.title}
                          </h3>
                          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                            {section.description}
                          </p>
                        </div>
                      </div>

                      {/* Bottom row: rights count + chevron */}
                      <div className="flex items-center justify-between mt-4">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${section.badgeClass}`}>
                          {section.rights.length} rights
                        </span>
                        <div className="text-slate-400 dark:text-slate-500 transition-transform duration-200">
                          {isOpen ? (
                            <ChevronUp className="h-4 w-4" />
                          ) : (
                            <ChevronDown className="h-4 w-4" />
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Expanded panel */}
                    {isOpen && (
                      <div className={`${section.expandedBorderClass} ${section.expandedBg} px-5 py-4`}>
                        <ul className="space-y-2.5">
                          {section.rights.map((right, i) => (
                            <li key={i} className="flex items-start gap-2.5 text-sm animate-fade-in">
                              <div className={`w-2 h-2 rounded-full ${section.bulletClass} mt-1.5 flex-shrink-0`} />
                              <span className="text-slate-700 dark:text-slate-300 leading-relaxed">
                                {right}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* ── CTA ───────────────────────────────────────────────────────────── */}
        <div className="relative overflow-hidden bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-700 dark:from-[#060d1a] dark:via-[#0a0f2e] dark:to-[#0d0a2a] py-20">
          {/* Faded scales watermark */}
          <ScalesWatermark className="absolute right-12 top-1/2 -translate-y-1/2 w-[220px] h-[260px] text-white opacity-[0.07] pointer-events-none select-none" />
          <ScalesWatermark className="absolute left-8 bottom-4 w-[120px] h-[140px] text-white opacity-[0.04] pointer-events-none select-none" />

          {/* Soft blobs */}
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-white/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 right-1/4 w-80 h-80 bg-purple-400/10 rounded-full blur-3xl pointer-events-none" />

          <div className="container mx-auto px-4 text-center relative z-10">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/15 border border-white/25 text-white/90 text-xs font-semibold mb-5">
              <CheckCircle className="h-3.5 w-3.5" />
              Free for all citizens
            </div>

            <h2 className="text-3xl md:text-4xl font-black text-white mb-4 tracking-tight">
              Need help exercising your rights?
            </h2>

            <p className="text-lg text-blue-100/80 mb-8 max-w-md mx-auto leading-relaxed">
              Know your rights, then act on them. Our legal assistant walks you through the process — whether that's drafting a complaint or understanding what the law actually says.
            </p>

            <Link
              to="/chat"
              className="inline-flex items-center justify-center rounded-full bg-white px-8 py-3.5 text-base font-bold text-blue-700 shadow-xl shadow-blue-900/30 hover:bg-blue-50 hover:scale-105 hover:shadow-2xl transition-all duration-300"
            >
              Chat with Legal Assistant
              <ArrowRight className="ml-2 h-5 w-5" />
            </Link>
          </div>
        </div>

      </div>
    </Layout>
  );
};

export default RightsPage;
