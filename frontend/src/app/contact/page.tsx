import type { Metadata } from "next";
import Link from "next/link";
import { LeadCaptureForm } from "@/components/LeadCaptureForm";
import { PublicPageShell } from "@/components/PublicPageShell";

export const metadata: Metadata = {
  title: "Contact",
  description: "Contact AeroSwarm for pilots, deployment questions, and commercial discussions.",
};

export default function ContactPage() {
  return (
    <PublicPageShell
      eyebrow="Contact"
      title="Talk to the team"
      description="Use this page as the public contact surface for pilots, private deployments, and product discussions."
    >
      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <LeadCaptureForm
          source="contact"
          submitLabel="Send Inquiry"
          successMessage="Inquiry received. Follow up from your configured delivery target should happen next."
          intro="Use this form for pricing, deployment planning, or commercial qualification."
        />
        <div className="grid gap-6">
          <div className="rounded-3xl border border-white/10 bg-slate-900/70 p-6">
          <h2 className="text-xl font-semibold text-white">Commercial</h2>
          <p className="mt-3 text-slate-300">
            For pilots, pricing, or private deployment conversations, point this page at your sales or founder inbox.
          </p>
          <p className="mt-4 text-sm text-slate-400">Example: founders@your-domain.com</p>
          <div className="mt-6">
            <Link
              href="/demo"
              className="rounded-full bg-sky-400 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-sky-300"
            >
              Request Pilot Flow
            </Link>
          </div>
          </div>
          <div className="rounded-3xl border border-white/10 bg-slate-900/70 p-6">
            <h2 className="text-xl font-semibold text-white">Security and support</h2>
            <p className="mt-3 text-slate-300">
              Use a separate inbox for security disclosure, platform incidents, or enterprise support questions.
            </p>
            <p className="mt-4 text-sm text-slate-400">Example: security@your-domain.com</p>
          </div>
        </div>
      </div>
    </PublicPageShell>
  );
}
