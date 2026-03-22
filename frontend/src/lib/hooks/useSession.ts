/**
 * useSession hook — loads a session summary and relies on websocket cache updates.
 */

"use client";

import useSWR from "swr";
import { fetchSession } from "../api";
import type { SessionResponse } from "../types";

export function useSession(sessionId?: string) {
  const { data, error, isLoading } = useSWR<SessionResponse>(
    sessionId ? `session:${sessionId}` : null,
    () => fetchSession(sessionId!),
  );

  return { session: data, error, isLoading };
}
