import Link from "next/link";

export function PublicFooter() {
  return (
    <footer className="border-t border-white/10 bg-slate-950">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-10 text-sm text-slate-400 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="font-medium text-slate-200">AeroSwarm</p>
          <p>Parallel agent orchestration for software teams.</p>
        </div>
        <div className="flex flex-wrap gap-4">
          <Link href="/about" className="hover:text-white">About</Link>
          <Link href="/pricing" className="hover:text-white">Pricing</Link>
          <Link href="/demo" className="hover:text-white">Request Pilot</Link>
          <Link href="/blog" className="hover:text-white">Blog</Link>
          <Link href="/faq" className="hover:text-white">FAQ</Link>
          <Link href="/feed.xml" className="hover:text-white">RSS</Link>
          <Link href="/security" className="hover:text-white">Security</Link>
          <Link href="/contact" className="hover:text-white">Contact</Link>
          <Link href="/privacy" className="hover:text-white">Privacy</Link>
          <Link href="/terms" className="hover:text-white">Terms</Link>
          <Link href="/dashboard" className="hover:text-white">Dashboard</Link>
        </div>
      </div>
    </footer>
  );
}
