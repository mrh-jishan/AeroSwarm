/**
 * AgentGrid — displays all active agents in a CSS grid.
 * Each card shows: task title, status badge, terminal panel, preview link.
 */

"use client";

import { AgentCard } from "./AgentCard";
import { useAgents } from "@/lib/hooks/useAgents";
import { useSession } from "@/lib/hooks/useSession";

interface AgentGridProps {
  sessionId?: string;
}

export function AgentGrid({ sessionId }: AgentGridProps) {
  const { session } = useSession(sessionId);
  const { agents, isLoading, error } = useAgents(sessionId, session?.status);

  if (!sessionId) {
    return (
      <div className="border border-dashed border-gray-700 rounded-xl p-12 text-center text-gray-500">
        Launch a session to see active agents.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="text-gray-400 text-sm animate-pulse">
        Loading agents...
      </div>
    );
  }

  if (error) {
    return (
      <div className="border border-red-900 bg-red-950/40 text-red-300 rounded-xl p-6 text-sm">
        Failed to load agents: {error instanceof Error ? error.message : "Unknown error"}
      </div>
    );
  }

  if (!agents || agents.length === 0) {
    if (session?.status === "queued" || session?.status === "planning") {
      return (
        <div className="border border-dashed border-blue-800 bg-blue-950/30 rounded-xl p-12 text-center text-blue-200">
          Session is {session.status}. AeroSwarm is preparing the repo and launching agents.
        </div>
      );
    }

    if (session?.status === "failed") {
      return (
        <div className="border border-red-900 bg-red-950/40 text-red-300 rounded-xl p-6 text-sm">
          Session failed: {session.error_message || "Unknown error"}
        </div>
      );
    }

    return (
      <div className="border border-dashed border-gray-700 rounded-xl p-12 text-center text-gray-500">
        No active agents. Start a session above to spawn agents.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      {agents.map((agent) => (
        <AgentCard key={agent.id} agent={agent} />
      ))}
    </div>
  );
}
