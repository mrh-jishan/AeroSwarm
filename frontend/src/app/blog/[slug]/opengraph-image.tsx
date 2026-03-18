import { ImageResponse } from "next/og";
import { getPostBySlug } from "@/lib/blog";
import { AeroSwarmOgImage, ogImageSize } from "@/lib/og";

export const alt = "AeroSwarm blog post";
export const size = ogImageSize;
export const contentType = "image/png";

interface BlogOgImageProps {
  params: Promise<{
    slug: string;
  }>;
}

export default async function BlogPostOpenGraphImage({ params }: BlogOgImageProps) {
  const { slug } = await params;
  const post = await getPostBySlug(slug);

  return new ImageResponse(
    (
      <AeroSwarmOgImage
        eyebrow="AeroSwarm Blog"
        title={post?.title ?? "AeroSwarm"}
        description={post?.excerpt ?? "Product updates and engineering notes from AeroSwarm."}
      />
    ),
    size,
  );
}
