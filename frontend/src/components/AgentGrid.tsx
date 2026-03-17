/**
 * AgentGrid — displays all active agents in a CSS grid.
 * Each card shows: task title, status badge, terminal panel, preview link.
 */

"use client";

import { AgentCard } from "./AgentCard";
import { useAgents } from "@/lib/hooks/useAgents";

export function AgentGrid() {
  const { agents, isLoading } = useAgents();

  if (isLoading) {
    return (
      <div className="text-gray-400 text-sm animate-pulse">
        Loading agents...
      </div>
    );
  }

  if (!agents || agents.length === 0) {
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
