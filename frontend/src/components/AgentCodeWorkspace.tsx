"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import useSWR from "swr";
import { fetchAgentFile, listAgentFiles, updateAgentFile } from "@/lib/api";
import type { AgentDirectoryListing, AgentFileDocument, AgentFileEntry } from "@/lib/types";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

interface AgentCodeWorkspaceProps {
  agentId: string;
  initialPath: string;
}

async function loadDirectoryWithFallback(
  agentId: string,
  path: string,
): Promise<AgentDirectoryListing> {
  let candidate = normalizePath(path);

  while (true) {
    try {
      const listing = await listAgentFiles(agentId, candidate);
      return {
        ...listing,
        path: candidate,
      };
    } catch (error) {
      if (!(error instanceof Error) || error.message !== "Path not found" || !candidate) {
        throw error;
      }
      candidate = parentPath(candidate);
    }
  }
}

function normalizePath(path: string) {
  return path.replace(/^\/+|\/+$/g, "");
}

function joinPath(base: string, next: string) {
  return normalizePath([base, next].filter(Boolean).join("/"));
}

function parentPath(path: string) {
  const segments = normalizePath(path).split("/").filter(Boolean);
  segments.pop();
  return segments.join("/");
}

function sortEntries(entries: AgentFileEntry[]) {
  return [...entries].sort((left, right) => {
    if (left.is_dir !== right.is_dir) {
      return left.is_dir ? -1 : 1;
    }
    return left.name.localeCompare(right.name);
  });
}

function languageForPath(path: string) {
  const extension = path.split(".").pop()?.toLowerCase();
  switch (extension) {
    case "ts":
    case "tsx":
      return "typescript";
    case "js":
    case "jsx":
      return "javascript";
    case "py":
      return "python";
    case "json":
      return "json";
    case "md":
      return "markdown";
    case "css":
      return "css";
    case "html":
      return "html";
    case "yml":
    case "yaml":
      return "yaml";
    case "sh":
      return "shell";
    default:
      return "plaintext";
  }
}

