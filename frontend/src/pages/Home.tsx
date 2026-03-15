import { FileText, MessageSquare, Shield, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import FeatureCard from "../components/FeatureCard";

const Home = () => {
  return (
    <Layout>
      <div className="relative overflow-hidden">

        {/* Hero Section */}
        <div className="gradient-hero">
          <div className="container mx-auto px-4 py-20 md:py-20">

            <div className="mx-auto max-w-3xl text-center animate-fade-up relative z-10">

              <h1 className="mb-6 text-4xl md:text-6xl font-bold tracking-tight text-foreground underline decoration-black underline-offset-8">
                Smart Legal Assistant
              </h1>

              <p className="mb-10 text-lg md:text-xl text-muted-foreground">
                Your AI-powered guide to legal documents, queries, and rights.
                Making law accessible for everyone.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center">

                <Link
                  to="/chat"
                  className="group inline-flex items-center justify-center rounded-lg gradient-primary px-8 py-3 text-sm font-medium text-primary-foreground shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105"
                >
                  Get Started
                  <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                </Link>

                <Link
                  to="/rights"
                  className="inline-flex items-center justify-center rounded-lg border-2 border-primary bg-background px-8 py-3 text-sm font-medium text-primary hover:bg-primary hover:text-primary-foreground transition-all duration-300"
                >
                  Know Your Rights
                </Link>

              </div>
            </div>
          </div>

          {/* Decorative gradient blur */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-96 bg-primary/10 rounded-full blur-3xl pointer-events-none" />

        </div>

        {/* Features Section */}
        <div className="container mx-auto px-4 py-20">

          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
              How We Can Help You
            </h2>

            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Choose from our suite of AI-powered legal tools designed to simplify your legal journey
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">

            <FeatureCard
              icon={FileText}
              title="Upload Legal Document"
              description="Upload complex legal documents and get instant, simplified explanations in plain language"
              link="/upload"
              color="primary"
            />

            <FeatureCard
              icon={MessageSquare}
              title="Ask Legal Question"
              description="Chat with our AI assistant to get answers to your legal queries and guidance"
              link="/chat"
              color="secondary"
            />

            <FeatureCard
              icon={Shield}
              title="Know Your Rights"
              description="Explore your constitutional rights and understand the laws that protect you"
              link="/rights"
              color="accent"
            />

          </div>
        </div>

        {/* CTA Section */}
        <div className="gradient-secondary py-20">

          <div className="container mx-auto px-4 text-center">

            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Ready to Get Legal Help?
            </h2>

            <p className="text-lg text-white/90 mb-8 max-w-2xl mx-auto">
              Join thousands of users who have simplified their legal journey with our AI assistant
            </p>

            <Link
              to="/chat"
              className="inline-flex items-center justify-center rounded-lg bg-white px-8 py-3 text-sm font-medium text-primary hover:bg-white/90 shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105"
            >
              Start Free Consultation
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>

          </div>
        </div>

      </div>
    </Layout>
  );
};

export default Home;