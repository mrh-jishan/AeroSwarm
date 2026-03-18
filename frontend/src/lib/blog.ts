import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";
import { remark } from "remark";
import html from "remark-html";
import { absoluteUrl } from "@/lib/site";

export interface BlogPostMeta {
  slug: string;
  title: string;
  excerpt: string;
  publishedAt: string;
  author: string;
  tags: string[];
}

export interface BlogPost extends BlogPostMeta {
  contentHtml: string;
}

const blogDirectory = path.join(process.cwd(), "content", "blog");

function parseMeta(slug: string, raw: string): BlogPostMeta & { body: string } {
  const { data, content } = matter(raw);
  return {
    slug,
    title: String(data.title ?? slug),
    excerpt: String(data.excerpt ?? ""),
    publishedAt: String(data.publishedAt ?? new Date().toISOString()),
    author: String(data.author ?? "AeroSwarm Team"),
    tags: Array.isArray(data.tags) ? data.tags.map((tag) => String(tag)) : [],
    body: content,
  };
}

export function getAllPostMeta(): BlogPostMeta[] {
  if (!fs.existsSync(blogDirectory)) {
    return [];
  }

  return fs
    .readdirSync(blogDirectory)
    .filter((file) => file.endsWith(".md"))
    .map((file) => {
      const slug = file.replace(/\.md$/, "");
      const raw = fs.readFileSync(path.join(blogDirectory, file), "utf-8");
      const { body: _body, ...meta } = parseMeta(slug, raw);
      return meta;
    })
    .sort((left, right) => right.publishedAt.localeCompare(left.publishedAt));
}

export async function getPostBySlug(slug: string): Promise<BlogPost | null> {
  const fullPath = path.join(blogDirectory, `${slug}.md`);
  if (!fs.existsSync(fullPath)) {
    return null;
  }

  const raw = fs.readFileSync(fullPath, "utf-8");
  const parsed = parseMeta(slug, raw);
  const processed = await remark().use(html).process(parsed.body);

  return {
    slug: parsed.slug,
    title: parsed.title,
    excerpt: parsed.excerpt,
    publishedAt: parsed.publishedAt,
    author: parsed.author,
    tags: parsed.tags,
    contentHtml: processed.toString(),
  };
}

export function getBlogJsonLd(post: BlogPost) {
  return {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    headline: post.title,
    description: post.excerpt,
    datePublished: post.publishedAt,
    author: {
      "@type": "Person",
      name: post.author,
    },
    mainEntityOfPage: absoluteUrl(`/blog/${post.slug}`),
  };
}
