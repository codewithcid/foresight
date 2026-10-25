import { useEffect, useState } from "react";
import { api, signedPct } from "./api";
import type { Insight, Overview, Recommendation, SimResult, Validation } from "./api";
import Funnel from "./components/Funnel";
import JourneySankey from "./components/JourneySankey";
import FrictionPanel from "./components/FrictionPanel";
import Recommendations from "./components/Recommendations";
import Simulator from "./components/Simulator";
import ValidationPanel from "./components/ValidationPanel";

export default function App() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [validation, setValidation] = useState<Validation | null>(null);
  const [selected, setSelected] = useState({ intervention: "cart_recovery_push", segment: "bargain_hunter" });
  const [sim, setSim] = useState<SimResult | null>(null);
  const [simInsight, setSimInsight] = useState<Insight | null>(null);
  const [simLoading, setSimLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.overview(), api.recommendations(), api.validation()])
      .then(([ov, rc, val]) => {
        setOverview(ov);
        setRecs(rc.recommendations);
        setValidation(val);
        if (rc.recommendations[0]) {
          const top = rc.recommendations[0];
          setSelected({ intervention: top.intervention, segment: top.segment });
        }
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    setSimLoading(true);
    api.simulate(selected.intervention, selected.segment)
      .then(setSim)
      .catch((e) => setError(String(e)))
      .finally(() => setSimLoading(false));
    setSimInsight(null);
    api.interventionInsight(selected.intervention, selected.segment)
      .then(setSimInsight)
      .catch(() => setSimInsight(null));
  }, [selected]);

  if (error) {
    return (
      <div className="flex h-full items-center justify-center p-8 text-center">
        <div>
          <div className="text-bad">Could not reach the Foresight API.</div>
          <div className="mt-2 stat text-xs text-slate-500">{error}</div>
          <div className="mt-2 text-xs text-slate-500">Is the backend running on :8000?</div>
        </div>
      </div>
    );
  }

  if (!overview || !validation) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="animate-pulse text-slate-500">Loading customer journeys…</div>
      </div>
    );
  }

  const acc = validation.headline;

  return (
    <div className="mx-auto max-w-[1280px] px-5 py-6">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-brand/20 text-lg">◎</div>
            <h1 className="text-2xl font-extrabold tracking-tight text-white">Foresight</h1>
            <span className="pill">Customer Journey Intelligence</span>
          </div>
          <p className="mt-1.5 max-w-2xl text-sm text-slate-400">
            Predict the lift of a marketing intervention <span className="text-slate-200">before you spend a cent</span> —
            and prove the prediction against held-out ground truth.
          </p>
        </div>
        <div className="rounded-xl border border-good/30 bg-good/[0.06] px-4 py-2 text-right">
          <div className="text-[11px] uppercase tracking-wider text-slate-500">Model validation</div>
          <div className="stat text-lg font-bold text-good">
            {signedPct(acc.predicted_rel_lift, 0)} vs {signedPct(acc.actual_rel_lift, 0)}
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <div className="lg:col-span-7"><Funnel funnel={overview.funnel} /></div>
        <div className="lg:col-span-5">
          <FrictionPanel overview={overview} narrative={overview.narrative} narrativeSource={overview.narrative_source} />
        </div>

        <div className="lg:col-span-12"><JourneySankey funnel={overview.funnel} /></div>

        <div className="lg:col-span-5">
          <Simulator
            meta={overview.meta}
            selected={selected}
            onChange={(intervention, segment) => setSelected({ intervention, segment })}
            result={sim}
            insight={simInsight}
            loading={simLoading}
          />
        </div>
        <div className="lg:col-span-7">
          <ValidationPanel validation={validation} selected={selected} />
        </div>

        <div className="lg:col-span-12">
          <Recommendations
            recs={recs}
            selected={selected}
            onPick={(intervention, segment) => setSelected({ intervention, segment })}
          />
        </div>
      </div>

      <footer className="mt-8 text-center text-[11px] text-slate-600">
        Foresight · synthetic omnichannel data · uplift via S-learner · built for Epsilon TeXpedition
      </footer>
    </div>
  );
}
