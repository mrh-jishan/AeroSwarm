import type { Metadata } from "next";
import Link from "next/link";
import { PublicFooter } from "@/components/PublicFooter";
import { PublicHeader } from "@/components/PublicHeader";
import { absoluteUrl } from "@/lib/site";

export const metadata: Metadata = {
  title: "Parallel Agent Software Factory",
  description: "AeroSwarm coordinates AI coding agents across isolated worktrees with review gates, audit trails, and GitHub integration for private engineering teams.",
};

const featureCards = [
  {
    title: "Parallel execution",
    body: "Split a feature into isolated tasks, launch workers in parallel, and keep every agent fenced to its assigned scope.",
  },
  {
    title: "Human-reviewed merges",
    body: "Run preflight checks, publish PR context back to GitHub, and keep merge authority with a real person.",
  },
  {
    title: "Self-hosted control",
    body: "Run the API, worker, repos, and containers in infrastructure your team controls instead of shipping code into a black box.",
  },
];

const useCases = [
  "Large refactors across well-separated modules",
  "Migration spikes that need multiple isolated implementation lanes",
  "Internal engineering workflows for private repositories",
  "Preflighted code generation with audit trails and approval gates",
];

const operatingModel = [
  {
    step: "01",
    title: "Connect a repo",
    body: "Use GitHub credentials or app installation, create a tracked session, and keep branch and PR state tied back to the provider.",
  },
  {
    step: "02",
    title: "Launch scoped agents",
    body: "Decompose the request into isolated work scopes so multiple agents can execute in parallel without trampling each other.",
  },
  {
    step: "03",
    title: "Gate delivery",
    body: "Run preflight, publish PR context, keep audit trails, and hold final merge authority with an approver on your team.",
  },
];

