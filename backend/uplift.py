"""Uplift / what-if engine.

Primary model is an **S-learner**: one LightGBM conversion model trained on the
addressable (reached-Intent) pool with the intervention encoded as a feature.
Predicting the same customer under treatment vs control gives the counterfactual
uplift tau_hat(X). The S-learner is chosen over a T-learner here because it uses
ALL outcomes in a single model (far more sample-efficient on a ~4k pool), while
LightGBM's trees still capture the segment x intervention heterogeneity.

Exposes:
  * simulate(intervention, segment) -> predicted lift, incremental conversions,
    revenue, ROI, and a bootstrap confidence interval.
  * rank_interventions()           -> candidates ranked by lift x reach / cost.
  * validate()                     -> predicted vs ground-truth (held-out) lift.
"""
from __future__ import annotations

from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
import pandas as pd

import config as C

# Fixed feature column order so train/predict always align.
_SEG_COLS = [f"seg_{s}" for s in C.SEGMENT_KEYS]
_CH_COLS = [f"ch_{c}" for c in C.CHANNELS]
_TRT_COLS = [f"trt_{t}" for t in (["control"] + C.INTERVENTION_KEYS)]
_NUM_COLS = ["engagement_propensity", "price_sensitivity"]
FEATURE_COLS = _SEG_COLS + _CH_COLS + _NUM_COLS + _TRT_COLS


def _base_features(df: pd.DataFrame) -> pd.DataFrame:
    """Customer features WITHOUT the treatment block (added per-scenario)."""
    out = pd.DataFrame(index=df.index)
    for s in C.SEGMENT_KEYS:
        out[f"seg_{s}"] = (df["segment"] == s).astype(float)
    for c in C.CHANNELS:
        out[f"ch_{c}"] = (df["preferred_channel"] == c).astype(float)
    out["engagement_propensity"] = df["engagement_propensity"].values
    out["price_sensitivity"] = df["price_sensitivity"].values
    return out


def _with_treatment(base: pd.DataFrame, treatment: str) -> pd.DataFrame:
    """Attach a one-hot treatment block, returning full FEATURE_COLS frame."""
    out = base.copy()
    for t in ["control"] + C.INTERVENTION_KEYS:
        out[f"trt_{t}"] = 1.0 if t == treatment else 0.0
    return out[FEATURE_COLS]


@dataclass
class SimResult:
    intervention: str
    segment: str
    reach: int
    baseline_conv: float          # control conversion rate (fraction)
    predicted_abs_lift: float     # absolute prob-point lift (fraction)
    predicted_rel_lift: float     # relative lift over baseline (fraction)
    incremental_conversions: float
    projected_revenue: float
    cost: float
    roi: float
    rel_lift_ci: tuple[float, float]
    revenue_ci: tuple[float, float]


