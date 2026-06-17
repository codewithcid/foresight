"""Pre-warm the Gemini insight cache for every intervention x segment combo.

Hits the running API so the prompts are byte-identical to what the dashboard
sends (guaranteeing cache hits). Spaced out to respect free-tier rate limits.
Run with the backend up:  ../.venv/Scripts/python.exe prewarm.py
"""
import time

import requests

import config as C

BASE = "http://127.0.0.1:8000"
combos = [(k, s) for k in C.INTERVENTION_KEYS for s in (["all"] + C.SEGMENT_KEYS)]

ov = requests.get(f"{BASE}/api/overview", timeout=20).json()
print(f"friction narrative: {ov['narrative_source']}")

ai = 0
for k, s in combos:
    for attempt in range(3):
        r = requests.get(f"{BASE}/api/insight/intervention",
                         params={"intervention": k, "segment": s}, timeout=25).json()
        if r["source"] == "ai":
            ai += 1
            print(f"  {k}/{s}: ai")
            break
        print(f"  {k}/{s}: {r['source']} (attempt {attempt+1}, backing off)")
        time.sleep(6)
    time.sleep(3)

print(f"\ncached AI narratives: {ai}/{len(combos)}")
