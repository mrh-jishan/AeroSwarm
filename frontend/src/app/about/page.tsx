import type { Metadata } from "next";
import { PublicPageShell } from "@/components/PublicPageShell";

export const metadata: Metadata = {
  title: "About",
  description: "What AeroSwarm is, who it is for, and how the platform fits into real engineering workflows.",
};

const principles = [
  {
    title: "Keep code changes isolated",
    body: "AeroSwarm launches agents into separate worktrees so parallel execution does not immediately become file corruption.",
  },
  {
    title: "Keep humans in the merge loop",
    body: "Automation can accelerate implementation, but merge authority stays with a human approver backed by checks and audit trails.",
  },
  {
    title: "Keep infrastructure under customer control",
    body: "The product is designed to work in environments where private repositories, credentials, and execution boundaries matter.",
  },
];

export default function AboutPage() {
  return (
    <PublicPageShell
      eyebrow="About"
      title="AeroSwarm is built for software teams that want agent speed without losing operational control."
      description="The product sits between a coding assistant and a full autonomous engineer: faster than a single-agent loop, but still structured around review, isolation, and deployment discipline."
    >
      <div className="grid gap-6">
        {principles.map((item) => (
          <article key={item.title} className="rounded-3xl border border-white/10 bg-slate-900/70 p-6">
            <h2 className="text-xl font-semibold text-white">{item.title}</h2>
            <p className="mt-3 text-slate-300">{item.body}</p>
          </article>
        ))}
      </div>
    </PublicPageShell>
  );
}