export function AgentCodeWorkspace({ agentId, initialPath }: AgentCodeWorkspaceProps) {
  const [currentDir, setCurrentDir] = useState(normalizePath(initialPath));
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const directoryKey = `agent:${agentId}:dir:${currentDir}`;
  const {
    data: directory,
    error: directoryError,
    isLoading: directoryLoading,
    mutate: mutateDirectory,
  } = useSWR<AgentDirectoryListing>(
    directoryKey,
    () => loadDirectoryWithFallback(agentId, currentDir),
  );

  const fileKey = selectedPath ? `agent:${agentId}:file:${selectedPath}` : null;
  const {
    data: fileDocument,
    error: fileError,
    isLoading: fileLoading,
    mutate: mutateFile,
  } = useSWR<AgentFileDocument>(
    fileKey,
    () => fetchAgentFile(agentId, selectedPath as string),
  );

  const activeDir = directory?.path ?? currentDir;
  const sortedEntries = useMemo(
    () => sortEntries(directory?.entries ?? []),
    [directory?.entries],
  );

  const editorValue = selectedPath
    ? (drafts[selectedPath] ?? fileDocument?.content ?? "")
    : "";
  const isDirty = Boolean(
    selectedPath
    && fileDocument
    && drafts[selectedPath] !== undefined
    && drafts[selectedPath] !== fileDocument.content
  );

  async function handleSave() {
    if (!selectedPath) {
      return;
    }

    setSaveState("saving");
    setSaveMessage(null);
    try {
      await updateAgentFile(agentId, selectedPath, editorValue);
      await mutateFile({ path: selectedPath, content: editorValue }, false);
      await mutateDirectory();
      setDrafts((current) => {
        const next = { ...current };
        delete next[selectedPath];
        return next;
      });
      setSaveState("saved");
      setSaveMessage("Saved");
    } catch (error) {
      setSaveState("error");
      setSaveMessage(error instanceof Error ? error.message : "Save failed");
    }
  }

  return (
    <section className="rounded-2xl border border-gray-800 bg-gray-900/80 p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-white">Code Workspace</h3>
          <p className="mt-1 text-sm text-gray-400">
            Browse the worker worktree, inspect generated files, and make manual edits when needed.
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-400">
          <span className="rounded-full border border-gray-700 px-3 py-1">
            {activeDir || "/"}
          </span>
          <button
            type="button"
            onClick={handleSave}
            disabled={!selectedPath || !isDirty || saveState === "saving"}
            className="rounded-lg border border-blue-700 bg-blue-600/20 px-4 py-2 text-sm text-blue-100 disabled:cursor-not-allowed disabled:border-gray-800 disabled:bg-gray-900 disabled:text-gray-500"
          >
            {saveState === "saving" ? "Saving..." : "Save File"}
          </button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="flex h-[36rem] min-h-[36rem] flex-col overflow-hidden rounded-xl border border-gray-800 bg-gray-950/80">
          <div className="flex items-center justify-between border-b border-gray-800 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.22em] text-gray-500">Files</p>
            <button
              type="button"
              onClick={() => {
                setCurrentDir(parentPath(activeDir));
                setSelectedPath(null);
                setSaveState("idle");
                setSaveMessage(null);
              }}
              disabled={!activeDir}
              className="text-xs text-gray-400 disabled:text-gray-700"
            >
              Up
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-2 py-2">
            {directoryLoading ? (
              <div className="px-3 py-4 text-sm text-gray-500">Loading files...</div>
            ) : directoryError ? (
              <div className="px-3 py-4 text-sm text-red-300">
                Failed to load files: {directoryError instanceof Error ? directoryError.message : "Unknown error"}
              </div>
            ) : sortedEntries.length === 0 ? (
              <div className="px-3 py-4 text-sm text-gray-500">No files in this folder.</div>
            ) : (
              sortedEntries.map((entry) => {
                const nextPath = joinPath(activeDir, entry.name);
                const active = !entry.is_dir && nextPath === selectedPath;
                return (
                  <button
                    key={`${entry.is_dir ? "dir" : "file"}:${nextPath}`}
                    type="button"
                    onClick={() => {
                      setSaveState("idle");
                      setSaveMessage(null);
                      if (entry.is_dir) {
                        setCurrentDir(nextPath);
                        setSelectedPath(null);
                        return;
                      }
                      setSelectedPath(nextPath);
                    }}
                    className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm ${
                      active
                        ? "bg-blue-600/20 text-blue-100"
                        : "text-gray-300 hover:bg-gray-800/80"
                    }`}
                  >
                    <span className={`text-xs ${entry.is_dir ? "text-amber-300" : "text-gray-500"}`}>
                      {entry.is_dir ? "DIR" : "FILE"}
                    </span>
                    <span className="truncate">{entry.name}</span>
                  </button>
                );
              })
            )}
          </div>
        </aside>

        <div className="flex h-[36rem] min-h-[36rem] flex-col overflow-hidden rounded-xl border border-gray-800 bg-[#111827]">
          <div className="flex items-center justify-between border-b border-gray-800 px-4 py-3">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-gray-500">Editor</p>
              <p className="mt-1 text-sm text-gray-300">{selectedPath || "Select a file"}</p>
            </div>
            {saveMessage ? (
              <span className={`text-xs ${
                saveState === "error" ? "text-red-300" : "text-emerald-300"
              }`}>
                {saveMessage}
              </span>
            ) : null}
          </div>

          <div className="flex-1 overflow-hidden">
            {!selectedPath ? (
              <div className="flex h-full items-center justify-center text-sm text-gray-500">
                Choose a file from the left to inspect the worker changes.
              </div>
            ) : fileLoading ? (
              <div className="flex h-full items-center justify-center text-sm text-gray-500">
                Loading file...
              </div>
            ) : fileError ? (
              <div className="flex h-full items-center justify-center px-6 text-sm text-red-300">
                Failed to load file: {fileError instanceof Error ? fileError.message : "Unknown error"}
              </div>
            ) : (
              <MonacoEditor
                key={selectedPath}
                height="100%"
                language={languageForPath(selectedPath)}
                theme="vs-dark"
                value={editorValue}
                onChange={(value) => {
                  if (!selectedPath) {
                    return;
                  }
                  setDrafts((current) => ({
                    ...current,
                    [selectedPath]: value ?? "",
                  }));
                  setSaveState("idle");
                  setSaveMessage(null);
                }}
                options={{
                  automaticLayout: true,
                  fontSize: 13,
                  minimap: { enabled: false },
                  padding: { top: 16 },
                  scrollBeyondLastLine: false,
                  wordWrap: "on",
                }}
              />
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
