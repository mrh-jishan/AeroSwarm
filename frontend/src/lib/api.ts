/** API client helpers — thin wrappers over fetch. */

import type {
  AgentDetail,
  AgentDirectoryListing,
  AgentFileDocument,
  AgentLogsPage,
  AgentSummary,
  AuthResponse,
  GitHubRepoSuggestion,
  MergeRequestResponse,
  PasswordResetRequestResponse,
  ProviderConnection,
  SessionAuditEvent,
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

function readCookie(name: string): string | undefined {
  if (typeof document === "undefined") {
    return undefined;
  }

  const prefix = `${name}=`;
  const cookie = document.cookie
    .split(";")
    .map((entry) => entry.trim())
    .find((entry) => entry.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : undefined;
}

function csrfHeaders(method?: string): Record<string, string> {
  const normalizedMethod = method?.toUpperCase() ?? "GET";
  if (normalizedMethod === "GET" || normalizedMethod === "HEAD" || normalizedMethod === "OPTIONS") {
    return {};
  }

  const csrfToken = readCookie("aeroswarm_csrf");
  return csrfToken ? { "X-CSRF-Token": csrfToken } : {};
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
  const headers = buildHeaders({
    ...csrfHeaders(init.method),
    ...((init.headers as Record<string, string>) || {}),
  });
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
  llmProvider: "openai" | "gemini";
  managerModel?: string;
  agentModel?: string;
  providerConnectionId?: string;
  repoAccessToken?: string;
  repoUsername?: string;
}): Promise<SessionResponse> {
  return requestJson<SessionResponse>("/api/sessions/", {
    method: "POST",
    body: JSON.stringify({
      repo_url: payload.repoUrl,
      prompt: payload.prompt,
      llm_provider: payload.llmProvider,
      manager_model: payload.managerModel || undefined,
      agent_model: payload.agentModel || undefined,
      provider_connection_id: payload.providerConnectionId || undefined,
      repo_access_token: payload.repoAccessToken || undefined,
      repo_username: payload.repoUsername || undefined,
    }),
  });
}

export async function listSessions(): Promise<SessionResponse[]> {
  return requestJson<SessionResponse[]>("/api/sessions/", { method: "GET" });
}

export async function listProviderConnections(): Promise<ProviderConnection[]> {
  return requestJson<ProviderConnection[]>("/api/vcs/connections", { method: "GET" });
}

export async function listGitHubRepositories(
  providerConnectionId: string,
  query = "",
  limit = 8,
): Promise<GitHubRepoSuggestion[]> {
  const params = new URLSearchParams({
    provider_connection_id: providerConnectionId,
    limit: String(limit),
  });
  if (query.trim()) {
    params.set("q", query.trim());
  }
  return requestJson<GitHubRepoSuggestion[]>(`/api/vcs/github/repos?${params.toString()}`, {
    method: "GET",
  });
}

export async function fetchSession(sessionId: string): Promise<SessionResponse> {
  return requestJson<SessionResponse>(`/api/sessions/${sessionId}`, { method: "GET" });
}

export async function listAgentFiles(agentId: string, path = ""): Promise<AgentDirectoryListing> {
  const params = new URLSearchParams();
  if (path) {
    params.set("path", path);
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  return requestJson<AgentDirectoryListing>(`/api/agents/${agentId}/files${suffix}`, {
    method: "GET",
  });
}

export async function fetchAgentFile(agentId: string, path: string): Promise<AgentFileDocument> {
  const params = new URLSearchParams({ path });
  return requestJson<AgentFileDocument>(`/api/agents/${agentId}/files?${params.toString()}`, {
    method: "GET",
  });
}

export async function updateAgentFile(
  agentId: string,
  path: string,
  content: string,
): Promise<void> {
  const params = new URLSearchParams({ path });
  await requestJson(`/api/agents/${agentId}/files?${params.toString()}`, {
    method: "PUT",
    body: JSON.stringify({ content }),
  });
}

export async function fetchAgentLogs(agentId: string): Promise<string[]> {
  return fetchAgentLogsPage(agentId).then((response) => response.lines);
}

export async function fetchAgentLogsPage(
  agentId: string,
  options: { before?: number; limit?: number } = {},
): Promise<AgentLogsPage> {
  const params = new URLSearchParams();
  if (options.before !== undefined) {
    params.set("before", String(options.before));
  }
  if (options.limit !== undefined) {
    params.set("limit", String(options.limit));
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  const response = await requestJson<{ lines: string[]; next_before: number | null }>(
    `/api/agents/${agentId}/logs${suffix}`,
    { method: "GET" },
  );
  return {
    lines: response.lines,
    nextBefore: response.next_before,
  };
}

export async function retrySession(sessionId: string): Promise<SessionResponse> {
  return requestJson<SessionResponse>(`/api/sessions/${sessionId}/retry`, { method: "POST" });
}

export async function stopSession(sessionId: string): Promise<SessionResponse> {
  return requestJson<SessionResponse>(`/api/sessions/${sessionId}/stop`, { method: "POST" });
}

export async function fetchSessionAudit(sessionId: string): Promise<SessionAuditEvent[]> {
  return requestJson<SessionAuditEvent[]>(`/api/sessions/${sessionId}/audit`, { method: "GET" });
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
  fullName: string;
  jobTitle?: string;
  companyName?: string;
  timezone?: string;
  bio?: string;
}): Promise<AuthResponse> {
  return requestJson<AuthResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({
      email: payload.email,
      password: payload.password,
      full_name: payload.fullName,
      job_title: payload.jobTitle || undefined,
      company_name: payload.companyName || undefined,
      timezone: payload.timezone || undefined,
      bio: payload.bio || undefined,
    }),
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

export async function fetchWebSocketToken(): Promise<string> {
  const response = await requestJson<{ token: string }>("/api/auth/ws-token", { method: "GET" });
  return response.token;
}

export async function updateMyProfile(payload: {
  fullName: string;
  jobTitle?: string;
  companyName?: string;
  timezone?: string;
  bio?: string;
}): Promise<User> {
  return requestJson<User>("/api/auth/me", {
    method: "PATCH",
    body: JSON.stringify({
      full_name: payload.fullName,
      job_title: payload.jobTitle || undefined,
      company_name: payload.companyName || undefined,
      timezone: payload.timezone || undefined,
      bio: payload.bio || undefined,
    }),
  });
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
    headers: buildHeaders(csrfHeaders("POST")),
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

export async function fetchAgents(sessionId: string): Promise<AgentSummary[]> {
  return requestJson<AgentSummary[]>(`/api/sessions/${sessionId}/agents`, { method: "GET" });
}

export async function fetchAgent(agentId: string): Promise<AgentDetail> {
  return requestJson<AgentDetail>(`/api/agents/${agentId}`, { method: "GET" });
}

export async function createMergeRequest(taskId: string): Promise<MergeRequestResponse> {
  return requestJson<MergeRequestResponse>("/api/merge-requests/", {
    method: "POST",
    body: JSON.stringify({ task_id: taskId }),
  });
}

export async function fetchMergeRequest(mrId: string): Promise<MergeRequestResponse> {
  return requestJson<MergeRequestResponse>(`/api/merge-requests/${mrId}`, {
    method: "GET",
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
