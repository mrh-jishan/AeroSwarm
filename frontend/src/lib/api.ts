/** API client helpers — thin wrappers over fetch. */

import type { SessionResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function createSession(payload: {
  repoUrl: string;
  prompt: string;
}): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/api/sessions/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_url: payload.repoUrl, prompt: payload.prompt }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }

  return res.json();
}

export async function fetchAgents(sessionId: string) {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/agents`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
