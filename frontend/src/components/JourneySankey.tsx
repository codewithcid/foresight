import type { Overview } from "../api";
import { num, pct } from "../api";

const STAGE_COLORS = ["#6366f1", "#818cf8", "#22d3ee", "#34d399", "#a3e635"];

// Build a filled ribbon path between a left vertical edge [y0a,y0b]@x0 and a
// right vertical edge [y1a,y1b]@x1 using horizontal cubic beziers.
function ribbon(x0: number, y0a: number, y0b: number, x1: number, y1a: number, y1b: number) {
  const mx = (x0 + x1) / 2;
  return [
    `M ${x0} ${y0a}`,
    `C ${mx} ${y0a}, ${mx} ${y1a}, ${x1} ${y1a}`,
    `L ${x1} ${y1b}`,
    `C ${mx} ${y1b}, ${mx} ${y0b}, ${x0} ${y0b}`,
    "Z",
  ].join(" ");
}

export default function JourneySankey({ funnel }: { funnel: Overview["funnel"] }) {
  const stages = funnel.stages;
  const W = 1000, H = 300, top = 18, bottom = 70, nodeW = 15;
  const usableH = H - top - bottom;
  const baseY = top + usableH;
  const maxCount = stages[0].count;
  const scale = usableH / maxCount;
  const colSpacing = (W - 48 - nodeW) / (stages.length - 1);
  const x = (i: number) => 24 + i * colSpacing;
  const h = (c: number) => c * scale;

  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <span className="card-title">Journey Flow</span>
        <span className="pill">advancing vs. dropped at each stage</span>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 w-full" preserveAspectRatio="xMidYMid meet">
        <defs>
          {STAGE_COLORS.map((c, i) => (
            <linearGradient key={i} id={`adv${i}`} x1="0" x2="1" y1="0" y2="0">
              <stop offset="0%" stopColor={STAGE_COLORS[i]} stopOpacity={0.45} />
              <stop offset="100%" stopColor={STAGE_COLORS[i + 1] ?? c} stopOpacity={0.45} />
            </linearGradient>
          ))}
          <linearGradient id="drop" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#fb7185" stopOpacity={0.55} />
            <stop offset="100%" stopColor="#fb7185" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="dropBig" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#fb7185" stopOpacity={0.85} />
            <stop offset="100%" stopColor="#fb7185" stopOpacity={0.05} />
          </linearGradient>
        </defs>

        {stages.slice(0, -1).map((s, i) => {
          const next = stages[i + 1];
          const advH = h(next.count);
          const dropH = h(s.count - next.count);
          const x0 = x(i) + nodeW, x1 = x(i + 1);
          const isBig = next.stage === funnel.biggest_drop.to_stage;
          const gapMid = (x0 + x1) / 2;
          return (
            <g key={i}>
              {/* advancing ribbon */}
              <path d={ribbon(x0, top, top + advH, x1, top, top + advH)} fill={`url(#adv${i})`} />
              {/* drop-off flare to the baseline */}
              {dropH > 1 && (
                <path
                  d={ribbon(x0, top + advH, top + advH + dropH, gapMid, baseY + 14, baseY + 20)}
                  fill={isBig ? "url(#dropBig)" : "url(#drop)"}
                />
              )}
              {/* drop label */}
              <text x={gapMid} y={baseY + 34} textAnchor="middle"
                    className="fill-bad" fontSize={isBig ? 13 : 11} fontWeight={isBig ? 700 : 500}>
                −{num(s.count - next.count)}
              </text>
              <text x={gapMid} y={baseY + 47} textAnchor="middle" className="fill-slate-500" fontSize={10}>
                {pct(1 - next.step_conversion, 0)} drop
              </text>
            </g>
          );
        })}

        {/* stage nodes */}
        {stages.map((s, i) => (
          <g key={s.stage}>
            <rect x={x(i)} y={top} width={nodeW} height={Math.max(h(s.count), 2)} rx={3}
                  fill={STAGE_COLORS[i]} />
            <text x={x(i) + nodeW / 2} y={baseY + 14} textAnchor="middle"
                  className="fill-slate-300" fontSize={12} fontWeight={600}>
              {s.stage}
            </text>
            <text x={x(i) + nodeW / 2} y={baseY + 28} textAnchor="middle"
                  className="fill-slate-500 stat" fontSize={11}>
              {num(s.count)}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
