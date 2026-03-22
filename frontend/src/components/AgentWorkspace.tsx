"use client";

import Link from "next/link";
import useSWR from "swr";
import { fetchAgent } from "@/lib/api";
import type { AgentDetail } from "@/lib/types";
import dynamic from "next/dynamic";

const AgentTerminal = dynamic(() => import("./AgentTerminal"), { ssr: false });

const ACTIVE_AGENT_STATUSES = new Set(["initializing", "running"]);
const STATUS_COLORS: Record<string, string> = {
  initializing: "bg-yellow-500",
  running: "bg-green-500",
  idle: "bg-blue-400",
  stopped: "bg-gray-500",
  error: "bg-red-500",
};

interface AgentWorkspaceProps {
  agentId: string;
}

export function AgentWorkspace({ agentId }: AgentWorkspaceProps) {
  const { data, error, isLoading } = useSWR<AgentDetail>(
    `agent:${agentId}`,
    () => fetchAgent(agentId),
    {
      refreshInterval: (agent) => (
        agent && !ACTIVE_AGENT_STATUSES.has(agent.status) ? 0 : 3000
      ),
    },
  );

  if (isLoading) {
    return <div className="text-sm text-gray-400">Loading worker details...</div>;
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-red-900 bg-red-950/40 p-6 text-sm text-red-300">
        Failed to load worker: {error instanceof Error ? error.message : "Unknown error"}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-2xl border border-dashed border-gray-700 p-8 text-sm text-gray-500">
        Worker not found.
      </div>
    );
  }

  const dotColor = STATUS_COLORS[data.status] ?? "bg-gray-400";

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-gray-800 bg-gray-900/80 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.25em] text-blue-300">Worker</p>
            <h2 className="mt-3 text-2xl font-semibold text-white">{data.task_title}</h2>
            <p className="mt-2 text-sm text-gray-400">{data.scope_dir}</p>
          </div>
          <div className="flex items-center gap-4">
            <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs text-white ${dotColor} bg-opacity-20`}>
              <span className={`h-2 w-2 rounded-full ${dotColor}`} />
              {data.status}
            </span>
            <Link
              href={`/history/${data.session_id}`}
              className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-200 hover:border-gray-500"
            >
              Back To Session
            </Link>
          </div>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-gray-800 bg-gray-950/70 p-4">
            <p className="text-xs uppercase tracking-wide text-gray-500">Agent ID</p>
            <p className="mt-2 break-all text-sm text-gray-200">{data.id}</p>
          </div>
          <div className="rounded-xl border border-gray-800 bg-gray-950/70 p-4">
            <p className="text-xs uppercase tracking-wide text-gray-500">Task ID</p>
            <p className="mt-2 break-all text-sm text-gray-200">{data.task_id}</p>
          </div>
          <div className="rounded-xl border border-gray-800 bg-gray-950/70 p-4">
            <p className="text-xs uppercase tracking-wide text-gray-500">Port</p>
            <p className="mt-2 text-sm text-gray-200">{data.port ?? "Not exposed"}</p>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-gray-800 bg-gray-900/80 p-5">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-white">Live Terminal</h3>
          <p className="mt-1 text-sm text-gray-400">
            This worker streams logs over the authenticated websocket channel. There is no separate HTTP preview unless a task explicitly starts one.
          </p>
        </div>
        <div className="min-h-[420px] overflow-hidden rounded-xl border border-gray-800 bg-black">
          <AgentTerminal agentId={data.id} />
        </div>
      </section>
    </div>
  );
}
