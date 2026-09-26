/**
 * ImpactPanel.tsx
 *
 * Change Impact Report panel for ImpactOS.
 *
 * B3 polish:
 *   - Stronger report hierarchy
 *   - Clear component/risk header
 *   - Impact summary
 *   - Refined blast-radius visualization
 *   - Verification checklist
 *   - Recommended action
 *   - Bob investigation CTA
 *
 * The component continues to consume ImpactData through props so the
 * current mock data can later be replaced by the backend without
 * changing this UI structure.
 */

import { useState } from "react";
import {
  Bot,
  Check,
  CheckSquare,
  ChevronRight,
  CircleDot,
  ClipboardCheck,
  Lightbulb,
  ShieldAlert,
  Square,
  Target,
  TriangleAlert,
  Zap,
} from "lucide-react";

import type { ImpactData } from "../utils/blastRadius";
import type { SelectedNode } from "./DependencyGraph";

// ─── Public props ─────────────────────────────────────────────────────────────

export interface ImpactPanelProps {
  selected: SelectedNode | null;
  impact: ImpactData | null;
  onInvestigate: () => void;
}

// ─── Risk configuration ───────────────────────────────────────────────────────

const RISK_CONFIG: Record<
  ImpactData["risk"],
  {
    label: string;
    shortLabel: string;
    bg: string;
    text: string;
    border: string;
    dot: string;
  }
> = {
  HIGH: {
    label: "HIGH RISK",
    shortLabel: "High",
    bg: "rgba(239,68,68,0.12)",
    text: "#f87171",
    border: "rgba(239,68,68,0.35)",
    dot: "#ef4444",
  },

  MEDIUM: {
    label: "MEDIUM RISK",
    shortLabel: "Medium",
    bg: "rgba(251,146,60,0.12)",
    text: "#fb923c",
    border: "rgba(251,146,60,0.35)",
    dot: "#f97316",
  },

  LOW: {
    label: "LOW RISK",
    shortLabel: "Low",
    bg: "rgba(52,211,153,0.12)",
    text: "#34d399",
    border: "rgba(52,211,153,0.35)",
    dot: "#10b981",
  },
};

// ─── Risk badge ───────────────────────────────────────────────────────────────

interface RiskBadgeProps {
  risk: ImpactData["risk"];
}

function RiskBadge({ risk }: RiskBadgeProps) {
  const config = RISK_CONFIG[risk];

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider"
      style={{
        background: config.bg,
        color: config.text,
        border: `1px solid ${config.border}`,
      }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{
          background: config.dot,
          boxShadow: `0 0 7px ${config.dot}`,
        }}
      />

      {config.label}
    </span>
  );
}

// ─── Metric card ──────────────────────────────────────────────────────────────

interface ImpactMetricProps {
  label: string;
  value: number;
  accent?: boolean;
}

function ImpactMetric({
  label,
  value,
  accent = false,
}: ImpactMetricProps) {
  return (
    <div
      className="rounded-lg px-3 py-3"
      style={{
        background: accent
          ? "linear-gradient(135deg, rgba(34,211,238,0.08), rgba(34,211,238,0.025))"
          : "rgba(255,255,255,0.025)",
        border: accent
          ? "1px solid rgba(34,211,238,0.18)"
          : "1px solid rgba(255,255,255,0.07)",
      }}
    >
      <div className="flex items-end justify-between gap-2">
        <span
          className="text-2xl font-semibold leading-none"
          style={{
            color: accent ? "#22d3ee" : "#f1f5f9",
          }}
        >
          {value}
        </span>

        {accent && (
          <Target className="mb-0.5 h-3.5 w-3.5 text-cyan-500/60" />
        )}
      </div>

      <p className="mt-2 text-[10px] font-medium uppercase tracking-wide text-slate-500">
        {label}
      </p>
    </div>
  );
}

// ─── Section ──────────────────────────────────────────────────────────────────

interface ImpactSectionProps {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
  description?: string;
}

