import type { Overview } from "../api";
import { num, pct, signedPct } from "../api";

export default function FrictionPanel({
  overview,
  narrative,
  narrativeSource,
}: {
  overview: Overview;
  narrative: string;
  narrativeSource: "ai" | "template" | "loading";
}) {
  const seg = overview.segment_friction;
  const maxConv = Math.max(...seg.by_segment.map((s) => s.purchase_conversion));
  const channels = overview.channel_patterns.channels.slice(0, 4);

  return (
    <div className="card flex flex-col gap-5">
      <div>
        <div className="flex items-center justify-between">
          <span className="card-title">Friction Insight</span>
          <span className="pill">
            <span className={`h-1.5 w-1.5 rounded-full ${narrativeSource === "ai" ? "bg-good" : "bg-warn"}`} />
            {narrativeSource === "ai" ? "Gemini" : narrativeSource === "loading" ? "…" : "Heuristic"}
          </span>
        </div>
        <p className="mt-3 text-[15px] leading-relaxed text-slate-200">{narrative}</p>
      </div>

      <div>
        <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
          {seg.transition} conversion by segment
        </div>
        <div className="space-y-2">
          {seg.by_segment.map((s) => {
            const worst = s.segment_label === seg.worst_segment.segment_label;
            return (
              <div key={s.segment} className="flex items-center gap-3">
                <div className="w-28 shrink-0 text-sm text-slate-300">{s.segment_label}</div>
                <div className="relative h-5 flex-1 overflow-hidden rounded bg-panel2">
                  <div
                    className="h-full rounded transition-all duration-700"
                    style={{
                      width: `${(s.purchase_conversion / maxConv) * 100}%`,
                      background: worst ? "#fb7185" : "#34d399",
                    }}
                  />
                </div>
                <div className="w-12 shrink-0 text-right stat text-xs text-slate-300">
                  {pct(s.purchase_conversion, 0)}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div>
        <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Channels correlated with conversion
        </div>
        <div className="grid grid-cols-2 gap-2">
          {channels.map((c) => (
            <div key={c.channel} className="rounded-lg border border-line bg-panel2 px-3 py-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-300">{c.channel.replace("_", " ")}</span>
                <span className={`stat text-sm font-semibold ${c.lift_vs_baseline >= 0 ? "text-good" : "text-bad"}`}>
                  {signedPct(c.lift_vs_baseline, 0)}
                </span>
              </div>
              <div className="stat text-[11px] text-slate-500">{num(c.reach)} reached</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
