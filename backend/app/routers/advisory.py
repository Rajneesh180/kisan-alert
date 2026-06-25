import hashlib
import time

from fastapi import APIRouter, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ..db import DbSession
from ..models import Plot
from ..services import gemini
from ..services.grounding import build_context, fallback_advisory

router = APIRouter(prefix="/api", tags=["advisory"])

CACHE_TTL_S = 6 * 3600
CACHE_MAX = 500  # keyed by unique question — bound it so a public URL can't grow memory
_cache: dict[tuple[str, str, str], tuple[float, dict]] = {}


class AdvisoryIn(BaseModel):
    plot_id: str
    question: str
    lang: str = "en"


def _answer(db, plot: Plot, lang: str, question: str | None, audio=None) -> dict:
    ctx = build_context(db, plot, question=question)
    result = gemini.ask_advisory(question, ctx, lang, audio=audio)
    if result.get("degraded"):
        return {
            "answer": fallback_advisory(db, plot, lang),
            "transcript": None,
            "degraded": True,
            "grounding": ctx,
        }
    return {
        "answer": result["answer"],
        "transcript": result.get("transcript"),
        "degraded": False,
        "grounding": ctx,
    }


@router.post("/advisory")
def advisory(payload: AdvisoryIn, db: DbSession):
    plot = db.get(Plot, payload.plot_id)
    if not plot:
        raise HTTPException(404, "unknown plot")
    if payload.lang not in ("en", "hi", "te"):
        raise HTTPException(422, "lang must be en, hi or te")
    key = (
        payload.plot_id,
        payload.lang,
        hashlib.sha1(payload.question.strip().lower().encode()).hexdigest(),
    )
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL_S:
        return hit[1]
    res = _answer(db, plot, payload.lang, payload.question)
    if not res["degraded"]:  # don't cache fallbacks; retry Gemini next time
        if len(_cache) >= CACHE_MAX:
            for k, _ in sorted(_cache.items(), key=lambda kv: kv[1][0])[: CACHE_MAX // 5]:
                _cache.pop(k, None)  # evict oldest fifth
        _cache[key] = (time.time(), res)
    return res


@router.post("/advisory/voice")
async def advisory_voice(
    db: DbSession,
    plot_id: str = Form(...),
    lang: str = Form("en"),
    audio: UploadFile = None,
):
    plot = db.get(Plot, plot_id)
    if not plot:
        raise HTTPException(404, "unknown plot")
    if audio is None:
        raise HTTPException(422, "audio file required")
    data = await audio.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "audio too large (10 MB max)")
    return _answer(db, plot, lang, None, audio=(data, audio.content_type or "audio/webm"))
