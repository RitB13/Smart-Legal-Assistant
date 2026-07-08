import { Scale } from "lucide-react";
import { Link } from "react-router-dom";

const Footer = () => {
  return (
    <footer className="mt-auto border-t border-slate-200 dark:border-slate-700/50 bg-white dark:bg-slate-900/60">
      <div className="container mx-auto px-4 py-8 max-w-6xl">

        {/* Main row */}
        <div className="flex flex-col md:flex-row items-start justify-between gap-6">

          {/* Brand + disclaimer */}
          <div className="max-w-sm">
            <div className="flex items-center gap-2 mb-3">
              <Scale className="h-4 w-4 text-primary flex-shrink-0" />
              <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                Smart Legal<span className="text-primary"> Assistant</span>
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              <span className="font-semibold text-amber-600 dark:text-amber-500">Not Legal Advice.</span>{" "}
              This platform provides AI-generated legal information for educational purposes only.
              Always consult a qualified legal professional before taking any legal action.
            </p>
          </div>

          {/* Navigation columns */}
          <div className="flex flex-wrap gap-8 text-xs">
            <div>
              <p className="font-semibold text-slate-700 dark:text-slate-300 mb-2.5 uppercase tracking-widest text-[10px]">Tools</p>
              <ul className="space-y-2 text-slate-500 dark:text-slate-400">
                <li><Link to="/chat"      className="hover:text-primary transition-colors">Legal Assistant</Link></li>
                <li><Link to="/predict"   className="hover:text-primary transition-colors">Case Predictor</Link></li>
                <li><Link to="/mediation" className="hover:text-primary transition-colors">AI Mediation</Link></li>
                <li><Link to="/rights"    className="hover:text-primary transition-colors">Know Your Rights</Link></li>
              </ul>
            </div>
            <div>
              <p className="font-semibold text-slate-700 dark:text-slate-300 mb-2.5 uppercase tracking-widest text-[10px]">Legal</p>
              <ul className="space-y-2 text-slate-500 dark:text-slate-400">
                <li><Link to="/privacy"    className="hover:text-primary transition-colors">Privacy Policy</Link></li>
                <li><Link to="/terms"      className="hover:text-primary transition-colors">Terms of Service</Link></li>
                <li><Link to="/disclaimer" className="hover:text-primary transition-colors">Disclaimer</Link></li>
              </ul>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="border-t border-slate-100 dark:border-slate-700/50 mt-6 pt-5 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-400 dark:text-slate-500">
          <p>© {new Date().getFullYear()} Smart Legal Assistant. All rights reserved.</p>
          <p>Built for Indian law &amp; Indian citizens.</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
