"""Friction detection over the synthetic journeys.

Pure descriptive analytics (no model): funnel conversion per stage, the biggest
drop-off, per-segment friction at the worst transition, channel patterns that
correlate with conversion, and a Sankey-ready flow with explicit drop-off
branches. Everything returns plain dicts ready for JSON serialisation.
"""
from __future__ import annotations

import pandas as pd

import config as C


def compute_funnel(customers: pd.DataFrame) -> dict:
    n = len(customers)
    counts = {
        "Awareness": n,
        "Consideration": int(customers.reached_consideration.sum()),
        "Intent": int(customers.reached_intent.sum()),
        "Purchase": int(customers.reached_purchase.sum()),
        "Retention": int(customers.reached_retention.sum()),
    }
    stages = []
    prev = None
    for stage in C.STAGES:
        cnt = counts[stage]
        step_conv = (cnt / prev) if prev else 1.0
        stages.append({
            "stage": stage,
            "count": cnt,
            "pct_of_total": cnt / n,
            "step_conversion": step_conv,   # vs previous stage
            "drop_off": (1 - step_conv) if prev else 0.0,
        })
        prev = cnt
    # Biggest drop-off transition (exclude the trivial Awareness anchor).
    worst = max(stages[1:], key=lambda s: s["drop_off"])
    worst_idx = C.STAGES.index(worst["stage"])
    return {
        "stages": stages,
        "biggest_drop": {
            "from_stage": C.STAGES[worst_idx - 1],
            "to_stage": worst["stage"],
            "step_conversion": worst["step_conversion"],
            "drop_off": worst["drop_off"],
            "lost_customers": counts[C.STAGES[worst_idx - 1]] - counts[worst["stage"]],
        },
    }


def compute_segment_friction(customers: pd.DataFrame) -> dict:
    """Intent->Purchase conversion per segment (the worst transition)."""
    pool = customers[customers.reached_intent]
    rows = []
    for s in C.SEGMENT_KEYS:
        sp = pool[pool.segment == s]
        conv = float(sp.reached_purchase.mean()) if len(sp) else 0.0
        rows.append({
            "segment": s,
            "segment_label": C.SEGMENTS[s]["label"],
            "intent_pool": int(len(sp)),
            "purchase_conversion": conv,
            "abandonment": 1 - conv,
            "avg_price_sensitivity": float(sp.price_sensitivity.mean()) if len(sp) else 0.0,
        })
    rows.sort(key=lambda r: r["purchase_conversion"])  # worst first
    return {"transition": "Intent->Purchase", "by_segment": rows, "worst_segment": rows[0]}


def compute_channel_patterns(customers: pd.DataFrame, touchpoints: pd.DataFrame) -> dict:
    """Which channels correlate with conversion among the Intent pool."""
    pool = customers[customers.reached_intent][["customer_id", "reached_purchase"]]
    base_conv = float(pool.reached_purchase.mean())
    tp = touchpoints.merge(pool, on="customer_id", how="inner")
    rows = []
    for ch in C.CHANNELS:
        seen = tp[tp.channel == ch]["customer_id"].unique()
        if len(seen) == 0:
            continue
        mask = pool.customer_id.isin(seen)
        conv_with = float(pool[mask].reached_purchase.mean())
        rows.append({
            "channel": ch,
            "reach": int(len(seen)),
            "conversion_with_channel": conv_with,
            "lift_vs_baseline": conv_with - base_conv,
        })
    rows.sort(key=lambda r: r["lift_vs_baseline"], reverse=True)
    return {"baseline_conversion": base_conv, "channels": rows}


def compute_sankey(customers: pd.DataFrame) -> dict:
    """Stage-to-stage flow with explicit drop-off branches for a Sankey."""
    counts = {
        "Awareness": len(customers),
        "Consideration": int(customers.reached_consideration.sum()),
        "Intent": int(customers.reached_intent.sum()),
        "Purchase": int(customers.reached_purchase.sum()),
        "Retention": int(customers.reached_retention.sum()),
    }
    nodes = list(C.STAGES) + [f"Dropped at {s}" for s in C.STAGES[:-1]]
    links = []
    for i in range(len(C.STAGES) - 1):
        src, dst = C.STAGES[i], C.STAGES[i + 1]
        advanced = counts[dst]
        dropped = counts[src] - counts[dst]
        links.append({"source": src, "target": dst, "value": advanced})
        if dropped > 0:
            links.append({"source": src, "target": f"Dropped at {src}", "value": dropped})
    return {"nodes": nodes, "links": links}


def detect_friction(customers: pd.DataFrame, touchpoints: pd.DataFrame) -> dict:
    """Top-level friction report bundling all of the above."""
    funnel = compute_funnel(customers)
    seg = compute_segment_friction(customers)
    chan = compute_channel_patterns(customers, touchpoints)
    drop = funnel["biggest_drop"]
    worst_seg = seg["worst_segment"]
    headline = (
        f"{drop['from_stage']}->{drop['to_stage']} is the biggest leak: only "
        f"{drop['step_conversion']*100:.0f}% advance, losing {drop['lost_customers']:,} "
        f"customers. The {worst_seg['segment_label']} segment is worst, converting "
        f"just {worst_seg['purchase_conversion']*100:.0f}%."
    )
    return {
        "funnel": funnel,
        "segment_friction": seg,
        "channel_patterns": chan,
        "sankey": compute_sankey(customers),
        "headline": headline,
    }
