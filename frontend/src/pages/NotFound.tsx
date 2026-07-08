import { Link, useLocation } from "react-router-dom";
import { useEffect } from "react";
import { Scale, Home, MessageSquare, TrendingUp, ArrowLeft } from "lucide-react";
import Layout from "../components/Layout";

const NotFound = () => {
  const location = useLocation();

  useEffect(() => {
    console.error("404 Error: User attempted to access non-existent route:", location.pathname);
  }, [location.pathname]);

  return (
    <Layout>
      <div className="min-h-[80vh] flex flex-col items-center justify-center px-4 text-center -mt-8">

        {/* Big 404 */}
        <div className="relative mb-6">
          <p className="text-[120px] md:text-[160px] font-black leading-none select-none
                        text-slate-100 dark:text-slate-800">
            404
          </p>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-xl shadow-blue-300/40 dark:shadow-blue-900/40">
              <Scale className="h-8 w-8 text-white" />
            </div>
          </div>
        </div>

        <h1 className="text-2xl md:text-3xl font-black text-slate-900 dark:text-white mb-3 tracking-tight">
          Page not found
        </h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm max-w-sm leading-relaxed mb-8">
          The page you're looking for doesn't exist or has been moved.
          Head back and use one of our legal tools instead.
        </p>

        {/* Navigation options */}
        <div className="flex flex-col sm:flex-row gap-3 mb-10">
          <Link
            to="/"
            className="inline-flex items-center justify-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-bold text-white shadow-lg hover:opacity-90 hover:scale-[1.02] transition-all"
          >
            <Home className="h-4 w-4" />
            Go home
          </Link>
          <Link
            to="/chat"
            className="inline-flex items-center justify-center gap-2 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-6 py-3 text-sm font-medium text-slate-700 dark:text-slate-300 hover:border-primary hover:text-primary transition-all"
          >
            <MessageSquare className="h-4 w-4" />
            Ask the Legal Assistant
          </Link>
        </div>

        {/* Quick links */}
        <div className="flex items-center gap-4 text-xs text-slate-400 dark:text-slate-500">
          <Link to="/predict" className="flex items-center gap-1 hover:text-primary transition-colors">
            <TrendingUp className="h-3.5 w-3.5" /> Case Predictor
          </Link>
          <span>·</span>
          <Link to="/mediation" className="hover:text-primary transition-colors">AI Mediation</Link>
          <span>·</span>
          <Link to="/rights" className="hover:text-primary transition-colors">Know Your Rights</Link>
        </div>

        <Link
          to="/"
          className="mt-8 flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to Smart Legal Assistant
        </Link>
      </div>
    </Layout>
  );
};

export default NotFound;
