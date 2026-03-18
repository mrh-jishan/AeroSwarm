import type { CSSProperties } from "react";

export const ogImageSize = {
  width: 1200,
  height: 630,
};

const pageStyle: CSSProperties = {
  display: "flex",
  width: "100%",
  height: "100%",
  background: "linear-gradient(135deg, #020617 0%, #0f172a 55%, #082f49 100%)",
  color: "#f8fafc",
  padding: "56px",
  position: "relative",
  fontFamily: "system-ui, sans-serif",
};

const haloStyle: CSSProperties = {
  position: "absolute",
  borderRadius: "9999px",
  filter: "blur(16px)",
  opacity: 0.9,
};

export function AeroSwarmOgImage({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div style={pageStyle}>
      <div
        style={{
          ...haloStyle,
          width: 380,
          height: 380,
          right: 40,
          top: 40,
          background: "radial-gradient(circle, rgba(56,189,248,0.35), transparent 70%)",
        }}
      />
      <div
        style={{
          ...haloStyle,
          width: 280,
          height: 280,
          left: -40,
          bottom: -40,
          background: "radial-gradient(circle, rgba(251,191,36,0.2), transparent 72%)",
        }}
      />
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          width: "100%",
          border: "1px solid rgba(255,255,255,0.12)",
          borderRadius: 32,
          padding: "40px",
          background: "rgba(15,23,42,0.58)",
          boxShadow: "0 25px 80px rgba(2,6,23,0.45)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span
              style={{
                color: "#7dd3fc",
                fontSize: 22,
                textTransform: "uppercase",
                letterSpacing: "0.35em",
                fontWeight: 700,
              }}
            >
              {eyebrow}
            </span>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "12px 18px",
              borderRadius: 999,
              border: "1px solid rgba(125,211,252,0.22)",
              color: "#e2e8f0",
              fontSize: 24,
            }}
          >
            <span style={{ fontWeight: 700 }}>Aero</span>
            <span style={{ color: "#38bdf8", fontWeight: 700 }}>Swarm</span>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 22, maxWidth: 920 }}>
          <h1
            style={{
              fontSize: 68,
              lineHeight: 1.02,
              fontWeight: 750,
              margin: 0,
              letterSpacing: "-0.05em",
            }}
          >
            {title}
          </h1>
          <p
            style={{
              margin: 0,
              fontSize: 30,
              lineHeight: 1.35,
              color: "#cbd5e1",
              maxWidth: 900,
            }}
          >
            {description}
          </p>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", gap: 12 }}>
            {["Parallel Agents", "GitHub Sync", "Human Review"].map((pill) => (
              <div
                key={pill}
                style={{
                  padding: "10px 18px",
                  borderRadius: 999,
                  background: "rgba(15,23,42,0.85)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  color: "#cbd5e1",
                  fontSize: 22,
                }}
              >
                {pill}
              </div>
            ))}
          </div>
          <div style={{ color: "#94a3b8", fontSize: 22 }}>aeroswarm.dev</div>
        </div>
      </div>
    </div>
  );
}
