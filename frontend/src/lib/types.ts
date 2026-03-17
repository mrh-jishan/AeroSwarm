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
}
