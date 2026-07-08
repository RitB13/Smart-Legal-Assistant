import Layout from "@/components/Layout";

export default function Privacy() {
  return (
    <Layout>
      <div className="max-w-2xl mx-auto px-4 py-12">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">Privacy Policy</h1>
        <p className="text-sm text-slate-400 mb-10">Last updated: July 2026</p>

        <div className="prose prose-sm dark:prose-invert max-w-none space-y-8 text-slate-700 dark:text-slate-300">

          <section>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">What we collect</h2>
            <p>When you create an account, we collect your name and email address. When you use our tools, we store the content you submit — legal questions, case descriptions, and mediation statements — to provide the service and save your history.</p>
            <p className="mt-2">We do not collect payment information. We do not track your location beyond what you voluntarily provide (state/jurisdiction) for legal analysis.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">How we use your data</h2>
            <ul className="list-disc list-inside space-y-1.5">
              <li>To provide AI-generated legal information in response to your queries</li>
              <li>To save your prediction history and conversation history so you can revisit them</li>
              <li>To send OTP and account-related emails</li>
              <li>To improve the accuracy of our AI tools (in aggregate, anonymized form only)</li>
            </ul>
            <p className="mt-3">We do not sell your personal data. We do not share your data with third parties except as required to operate the service (e.g., our AI provider processes queries but does not store them).</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Mediation confidentiality</h2>
            <p>Statements submitted during mediation are seen only by the AI mediator. Neither party sees the other's submission. Mediation data is stored securely and is not shared with any third party or used to train public models.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Data retention</h2>
            <p>Your account data and conversation history are retained as long as your account is active. You can delete individual predictions from your history at any time. To request full account deletion, contact us at the email below.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Security</h2>
            <p>Passwords are hashed and never stored in plain text. All data is transmitted over HTTPS. Access tokens are short-lived and signed. We follow standard security practices for a web application of this type.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Contact</h2>
            <p>For any privacy concerns or data deletion requests, write to us at <span className="font-medium text-primary">contact@smartlegalassistant.in</span>.</p>
          </section>

        </div>
      </div>
    </Layout>
  );
}
