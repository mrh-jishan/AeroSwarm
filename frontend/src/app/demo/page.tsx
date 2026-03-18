import type { Metadata } from "next";
import Link from "next/link";
import { LeadCaptureForm } from "@/components/LeadCaptureForm";
import { PublicPageShell } from "@/components/PublicPageShell";

export const metadata: Metadata = {
  title: "Request Pilot",
  description: "What an AeroSwarm pilot should cover, how it is evaluated, and how to start the conversation.",
};

const steps = [
  {
    title: "Choose one workflow",
    body: "Start with one repo and one kind of work where parallel execution is useful: migrations, broad refactors, or repetitive review-heavy changes.",
  },
  {
    title: "Run a controlled rollout",
    body: "Connect the repo, launch a limited pilot, and validate branch handling, preflight checks, merge approval, and operator visibility.",
  },
  {
    title: "Measure fit before expansion",
    body: "Review cycle time, merge quality, operator effort, and whether the workflow should expand to more repos or teams.",
  },
];

const checklist = [
  "One target repository or sandbox environment",
  "One engineering lead or approver who owns final merge decisions",
  "A clear task class that benefits from parallel execution",
  "A deployment environment for backend, worker, Postgres, and Redis",
];

export default function DemoPage() {
  return (
    <PublicPageShell
      eyebrow="Pilot"
      title="Request a pilot with a workflow that is small enough to prove and important enough to matter."
      description="AeroSwarm should be evaluated against a real engineering path, not a staged demo script. This page gives prospects a concrete pilot shape to work from."
    >
      <div className="grid gap-6">
        {steps.map((step, index) => (
          <article key={step.title} className="rounded-3xl border border-white/10 bg-slate-900/70 p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.35em] text-emerald-300">
              Step {index + 1}
            </p>
            <h2 className="mt-4 text-2xl font-semibold text-white">{step.title}</h2>
            <p className="mt-3 text-slate-300">{step.body}</p>
          </article>
        ))}
      </div>
      <div className="mt-10 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <section className="rounded-3xl border border-white/10 bg-slate-900/70 p-6">
          <h2 className="text-2xl font-semibold text-white">Pilot checklist</h2>
          <ul className="mt-5 grid gap-3 text-sm text-slate-300">
            {checklist.map((item) => (
              <li key={item} className="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3">
                {item}
              </li>
            ))}
          </ul>
        </section>
        <LeadCaptureForm
          source="pilot"
          submitLabel="Request Pilot"
          successMessage="Pilot request received. The next step is qualification through your configured delivery channel."
          intro="Use this to qualify one repo, one team, and one workflow where agent parallelism can be evaluated in a controlled rollout."
        />
      </div>
      <div className="mt-10 rounded-3xl border border-sky-400/20 bg-sky-400/5 p-6">
        <h2 className="text-2xl font-semibold text-white">Need to talk first?</h2>
        <p className="mt-4 text-slate-300">
          If the pilot shape is not clear yet, route the conversation through commercial contact first and qualify around repo access,
          deployment constraints, and success criteria.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            href="/contact"
            className="rounded-full bg-sky-400 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-sky-300"
          >
            Contact Team
          </Link>
          <Link
            href="/pricing"
            className="rounded-full border border-slate-700 px-5 py-3 text-sm text-slate-100 hover:border-slate-500"
          >
            See Pricing
          </Link>
        </div>
      </div>
    </PublicPageShell>
  );
}
