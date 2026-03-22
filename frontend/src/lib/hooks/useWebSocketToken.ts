/**
 * useWebSocketToken — fetches a short-lived websocket bearer token for authenticated realtime routes.
 */

"use client";

import useSWR from "swr";
import { fetchWebSocketToken } from "../api";

export function useWebSocketToken(enabled = true) {
  const { data, error, isLoading, mutate } = useSWR<string>(
    enabled ? "websocket-token" : null,
    fetchWebSocketToken,
    {
      revalidateOnFocus: false,
      dedupingInterval: 60_000,
    },
  );

  return { token: data, error, isLoading, refreshToken: mutate };
}
