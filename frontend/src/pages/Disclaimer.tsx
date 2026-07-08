import Layout from "@/components/Layout";
import { AlertTriangle } from "lucide-react";

export default function Disclaimer() {
  return (
    <Layout>
      <div className="max-w-2xl mx-auto px-4 py-12">
        <div className="flex items-center gap-3 mb-2">
          <AlertTriangle className="h-6 w-6 text-amber-500" />
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Disclaimer</h1>
        </div>
        <p className="text-sm text-slate-400 mb-10">Last updated: July 2026</p>

        <div className="rounded-xl border border-amber-200 dark:border-amber-700/40 bg-amber-50 dark:bg-amber-900/10 px-5 py-4 mb-10">
          <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">
            Smart Legal Assistant is an informational tool. It is not a law firm and does not provide legal advice. Nothing you read or receive here should be treated as a substitute for advice from a licensed advocate.
          </p>
        </div>

        <div className="prose prose-sm dark:prose-invert max-w-none space-y-8 text-slate-700 dark:text-slate-300">

          <section>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">AI limitations</h2>
            <p>Our tools use AI models trained on Indian legal datasets. These models can produce incorrect, incomplete, or outdated information. Legal outcomes depend on specific facts, judicial discretion, local court practice, and many other factors that an AI cannot fully account for.</p>
            <p className="mt-2">Predictions about case outcomes are probabilistic estimates based on historical patterns — they are not guarantees, and past outcomes do not predict future ones.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">No lawyer-client relationship</h2>
            <p>Using this platform does not create a lawyer-client relationship between you and Smart Legal Assistant or any of its operators, developers, or affiliates. Communications through this platform are not protected by attorney-client privilege.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Jurisdiction</h2>
            <p>This platform is designed for use under Indian law. It is not intended for use in other jurisdictions. If you are outside India or dealing with a matter that involves laws of another country, consult a legal professional in the relevant jurisdiction.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Mediation outcomes</h2>
            <p>Settlements proposed through our AI Mediation tool are non-binding suggestions. They carry no legal weight unless both parties agree to them and formalize the agreement through proper legal channels. We are not responsible for any outcome of a mediation conducted on this platform.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Limitation of liability</h2>
            <p>To the maximum extent permitted by law, Smart Legal Assistant and its operators shall not be liable for any loss, harm, or damage arising from your use of, or reliance on, information provided by this platform.</p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">When to consult a lawyer</h2>
            <p>Always consult a qualified advocate when:</p>
            <ul className="list-disc list-inside space-y-1.5 mt-2">
              <li>You are about to file or respond to a court case</li>
              <li>You are signing a legally binding agreement</li>
              <li>You face criminal charges or police action</li>
              <li>A dispute involves significant money, property, or family matters</li>
              <li>You are unsure how to interpret a judgment or notice</li>
            </ul>
          </section>

        </div>
      </div>
    </Layout>
  );
}
