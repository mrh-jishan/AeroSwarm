import type { ReactNode } from "react";
import { PublicFooter } from "@/components/PublicFooter";
import { PublicHeader } from "@/components/PublicHeader";

interface PublicPageShellProps {
  title: string;
  eyebrow?: string;
  description: string;
  children: ReactNode;
}

export function PublicPageShell({
  title,
  eyebrow,
  description,
  children,
}: PublicPageShellProps) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <PublicHeader />
      <main>
        <section className="border-b border-white/10 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.16),_transparent_48%),linear-gradient(180deg,_rgba(15,23,42,1),_rgba(2,6,23,1))]">
          <div className="mx-auto max-w-4xl px-6 py-20">
            {eyebrow ? (
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.3em] text-sky-300">{eyebrow}</p>
            ) : null}
            <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-white md:text-5xl">{title}</h1>
            <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-300">{description}</p>
          </div>
        </section>
        <section className="mx-auto max-w-4xl px-6 py-14">{children}</section>
      </main>
      <PublicFooter />
    </div>
  );
}
