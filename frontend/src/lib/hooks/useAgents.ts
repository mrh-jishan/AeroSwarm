/**
 * useAgents hook — polls the backend for active agents.
 * In Phase 2, this will be replaced with WebSocket-based real-time updates.
 */

"use client";

import useSWR from "swr";
import { fetchAgents } from "../api";
import type { AgentSummary } from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function useAgents(sessionId?: string) {
  const { data, error, isLoading } = useSWR<AgentSummary[]>(
    sessionId ? `session-agents:${sessionId}` : null,
    () => fetchAgents(sessionId!),
    {
      refreshInterval: 3000,
    },
  );

  return { agents: data ?? [], error, isLoading };
}
