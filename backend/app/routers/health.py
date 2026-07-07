import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ..config import settings
from ..db import DbSession
from ..models import HealthLog, Plot
from ..services import gemini

router = APIRouter(prefix="/api", tags=["health"])

ESCALATE_CONFIDENCE = 0.6
MAX_PHOTO_BYTES = 8 * 1024 * 1024


def _log_json(log: HealthLog, plot: Plot | None = None) -> dict:
    out = {
        "id": log.id,
        "plot_id": log.plot_id,
        "created_at": log.created_at.isoformat(),
        "source": log.source,
        "language": log.language,
        "transcript": log.transcript,
        "photo_url": f"/uploads/{log.media_path}" if log.media_path else None,
        "diagnosis": log.diagnosis,
        "confidence": log.confidence,
        "severity": log.severity,
        "treatment": log.treatment,
        "escalated": log.escalated,
        "expert_reply": log.expert_reply,
        "replied_at": log.replied_at.isoformat() if log.replied_at else None,
    }
    if plot:
        out["plot"] = {"farmer": plot.farmer, "village": plot.village, "crop": plot.crop_current}
    return out


@router.post("/health-log")
async def create_health_log(
    db: DbSession,
    plot_id: str = Form(...),
    lang: str = Form("en"),
    note: str = Form(None),
    photo: UploadFile = None,
):
    plot = db.get(Plot, plot_id)
    if not plot:
        raise HTTPException(404, "unknown plot")
    if not note and photo is None:
        raise HTTPException(422, "provide a note or a photo")

    media_path = None
    photo_arg = None
    if photo is not None:
        data = await photo.read()
        if len(data) > MAX_PHOTO_BYTES:
            raise HTTPException(413, "photo too large (8 MB max)")
        uploads = settings.uploads_dir
        uploads.mkdir(parents=True, exist_ok=True)
        suffix = (photo.filename or "photo.jpg").rsplit(".", 1)[-1][:4] or "jpg"
        media_path = f"{uuid.uuid4().hex}.{suffix}"
        (uploads / media_path).write_bytes(data)
        photo_arg = (data, photo.content_type or "image/jpeg")

    result = gemini.diagnose(photo_arg, note, lang)
    degraded = result.get("degraded", False)
    # Escalate to the RSK expert whenever the AI is unavailable, unsure, or
    # sees something severe - the human loop is the product's safety net.
    escalated = degraded or (result.get("confidence") or 0) < ESCALATE_CONFIDENCE
    escalated = escalated or result.get("severity") == "severe"

    log = HealthLog(
        plot_id=plot_id,
        created_at=datetime.now(UTC),
        source="photo" if photo is not None else "text",
        language=lang,
        transcript=note,
        media_path=media_path,
        diagnosis=result.get("diagnosis"),
        confidence=result.get("confidence"),
        severity=result.get("severity"),
        treatment=result.get("treatment"),
        escalated=escalated,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return {**_log_json(log), "degraded": degraded}


@router.get("/health-log")
def list_health_logs(plot_id: str, db: DbSession):
    if not db.get(Plot, plot_id):
        raise HTTPException(404, "unknown plot")
    rows = (
        db.query(HealthLog).filter_by(plot_id=plot_id).order_by(HealthLog.created_at.desc()).all()
    )
    return [_log_json(r) for r in rows]


@router.get("/rsk/cases")
def rsk_cases(db: DbSession):
    rows = db.query(HealthLog).filter_by(escalated=True).order_by(HealthLog.created_at.desc()).all()
    return [_log_json(r, db.get(Plot, r.plot_id)) for r in rows]


class ReplyIn(BaseModel):
    reply: str


@router.post("/rsk/cases/{log_id}/reply")
def rsk_reply(log_id: int, payload: ReplyIn, db: DbSession):
    log = db.get(HealthLog, log_id)
    if not log:
        raise HTTPException(404, "unknown case")
    log.expert_reply = payload.reply.strip()
    log.replied_at = datetime.now(UTC)
    db.commit()
    db.refresh(log)
    return _log_json(log)
