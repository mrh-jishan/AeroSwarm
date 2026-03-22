/**
 * useAgents hook — polls the backend for active agents.
 * In Phase 2, this will be replaced with WebSocket-based real-time updates.
 */

"use client";

import useSWR from "swr";
import { fetchAgents } from "../api";
import type { AgentSummary } from "../types";

const ACTIVE_AGENT_STATUSES = new Set(["initializing", "running"]);
const ACTIVE_SESSION_STATUSES = new Set(["queued", "planning", "running", "merging"]);

export function useAgents(sessionId?: string, sessionStatus?: string) {
  const { data, error, isLoading } = useSWR<AgentSummary[]>(
    sessionId ? `session-agents:${sessionId}` : null,
    () => fetchAgents(sessionId!),
    {
      refreshInterval: (agents) => {
        if (!agents || agents.length === 0) {
          return sessionStatus && !ACTIVE_SESSION_STATUSES.has(sessionStatus) ? 0 : 3000;
        }
        return agents.some((agent) => ACTIVE_AGENT_STATUSES.has(agent.status)) ? 3000 : 0;
      },
    },
  );

  return { agents: data ?? [], error, isLoading };
}
