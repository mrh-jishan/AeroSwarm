/**
 * AgentTerminal — lightweight websocket log console for agent output.
 */

"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useWebSocketToken } from "@/lib/hooks/useWebSocketToken";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
const MAX_LINES = 400;

interface AgentTerminalProps {
  agentId: string;
}

function stripAnsi(value: string) {
  return value.replace(/\x1B\[[0-9;]*[A-Za-z]/g, "");
}

export default function AgentTerminal({ agentId }: AgentTerminalProps) {
  const [lines, setLines] = useState<string[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { token } = useWebSocketToken();

  const renderedText = useMemo(() => lines.join("\n"), [lines]);

  useEffect(() => {
    const scroller = scrollRef.current;
    if (!scroller) {
      return;
    }
    scroller.scrollTop = scroller.scrollHeight;
  }, [renderedText]);

  useEffect(() => {
    if (!token) {
      return;
    }

    let active = true;
    const url = new URL(`${WS_BASE}/api/agents/${agentId}/logs`);
    url.searchParams.set("token", token);
    const socket = new WebSocket(url.toString());

    const appendLine = (message: string) => {
      if (!active) {
        return;
      }
      const cleanLine = stripAnsi(message).replace(/\r/g, "").trimEnd();
      setLines((current) => {
        const next = cleanLine ? [...current, cleanLine] : current;
        return next.slice(-MAX_LINES);
      });
    };

    socket.onopen = () => {
      appendLine("[connected]");
    };

    socket.onmessage = (event) => {
      const chunks = String(event.data).split("\n");
      for (const chunk of chunks) {
        appendLine(chunk);
      }
    };

    socket.onerror = () => {
      appendLine("[connection error]");
    };

    socket.onclose = () => {
      appendLine("[stream closed]");
    };

    return () => {
      active = false;
      socket.close();
    };
  }, [agentId, token]);

  return (
    <div
      ref={scrollRef}
      className="h-full min-h-[200px] overflow-auto bg-black px-4 py-3 font-mono text-xs leading-6 text-emerald-300"
    >
      <pre className="whitespace-pre-wrap break-words">
        {renderedText || (token ? "Connecting to worker log stream..." : "Waiting for log stream...")}
      </pre>
    </div>
  );
}
