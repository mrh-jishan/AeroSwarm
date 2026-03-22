/**
 * useAgents hook — loads agents and relies on websocket cache updates.
 */

"use client";

import useSWR from "swr";
import { fetchAgents } from "../api";
import type { AgentSummary } from "../types";

export function useAgents(sessionId?: string, _sessionStatus?: string) {
  const { data, error, isLoading } = useSWR<AgentSummary[]>(
    sessionId ? `session-agents:${sessionId}` : null,
    () => fetchAgents(sessionId!),
  );

  return { agents: data ?? [], error, isLoading };
}
