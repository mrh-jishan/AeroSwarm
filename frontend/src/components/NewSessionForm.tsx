/**
 * NewSessionForm — lets the user enter a repo URL + prompt to start a session.
 */

"use client";

import { useEffect, useState } from "react";
import {
  connectGitHub,
  createSession,
  getGitHubAppInstallStartUrl,
  getGitHubOAuthStartUrl,
  listProviderConnections,
} from "@/lib/api";
import type { ProviderConnection } from "@/lib/types";

interface NewSessionFormProps {
  onSessionCreated?: (sessionId: string) => void;
  currentUserEmail: string;
}

function describeConnection(connection: ProviderConnection) {
  if (connection.auth_mode === "github_app") {
    return `${connection.provider}: ${connection.account_login} (GitHub App #${connection.installation_id ?? "?"})`;
  }
  return `${connection.provider}: ${connection.account_login} (${connection.auth_mode})`;
}

export function NewSessionForm({ onSessionCreated, currentUserEmail }: NewSessionFormProps) {
  const [repoUrl, setRepoUrl] = useState("");
  const [repoUsername, setRepoUsername] = useState("");
  const [repoAccessToken, setRepoAccessToken] = useState("");
  const [githubAccessToken, setGitHubAccessToken] = useState("");
  const [providerConnections, setProviderConnections] = useState<ProviderConnection[]>([]);
  const [selectedConnectionId, setSelectedConnectionId] = useState("");
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadConnections() {
      try {
        const connections = await listProviderConnections();
        if (!cancelled) {
          setProviderConnections(connections);
          if (!selectedConnectionId && connections.length > 0) {
            setSelectedConnectionId(connections[0].id);
          }
        }
      } catch {
        if (!cancelled) {
          setProviderConnections([]);
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
            : "GitHub App installation added."
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
  }, [selectedConnectionId]);

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

  function handleConnectGitHubOAuth() {
    window.location.href = getGitHubOAuthStartUrl(window.location.pathname);
  }

  function handleInstallGitHubApp() {
    window.location.href = getGitHubAppInstallStartUrl(window.location.pathname);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const session = await createSession({
        repoUrl,
        prompt,
        providerConnectionId: selectedConnectionId || undefined,
        repoAccessToken,
        repoUsername,
      });
      const repoSummary = session.repo_owner && session.repo_name
        ? ` • ${session.repo_owner}/${session.repo_name}@${session.base_branch ?? "unknown"}`
        : "";
      setResult(`Session created: ${session.id} — ${session.agent_count} agents launched${repoSummary}`);
      onSessionCreated?.(session.id);
      setRepoUrl("");
      setRepoAccessToken("");
      setRepoUsername("");
      setPrompt("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-5">
      <h2 className="text-lg font-semibold">New Session</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Signed In As</label>
          <input
            type="text"
            value={currentUserEmail}
            disabled
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">Repository URL</label>
          <input
            type="text"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            placeholder="https://github.com/org/repo"
            required
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">Saved VCS Connection</label>
          <select
            value={selectedConnectionId}
            onChange={(e) => setSelectedConnectionId(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">None</option>
            {providerConnections.map((connection) => (
              <option key={connection.id} value={connection.id}>
                {describeConnection(connection)}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <label className="block text-xs text-gray-400 mb-1">GitHub Connection</label>
          <div className="grid grid-cols-1 gap-2">
            <button
              type="button"
              onClick={handleConnectGitHubOAuth}
              className="w-full px-3 py-2 bg-blue-700 hover:bg-blue-600 rounded-lg text-sm"
            >
              Connect With GitHub OAuth
            </button>
            <button
              type="button"
              onClick={handleInstallGitHubApp}
              className="w-full px-3 py-2 bg-emerald-700 hover:bg-emerald-600 rounded-lg text-sm"
            >
              Install GitHub App
            </button>
            <div className="flex gap-2">
              <input
                type="password"
                value={githubAccessToken}
                onChange={(e) => setGitHubAccessToken(e.target.value)}
                placeholder="Fallback PAT"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                onClick={handleConnectGitHubToken}
                disabled={connecting || !githubAccessToken}
                className="px-3 py-2 bg-gray-800 hover:bg-gray-700 disabled:bg-gray-900 rounded-lg text-sm"
              >
                {connecting ? "Saving..." : "Save PAT"}
              </button>
            </div>
          </div>
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">One-Off Repo Username</label>
          <input
            type="text"
            value={repoUsername}
            onChange={(e) => setRepoUsername(e.target.value)}
            placeholder="Optional fallback for clone auth"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">One-Off Repo Token</label>
          <input
            type="password"
            value={repoAccessToken}
            onChange={(e) => setRepoAccessToken(e.target.value)}
            placeholder="Used if no saved connection is selected"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="md:col-span-2">
          <label className="block text-xs text-gray-400 mb-1">Feature Prompt</label>
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Build a Stripe checkout flow"
            required
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button
          type="submit"
          disabled={loading}
          className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 rounded-lg text-sm font-medium transition-colors"
        >
          {loading ? "Launching session..." : "Launch Session"}
        </button>
        {error && <p className="text-red-400 text-sm">{error}</p>}
        {result && <p className="text-green-400 text-sm">{result}</p>}
      </div>
    </form>
  );
}
