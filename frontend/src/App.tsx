import { useState, useCallback, useMemo } from "react";
import { Activity, GitBranch } from "lucide-react";

import StatCard from "./components/StatCard";
import DependencyGraph, {
  type SelectedNode,
} from "./components/DependencyGraph";
import ImpactPanel from "./components/ImpactPanel";
import IncidentInvestigation from "./components/IncidentInvestigation";
import { computeImpactMap, getMockImpactData } from "./utils/blastRadius";
import { GRAPH_NODES, GRAPH_EDGES } from "./data/graphData";

// Pre-compute the node-id list (stable — same order as GRAPH_NODES)
const ALL_NODE_IDS = GRAPH_NODES.map((n) => n.id);

function App() {
  const [selected, setSelected] = useState<SelectedNode | null>(null);

  const handleNodeSelect = useCallback((node: SelectedNode) => {
    setSelected(node);
  }, []);

  // Recompute impact map whenever the selected node changes
  const impactMap = useMemo(() => {
    if (!selected) return {};
    return computeImpactMap(selected.id, ALL_NODE_IDS, GRAPH_EDGES);
  }, [selected]);

  // Derive mock impact data (deterministic; no randomness)
  const impactData = useMemo(() => {
    if (!selected) return null;

    return getMockImpactData(
      selected.id,
      selected.label,
      selected.type,
      impactMap,
    );
  }, [selected, impactMap]);

  const handleInvestigate = useCallback(() => {
    // Placeholder — Builder A will wire this to Bob AI.
    // B5 can turn this into the Bob investigation workflow.
  }, []);

  return (
    <div className="min-h-screen bg-[#080b12] text-slate-100">
      {/* Header */}
      <header className="border-b border-white/10 bg-[#0b0f17]/80">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-500/10">
              <Activity className="h-5 w-5 text-cyan-400" />
            </div>

            <div>
              <h1 className="text-lg font-semibold tracking-tight">
                ImpactOS
              </h1>

              <p className="text-xs text-slate-500">
                Developer impact intelligence
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Repository connected
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="mx-auto max-w-7xl px-6 py-10">
        {/* Hero */}
        <section className="mb-10">
          <div className="max-w-3xl">
            <p className="mb-3 text-sm font-medium text-cyan-400">
              CHANGE IMPACT INTELLIGENCE
            </p>

            <h2 className="text-4xl font-semibold tracking-tight text-white">
              Know what your code change
              <span className="text-slate-500"> can break.</span>
            </h2>

            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-400">
              ImpactOS analyzes your repository, maps dependencies, predicts
              change blast radius, and helps investigate production incidents
              before they become expensive problems.
            </p>
          </div>
        </section>

        {/* Stats */}
        <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard
            label="Files"
            value="247"
            description="Analyzed"
          />

          <StatCard
            label="Functions"
            value="1,842"
            description="Indexed"
          />

          <StatCard
            label="Tests"
            value="86"
            description="Detected"
          />

          <StatCard
            label="Services"
            value="12"
            description="Mapped"
          />
        </section>

        {/* Dependency + Impact */}
        <section className="mt-6 grid gap-6 lg:grid-cols-3">
          {/* Dependency graph panel */}
          <div className="min-h-[420px] rounded-xl border border-white/10 bg-white/[0.03] lg:col-span-2">
            <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
              <div>
                <h3 className="font-medium text-white">
                  Dependency Graph
                </h3>

                <p className="mt-1 text-xs text-slate-500">
                  Repository architecture
                </p>
              </div>

              <GitBranch className="h-5 w-5 text-slate-500" />
            </div>

            {/* Graph canvas */}
            <div className="h-[340px]">
              <DependencyGraph
                onNodeSelect={handleNodeSelect}
                selectedNodeId={selected?.id ?? null}
                impactMap={impactMap}
              />
            </div>
          </div>

          {/* Change Impact panel */}
          <ImpactPanel
            selected={selected}
            impact={impactData}
            onInvestigate={handleInvestigate}
          />
        </section>

        {/* ────────────────────────────────────────────────────────────────
            B4 — Incident Investigation
        ──────────────────────────────────────────────────────────────── */}

        <section className="mt-8">
          <IncidentInvestigation
            onInvestigate={handleInvestigate}
          />
        </section>
      </main>
    </div>
  );
}

export default App;