import type { Metadata } from "next";
import { PublicPageShell } from "@/components/PublicPageShell";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "Privacy policy for AeroSwarm public site and hosted product usage.",
};

export default function PrivacyPage() {
  return (
    <PublicPageShell
      eyebrow="Legal"
      title="Privacy Policy"
      description="How AeroSwarm handles account data, repository metadata, and operational logs."
    >
      <div className="article-content space-y-6 text-slate-300">
        <p>
          AeroSwarm stores the minimum account, session, and audit information required to
          operate the product. Repository credentials are encrypted before storage.
        </p>
        <h2>What We Collect</h2>
        <p>
          We may store account identifiers, provider connection metadata, session prompts,
          audit events, and system logs generated during orchestration and merge review.
        </p>
        <h2>How We Use Data</h2>
        <p>
          Data is used to authenticate users, run requested sessions, display status in the
          dashboard, and provide traceability for approvals and merge actions.
        </p>
        <h2>Repository Access</h2>
        <p>
          Provider tokens and installation credentials are used only to clone repositories,
          open pull requests, comment on preflight status, and merge approved work.
        </p>
        <h2>Contact</h2>
        <p>
          For privacy questions, use the contact details on the public contact page.
        </p>
      </div>
    </PublicPageShell>
  );
}
