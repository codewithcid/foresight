import type { Recommendation } from "../api";
import { num, signedPct, usd } from "../api";

export default function Recommendations({
  recs,
  selected,
  onPick,
}: {
  recs: Recommendation[];
  selected: { intervention: string; segment: string };
  onPick: (intervention: string, segment: string) => void;
}) {
  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <span className="card-title">Recommended Interventions</span>
        <span className="text-[11px] text-slate-500">ranked by lift × reach ÷ cost</span>
      </div>

      <div className="mt-3 overflow-hidden rounded-xl border border-line">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-panel2 text-[11px] uppercase tracking-wider text-slate-500">
              <th className="px-3 py-2 text-left font-semibold">Intervention</th>
              <th className="px-3 py-2 text-left font-semibold">Segment</th>
              <th className="px-3 py-2 text-right font-semibold">Pred. lift</th>
              <th className="px-3 py-2 text-right font-semibold">+Conv</th>
              <th className="px-3 py-2 text-right font-semibold">Revenue</th>
              <th className="px-3 py-2 text-right font-semibold">ROI</th>
            </tr>
          </thead>
          <tbody>
            {recs.map((r, i) => {
              const isSel = r.intervention === selected.intervention && r.segment === selected.segment;
              return (
                <tr
                  key={`${r.intervention}-${r.segment}`}
                  onClick={() => onPick(r.intervention, r.segment)}
                  className={`cursor-pointer border-t border-line transition-colors ${
                    isSel ? "bg-brand/20" : "hover:bg-panel2/60"
                  }`}
                >
                  <td className="px-3 py-2.5">
                    <span className="text-slate-200">{r.intervention_label}</span>
                    {i === 0 && (
                      <span className="ml-2 rounded bg-good/15 px-1.5 py-0.5 text-[10px] font-bold uppercase text-good">
                        top
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-slate-400">{r.segment_label}</td>
                  <td className="px-3 py-2.5 text-right stat font-semibold text-good">{signedPct(r.predicted_rel_lift, 0)}</td>
                  <td className="px-3 py-2.5 text-right stat text-slate-300">{num(r.incremental_conversions)}</td>
                  <td className="px-3 py-2.5 text-right stat text-slate-300">{usd(r.projected_revenue)}</td>
                  <td className="px-3 py-2.5 text-right stat text-slate-400">{num(r.roi)}×</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-[11px] text-slate-500">Click any row to load it into the What-If Simulator →</p>
    </div>
  );
}
