/**
 * AgentTerminal — lightweight websocket log console for agent output.
 */

"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { fetchAgentLogsPage } from "@/lib/api";
import { useWebSocketToken } from "@/lib/hooks/useWebSocketToken";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
const MAX_LIVE_BUFFER = 2000;
const HISTORY_PAGE_SIZE = 150;

interface AgentTerminalProps {
  agentId: string;
}

function stripAnsi(value: string) {
  return value.replace(/\x1B\[[0-9;]*[A-Za-z]/g, "");
}

export default function AgentTerminal({ agentId }: AgentTerminalProps) {
  const [historyAgentId, setHistoryAgentId] = useState<string | null>(null);
  const [lines, setLines] = useState<string[]>([]);
  const [nextBefore, setNextBefore] = useState<number | null>(null);
  const [isLoadingOlder, setIsLoadingOlder] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const shouldStickToBottomRef = useRef(true);
  const { token } = useWebSocketToken();
  const historyLoaded = historyAgentId === agentId;

  const renderedText = useMemo(() => lines.join("\n"), [lines]);

  useEffect(() => {
    let active = true;

    fetchAgentLogsPage(agentId, { limit: HISTORY_PAGE_SIZE })
      .then((page) => {
        if (!active) {
          return;
        }
        const normalized = page.lines
          .map((line) => stripAnsi(line).replace(/\r/g, "").trimEnd())
          .filter(Boolean);
        setLines(normalized.slice(-MAX_LIVE_BUFFER));
        setNextBefore(page.nextBefore);
        setHistoryAgentId(agentId);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setLines([]);
        setNextBefore(null);
        setHistoryAgentId(agentId);
      });

    return () => {
      active = false;
    };
  }, [agentId]);

  useEffect(() => {
    const scroller = scrollRef.current;
    if (!scroller || !historyLoaded) {
      return;
    }

    const handleScroll = () => {
      shouldStickToBottomRef.current = (
        scroller.scrollHeight - scroller.clientHeight - scroller.scrollTop
      ) < 48;
      if (scroller.scrollTop > 48 || nextBefore === null || isLoadingOlder) {
        return;
      }

      const previousHeight = scroller.scrollHeight;
      setIsLoadingOlder(true);
      fetchAgentLogsPage(agentId, { before: nextBefore, limit: HISTORY_PAGE_SIZE })
        .then((page) => {
          const normalized = page.lines
            .map((line) => stripAnsi(line).replace(/\r/g, "").trimEnd())
            .filter(Boolean);
          if (normalized.length === 0) {
            setNextBefore(page.nextBefore);
            return;
          }
          setLines((current) => [...normalized, ...current].slice(-2000));
          setNextBefore(page.nextBefore);
          window.requestAnimationFrame(() => {
            const updatedScroller = scrollRef.current;
            if (!updatedScroller) {
              return;
            }
            updatedScroller.scrollTop = updatedScroller.scrollHeight - previousHeight;
          });
        })
        .catch(() => {
          setNextBefore(null);
        })
        .finally(() => {
          setIsLoadingOlder(false);
        });
    };

    scroller.addEventListener("scroll", handleScroll);
    return () => {
      scroller.removeEventListener("scroll", handleScroll);
    };
  }, [agentId, historyLoaded, isLoadingOlder, nextBefore]);

  useEffect(() => {
    const scroller = scrollRef.current;
    if (!scroller || !shouldStickToBottomRef.current || isLoadingOlder) {
      return;
    }
    scroller.scrollTop = scroller.scrollHeight;
  }, [isLoadingOlder, renderedText]);

  useEffect(() => {
    if (!token) {
      return;
    }

    let active = true;
    let didOpen = false;
    let socket: WebSocket | null = null;
    const connectTimer = window.setTimeout(() => {
      if (!active) {
        return;
      }
      const url = new URL(`${WS_BASE}/api/agents/${agentId}/logs`);
      url.searchParams.set("token", token);
      socket = new WebSocket(url.toString());

      const appendLine = (message: string) => {
        if (!active) {
          return;
        }
        const cleanLine = stripAnsi(message).replace(/\r/g, "").trimEnd();
        setLines((current) => {
          const next = cleanLine ? [...current, cleanLine] : current;
          return next.slice(-MAX_LIVE_BUFFER);
        });
      };

      socket.onopen = () => {
        didOpen = true;
      };

      socket.onmessage = (event) => {
        const chunks = String(event.data).split("\n");
        for (const chunk of chunks) {
          appendLine(chunk);
        }
      };

      socket.onerror = () => {
        if (didOpen) {
          appendLine("[connection error]");
        }
      };

      socket.onclose = () => {
        if (didOpen) {
          appendLine("[stream closed]");
        }
      };
    }, 0);

    return () => {
      active = false;
      window.clearTimeout(connectTimer);
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    };
  }, [agentId, token]);

  return (
    <div
      ref={scrollRef}
      className="h-full min-h-[200px] overflow-auto bg-black px-4 py-3 font-mono text-xs leading-6 text-emerald-300"
    >
      {isLoadingOlder ? (
        <div className="mb-2 text-[11px] uppercase tracking-[0.22em] text-emerald-500/70">
          Loading older logs...
        </div>
      ) : null}
      <pre className="whitespace-pre-wrap break-words">
        {(historyLoaded ? renderedText : "")
          || (!historyLoaded
            ? "Loading worker logs..."
            : token
              ? "Waiting for live worker logs..."
              : "Waiting for log stream...")}
      </pre>
    </div>
  );
}
