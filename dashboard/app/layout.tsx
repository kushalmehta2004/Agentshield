import type { Metadata } from "next";
import { Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const mono = Geist_Mono({ variable: "--font-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AgentShield",
  description: "Security proxy for AI agents — Proof of Cause engine",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${mono.variable} dark h-full`}>
      <body className="min-h-full flex flex-col bg-zinc-950 text-zinc-100 font-mono">
        <nav className="border-b border-zinc-800 px-6 py-3 flex items-center gap-6 text-sm">
          <Link href="/" className="font-bold text-cyan-400 tracking-widest uppercase">
            AgentShield
          </Link>
          <Link href="/" className="text-zinc-400 hover:text-zinc-100 transition-colors">Sessions</Link>
          <Link href="/demo" className="text-zinc-400 hover:text-zinc-100 transition-colors">Demo</Link>
          <Link href="/eval" className="text-zinc-400 hover:text-zinc-100 transition-colors">Eval</Link>
        </nav>
        <main className="flex-1 flex flex-col">{children}</main>
      </body>
    </html>
  );
}