function ImpactSection({
  icon,
  title,
  children,
  description,
}: ImpactSectionProps) {
  return (
    <section className="mb-5">
      <div className="mb-2.5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-1.5">
          {icon}

          <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400">
            {title}
          </span>
        </div>

        {description && (
          <span className="text-[9px] text-slate-600">
            {description}
          </span>
        )}
      </div>

      {children}
    </section>
  );
}

// ─── Verification item ────────────────────────────────────────────────────────

interface VerificationItemProps {
  label: string;
  checked: boolean;
  onToggle: () => void;
}

function VerificationItem({
  label,
  checked,
  onToggle,
}: VerificationItemProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="group flex w-full items-center gap-2.5 rounded-md px-2 py-2 text-left transition hover:bg-white/[0.04]"
    >
      {checked ? (
        <CheckSquare className="h-3.5 w-3.5 shrink-0 text-emerald-400" />
      ) : (
        <Square className="h-3.5 w-3.5 shrink-0 text-slate-600 transition group-hover:text-slate-400" />
      )}

      <span
        className="text-xs leading-snug transition"
        style={{
          color: checked ? "#64748b" : "#cbd5e1",
          textDecoration: checked ? "line-through" : "none",
        }}
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

function ImpactGroup({
  label,
  items,
  dotColor,
}: ImpactGroupProps) {
  if (items.length === 0) return null;

  return (
    <div className="mb-3 last:mb-0">
      <div className="mb-1.5 flex items-center gap-2">
        <span
          className="h-1.5 w-1.5 rounded-full"
          style={{
            background: dotColor,
            boxShadow: `0 0 6px ${dotColor}`,
          }}
        />

        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          {label}
        </span>

        <span className="text-[9px] text-slate-600">
          {items.length}
        </span>
      </div>

      <div className="space-y-0.5 pl-3.5">
        {items.map((name) => (
          <div
            key={name}
            className="flex items-center gap-1.5 rounded px-1 py-1"
          >
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

// ─── Empty state ──────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex min-h-[330px] flex-col items-center justify-center px-6 text-center">
      <div
        className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl"
        style={{
          background: "rgba(249,115,22,0.07)",
          border: "1px solid rgba(249,115,22,0.15)",
        }}
      >
        <ShieldAlert className="h-5 w-5 text-orange-400/80" />
      </div>

      <p className="text-sm font-semibold text-slate-300">
        Select a component
      </p>

      <p className="mt-1.5 max-w-[250px] text-xs leading-5 text-slate-600">
        Choose a service from the dependency graph to calculate its potential
        change impact and blast radius.
      </p>

      <div className="mt-4 flex items-center gap-2 text-[10px] text-slate-700">
        <CircleDot className="h-3 w-3" />
        <span>Impact analysis ready</span>
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function ImpactPanel({
  selected,
  impact,
  onInvestigate,
}: ImpactPanelProps) {
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [investigating, setInvestigating] = useState(false);

  const stepKey = (step: string) =>
    `${selected?.id ?? ""}::${step}`;

  const toggle = (step: string) => {
    setChecked((prev) => ({
      ...prev,
      [stepKey(step)]: !prev[stepKey(step)],
    }));
  };

  const handleInvestigate = () => {
    setInvestigating(true);
    onInvestigate();

    window.setTimeout(() => {
      setInvestigating(false);
    }, 3000);
  };

  const riskConfig = impact
    ? RISK_CONFIG[impact.risk]
    : null;

  const totalAffected =
    impact
      ? impact.directImpact.length + impact.indirectImpact.length
      : 0;

  return (
    <div
      className="flex min-h-[420px] flex-col overflow-hidden rounded-xl border border-white/10 bg-white/[0.025]"
      style={{
        boxShadow: "0 10px 40px rgba(0,0,0,0.18)",
      }}
    >
      {/* ── Header ───────────────────────────────────────────────────────── */}

      <div className="flex-shrink-0 border-b border-white/10 px-5 py-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <div
                className="flex h-7 w-7 items-center justify-center rounded-md"
                style={{
                  background: "rgba(249,115,22,0.08)",
                  border: "1px solid rgba(249,115,22,0.16)",
                }}
              >
                <ShieldAlert className="h-3.5 w-3.5 text-orange-400" />
              </div>

              <div>
                <h3 className="text-sm font-semibold text-slate-100">
                  Change Impact
                </h3>

                <p className="mt-0.5 text-[10px] uppercase tracking-wider text-slate-600">
                  Impact intelligence
                </p>
              </div>
            </div>
          </div>

          {selected && impact && (
            <RiskBadge risk={impact.risk} />
          )}
        </div>

        {selected && (
          <div className="mt-3 flex items-center gap-2">
            <div
              className="h-1.5 w-1.5 rounded-full bg-cyan-400"
              style={{
                boxShadow: "0 0 7px rgba(34,211,238,0.8)",
              }}
            />

            <span className="text-xs font-medium text-slate-300">
              {selected.label}
            </span>

            <span className="text-slate-700">/</span>

            <span className="text-[10px] text-slate-500">
              {selected.type}
            </span>
          </div>
        )}
      </div>

      {/* ── Scrollable body ──────────────────────────────────────────────── */}

      <div
        className="min-h-0 flex-1 overflow-y-auto px-5 py-4"
        style={{
          scrollbarWidth: "thin",
        }}
      >
        {/* Empty state */}

        {!selected || !impact ? (
          <EmptyState />
        ) : (
          <>
            {/* ── Report identity ───────────────────────────────────────── */}

            <div
              className="mb-5 rounded-xl p-4"
              style={{
                background: `linear-gradient(135deg, ${riskConfig?.bg}, rgba(255,255,255,0.015))`,
                border: `1px solid ${riskConfig?.border}`,
              }}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-1.5">
                    <Zap className="h-3.5 w-3.5 text-cyan-400" />

                    <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                      Impact report
                    </span>
                  </div>

                  <h4 className="mt-2 text-base font-semibold text-white">
                    {selected.label}
                  </h4>

                  <p className="mt-0.5 text-[11px] text-slate-500">
                    {selected.type} · {totalAffected} downstream component
                    {totalAffected === 1 ? "" : "s"} affected
                  </p>
                </div>

                <RiskBadge risk={impact.risk} />
              </div>
            </div>

            {/* ── Metrics ───────────────────────────────────────────────── */}

            <ImpactSection
              icon={<Target className="h-3 w-3 text-cyan-400" />}
              title="Impact Surface"
            >
              <div className="grid grid-cols-2 gap-2">
                <ImpactMetric
                  label="Direct dependencies"
                  value={impact.directDeps}
                  accent
                />

                <ImpactMetric
                  label="Indirect dependencies"
                  value={impact.indirectDeps}
                />

                <ImpactMetric
                  label="Affected APIs"
                  value={impact.affectedApis}
                />

                <ImpactMetric
                  label="Affected tests"
                  value={impact.affectedTests}
                />
              </div>
            </ImpactSection>

            {/* ── Blast radius ───────────────────────────────────────────── */}

            <ImpactSection
              icon={<CircleDot className="h-3 w-3 text-orange-400" />}
              title="Blast Radius"
              description={`${totalAffected} affected`}
            >
              <div
                className="rounded-xl p-3.5"
                style={{
                  background:
                    "linear-gradient(135deg, rgba(249,115,22,0.055), rgba(255,255,255,0.015))",
                  border: "1px solid rgba(249,115,22,0.14)",
                }}
              >
                <ImpactGroup
                  label="Direct impact"
                  items={impact.directImpact}
                  dotColor="#fb923c"
                />

                <ImpactGroup
                  label="Indirect impact"
                  items={impact.indirectImpact}
                  dotColor="#fbbf24"
                />

                {impact.directImpact.length === 0 &&
                  impact.indirectImpact.length === 0 && (
                    <div className="flex items-center gap-2 py-2">
                      <Check className="h-3.5 w-3.5 text-emerald-400" />

                      <p className="text-xs text-slate-500">
                        No downstream components affected.
                      </p>
                    </div>
                  )}
              </div>
            </ImpactSection>

            {/* ── Risk analysis ─────────────────────────────────────────── */}

            <ImpactSection
              icon={<TriangleAlert className="h-3 w-3 text-amber-400" />}
              title="Risk Analysis"
            >
              <div
                className="rounded-xl p-3.5"
                style={{
                  background: "rgba(255,255,255,0.018)",
                  border: "1px solid rgba(255,255,255,0.07)",
                }}
              >
                <div className="mb-3 flex items-center gap-2">
                  <span className="text-[10px] text-slate-500">
                    Current assessment
                  </span>

                  <RiskBadge risk={impact.risk} />
                </div>

                <p className="mb-2 text-[10px] text-slate-600">
                  Factors contributing to this assessment
                </p>

                <ul className="space-y-2">
                  {impact.riskReasons.map((reason) => (
                    <li
                      key={reason}
                      className="flex items-start gap-2"
                    >
                      <span
                        className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full"
                        style={{
                          background: riskConfig?.dot,
                          boxShadow: `0 0 5px ${riskConfig?.dot}`,
                        }}
                      />

                      <span className="text-xs leading-relaxed text-slate-300">
                        {reason}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </ImpactSection>

            {/* ── Verification ──────────────────────────────────────────── */}

            {impact.verificationSteps.length > 0 && (
              <ImpactSection
                icon={
                  <ClipboardCheck className="h-3 w-3 text-emerald-400" />
                }
                title="Verification Checklist"
                description={`${impact.verificationSteps.length} checks`}
              >
                <div
                  className="rounded-xl p-1"
                  style={{
                    background: "rgba(255,255,255,0.018)",
                    border: "1px solid rgba(255,255,255,0.07)",
                  }}
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

            {/* ── Recommended action ────────────────────────────────────── */}

            <ImpactSection
              icon={<Lightbulb className="h-3 w-3 text-cyan-400" />}
              title="Recommended Action"
            >
              <div
                className="rounded-xl p-4"
                style={{
                  background:
                    "linear-gradient(135deg, rgba(34,211,238,0.055), rgba(34,211,238,0.015))",
                  border: "1px solid rgba(34,211,238,0.14)",
                }}
              >
                <div className="mb-2 flex items-center gap-2">
                  <Lightbulb className="h-3.5 w-3.5 text-cyan-400" />

                  <span className="text-[10px] font-semibold uppercase tracking-wider text-cyan-400/80">
                    Before you merge
                  </span>
                </div>

                <p className="text-xs leading-relaxed text-slate-300">
                  {impact.recommendedAction}
                </p>
              </div>
            </ImpactSection>
          </>
        )}
      </div>

      {/* ── Sticky footer ───────────────────────────────────────────────── */}

      <div className="flex-shrink-0 border-t border-white/10 px-5 py-4">
        <button
          type="button"
          disabled={!selected}
          onClick={handleInvestigate}
          className="flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-35"
          style={{
            background: investigating
              ? "#34d399"
              : selected
                ? "#22d3ee"
                : "#1e293b",

            color: selected || investigating
              ? "#061116"
              : "#64748b",

            boxShadow:
              selected && !investigating
                ? "0 0 18px rgba(34,211,238,0.12)"
                : "none",
          }}
        >
          {investigating ? (
            <>
              <Check className="h-4 w-4" />
              Investigation prepared
            </>
          ) : (
            <>
              <Bot className="h-4 w-4" />
              Investigate with Bob
              <ChevronRight className="h-3.5 w-3.5 opacity-60" />
            </>
          )}
        </button>

        <p className="mt-2 text-center text-[9px] text-slate-700">
          AI-assisted repository investigation
        </p>
      </div>
    </div>
  );
}