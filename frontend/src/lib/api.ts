/** API client helpers — thin wrappers over fetch. */

import type {
  AuthResponse,
  MergeRequestResponse,
  PasswordResetRequestResponse,
  ProviderConnection,
  SessionResponse,
  User,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_TOKEN = process.env.NEXT_PUBLIC_AEROSWARM_TOKEN;

export function getApiToken(): string | undefined {
  return API_TOKEN || undefined;
}

export function clearApiToken() {
  // Cookie-backed auth does not require browser-side token storage.
}

function buildHeaders(extra: Record<string, string> = {}) {
  const token = getApiToken();
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

async function requestJson<T>(path: string, init: RequestInit = {}, retryOnAuth = true): Promise<T> {
  const headers = buildHeaders((init.headers as Record<string, string>) || {});
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers,
  });

  if (res.status === 401 && retryOnAuth && !API_TOKEN) {
    try {
      await refreshAccessToken();
      return requestJson<T>(path, init, false);
    } catch {
      clearApiToken();
    }
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

export async function createSession(payload: {
  repoUrl: string;
  prompt: string;
  providerConnectionId?: string;
  repoAccessToken?: string;
  repoUsername?: string;
}): Promise<SessionResponse> {
  return requestJson<SessionResponse>("/api/sessions/", {
    method: "POST",
    body: JSON.stringify({
      repo_url: payload.repoUrl,
      prompt: payload.prompt,
      provider_connection_id: payload.providerConnectionId || undefined,
      repo_access_token: payload.repoAccessToken || undefined,
      repo_username: payload.repoUsername || undefined,
    }),
  });
}

export async function listProviderConnections(): Promise<ProviderConnection[]> {
  return requestJson<ProviderConnection[]>("/api/vcs/connections", { method: "GET" });
}

export async function connectGitHub(payload: {
  accessToken: string;
}): Promise<ProviderConnection> {
  return requestJson<ProviderConnection>("/api/vcs/github/connect", {
    method: "POST",
    body: JSON.stringify({ access_token: payload.accessToken }),
  });
}

export function getGitHubOAuthStartUrl(redirectPath = "/"): string {
  const url = new URL(`${API_BASE}/api/vcs/github/oauth/start`);
  url.searchParams.set("redirect_path", redirectPath);
  return url.toString();
}

export function getGitHubAppInstallStartUrl(redirectPath = "/"): string {
  const url = new URL(`${API_BASE}/api/vcs/github-app/install/start`);
  url.searchParams.set("redirect_path", redirectPath);
  return url.toString();
}

export async function register(payload: {
  email: string;
  password: string;
}): Promise<AuthResponse> {
  return requestJson<AuthResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function login(payload: {
  email: string;
  password: string;
}): Promise<AuthResponse> {
  return requestJson<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchMe(): Promise<User> {
  return requestJson<User>("/api/auth/me", { method: "GET" });
}

export async function refreshAccessToken(): Promise<AuthResponse> {
  return requestJson<AuthResponse>("/api/auth/refresh", {
    method: "POST",
  }, false);
}

export async function logout(): Promise<void> {
  await fetch(`${API_BASE}/api/auth/logout`, {
    method: "POST",
    credentials: "include",
    headers: buildHeaders(),
  }).catch(() => undefined);

  clearApiToken();
}

export async function requestPasswordReset(payload: {
  email: string;
}): Promise<PasswordResetRequestResponse> {
  return requestJson<PasswordResetRequestResponse>("/api/auth/password-reset/request", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function confirmPasswordReset(payload: {
  token: string;
  newPassword: string;
}): Promise<void> {
  await requestJson<void>("/api/auth/password-reset/confirm", {
    method: "POST",
    body: JSON.stringify({
      token: payload.token,
      new_password: payload.newPassword,
    }),
  });
}

export async function fetchAgents(sessionId: string) {
  return requestJson(`/api/sessions/${sessionId}/agents`, { method: "GET" });
}

export async function createMergeRequest(taskId: string): Promise<MergeRequestResponse> {
  return requestJson<MergeRequestResponse>("/api/merge-requests/", {
    method: "POST",
    body: JSON.stringify({ task_id: taskId }),
  });
}

export async function approveMergeRequest(mrId: string, approvedBy: string) {
  return requestJson(`/api/merge-requests/${mrId}/approve`, {
    method: "POST",
    body: JSON.stringify({ approved_by: approvedBy }),
  });
}

export async function rejectMergeRequest(mrId: string, rejectedBy: string) {
  return requestJson(`/api/merge-requests/${mrId}/reject`, {
    method: "POST",
    body: JSON.stringify({ rejected_by: rejectedBy }),
  });
}
