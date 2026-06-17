"""Foresight API.

On startup: load the synthetic data, train the uplift engine once, and cache the
static panels (friction, recommendations, validation). The headline demo flow is
served from this in-memory cache so it never depends on a live recompute; only
the interactive simulator runs per-request (deterministic, ~instant).
"""
from __future__ import annotations

import dataclasses
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config as C
import insights
from analysis import detect_friction
from uplift import UpliftEngine

STATE: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    customers = pd.read_parquet(C.CUSTOMERS_PARQUET)
    touchpoints = pd.read_parquet(C.TOUCHPOINTS_PARQUET)
    engine = UpliftEngine(customers=customers)
    engine.train()

    STATE["engine"] = engine
    STATE["friction"] = detect_friction(customers, touchpoints)
    STATE["recommendations"] = engine.rank_interventions()
    STATE["validation"] = engine.validate()
    STATE["friction_narrative"] = insights.friction_narrative(STATE["friction"])
    print(f"[foresight] ready: {len(customers):,} customers, model={engine.method}-learner, "
          f"llm={'gemini' if insights.has_key() else 'fallback'}")
    yield
    STATE.clear()


app = FastAPI(title="Foresight API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


class SimulateRequest(BaseModel):
    intervention: str
    segment: str  # a segment key or "all"


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


@app.get("/api/health")
def health():
    return {"status": "ok", "ready": "engine" in STATE}


@app.get("/api/meta")
def meta():
    return _meta()


@app.get("/api/overview")
def overview():
    """Everything the dashboard needs for the funnel + friction panels."""
    nar = STATE["friction_narrative"]
    return {**STATE["friction"], "narrative": nar["text"], "narrative_source": nar["source"],
            "meta": _meta()}


@app.get("/api/recommendations")
def recommendations(limit: int = 8):
    return {"recommendations": STATE["recommendations"][:limit]}


@app.get("/api/validation")
def validation():
    val = STATE["validation"]
    # Headline = the top-recommended intervention's aggregate predicted vs actual.
    top_intervention = STATE["recommendations"][0]["intervention"]
    headline = next(r for r in val["per_intervention"] if r["intervention"] == top_intervention)
    return {**val, "headline": headline}


@app.post("/api/simulate")
def simulate(req: SimulateRequest):
    if req.intervention not in C.INTERVENTION_KEYS:
        raise HTTPException(400, f"unknown intervention {req.intervention!r}")
    if req.segment not in C.SEGMENT_KEYS and req.segment != "all":
        raise HTTPException(400, f"unknown segment {req.segment!r}")
    res = STATE["engine"].simulate(req.intervention, req.segment)
    out = dataclasses.asdict(res)
    out["intervention_label"] = C.INTERVENTIONS[req.intervention]["label"]
    out["segment_label"] = "All segments" if req.segment == "all" else C.SEGMENTS[req.segment]["label"]
    return out


@app.get("/api/insight/intervention")
def insight_intervention(intervention: str, segment: str):
    if intervention not in C.INTERVENTION_KEYS:
        raise HTTPException(400, f"unknown intervention {intervention!r}")
    res = STATE["engine"].simulate(intervention, segment)
    sim = dataclasses.asdict(res)
    sim["intervention_label"] = C.INTERVENTIONS[intervention]["label"]
    sim["segment_label"] = "All segments" if segment == "all" else C.SEGMENTS[segment]["label"]
    return insights.intervention_narrative(sim)
