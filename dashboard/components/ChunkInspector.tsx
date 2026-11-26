"use client";

interface CauseInfo {
  source_label: string;
  chunk_index: number | null;
  chunk_text: string | null;
  effect: string;
}

interface Props {
  cause: CauseInfo;
  targetValue?: string;
  onClose: () => void;
}

function highlightTarget(text: string, target: string) {
  if (!target) return <span>{text}</span>;
  const idx = text.toLowerCase().indexOf(target.toLowerCase());
  if (idx === -1) return <span>{text}</span>;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-red-800 text-red-200 rounded px-0.5">{text.slice(idx, idx + target.length)}</mark>
      {text.slice(idx + target.length)}
    </>
  );
}

export function ChunkInspector({ cause, targetValue, onClose }: Props) {
  return (
    <div className="border border-zinc-700 rounded-lg bg-zinc-900 p-4 relative">
      <button
        onClick={onClose}
        className="absolute top-3 right-3 text-zinc-500 hover:text-zinc-200 text-xs"
      >
        ✕ close
      </button>
      <div className="text-xs text-zinc-500 mb-1">Source: {cause.source_label}</div>
      {cause.chunk_index !== null && (
        <div className="text-xs text-zinc-500 mb-2">Paragraph {cause.chunk_index + 1} · effect: {cause.effect}</div>
      )}
      <div className="font-mono text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap border border-zinc-800 rounded p-3 bg-zinc-950">
        {cause.chunk_text
          ? highlightTarget(cause.chunk_text, targetValue ?? "")
          : <span className="text-zinc-500 italic">No chunk text available</span>
        }
      </div>
    </div>
  );
}
