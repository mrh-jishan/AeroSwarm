/**
 * AgentTerminal — xterm.js terminal panel connected to backend WebSocket.
 * Streams real-time agent stdout from Redis via FastAPI /api/agents/:id/logs
 */

"use client";

import { useEffect, useRef } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";
import { getApiToken } from "@/lib/api";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

interface AgentTerminalProps {
  agentId: string;
}

export default function AgentTerminal({ agentId }: AgentTerminalProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const term = new Terminal({
      theme: { background: "#000000", foreground: "#d4d4d4" },
      fontSize: 12,
      fontFamily: "monospace",
      rows: 12,
      cursorBlink: false,
    });
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(containerRef.current);
    fitAddon.fit();
    termRef.current = term;

    const token = getApiToken();
    const url = new URL(`${WS_BASE}/api/agents/${agentId}/logs`);
    if (token) {
      url.searchParams.set("token", token);
    }

    const ws = new WebSocket(url.toString());
    wsRef.current = ws;

    ws.onmessage = (e) => {
      term.writeln(e.data);
    };

    ws.onerror = () => {
      term.writeln("\r\n\x1b[31m[Connection error]\x1b[0m");
    };

    ws.onclose = () => {
      term.writeln("\r\n\x1b[33m[Stream closed]\x1b[0m");
    };

    return () => {
      ws.close();
      term.dispose();
    };
  }, [agentId]);

  return <div ref={containerRef} className="w-full h-full p-1" />;
}
