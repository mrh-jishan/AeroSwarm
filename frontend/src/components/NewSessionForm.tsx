/**
 * NewSessionForm — minimal launch surface backed by saved launch settings.
 */

"use client";

import Link from "next/link";
import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { createSession, listGitHubRepositories, listProviderConnections } from "@/lib/api";
import { loadLaunchSettings } from "@/lib/launchSettings";
import type { GitHubRepoSuggestion, ProviderConnection } from "@/lib/types";

interface NewSessionFormProps {
  onSessionCreated?: (sessionId: string) => void;
}

function describeConnection(connection: ProviderConnection) {
  if (connection.auth_mode === "github_app") {
    return `${connection.account_login} · GitHub App #${connection.installation_id ?? "?"}`;
  }
  return `${connection.account_login} · ${connection.auth_mode}`;
}

function getConnectionLabel(
  connections: ProviderConnection[],
  selectedConnectionId: string,
) {
  const selectedConnection = connections.find((connection) => connection.id === selectedConnectionId);
  return selectedConnection ? describeConnection(selectedConnection) : "No default GitHub connection selected";
}

function getRepoInputValue(repo: GitHubRepoSuggestion) {
  return repo.html_url;
}

export function NewSessionForm({ onSessionCreated }: NewSessionFormProps) {
  const [repoUrl, setRepoUrl] = useState("");
  const [prompt, setPrompt] = useState("");
  const [providerConnections, setProviderConnections] = useState<ProviderConnection[]>([]);
  const [selectedConnectionId, setSelectedConnectionId] = useState("");
  const [llmProvider, setLlmProvider] = useState<"openai" | "gemini">("gemini");
  const [managerModel, setManagerModel] = useState("gemini-2.5-flash");
  const [agentModel, setAgentModel] = useState("gemini-2.5-flash");
  const [loading, setLoading] = useState(false);
  const [repoSuggestions, setRepoSuggestions] = useState<GitHubRepoSuggestion[]>([]);
  const [repoSuggestionsLoading, setRepoSuggestionsLoading] = useState(false);
  const [repoPickerOpen, setRepoPickerOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const closeTimerRef = useRef<number | null>(null);
  const deferredRepoUrl = useDeferredValue(repoUrl.trim());
  const repoQueryReady = deferredRepoUrl.length >= 2;

  useEffect(() => {
    const saved = loadLaunchSettings();
    setSelectedConnectionId(saved.providerConnectionId);
    setLlmProvider(saved.llmProvider);
    setManagerModel(saved.managerModel);
    setAgentModel(saved.agentModel);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadConnections() {
      try {
        const connections = await listProviderConnections();
        if (!cancelled) {
          setProviderConnections(connections);
        }
      } catch {
        if (!cancelled) {
          setProviderConnections([]);
        }
      }
    }

    void loadConnections();
    return () => {
      cancelled = true;
    };
  }, []);

  const resolvedConnectionId = useMemo(() => {
    if (providerConnections.some((connection) => connection.id === selectedConnectionId)) {
      return selectedConnectionId;
    }
    return providerConnections.length === 1 ? providerConnections[0].id : "";
  }, [providerConnections, selectedConnectionId]);

  const selectedConnection = useMemo(
    () => providerConnections.find((connection) => connection.id === resolvedConnectionId) ?? null,
    [providerConnections, resolvedConnectionId],
  );

  useEffect(() => {
    if (!selectedConnection || selectedConnection.provider !== "github") {
      setRepoSuggestions([]);
      setRepoSuggestionsLoading(false);
      return;
    }

    if (!repoQueryReady) {
      setRepoSuggestions([]);
      setRepoSuggestionsLoading(false);
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setRepoSuggestionsLoading(true);
      try {
        const suggestions = await listGitHubRepositories(selectedConnection.id, deferredRepoUrl, 8);
        if (!cancelled) {
          setRepoSuggestions(suggestions);
          setRepoPickerOpen(true);
        }
      } catch {
        if (!cancelled) {
          setRepoSuggestions([]);
        }
      } finally {
        if (!cancelled) {
          setRepoSuggestionsLoading(false);
        }
      }
    }, 180);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [deferredRepoUrl, repoQueryReady, selectedConnection]);

  useEffect(() => {
    return () => {
      if (closeTimerRef.current) {
        window.clearTimeout(closeTimerRef.current);
      }
    };
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const session = await createSession({
        repoUrl: repoUrl.trim(),
        prompt: prompt.trim(),
        llmProvider,
        managerModel,
        agentModel,
        providerConnectionId: resolvedConnectionId || undefined,
      });
      const repoSummary =
        session.repo_owner && session.repo_name
          ? ` • ${session.repo_owner}/${session.repo_name}@${session.base_branch ?? "unknown"}`
          : "";
      setResult(
        `Session queued: ${session.id} — status ${session.status}${repoSummary} • ${session.llm_provider}:${session.agent_model}`,
      );
      onSessionCreated?.(session.id);
      setRepoUrl("");
      setPrompt("");
      setRepoPickerOpen(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  const showSuggestions =
    repoPickerOpen &&
    selectedConnection?.provider === "github" &&
    repoQueryReady &&
    (repoSuggestionsLoading || repoSuggestions.length > 0 || deferredRepoUrl.length > 0);

  return (
    <div className="space-y-6">
      <section className="rounded-[28px] border border-gray-800 bg-gradient-to-br from-gray-900 via-gray-900 to-gray-950 p-7 shadow-2xl shadow-black/20">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-blue-300">New Session</p>
            <h2 className="mt-3 text-3xl font-semibold text-white">Launch a new session</h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-gray-400">
              Keep this page focused on the repo and the prompt. GitHub connection management and model choices live in settings.
            </p>
          </div>
          <Link
            href="/settings"
            className="rounded-full border border-gray-700 bg-gray-950/70 px-4 py-2 text-sm text-gray-200 transition hover:border-gray-500 hover:text-white"
          >
            Open Settings
          </Link>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_360px]">
        <form onSubmit={handleSubmit} className="rounded-[28px] border border-gray-800 bg-gray-900/85 p-6">
          <div className="space-y-6">
            <div>
              <label className="block text-xs uppercase tracking-wide text-gray-500">Repository</label>
              <div className="relative mt-3">
                <input
                  type="text"
                  value={repoUrl}
                  onChange={(e) => {
                    setRepoUrl(e.target.value);
                    setRepoPickerOpen(true);
                  }}
                  onFocus={() => setRepoPickerOpen(true)}
                  onBlur={() => {
                    closeTimerRef.current = window.setTimeout(() => setRepoPickerOpen(false), 120);
                  }}
                  placeholder="Type at least 2 characters: org/repo or https://github.com/org/repo"
                  required
                  className="w-full rounded-2xl border border-gray-700 bg-gray-950 px-4 py-4 text-sm text-white outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20"
                />

                {showSuggestions && (
                  <div className="absolute left-0 right-0 top-[calc(100%+0.6rem)] z-20 max-h-[320px] overflow-y-auto rounded-2xl border border-gray-800 bg-gray-950/95 p-2 shadow-2xl shadow-black/40 backdrop-blur">
                    {repoSuggestionsLoading ? (
                      <div className="px-3 py-4 text-sm text-gray-400">Loading repository matches...</div>
                    ) : repoSuggestions.length > 0 ? (
                      <div className="space-y-1">
                        {repoSuggestions.map((repo) => (
                          <button
                            key={repo.html_url}
                            type="button"
                            onMouseDown={(event) => event.preventDefault()}
                            onClick={() => {
                              setRepoUrl(getRepoInputValue(repo));
                              setRepoPickerOpen(false);
                            }}
                            className="flex w-full items-start justify-between gap-3 rounded-xl px-3 py-3 text-left transition hover:bg-white/5"
                          >
                            <div>
                              <p className="text-sm font-medium text-white">{repo.full_name}</p>
                              <p className="mt-1 text-xs text-gray-400">{repo.html_url}</p>
                            </div>
                            <div className="text-right">
                              <p className="text-[11px] uppercase tracking-wide text-gray-500">
                                {repo.private ? "Private" : "Public"}
                              </p>
                              <p className="mt-1 text-xs text-gray-400">{repo.default_branch}</p>
                            </div>
                          </button>
                        ))}
                      </div>
                    ) : (
                      <div className="px-3 py-4 text-sm text-gray-500">
                        {selectedConnection
                          ? "No matching repositories found for that input."
                          : "Pick a default GitHub connection in settings to enable autocomplete."}
                      </div>
                    )}
                  </div>
                )}
              </div>
              <p className="mt-3 text-sm text-gray-500">
                {selectedConnection
                  ? repoQueryReady
                    ? "Autocomplete suggestions come from your saved GitHub connection."
                    : "Start typing at least 2 characters to search your GitHub repositories."
                  : "Autocomplete is disabled until a default GitHub connection is selected in settings."}
              </p>
            </div>

            <div>
              <label className="block text-xs uppercase tracking-wide text-gray-500">Build prompt</label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder={"Add a Q/A page\n\nUse the existing design system.\nInclude an FAQ route and accordion layout."}
                required
                rows={8}
                className="mt-3 min-h-[220px] w-full resize-y rounded-2xl border border-gray-700 bg-gray-950 px-4 py-4 text-sm leading-7 text-white outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20"
              />
              <p className="mt-3 text-sm text-gray-500">
                Multi-line prompts are supported. Be specific about scope, style, and constraints.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <button
                type="submit"
                disabled={loading}
                className="rounded-2xl bg-white px-5 py-3 text-sm font-medium text-gray-950 transition hover:bg-gray-200 disabled:cursor-not-allowed disabled:bg-gray-800 disabled:text-gray-500"
              >
                {loading ? "Queueing session..." : "Launch Session"}
              </button>
              {error && <p className="text-sm text-red-400">{error}</p>}
              {result && <p className="text-sm text-emerald-400">{result}</p>}
            </div>
          </div>
        </form>

        <aside className="rounded-[28px] border border-gray-800 bg-gray-900/85 p-6">
          <p className="text-xs uppercase tracking-[0.25em] text-gray-500">Launch profile</p>
          <div className="mt-5 space-y-4">
            <div className="rounded-2xl border border-gray-800 bg-gray-950/80 p-4">
              <p className="text-xs uppercase tracking-wide text-gray-500">GitHub</p>
              <p className="mt-2 text-sm font-medium text-white">
                {getConnectionLabel(providerConnections, resolvedConnectionId)}
              </p>
              <p className="mt-2 text-sm text-gray-400">
                Repo discovery and authenticated cloning use this default connection.
              </p>
            </div>

            <div className="rounded-2xl border border-gray-800 bg-gray-950/80 p-4">
              <p className="text-xs uppercase tracking-wide text-gray-500">Models</p>
              <p className="mt-2 text-sm font-medium text-white">
                {llmProvider}:{managerModel}
              </p>
              <p className="mt-1 text-sm text-gray-400">Agent model: {agentModel}</p>
            </div>

            <div className="rounded-2xl border border-dashed border-gray-700 p-4 text-sm leading-7 text-gray-400">
              Need to change GitHub auth or AI defaults? Update them in <Link href="/settings" className="text-white underline decoration-gray-600 underline-offset-4">settings</Link> and come back here.
            </div>
          </div>
        </aside>
      </section>
    </div>
  );
}
