/**
 * useSession hook — polls the backend for a session summary.
 */

"use client";

import useSWR from "swr";
import { fetchSession } from "../api";
import type { SessionResponse } from "../types";

const ACTIVE_SESSION_STATUSES = new Set(["queued", "planning", "running", "merging"]);

export function useSession(sessionId?: string) {
  const { data, error, isLoading } = useSWR<SessionResponse>(
    sessionId ? `session:${sessionId}` : null,
    () => fetchSession(sessionId!),
    {
      refreshInterval: (session) => (
        session && !ACTIVE_SESSION_STATUSES.has(session.status) ? 0 : 3000
      ),
    },
  );

  return { session: data, error, isLoading };
}
