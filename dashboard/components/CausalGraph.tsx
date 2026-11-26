"use client";

import { useEffect, useState, useCallback } from "react";
import {
  ReactFlow,
  type Node,
  type Edge,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

interface CauseInfo {
  source_label: string;
  chunk_index: number | null;
  chunk_text: string | null;
  effect: string;
}

interface VerdictData {
  decision: string;
  attack_detected: boolean;
  unstable: boolean;
  causes: CauseInfo[];
  reruns: Array<{ variant: string; tool_calls: Array<{ name: string; arguments: string }> }>;
  latency_ms: number;
}

interface Props {
  sessionId: string;
  userTask: string;
  toolCallName: string;
  toolCallArgs: string;
  verdict: VerdictData;
  onSelectChunk?: (cause: CauseInfo) => void;
}

const STAGGER = 300;

export function CausalGraph({ sessionId, userTask, toolCallName, toolCallArgs, verdict, onSelectChunk }: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [visibleCount, setVisibleCount] = useState(0);

  const isBlocked = verdict.decision === "BLOCK";

  useEffect(() => {
    // Build nodes
    const allNodes: Node[] = [];
    const allEdges: Edge[] = [];

    // User prompt node
    allNodes.push({
      id: "user",
      position: { x: 0, y: 120 },
      data: { label: `👤 User\n${userTask.slice(0, 60)}${userTask.length > 60 ? "…" : ""}` },
      style: {
        background: "#052e16",
        border: "1px solid #16a34a",
        color: "#86efac",
        borderRadius: 8,
        fontSize: 11,
        fontFamily: "monospace",
        padding: "8px 12px",
        maxWidth: 160,
        whiteSpace: "pre-wrap",
      },
    });

    // Source nodes
    const sources = verdict.causes.length > 0
      ? verdict.causes
      : [{ source_label: "web_fetch:unknown", chunk_index: null, chunk_text: null, effect: "none" }];

    sources.forEach((cause, i) => {
      const isCause = cause.effect !== "none";
      allNodes.push({
        id: `src-${i}`,
        position: { x: 220, y: i * 160 + 20 },
        data: { label: `🌐 ${cause.source_label.replace(/^web_fetch:/, "")}` },
        style: {
          background: isCause ? "#1c0a0a" : "#18181b",
          border: `1px solid ${isCause ? "#ef4444" : "#52525b"}`,
          color: isCause ? "#fca5a5" : "#a1a1aa",
          borderRadius: 8,
          fontSize: 10,
          fontFamily: "monospace",
          padding: "8px 12px",
          maxWidth: 180,
          cursor: isCause ? "pointer" : "default",
        },
      });

      allEdges.push({
        id: `e-user-src-${i}`,
        source: "user",
        target: `src-${i}`,
        style: { stroke: "#52525b", strokeWidth: 1 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#52525b" },
      });

      // Paragraph chunk node if attributed
      if (cause.chunk_index !== null && cause.chunk_text) {
        const chunkId = `chunk-${i}`;
        allNodes.push({
          id: chunkId,
          position: { x: 460, y: i * 160 + 20 },
          data: {
            label: `¶${cause.chunk_index + 1}  ${cause.chunk_text.slice(0, 80)}${cause.chunk_text.length > 80 ? "…" : ""}`,
            cause,
          },
          style: {
            background: "#1c0a0a",
            border: "1px solid #dc2626",
            color: "#fca5a5",
            borderRadius: 8,
            fontSize: 10,
            fontFamily: "monospace",
            padding: "8px 12px",
            maxWidth: 200,
            cursor: "pointer",
            whiteSpace: "pre-wrap",
          },
        });

        allEdges.push({
          id: `e-src-chunk-${i}`,
          source: `src-${i}`,
          target: chunkId,
          label: cause.effect === "removes_call" ? "removes call" : "changes target",
          labelStyle: { fill: "#ef4444", fontSize: 9, fontFamily: "monospace" },
          style: { stroke: "#ef4444", strokeWidth: 2, strokeDasharray: "4 2" },
          markerEnd: { type: MarkerType.ArrowClosed, color: "#ef4444" },
          animated: true,
        });

        // Edge from chunk to tool call
        allEdges.push({
          id: `e-chunk-tc-${i}`,
          source: chunkId,
          target: "toolcall",
          style: { stroke: "#dc2626", strokeWidth: 2 },
          markerEnd: { type: MarkerType.ArrowClosed, color: "#dc2626" },
          animated: true,
        });
      } else if (isCause) {
        allEdges.push({
          id: `e-src-tc-${i}`,
          source: `src-${i}`,
          target: "toolcall",
          label: cause.effect,
          labelStyle: { fill: "#ef4444", fontSize: 9, fontFamily: "monospace" },
          style: { stroke: "#ef4444", strokeWidth: 2 },
          markerEnd: { type: MarkerType.ArrowClosed, color: "#ef4444" },
          animated: true,
        });
      }
    });

    // Tool call node
    const tcX = verdict.causes.some(c => c.chunk_index !== null) ? 720 : 500;
    const tcColor = isBlocked ? "#dc2626" : verdict.decision === "WARN" ? "#d97706" : "#16a34a";
    const tcBg = isBlocked ? "#1c0a0a" : verdict.decision === "WARN" ? "#1c1300" : "#052e16";
    allNodes.push({
      id: "toolcall",
      position: { x: tcX, y: 80 },
      data: {
        label: `${isBlocked ? "🚫 BLOCKED" : verdict.decision === "WARN" ? "⚠️ WARN" : "✅ ALLOW"}\n${toolCallName}(${toolCallArgs.slice(0, 40)}${toolCallArgs.length > 40 ? "…" : ""})`,
      },
      style: {
        background: tcBg,
        border: `2px solid ${tcColor}`,
        color: tcColor === "#dc2626" ? "#fca5a5" : tcColor === "#d97706" ? "#fcd34d" : "#86efac",
        borderRadius: 8,
        fontSize: 11,
        fontFamily: "monospace",
        padding: "10px 14px",
        maxWidth: 200,
        fontWeight: "bold",
        whiteSpace: "pre-wrap",
      },
    });

    setNodes(allNodes.map(n => ({ ...n, hidden: true })) as Node[]);
    setEdges(allEdges.map(e => ({ ...e, hidden: true })) as Edge[]);
    setVisibleCount(0);

    // Stagger animation
    allNodes.forEach((_, idx) => {
      setTimeout(() => {
        setVisibleCount(idx + 1);
      }, idx * STAGGER);
    });
  }, [verdict, toolCallName, toolCallArgs, userTask, isBlocked]);

  // Reveal nodes one by one
  useEffect(() => {
    setNodes(prev => (prev as Node[]).map((n, i) => ({ ...n, hidden: i >= visibleCount })) as Node[]);
    setEdges(prev => (prev as Edge[]).map((e, i) => ({ ...e, hidden: i >= visibleCount })) as Edge[]);
  }, [visibleCount]);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    if (node.data?.cause && onSelectChunk) {
      onSelectChunk(node.data.cause as CauseInfo);
    }
  }, [onSelectChunk]);

  return (
    <div className="h-72 w-full rounded-lg border border-zinc-800 overflow-hidden bg-zinc-950">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#27272a" gap={16} />
        <Controls style={{ background: "#18181b", border: "1px solid #3f3f46" }} />
      </ReactFlow>
    </div>
  );
}
