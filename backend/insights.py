"""LLM insight layer (Google Gemini via REST) with a hard template fallback.

Design priorities for a live demo:
  * Never break: any failure (no key, network, bad response) silently falls back
    to a templated, numerically-correct narrative.
  * Never lag the critical path: responses are cached on disk, so once generated
    (or after a one-time precompute) the narrative is instant and offline.
"""
from __future__ import annotations

import hashlib
import json
import os

import requests
from dotenv import load_dotenv

import config as C

load_dotenv(C.ROOT / "backend" / ".env")

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_CACHE_PATH = C.ARTIFACTS_DIR / "insight_cache.json"


def _load_cache() -> dict:
    if _CACHE_PATH.exists():
        try:
            return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    C.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")


_CACHE = _load_cache()


def has_key() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def _gemini(prompt: str) -> str | None:
    """Call Gemini; return text or None on any failure."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    try:
        resp = requests.post(
            GEMINI_URL.format(model=GEMINI_MODEL),
            params={"key": key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.4, "maxOutputTokens": 220},
            },
            timeout=12,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return text or None
    except Exception as exc:  # noqa: BLE001 - demo must never crash on LLM
        print(f"[insights] Gemini call failed, using fallback: {exc}")
        return None


def _cached(prompt: str, fallback: str) -> dict:
    """Return {text, source}; prefer cache, then Gemini, then template."""
    h = hashlib.sha1(prompt.encode()).hexdigest()[:16]
    if h in _CACHE:
        return {"text": _CACHE[h], "source": "ai"}
    text = _gemini(prompt)
    if text:
        _CACHE[h] = text
        _save_cache(_CACHE)
        return {"text": text, "source": "ai"}
    return {"text": fallback, "source": "template"}


# ---------------------------------------------------------------------------
# Friction narrative (powers the Friction Insight panel)
# ---------------------------------------------------------------------------
def friction_narrative(friction: dict) -> dict:
    drop = friction["funnel"]["biggest_drop"]
    worst = friction["segment_friction"]["worst_segment"]
    channels = friction["channel_patterns"]["channels"][:3]
    chan_str = ", ".join(f"{c['channel']} ({c['lift_vs_baseline']*100:+.0f}pp)" for c in channels)

    prompt = (
        "You are a senior marketing analyst writing for a CMO. In 2-3 crisp "
        "sentences, no bullet points, explain this funnel friction and what it "
        "implies. Be specific with the numbers; do not invent any.\n\n"
        f"Biggest drop-off: {drop['from_stage']} -> {drop['to_stage']}, only "
        f"{drop['step_conversion']*100:.0f}% advance, {drop['lost_customers']:,} customers lost.\n"
        f"Worst segment: {worst['segment_label']} at {worst['purchase_conversion']*100:.0f}% conversion.\n"
        f"Channels most correlated with conversion: {chan_str}.\n"
    )
    fallback = friction["headline"] + (
        f" Channels most associated with conversion: {chan_str}."
    )
    return _cached(prompt, fallback)


# ---------------------------------------------------------------------------
# Intervention rationale (powers the simulator narrative)
# ---------------------------------------------------------------------------
def intervention_narrative(sim: dict) -> dict:
    prompt = (
        "You are a marketing strategist. In 2 sentences, explain to a marketer "
        "why this intervention is predicted to lift conversion for this segment, "
        "and state the projected impact. Use the numbers; do not invent any.\n\n"
        f"Intervention: {sim['intervention_label']} (channel-based).\n"
        f"Target segment: {sim['segment_label']}.\n"
        f"Predicted relative lift: {sim['predicted_rel_lift']*100:.0f}%.\n"
        f"Incremental conversions: {sim['incremental_conversions']:.0f} on "
        f"{sim['reach']:,} reached.\n"
        f"Projected revenue: ${sim['projected_revenue']:,.0f}; ROI {sim['roi']:.0f}x.\n"
    )
    fallback = (
        f"{sim['intervention_label']} targeted at {sim['segment_label']} is "
        f"predicted to lift conversion {sim['predicted_rel_lift']*100:.0f}%, adding "
        f"{sim['incremental_conversions']:.0f} conversions worth "
        f"${sim['projected_revenue']:,.0f} at a {sim['roi']:.0f}x return — before any spend."
    )
    return _cached(prompt, fallback)
