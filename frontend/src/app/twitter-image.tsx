import { ImageResponse } from "next/og";
import { AeroSwarmOgImage, ogImageSize } from "@/lib/og";

export const alt = "AeroSwarm";
export const size = ogImageSize;
export const contentType = "image/png";

export default function TwitterImage() {
  return new ImageResponse(
    (
      <AeroSwarmOgImage
        eyebrow="AeroSwarm"
        title="Parallel agents. Human-reviewed merges. Self-hosted control."
        description="Multi-agent coding orchestration for teams shipping through audit trails and preflight gates."
      />
    ),
    size,
  );
}
