/**
 * AgentCard — a single agent panel showing:
 *   - Task title + status badge
 *   - Live terminal (xterm.js via WebSocket)
 *   - Preview URL link
 *   - Merge / Reject buttons
 */

"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import type { AgentSummary } from "@/lib/types";
import {
  approveMergeRequest,
  createMergeRequest,
  fetchMergeRequest,
  rejectMergeRequest,
} from "@/lib/api";

// Dynamically import Terminal to avoid SSR issues
const AgentTerminal = dynamic(() => import("./AgentTerminal"), { ssr: false });

const STATUS_COLORS: Record<string, string> = {
  initializing: "bg-yellow-500",
  running:      "bg-green-500",
  idle:         "bg-blue-400",
  stopped:      "bg-gray-500",
  error:        "bg-red-500",
};

interface AgentCardProps {
  agent: AgentSummary;
}

export function AgentCard({ agent }: AgentCardProps) {
  const dotColor = STATUS_COLORS[agent.status] ?? "bg-gray-400";
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<"merge" | "reject" | null>(null);

  async function waitForMergeRequest(mrId: string) {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      const mr = await fetchMergeRequest(mrId);
      if (!["queued", "running"].includes(mr.status)) {
        return mr;
      }
      await new Promise((resolve) => window.setTimeout(resolve, 2000));
    }
    throw new Error("Timed out waiting for merge preflight to finish.");
  }

  async function handleMerge() {
    setActionLoading("merge");
    setActionError(null);

    try {
      const createdMr = await createMergeRequest(agent.taskId);
      const mr = ["queued", "running"].includes(createdMr.status)
        ? await waitForMergeRequest(createdMr.merge_request_id)
        : createdMr;
      if (!mr.ready_to_merge) {
        const failedChecks = mr.checks.filter((check) => check.status === "failed");
        const details = failedChecks.length > 0
          ? failedChecks.map((check) => {
              const output = check.output ? `\n${check.output}` : "";
              return `${check.label}: ${check.summary}${output}`;
            }).join("\n\n")
          : mr.error_message || "Preflight checks did not pass.";
        throw new Error(details);
      }
      await approveMergeRequest(mr.merge_request_id, "dashboard-user");
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleReject() {
    setActionLoading("reject");
    setActionError(null);

    try {
      const mr = await createMergeRequest(agent.taskId);
      await rejectMergeRequest(mr.merge_request_id, "dashboard-user");
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setActionLoading(null);
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden flex flex-col shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <div>
          <h3 className="font-semibold text-sm truncate max-w-[180px]" title={agent.taskTitle}>
            {agent.taskTitle}
          </h3>
          <p className="text-xs text-gray-500 truncate">{agent.scopeDir}</p>
        </div>
        <span className={`inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded-full ${dotColor} bg-opacity-20 text-white`}>
          <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
          {agent.status}
        </span>
      </div>

      {/* Terminal */}
      <div className="flex-1 min-h-[200px] bg-black">
        <AgentTerminal agentId={agent.id} />
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-4 py-2 border-t border-gray-800 text-xs">
        {agent.previewUrl ? (
          <a
            href={agent.previewUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:text-blue-300 underline"
          >
            Live Preview ↗
          </a>
        ) : (
          <span className="text-gray-600">No preview yet</span>
        )}

        {agent.status === "idle" && (
          <div className="flex gap-2">
            <button
              onClick={handleMerge}
              disabled={actionLoading !== null}
              className="px-2 py-1 bg-green-700 hover:bg-green-600 disabled:bg-green-900 rounded text-white text-xs"
            >
              {actionLoading === "merge" ? "Merging..." : "Merge"}
            </button>
            <button
              onClick={handleReject}
              disabled={actionLoading !== null}
              className="px-2 py-1 bg-red-900 hover:bg-red-800 disabled:bg-red-950 rounded text-white text-xs"
            >
              {actionLoading === "reject" ? "Rejecting..." : "Reject"}
            </button>
          </div>
        )}
      </div>
      {actionError && (
        <div className="px-4 py-2 border-t border-red-950 bg-red-950/40 text-red-300 text-xs">
          {actionError}
        </div>
      )}
    </div>
  );
}
