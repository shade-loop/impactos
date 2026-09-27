import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FileCode2,
  GitBranch,
  Search,
  ShieldAlert,
  Sparkles,
  TriangleAlert,
} from "lucide-react";

import type { AnalyzeData } from "../api/analyzeApi";

interface BobInvestigationProps {
  onContinue?: () => void;
  /** Live analysis result from the Backend Analyzer, or null if not yet run. */
  analysis?: AnalyzeData | null;
}

// ── Static demo content (graph topology) ─────────────────────────────────────
// The dependency path below reflects the static graph rendered in the
// Dependency Graph panel (graphData.ts). It is NOT derived from a real incident.
const DEMO_DEPENDENCY_PATH = [
  { name: "UserService", color: "#a78bfa" },
  { name: "CheckoutService", color: "#f87171" },
  { name: "PaymentService", color: "#fbbf24" },
];

const DEMO_DEPTH_CARDS = [
  { label: "CheckoutService", value: "Depth 1", accent: "#f97316" },
  { label: "PaymentService", value: "Depth 2", accent: "#fbbf24" },
];

// ── Evidence gaps that always apply ──────────────────────────────────────────
const STATIC_EVIDENCE_GAPS = [
  "No APM, telemetry, deployment, or service-mesh data exists in the repository.",
  "Incident IDs, deployment timestamps, and commit hashes are demo placeholders.",
  "Root-cause confirmation requires real operational data sources.",
];

