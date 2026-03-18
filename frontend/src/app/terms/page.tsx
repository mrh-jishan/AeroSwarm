import type { Metadata } from "next";
import { PublicPageShell } from "@/components/PublicPageShell";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "Terms governing use of the AeroSwarm product and public website.",
};

export default function TermsPage() {
  return (
    <PublicPageShell
      eyebrow="Legal"
      title="Terms of Service"
      description="Baseline commercial and operational terms for using AeroSwarm."
    >
      <div className="article-content space-y-6 text-slate-300">
        <p>
          By using AeroSwarm, you agree to use the service only for repositories and systems
          you are authorized to access.
        </p>
        <h2>Acceptable Use</h2>
        <p>
          You may not use the service to access repositories unlawfully, interfere with
          infrastructure, or attempt to bypass account, audit, or merge controls.
        </p>
        <h2>Human Approval</h2>
        <p>
          AeroSwarm is designed to support human-reviewed software delivery. Final merge
          responsibility remains with the customer and its authorized approvers.
        </p>
        <h2>Availability</h2>
        <p>
          Hosted or self-managed deployments may experience outages, maintenance windows,
          or provider failures. Production usage should include your own backup and review procedures.
        </p>
      </div>
    </PublicPageShell>
  );
}
