import { Suspense } from "react";
import SessionClient from "./SessionClient";

export default function SessionPage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <Suspense fallback={<div className="p-6 text-zinc-500 text-sm">Loading session…</div>}>
      <SessionInner params={params} />
    </Suspense>
  );
}

async function SessionInner({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <SessionClient id={id} />;
}
