"""Two-way SMS simulator: inbound keyword -> the shared engine router -> the
exact 160/70-char reply a DLT-registered gateway would send. This IS the
feature-phone product, demonstrated without the gateway."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import DbSession
from ..models import Plot
from ..services.sms_router import route_sms

router = APIRouter(prefix="/api", tags=["sms"])


class SmsIn(BaseModel):
    plot_id: str
    text: str
    lang: str = "en"


@router.post("/sms/inbound")
def sms_inbound(payload: SmsIn, db: DbSession):
    plot = db.get(Plot, payload.plot_id)
    if not plot:
        raise HTTPException(404, "unknown plot")
    reply, seg = route_sms(db, plot, payload.text, payload.lang)
    return {"reply": reply, "lang": payload.lang, "segments": seg}
