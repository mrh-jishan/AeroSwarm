import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { PublicPageShell } from "@/components/PublicPageShell";
import { getAllPostMeta, getBlogJsonLd, getPostBySlug } from "@/lib/blog";
import { absoluteUrl } from "@/lib/site";

interface BlogPostPageProps {
  params: Promise<{
    slug: string;
  }>;
}

export async function generateStaticParams() {
  return getAllPostMeta().map((post) => ({ slug: post.slug }));
}

export async function generateMetadata({ params }: BlogPostPageProps): Promise<Metadata> {
  const { slug } = await params;
  const post = await getPostBySlug(slug);
  if (!post) {
    return {};
  }

  return {
    title: post.title,
    description: post.excerpt,
    alternates: {
      canonical: absoluteUrl(`/blog/${post.slug}`),
    },
    openGraph: {
      type: "article",
      title: post.title,
      description: post.excerpt,
      url: absoluteUrl(`/blog/${post.slug}`),
      publishedTime: post.publishedAt,
    },
  };
}

export default async function BlogPostPage({ params }: BlogPostPageProps) {
  const { slug } = await params;
  const post = await getPostBySlug(slug);
  if (!post) {
    notFound();
  }

  const jsonLd = getBlogJsonLd(post);

  return (
    <PublicPageShell
      eyebrow="Blog"
      title={post.title}
      description={post.excerpt}
    >
      <article className="article-content">
        <p className="text-sm text-slate-400">
          {post.publishedAt} · {post.author}
        </p>
        <div
          className="mt-8"
          dangerouslySetInnerHTML={{ __html: post.contentHtml }}
        />
      </article>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
    </PublicPageShell>
  );
}
