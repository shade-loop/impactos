/**
 * ImpactPanel.tsx
 *
 * Change Impact Report panel for ImpactOS.
 * Accepts ImpactData + SelectedNode via props so the data source can be
 * swapped for a real backend payload without touching this file.
 *
 * Subcomponents (all in this file, all pure):
 *   RiskBadge        – colour-coded risk level pill
 *   ImpactMetric     – single numbered metric tile
 *   ImpactSection    – labelled section wrapper
 *   VerificationItem – checkbox row in the verification checklist
 */

import { useState } from "react";
import {
  AlertTriangle,
  Bot,
  CheckSquare,
  ChevronRight,
  CircleDot,
  ClipboardCheck,
  Lightbulb,
  ShieldAlert,
  Square,
  TriangleAlert,
  Zap,
} from "lucide-react";
import type { ImpactData } from "../utils/blastRadius";
import type { SelectedNode } from "./DependencyGraph";

// ─── Public prop types ────────────────────────────────────────────────────────

export interface ImpactPanelProps {
  /** The node currently selected in the graph, or null when nothing is selected. */
  selected: SelectedNode | null;
  /** Full impact report for the selected node, or null when nothing is selected. */
  impact: ImpactData | null;
  /** Called when the user clicks "Investigate with Bob". */
  onInvestigate: () => void;
}

// ─── RiskBadge ────────────────────────────────────────────────────────────────

interface RiskBadgeProps {
  risk: ImpactData["risk"];
  large?: boolean;
}

const RISK_CONFIG: Record<
  ImpactData["risk"],
  { label: string; bg: string; text: string; border: string; dot: string }
> = {
  HIGH:   { label: "HIGH RISK",   bg: "rgba(239,68,68,0.12)",  text: "#f87171", border: "rgba(239,68,68,0.35)",  dot: "#ef4444" },
  MEDIUM: { label: "MEDIUM RISK", bg: "rgba(251,146,60,0.12)", text: "#fb923c", border: "rgba(251,146,60,0.35)", dot: "#f97316" },
  LOW:    { label: "LOW RISK",    bg: "rgba(52,211,153,0.12)", text: "#34d399", border: "rgba(52,211,153,0.35)", dot: "#10b981" },
};

function RiskBadge({ risk, large = false }: RiskBadgeProps) {
  const c = RISK_CONFIG[risk];
  return (
    <span
      style={{
        display:      "inline-flex",
        alignItems:   "center",
        gap:          6,
        padding:      large ? "5px 12px" : "3px 9px",
        borderRadius: 99,
        fontSize:     large ? 12 : 10,
        fontWeight:   700,
        letterSpacing: "0.05em",
        background:   c.bg,
        color:        c.text,
        border:       `1px solid ${c.border}`,
        whiteSpace:   "nowrap",
      }}
    >
      <span
        style={{
          width: large ? 8 : 6,
          height: large ? 8 : 6,
          borderRadius: "50%",
          background: c.dot,
          display: "inline-block",
          flexShrink: 0,
        }}
      />
      {c.label}
    </span>
  );
}

// ─── ImpactMetric ─────────────────────────────────────────────────────────────

interface ImpactMetricProps {
  label: string;
  value: number;
  highlight?: boolean;
}

function ImpactMetric({ label, value, highlight = false }: ImpactMetricProps) {
  return (
    <div
      className="rounded-lg p-3 text-center"
      style={{
        background: highlight ? "rgba(34,211,238,0.06)" : "rgba(255,255,255,0.03)",
        border:     `1px solid ${highlight ? "rgba(34,211,238,0.18)" : "rgba(255,255,255,0.07)"}`,
      }}
    >
      <p
        className="text-xl font-bold leading-none"
        style={{ color: highlight ? "#22d3ee" : "#f1f5f9" }}
      >
        {value}
      </p>
      <p className="mt-1.5 text-[10px] leading-tight text-slate-500">{label}</p>
    </div>
  );
}

// ─── ImpactSection ────────────────────────────────────────────────────────────