class UpliftEngine:
    def __init__(self, customers: pd.DataFrame | None = None, seed: int = C.SEED,
                 method: str = "s"):
        self.seed = seed
        self.method = method  # "s" = S-learner (default, best validation), "t" = T-learner
        self.customers = customers if customers is not None else pd.read_parquet(C.CUSTOMERS_PARQUET)
        self.pool = self.customers[self.customers.reached_intent].reset_index(drop=True)
        self.model: lgb.LGBMClassifier | None = None          # S-learner
        self.models: dict[str, lgb.LGBMClassifier] = {}       # T-learner (per arm)
        self.train_idx: np.ndarray | None = None
        self.test_idx: np.ndarray | None = None
        # Std of held-out relative-lift residuals = the model's own uncertainty,
        # folded into every simulated confidence interval so it reflects how
        # wrong the model typically is (not just sampling noise).
        self.model_rel_sigma: float = 0.0

    def _make_clf(self, n: int) -> lgb.LGBMClassifier:
        # Lighter trees for the smaller per-arm T-learner models.
        leaves = 31 if n > 1500 else 15
        return lgb.LGBMClassifier(
            n_estimators=300, learning_rate=0.05, num_leaves=leaves,
            min_child_samples=30, subsample=0.9, colsample_bytree=0.9,
            random_state=self.seed, verbose=-1,
        )

    # ------------------------------------------------------------------ train
    def train(self) -> None:
        pool = self.pool
        rng = np.random.default_rng(self.seed)
        perm = rng.permutation(len(pool))
        n_test = int(len(pool) * C.TEST_SIZE)
        self.test_idx = perm[:n_test]
        self.train_idx = perm[n_test:]
        train = pool.iloc[self.train_idx]

        if self.method == "s":
            # S-learner: one model, treatment one-hot from factual assignment.
            feat = _base_features(train)
            assigned = train["assigned_treatment"].values
            for t in ["control"] + C.INTERVENTION_KEYS:
                feat[f"trt_{t}"] = (assigned == t).astype(float)
            self.model = self._make_clf(len(train))
            self.model.fit(feat[FEATURE_COLS], train["converted"].values)
        else:
            # T-learner: one conversion model per arm (control + each intervention).
            for t in ["control"] + C.INTERVENTION_KEYS:
                sub = train[train.assigned_treatment == t]
                clf = self._make_clf(len(sub))
                clf.fit(_base_features(sub), sub["converted"].values)
                self.models[t] = clf

        # Calibrate model uncertainty from held-out per-cell residuals.
        residuals = [c["predicted_rel_lift"] - c["actual_rel_lift"]
                     for c in self.validate()["per_cell"]]
        self.model_rel_sigma = float(np.std(residuals)) if residuals else 0.0

    # ------------------------------------------------------------- prediction
    def _predict_prob(self, df: pd.DataFrame, treatment: str) -> np.ndarray:
        if self.method == "s":
            X = _with_treatment(_base_features(df), treatment)
            return self.model.predict_proba(X)[:, 1]
        return self.models[treatment].predict_proba(_base_features(df))[:, 1]

    def _tau(self, df: pd.DataFrame, intervention: str) -> np.ndarray:
        return self._predict_prob(df, intervention) - self._predict_prob(df, "control")

    # ---------------------------------------------------------------- segment
    def _segment_pool(self, segment: str, split: str = "all") -> pd.DataFrame:
        if split == "test":
            df = self.pool.iloc[self.test_idx]
        elif split == "train":
            df = self.pool.iloc[self.train_idx]
        else:
            df = self.pool
        if segment != "all":
            df = df[df.segment == segment]
        return df

    # --------------------------------------------------------------- simulate
    def simulate(self, intervention: str, segment: str, n_boot: int = 200) -> SimResult:
        df = self._segment_pool(segment, split="all")
        reach = len(df)
        ctrl = self._predict_prob(df, "control")
        tau = self._predict_prob(df, intervention) - ctrl

        baseline = float(ctrl.mean())
        abs_lift = float(tau.mean())
        rel_lift = abs_lift / baseline if baseline > 0 else 0.0
        incremental = abs_lift * reach
        revenue = incremental * C.AOV
        cost = reach * C.INTERVENTIONS[intervention]["cost_per_contact"]
        roi = (revenue - cost) / cost if cost > 0 else 0.0

        # CI combines (a) sampling variance over the segment population via a
        # bootstrap with (b) the model's own held-out error (model_rel_sigma).
        rng = np.random.default_rng(self.seed)
        boot_rel = []
        for _ in range(n_boot):
            idx = rng.integers(0, reach, size=reach)
            b_base = ctrl[idx].mean()
            boot_rel.append(tau[idx].mean() / b_base if b_base > 0 else 0.0)
        samp_std = float(np.std(boot_rel)) if n_boot > 0 else 0.0
        total_std = (samp_std ** 2 + self.model_rel_sigma ** 2) ** 0.5
        z = 1.64  # ~90%
        rel_ci = (rel_lift - z * total_std, rel_lift + z * total_std)
        # Propagate the same relative uncertainty to revenue (revenue ∝ lift).
        rev_sigma = total_std * baseline * reach * C.AOV
        rev_ci = (max(0.0, revenue - z * rev_sigma), revenue + z * rev_sigma)

        return SimResult(
            intervention=intervention, segment=segment, reach=reach,
            baseline_conv=baseline, predicted_abs_lift=abs_lift,
            predicted_rel_lift=rel_lift, incremental_conversions=incremental,
            projected_revenue=revenue, cost=cost, roi=roi,
            rel_lift_ci=rel_ci, revenue_ci=rev_ci,
        )

    # -------------------------------------------------------------- ranking
    def rank_interventions(self) -> list[dict]:
        rows = []
        for k in C.INTERVENTION_KEYS:
            for s in C.SEGMENT_KEYS:
                r = self.simulate(k, s, n_boot=0) if False else self.simulate(k, s, n_boot=60)
                score = r.predicted_abs_lift * r.reach / max(r.cost, 1e-9)
                rows.append({
                    "intervention": k, "intervention_label": C.INTERVENTIONS[k]["label"],
                    "segment": s, "segment_label": C.SEGMENTS[s]["label"],
                    "predicted_rel_lift": r.predicted_rel_lift,
                    "incremental_conversions": r.incremental_conversions,
                    "projected_revenue": r.projected_revenue, "cost": r.cost,
                    "roi": r.roi, "reach": r.reach, "score": score,
                })
        rows.sort(key=lambda d: d["score"], reverse=True)
        return rows

    # -------------------------------------------------------------- validate
    def validate(self) -> dict:
        """Predicted vs ground-truth (held-out) lift on the test set."""
        test = self.pool.iloc[self.test_idx]
        per_cell = []
        for k in C.INTERVENTION_KEYS:
            for s in C.SEGMENT_KEYS:
                df = test[test.segment == s]
                if len(df) == 0:
                    continue
                # Predicted (model)
                ctrl = self._predict_prob(df, "control")
                pred_abs = (self._predict_prob(df, k) - ctrl).mean()
                pred_rel = pred_abs / ctrl.mean()
                # Actual (generator ground truth — the oracle)
                true_abs = (df[f"p1_{k}"] - df["p0"]).mean()
                true_rel = true_abs / df["p0"].mean()
                per_cell.append({
                    "intervention": k, "intervention_label": C.INTERVENTIONS[k]["label"],
                    "segment": s, "segment_label": C.SEGMENTS[s]["label"],
                    "predicted_rel_lift": float(pred_rel), "actual_rel_lift": float(true_rel),
                    "abs_error": float(abs(pred_rel - true_rel)),
                    "n": int(len(df)),
                })
        # Aggregate headline per intervention (averaged over segments, test pop).
        per_intervention = []
        for k in C.INTERVENTION_KEYS:
            df = test
            ctrl = self._predict_prob(df, "control")
            pred_rel = (self._predict_prob(df, k) - ctrl).mean() / ctrl.mean()
            true_rel = (df[f"p1_{k}"] - df["p0"]).mean() / df["p0"].mean()
            per_intervention.append({
                "intervention": k, "intervention_label": C.INTERVENTIONS[k]["label"],
                "predicted_rel_lift": float(pred_rel), "actual_rel_lift": float(true_rel),
                "abs_error": float(abs(pred_rel - true_rel)),
            })
        mae = float(np.mean([c["abs_error"] for c in per_cell]))
        return {"per_cell": per_cell, "per_intervention": per_intervention, "cell_mae": mae}


