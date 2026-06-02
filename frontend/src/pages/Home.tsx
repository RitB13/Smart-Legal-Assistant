import { FileText, MessageSquare, Shield, ArrowRight, Scale, Users } from "lucide-react";
import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import FeatureCard from "../components/FeatureCard";

const Home = () => {
  return (
    <Layout>
      <div className="relative overflow-hidden">

        {/* Hero Section */}
        <div className="gradient-hero">
          <div className="container mx-auto px-4 py-32 md:py-48">

            <div className="mx-auto max-w-3xl text-center animate-fade-up relative z-10">

              <h1 className="mb-6 text-5xl md:text-7xl font-black tracking-tighter text-primary animate-fade-up" style={{animationDelay: '0.1s', textShadow: '0 4px 20px rgba(25, 118, 210, 0.15)', letterSpacing: '-0.02em'}}>
                Smart Legal Assistant
              </h1>

              <p className="mb-12 text-lg md:text-xl text-muted-foreground font-medium leading-relaxed max-w-2xl mx-auto" style={{animationDelay: '0.2s'}}>
                Your AI-powered guide to legal documents, queries, and rights.
                Making law accessible for everyone.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center" style={{animationDelay: '0.3s'}}>

                <Link
                  to="/chat"
                  className="group inline-flex items-center justify-center rounded-full gradient-primary px-8 py-4 text-base font-bold text-primary-foreground shadow-lg hover:shadow-2xl transition-all duration-300 hover:scale-110 hover:-translate-y-1"
                >
                  Get Started
                  <ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-2" />
                </Link>

                <Link
                  to="/rights"
                  className="inline-flex items-center justify-center rounded-full border-3 border-primary bg-white px-8 py-4 text-base font-bold text-primary hover:bg-primary hover:text-white transition-all duration-300 hover:scale-110 hover:-translate-y-1 shadow-md hover:shadow-xl"
                >
                  Know Your Rights
                </Link>

              </div>
            </div>
          </div>

          {/* Decorative gradient blur */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-96 bg-primary/20 rounded-full blur-3xl pointer-events-none animate-pulse" />
          <div className="absolute bottom-0 right-0 w-80 h-80 bg-secondary/15 rounded-full blur-3xl pointer-events-none animate-pulse" style={{animationDelay: '1s'}} />

        </div>

        {/* Features Section */}
        <div className="container mx-auto px-4 py-20">

          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-black text-foreground mb-4 tracking-tight">
              How We Can Help You
            </h2>

            <div className="w-16 h-1 bg-gradient-to-r from-primary via-secondary to-accent rounded-full mx-auto mb-6" />
            <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto font-medium leading-relaxed">
              Choose from our suite of AI-powered legal tools designed to simplify your legal journey
            </p>
          </div>

          {/* Mediation — hero feature */}
          <div className="max-w-5xl mx-auto mb-6">
            <Link
              to="/mediation"
              className="group flex flex-col sm:flex-row items-start sm:items-center gap-5 bg-white border border-primary/20 rounded-2xl px-6 py-5 hover:border-primary/40 hover:shadow-md transition-all"
            >
              <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:bg-primary/15 transition-colors">
                <Scale className="h-6 w-6 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-bold text-slate-900">AI-Mediated Dispute Resolution</h3>
                  <span className="text-[10px] font-semibold bg-primary text-white px-2 py-0.5 rounded-full">NEW</span>
                </div>
                <p className="text-sm text-slate-500">
                  Both parties submit their side privately. Our AI mediates, detects bias, and proposes a fair settlement backed by 71,000+ Indian court cases.
                </p>
              </div>
              <div className="flex items-center gap-1 text-primary font-medium text-sm flex-shrink-0 group-hover:gap-2 transition-all">
                Try mediation <ArrowRight className="h-4 w-4" />
              </div>
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 max-w-5xl mx-auto">

            <FeatureCard
              icon={MessageSquare}
              title="Legal Assistant"
              description="Chat with our AI to understand your legal situation and explore your options"
              link="/chat"
              color="primary"
            />

            <FeatureCard
              icon={FileText}
              title="Document Analysis"
              description="Upload legal documents and get instant plain-language explanations and risk scores"
              link="/upload"
              color="secondary"
            />

            <FeatureCard
              icon={Shield}
              title="Know Your Rights"
              description="Explore your constitutional and consumer rights under Indian law"
              link="/rights"
              color="accent"
            />

            <FeatureCard
              icon={Users}
              title="My Disputes"
              description="View and manage all your active and completed mediation disputes"
              link="/mediation"
              color="primary"
            />

          </div>
        </div>

        {/* CTA Section */}
        <div className="gradient-secondary py-24 relative overflow-hidden">
          <div className="absolute inset-0 opacity-10">
            <div className="absolute top-0 left-0 w-96 h-96 bg-white rounded-full blur-3xl" />
            <div className="absolute bottom-0 right-0 w-96 h-96 bg-white rounded-full blur-3xl" />
          </div>

          <div className="container mx-auto px-4 text-center relative z-10">

            <h2 className="text-4xl md:text-5xl font-black text-white mb-6 tracking-tight">
              Ready to Get Legal Help?
            </h2>

            <p className="text-lg md:text-xl text-white/95 mb-10 max-w-2xl mx-auto font-medium leading-relaxed">
              Join thousands of users who have simplified their legal journey with our AI assistant
            </p>

            <Link
              to="/chat"
              className="inline-flex items-center justify-center rounded-full bg-white px-10 py-4 text-base font-bold text-primary hover:bg-white/95 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-110 hover:-translate-y-1"
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