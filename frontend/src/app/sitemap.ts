import type { MetadataRoute } from "next";
import { getAllPostMeta } from "@/lib/blog";
import { absoluteUrl } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  const staticPages = [
    "/",
    "/about",
    "/blog",
    "/contact",
    "/demo",
    "/faq",
    "/feed.xml",
    "/pricing",
    "/privacy",
    "/security",
    "/terms",
  ];

  return [
    ...staticPages.map((path) => ({
      url: absoluteUrl(path),
      lastModified: new Date(),
    })),
    ...getAllPostMeta().map((post) => ({
      url: absoluteUrl(`/blog/${post.slug}`),
      lastModified: new Date(post.publishedAt),
    })),
  ];
}
