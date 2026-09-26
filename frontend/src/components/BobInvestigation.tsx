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

interface BobInvestigationProps {
  onContinue?: () => void;
}

const SUPPORTED_FINDINGS = [
  "The repository contains a UserService → CheckoutService → PaymentService dependency path.",
  "The blast-radius traversal identifies CheckoutService as depth 1 from UserService.",
  "PaymentService is reachable at depth 2 from UserService.",
  "UserService also directly affects OrdersService.",
];

const EVIDENCE_GAPS = [
  "Commit a81f2c7 is a static demo constant, not verified git history.",
  "The 14:02 deployment timestamp is static demo data.",
  "No APM, telemetry, deployment, or service-mesh data exists in the repository.",
  "The current incident evidence bullets are static constants.",
];

const NEXT_STEPS = [
  "Inspect real git history for the UserService change.",
  "Compare the deployment timestamp with the incident start.",
  "Inspect CheckoutService telemetry around the incident window.",
  "Check OrdersService for correlated degradation.",
  "Connect real incident and telemetry sources.",
];

export default function BobInvestigation({
  onContinue,
}: BobInvestigationProps) {
  return (
    <section
      className="overflow-hidden rounded-xl border border-cyan-400/10 bg-white/[0.025]"
      style={{
        boxShadow: "0 10px 40px rgba(0,0,0,0.16)",
      }}
    >
      {/* Header */}
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
            style={{
              background: "rgba(52,211,153,0.08)",
              color: "#34d399",
              border: "1px solid rgba(52,211,153,0.18)",
            }}
          >
            <CheckCircle2 className="h-3 w-3" />
            Analysis complete
          </span>
        </div>
      </div>

      {/* Incident summary */}
      <div className="border-b border-white/10 px-5 py-5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">
            INC-1042
          </span>

          <span className="text-slate-700">•</span>

          <span className="text-xs font-medium text-slate-300">
            Checkout API latency spike
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
                Candidate contributor identified
              </p>

              <p className="mt-1 text-xs leading-5 text-slate-400">
                The repository supports the dependency relationship between
                UserService, CheckoutService, and PaymentService, but does not
                contain enough real operational evidence to confirm UserService
                as the root cause.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main investigation */}
      <div className="grid lg:grid-cols-2">
        {/* Supported findings */}
        <div className="border-b border-white/10 p-5 lg:border-b-0 lg:border-r">
          <SectionHeader
            icon={<CheckCircle2 className="h-3 w-3 text-emerald-400" />}
            title="Supported by Repository"
          />

          <div className="mt-4 space-y-2">
            {SUPPORTED_FINDINGS.map((finding) => (
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

        {/* Dependency path */}
        <div className="border-b border-white/10 p-5">
          <SectionHeader
            icon={<GitBranch className="h-3 w-3 text-cyan-400" />}
            title="Dependency Evidence"
          />

          <div
            className="mt-4 rounded-xl p-4"
            style={{
              background: "rgba(255,255,255,0.018)",
              border: "1px solid rgba(255,255,255,0.07)",
            }}
          >
            <div className="flex flex-wrap items-center gap-2">
              <ServiceNode
                name="UserService"
                color="#a78bfa"
              />

              <ArrowRight className="h-3.5 w-3.5 text-slate-600" />

              <ServiceNode
                name="CheckoutService"
                color="#f87171"
              />

              <ArrowRight className="h-3.5 w-3.5 text-slate-600" />

              <ServiceNode
                name="PaymentService"
                color="#fbbf24"
              />
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2">
              <DepthCard
                label="CheckoutService"
                value="Depth 1"
                accent="#f97316"
              />

              <DepthCard
                label="PaymentService"
                value="Depth 2"
                accent="#fbbf24"
              />
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
            Bob found these values in the demo, but they cannot currently be
            verified against external operational sources.
          </p>

          <div className="mt-4 space-y-2">
            {EVIDENCE_GAPS.map((gap) => (
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

        {/* Important observation */}
        <div className="p-5">
          <SectionHeader
            icon={<Search className="h-3 w-3 text-orange-400" />}
            title="Important Observation"
          />

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
                  OrdersService is also directly downstream.
                </p>

                <p className="mt-2 text-xs leading-5 text-slate-500">
                  If UserService regressed, OrdersService would also be
                  affected through the same direct dependency relationship.
                  If OrdersService shows no degradation during the same
                  window, that would argue against UserService as the root
                  cause.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Next steps */}
      <div className="border-t border-white/10 p-5">
        <SectionHeader
          icon={<FileCode2 className="h-3 w-3 text-violet-400" />}
          title="Recommended Investigation"
        />

        <div className="mt-4 grid gap-2 md:grid-cols-2">
          {NEXT_STEPS.map((step, index) => (
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

      {/* Footer */}
      <div className="flex flex-col gap-3 border-t border-white/10 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-3.5 w-3.5 text-cyan-400" />

          <span className="text-[10px] text-slate-600">
            Findings generated from repository analysis.
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