export default function BobInvestigation({
  onContinue,
  analysis,
}: BobInvestigationProps) {
  const hasAnalysis = analysis != null;

  // Build "Supported by Repository" findings from live API data when available,
  // otherwise fall back to static demo findings grounded in the graph topology.
  const supportedFindings: string[] = hasAnalysis
    ? buildSupportedFindings(analysis!)
    : [
        "The repository contains a UserService → CheckoutService → PaymentService dependency path.",
        "The blast-radius traversal identifies CheckoutService as depth 1 from UserService.",
        "PaymentService is reachable at depth 2 from UserService.",
        "UserService also directly affects OrdersService.",
      ];

  // Build recommended investigation steps from live recommendations when available.
  const nextSteps: string[] = hasAnalysis
    ? buildNextSteps(analysis!)
    : [
        "Inspect real git history for the UserService change.",
        "Compare the deployment timestamp with the incident start.",
        "Inspect CheckoutService telemetry around the incident window.",
        "Check OrdersService for correlated degradation.",
        "Connect real incident and telemetry sources.",
      ];

  return (
    <section
      className="overflow-hidden rounded-xl border border-cyan-400/10 bg-white/[0.025]"
      style={{
        boxShadow: "0 10px 40px rgba(0,0,0,0.16)",
      }}
    >
      {/* ── Demo data notice ─────────────────────────────────────────────── */}
      <div
        className="flex items-center gap-2 border-b border-amber-400/20 px-5 py-2.5"
        style={{ background: "rgba(251,191,36,0.04)" }}
      >
        <AlertTriangle className="h-3 w-3 shrink-0 text-amber-400" />
        <span className="text-[10px] font-medium text-amber-400/80">
          {hasAnalysis
            ? "Supported findings and recommendations are sourced from the live ImpactOS analysis. Incident data and dependency-path visualization remain demo placeholders."
            : "No analysis run yet. All findings below are static demo data. Run the Backend Analyzer to populate live results."}
        </span>
      </div>

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div className="border-b border-white/10 px-5 py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div
              className="flex h-8 w-8 items-center justify-center rounded-lg"
              style={{
                background: "rgba(34,211,238,0.08)",
                border: "1px solid rgba(34,211,238,0.16)",
              }}
            >
              <Sparkles className="h-4 w-4 text-cyan-400" />
            </div>

            <div>
              <h2 className="text-sm font-semibold text-slate-100">
                Bob Investigation
              </h2>

              <p className="mt-0.5 text-[10px] uppercase tracking-[0.12em] text-slate-600">
                Repository-aware incident analysis
              </p>
            </div>
          </div>

          <span
            className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider"
            style={
              hasAnalysis
                ? {
                    background: "rgba(52,211,153,0.08)",
                    color: "#34d399",
                    border: "1px solid rgba(52,211,153,0.18)",
                  }
                : {
                    background: "rgba(100,116,139,0.08)",
                    color: "#94a3b8",
                    border: "1px solid rgba(100,116,139,0.18)",
                  }
            }
          >
            <CheckCircle2 className="h-3 w-3" />
            {hasAnalysis ? "Live analysis" : "Awaiting analysis"}
          </span>
        </div>
      </div>

      {/* ── Incident summary ─────────────────────────────────────────────── */}
      <div className="border-b border-white/10 px-5 py-5">
        {hasAnalysis ? (
          /* Live analysis summary */
          <div
            className="rounded-xl p-4"
            style={{
              background:
                "linear-gradient(135deg, rgba(34,211,238,0.05), rgba(255,255,255,0.012))",
              border: "1px solid rgba(34,211,238,0.13)",
            }}
          >
            <div className="flex items-start gap-3">
              <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-cyan-400" />

              <div>
                <p className="text-sm font-semibold text-slate-100">
                  Repository analysis complete
                </p>

                <p className="mt-1 text-xs leading-5 text-slate-400">
                  Analyzed{" "}
                  <span className="font-medium text-slate-200">
                    {analysis!.changed_files.length} file
                    {analysis!.changed_files.length !== 1 ? "s" : ""}
                  </span>{" "}
                  ({analysis!.changed_modules.join(", ")}). Risk:{" "}
                  <span className="font-medium text-orange-300">
                    {analysis!.risk_level}
                  </span>
                  . Impact score:{" "}
                  <span className="font-medium text-cyan-300">
                    {analysis!.impact_score}
                  </span>
                  . {analysis!.direct_count} direct and{" "}
                  {analysis!.indirect_count} indirect modules affected.
                </p>
              </div>
            </div>
          </div>
        ) : (
          /* Demo incident badge — clearly labeled */
          <>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                INC-1042 (demo)
              </span>

              <span className="text-slate-700">•</span>

              <span className="text-xs font-medium text-slate-300">
                Checkout API latency spike (demo)
              </span>
            </div>

            <div
              className="mt-4 rounded-xl p-4"
              style={{
                background:
                  "linear-gradient(135deg, rgba(34,211,238,0.05), rgba(255,255,255,0.012))",
                border: "1px solid rgba(34,211,238,0.13)",
              }}
            >
              <div className="flex items-start gap-3">
                <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-cyan-400" />

                <div>
                  <p className="text-sm font-semibold text-slate-100">
                    Candidate contributor identified (demo)
                  </p>

                  <p className="mt-1 text-xs leading-5 text-slate-400">
                    The repository supports the dependency relationship between
                    UserService, CheckoutService, and PaymentService, but does
                    not contain enough real operational evidence to confirm
                    UserService as the root cause.
                  </p>
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* ── Main investigation grid ───────────────────────────────────────── */}
      <div className="grid lg:grid-cols-2">
        {/* Supported findings */}
        <div className="border-b border-white/10 p-5 lg:border-b-0 lg:border-r">
          <SectionHeader
            icon={<CheckCircle2 className="h-3 w-3 text-emerald-400" />}
            title={hasAnalysis ? "Supported by Repository (live)" : "Supported by Repository (demo)"}
          />

          <div className="mt-4 space-y-2">
            {supportedFindings.map((finding) => (
              <div
                key={finding}
                className="flex items-start gap-2.5 rounded-lg px-3 py-2.5"
                style={{
                  background: "rgba(52,211,153,0.025)",
                  border: "1px solid rgba(52,211,153,0.08)",
                }}
              >
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" />

                <span className="text-xs leading-5 text-slate-400">
                  {finding}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Dependency path — static graph visualization */}
        <div className="border-b border-white/10 p-5">
          <SectionHeader
            icon={<GitBranch className="h-3 w-3 text-cyan-400" />}
            title="Dependency Evidence (graph topology)"
          />

          <p className="mt-1 text-[10px] leading-4 text-slate-600">
            Static topology from graphData.ts — not derived from the analyzed repository path.
          </p>

          <div
            className="mt-3 rounded-xl p-4"
            style={{
              background: "rgba(255,255,255,0.018)",
              border: "1px solid rgba(255,255,255,0.07)",
            }}
          >
            <div className="flex flex-wrap items-center gap-2">
              {DEMO_DEPENDENCY_PATH.map((svc, i) => (
                <span key={svc.name} className="flex items-center gap-2">
                  {i > 0 && (
                    <ArrowRight className="h-3.5 w-3.5 text-slate-600" />
                  )}
                  <ServiceNode name={svc.name} color={svc.color} />
                </span>
              ))}
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2">
              {DEMO_DEPTH_CARDS.map((card) => (
                <DepthCard
                  key={card.label}
                  label={card.label}
                  value={card.value}
                  accent={card.accent}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Evidence gaps */}
        <div className="border-b border-white/10 p-5 lg:border-b-0 lg:border-r">
          <SectionHeader
            icon={<TriangleAlert className="h-3 w-3 text-amber-400" />}
            title="Evidence Gaps"
          />

          <p className="mt-2 text-[10px] leading-4 text-slate-600">
            These data sources are not available in the repository and cannot be
            verified.
          </p>

          <div className="mt-4 space-y-2">
            {STATIC_EVIDENCE_GAPS.map((gap) => (
              <div
                key={gap}
                className="flex items-start gap-2.5 rounded-lg px-3 py-2.5"
                style={{
                  background: "rgba(251,191,36,0.025)",
                  border: "1px solid rgba(251,191,36,0.08)",
                }}
              >
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" />

                <span className="text-xs leading-5 text-slate-400">
                  {gap}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Live evidence from API or static observation */}
        <div className="p-5">
          <SectionHeader
            icon={<Search className="h-3 w-3 text-orange-400" />}
            title={hasAnalysis ? "API Evidence (live)" : "Important Observation (demo)"}
          />

          {hasAnalysis ? (
            <div className="mt-4 space-y-2">
              {analysis!.evidence.length > 0 ? (
                analysis!.evidence.map((item) => (
                  <div
                    key={item}
                    className="flex items-start gap-2.5 rounded-lg px-3 py-2.5"
                    style={{
                      background:
                        "linear-gradient(135deg, rgba(249,115,22,0.05), rgba(255,255,255,0.012))",
                      border: "1px solid rgba(249,115,22,0.13)",
                    }}
                  >
                    <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-orange-400" />
                    <span className="text-xs leading-5 text-slate-300">
                      {item}
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-600">
                  No evidence statements returned for this analysis.
                </p>
              )}
            </div>
          ) : (
            <div
              className="mt-4 rounded-xl p-4"
              style={{
                background:
                  "linear-gradient(135deg, rgba(249,115,22,0.05), rgba(255,255,255,0.012))",
                border: "1px solid rgba(249,115,22,0.13)",
              }}
            >
              <div className="flex items-start gap-2.5">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-orange-400" />

                <div>
                  <p className="text-xs font-semibold text-slate-200">
                    OrdersService is also directly downstream. (demo)
                  </p>

                  <p className="mt-2 text-xs leading-5 text-slate-500">
                    If UserService regressed, OrdersService would also be
                    affected through the same direct dependency relationship.
                    This is inferred from the static graph topology only.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Next steps ───────────────────────────────────────────────────── */}
      <div className="border-t border-white/10 p-5">
        <SectionHeader
          icon={<FileCode2 className="h-3 w-3 text-violet-400" />}
          title={hasAnalysis ? "Recommended Investigation (from API)" : "Recommended Investigation (demo)"}
        />

        <div className="mt-4 grid gap-2 md:grid-cols-2">
          {nextSteps.map((step, index) => (
            <div
              key={step}
              className="flex items-start gap-3 rounded-lg px-3 py-2.5"
              style={{
                background: "rgba(255,255,255,0.018)",
                border: "1px solid rgba(255,255,255,0.06)",
              }}
            >
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-violet-400/10 text-[9px] font-semibold text-violet-400">
                {index + 1}
              </span>

              <span className="text-xs leading-5 text-slate-400">
                {step}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 border-t border-white/10 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-3.5 w-3.5 text-cyan-400" />

          <span className="text-[10px] text-slate-600">
            {hasAnalysis
              ? "Findings generated from live repository analysis."
              : "Run the Backend Analyzer above to populate live findings."}
          </span>
        </div>

        <button
          type="button"
          onClick={onContinue}
          className="inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold transition hover:brightness-110"
          style={{
            background: "#22d3ee",
            color: "#061116",
            boxShadow: "0 0 18px rgba(34,211,238,0.1)",
          }}
        >
          <Search className="h-3.5 w-3.5" />
          Continue investigation
          <ArrowRight className="h-3 w-3" />
        </button>
      </div>
    </section>
  );
}

// ── Helper functions ──────────────────────────────────────────────────────────

function buildSupportedFindings(analysis: AnalyzeData): string[] {
  const findings: string[] = [];

  if (analysis.changed_modules.length > 0) {
    findings.push(
      `Changed module(s): ${analysis.changed_modules.join(", ")}.`
    );
  }

  if (analysis.direct_count > 0) {
    findings.push(
      `${analysis.direct_count} module${analysis.direct_count !== 1 ? "s" : ""} directly depend on the changed module(s): ${analysis.direct_affected.join(", ")}.`
    );
  }

  if (analysis.indirect_count > 0) {
    findings.push(
      `${analysis.indirect_count} module${analysis.indirect_count !== 1 ? "s" : ""} indirectly affected: ${analysis.indirect_affected.join(", ")}.`
    );
  }

  if (analysis.max_depth > 0) {
    findings.push(
      `Change propagates through ${analysis.max_depth} dependency level${analysis.max_depth !== 1 ? "s" : ""}.`
    );
  }

  if (findings.length === 0) {
    findings.push("No downstream dependents detected — change is isolated.");
  }

  return findings;
}

function buildNextSteps(analysis: AnalyzeData): string[] {
  if (analysis.recommendations.length === 0) {
    return ["No recommendations generated for this analysis."];
  }

  // Show unique action+module pairs, deduplicated and limited to 6 for layout.
  const seen = new Set<string>();
  const steps: string[] = [];
  for (const rec of analysis.recommendations) {
    const key = `${rec.action} — ${rec.module}`;
    if (!seen.has(key)) {
      seen.add(key);
      steps.push(`[${rec.priority}] ${rec.action} — ${rec.module}`);
    }
    if (steps.length >= 6) break;
  }
  return steps;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionHeader({
  icon,
  title,
}: {
  icon: React.ReactNode;
  title: string;
}) {
  return (
    <div className="flex items-center gap-1.5">
      {icon}

      <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400">
        {title}
      </span>
    </div>
  );
}

function ServiceNode({
  name,
  color,
}: {
  name: string;
  color: string;
}) {
  return (
    <span
      className="rounded-md px-2.5 py-1.5 text-[10px] font-medium"
      style={{
        color,
        background: `${color}0D`,
        border: `1px solid ${color}30`,
      }}
    >
      {name}
    </span>
  );
}

function DepthCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent: string;
}) {
  return (
    <div
      className="rounded-md px-3 py-2"
      style={{
        background: `${accent}08`,
        border: `1px solid ${accent}18`,
      }}
    >
      <p className="text-[9px] uppercase tracking-wider text-slate-600">
        {label}
      </p>

      <p
        className="mt-1 text-xs font-semibold"
        style={{ color: accent }}
      >
        {value}
      </p>
    </div>
  );
}
