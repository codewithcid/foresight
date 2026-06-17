import type { Overview } from "../api";
import { num, pct } from "../api";

const STAGE_COLORS: Record<string, string> = {
  Awareness: "#6366f1",
  Consideration: "#818cf8",
  Intent: "#22d3ee",
  Purchase: "#34d399",
  Retention: "#a3e635",
};

export default function Funnel({ funnel }: { funnel: Overview["funnel"] }) {
  const { stages, biggest_drop } = funnel;
  const total = stages[0].count;

  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <span className="card-title">Customer Journey Funnel</span>
        <span className="pill">{num(total)} journeys</span>
      </div>

      <div className="mt-4 space-y-1">
        {stages.map((s, i) => {
          const isDropTo = s.stage === biggest_drop.to_stage;
          const w = Math.max(s.pct_of_total * 100, 6);
          return (
            <div key={s.stage}>
              <div className="flex items-center gap-3">
                <div className="w-28 shrink-0 text-sm font-medium text-slate-300">{s.stage}</div>
                <div className="relative h-9 flex-1 overflow-hidden rounded-lg bg-panel2">
                  <div
                    className="flex h-full items-center justify-end rounded-lg px-3 transition-all duration-700"
                    style={{
                      width: `${w}%`,
                      background: `linear-gradient(90deg, ${STAGE_COLORS[s.stage]}22, ${STAGE_COLORS[s.stage]}cc)`,
                    }}
                  >
                    <span className="stat text-sm font-semibold text-white">{num(s.count)}</span>
                  </div>
                </div>
                <div className="w-14 shrink-0 text-right stat text-xs text-slate-400">
                  {pct(s.pct_of_total, 0)}
                </div>
              </div>

              {i < stages.length - 1 && (
                <div className="flex items-center gap-3 py-0.5">
                  <div className="w-28 shrink-0" />
                  <div className="flex-1 pl-1">
                    <span
                      className={`text-xs ${
                        isDropTo || stages[i + 1].stage === biggest_drop.to_stage
                          ? "font-semibold text-bad"
                          : "text-slate-500"
                      }`}
                    >
                      ↓ {pct(stages[i + 1].step_conversion, 0)} advance
                      <span className="text-slate-600">
                        {" "}· {num(s.count - stages[i + 1].count)} lost
                      </span>
                      {stages[i + 1].stage === biggest_drop.to_stage && (
                        <span className="ml-2 rounded bg-bad/15 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-bad">
                          biggest leak
                        </span>
                      )}
                    </span>
                  </div>
                  <div className="w-14 shrink-0" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