export default function HomePage() {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "AeroSwarm",
    applicationCategory: "DeveloperApplication",
    operatingSystem: "Web",
    url: absoluteUrl("/"),
    description:
      "A self-hosted multi-agent coding orchestration platform for secure software delivery.",
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <PublicHeader />
      <main>
        <section className="overflow-hidden border-b border-white/10 bg-[radial-gradient(circle_at_top_left,_rgba(56,189,248,0.18),_transparent_40%),radial-gradient(circle_at_top_right,_rgba(250,204,21,0.12),_transparent_32%),linear-gradient(180deg,_rgba(15,23,42,1),_rgba(2,6,23,1))]">
          <div className="mx-auto grid max-w-6xl gap-12 px-6 py-24 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-sky-300">
                Multi-Agent Delivery Infrastructure
              </p>
              <h1 className="mt-5 max-w-4xl text-5xl font-semibold tracking-tight text-white md:text-6xl">
                Let software agents work in parallel without losing review control.
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
                AeroSwarm decomposes engineering requests, launches isolated coding agents,
                runs merge preflight, and keeps the final decision with your team.
              </p>
              <div className="mt-8 flex flex-wrap gap-4">
                <Link
                  href="/demo"
                  className="rounded-full bg-sky-400 px-6 py-3 text-sm font-semibold text-slate-950 hover:bg-sky-300"
                >
                  Request Pilot
                </Link>
                <Link
                  href="/pricing"
                  className="rounded-full border border-slate-700 px-6 py-3 text-sm font-semibold text-slate-100 hover:border-slate-500"
                >
                  View Pricing
                </Link>
                <Link
                  href="/dashboard"
                  className="rounded-full border border-slate-700 px-6 py-3 text-sm font-semibold text-slate-100 hover:border-slate-500"
                >
                  Open Dashboard
                </Link>
              </div>
              <p className="mt-5 text-sm text-slate-400">
                Best for private engineering teams running refactors, migrations, and review-heavy implementation work.
              </p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-slate-900/70 p-6 shadow-2xl shadow-sky-950/40">
              <div className="rounded-2xl border border-white/10 bg-slate-950 p-5">
                <div className="flex items-center justify-between text-xs uppercase tracking-[0.3em] text-slate-500">
                  <span>Session State</span>
                  <span className="rounded-full bg-emerald-400/15 px-3 py-1 text-emerald-300">running</span>
                </div>
                <div className="mt-5 space-y-4">
                  {[
                    ["Agent A", "Auth migration", "idle"],
                    ["Agent B", "Billing hooks", "running"],
                    ["Agent C", "Dashboard tests", "running"],
                  ].map(([name, task, status]) => (
                    <div key={name} className="rounded-2xl border border-white/10 bg-slate-900 px-4 py-3">
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-white">{name}</p>
                        <span className="text-xs text-sky-300">{status}</span>
                      </div>
                      <p className="mt-1 text-sm text-slate-400">{task}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-6 py-20">
          <div className="grid gap-6 md:grid-cols-3">
            {featureCards.map((feature) => (
              <article key={feature.title} className="rounded-3xl border border-white/10 bg-slate-900/60 p-6">
                <h2 className="text-xl font-semibold text-white">{feature.title}</h2>
                <p className="mt-3 text-sm leading-7 text-slate-300">{feature.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-6 py-4">
          <div className="grid gap-6 lg:grid-cols-3">
            {operatingModel.map((item) => (
              <article key={item.step} className="rounded-3xl border border-white/10 bg-slate-900/60 p-6">
                <p className="text-xs font-semibold uppercase tracking-[0.35em] text-amber-300">{item.step}</p>
                <h2 className="mt-4 text-2xl font-semibold text-white">{item.title}</h2>
                <p className="mt-3 text-sm leading-7 text-slate-300">{item.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="border-y border-white/10 bg-slate-900/40">
          <div className="mx-auto grid max-w-6xl gap-10 px-6 py-20 lg:grid-cols-2">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-amber-300">Best Fit</p>
              <h2 className="mt-4 text-3xl font-semibold text-white">Built for teams that need control, not novelty demos.</h2>
            </div>
            <ul className="grid gap-4 text-slate-300">
              {useCases.map((item) => (
                <li key={item} className="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-4">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-6 py-20">
          <div className="mb-8 rounded-3xl border border-emerald-400/20 bg-emerald-400/5 px-8 py-10">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-emerald-300">Go-To-Market Path</p>
            <h2 className="mt-4 text-3xl font-semibold text-white">Start with a pilot, not a platform migration.</h2>
            <p className="mt-4 max-w-3xl text-slate-300">
              The fastest path to value is one repo, one team, and one class of work with clear review gates. Use the pilot
              to prove repo integration, merge discipline, and delivery speed before rolling out more broadly.
            </p>
            <div className="mt-6 flex flex-wrap gap-4">
              <Link href="/demo" className="rounded-full bg-emerald-400 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-emerald-300">Request Pilot</Link>
              <Link href="/pricing" className="rounded-full border border-slate-700 px-5 py-3 text-sm text-slate-100 hover:border-slate-500">See Packaging</Link>
            </div>
          </div>
          <div className="rounded-3xl border border-sky-400/20 bg-sky-400/5 px-8 py-10">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-sky-300">Public Resources</p>
            <div className="mt-6 flex flex-wrap gap-4">
              <Link href="/security" className="rounded-full border border-slate-700 px-5 py-3 text-sm text-slate-100 hover:border-slate-500">Security</Link>
              <Link href="/about" className="rounded-full border border-slate-700 px-5 py-3 text-sm text-slate-100 hover:border-slate-500">About</Link>
              <Link href="/pricing" className="rounded-full border border-slate-700 px-5 py-3 text-sm text-slate-100 hover:border-slate-500">Pricing</Link>
              <Link href="/demo" className="rounded-full border border-slate-700 px-5 py-3 text-sm text-slate-100 hover:border-slate-500">Request Pilot</Link>
              <Link href="/faq" className="rounded-full border border-slate-700 px-5 py-3 text-sm text-slate-100 hover:border-slate-500">FAQ</Link>
              <Link href="/privacy" className="rounded-full border border-slate-700 px-5 py-3 text-sm text-slate-100 hover:border-slate-500">Privacy</Link>
              <Link href="/terms" className="rounded-full border border-slate-700 px-5 py-3 text-sm text-slate-100 hover:border-slate-500">Terms</Link>
              <Link href="/contact" className="rounded-full border border-slate-700 px-5 py-3 text-sm text-slate-100 hover:border-slate-500">Contact</Link>
            </div>
          </div>
        </section>
      </main>
      <PublicFooter />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
    </div>
  );
}
