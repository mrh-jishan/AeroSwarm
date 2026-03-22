/** Shared TypeScript types for the AeroSwarm frontend. */

export interface AgentSummary {
  id: string;
  taskId: string;
  taskTitle: string;
  scopeDir: string;
  status: "initializing" | "running" | "idle" | "stopped" | "error";
  port: number | null;
  previewUrl: string | null;
}

export interface AgentDetail {
  id: string;
  session_id: string;
  task_id: string;
  task_title: string;
  scope_dir: string;
  status: "initializing" | "running" | "idle" | "stopped" | "error";
  port: number | null;
}

export interface AgentLogsPage {
  lines: string[];
  nextBefore: number | null;
}

export interface AgentFileEntry {
  name: string;
  is_dir: boolean;
}

export interface AgentDirectoryListing {
  path: string;
  entries: AgentFileEntry[];
}

export interface AgentFileDocument {
  path: string;
  content: string;
}

export interface SessionResponse {
  id: string;
  provider_connection_id?: string | null;
  repo_url: string;
  vcs_provider?: string | null;
  repo_owner?: string | null;
  repo_name?: string | null;
  base_branch?: string | null;
  llm_provider: "openai" | "gemini";
  manager_model: string;
  agent_model: string;
  prompt: string;
  status: string;
  error_message?: string | null;
  task_count: number;
  agent_count: number;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  full_name?: string | null;
  job_title?: string | null;
  company_name?: string | null;
  timezone?: string | null;
  bio?: string | null;
  created_at: string;
}

export interface SessionAuditEvent {
  id: string;
  action: string;
  actor: string;
  details?: Record<string, unknown> | null;
  created_at: string;
}

export interface PreflightCheck {
  category: string;
  label: string;
  status: "passed" | "failed" | "skipped";
  command: string | null;
  summary: string;
  output: string | null;
}

export interface MergeRequestResponse {
  merge_request_id: string;
  status: string;
  ready_to_merge: boolean;
  lint_passed: boolean;
  tests_passed: boolean;
  provider_pr_number?: number | null;
  provider_pr_url?: string | null;
  error_message?: string | null;
  checks: PreflightCheck[];
}

export interface AuthResponse {
  access_token?: string | null;
  refresh_token?: string | null;
  token_type: string;
  user: User;
}

export interface PasswordResetRequestResponse {
  accepted: boolean;
  reset_token?: string | null;
}

export interface ProviderConnection {
  id: string;
  provider: string;
  auth_mode: string;
  account_login: string;
  installation_id?: number | null;
}

export interface GitHubRepoSuggestion {
  owner: string;
  name: string;
  full_name: string;
  default_branch: string;
  html_url: string;
  private: boolean;
}
