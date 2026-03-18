import type { Metadata } from "next";
import Link from "next/link";
import { PublicPageShell } from "@/components/PublicPageShell";
import { absoluteUrl } from "@/lib/site";

export const metadata: Metadata = {
  title: "Pricing",
  description: "Commercial packaging for AeroSwarm pilots, team deployments, and enterprise rollouts.",
};

const tiers = [
  {
    name: "Pilot",
    fit: "Best for proving value on one repo and one engineering team.",
    price: "Guided pilot engagement",
    points: [
      "One workflow or repo scope",
      "Hands-on setup and operator support",
      "Review-gated delivery validation",
    ],
    cta: { href: "/demo", label: "Start Pilot" },
  },
  {
    name: "Team",
    fit: "Best for internal platform or product teams expanding regular usage.",
    price: "Annual platform pricing",
    points: [
      "Multiple repos and teams",
      "GitHub integration and PR sync",
      "Self-hosted deployment with audit trails",
    ],
    cta: { href: "/contact", label: "Talk Commercials" },
  },
  {
    name: "Enterprise",
    fit: "Best for org-wide rollout, compliance requirements, and infra control.",
    price: "Custom commercial terms",
    points: [
      "Private deployment architecture",
      "Operational onboarding and rollout planning",
      "Support path for platform and security review",
    ],
    cta: { href: "/contact", label: "Request Enterprise Review" },
  },
];

export default function PricingPage() {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Service",
    name: "AeroSwarm",
    serviceType: "AI agent orchestration for software delivery",
    url: absoluteUrl("/pricing"),
    offers: tiers.map((tier) => ({
      "@type": "Offer",
      name: tier.name,
      description: tier.fit,
    })),
  };

  return (
    <PublicPageShell
      eyebrow="Pricing"
      title="Commercial packaging built around pilots first."
      description="AeroSwarm should be bought the same way it should be deployed: start with one controlled workflow, prove operational fit, then expand to broader team usage."
    >
      <div className="grid gap-6 lg:grid-cols-3">
        {tiers.map((tier) => (
          <article key={tier.name} className="rounded-3xl border border-white/10 bg-slate-900/70 p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.35em] text-sky-300">{tier.name}</p>
            <h2 className="mt-4 text-2xl font-semibold text-white">{tier.price}</h2>
            <p className="mt-3 text-sm leading-7 text-slate-300">{tier.fit}</p>
            <ul className="mt-6 grid gap-3 text-sm text-slate-300">
              {tier.points.map((point) => (
                <li key={point} className="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3">
                  {point}
                </li>
              ))}
            </ul>
            <div className="mt-6">
              <Link
                href={tier.cta.href}
                className="inline-flex rounded-full bg-sky-400 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-sky-300"
              >
                {tier.cta.label}
              </Link>
            </div>
          </article>
        ))}
      </div>
      <div className="mt-10 rounded-3xl border border-amber-400/20 bg-amber-400/5 p-6">
        <h2 className="text-2xl font-semibold text-white">How to package this credibly</h2>
        <p className="mt-4 text-slate-300">
          Sell the first engagement around one high-value workflow: refactors, migrations, repetitive preflighted changes, or internal tooling work.
          That lets you prove repo integration, human approval flow, and deployment fit before promising broader autonomy.
        </p>
      </div>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
    </PublicPageShell>
  );
}