interface ImpactSectionProps {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}

function ImpactSection({ icon, title, children }: ImpactSectionProps) {
  return (
    <div className="mb-4">
      <div className="mb-2 flex items-center gap-1.5">
        {icon}
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </span>
      </div>
      {children}
    </div>
  );
}

// ─── VerificationItem ─────────────────────────────────────────────────────────

interface VerificationItemProps {
  label: string;
  checked: boolean;
  onToggle: () => void;
}

function VerificationItem({ label, checked, onToggle }: VerificationItemProps) {
  return (
    <button
      onClick={onToggle}
      className="flex w-full items-center gap-2.5 rounded px-1 py-1.5 text-left transition hover:bg-white/5"
    >
      {checked
        ? <CheckSquare className="h-3.5 w-3.5 shrink-0 text-emerald-400" />
        : <Square      className="h-3.5 w-3.5 shrink-0 text-slate-600"   />}
      <span
        className="text-xs leading-snug"
        style={{ color: checked ? "#94a3b8" : "#cbd5e1", textDecoration: checked ? "line-through" : "none" }}
      >
        {label}
      </span>
    </button>
  );
}

// ─── Blast radius group ───────────────────────────────────────────────────────

interface ImpactGroupProps {
  label: string;
  items: string[];
  dotColor: string;
}

