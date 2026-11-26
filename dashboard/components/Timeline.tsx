"use client";

import { useState } from "react";

interface ToolCall {
  id: string;
  tool_name: string;
  args: Record<string, unknown>;
  is_sensitive: boolean;
  created_at: string;
}

interface LlmCall {
  id: string;
  created_at: string;
  latency_ms: number;
  request_messages: unknown[];
  response: Record<string, unknown>;
}

interface Verdict {
  id: string;
  created_at: string;
  mode: string;
  decision: string;
  attack_detected: boolean;
  unstable: boolean;
  causes: Array<{ source_label: string; chunk_index: number | null; chunk_text: string | null; effect: string }>;
  reruns: Array<{ variant: string; tool_calls: Array<{ name: string; arguments: string }> }>;
  latency_ms: number;
}

interface Props {
  llmCalls: LlmCall[];
  toolCalls: ToolCall[];
  verdicts: Verdict[];
  onSelectVerdict?: (v: Verdict) => void;
}

const DECISION_COLORS: Record<string, string> = {
  BLOCK: "border-red-700 bg-red-900/30 text-red-300",
  WARN: "border-amber-700 bg-amber-900/30 text-amber-300",
  ALLOW: "border-emerald-700 bg-emerald-900/30 text-emerald-300",
};

export function Timeline({ llmCalls, toolCalls, verdicts, onSelectVerdict }: Props) {
  const [openRerun, setOpenRerun] = useState<string | null>(null);

  if (!llmCalls.length && !toolCalls.length && !verdicts.length) {
    return <div className="text-zinc-600 text-sm py-4">No timeline events yet.</div>;
  }

  // Build a flat sorted event list
  type Event =
    | { type: "llm"; data: LlmCall }
    | { type: "tool"; data: ToolCall }
    | { type: "verdict"; data: Verdict };

  const events: Event[] = [
    ...llmCalls.map(d => ({ type: "llm" as const, data: d })),
    ...toolCalls.map(d => ({ type: "tool" as const, data: d })),
    ...verdicts.map(d => ({ type: "verdict" as const, data: d })),
  ].sort((a, b) => new Date(a.data.created_at).getTime() - new Date(b.data.created_at).getTime());

  return (
    <div className="relative pl-6">
      <div className="absolute left-2 top-0 bottom-0 w-px bg-zinc-800" />
      {events.map((evt, i) => (
        <div key={i} className="relative mb-4">
          <div className="absolute -left-4 top-1.5 w-2 h-2 rounded-full border border-zinc-700 bg-zinc-900" />

          {evt.type === "llm" && (
            <div className="border border-zinc-800 rounded-lg bg-zinc-900/50 p-3">
              <div className="flex items-center gap-2 text-xs text-zinc-500 mb-1">
                <span className="text-zinc-300 font-semibold">LLM Call</span>
                <span>{new Date(evt.data.created_at).toLocaleTimeString()}</span>
                <span>{evt.data.latency_ms}ms</span>
              </div>
            </div>
          )}

          {evt.type === "tool" && (
            <div className={`border rounded-lg p-3 text-xs ${evt.data.is_sensitive ? "border-amber-800 bg-amber-900/20" : "border-zinc-800 bg-zinc-900/50"}`}>
              <div className="flex items-center gap-2 mb-1">
                <span className={`font-semibold ${evt.data.is_sensitive ? "text-amber-300" : "text-zinc-300"}`}>
                  {evt.data.is_sensitive ? "⚠ " : ""}Tool Call
                </span>
                <span className="font-mono text-cyan-400">{evt.data.tool_name}</span>
                <span className="text-zinc-500">{new Date(evt.data.created_at).toLocaleTimeString()}</span>
              </div>
              <pre className="text-zinc-400 overflow-x-auto">{JSON.stringify(evt.data.args, null, 2)}</pre>
            </div>
          )}

          {evt.type === "verdict" && (
            <div
              className={`border rounded-lg p-3 cursor-pointer transition-colors ${DECISION_COLORS[evt.data.decision] ?? "border-zinc-700"}`}
              onClick={() => onSelectVerdict?.(evt.data)}
            >
              <div className="flex items-center gap-3 mb-2">
                <span className="font-bold text-sm">{evt.data.decision}</span>
                <span className="text-xs opacity-70">mode: {evt.data.mode}</span>
                {evt.data.attack_detected && <span className="text-xs bg-red-800 text-red-200 rounded px-1">attack detected</span>}
                {evt.data.unstable && <span className="text-xs bg-zinc-700 text-zinc-300 rounded px-1">unstable</span>}
                <span className="text-xs opacity-70">{evt.data.latency_ms}ms</span>
              </div>

              {evt.data.causes.length > 0 && (
                <div className="text-xs mb-2">
                  {evt.data.causes.map((c, ci) => (
                    <div key={ci} className="flex gap-2">
                      <span className="opacity-60">cause:</span>
                      <span className="font-mono">{c.source_label}{c.chunk_index !== null ? `#p${c.chunk_index + 1}` : ""}</span>
                      <span className="opacity-60">({c.effect})</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Re-run accordion */}
              {evt.data.reruns.length > 0 && (
                <div>
                  <button
                    className="text-xs underline opacity-60 hover:opacity-100"
                    onClick={e => { e.stopPropagation(); setOpenRerun(openRerun === evt.data.id ? null : evt.data.id); }}
                  >
                    {openRerun === evt.data.id ? "hide" : "show"} {evt.data.reruns.length} re-runs
                  </button>
                  {openRerun === evt.data.id && (
                    <div className="mt-2 space-y-1">
                      {evt.data.reruns.map((r, ri) => (
                        <div key={ri} className="border border-zinc-700/50 rounded p-2 text-xs">
                          <span className="font-mono text-zinc-400">{r.variant}: </span>
                          {r.tool_calls.length === 0
                            ? <span className="text-zinc-600">no tool calls</span>
                            : r.tool_calls.map((tc, tci) => (
                                <span key={tci} className="font-mono text-zinc-300">{tc.name}({tc.arguments.slice(0, 60)})</span>
                              ))
                          }
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
