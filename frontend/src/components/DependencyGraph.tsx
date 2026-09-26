/**
 * DependencyGraph.tsx
 *
 * Renders a directed service-dependency graph using @xyflow/react.
 *
 * Graph data (GRAPH_NODES / GRAPH_EDGES) is kept separate from rendering so
 * it can be swapped for backend data without touching this component's logic.
 *
 * Visual impact states:
 *   selected    – cyan glow, strongest highlight
 *   direct      – orange highlight (directly reachable in 1 hop)
 *   indirect    – yellow/amber, dimmer highlight (2+ hops)
 *   unaffected  – muted, reduced opacity
 */

import { useCallback, useEffect, useMemo } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  type NodeProps,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { ImpactMap, ImpactState } from "../utils/blastRadius";
import { GRAPH_NODES, GRAPH_EDGES } from "../data/graphData";
import type { ServiceNodeData } from "../types/graphTypes";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface SelectedNode {
  id: string;
  label: string;
  type: string;
}

export interface DependencyGraphProps {
  /** Called whenever the user clicks a node. */
  onNodeSelect: (node: SelectedNode) => void;
  /** Currently selected node id — drives graph highlight update. */
  selectedNodeId: string | null;
  /** Per-node impact classification from computeImpactMap. */
  impactMap: ImpactMap;
}

// ─── Type badge colours ────────────────────────────────────────────────────────

const TYPE_COLOURS: Record<string, { bg: string; text: string; border: string }> = {
  Gateway:  { bg: "rgba(34,211,238,0.12)", text: "#22d3ee", border: "rgba(34,211,238,0.35)" },
  Service:  { bg: "rgba(99,102,241,0.12)", text: "#818cf8", border: "rgba(99,102,241,0.35)" },
  Database: { bg: "rgba(52,211,153,0.12)", text: "#34d399", border: "rgba(52,211,153,0.35)" },
};

const DEFAULT_COLOUR = { bg: "rgba(148,163,184,0.1)", text: "#94a3b8", border: "rgba(148,163,184,0.3)" };

// ─── Visual state → border / background / opacity ─────────────────────────────

const STATE_STYLE: Record<
  ImpactState,
  { border: string; background: string; boxShadow: string; opacity: number }
> = {
  selected:   {
    border:     "#22d3ee",
    background: "rgba(34,211,238,0.15)",
    boxShadow:  "0 0 0 2px rgba(34,211,238,0.4)",
    opacity:    1,
  },
  direct:     {
    border:     "#f97316",
    background: "rgba(249,115,22,0.12)",
    boxShadow:  "0 0 0 2px rgba(249,115,22,0.3)",
    opacity:    1,
  },
  indirect:   {
    border:     "rgba(251,191,36,0.5)",
    background: "rgba(251,191,36,0.07)",
    boxShadow:  "none",
    opacity:    0.85,
  },
  unaffected: {
    border:     "rgba(255,255,255,0.08)",
    background: "#0f1724",
    boxShadow:  "none",
    opacity:    0.4,
  },
};

// ─── Custom node renderer ──────────────────────────────────────────────────────

function ServiceNode({
  data,
}: NodeProps<Node<ServiceNodeData & { onSelect?: () => void }>>) {
  const colour = TYPE_COLOURS[data.type] ?? DEFAULT_COLOUR;
  const vs     = STATE_STYLE[data.impactState];

  return (
    <>
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: "#475569", border: "none", width: 8, height: 8 }}
      />

      <div
      onClick={(event) => {
  event.stopPropagation();
  data.onSelect?.();
}}
        style={{
          background:  vs.background,
          border:      `1px solid ${vs.border}`,
          borderRadius: 10,
          padding:     "10px 14px",
          minWidth:    130,
          boxShadow:   vs.boxShadow,
          cursor:      "pointer",
          opacity:     vs.opacity,
          transition:  "border 0.2s, box-shadow 0.2s, background 0.2s, opacity 0.2s",
        }}
      >
        <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: "#f1f5f9", lineHeight: 1.3 }}>
          {data.label}
        </p>

        <span
          style={{
            display:     "inline-block",
            marginTop:   5,
            padding:     "2px 7px",
            borderRadius: 99,
            fontSize:    10,
            fontWeight:  500,
            background:  colour.bg,
            color:       colour.text,
            border:      `1px solid ${colour.border}`,
          }}
        >
          {data.type}
        </span>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        style={{ background: "#475569", border: "none", width: 8, height: 8 }}
      />
    </>
  );
}

// Register once outside the component to avoid React Flow re-registrations.
const NODE_TYPES = { service: ServiceNode };

// ─── Initialise nodes ────────────────────────────────────────────────────────

const INITIAL_NODES: Node<ServiceNodeData>[] = GRAPH_NODES.map((n) => ({
  ...n,
  type: "service",
}));

// ─── Inner graph (must live inside ReactFlowProvider) ────────────────────────

function DependencyGraphInner({
  onNodeSelect,
  selectedNodeId,
  impactMap,
}: DependencyGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(INITIAL_NODES);
  const [edges, , onEdgesChange]         = useEdgesState(GRAPH_EDGES);

  // Sync impactMap → node data every time the selection changes
  useEffect(() => {
  setNodes((prev) =>
    prev.map((n) => ({
      ...n,
      data: {
        ...n.data,
        impactState: selectedNodeId
          ? (impactMap[n.id] ?? "unaffected")
          : "unaffected",

        onSelect: () => {
          onNodeSelect({
            id: n.id,
            label: n.data.label,
            type: n.data.type,
          });
        },
      },
    })),
  );
}, [selectedNodeId, impactMap, setNodes, onNodeSelect]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node<ServiceNodeData>) => {
      onNodeSelect({
        id:    node.id,
        label: node.data.label,
        type:  node.data.type,
      });
    },
    [onNodeSelect],
  );

  const styledEdges = useMemo(() => {
    if (!selectedNodeId) {
      return edges.map((e) => ({
        ...e,
        style:     { stroke: "#334155", strokeWidth: 1.5 },
        markerEnd: { type: "arrowclosed" as const, color: "#334155" },
        animated:  true,
      }));
    }

    return edges.map((e) => {
      const sourceState = impactMap[e.source] ?? "unaffected";
      const targetState = impactMap[e.target] ?? "unaffected";

      // Highlight an edge if both endpoints are in the blast radius
      const isActive =
        sourceState !== "unaffected" && targetState !== "unaffected";

      const colour = isActive
        ? sourceState === "selected" || targetState === "direct"
          ? "#f97316"
          : "#fbbf24"
        : "rgba(71,85,105,0.3)";

      return {
        ...e,
        style:     { stroke: colour, strokeWidth: isActive ? 2 : 1 },
        markerEnd: { type: "arrowclosed" as const, color: colour },
        animated:  isActive,
        opacity:   isActive ? 1 : 0.25,
      };
    });
  }, [edges, selectedNodeId, impactMap]);

  return (
    <div style={{ width: "100%", height: "100%" }}>
      <ReactFlow
        nodes={nodes}
        edges={styledEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={NODE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        proOptions={{ hideAttribution: true }}
        style={{ background: "transparent" }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="rgba(255,255,255,0.04)"
        />
        <Controls
          style={{
            background:   "#0f1724",
            border:       "1px solid rgba(255,255,255,0.1)",
            borderRadius: 8,
          }}
        />
      </ReactFlow>
    </div>
  );
}

export default function DependencyGraph(props: DependencyGraphProps) {
  return <DependencyGraphInner {...props} />;
}
