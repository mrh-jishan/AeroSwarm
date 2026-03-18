import Link from "next/link";

const links = [
  { href: "/about", label: "About" },
  { href: "/pricing", label: "Pricing" },
  { href: "/demo", label: "Request Pilot" },
  { href: "/blog", label: "Blog" },
  { href: "/faq", label: "FAQ" },
  { href: "/security", label: "Security" },
  { href: "/contact", label: "Contact" },
  { href: "/privacy", label: "Privacy" },
  { href: "/terms", label: "Terms" },
];

export function PublicHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-white/10 bg-slate-950/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="text-lg font-semibold tracking-tight text-white">
          Aero<span className="text-sky-400">Swarm</span>
        </Link>
        <nav className="hidden items-center gap-6 text-sm text-slate-300 lg:flex">
          {links.map((link) => (
            <Link key={link.href} href={link.href} className="hover:text-white">
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <Link
            href="/demo"
            className="hidden rounded-full bg-sky-400 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-sky-300 lg:inline-flex"
          >
            Request Pilot
          </Link>
          <Link
            href="/dashboard"
            className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-slate-500 hover:text-white"
          >
            Dashboard
          </Link>
        </div>
      </div>
    </header>
  );
}
