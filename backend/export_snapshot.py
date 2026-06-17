"""Export a static snapshot of every API response to frontend/public/snapshot/.

Because every dashboard input is a fixed dropdown combo (4 interventions x
{all + 4 segments} = 20), the entire app can run as a pure static site with no
backend. This bakes in the precomputed panels AND the cached Gemini narratives,
so the deployed demo has zero cold starts, zero backend to fail, and no API key
shipped to the client. Shapes match the live endpoints exactly.

Run with the cache already warmed (so narratives are 'ai'):
    ../.venv/Scripts/python.exe export_snapshot.py
"""
from __future__ import annotations

import dataclasses
import json

import pandas as pd

import config as C
import insights
from analysis import detect_friction
from uplift import UpliftEngine

OUT = C.ROOT / "frontend" / "public" / "snapshot"


def _meta() -> dict:
    return {
        "segments": [{"key": k, "label": v["label"]} for k, v in C.SEGMENTS.items()],
        "interventions": [
            {"key": k, "label": v["label"], "channel": v["channel"],
             "cost_per_contact": v["cost_per_contact"]}
            for k, v in C.INTERVENTIONS.items()
        ],
        "aov": C.AOV,
        "stages": C.STAGES,
    }


def _sim_dict(engine: UpliftEngine, intervention: str, segment: str) -> dict:
    res = engine.simulate(intervention, segment)
    out = dataclasses.asdict(res)
    out["intervention_label"] = C.INTERVENTIONS[intervention]["label"]
    out["segment_label"] = "All segments" if segment == "all" else C.SEGMENTS[segment]["label"]
    return out


def main() -> None:
    customers = pd.read_parquet(C.CUSTOMERS_PARQUET)
    touchpoints = pd.read_parquet(C.TOUCHPOINTS_PARQUET)
    engine = UpliftEngine(customers=customers)
    engine.train()

    friction = detect_friction(customers, touchpoints)
    nar = insights.friction_narrative(friction)
    recommendations = engine.rank_interventions()
    validation = engine.validate()
    top = recommendations[0]["intervention"]
    validation = {**validation,
                  "headline": next(r for r in validation["per_intervention"] if r["intervention"] == top)}

    segments = ["all"] + C.SEGMENT_KEYS
    sim_map, insight_map = {}, {}
    ai = 0
    for k in C.INTERVENTION_KEYS:
        for s in segments:
            key = f"{k}__{s}"
            sim = _sim_dict(engine, k, s)
            sim_map[key] = sim
            ins = insights.intervention_narrative(sim)
            insight_map[key] = ins
            ai += ins["source"] == "ai"

    overview = {**friction, "narrative": nar["text"],
                "narrative_source": nar["source"], "meta": _meta()}

    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        "overview.json": overview,
        "recommendations.json": {"recommendations": recommendations[:8]},
        "validation.json": validation,
        "simulate.json": sim_map,
        "insight.json": insight_map,
    }
    for name, data in files.items():
        (OUT / name).write_text(json.dumps(data), encoding="utf-8")

    print(f"Snapshot written to {OUT}")
    print(f"  friction narrative: {nar['source']}")
    print(f"  intervention narratives: {ai}/{len(sim_map)} ai")
    print(f"  files: {', '.join(files)}")


if __name__ == "__main__":
    main()
