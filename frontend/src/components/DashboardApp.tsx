/**
 * DashboardApp — authenticated AeroSwarm workspace.
 */

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import useSWR, { useSWRConfig } from "swr";
import { AgentGrid } from "@/components/AgentGrid";
import { AgentWorkspace } from "@/components/AgentWorkspace";
import { NewSessionForm } from "@/components/NewSessionForm";
import { ProfileSettingsPanel } from "@/components/ProfileSettingsPanel";
import { SessionSettingsPanel } from "@/components/SessionSettingsPanel";
import { fetchMe, fetchSessionAudit, listSessions, logout, retrySession, stopSession } from "@/lib/api";
import { useSession } from "@/lib/hooks/useSession";
import { useWebSocketToken } from "@/lib/hooks/useWebSocketToken";
import type { AgentSummary, SessionAuditEvent, SessionResponse, User } from "@/lib/types";

type DashboardRouteView = "dashboard" | "new" | "history" | "session" | "settings" | "profile" | "agent";

const SESSION_STORAGE_KEY = "aeroswarm.dashboard.session";
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
const ACTIVE_SESSION_STATUSES = new Set(["queued", "planning", "running", "merging"]);
const FAILED_SESSION_STATUSES = new Set(["failed", "error"]);
const COMPLETED_SESSION_STATUSES = new Set(["done", "merged", "completed", "stopped"]);

interface SessionDetailStreamPayload {
  session: SessionResponse;
  agents: AgentSummary[];
  audit_events: SessionAuditEvent[];
}

interface DashboardAppProps {
  routeView: DashboardRouteView;
  sessionId?: string;
  agentId?: string;
}

