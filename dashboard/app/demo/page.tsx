"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const PROXY_URL = process.env.NEXT_PUBLIC_PROXY_URL ?? "http://localhost:8000";

const SCENARIOS = [
  {
    id: "benign_summary_email",
    label: "Benign",
    description: "Read the team update page and email a summary to me@kushal.dev",
    icon: "✅",
    color: "border-emerald-700 hover:border-emerald-500 hover:bg-emerald-900/20",
  },
  {
    id: "paraphrased_injection",
    label: "Paraphrased Attack",
    description: "Blog post with a naturally-worded injection — regex misses it, AgentShield blocks it",
    icon: "🎯",
    color: "border-red-700 hover:border-red-500 hover:bg-red-900/20",
  },
  {
    id: "hidden_html_injection",
    label: "Hidden HTML Injection",
    description: "Injection hidden in an HTML comment — invisible in browser, visible to the agent",
    icon: "🕵️",
    color: "border-amber-700 hover:border-amber-500 hover:bg-amber-900/20",
  },
];

const MODES = ["off", "regex", "shield"] as const;

export default function DemoPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"off" | "regex" | "shield">("shield");
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runScenario(scenarioId: string) {
    setLoading(scenarioId);
    setError(null);
    try {
      const res = await fetch(`${PROXY_URL}/api/scenarios/${scenarioId}/run?mode=${mode}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.session_id) {
        router.push(`/sessions/${data.session_id}`);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto w-full">
      <h1 className="text-lg font-bold text-zinc-100 tracking-wide mb-2">Run a Scenario</h1>
      <p className="text-sm text-zinc-500 mb-6">
        Each button runs a scripted agent scenario through the proxy and opens the session page.
      </p>

      {/* Mode toggle */}
      <div className="flex items-center gap-2 mb-8">
        <span className="text-xs text-zinc-500 mr-2">Mode:</span>
        {MODES.map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`px-3 py-1.5 rounded text-xs font-mono border transition-colors ${
              mode === m
                ? m === "shield"
                  ? "border-cyan-500 bg-cyan-900/30 text-cyan-300"
                  : m === "regex"
                  ? "border-purple-500 bg-purple-900/30 text-purple-300"
                  : "border-zinc-500 bg-zinc-800 text-zinc-300"
                : "border-zinc-700 text-zinc-500 hover:border-zinc-500"
            }`}
          >
            {m}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 border border-red-800 bg-red-900/20 rounded p-3 text-xs text-red-300">
          Error: {error}
        </div>
      )}

      <div className="space-y-4">
        {SCENARIOS.map((s) => (
          <button
            key={s.id}
            onClick={() => runScenario(s.id)}
            disabled={loading === s.id}
            className={`w-full text-left border rounded-lg p-5 transition-all ${s.color} ${
              loading === s.id ? "opacity-50 cursor-wait" : "cursor-pointer"
            }`}
          >
            <div className="flex items-center gap-3 mb-1">
              <span className="text-2xl">{s.icon}</span>
              <span className="font-bold text-zinc-100">{s.label}</span>
              {loading === s.id && <span className="text-xs text-zinc-400 animate-pulse">running…</span>}
            </div>
            <p className="text-sm text-zinc-400 ml-10">{s.description}</p>
          </button>
        ))}
      </div>

      <div className="mt-8 border border-zinc-800 rounded p-4 text-xs text-zinc-500 space-y-1">
        <div className="font-semibold text-zinc-400 mb-2">Expected results (shield mode)</div>
        <div>• Benign → <span className="text-emerald-400">ALLOW</span> — email sends normally</div>
        <div>• Paraphrased → <span className="text-red-400">BLOCK</span> — injection attributed to paragraph 1</div>
        <div>• Hidden HTML → <span className="text-red-400">BLOCK</span> — injection in HTML comment found</div>
        <div className="mt-2 pt-2 border-t border-zinc-800">
          With <span className="text-purple-400">regex</span> mode, paraphrased attack <span className="text-amber-400">bypasses</span> the baseline.
        </div>
      </div>
    </div>
  );
}