def _fmt_pct(x: float) -> str:
    return f"{x * 100:+.1f}%"


if __name__ == "__main__":
    eng = UpliftEngine()
    eng.train()

    print("=" * 64)
    print("VALIDATION — predicted vs actual (held-out) RELATIVE lift")
    print("=" * 64)
    val = eng.validate()
    print(f"\nPer-intervention (averaged across all segments, test set):")
    print(f"  {'Intervention':24s} {'Predicted':>10s} {'Actual':>10s} {'Err':>7s}")
    for r in val["per_intervention"]:
        print(f"  {r['intervention_label']:24s} {_fmt_pct(r['predicted_rel_lift']):>10s} "
              f"{_fmt_pct(r['actual_rel_lift']):>10s} {r['abs_error'] * 100:6.1f}pp")
    print(f"\nPer-cell mean abs error: {val['cell_mae'] * 100:.1f} pp")

    print("\n" + "=" * 64)
    print("TOP RANKED INTERVENTIONS (by lift x reach / cost)")
    print("=" * 64)
    for r in eng.rank_interventions()[:5]:
        print(f"  {r['intervention_label']:22s} -> {r['segment_label']:14s} "
              f"lift {_fmt_pct(r['predicted_rel_lift'])}  "
              f"+{r['incremental_conversions']:5.0f} conv  "
              f"${r['projected_revenue']:8,.0f}  ROI {r['roi']:6.0f}x")

    print("\n" + "=" * 64)
    print("SAMPLE SIMULATION")
    print("=" * 64)
    r = eng.simulate("cart_recovery_push", "bargain_hunter")
    print(f"  {C.INTERVENTIONS[r.intervention]['label']} -> {C.SEGMENTS[r.segment]['label']}")
    print(f"    reach={r.reach:,}  baseline={r.baseline_conv*100:.1f}%")
    print(f"    predicted lift {_fmt_pct(r.predicted_rel_lift)} "
          f"(90% CI {_fmt_pct(r.rel_lift_ci[0])}..{_fmt_pct(r.rel_lift_ci[1])})")
    print(f"    +{r.incremental_conversions:.0f} conversions  "
          f"${r.projected_revenue:,.0f} revenue (CI ${r.revenue_ci[0]:,.0f}..${r.revenue_ci[1]:,.0f})")
    print(f"    cost ${r.cost:,.2f}  ROI {r.roi:,.0f}x")
