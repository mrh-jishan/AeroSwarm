/**
 * AuthPageShell — shared layout for dedicated login and registration routes.
 */

import type { ReactNode } from "react";
import Link from "next/link";

export function AuthPageShell({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(56,189,248,0.16),_transparent_28%),radial-gradient(circle_at_bottom_right,_rgba(14,165,233,0.1),_transparent_24%),#020617] px-6 py-10 text-slate-100">
      <div className="mx-auto max-w-6xl">
        <div className="mb-8 flex items-center justify-between gap-4">
          <Link href="/" className="text-3xl font-bold tracking-tight text-white">
            Aero<span className="text-sky-400">Swarm</span>
          </Link>
          <div className="flex gap-3 text-sm">
            <Link
              href="/login"
              className="rounded-full border border-slate-800 px-4 py-2 text-slate-300 transition hover:border-slate-600 hover:text-white"
            >
              Sign In
            </Link>
            <Link
              href="/register"
              className="rounded-full border border-slate-800 px-4 py-2 text-slate-300 transition hover:border-slate-600 hover:text-white"
            >
              Register
            </Link>
          </div>
        </div>

        <div className="mb-8 max-w-3xl">
          <p className="text-xs uppercase tracking-[0.35em] text-sky-300">{eyebrow}</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight text-white md:text-5xl">{title}</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300">{description}</p>
        </div>

        {children}
      </div>
    </main>
  );
}
