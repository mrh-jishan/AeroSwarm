/**
 * AgentCard — a single agent panel showing:
 *   - Task title + status badge
 *   - Live terminal (xterm.js via WebSocket)
 *   - Preview URL link
 *   - Merge / Reject buttons
 */

"use client";

import { useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import type { AgentSummary } from "@/lib/types";

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
            <button className="px-2 py-1 bg-green-700 hover:bg-green-600 rounded text-white text-xs">
              Merge
            </button>
            <button className="px-2 py-1 bg-red-900 hover:bg-red-800 rounded text-white text-xs">
              Reject
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
