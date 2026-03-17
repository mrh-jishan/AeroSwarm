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

export interface SessionResponse {
  id: string;
  repo_url: string;
  vcs_provider?: string | null;
  repo_owner?: string | null;
  repo_name?: string | null;
  base_branch?: string | null;
  prompt: string;
  status: string;
  task_count: number;
  agent_count: number;
}

export interface User {
  id: string;
  email: string;
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
