import type { Metadata } from "next";
import { PublicPageShell } from "@/components/PublicPageShell";

export const metadata: Metadata = {
  title: "Security",
  description: "Security posture and platform controls for AeroSwarm.",
};

const controls = [
  "Cookie-backed auth with CSRF protection for browser mutations",
  "Encrypted storage for provider access credentials",
  "Human-reviewed merge approval flow with audit events",
  "Background worker separation for long-running orchestration",
  "Container-isolated task execution with scoped worktrees",
];

export default function SecurityPage() {
  return (
    <PublicPageShell
      eyebrow="Trust"
      title="Security"
      description="AeroSwarm is designed for teams that want agent automation without giving up infrastructure control."
    >
      <div className="grid gap-4">
        {controls.map((control) => (
          <div key={control} className="rounded-2xl border border-white/10 bg-slate-900/70 px-5 py-4 text-slate-300">
            {control}
          </div>
        ))}
      </div>
    </PublicPageShell>
  );
}
