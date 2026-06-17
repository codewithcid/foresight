import type { Insight, Meta, SimResult } from "../api";
import { num, pct, signedPct, usdFull } from "../api";

function Metric({
  label, value, sub, accent = "text-white",
}: { label: string; value: string; sub?: string; accent?: string }) {
  return (
    <div className="rounded-xl border border-line bg-panel2 p-3">
      <div className="text-[11px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className={`mt-1 stat text-2xl font-bold ${accent}`}>{value}</div>
      {sub && <div className="stat mt-0.5 text-[11px] text-slate-500">{sub}</div>}
    </div>
  );
}

export default function Simulator({
  meta, selected, onChange, result, insight, loading,
}: {
  meta: Meta;
  selected: { intervention: string; segment: string };
  onChange: (intervention: string, segment: string) => void;
  result: SimResult | null;
  insight: Insight | null;
  loading: boolean;
}) {
  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <span className="card-title">What-If Simulator</span>
        <span className="pill">counterfactual · before you spend</span>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <label className="text-xs text-slate-400">
          Intervention
          <select
            className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand"
            value={selected.intervention}
            onChange={(e) => onChange(e.target.value, selected.segment)}
          >
            {meta.interventions.map((i) => (
              <option key={i.key} value={i.key}>{i.label} · {i.channel.replace("_", " ")}</option>
            ))}
          </select>
        </label>
        <label className="text-xs text-slate-400">
          Target segment
          <select
            className="mt-1 w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-sm text-slate-100 outline-none focus:border-brand"
            value={selected.segment}
            onChange={(e) => onChange(selected.intervention, e.target.value)}
          >
            <option value="all">All segments</option>
            {meta.segments.map((s) => (
              <option key={s.key} value={s.key}>{s.label}</option>
            ))}
          </select>
        </label>
      </div>

      <div className={`mt-4 transition-opacity ${loading ? "opacity-40" : "opacity-100"}`}>
        {result && (
          <>
            <div className="grid grid-cols-2 gap-3">
              <Metric
                label="Predicted lift"
                value={signedPct(result.predicted_rel_lift)}
                sub={`90% CI ${signedPct(result.rel_lift_ci[0])} … ${signedPct(result.rel_lift_ci[1])}`}
                accent="text-good"
              />
              <Metric
                label="Incremental conversions"
                value={`+${num(result.incremental_conversions)}`}
                sub={`on ${num(result.reach)} reached · base ${pct(result.baseline_conv, 0)}`}
              />
              <Metric
                label="Projected revenue"
                value={usdFull(result.projected_revenue)}
                sub={`CI ${usdFull(result.revenue_ci[0])} … ${usdFull(result.revenue_ci[1])}`}
                accent="text-good"
              />
              <Metric
                label="Return on spend"
                value={`${num(result.roi)}×`}
                sub={`cost ${usdFull(result.cost)} @ AOV $${meta.aov}`}
              />
            </div>
            <div className="mt-3 rounded-xl border border-line bg-panel2/60 p-3">
              <div className="mb-1 flex items-center gap-1.5">
                <span className={`h-1.5 w-1.5 rounded-full ${insight?.source === "ai" ? "bg-good" : "bg-warn"}`} />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  {insight?.source === "ai" ? "Gemini rationale" : "Rationale"}
                </span>
              </div>
              <p className="text-[12px] leading-relaxed text-slate-300">
                {insight?.text ?? (
                  <>
                    Targeting <span className="text-slate-200">{result.segment_label}</span> with{" "}
                    <span className="text-slate-200">{result.intervention_label}</span> is predicted to convert{" "}
                    <span className="stat text-good">+{num(result.incremental_conversions)}</span> additional
                    customers, worth <span className="stat text-good">{usdFull(result.projected_revenue)}</span> —
                    modelled counterfactually, no spend required.
                  </>
                )}
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
