/**
 * useSession hook — polls the backend for a session summary.
 */

"use client";

import useSWR from "swr";
import { fetchSession } from "../api";
import type { SessionResponse } from "../types";

export function useSession(sessionId?: string) {
  const { data, error, isLoading } = useSWR<SessionResponse>(
    sessionId ? `session:${sessionId}` : null,
    () => fetchSession(sessionId!),
    {
      refreshInterval: 3000,
    },
  );

  return { session: data, error, isLoading };
}
