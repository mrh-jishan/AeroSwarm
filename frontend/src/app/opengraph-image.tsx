import { ImageResponse } from "next/og";
import { AeroSwarmOgImage, ogImageSize } from "@/lib/og";

export const alt = "AeroSwarm";
export const size = ogImageSize;
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <AeroSwarmOgImage
        eyebrow="Parallel Agent Software Factory"
        title="Run multiple software agents without giving up review control."
        description="AeroSwarm coordinates isolated coding agents, preflight checks, and merge approval for engineering teams."
      />
    ),
    size,
  );
}
