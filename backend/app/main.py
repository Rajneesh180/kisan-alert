import time
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers import (
    advisory,
    alerts,
    fertilizer,
    forecast,
    health,
    plots,
    recommend,
    sensors,
    sms_sim,
    tts_router,
    twilio,
)
from .seed import seed
from .services.ndvi_forecast import load_on_boot
from .services.rag import load_knowledge

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

# Public demo URL protection: token-ish bucket per client IP. LLM-backed
# endpoints get a tighter budget than reads. Twilio webhooks are exempt (Twilio
# retries and comes from a shared pool of IPs).
RATE_WINDOW_S = 60
RATE_LIMITS = {"expensive": 12, "default": 120}
RATE_MAX_KEYS = 5000  # bound the bucket map so a flood of IPs can't grow memory
EXPENSIVE_PATHS = ("/api/advisory", "/api/health-log")
EXEMPT_PATHS = ("/api/twilio/inbound",)
_hits: dict[tuple[str, str], list[float]] = defaultdict(list)


def _client_ip(request: Request) -> str:
    # Behind HF Spaces / any proxy, request.client.host is the proxy; the real
    # client is the first hop in X-Forwarded-For.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


UPLOADS_DIR = settings.data_dir / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)  # must exist before the static mount below


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed()
    from .db import SessionLocal

    with SessionLocal() as db:
        load_on_boot(db)
    load_knowledge()
    yield


app = FastAPI(title="Kisan Alert", lifespan=lifespan)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    path = request.url.path
    if any(path.startswith(p) for p in EXEMPT_PATHS):
        return await call_next(request)
    bucket = "expensive" if any(path.startswith(p) for p in EXPENSIVE_PATHS) else "default"
    now = time.time()
    if len(_hits) > RATE_MAX_KEYS:  # drop stale buckets before they grow unbounded
        for k in [k for k, v in _hits.items() if not v or now - v[-1] > RATE_WINDOW_S]:
            _hits.pop(k, None)
    hits = _hits[(_client_ip(request), bucket)]
    hits[:] = [t for t in hits if now - t < RATE_WINDOW_S]
    if len(hits) >= RATE_LIMITS[bucket]:
        return JSONResponse({"detail": "rate limit exceeded, try again shortly"}, status_code=429)
    hits.append(now)
    return await call_next(request)


for r in (
    plots,
    alerts,
    forecast,
    recommend,
    fertilizer,
    advisory,
    health,
    sensors,
    sms_sim,
    twilio,
    tts_router,
):
    app.include_router(r.router)


@app.get("/api/health")
def api_health():
    return {"status": "ok"}


app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
