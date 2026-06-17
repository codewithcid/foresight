"""Shared configuration: segments, channels, stages, interventions, economics, paths.

Imported by both the data generator and the backend so the ground-truth labels
and the model/serving layer never drift apart.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]          # foresight/
DATA_DIR = ROOT / "data"
ARTIFACTS_DIR = ROOT / "backend" / "artifacts"
CUSTOMERS_PARQUET = DATA_DIR / "customers.parquet"
TOUCHPOINTS_PARQUET = DATA_DIR / "touchpoints.parquet"
RESULTS_JSON = ARTIFACTS_DIR / "results.json"

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
SEED = 42
N_CUSTOMERS = 20_000  # bumped from ~10k: ~halves per-cell validation variance

# ---------------------------------------------------------------------------
# Domain vocabulary
# ---------------------------------------------------------------------------
STAGES = ["Awareness", "Consideration", "Intent", "Purchase", "Retention"]
CHANNELS = ["email", "paid_social", "web", "app_push", "sms", "organic"]

SEGMENTS = {
    "bargain_hunter": {"label": "Bargain Hunter", "prop": 0.30},
    "loyalist":       {"label": "Loyalist",       "prop": 0.22},
    "browser":        {"label": "Browser",        "prop": 0.30},
    "high_intent":    {"label": "High-Intent",    "prop": 0.18},
}
SEGMENT_KEYS = list(SEGMENTS.keys())

# ---------------------------------------------------------------------------
# Interventions: channel + unit economics (per-contact cost in USD)
# ---------------------------------------------------------------------------
INTERVENTIONS = {
    "cart_recovery_push": {"label": "Cart-Recovery Push",      "channel": "app_push",    "cost_per_contact": 0.01},
    "personalized_email": {"label": "Personalized Email",      "channel": "email",       "cost_per_contact": 0.02},
    "sms_discount":       {"label": "SMS Discount",            "channel": "sms",         "cost_per_contact": 0.08},
    "retargeting_social": {"label": "Paid-Social Retargeting", "channel": "paid_social", "cost_per_contact": 0.25},
}
INTERVENTION_KEYS = list(INTERVENTIONS.keys())

# Average order value used to translate incremental conversions into revenue.
AOV = 85.0

# Treatment-assignment shares across the addressable (reached-Intent) pool.
# Control gets ~1/3, each intervention ~1/6 — the variance-optimal split for a
# shared-control T-learner with 4 interventions.
CONTROL_SHARE = 0.34
TREATMENT_SHARE = (1.0 - CONTROL_SHARE) / len(INTERVENTIONS)

# Fraction of customers held out of model training for honest validation.
TEST_SIZE = 0.30
