"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { Timeline } from "@/components/Timeline";
import { CausalGraph } from "@/components/CausalGraph";
import { ChunkInspector } from "@/components/ChunkInspector";

interface Session {
  id: string;
  created_at: string;
  scenario: string | null;
  mode: string;
  status: string;
}

interface CauseInfo {
  source_label: string;
  chunk_index: number | null;
  chunk_text: string | null;
  effect: string;
}

interface Verdict {
  id: string;
  created_at: string;
  mode: string;
  decision: string;
  attack_detected: boolean;
  unstable: boolean;
  causes: CauseInfo[];
  reruns: Array<{ variant: string; tool_calls: Array<{ name: string; arguments: string }> }>;
  latency_ms: number;
  tool_call_id?: string;
}

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

const STATUS_COLORS: Record<string, string> = {
  blocked: "text-red-400",
  allowed: "text-emerald-400",
  warn: "text-amber-400",
  running: "text-zinc-400",
};

export default function SessionClient({ id }: { id: string }) {
  const [session, setSession] = useState<Session | null>(null);
  const [llmCalls, setLlmCalls] = useState<LlmCall[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [verdicts, setVerdicts] = useState<Verdict[]>([]);
  const [selectedVerdict, setSelectedVerdict] = useState<Verdict | null>(null);
  const [selectedChunk, setSelectedChunk] = useState<CauseInfo | null>(null);

  useEffect(() => {
    supabase.from("sessions").select("*").eq("id", id).single()
      .then(({ data }) => { if (data) setSession(data as Session); });

    supabase.from("llm_calls").select("*").eq("session_id", id).order("created_at")
      .then(({ data }) => { if (data) setLlmCalls(data as LlmCall[]); });

    supabase.from("tool_calls").select("*").eq("session_id", id).order("created_at")
      .then(({ data }) => { if (data) setToolCalls(data as ToolCall[]); });

    supabase.from("verdicts").select("*").eq("session_id", id).order("created_at")
      .then(({ data }) => {
        if (data) {
          setVerdicts(data as Verdict[]);
          const blocked = (data as Verdict[]).find(v => v.decision === "BLOCK");
          if (blocked) setSelectedVerdict(blocked);
        }
      });

    const channel = supabase
      .channel(`session-${id}`)
      .on("postgres_changes", { event: "*", schema: "public", table: "sessions", filter: `id=eq.${id}` },
        (p) => { if (p.new) setSession(p.new as Session); })
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "tool_calls", filter: `session_id=eq.${id}` },
        (p) => { setToolCalls(prev => [...prev, p.new as ToolCall]); })
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "verdicts", filter: `session_id=eq.${id}` },
        (p) => {
          const v = p.new as Verdict;
          setVerdicts(prev => [...prev, v]);
          if (v.decision === "BLOCK") setSelectedVerdict(v);
        })
      .subscribe();

    return () => { supabase.removeChannel(channel); };
  }, [id]);

  const userTask = (() => {
    if (llmCalls.length === 0) return "";
    const msgs = llmCalls[0].request_messages as Array<{ role: string; content: string }>;
    return msgs?.find(m => m.role === "user")?.content ?? "";
  })();

  const sensitiveTc = selectedVerdict
    ? toolCalls.find(tc => tc.id === selectedVerdict.tool_call_id || tc.is_sensitive)
    : null;

  const targetValue = sensitiveTc ? String(Object.values(sensitiveTc.args)[0] ?? "") : "";

  return (
    <div className="p-6 max-w-5xl mx-auto w-full">
      <div className="flex items-center gap-3 mb-6 text-xs text-zinc-500">
        <Link href="/" className="hover:text-zinc-300">Sessions</Link>
        <span>/</span>
        <span className="font-mono text-zinc-300">{id}</span>
      </div>

      {session && (
        <div className="flex items-center gap-4 mb-6">
          <span className="font-mono text-sm text-zinc-300">{session.scenario ?? "unknown"}</span>
          <span className="text-xs text-zinc-500">mode: {session.mode}</span>
          <span className={`text-sm font-bold ${STATUS_COLORS[session.status] ?? "text-zinc-400"}`}>
            {session.status.toUpperCase()}
          </span>
        </div>
      )}

      {selectedVerdict && selectedVerdict.causes.length > 0 && (
        <div className="mb-6">
          <h2 className="text-xs text-zinc-500 uppercase tracking-widest mb-2">Causal Graph</h2>
          <CausalGraph
            sessionId={id}
            userTask={userTask}
            toolCallName={sensitiveTc?.tool_name ?? "unknown"}
            toolCallArgs={JSON.stringify(sensitiveTc?.args ?? {})}
            verdict={selectedVerdict}
            onSelectChunk={(cause) => setSelectedChunk(cause)}
          />
        </div>
      )}

      {selectedChunk && (
        <div className="mb-6">
          <h2 className="text-xs text-zinc-500 uppercase tracking-widest mb-2">Culprit Chunk</h2>
          <ChunkInspector
            cause={selectedChunk}
            targetValue={targetValue}
            onClose={() => setSelectedChunk(null)}
          />
        </div>
      )}

      <div>
        <h2 className="text-xs text-zinc-500 uppercase tracking-widest mb-3">Timeline</h2>
        <Timeline
          llmCalls={llmCalls}
          toolCalls={toolCalls}
          verdicts={verdicts}
          onSelectVerdict={(v) => {
            setSelectedVerdict(v);
            setSelectedChunk(null);
          }}
        />
      </div>
    </div>
  );
}
