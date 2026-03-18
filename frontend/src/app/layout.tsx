import type { Metadata } from "next";
import "./globals.css";
import { absoluteUrl, siteConfig } from "@/lib/site";

export const metadata: Metadata = {
  metadataBase: new URL(siteConfig.siteUrl),
  title: {
    default: "AeroSwarm | Parallel Agent Software Factory",
    template: "%s | AeroSwarm",
  },
  description: siteConfig.description,
  alternates: {
    canonical: absoluteUrl("/"),
    types: {
      "application/rss+xml": absoluteUrl("/feed.xml"),
    },
  },
  openGraph: {
    title: "AeroSwarm",
    description: siteConfig.description,
    url: absoluteUrl("/"),
    siteName: siteConfig.name,
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "AeroSwarm",
    description: siteConfig.description,
  },
  keywords: [
    "multi-agent coding",
    "ai software engineering",
    "self-hosted coding agents",
    "github agent orchestration",
    "parallel coding agents",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
