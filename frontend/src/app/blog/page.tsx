import type { Metadata } from "next";
import Link from "next/link";
import { PublicPageShell } from "@/components/PublicPageShell";
import { getAllPostMeta } from "@/lib/blog";

export const metadata: Metadata = {
  title: "Blog",
  description: "Product updates, engineering notes, and deployment guidance for AeroSwarm.",
};

export default function BlogIndexPage() {
  const posts = getAllPostMeta();

  return (
    <PublicPageShell
      eyebrow="Blog"
      title="Engineering notes and product updates"
      description="Markdown-backed articles for launch notes, deployment guidance, and architecture decisions."
    >
      <div className="grid gap-6">
        {posts.map((post) => (
          <article key={post.slug} className="rounded-3xl border border-white/10 bg-slate-900/70 p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-sky-300">{post.publishedAt}</p>
            <h2 className="mt-3 text-2xl font-semibold text-white">
              <Link href={`/blog/${post.slug}`} className="hover:text-sky-300">
                {post.title}
              </Link>
            </h2>
            <p className="mt-3 text-slate-300">{post.excerpt}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {post.tags.map((tag) => (
                <span key={tag} className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300">
                  {tag}
                </span>
              ))}
            </div>
          </article>
        ))}
      </div>
    </PublicPageShell>
  );
}
