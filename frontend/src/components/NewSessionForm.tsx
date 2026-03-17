/**
 * NewSessionForm — lets the user enter a repo URL + prompt to start a session.
 */

"use client";

import { useState } from "react";
import { createSession } from "@/lib/api";

interface NewSessionFormProps {
  onSessionCreated?: (sessionId: string) => void;
  currentUserEmail: string;
}

export function NewSessionForm({ onSessionCreated, currentUserEmail }: NewSessionFormProps) {
  const [repoUrl, setRepoUrl] = useState("");
  const [repoUsername, setRepoUsername] = useState("");
  const [repoAccessToken, setRepoAccessToken] = useState("");
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const session = await createSession({
        repoUrl,
        prompt,
        repoAccessToken,
        repoUsername,
      });
      setResult(`Session created: ${session.id} — ${session.agent_count} agents launched`);
      onSessionCreated?.(session.id);
      setRepoUrl("");
      setRepoAccessToken("");
      setPrompt("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
      <h2 className="text-lg font-semibold">New Session</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Signed In As</label>
          <input
            type="text"
            value={currentUserEmail}
            disabled
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
          <label className="block text-xs text-gray-400 mb-1">Repo Username (Optional)</label>
          <input
            type="text"
            value={repoUsername}
            onChange={(e) => setRepoUsername(e.target.value)}
            placeholder="x-access-token"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">Repo Access Token (Optional)</label>
          <input
            type="password"
            value={repoAccessToken}
            onChange={(e) => setRepoAccessToken(e.target.value)}
            placeholder="Used only for the clone request"
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