function formatSessionLabel(session: SessionResponse) {
  if (session.repo_owner && session.repo_name) {
    return `${session.repo_owner}/${session.repo_name}`;
  }

  return session.repo_url;
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "Unknown time";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function formatAuditDetails(details?: Record<string, unknown> | null) {
  if (!details || Object.keys(details).length === 0) {
    return null;
  }

  return Object.entries(details)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(" • ");
}

function truncateText(value: string, maxLength: number) {
  if (value.length <= maxLength) {
    return value;
  }

  return `${value.slice(0, maxLength - 1)}…`;
}

function buildWebSocketUrl(path: string, token: string) {
  const url = new URL(`${WS_BASE}${path}`);
  url.searchParams.set("token", token);
  return url.toString();
}

function DashboardNavButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-4 py-2 text-sm transition-colors ${
        active
          ? "bg-blue-600 text-white"
          : "border border-gray-700 text-gray-300 hover:border-gray-500 hover:text-white"
      }`}
    >
      {label}
    </button>
  );
}

function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: number;
  hint: string;
}) {
  return (
    <div className="rounded-2xl border border-gray-800 bg-gray-900/80 p-5">
      <p className="text-xs uppercase tracking-wide text-gray-500">{label}</p>
      <p className="mt-3 text-3xl font-semibold text-white">{value}</p>
      <p className="mt-2 text-sm text-gray-400">{hint}</p>
    </div>
  );
}

function SidebarSessionItem({
  session,
  selected,
  onOpen,
}: {
  session: SessionResponse;
  selected: boolean;
  onOpen: () => void;
}) {
  return (
    <div
      className={`rounded-lg border px-3 py-2 transition-colors ${
        selected ? "border-blue-500 bg-blue-950/30" : "border-gray-800 bg-gray-950/70"
      }`}
    >
      <button type="button" onClick={onOpen} className="w-full text-left">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-sm font-medium text-white">{truncateText(formatSessionLabel(session), 30)}</p>
            <p className="mt-1 text-[11px] text-gray-400">{formatDateTime(session.created_at)}</p>
          </div>
          <span className="rounded-full border border-gray-700 px-2 py-0.5 text-[10px] uppercase tracking-wide text-gray-300">
            {session.status}
          </span>
        </div>
        <p className="mt-2 text-xs leading-5 text-gray-400">{truncateText(session.prompt, 72)}</p>
      </button>
    </div>
  );
}

function HistorySessionCard({
  session,
  retrying,
  stopping,
  onOpen,
  onRetry,
  onStop,
}: {
  session: SessionResponse;
  retrying: boolean;
  stopping: boolean;
  onOpen: () => void;
  onRetry: () => void;
  onStop: () => void;
}) {
  const canStop = ACTIVE_SESSION_STATUSES.has(session.status);

  return (
    <div className="rounded-2xl border border-gray-800 bg-gray-900/80 p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-white">{formatSessionLabel(session)}</h3>
          <p className="mt-1 text-sm text-gray-400">{session.repo_url}</p>
        </div>
        <div className="text-right">
          <p className="rounded-full border border-gray-700 px-3 py-1 text-xs uppercase tracking-wide text-gray-300">
            {session.status}
          </p>
          <p className="mt-2 text-xs text-gray-500">{formatDateTime(session.created_at)}</p>
        </div>
      </div>

      <p className="mt-4 text-sm leading-7 text-gray-300">{session.prompt}</p>

      <div className="mt-4 flex flex-wrap gap-4 text-xs text-gray-500">
        <span>{session.llm_provider}:{session.agent_model}</span>
        <span>{session.task_count} tasks</span>
        <span>{session.agent_count} agents</span>
        <span>Branch: {session.base_branch ?? "Unknown"}</span>
      </div>

      {session.error_message && (
        <div className="mt-4 rounded-xl border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">
          {session.error_message}
        </div>
      )}

      <div className="mt-5 flex gap-3">
        {canStop && (
          <button
            type="button"
            onClick={onStop}
            disabled={stopping}
            className="rounded-lg border border-red-700 px-4 py-2 text-sm text-red-200 hover:border-red-500 disabled:border-red-900 disabled:text-red-500"
          >
            {stopping ? "Stopping..." : "Stop Session"}
          </button>
        )}
        <button
          type="button"
          onClick={onOpen}
          className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-200 hover:border-gray-500"
        >
          Open Details
        </button>
        {!canStop && (
          <button
            type="button"
            onClick={onRetry}
            disabled={retrying}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:bg-blue-900"
          >
            {retrying ? "Retrying..." : "Retry Session"}
          </button>
        )}
      </div>
    </div>
  );
}

export function DashboardApp({
  routeView,
  sessionId,
  agentId,
}: DashboardAppProps) {
  const router = useRouter();
  const { mutate } = useSWRConfig();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [authResolved, setAuthResolved] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<string | undefined>(sessionId);
  const [retryingSessionId, setRetryingSessionId] = useState<string | null>(null);
  const [stoppingSessionId, setStoppingSessionId] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const { token: websocketToken, refreshToken: refreshWebSocketToken } = useWebSocketToken(Boolean(currentUser));

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

  useEffect(() => {
    if (!authResolved || currentUser) {
      return;
    }
    router.replace("/login");
  }, [authResolved, currentUser, router]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    if (routeView === "session" && sessionId) {
      setSelectedSessionId(sessionId);
      window.localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
      return;
    }

    const storedSessionId = window.localStorage.getItem(SESSION_STORAGE_KEY) || undefined;
    setSelectedSessionId(storedSessionId);
  }, [routeView, sessionId]);

  const {
    data: sessions = [],
    isLoading: sessionsLoading,
    mutate: mutateSessions,
  } = useSWR<SessionResponse[]>(
    currentUser ? "sessions-history" : null,
    listSessions,
  );

  useEffect(() => {
    if (sessions.length === 0 || selectedSessionId) {
      return;
    }

    const fallbackId = sessions[0].id;
    setSelectedSessionId(fallbackId);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(SESSION_STORAGE_KEY, fallbackId);
    }
  }, [selectedSessionId, sessions]);

  const shouldLoadSession = routeView === "session" && Boolean(selectedSessionId);
  const { session: activeSession, error: sessionError, isLoading: sessionLoading } = useSession(
    shouldLoadSession ? selectedSessionId : undefined
  );
  const { data: auditEvents = [], isLoading: auditLoading } = useSWR<SessionAuditEvent[]>(
    shouldLoadSession ? `session-audit:${selectedSessionId}` : null,
    () => fetchSessionAudit(selectedSessionId!),
  );

  const displayedSession = activeSession ?? sessions.find((session) => session.id === selectedSessionId);

  const stats = useMemo(() => {
    return {
      totalSessions: sessions.length,
      activeSessions: sessions.filter((session) => ACTIVE_SESSION_STATUSES.has(session.status)).length,
      failedSessions: sessions.filter((session) => FAILED_SESSION_STATUSES.has(session.status)).length,
      completedSessions: sessions.filter((session) => COMPLETED_SESSION_STATUSES.has(session.status)).length,
      totalTasks: sessions.reduce((sum, session) => sum + session.task_count, 0),
      totalAgents: sessions.reduce((sum, session) => sum + session.agent_count, 0),
    };
  }, [sessions]);

  function persistSelectedSession(nextSessionId?: string) {
    setSelectedSessionId(nextSessionId);
    if (typeof window !== "undefined") {
      if (nextSessionId) {
        window.localStorage.setItem(SESSION_STORAGE_KEY, nextSessionId);
      } else {
        window.localStorage.removeItem(SESSION_STORAGE_KEY);
      }
    }
  }

  function openDashboard() {
    setPageError(null);
    router.push("/dashboard");
  }

  function openNewSession() {
    setPageError(null);
    router.push("/dashboard/new");
  }

  function openHistory() {
    setPageError(null);
    router.push("/history");
  }

  function openSettings() {
    setPageError(null);
    router.push("/settings");
  }

  function openProfile() {
    setPageError(null);
    router.push("/profile");
  }

  function openSession(nextSessionId: string) {
    setPageError(null);
    persistSelectedSession(nextSessionId);
    router.push(`/history/${nextSessionId}`);
  }

  async function handleSessionCreated(nextSessionId: string) {
    setPageError(null);
    persistSelectedSession(nextSessionId);
    await mutateSessions();
    router.push(`/history/${nextSessionId}`);
  }

  async function handleRetrySession(sourceSessionId: string) {
    setRetryingSessionId(sourceSessionId);
    setPageError(null);

    try {
      const nextSession = await retrySession(sourceSessionId);
      persistSelectedSession(nextSession.id);
      await mutateSessions();
      router.push(`/history/${nextSession.id}`);
    } catch (error: unknown) {
      setPageError(error instanceof Error ? error.message : "Failed to retry session");
    } finally {
      setRetryingSessionId(null);
    }
  }

  async function handleStopSession(targetSessionId: string) {
    setStoppingSessionId(targetSessionId);
    setPageError(null);

    try {
      const stoppedSession = await stopSession(targetSessionId);
      await mutate(`session:${targetSessionId}`, stoppedSession, { revalidate: false });
      await mutate(`session-audit:${targetSessionId}`);
      await mutateSessions();
    } catch (error: unknown) {
      setPageError(error instanceof Error ? error.message : "Failed to stop session");
    } finally {
      setStoppingSessionId(null);
    }
  }

  useEffect(() => {
    if (!currentUser || !websocketToken) {
      return;
    }

    let cancelled = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (cancelled) {
        return;
      }

      socket = new WebSocket(buildWebSocketUrl("/api/sessions/stream", websocketToken));

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as SessionResponse[];
          void mutate("sessions-history", payload, { revalidate: false });
        } catch {
          // Ignore malformed stream messages and keep the current cache.
        }
      };

      socket.onerror = () => {
        socket?.close();
      };

      socket.onclose = () => {
        if (cancelled) {
          return;
        }
        void refreshWebSocketToken();
        reconnectTimer = setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      socket?.close();
    };
  }, [currentUser, mutate, refreshWebSocketToken, websocketToken]);

  useEffect(() => {
    if (!currentUser || !websocketToken || routeView !== "session" || !selectedSessionId) {
      return;
    }

    let cancelled = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (cancelled) {
        return;
      }

      socket = new WebSocket(
        buildWebSocketUrl(`/api/sessions/${selectedSessionId}/stream`, websocketToken),
      );

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as SessionDetailStreamPayload;
          void mutate(`session:${selectedSessionId}`, payload.session, { revalidate: false });
          void mutate(`session-agents:${selectedSessionId}`, payload.agents, { revalidate: false });
          void mutate(`session-audit:${selectedSessionId}`, payload.audit_events, { revalidate: false });
          void mutate(
            "sessions-history",
            (currentSessions: SessionResponse[] = []) =>
              currentSessions.map((session) =>
                session.id === payload.session.id ? payload.session : session
              ),
            { revalidate: false },
          );
        } catch {
          // Ignore malformed stream messages and keep the current cache.
        }
      };

      socket.onerror = () => {
        socket?.close();
      };

      socket.onclose = () => {
        if (cancelled) {
          return;
        }
        void refreshWebSocketToken();
        reconnectTimer = setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      socket?.close();
    };
  }, [currentUser, mutate, refreshWebSocketToken, routeView, selectedSessionId, websocketToken]);

  if (!authResolved) {
    return <main className="min-h-screen bg-gray-950 p-6 text-gray-100">Loading...</main>;
  }

  if (!currentUser) {
    return <main className="min-h-screen bg-gray-950 p-6 text-gray-100">Redirecting to sign in...</main>;
  }

  const onDashboardPage = routeView === "dashboard";
  const onNewSessionPage = routeView === "new";
  const onHistoryPage = routeView === "history" || routeView === "session";
  const onSettingsPage = routeView === "settings";
  const onProfilePage = routeView === "profile";

  return (
    <main className="min-h-screen bg-gray-950 p-6 text-gray-100">
      <header className="mb-8 flex flex-wrap items-center justify-between gap-6 xl:grid xl:grid-cols-[1fr_auto_1fr] xl:items-center">
        <div className="justify-self-start">
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
          <p className="mt-1 text-sm text-gray-400">Parallel Software Factory</p>
        </div>

        <nav className="flex flex-wrap items-center justify-center gap-3 xl:justify-self-center">
          <DashboardNavButton
            label="Dashboard"
            active={onDashboardPage}
            onClick={openDashboard}
          />
          <DashboardNavButton
            label="New Session"
            active={onNewSessionPage}
            onClick={openNewSession}
          />
          <DashboardNavButton
            label="Session History"
            active={onHistoryPage}
            onClick={openHistory}
          />
          <DashboardNavButton
            label="Settings"
            active={onSettingsPage}
            onClick={openSettings}
          />
          <DashboardNavButton
            label="Profile"
            active={onProfilePage}
            onClick={openProfile}
          />
        </nav>

        <div className="flex items-center gap-3 justify-self-end">
          <div className="hidden rounded-full border border-gray-800 bg-gray-900/80 px-4 py-2 text-right sm:block">
            <p className="text-sm font-medium text-white">{currentUser.full_name || currentUser.email}</p>
            <p className="text-xs text-gray-500">{currentUser.email}</p>
          </div>
          <button
            onClick={async () => {
              await logout();
              setCurrentUser(null);
            }}
            className="rounded-lg bg-gray-800 px-4 py-2 text-sm hover:bg-gray-700"
          >
            Sign Out
          </button>
        </div>
      </header>

      {pageError && (
        <section className="mb-6 rounded-xl border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">
          {pageError}
        </section>
      )}

      <section className={onHistoryPage ? "grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]" : ""}>
        {onHistoryPage && (
          <aside className="rounded-2xl border border-gray-800 bg-gray-900/80 p-4">
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-white">Session History</h2>
              <p className="mt-1 text-sm text-gray-400">
                Open prior runs from the left rail and keep the last one selected.
              </p>
            </div>

            {sessionsLoading ? (
              <div className="text-sm text-gray-400">Loading session history...</div>
            ) : sessions.length === 0 ? (
              <div className="rounded-xl border border-dashed border-gray-700 p-6 text-sm text-gray-500">
                No previous sessions yet.
              </div>
            ) : (
              <div className="space-y-3">
                {sessions.map((session) => (
                <SidebarSessionItem
                  key={session.id}
                  session={session}
                  selected={session.id === selectedSessionId}
                  onOpen={() => openSession(session.id)}
                />
              ))}
            </div>
            )}
          </aside>
        )}

        <div className="space-y-6">
          {routeView === "dashboard" && (
            <>
              <section className="rounded-2xl border border-gray-800 bg-gray-900/80 p-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h2 className="text-2xl font-semibold text-white">Dashboard Overview</h2>
                    <p className="mt-2 text-sm text-gray-400">
                      Track current activity, review previous runs, and jump into the next session from one place.
                    </p>
                  </div>
                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={openNewSession}
                      className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
                    >
                      Launch New Session
                    </button>
                    <button
                      type="button"
                      onClick={openSettings}
                      className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-200 hover:border-gray-500"
                    >
                      Open Settings
                    </button>
                    <button
                      type="button"
                      onClick={openHistory}
                      className="rounded-lg border border-gray-700 px-4 py-2 text-sm text-gray-200 hover:border-gray-500"
                    >
                      Open Full History
                    </button>
                  </div>
                </div>
              </section>

              <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <StatCard label="Total Sessions" value={stats.totalSessions} hint="All recorded runs for your account." />
                <StatCard label="Active Sessions" value={stats.activeSessions} hint="Queued, planning, or currently running." />
                <StatCard label="Failed Sessions" value={stats.failedSessions} hint="Runs that ended with an error." />
                <StatCard label="Completed Sessions" value={stats.completedSessions} hint="Finished delivery flows." />
                <StatCard label="Total Tasks" value={stats.totalTasks} hint="Manager-generated work items across sessions." />
                <StatCard label="Total Agents" value={stats.totalAgents} hint="Spawned workers across tracked runs." />
              </section>

              <section className="rounded-2xl border border-gray-800 bg-gray-900/80 p-6">
                  <div className="mb-4">
                    <h3 className="text-lg font-semibold text-white">Current Focus</h3>
                    <p className="mt-1 text-sm text-gray-400">
                      The most recently opened session stays selected and is ready to continue.
                    </p>
                  </div>

                {!displayedSession ? (
                  <div className="rounded-xl border border-dashed border-gray-700 p-6 text-sm text-gray-500">
                    Open a session from session history to pin it here.
                  </div>
                ) : (
                  <HistorySessionCard
                    session={displayedSession}
                    retrying={retryingSessionId === displayedSession.id}
                    stopping={stoppingSessionId === displayedSession.id}
                    onOpen={() => openSession(displayedSession.id)}
                    onRetry={() => void handleRetrySession(displayedSession.id)}
                    onStop={() => void handleStopSession(displayedSession.id)}
                  />
                )}
              </section>
            </>
          )}

          {routeView === "new" && (
            <section className="rounded-2xl border border-gray-800 bg-gray-900/80 p-6">
              <div className="mb-6">
                <h2 className="text-2xl font-semibold text-white">Launch a New Session</h2>
                <p className="mt-2 text-sm text-gray-400">
                  Create a fresh run from a minimal page. GitHub and AI defaults are configured separately in settings.
                </p>
              </div>
              <NewSessionForm onSessionCreated={handleSessionCreated} />
            </section>
          )}

          {routeView === "settings" && (
            <section className="rounded-2xl border border-gray-800 bg-gray-900/80 p-6">
              <SessionSettingsPanel currentUserEmail={currentUser.email} />
            </section>
          )}

          {routeView === "profile" && (
            <ProfileSettingsPanel user={currentUser} onUserUpdated={setCurrentUser} />
          )}

          {routeView === "agent" && agentId && (
            <section className="rounded-2xl border border-gray-800 bg-gray-900/80 p-6">
              <AgentWorkspace agentId={agentId} />
            </section>
          )}

          {routeView === "history" && (
            <section className="space-y-5">
              <div>
                <h2 className="text-2xl font-semibold text-white">Full Session History</h2>
                <p className="mt-2 text-sm text-gray-400">
                  Browse all recorded runs, inspect their details, and relaunch them from a clean history route.
                </p>
              </div>

              {sessionsLoading ? (
                <div className="text-sm text-gray-400">Loading session history...</div>
              ) : sessions.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-gray-700 p-8 text-sm text-gray-500">
                  No session history yet. Create a new run from the dashboard.
                </div>
              ) : (
                <div className="space-y-4">
                  {sessions.map((session) => (
                    <HistorySessionCard
                      key={session.id}
                      session={session}
                      retrying={retryingSessionId === session.id}
                      stopping={stoppingSessionId === session.id}
                      onOpen={() => openSession(session.id)}
                      onRetry={() => void handleRetrySession(session.id)}
                      onStop={() => void handleStopSession(session.id)}
                    />
                  ))}
                </div>
              )}
            </section>
          )}

          {routeView === "session" && (
            <>
              <section className="rounded-2xl border border-gray-800 bg-gray-900/80 p-6">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <h2 className="text-2xl font-semibold text-white">Session Details</h2>
                    <p className="mt-2 text-sm text-gray-400">
                      Opened from real history routes while keeping the history rail on the left.
                    </p>
                  </div>
                  {selectedSessionId && displayedSession && ACTIVE_SESSION_STATUSES.has(displayedSession.status) && (
                    <button
                      type="button"
                      onClick={() => void handleStopSession(selectedSessionId)}
                      disabled={stoppingSessionId === selectedSessionId}
                      className="rounded-lg border border-red-700 px-4 py-2 text-sm font-medium text-red-200 hover:border-red-500 disabled:border-red-900 disabled:text-red-500"
                    >
                      {stoppingSessionId === selectedSessionId ? "Stopping..." : "Stop This Session"}
                    </button>
                  )}
                  {selectedSessionId && displayedSession && !ACTIVE_SESSION_STATUSES.has(displayedSession.status) && (
                    <button
                      type="button"
                      onClick={() => void handleRetrySession(selectedSessionId)}
                      disabled={retryingSessionId === selectedSessionId}
                      className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:bg-blue-900"
                    >
                      {retryingSessionId === selectedSessionId ? "Retrying..." : "Retry This Session"}
                    </button>
                  )}
                </div>
              </section>

              {sessionLoading ? (
                <div className="text-sm text-gray-400">Loading session details...</div>
              ) : sessionError ? (
                <div className="rounded-2xl border border-red-900 bg-red-950/40 p-6 text-sm text-red-300">
                  Failed to load session: {sessionError instanceof Error ? sessionError.message : "Unknown error"}
                </div>
              ) : !displayedSession ? (
                <div className="rounded-2xl border border-dashed border-gray-700 p-8 text-sm text-gray-500">
                  Session not found.
                </div>
              ) : (
                <>
                  <section className="rounded-2xl border border-gray-800 bg-gray-900/80 p-6">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <h3 className="text-xl font-semibold text-white">{formatSessionLabel(displayedSession)}</h3>
                        <p className="mt-1 text-sm text-gray-400">{displayedSession.repo_url}</p>
                      </div>
                      <div className="text-right text-sm text-gray-400">
                        <p>{formatDateTime(displayedSession.created_at)}</p>
                        <p className="mt-2 uppercase tracking-wide text-gray-300">{displayedSession.status}</p>
                      </div>
                    </div>

                    <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                      <div className="rounded-xl border border-gray-800 bg-gray-950/70 p-4">
                        <p className="text-xs uppercase tracking-wide text-gray-500">Models</p>
                        <p className="mt-2 text-sm text-gray-200">
                          {displayedSession.llm_provider}:{displayedSession.manager_model}
                        </p>
                        <p className="mt-1 text-sm text-gray-400">Agent: {displayedSession.agent_model}</p>
                      </div>
                      <div className="rounded-xl border border-gray-800 bg-gray-950/70 p-4">
                        <p className="text-xs uppercase tracking-wide text-gray-500">Branch</p>
                        <p className="mt-2 text-sm text-gray-200">{displayedSession.base_branch ?? "Unknown"}</p>
                      </div>
                      <div className="rounded-xl border border-gray-800 bg-gray-950/70 p-4">
                        <p className="text-xs uppercase tracking-wide text-gray-500">Tasks</p>
                        <p className="mt-2 text-sm text-gray-200">{displayedSession.task_count}</p>
                      </div>
                      <div className="rounded-xl border border-gray-800 bg-gray-950/70 p-4">
                        <p className="text-xs uppercase tracking-wide text-gray-500">Agents</p>
                        <p className="mt-2 text-sm text-gray-200">{displayedSession.agent_count}</p>
                      </div>
                    </div>

                    <div className="mt-5 rounded-xl border border-gray-800 bg-gray-950/70 p-4">
                      <p className="text-xs uppercase tracking-wide text-gray-500">Prompt</p>
                      <p className="mt-2 text-sm leading-7 text-gray-200">{displayedSession.prompt}</p>
                      {displayedSession.error_message && (
                        <div className="mt-4 rounded-lg border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">
                          {displayedSession.error_message}
                        </div>
                      )}
                    </div>
                  </section>

                  <section>
                    <AgentGrid sessionId={selectedSessionId} />
                  </section>

                  <section className="rounded-2xl border border-gray-800 bg-gray-900/80 p-5">
                    <div className="mb-4">
                      <h3 className="text-lg font-semibold text-white">Audit Trail</h3>
                      <p className="mt-1 text-sm text-gray-400">
                        Session lifecycle, repo preparation, and agent launch activity.
                      </p>
                    </div>

                    {auditLoading ? (
                      <div className="text-sm text-gray-400">Loading audit trail...</div>
                    ) : auditEvents.length === 0 ? (
                      <div className="rounded-xl border border-dashed border-gray-700 p-6 text-sm text-gray-500">
                        No audit events recorded for this session yet.
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {auditEvents.map((event) => {
                          const details = formatAuditDetails(event.details);
                          return (
                            <div key={event.id} className="rounded-xl border border-gray-800 bg-gray-950/70 p-4">
                              <div className="flex flex-wrap items-center justify-between gap-3">
                                <p className="text-sm font-medium text-white">{event.action}</p>
                                <p className="text-xs text-gray-500">{formatDateTime(event.created_at)}</p>
                              </div>
                              <p className="mt-2 text-xs uppercase tracking-wide text-gray-500">{event.actor}</p>
                              {details && <p className="mt-3 text-sm text-gray-300">{details}</p>}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </section>
                </>
              )}
            </>
          )}
        </div>
      </section>
    </main>
  );
}
