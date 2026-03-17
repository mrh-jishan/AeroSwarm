/**
 * useAgents hook — polls the backend for active agents.
 * In Phase 2, this will be replaced with WebSocket-based real-time updates.
 */

"use client";

import useSWR from "swr";
import type { AgentSummary } from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export function useAgents(sessionId?: string) {
  const url = sessionId
    ? `${API_BASE}/api/sessions/${sessionId}/agents`
    : null;

  const { data, error, isLoading } = useSWR<AgentSummary[]>(url, fetcher, {
    refreshInterval: 3000,
  });

  return { agents: data ?? [], error, isLoading };
}
