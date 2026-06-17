"""Synthetic omnichannel customer-journey generator.

Produces two tables:
  * customers.parquet   — one row per customer: latent features, furthest funnel
                          stage, treatment assignment, factual outcome, and the
                          GROUND-TRUTH potential outcomes (p0 and p1 per
                          intervention). The potential outcomes are what make
                          honest predicted-vs-actual validation possible.
  * touchpoints.parquet — one row per touchpoint (customer_id, order, channel,
                          stage, timestamp) for the funnel / Sankey / sequence
                          visualisations.

Everything is seeded for reproducibility.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Make `import config` work regardless of where this script is run from.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import config as C  # noqa: E402


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


# ---------------------------------------------------------------------------
# GROUND-TRUTH treatment effect (the "oracle" we later validate against).
#
# tau = absolute lift in Intent->Purchase conversion probability, heterogeneous
# by segment. Some interventions additionally scale with price sensitivity.
# These numbers are the secret the uplift model is NOT told; it must recover
# them from factual outcomes alone.
# ---------------------------------------------------------------------------
TAU_BASE = {
    # intervention            bargain  loyalist  browser  high_intent
    "cart_recovery_push": {"bargain_hunter": 0.10, "loyalist": 0.03, "browser": 0.05, "high_intent": 0.14},
    "personalized_email": {"bargain_hunter": 0.05, "loyalist": 0.10, "browser": 0.08, "high_intent": 0.06},
    "sms_discount":       {"bargain_hunter": 0.12, "loyalist": 0.02, "browser": 0.04, "high_intent": 0.08},
    "retargeting_social": {"bargain_hunter": 0.04, "loyalist": 0.04, "browser": 0.11, "high_intent": 0.05},
}


def true_tau(intervention: str, segment: np.ndarray, price_sensitivity: np.ndarray) -> np.ndarray:
    """Vectorised ground-truth CATE (absolute prob-point lift) per customer."""
    base = np.array([TAU_BASE[intervention][s] for s in segment])
    if intervention == "sms_discount":
        # Discounts over-index on the price-sensitive: scale 0.5x..1.5x.
        base = base * (0.5 + price_sensitivity)
    elif intervention == "cart_recovery_push":
        # Slightly stronger for the already-engaged (higher price sens hesitates less here).
        base = base * (1.2 - 0.4 * price_sensitivity)
    return base


def main() -> None:
    rng = np.random.default_rng(C.SEED)
    n = C.N_CUSTOMERS

    # --- Latent customer features ------------------------------------------
    seg_keys = C.SEGMENT_KEYS
    seg_probs = np.array([C.SEGMENTS[k]["prop"] for k in seg_keys])
    seg_probs = seg_probs / seg_probs.sum()
    segment = rng.choice(seg_keys, size=n, p=seg_probs)

    engagement = rng.beta(2.0, 2.0, size=n)             # 0..1, centred ~0.5
    price_sensitivity = rng.beta(2.0, 2.0, size=n)      # 0..1

    # Preferred channel skews by segment (purely for realism / viz).
    channel_pref = {
        "bargain_hunter": [0.10, 0.15, 0.20, 0.10, 0.30, 0.15],  # likes sms
        "loyalist":       [0.30, 0.05, 0.25, 0.20, 0.05, 0.15],  # likes email/app
        "browser":        [0.10, 0.30, 0.30, 0.05, 0.05, 0.20],  # likes paid_social/web
        "high_intent":    [0.20, 0.15, 0.30, 0.20, 0.05, 0.10],
    }
    preferred_channel = np.array([
        rng.choice(C.CHANNELS, p=channel_pref[s]) for s in segment
    ])

    # --- Funnel progression (Awareness -> Consideration -> Intent) ---------
    seg_intent_offset = {"bargain_hunter": -0.1, "loyalist": 0.3, "browser": -0.4, "high_intent": 0.8}
    intent_off = np.array([seg_intent_offset[s] for s in segment])

    p_consideration = _sigmoid(1.1 + 1.4 * (engagement - 0.5))
    reached_consideration = rng.random(n) < p_consideration

    p_intent = _sigmoid(0.65 + 1.6 * (engagement - 0.5) + intent_off)
    reached_intent = reached_consideration & (rng.random(n) < p_intent)

    # --- Baseline Intent->Purchase probability p0 (control) ----------------
    seg_purchase_offset = {"bargain_hunter": -0.4, "loyalist": 0.5, "browser": -0.2, "high_intent": 0.8}
    purch_off = np.array([seg_purchase_offset[s] for s in segment])
    logit_p0 = (
        -0.9
        + purch_off
        + 1.2 * (engagement - 0.5)
        - 1.0 * (price_sensitivity - 0.5)
        + rng.normal(0, 0.25, size=n)
    )
    p0 = _sigmoid(logit_p0)

    # --- Ground-truth treated probabilities p1 per intervention ------------
    p1 = {}
    for k in C.INTERVENTION_KEYS:
        tau = true_tau(k, segment, price_sensitivity)
        p1[k] = np.clip(p0 + tau, 0.0, 0.98)

    # --- Treatment assignment over the addressable (reached-Intent) pool ----
    groups = ["control"] + C.INTERVENTION_KEYS
    group_probs = [C.CONTROL_SHARE] + [C.TREATMENT_SHARE] * len(C.INTERVENTION_KEYS)
    assigned = np.array(["none"] * n, dtype=object)
    pool_idx = np.where(reached_intent)[0]
    assigned[pool_idx] = rng.choice(groups, size=pool_idx.size, p=group_probs)

    # --- Factual purchase outcome under the assigned treatment -------------
    purchase_prob = p0.copy()
    for k in C.INTERVENTION_KEYS:
        mask = assigned == k
        purchase_prob[mask] = p1[k][mask]
    converted = np.zeros(n, dtype=int)
    converted[pool_idx] = (rng.random(pool_idx.size) < purchase_prob[pool_idx]).astype(int)

    reached_purchase = reached_intent & (converted == 1)
    p_retention = _sigmoid(0.3 + 1.0 * (engagement - 0.5))
    reached_retention = reached_purchase & (rng.random(n) < p_retention)

    furthest = np.full(n, "Awareness", dtype=object)
    furthest[reached_consideration] = "Consideration"
    furthest[reached_intent] = "Intent"
    furthest[reached_purchase] = "Purchase"
    furthest[reached_retention] = "Retention"

    customers = pd.DataFrame({
        "customer_id": np.arange(n),
        "segment": segment,
        "engagement_propensity": engagement,
        "price_sensitivity": price_sensitivity,
        "preferred_channel": preferred_channel,
        "furthest_stage": furthest,
        "reached_consideration": reached_consideration,
        "reached_intent": reached_intent,
        "reached_purchase": reached_purchase,
        "reached_retention": reached_retention,
        "assigned_treatment": assigned,
        "converted": converted,
        "p0": p0,
    })
    for k in C.INTERVENTION_KEYS:
        customers[f"p1_{k}"] = p1[k]

    # --- Touchpoints (for funnel / Sankey / sequence viz) ------------------
    stage_rank = {s: i for i, s in enumerate(C.STAGES)}
    rows = []
    base_ts = np.datetime64("2026-01-01T00:00:00")
    for cid, seg, pch, fstage in zip(
        customers.customer_id, segment, preferred_channel, furthest
    ):
        max_rank = stage_rank[fstage]
        t = base_ts + np.timedelta64(int(rng.integers(0, 60 * 24 * 60)), "m")
        order = 0
        for sr in range(max_rank + 1):
            stage = C.STAGES[sr]
            n_tp = 1 + int(rng.integers(0, 3))  # 1-3 touchpoints per reached stage
            for _ in range(n_tp):
                # Bias toward preferred channel, otherwise random.
                ch = pch if rng.random() < 0.45 else rng.choice(C.CHANNELS)
                t = t + np.timedelta64(int(rng.integers(30, 60 * 48)), "m")
                rows.append((int(cid), order, ch, stage, t))
                order += 1
    touchpoints = pd.DataFrame(rows, columns=["customer_id", "order", "channel", "stage", "timestamp"])

    C.DATA_DIR.mkdir(parents=True, exist_ok=True)
    customers.to_parquet(C.CUSTOMERS_PARQUET, index=False)
    touchpoints.to_parquet(C.TOUCHPOINTS_PARQUET, index=False)

    # --- Console summary ---------------------------------------------------
    print(f"Customers: {len(customers):,}   Touchpoints: {len(touchpoints):,}")
    print("\nFunnel (overall):")
    funnel = {
        "Awareness": n,
        "Consideration": int(reached_consideration.sum()),
        "Intent": int(reached_intent.sum()),
        "Purchase": int(reached_purchase.sum()),
        "Retention": int(reached_retention.sum()),
    }
    prev = n
    for stage, cnt in funnel.items():
        step = f"{cnt / prev * 100:5.1f}% of prev" if stage != "Awareness" else "  ---"
        print(f"  {stage:14s} {cnt:6,d}  ({cnt / n * 100:5.1f}% of all)  {step}")
        prev = cnt
    pool = customers[customers.reached_intent]
    print(f"\nIntent->Purchase conversion (control truth) by segment:")
    for s in C.SEGMENT_KEYS:
        sp = pool[pool.segment == s]
        print(f"  {C.SEGMENTS[s]['label']:14s} base p0 = {sp.p0.mean() * 100:5.1f}%   n={len(sp):,}")


if __name__ == "__main__":
    main()
