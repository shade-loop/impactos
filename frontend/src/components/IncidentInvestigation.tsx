import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock3,
  GitCommit,
  Lightbulb,
  Search,
  Server,
  ShieldAlert,
  TriangleAlert,
} from "lucide-react";

interface IncidentInvestigationProps {
  onInvestigate?: () => void;
}

const INCIDENT = {
  id: "INC-1042",
  title: "Checkout API latency spike",
  status: "Investigating",
  severity: "SEV-2",
  detectedAt: "14:02",
  openedAt: "14:14",
};

const TIMELINE = [
  {
    time: "14:02",
    title: "Deployment detected",
    description: "A new UserService version was deployed.",
    type: "change",
  },
  {
    time: "14:07",
    title: "Latency begins increasing",
    description: "Checkout request latency starts deviating from baseline.",
    type: "signal",
  },
  {
    time: "14:11",
    title: "Error rate crosses threshold",
    description: "Checkout failures exceed the configured alert threshold.",
    type: "alert",
  },
  {
    time: "14:14",
    title: "Incident opened",
    description: "Automated monitoring creates an incident for investigation.",
    type: "incident",
  },
];


const EVIDENCE = [
  "UserService was changed shortly before the incident began.",
  "CheckoutService has a dependency path through UserService.",
  "The observed degradation overlaps the recent deployment window.",
  "PaymentService is downstream of the affected checkout path.",
];

const NEXT_STEPS = [
  "Inspect UserService request latency before and after deployment.",
  "Compare checkout error rates against the previous release.",
  "Run CheckoutService integration tests against the changed version.",
  "Verify PaymentService requests for correlated failures.",
];

