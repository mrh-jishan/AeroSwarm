import type { MetadataRoute } from "next";
import { absoluteUrl } from "@/lib/site";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: ["/", "/blog", "/contact", "/privacy", "/security", "/terms"],
      disallow: ["/dashboard"],
    },
    sitemap: absoluteUrl("/sitemap.xml"),
  };
}
