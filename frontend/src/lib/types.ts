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
