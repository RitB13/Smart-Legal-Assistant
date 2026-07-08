import Layout from "@/components/Layout";

export default function Terms() {
  return (
    <Layout>
      <div className="max-w-2xl mx-auto px-4 py-12">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">Terms of Service</h1>
        <p className="text-sm text-slate-400 mb-10">Last updated: July 2026</p>

        <div className="prose prose-sm dark:prose-invert max-w-none space-y-8 text-slate-700 dark:text-slate-300">

          <section>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Not legal advice</h2>
            <p>Smart Legal Assistant provides AI-generated legal <strong>information</strong>, not legal <strong>advice</strong>. Nothing on this platform constitutes a lawyer-client relationship. Do not rely solely on output from this platform to make legal decisions. Always consult a qualified advocate or legal professional before taking action.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Eligibility</h2>
            <p>You must be at least 18 years old to create an account. By registering, you confirm that the information you provide is accurate and that you will not use the platform on behalf of another person without their knowledge.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Permitted use</h2>
            <p>You may use this platform to understand Indian law, assess your legal situation, and explore dispute resolution options. You may not:</p>
            <ul className="list-disc list-inside space-y-1.5 mt-2">
              <li>Submit false, fabricated, or fraudulent information to manipulate AI outputs</li>
              <li>Attempt to extract training data, reverse-engineer models, or scrape the platform</li>
              <li>Use the platform to harass, threaten, or harm another party in a mediation</li>
              <li>Create multiple accounts to circumvent any restriction</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Mediation</h2>
            <p>Mediation sessions on this platform are non-binding. Any settlement proposed by the AI is a suggestion only. Both parties must independently agree to any terms and formalize them through appropriate legal channels if they wish to make the settlement enforceable.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Accuracy</h2>
            <p>AI-generated outputs may be incomplete, outdated, or incorrect. Laws change, court interpretations vary by jurisdiction, and individual case facts matter greatly. We make no guarantee of accuracy and are not liable for decisions made based on our outputs.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Changes to these terms</h2>
            <p>We may update these terms from time to time. Continued use of the platform after changes constitutes acceptance of the revised terms. We will notify registered users of material changes by email.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Contact</h2>
            <p>Questions about these terms? Write to us at <span className="font-medium text-primary">contact@smartlegalassistant.in</span>.</p>
          </section>

        </div>
      </div>
    </Layout>
  );
}
