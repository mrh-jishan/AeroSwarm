"use client";

import { useEffect, useMemo, useState } from "react";
import {
  connectGitHub,
  getGitHubAppInstallStartUrl,
  getGitHubOAuthStartUrl,
  listProviderConnections,
} from "@/lib/api";
import {
  loadLaunchSettings,
  PROVIDER_DEFAULTS,
  saveLaunchSettings,
  type LaunchLlmProvider,
} from "@/lib/launchSettings";
import type { ProviderConnection } from "@/lib/types";

interface SessionSettingsPanelProps {
  currentUserEmail: string;
}

function describeConnection(connection: ProviderConnection) {
  if (connection.auth_mode === "github_app") {
    return `${connection.account_login} · GitHub App #${connection.installation_id ?? "?"}`;
  }

  return `${connection.account_login} · ${connection.auth_mode}`;
}

export function SessionSettingsPanel({
  currentUserEmail,
}: SessionSettingsPanelProps) {
  const [settingsReady, setSettingsReady] = useState(false);
  const [providerConnections, setProviderConnections] = useState<ProviderConnection[]>([]);
  const [selectedConnectionId, setSelectedConnectionId] = useState("");
  const [llmProvider, setLlmProvider] = useState<LaunchLlmProvider>("gemini");
  const [managerModel, setManagerModel] = useState(PROVIDER_DEFAULTS.gemini.managerModel);
  const [agentModel, setAgentModel] = useState(PROVIDER_DEFAULTS.gemini.agentModel);
  const [githubAccessToken, setGitHubAccessToken] = useState("");
  const [loadingConnections, setLoadingConnections] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  useEffect(() => {
    const saved = loadLaunchSettings();
    setSelectedConnectionId(saved.providerConnectionId);
    setLlmProvider(saved.llmProvider);
    setManagerModel(saved.managerModel);
    setAgentModel(saved.agentModel);
    setSettingsReady(true);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadConnections() {
      setLoadingConnections(true);
      try {
        const connections = await listProviderConnections();
        if (cancelled) {
          return;
        }
        setProviderConnections(connections);
      } catch {
        if (!cancelled) {
          setProviderConnections([]);
        }
      } finally {
        if (!cancelled) {
          setLoadingConnections(false);
        }
      }
    }

    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const githubOauthStatus = params.get("github_oauth");
      const githubAppStatus = params.get("github_app");
      const account = params.get("account");
      const installationId = params.get("installation_id");
      const message = params.get("message");

      if (githubOauthStatus === "connected") {
        setResult(account ? `Connected GitHub account: ${account}` : "GitHub OAuth connection added.");
      } else if (githubAppStatus === "connected") {
        setResult(
          account
            ? `Connected GitHub App installation for ${account}${installationId ? ` (#${installationId})` : ""}`
            : "GitHub App installation added.",
        );
      } else if (githubOauthStatus === "error" || githubAppStatus === "error") {
        setError(message || "GitHub connection failed");
      }

      if (githubOauthStatus || githubAppStatus || message || account || installationId) {
        params.delete("github_oauth");
        params.delete("github_app");
        params.delete("account");
        params.delete("installation_id");
        params.delete("message");
        const nextQuery = params.toString();
        const nextUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ""}`;
        window.history.replaceState({}, "", nextUrl);
      }
    }

    void loadConnections();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedConnectionId || providerConnections.some((item) => item.id === selectedConnectionId)) {
      return;
    }

    setSelectedConnectionId("");
  }, [providerConnections, selectedConnectionId]);

  useEffect(() => {
    if (!settingsReady) {
      return;
    }

    saveLaunchSettings({
      providerConnectionId: selectedConnectionId,
      llmProvider,
      managerModel,
      agentModel,
    });
  }, [agentModel, llmProvider, managerModel, selectedConnectionId, settingsReady]);

  const selectedConnection = useMemo(
    () => providerConnections.find((item) => item.id === selectedConnectionId) ?? null,
    [providerConnections, selectedConnectionId],
  );

  function handleProviderChange(nextProvider: LaunchLlmProvider) {
    setLlmProvider(nextProvider);
    setManagerModel(PROVIDER_DEFAULTS[nextProvider].managerModel);
    setAgentModel(PROVIDER_DEFAULTS[nextProvider].agentModel);
  }

  async function handleConnectGitHubToken() {
    setConnecting(true);
    setError(null);
    setResult(null);

    try {
      const connection = await connectGitHub({ accessToken: githubAccessToken });
      const nextConnections = [...providerConnections.filter((item) => item.id !== connection.id), connection];
      setProviderConnections(nextConnections);
      setSelectedConnectionId(connection.id);
      setGitHubAccessToken("");
      setResult(`Connected GitHub account: ${connection.account_login}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setConnecting(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[28px] border border-gray-800 bg-gradient-to-br from-gray-900 via-gray-900 to-gray-950 p-7 shadow-2xl shadow-black/20">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-blue-300">Launch Settings</p>
            <h2 className="mt-3 text-3xl font-semibold text-white">GitHub access and AI defaults</h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-gray-400">
              Configure the connection and model profile used by the minimal new-session page. These defaults are
              saved in this browser and applied to future launches automatically.
            </p>
          </div>
          <div className="rounded-2xl border border-gray-800 bg-gray-950/80 px-4 py-3 text-sm text-gray-300">
            <p className="text-xs uppercase tracking-wide text-gray-500">Signed in as</p>
            <p className="mt-1 font-medium text-white">{currentUserEmail}</p>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_380px]">
        <div className="space-y-6">
          <div className="rounded-[24px] border border-gray-800 bg-gray-900/85 p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h3 className="text-xl font-semibold text-white">GitHub</h3>
                <p className="mt-2 text-sm text-gray-400">
                  Choose which saved connection new sessions should use for repo discovery and cloning.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => {
                    window.location.href = getGitHubOAuthStartUrl("/settings");
                  }}
                  className="rounded-full border border-blue-500/40 bg-blue-500/10 px-4 py-2 text-sm text-blue-100 hover:border-blue-400 hover:bg-blue-500/20"
                >
                  Connect OAuth
                </button>
                <button
                  type="button"
                  onClick={() => {
                    window.location.href = getGitHubAppInstallStartUrl("/settings");
                  }}
                  className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-100 hover:border-emerald-400 hover:bg-emerald-500/20"
                >
                  Install App
                </button>
              </div>
            </div>

            <div className="mt-5 rounded-2xl border border-gray-800 bg-gray-950/70 p-4">
              <label className="block text-xs uppercase tracking-wide text-gray-500">Save a GitHub PAT</label>
              <div className="mt-3 flex flex-col gap-3 md:flex-row">
                <input
                  type="password"
                  value={githubAccessToken}
                  onChange={(e) => setGitHubAccessToken(e.target.value)}
                  placeholder="ghp_..."
                  className="min-w-0 flex-1 rounded-xl border border-gray-700 bg-gray-900 px-4 py-3 text-sm text-white outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20"
                />
                <button
                  type="button"
                  onClick={handleConnectGitHubToken}
                  disabled={connecting || !githubAccessToken.trim()}
                  className="rounded-xl bg-white px-4 py-3 text-sm font-medium text-gray-950 transition hover:bg-gray-200 disabled:cursor-not-allowed disabled:bg-gray-800 disabled:text-gray-500"
                >
                  {connecting ? "Saving..." : "Save PAT"}
                </button>
              </div>
              <p className="mt-3 text-xs text-gray-500">
                Saved connections appear below and can be marked as the default for new launches.
              </p>
            </div>

            <div className="mt-5 space-y-3">
              {loadingConnections ? (
                <div className="rounded-2xl border border-dashed border-gray-700 p-6 text-sm text-gray-500">
                  Loading saved GitHub connections...
                </div>
              ) : providerConnections.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-gray-700 p-6 text-sm text-gray-500">
                  No saved GitHub connections yet. Add one above to enable repo autocomplete on the launch page.
                </div>
              ) : (
                providerConnections.map((connection) => {
                  const selected = connection.id === selectedConnectionId;
                  return (
                    <button
                      key={connection.id}
                      type="button"
                      onClick={() => setSelectedConnectionId(selected ? "" : connection.id)}
                      className={`w-full rounded-2xl border p-4 text-left transition ${
                        selected
                          ? "border-blue-500 bg-blue-950/40"
                          : "border-gray-800 bg-gray-950/70 hover:border-gray-700"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-medium text-white">{connection.provider.toUpperCase()}</p>
                          <p className="mt-1 text-sm text-gray-300">{describeConnection(connection)}</p>
                        </div>
                        <span
                          className={`rounded-full px-3 py-1 text-[11px] uppercase tracking-wide ${
                            selected
                              ? "bg-blue-400/20 text-blue-100"
                              : "border border-gray-700 text-gray-400"
                          }`}
                        >
                          {selected ? "Default" : "Available"}
                        </span>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          <div className="rounded-[24px] border border-gray-800 bg-gray-900/85 p-6">
            <h3 className="text-xl font-semibold text-white">AI runtime</h3>
            <p className="mt-2 text-sm text-gray-400">
              These defaults are used whenever you launch a new session unless the backend applies a stronger server-side override.
            </p>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <button
                type="button"
                onClick={() => handleProviderChange("gemini")}
                className={`rounded-2xl border p-4 text-left transition ${
                  llmProvider === "gemini"
                    ? "border-blue-500 bg-blue-950/40"
                    : "border-gray-800 bg-gray-950/70 hover:border-gray-700"
                }`}
              >
                <p className="text-sm font-medium text-white">Gemini</p>
                <p className="mt-2 text-sm text-gray-400">Default fast planner/agent setup for current sessions.</p>
              </button>
              <button
                type="button"
                onClick={() => handleProviderChange("openai")}
                className={`rounded-2xl border p-4 text-left transition ${
                  llmProvider === "openai"
                    ? "border-blue-500 bg-blue-950/40"
                    : "border-gray-800 bg-gray-950/70 hover:border-gray-700"
                }`}
              >
                <p className="text-sm font-medium text-white">OpenAI</p>
                <p className="mt-2 text-sm text-gray-400">Use OpenAI models for orchestration and agent launches.</p>
              </button>
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <div>
                <label className="block text-xs uppercase tracking-wide text-gray-500">Manager model</label>
                <input
                  type="text"
                  value={managerModel}
                  onChange={(e) => setManagerModel(e.target.value)}
                  placeholder={PROVIDER_DEFAULTS[llmProvider].managerModel}
                  className="mt-2 w-full rounded-xl border border-gray-700 bg-gray-950 px-4 py-3 text-sm text-white outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20"
                />
              </div>
              <div>
                <label className="block text-xs uppercase tracking-wide text-gray-500">Agent model</label>
                <input
                  type="text"
                  value={agentModel}
                  onChange={(e) => setAgentModel(e.target.value)}
                  placeholder={PROVIDER_DEFAULTS[llmProvider].agentModel}
                  className="mt-2 w-full rounded-xl border border-gray-700 bg-gray-950 px-4 py-3 text-sm text-white outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20"
                />
              </div>
            </div>
          </div>
        </div>

        <aside className="rounded-[24px] border border-gray-800 bg-gray-900/85 p-6">
          <p className="text-xs uppercase tracking-[0.25em] text-gray-500">Current launch profile</p>
          <div className="mt-5 space-y-5">
            <div className="rounded-2xl border border-gray-800 bg-gray-950/80 p-4">
              <p className="text-xs uppercase tracking-wide text-gray-500">GitHub connection</p>
              <p className="mt-2 text-sm font-medium text-white">
                {selectedConnection ? describeConnection(selectedConnection) : "No default connection selected"}
              </p>
              <p className="mt-2 text-sm text-gray-400">
                {selectedConnection
                  ? "Repo autocomplete and clone auth on the launch page will use this connection."
                  : "The launch page will still work, but repo autocomplete will stay disabled until you pick a connection."}
              </p>
            </div>

            <div className="rounded-2xl border border-gray-800 bg-gray-950/80 p-4">
              <p className="text-xs uppercase tracking-wide text-gray-500">AI defaults</p>
              <p className="mt-2 text-sm font-medium text-white">
                {llmProvider}:{managerModel}
              </p>
              <p className="mt-1 text-sm text-gray-400">Agent model: {agentModel}</p>
            </div>

            {(error || result) && (
              <div
                className={`rounded-2xl border p-4 text-sm ${
                  error
                    ? "border-red-900 bg-red-950/40 text-red-300"
                    : "border-emerald-900 bg-emerald-950/40 text-emerald-300"
                }`}
              >
                {error ?? result}
              </div>
            )}

            <div className="rounded-2xl border border-dashed border-gray-700 p-4 text-sm leading-7 text-gray-400">
              Settings are stored locally in this browser. If you change machines or browsers, reselect the preferred
              GitHub connection and model profile here.
            </div>
          </div>
        </aside>
      </section>
    </div>
  );
}
