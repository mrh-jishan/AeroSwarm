/**
 * DashboardApp — authenticated AeroSwarm workspace.
 */

"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AgentGrid } from "@/components/AgentGrid";
import { AuthPanel } from "@/components/AuthPanel";
import { NewSessionForm } from "@/components/NewSessionForm";
import { fetchMe, logout } from "@/lib/api";
import type { User } from "@/lib/types";

export function DashboardApp() {
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
      <header className="mb-8 flex items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">
              Aero<span className="text-blue-400">Swarm</span>
            </h1>
            <Link
              href="/"
              className="rounded-full border border-gray-700 px-3 py-1 text-xs text-gray-300 hover:border-gray-500 hover:text-white"
            >
              Public Site
            </Link>
          </div>
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
