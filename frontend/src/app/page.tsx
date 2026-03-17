/**
 * AeroSwarm Grid Dashboard — main page
 * Displays agent cards in a responsive grid layout.
 */

"use client";

import { useEffect, useState } from "react";
import { AgentGrid } from "@/components/AgentGrid";
import { AuthPanel } from "@/components/AuthPanel";
import { NewSessionForm } from "@/components/NewSessionForm";
import { fetchMe, logout } from "@/lib/api";
import type { User } from "@/lib/types";

export default function DashboardPage() {
  const [sessionId, setSessionId] = useState<string>();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [authResolved, setAuthResolved] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadUser() {
      try {
        const user = await fetchMe();
        if (!cancelled) {
          setCurrentUser(user);
        }
      } catch {
        if (!cancelled) {
          setCurrentUser(null);
        }
      } finally {
        if (!cancelled) {
          setAuthResolved(true);
        }
      }
    }

    void loadUser();

    return () => {
      cancelled = true;
    };
  }, []);

  if (!authResolved) {
    return <main className="min-h-screen bg-gray-950 text-gray-100 p-6">Loading...</main>;
  }

  if (!currentUser) {
    return (
      <main className="min-h-screen bg-gray-950 text-gray-100 p-6 flex items-center justify-center">
        <AuthPanel onAuthenticated={setCurrentUser} />
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-950 text-gray-100 p-6">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Aero<span className="text-blue-400">Swarm</span>
          </h1>
          <p className="text-gray-400 text-sm mt-1">Parallel Software Factory</p>
        </div>
        <button
          onClick={async () => {
            await logout();
            setCurrentUser(null);
            setSessionId(undefined);
          }}
          className="px-4 py-2 text-sm bg-gray-800 hover:bg-gray-700 rounded-lg"
        >
          Sign Out
        </button>
      </header>

      <section className="mb-8">
        <NewSessionForm onSessionCreated={setSessionId} currentUserEmail={currentUser.email} />
      </section>

      <section>
        <AgentGrid sessionId={sessionId} />
      </section>
    </main>
  );
}
