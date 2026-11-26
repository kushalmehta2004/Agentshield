"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabase";

interface Session {
  id: string;
  created_at: string;
  scenario: string | null;
  mode: string;
  status: string;
}

const STATUS_COLORS: Record<string, string> = {
  blocked: "bg-red-900 text-red-300 border-red-700",
  allowed: "bg-emerald-900 text-emerald-300 border-emerald-700",
  warn: "bg-amber-900 text-amber-300 border-amber-700",
  running: "bg-zinc-800 text-zinc-400 border-zinc-600",
};

function StatusChip({ status }: { status: string }) {
  const cls = STATUS_COLORS[status] ?? STATUS_COLORS.running;
  return (
    <span className={`inline-block border rounded px-2 py-0.5 text-xs font-mono uppercase tracking-wider ${cls}`}>
      {status}
    </span>
  );
}

function ModeChip({ mode }: { mode: string }) {
  const colors: Record<string, string> = {
    shield: "text-cyan-400",
    regex: "text-purple-400",
    off: "text-zinc-500",
  };
  return <span className={`${colors[mode] ?? "text-zinc-400"} text-xs`}>{mode}</span>;
}

export default function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);

  useEffect(() => {
    // Initial load — newest first
    supabase
      .from("sessions")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(50)
      .then(({ data }) => {
        if (data) setSessions(data as Session[]);
      });

    // Realtime subscription
    const channel = supabase
      .channel("sessions-list")
      .on("postgres_changes", { event: "*", schema: "public", table: "sessions" }, (payload) => {
        if (payload.eventType === "INSERT") {
          setSessions((prev) => [payload.new as Session, ...prev]);
        } else if (payload.eventType === "UPDATE") {
          setSessions((prev) =>
            prev.map((s) => (s.id === (payload.new as Session).id ? (payload.new as Session) : s))
          );
        }
      })
      .subscribe();

    return () => { supabase.removeChannel(channel); };
  }, []);

  return (
    <div className="p-6 max-w-5xl mx-auto w-full">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-bold text-zinc-100 tracking-wide">Sessions</h1>
        <span className="text-xs text-zinc-500">live • {sessions.length} rows</span>
      </div>

      <div className="border border-zinc-800 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900">
              <th className="text-left px-4 py-2 text-zinc-500 font-normal">Session ID</th>
              <th className="text-left px-4 py-2 text-zinc-500 font-normal">Scenario</th>
              <th className="text-left px-4 py-2 text-zinc-500 font-normal">Mode</th>
              <th className="text-left px-4 py-2 text-zinc-500 font-normal">Status</th>
              <th className="text-left px-4 py-2 text-zinc-500 font-normal">Time</th>
            </tr>
          </thead>
          <tbody>
            {sessions.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-zinc-600">
                  No sessions yet — run a scenario to see data here.
                </td>
              </tr>
            )}
            {sessions.map((s) => (
              <tr key={s.id} className="border-b border-zinc-800/50 hover:bg-zinc-900/60 transition-colors">
                <td className="px-4 py-2">
                  <Link href={`/sessions/${s.id}`} className="text-cyan-400 hover:text-cyan-300 font-mono text-xs">
                    {s.id.slice(0, 8)}…
                  </Link>
                </td>
                <td className="px-4 py-2 text-zinc-300 text-xs">{s.scenario ?? "—"}</td>
                <td className="px-4 py-2"><ModeChip mode={s.mode} /></td>
                <td className="px-4 py-2"><StatusChip status={s.status} /></td>
                <td className="px-4 py-2 text-zinc-500 text-xs">
                  {new Date(s.created_at).toLocaleTimeString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
