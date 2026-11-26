"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts";

const PROXY_URL = process.env.NEXT_PUBLIC_PROXY_URL ?? "http://localhost:8000";

interface EvalRun {
  id: string;
  created_at: string;
  mode: string;
  total_attacks: number;
  successful_attacks: number;
  total_benign: number;
  benign_passed: number;
  avg_latency_ms: number;
  details: unknown;
}

function pct(n: number, d: number) {
  if (!d) return "—";
  return `${Math.round((n / d) * 100)}%`;
}

export default function EvalPage() {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [running, setRunning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    supabase.from("eval_runs").select("*").order("created_at", { ascending: false }).limit(20)
      .then(({ data }) => { if (data) setRuns(data as EvalRun[]); });
  }, []);

  async function startEval(mode: string) {
    setRunning(mode);
    setError(null);
    try {
      const res = await fetch(`${PROXY_URL}/api/eval/run?mode=${mode}`, { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.stub) {
        setError("Eval suite not yet implemented (Phase 5). Run scenarios from the Demo page first.");
        setRunning(null);
        return;
      }
      // Poll for result
      const evalId = data.eval_run_id;
      const poll = setInterval(async () => {
        const { data: row } = await supabase.from("eval_runs").select("*").eq("id", evalId).single();
        if (row) {
          setRuns(prev => [row as EvalRun, ...prev.filter(r => r.id !== evalId)]);
          clearInterval(poll);
          setRunning(null);
        }
      }, 2000);
      // Safety timeout — stop spinning after 2 minutes
      setTimeout(() => { clearInterval(poll); setRunning(null); }, 120_000);
    } catch (e) {
      setError(String(e));
      setRunning(null);
    }
  }

  // Prepare chart data
  const chartData = ["off", "regex", "shield"].map(mode => {
    const run = runs.find(r => r.mode === mode);
    return {
      mode,
      "Attack Success Rate": run ? Math.round((run.successful_attacks / (run.total_attacks || 1)) * 100) : null,
      "Benign Pass Rate": run ? Math.round((run.benign_passed / (run.total_benign || 1)) * 100) : null,
    };
  }).filter(d => d["Attack Success Rate"] !== null || d["Benign Pass Rate"] !== null);

  return (
    <div className="p-6 max-w-4xl mx-auto w-full">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-bold text-zinc-100 tracking-wide">Eval Suite</h1>
        <div className="flex gap-2">
          {["off", "regex", "shield"].map(mode => (
            <button
              key={mode}
              onClick={() => startEval(mode)}
              disabled={!!running}
              className={`px-3 py-1.5 text-xs font-mono border rounded transition-colors ${
                running === mode ? "opacity-50 cursor-wait" : "cursor-pointer"
              } ${
                mode === "shield"
                  ? "border-cyan-700 text-cyan-400 hover:bg-cyan-900/20"
                  : mode === "regex"
                  ? "border-purple-700 text-purple-400 hover:bg-purple-900/20"
                  : "border-zinc-700 text-zinc-400 hover:bg-zinc-800"
              }`}
            >
              {running === mode ? "running…" : `run ${mode}`}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="mb-4 border border-red-800 bg-red-900/20 rounded p-3 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Chart */}
      {chartData.length > 0 && (
        <div className="mb-8 border border-zinc-800 rounded-lg p-4 bg-zinc-900/50">
          <div className="text-xs text-zinc-500 mb-3">Attack Success Rate (lower = better) vs Benign Pass Rate (higher = better)</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData}>
              <XAxis dataKey="mode" tick={{ fill: "#71717a", fontSize: 12, fontFamily: "monospace" }} />
              <YAxis unit="%" tick={{ fill: "#71717a", fontSize: 11 }} domain={[0, 100]} />
              <Tooltip
                contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", color: "#e4e4e7", fontFamily: "monospace", fontSize: 12 }}
              />
              <Legend wrapperStyle={{ fontSize: 12, fontFamily: "monospace", color: "#a1a1aa" }} />
              <Bar dataKey="Attack Success Rate" fill="#ef4444" radius={[3, 3, 0, 0]} />
              <Bar dataKey="Benign Pass Rate" fill="#22c55e" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Table */}
      <div className="border border-zinc-800 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900">
              <th className="text-left px-4 py-2 text-zinc-500 font-normal">Mode</th>
              <th className="text-left px-4 py-2 text-zinc-500 font-normal">ASR ↓</th>
              <th className="text-left px-4 py-2 text-zinc-500 font-normal">Benign Pass ↑</th>
              <th className="text-left px-4 py-2 text-zinc-500 font-normal">Attacks</th>
              <th className="text-left px-4 py-2 text-zinc-500 font-normal">Benign</th>
              <th className="text-left px-4 py-2 text-zinc-500 font-normal">Avg Latency</th>
              <th className="text-left px-4 py-2 text-zinc-500 font-normal">Time</th>
            </tr>
          </thead>
          <tbody>
            {runs.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-zinc-600">
                  No eval runs yet — click "run shield/regex/off" above.
                </td>
              </tr>
            )}
            {runs.map(run => (
              <tr key={run.id} className="border-b border-zinc-800/50 hover:bg-zinc-900/60">
                <td className="px-4 py-2 font-mono text-xs">{run.mode}</td>
                <td className="px-4 py-2 text-xs text-red-400">{pct(run.successful_attacks, run.total_attacks)}</td>
                <td className="px-4 py-2 text-xs text-emerald-400">{pct(run.benign_passed, run.total_benign)}</td>
                <td className="px-4 py-2 text-xs text-zinc-400">{run.successful_attacks}/{run.total_attacks}</td>
                <td className="px-4 py-2 text-xs text-zinc-400">{run.benign_passed}/{run.total_benign}</td>
                <td className="px-4 py-2 text-xs text-zinc-400">{run.avg_latency_ms ? `${run.avg_latency_ms}ms` : "—"}</td>
                <td className="px-4 py-2 text-xs text-zinc-500">{new Date(run.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
