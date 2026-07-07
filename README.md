# Kisan Alert — satellite-grounded crop advisory for small farmers

Built for Google Cloud **"Build with AI: Code for Communities" 2026** — Track 4,
*Kisan Alert* (sponsoring MP: Lavu Sri Krishna Devarayalu, Narasaraopet).

Timely irrigation, crop, fertilizer and plant-health advice for small and
marginal farmers — in Telugu, Hindi and English, over the web, voice and SMS.
Every number a farmer sees comes from a deterministic agronomy engine grounded
in real satellite and climate data; Gemini only handles language, speech and
vision, so the advice can't hallucinate figures.

## How the AI works (and where it does real work)

- **Crop-stress early warning (gradient-boosted model).** Predicts the next
  10-day NDVI for a plot from its current vegetation + water-balance state
  (canopy moisture / NDMI, rainfall deficit, ET0, soil moisture and trends).
  It is benchmarked honestly: **~6% lower RMSE than a persistence baseline under
  leave-one-plot-out cross-validation**, with the top drivers (canopy moisture,
  greenness trend) reported for interpretability. Deep sequence models were
  tried and rejected — 12 plots × ~53 ten-day windows is far too little data for
  them, and a naive persistence baseline beats an LSTM at this horizon.
  Gradient-boosted trees on engineered agronomic features are the right-sized,
  honest choice. Trains at boot in ~1–2s, so the served model never drifts from
  the committed data.
- **Grounded advisory (Gemini).** The deterministic engines compute the numbers
  (water balance, dry-spell, stress); Gemini phrases them in the farmer's
  language and is instructed never to invent measurements. Works by voice or
  text; transcribes Indic speech directly.
- **RAG over ICAR/TNAU practices (Gemini embeddings).** The farmer's question is
  embedded and matched against a curated package-of-practices corpus, so answers
  prefer authoritative agronomic text over parametric memory.
- **Photo diagnosis (Gemini multimodal).** Crop-photo pest/disease triage with a
  confidence score; low-confidence cases escalate to a Rythu Seva Kendra expert.
- **Native text-to-speech (Gemini TTS).** Telugu/Hindi voice output on the free
  API key — no paid Cloud TTS, no billing.
- **Deterministic engines (no LLM):** FAO-56 water balance, dry-spell detection,
  NDVI seasonal-anomaly stress, crop-suitability scoring, and a soil-test-based
  NPK / urea-DAP-MOP fertilizer plan.

**Degraded-mode by design:** with no API key or on any Gemini failure, every
feature falls back to its deterministic result — the platform stays useful with
zero LLM availability.

## Data (all real; free or keyless wherever possible)

| Source | Signal | Access |
|---|---|---|
| Sentinel-2 (Google Earth Engine) | NDVI / NDMI, 10-day composites | GEE noncommercial (offline pipeline) |
| Open-Meteo archive (ERA5 / ERA5-Land) | rainfall, ET0, soil moisture | keyless |
| ISRIC SoilGrids v2 | pH, texture, organic carbon | keyless |
| CGWB | groundwater category (mandal-level, representative) | committed table |

18 months of history per plot is fetched once by the pipeline, committed as
JSON artifacts, and served from SQLite — so the running app needs no live GEE
access. The demo ships 12 plots across two constituencies (Anantapur and the
sponsoring MP's Narasaraopet); **farmer profiles are illustrative, the
satellite/soil/climate data under them is real.**

## Architecture & how it scales

FastAPI + SQLite backend, React + Vite frontend, one Cloud Run container
(`Dockerfile` builds the frontend and serves it with the API). The current build
seeds SQLite from the committed artifacts on boot — a self-contained demo
harness. The production path is deliberately short:

- **Data store:** SQLite → Cloud SQL (Postgres) or BigQuery for many thousands
  of plots and multi-tenant constituencies.
- **Ingestion:** the manual pipeline → Cloud Scheduler-triggered GEE exports and
  Open-Meteo pulls, writing new 10-day windows on a cron.
- **Rate limiting:** the in-process limiter (fine for one instance) → Memorystore
  (Redis) so limits hold across autoscaled instances.
- **Delivery:** the in-app SMS simulator → the wired Twilio WhatsApp/SMS webhook
  for real two-way messaging on any phone.

## Dev setup

```sh
uv sync --group dev --group pipeline
cd frontend && npm install
```

Backend: `uv run uvicorn app.main:app --app-dir backend --reload`
Frontend: `cd frontend && npm run dev`
Tests/lint: `uv run pytest && uv run ruff check .`

Copy `.env.example` to `.env` and add a free Gemini key (from
https://aistudio.google.com — no card) to enable the advisory, TTS and RAG.
Everything else works without it.

## Data pipeline (offline, one-time per refresh)

Earth Engine needs noncommercial registration, `ee.Authenticate()`, and
`GEE_PROJECT` in `.env`. Open-Meteo and SoilGrids need no credentials.

```sh
uv run python pipeline/fetch_soil.py       # ISRIC SoilGrids soil profiles
uv run python pipeline/fetch_satellite.py  # Sentinel-2 NDVI/NDMI via Earth Engine
uv run python pipeline/fetch_climate.py    # rainfall + ET0 + soil moisture via Open-Meteo
```

Artifacts land in `data/artifacts/` and are committed.

## Google Cloud used

Gemini API (advisory, photo diagnosis, native TTS, RAG embeddings) and Google
Earth Engine (Sentinel-2) — both on free / noncommercial tiers, no billing.
