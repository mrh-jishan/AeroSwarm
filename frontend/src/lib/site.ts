export const siteConfig = {
  name: "AeroSwarm",
  description: "Parallel AI agent orchestration for software teams that want secure, human-reviewed execution.",
  siteUrl: process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000",
};

export function absoluteUrl(path = "/") {
  return new URL(path, siteConfig.siteUrl).toString();
}