export default function IncidentInvestigation({
  onInvestigate,
}: IncidentInvestigationProps) {
  return (
    <section
      className="overflow-hidden rounded-xl border border-white/10 bg-white/[0.025]"
      style={{
        boxShadow: "0 10px 40px rgba(0,0,0,0.14)",
      }}
    >
      {/* ── Header ───────────────────────────────────────────────────────── */}

      <div className="border-b border-white/10 px-5 py-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <div
                className="flex h-7 w-7 items-center justify-center rounded-md"
                style={{
                  background: "rgba(239,68,68,0.08)",
                  border: "1px solid rgba(239,68,68,0.16)",
                }}
              >
                <ShieldAlert className="h-3.5 w-3.5 text-red-400" />
              </div>

              <div>
                <h2 className="text-sm font-semibold text-slate-100">
                  Incident Investigation
                </h2>

                <p className="mt-0.5 text-[10px] uppercase tracking-wider text-slate-600">
                  Change → impact → evidence
                </p>
              </div>
            </div>
          </div>

          <span
            className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider"
            style={{
              background: "rgba(251,146,60,0.1)",
              color: "#fb923c",
              border: "1px solid rgba(251,146,60,0.25)",
            }}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-orange-400" />
            {INCIDENT.status}
          </span>
        </div>
      </div>

      {/* ── Incident summary ─────────────────────────────────────────────── */}

      <div className="grid gap-4 border-b border-white/10 p-5 lg:grid-cols-[1.4fr_1fr]">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-600">
              {INCIDENT.id}
            </span>

            <span className="text-slate-700">•</span>

            <span className="text-[10px] font-medium text-red-400">
              {INCIDENT.severity}
            </span>
          </div>

          <h3 className="text-lg font-semibold text-white">
            {INCIDENT.title}
          </h3>

          <p className="mt-1.5 max-w-xl text-xs leading-5 text-slate-500">
            ImpactOS is correlating the incident timeline with recent code
            changes and the repository dependency graph.
          </p>

          <div className="mt-4 flex flex-wrap gap-2">
            <div
              className="flex items-center gap-2 rounded-md px-2.5 py-2"
              style={{
                background: "rgba(255,255,255,0.025)",
                border: "1px solid rgba(255,255,255,0.07)",
              }}
            >
              <Clock3 className="h-3.5 w-3.5 text-slate-500" />

              <div>
                <p className="text-[9px] uppercase tracking-wider text-slate-600">
                  Detected
                </p>

                <p className="mt-0.5 text-[11px] text-slate-300">
                  {INCIDENT.detectedAt}
                </p>
              </div>
            </div>

            <div
              className="flex items-center gap-2 rounded-md px-2.5 py-2"
              style={{
                background: "rgba(255,255,255,0.025)",
                border: "1px solid rgba(255,255,255,0.07)",
              }}
            >
              <AlertTriangle className="h-3.5 w-3.5 text-orange-400" />

              <div>
                <p className="text-[9px] uppercase tracking-wider text-slate-600">
                  Opened
                </p>

                <p className="mt-0.5 text-[11px] text-slate-300">
                  {INCIDENT.openedAt}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Impact path */}

        <div
          className="rounded-xl p-4"
          style={{
            background:
              "linear-gradient(135deg, rgba(239,68,68,0.05), rgba(255,255,255,0.015))",
            border: "1px solid rgba(239,68,68,0.13)",
          }}
        >
          <div className="mb-3 flex items-center justify-between">
            <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
              Suspected impact path
            </span>

            <Server className="h-3.5 w-3.5 text-slate-600" />
          </div>

          <div className="flex items-center gap-2">
            <ServicePill
              name="UserService"
              state="changed"
            />

            <ArrowRight className="h-3.5 w-3.5 shrink-0 text-slate-600" />

            <ServicePill
              name="CheckoutService"
              state="affected"
            />

            <ArrowRight className="h-3.5 w-3.5 shrink-0 text-slate-600" />

            <ServicePill
              name="PaymentService"
              state="downstream"
            />
          </div>

          <p className="mt-3 text-[10px] leading-4 text-slate-600">
            Dependency relationship combined with timing evidence.
          </p>
        </div>
      </div>

      {/* ── Main investigation grid ─────────────────────────────────────── */}

      <div className="grid lg:grid-cols-2">
        {/* Timeline */}

        <div className="border-b border-white/10 p-5 lg:border-b-0 lg:border-r">
          <SectionHeader
            icon={<Clock3 className="h-3 w-3 text-cyan-400" />}
            title="Incident Timeline"
          />

          <div className="relative ml-1.5 mt-4 space-y-4">
            <div className="absolute bottom-2 left-[5px] top-2 w-px bg-white/10" />

            {TIMELINE.map((event) => (
              <div
                key={`${event.time}-${event.title}`}
                className="relative flex gap-3"
              >
                <TimelineDot type={event.type} />

                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] text-slate-600">
                      {event.time}
                    </span>

                    <span className="text-xs font-medium text-slate-300">
                      {event.title}
                    </span>
                  </div>

                  <p className="mt-1 text-[10px] leading-4 text-slate-600">
                    {event.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent changes */}

        <div className="border-b border-white/10 p-5">
          <SectionHeader
            icon={<GitCommit className="h-3 w-3 text-violet-400" />}
            title="Recent Changes"
          />

          <div
            className="mt-4 rounded-lg p-3.5"
            style={{
              background: "rgba(139,92,246,0.035)",
              border: "1px solid rgba(139,92,246,0.12)",
            }}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-white">
                    UserService
                  </span>

                  <span className="rounded bg-violet-400/10 px-1.5 py-0.5 text-[9px] text-violet-400">
                    DEPLOYED
                  </span>
                </div>

                <p className="mt-1.5 text-xs text-slate-400">
                  Update session validation
                </p>

                <p className="mt-1 text-[10px] text-slate-600">
                  Changed shortly before incident onset
                </p>
              </div>

              <GitCommit className="h-4 w-4 shrink-0 text-violet-400/60" />
            </div>

            <div className="mt-3 flex items-center gap-2 border-t border-white/5 pt-3">
              <span className="font-mono text-[9px] text-slate-600">
                commit: a81f2c7
              </span>

              <span className="text-slate-700">•</span>

              <span className="text-[9px] text-slate-600">
                12 min before incident
              </span>
            </div>
          </div>

          <div className="mt-3 flex items-center gap-2 text-[10px] text-slate-600">
            <Search className="h-3 w-3" />
            <span>Correlation based on change timing and dependencies</span>
          </div>
        </div>

        {/* Evidence */}

        <div className="border-b border-white/10 p-5 lg:border-b-0 lg:border-r">
          <SectionHeader
            icon={<Search className="h-3 w-3 text-amber-400" />}
            title="Evidence"
          />

          <div className="mt-4 space-y-2">
            {EVIDENCE.map((item) => (
              <div
                key={item}
                className="flex items-start gap-2.5 rounded-md px-2.5 py-2"
                style={{
                  background: "rgba(255,255,255,0.018)",
                  border: "1px solid rgba(255,255,255,0.05)",
                }}
              >
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400" />

                <span className="text-xs leading-5 text-slate-400">
                  {item}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Hypothesis */}

        <div className="p-5">
          <SectionHeader
            icon={<Lightbulb className="h-3 w-3 text-cyan-400" />}
            title="Investigation Hypothesis"
          />

          <div
            className="mt-4 rounded-xl p-4"
            style={{
              background:
                "linear-gradient(135deg, rgba(34,211,238,0.055), rgba(255,255,255,0.015))",
              border: "1px solid rgba(34,211,238,0.14)",
            }}
          >
            <div className="flex items-start gap-2.5">
              <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-cyan-400" />

              <p className="text-xs leading-5 text-slate-300">
                The recent UserService change is a candidate contributor to
                the checkout degradation because the deployment precedes the
                incident and UserService sits on the affected dependency path.
              </p>
            </div>

            <div className="mt-3 border-t border-cyan-400/10 pt-3">
              <p className="text-[9px] uppercase tracking-wider text-slate-600">
                Confidence
              </p>

              <div className="mt-2 flex items-center gap-2">
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
                  <div
                    className="h-full w-[68%] rounded-full bg-cyan-400"
                    style={{
                      boxShadow: "0 0 8px rgba(34,211,238,0.35)",
                    }}
                  />
                </div>

                <span className="text-[10px] font-medium text-cyan-400">
                  Correlated
                </span>
              </div>

              <p className="mt-2 text-[9px] leading-4 text-slate-600">
                This is an investigation hypothesis, not a confirmed root
                cause.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Next steps ───────────────────────────────────────────────────── */}

      <div className="border-t border-white/10 p-5">
        <SectionHeader
          icon={<CheckCircle2 className="h-3 w-3 text-emerald-400" />}
          title="Recommended Investigation Steps"
        />

        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {NEXT_STEPS.map((step, index) => (
            <div
              key={step}
              className="flex items-start gap-3 rounded-lg px-3 py-2.5"
              style={{
                background: "rgba(255,255,255,0.018)",
                border: "1px solid rgba(255,255,255,0.06)",
              }}
            >
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-400/10 text-[9px] font-semibold text-emerald-400">
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
          <AlertTriangle className="h-3.5 w-3.5 text-orange-400" />

          <span className="text-[10px] text-slate-600">
            Demo incident data — backend investigation will replace this.
          </span>
        </div>

        <button
          type="button"
          onClick={onInvestigate}
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

// ─── Supporting components ────────────────────────────────────────────────────

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

function ServicePill({
  name,
  state,
}: {
  name: string;
  state: "changed" | "affected" | "downstream";
}) {
  const styles = {
    changed: {
      background: "rgba(139,92,246,0.08)",
      border: "rgba(139,92,246,0.2)",
      text: "#a78bfa",
    },
    affected: {
      background: "rgba(239,68,68,0.08)",
      border: "rgba(239,68,68,0.2)",
      text: "#f87171",
    },
    downstream: {
      background: "rgba(251,191,36,0.06)",
      border: "rgba(251,191,36,0.18)",
      text: "#fbbf24",
    },
  };

  const style = styles[state];

  return (
    <div
      className="rounded-md px-2 py-1.5"
      style={{
        background: style.background,
        border: `1px solid ${style.border}`,
      }}
    >
      <p
        className="text-[10px] font-medium whitespace-nowrap"
        style={{ color: style.text }}
      >
        {name}
      </p>
    </div>
  );
}

function TimelineDot({
  type,
}: {
  type: string;
}) {
  const styles: Record<string, string> = {
    change: "bg-violet-400",
    signal: "bg-cyan-400",
    alert: "bg-orange-400",
    incident: "bg-red-400",
  };

  return (
    <span
      className={`relative z-10 mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full border-2 border-[#0b0f14] ${
        styles[type] ?? "bg-slate-500"
      }`}
    />
  );
}