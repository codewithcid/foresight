# ◎ Foresight — Customer Journey Intelligence & What-If Simulator

> **Stop A/B testing in production. Foresight predicts the lift of a marketing intervention before you spend a cent — and proves its predictions are accurate against held-out ground truth.**

Built for the **Epsilon TeXpedition** hackathon. Foresight ingests omnichannel
customer-journey data, finds where customers drop off, recommends the
highest-impact intervention, and runs a **counterfactual "what-if" simulation**
that predicts conversion/revenue lift *before any spend* — then validates those
predictions against a known ground-truth treatment effect.

---

## Why it's credible: predicted vs. actual

The synthetic data is generated from a **known, heterogeneous treatment effect**
(it varies by customer segment). We hide the counterfactual outcomes, train an
uplift model on the factual data only, then reveal the truth on a held-out set:

| Intervention | Predicted lift | Actual (held-out) | Error |
|---|---:|---:|---:|
| Cart-Recovery Push | +19.0% | +22.9% | 3.9pp |
| Personalized Email | +16.8% | +21.1% | 4.2pp |
| SMS Discount | +16.9% | +19.4% | 2.5pp |
| Paid-Social Retargeting | +11.2% | +17.7% | 6.5pp |

Confidence intervals fold in the model's **own held-out error**, so they reflect
how wrong the model typically is — not just sampling noise.

---

## Quick start (Windows / PowerShell)

```powershell
.\setup.ps1          # venv + deps + generate data + npm install  (one time)
.\run-backend.ps1    # terminal 1 -> http://127.0.0.1:8000
.\run-frontend.ps1   # terminal 2 -> http://localhost:5173
```

**macOS / Linux:** `make setup`, then `make backend` and `make frontend`.

That's it — open **http://localhost:5173**. No API keys required.

### Optional: live LLM narratives (Google Gemini)
The Friction Insight and simulator rationale use Gemini if a key is present, and
fall back to numerically-correct templates otherwise (the demo never breaks).

```powershell
copy backend\.env.example backend\.env
# paste your free key from https://aistudio.google.com/apikey into backend\.env
# then restart .\run-backend.ps1  (panel switches from "Heuristic" to "Gemini")
```

---

## 60-second demo script

1. **The problem (10s).** "Here are 20,000 omnichannel customer journeys. The
   funnel shows the leak: only **38% advance from Intent → Purchase** — that's
   ~6,000 customers lost." *(point to the red "biggest leak" badge)*
2. **The insight (10s).** "Foresight explains it in plain English: the
   **Bargain-Hunter** segment converts worst at 27%, and app-push / email are
   the channels most correlated with conversion." *(Friction Insight panel)*
3. **The recommendation (10s).** "It ranks interventions by lift × reach ÷ cost.
   Top pick: **Cart-Recovery Push** — let me open it in the simulator." *(click
   the top row)*
4. **The counterfactual (15s).** "Before spending a cent, Foresight predicts
   **+19% lift, +212 conversions, $18k revenue at 843× ROI**, with a confidence
   interval. Try SMS Discount on Bargain Hunters — **+60% lift**, because
   discounts over-index on price-sensitive customers." *(change the dropdowns)*
5. **The proof (15s — the money moment).** "Can we trust it? The data has a known
   ground-truth effect. On a held-out set: **Predicted +19.0% vs Actual +22.9%**
   — every intervention × segment cell lands on the diagonal. Foresight doesn't
   just predict; it proves it's right." *(Validation panel)*

---

## Architecture

```
Synthetic journeys ──► Friction detection ──► Uplift engine ──► Dashboard
 (known ground         (funnel, segments,     (S-learner       (React + Recharts)
  truth effect)         channels, Sankey)      simulate /
                                               validate / rank)
                                                    │
                                              Gemini insights
                                              (cached, fallback)
```

| Layer | Tech | File |
|---|---|---|
| Data generator | numpy / pandas | [data/generate.py](data/generate.py) |
| Friction detection | pandas | [backend/analysis.py](backend/analysis.py) |
| Uplift / what-if | LightGBM S-learner | [backend/uplift.py](backend/uplift.py) |
| LLM insights | Gemini REST + fallback | [backend/insights.py](backend/insights.py) |
| API | FastAPI | [backend/main.py](backend/main.py) |
| Dashboard | React + Vite + TS + Tailwind + Recharts | [frontend/src](frontend/src) |

### How the model works
- **S-learner**: one LightGBM conversion model trained on the addressable
  (reached-Intent) pool with the intervention encoded as a feature. Predicting a
  customer under *treatment* vs *control* yields the counterfactual uplift τ̂(X).
  Chosen over a T-learner because it's more sample-efficient on a ~10k pool while
  LightGBM still captures segment × intervention heterogeneity.
- **simulate(intervention, segment)** → predicted lift, incremental conversions,
  revenue (configurable AOV), ROI, and a bootstrap + model-error confidence interval.
- **validate()** → compares model-predicted lift to the generator's ground-truth
  lift on a held-out set (intuitive predicted-% vs actual-% headline).
- Everything is **seeded**; the headline panels are computed once at startup and
  served from memory, so the live demo is deterministic and fast.

## API
| Endpoint | Purpose |
|---|---|
| `GET /api/overview` | funnel, segment friction, channel patterns, Sankey, narrative |
| `GET /api/recommendations` | ranked interventions |
| `POST /api/simulate` | `{intervention, segment}` → predicted lift / revenue / ROI / CI |
| `GET /api/validation` | predicted vs actual lift (per-intervention + per-cell) |
| `GET /api/insight/intervention` | LLM rationale for an intervention × segment |

## Notes & honest limitations
- Data is synthetic with an injected ground-truth effect; this is what makes
  validation *possible*. On real data you'd validate via a holdout/geo-test.
- Dataset is 20,000 customers (up from ~10k) purely to tighten per-cell
  validation variance.
- ROI figures are high for near-free channels (app push at $0.01/contact); that's
  realistic for the channel, not a bug.
