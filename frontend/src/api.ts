// Typed client for the Foresight API (proxied at /api by Vite).

export interface Meta {
  segments: { key: string; label: string }[];
  interventions: { key: string; label: string; channel: string; cost_per_contact: number }[];
  aov: number;
  stages: string[];
}

export interface FunnelStage {
  stage: string;
  count: number;
  pct_of_total: number;
  step_conversion: number;
  drop_off: number;
}

export interface Overview {
  funnel: {
    stages: FunnelStage[];
    biggest_drop: {
      from_stage: string; to_stage: string;
      step_conversion: number; drop_off: number; lost_customers: number;
    };
  };
  segment_friction: {
    transition: string;
    by_segment: {
      segment: string; segment_label: string; intent_pool: number;
      purchase_conversion: number; abandonment: number; avg_price_sensitivity: number;
    }[];
    worst_segment: { segment_label: string; purchase_conversion: number };
  };
  channel_patterns: {
    baseline_conversion: number;
    channels: { channel: string; reach: number; conversion_with_channel: number; lift_vs_baseline: number }[];
  };
  sankey: { nodes: string[]; links: { source: string; target: string; value: number }[] };
  headline: string;
  narrative: string;
  narrative_source: "ai" | "template";
  meta: Meta;
}

export interface Insight {
  text: string;
  source: "ai" | "template";
}

export interface Recommendation {
  intervention: string; intervention_label: string;
  segment: string; segment_label: string;
  predicted_rel_lift: number; incremental_conversions: number;
  projected_revenue: number; cost: number; roi: number; reach: number; score: number;
}

export interface SimResult {
  intervention: string; intervention_label: string;
  segment: string; segment_label: string;
  reach: number; baseline_conv: number;
  predicted_abs_lift: number; predicted_rel_lift: number;
  incremental_conversions: number; projected_revenue: number;
  cost: number; roi: number;
  rel_lift_ci: [number, number]; revenue_ci: [number, number];
}

export interface ValidationCell {
  intervention: string; intervention_label: string;
  segment: string; segment_label: string;
  predicted_rel_lift: number; actual_rel_lift: number; abs_error: number; n: number;
}

export interface Validation {
  per_cell: ValidationCell[];
  per_intervention: { intervention: string; intervention_label: string; predicted_rel_lift: number; actual_rel_lift: number; abs_error: number }[];
  cell_mae: number;
  headline: { intervention_label: string; predicted_rel_lift: number; actual_rel_lift: number; abs_error: number };
}

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url} -> ${r.status}`);
  return r.json();
}

// In a production build there is no backend: read the precomputed static
// snapshot instead (deterministic, zero cold start). In dev, hit the live API.
const STATIC = import.meta.env.PROD;

let simMapP: Promise<Record<string, SimResult>> | null = null;
let insMapP: Promise<Record<string, Insight>> | null = null;
const simMap = () => (simMapP ??= get<Record<string, SimResult>>("/snapshot/simulate.json"));
const insMap = () => (insMapP ??= get<Record<string, Insight>>("/snapshot/insight.json"));

export const api = {
  overview: () => get<Overview>(STATIC ? "/snapshot/overview.json" : "/api/overview"),
  recommendations: () =>
    get<{ recommendations: Recommendation[] }>(STATIC ? "/snapshot/recommendations.json" : "/api/recommendations?limit=8"),
  validation: () => get<Validation>(STATIC ? "/snapshot/validation.json" : "/api/validation"),
  simulate: async (intervention: string, segment: string): Promise<SimResult> => {
    if (STATIC) return (await simMap())[`${intervention}__${segment}`];
    const r = await fetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intervention, segment }),
    });
    if (!r.ok) throw new Error(`simulate -> ${r.status}`);
    return r.json();
  },
  interventionInsight: async (intervention: string, segment: string): Promise<Insight> => {
    if (STATIC) return (await insMap())[`${intervention}__${segment}`];
    return get<Insight>(`/api/insight/intervention?intervention=${intervention}&segment=${segment}`);
  },
};

// --- formatting helpers -----------------------------------------------------
export const pct = (x: number, d = 1) => `${(x * 100).toFixed(d)}%`;
export const signedPct = (x: number, d = 1) => `${x >= 0 ? "+" : ""}${(x * 100).toFixed(d)}%`;
export const usd = (x: number) =>
  x >= 1000 ? `$${(x / 1000).toFixed(1)}k` : `$${x.toFixed(0)}`;
export const usdFull = (x: number) => `$${Math.round(x).toLocaleString()}`;
export const num = (x: number) => Math.round(x).toLocaleString();
