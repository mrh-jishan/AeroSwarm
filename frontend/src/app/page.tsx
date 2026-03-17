/**
 * AeroSwarm Grid Dashboard — main page
 * Displays agent cards in a responsive grid layout.
 */

import { AgentGrid } from "@/components/AgentGrid";
import { NewSessionForm } from "@/components/NewSessionForm";

export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-gray-950 text-gray-100 p-6">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Aero<span className="text-blue-400">Swarm</span>
          </h1>
          <p className="text-gray-400 text-sm mt-1">Parallel Software Factory</p>
        </div>
      </header>

      <section className="mb-8">
        <NewSessionForm />
      </section>

      <section>
        <AgentGrid />
      </section>
    </main>
  );
}
