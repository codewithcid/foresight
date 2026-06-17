import {
  CartesianGrid, Cell, ReferenceLine, Scatter, ScatterChart,
  Tooltip, XAxis, YAxis, ZAxis, ResponsiveContainer,
} from "recharts";
import type { Validation } from "../api";
import { useCountUp } from "../useCountUp";

const COLORS: Record<string, string> = {
  cart_recovery_push: "#34d399",
  personalized_email: "#6366f1",
  sms_discount: "#fbbf24",
  retargeting_social: "#22d3ee",
};

export default function ValidationPanel({
  validation, selected,
}: {
  validation: Validation;
  selected: { intervention: string; segment: string };
}) {
  const h = validation.headline;
  const accuracy = 1 - h.abs_error / Math.max(h.actual_rel_lift, 1e-6);
  const predUp = useCountUp(h.predicted_rel_lift * 100);
  const actUp = useCountUp(h.actual_rel_lift * 100);

  const points = validation.per_cell.map((c) => ({
    x: c.predicted_rel_lift * 100,
    y: c.actual_rel_lift * 100,
    intervention: c.intervention,
    label: `${c.intervention_label} · ${c.segment_label}`,
    isSel: c.intervention === selected.intervention && c.segment === selected.segment,
  }));
  const maxV = Math.ceil(Math.max(...points.flatMap((p) => [p.x, p.y]), 10) / 5) * 5;

  return (
    <div className="card border-good/30 bg-gradient-to-b from-good/[0.06] to-transparent">
      <div className="flex items-center justify-between">
        <span className="card-title text-good">✓ Validation — Predicted vs Actual</span>
        <span className="pill">held-out ground truth</span>
      </div>

      {/* Hero: predicted vs actual for the top recommendation */}
      <div className="mt-4 grid grid-cols-3 items-center gap-3">
        <div className="rounded-xl border border-good/30 bg-panel2 p-4 text-center">
          <div className="text-[11px] uppercase tracking-wider text-slate-500">Foresight predicted</div>
          <div className="stat mt-1 text-3xl font-extrabold text-good">+{predUp.toFixed(1)}%</div>
        </div>
        <div className="text-center">
          <div className="stat text-2xl text-slate-500">vs</div>
          <div className="mt-1 text-[11px] text-slate-500">{h.intervention_label}</div>
        </div>
        <div className="rounded-xl border border-line bg-panel2 p-4 text-center">
          <div className="text-[11px] uppercase tracking-wider text-slate-500">Actual (held-out)</div>
          <div className="stat mt-1 text-3xl font-extrabold text-white">+{actUp.toFixed(1)}%</div>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-center gap-4 text-sm">
        <span className="text-slate-400">
          Error <span className="stat font-semibold text-slate-200">{(h.abs_error * 100).toFixed(1)}pp</span>
        </span>
        <span className="h-3 w-px bg-line" />
        <span className="text-slate-400">
          Accuracy <span className="stat font-semibold text-good">{(accuracy * 100).toFixed(0)}%</span>
        </span>
        <span className="h-3 w-px bg-line" />
        <span className="text-slate-400">
          Cell MAE <span className="stat font-semibold text-slate-200">{(validation.cell_mae * 100).toFixed(1)}pp</span>
        </span>
      </div>

      {/* Scatter: every intervention×segment cell vs the diagonal */}
      <div className="mt-4 h-56">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 8, right: 12, bottom: 24, left: 0 }}>
            <CartesianGrid stroke="#202b44" strokeDasharray="3 3" />
            <XAxis
              type="number" dataKey="x" domain={[0, maxV]} tick={{ fill: "#64748b", fontSize: 11 }}
              label={{ value: "Predicted lift %", position: "bottom", fill: "#64748b", fontSize: 11 }}
            />
            <YAxis
              type="number" dataKey="y" domain={[0, maxV]} tick={{ fill: "#64748b", fontSize: 11 }}
              label={{ value: "Actual lift %", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 11 }}
            />
            <ZAxis range={[60, 240]} />
            <ReferenceLine
              segment={[{ x: 0, y: 0 }, { x: maxV, y: maxV }]}
              stroke="#475569" strokeDasharray="5 5"
            />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              content={(props: any) => {
                const payload = props?.payload;
                if (!payload?.length) return null;
                const p = payload[0].payload;
                return (
                  <div className="rounded-lg border border-line bg-panel px-3 py-2 text-xs">
                    <div className="text-slate-200">{p.label}</div>
                    <div className="stat text-slate-400">pred {p.x.toFixed(1)}% · actual {p.y.toFixed(1)}%</div>
                  </div>
                );
              }}
            />
            <Scatter data={points}>
              {points.map((p, i) => (
                <Cell
                  key={i}
                  fill={COLORS[p.intervention]}
                  stroke={p.isSel ? "#fff" : "none"}
                  strokeWidth={p.isSel ? 2 : 0}
                  fillOpacity={p.isSel ? 1 : 0.75}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="-mt-1 flex flex-wrap justify-center gap-3 text-[11px] text-slate-400">
        {Object.entries(COLORS).map(([k, c]) => (
          <span key={k} className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ background: c }} />
            {k.replace(/_/g, " ")}
          </span>
        ))}
      </div>
      <p className="mt-2 text-center text-[11px] text-slate-500">
        Points on the dashed diagonal = perfect prediction. Each dot is one intervention × segment cell.
      </p>
    </div>
  );
}
