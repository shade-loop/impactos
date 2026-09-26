import {
  useState,
  useCallback,
  useMemo,
  useRef,
} from "react";
import { Activity, GitBranch } from "lucide-react";

import StatCard from "./components/StatCard";
import DependencyGraph, {
  type SelectedNode,
} from "./components/DependencyGraph";
import ImpactPanel from "./components/ImpactPanel";
import IncidentInvestigation from "./components/IncidentInvestigation";
import BobInvestigation from "./components/BobInvestigation";
import {
  computeImpactMap,
  getMockImpactData,
} from "./utils/blastRadius";
import { GRAPH_NODES, GRAPH_EDGES } from "./data/graphData";
import { analyzeRepository } from "./api/analyzeApi";

// Pre-compute the node-id list (stable — same order as GRAPH_NODES)
const ALL_NODE_IDS = GRAPH_NODES.map((n) => n.id);

function App() {
  const [selected, setSelected] =
    useState<SelectedNode | null>(null);
  const [analysis, setAnalysis] =
  useState<Awaited<ReturnType<typeof analyzeRepository>> | null>(null);

  const bobSectionRef = useRef<HTMLElement | null>(null);

  const handleNodeSelect = useCallback(
    (node: SelectedNode) => {
      setSelected(node);
    },
    [],
  );

  const handleBackendAnalysis = async () => {
  try {
    const result = await analyzeRepository({
      repo_path: "tests/fixtures",
      changed_files: ["sample_app/utils.py"],
    });

    setAnalysis(result);
  } catch (error) {
    console.error("ImpactOS analysis failed:", error);
  }
};

  // Recompute impact map whenever the selected node changes
  const impactMap = useMemo(() => {
    if (!selected) return {};

    return computeImpactMap(
      selected.id,
      ALL_NODE_IDS,
      GRAPH_EDGES,
    );
  }, [selected]);

  // Derive mock impact data
  const impactData = useMemo(() => {
    if (!selected) return null;

    return getMockImpactData(
      selected.id,
      selected.label,
      selected.type,
      impactMap,
    );
  }, [selected, impactMap]);

  // Scroll to Bob investigation
  const handleInvestigate = useCallback(() => {
    bobSectionRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
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
              <span className="text-slate-500">
                {" "}can break.
              </span>
            </h2>

            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-400">
              ImpactOS analyzes your repository, maps dependencies,
              predicts change blast radius, and helps investigate
              production incidents before they become expensive
              problems.
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
          {/* Dependency graph */}
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

            <div className="h-[340px]">
              <DependencyGraph
                onNodeSelect={handleNodeSelect}
                selectedNodeId={selected?.id ?? null}
                impactMap={impactMap}
              />
            </div>
          </div>

          {/* Change Impact */}
          <ImpactPanel
            selected={selected}
            impact={impactData}
            onInvestigate={handleInvestigate}
          />
          <div className="mt-4 rounded-xl border border-cyan-500/20 bg-cyan-500/[0.04] p-4">
  <div className="flex items-center justify-between">
    <div>
      <p className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
        Backend Analyzer
      </p>

      <p className="mt-1 text-xs text-slate-500">
        Repository analysis from the ImpactOS Python engine
      </p>
    </div>

    <button
      onClick={handleBackendAnalysis}
      className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-xs font-medium text-cyan-300 transition hover:bg-cyan-500/20"
    >
      {analysis ? "Run Again" : "Run Analysis"}
    </button>
  </div>

  {analysis && (
    <div className="mt-4 grid grid-cols-2 gap-2">
      <div className="rounded-lg border border-white/10 bg-white/[0.025] p-3">
        <p className="text-[10px] uppercase tracking-wide text-slate-500">
          Risk
        </p>
        <p className="mt-1 text-lg font-semibold text-orange-400">
          {analysis.risk_level}
        </p>
      </div>

      <div className="rounded-lg border border-white/10 bg-white/[0.025] p-3">
        <p className="text-[10px] uppercase tracking-wide text-slate-500">
          Impact Score
        </p>
        <p className="mt-1 text-lg font-semibold text-cyan-400">
          {analysis.impact_score}
        </p>
      </div>

      <div className="rounded-lg border border-white/10 bg-white/[0.025] p-3">
        <p className="text-[10px] uppercase tracking-wide text-slate-500">
          Direct
        </p>
        <p className="mt-1 text-lg font-semibold text-slate-200">
          {analysis.direct_count}
        </p>
      </div>

      <div className="rounded-lg border border-white/10 bg-white/[0.025] p-3">
        <p className="text-[10px] uppercase tracking-wide text-slate-500">
          Indirect
        </p>
        <p className="mt-1 text-lg font-semibold text-slate-200">
          {analysis.indirect_count}
        </p>
      </div>
    </div>
  )}
</div>

          
        </section>

        {/* B4 — Incident Investigation */}
        <section className="mt-8">
          <IncidentInvestigation
            onInvestigate={handleInvestigate}
          />
        </section>

        {/* B5 — Bob Investigation */}
        <section
          ref={bobSectionRef}
          className="mt-8 scroll-mt-6"
        >
          <BobInvestigation
            onContinue={() => {
              // B6 will connect this workflow to the real
              // backend analysis endpoint.
              console.log(
                "Continue Bob investigation",
              );
            }}
          />
        </section>
      </main>
    </div>
  );
}

export default App;