function ImpactGroup({ label, items, dotColor }: ImpactGroupProps) {
  if (items.length === 0) return null;
  return (
    <div className="mb-2">
      <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-slate-500">
        {label}
      </p>
      <div className="space-y-0.5">
        {items.map((name) => (
          <div key={name} className="flex items-center gap-2 py-0.5">
            <ChevronRight className="h-3 w-3 shrink-0 text-slate-600" />
            <span
              className="text-xs"
              style={{ color: dotColor }}
            >
              {name}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main component ────────────────────────────────────────────────────────────

export default function ImpactPanel({ selected, impact, onInvestigate }: ImpactPanelProps) {
  // Local checklist state — tracks which verification steps the user has ticked
  const [checked, setChecked] = useState<Record<string, boolean>>({});

  // Reset checklist whenever a different node is selected
  const stepKey = (step: string) => `${selected?.id ?? ""}::${step}`;
  const toggle  = (step: string) =>
    setChecked((prev) => ({ ...prev, [stepKey(step)]: !prev[stepKey(step)] }));

  // Bob investigation state
  const [investigating, setInvestigating] = useState(false);
  const handleInvestigate = () => {
    setInvestigating(true);
    onInvestigate();
    // Reset the "prepared" state after 3 s so the button is reusable
    setTimeout(() => setInvestigating(false), 3000);
  };

  return (
    <div
      className="flex flex-col rounded-xl border border-white/10 bg-white/[0.03]"
      style={{ minHeight: 420 }}
    >
      {/* ── Panel header ─────────────────────────────────────────────── */}
      <div className="flex-shrink-0 border-b border-white/10 px-5 py-4">
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-4 w-4 text-orange-400" />
          <h3 className="text-sm font-semibold">Change Impact</h3>
        </div>
        <p className="mt-0.5 text-xs text-slate-500">
          {selected ? `Analyzing ${selected.label}` : "Select a component to analyze"}
        </p>
      </div>

      {/* ── Scrollable body ───────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-5 py-4" style={{ scrollbarWidth: "thin" }}>

        {/* ── Empty state ───────────────────────────────────────────── */}
        {!selected && (
          <div className="rounded-lg border border-orange-400/20 bg-orange-400/5 p-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-orange-400" />
              <span className="text-sm font-medium text-orange-300">Awaiting analysis</span>
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-500">
              Choose a component from the dependency graph to calculate its
              potential blast radius.
            </p>
          </div>
        )}

        {/* ── Populated state ───────────────────────────────────────── */}
        {selected && impact && (
          <>
            {/* HEADER — component name / type / risk */}
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-1.5">
                  <Zap className="h-3.5 w-3.5 text-cyan-400" />
                  <span className="text-sm font-bold text-white">{selected.label}</span>
                </div>
                <p className="mt-0.5 text-[11px] text-slate-500">{selected.type}</p>
              </div>
              <RiskBadge risk={impact.risk} large />
            </div>

            {/* METRICS — 2 × 2 grid */}
            <div className="mb-4 grid grid-cols-2 gap-2">
              <ImpactMetric label="Direct dependencies"   value={impact.directDeps}   highlight />
              <ImpactMetric label="Indirect dependencies" value={impact.indirectDeps} />
              <ImpactMetric label="Affected APIs"         value={impact.affectedApis} />
              <ImpactMetric label="Affected tests"        value={impact.affectedTests} />
            </div>

            {/* BLAST RADIUS */}
            <ImpactSection
              icon={<CircleDot className="h-3 w-3 text-orange-400" />}
              title="Blast Radius"
            >
              <div
                className="rounded-lg p-3"
                style={{ background: "rgba(249,115,22,0.05)", border: "1px solid rgba(249,115,22,0.15)" }}
              >
                <ImpactGroup label="Direct impact"   items={impact.directImpact}   dotColor="#fb923c" />
                <ImpactGroup label="Indirect impact" items={impact.indirectImpact} dotColor="#fbbf24" />
                {impact.directImpact.length === 0 && impact.indirectImpact.length === 0 && (
                  <p className="text-xs text-slate-500">No downstream components affected.</p>
                )}
              </div>
            </ImpactSection>

            {/* RISK ANALYSIS */}
            <ImpactSection
              icon={<TriangleAlert className="h-3 w-3 text-amber-400" />}
              title="Risk Analysis"
            >
              <div
                className="rounded-lg p-3"
                style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.07)" }}
              >
                <p className="mb-2 text-[10px] font-medium text-slate-500">
                  Why this is {impact.risk.toLowerCase()} risk:
                </p>
                <ul className="space-y-1">
                  {impact.riskReasons.map((reason) => (
                    <li key={reason} className="flex items-start gap-2">
                      <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />
                      <span className="text-xs leading-relaxed text-slate-300">{reason}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </ImpactSection>

            {/* VERIFICATION CHECKLIST */}
            {impact.verificationSteps.length > 0 && (
              <ImpactSection
                icon={<ClipboardCheck className="h-3 w-3 text-emerald-400" />}
                title="Verification Checklist"
              >
                <div
                  className="rounded-lg px-2 py-1"
                  style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.07)" }}
                >
                  {impact.verificationSteps.map((step) => (
                    <VerificationItem
                      key={step}
                      label={step}
                      checked={!!checked[stepKey(step)]}
                      onToggle={() => toggle(step)}
                    />
                  ))}
                </div>
              </ImpactSection>
            )}

            {/* RECOMMENDED ACTION */}
            <ImpactSection
              icon={<Lightbulb className="h-3 w-3 text-cyan-400" />}
              title="Recommended Action"
            >
              <div
                className="rounded-lg p-3"
                style={{ background: "rgba(34,211,238,0.05)", border: "1px solid rgba(34,211,238,0.15)" }}
              >
                <p className="text-xs leading-relaxed text-slate-300">
                  {impact.recommendedAction}
                </p>
              </div>
            </ImpactSection>
          </>
        )}
      </div>

      {/* ── Sticky footer — Bob Investigation button ─────────────────── */}
      <div className="flex-shrink-0 border-t border-white/10 px-5 py-4">
        <button
          className="flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5
            text-sm font-medium text-slate-950 transition
            disabled:cursor-not-allowed disabled:opacity-40"
          style={{
            background: investigating ? "#34d399" : selected ? "#22d3ee" : "#1e3a4a",
          }}
          disabled={!selected}
          onClick={handleInvestigate}
        >
          <Bot className="h-4 w-4" />
          {investigating ? "Investigation prepared" : "Investigate with Bob"}
        </button>
      </div>
    </div>
  );
}
