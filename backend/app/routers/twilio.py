"""Real WhatsApp/SMS path via Twilio.

/api/twilio/inbound  — webhook Twilio calls when a farmer texts the sandbox;
                       returns TwiML with the engine's reply.
/api/twilio/send-alert — push the current top alert to a phone (stage demo:
                       trigger a real dry-spell SMS to your own handset).

The in-app SMS simulator remains the credential-free fallback.
"""

from fastapi import APIRouter, Form, HTTPException, Response

from ..config import settings
from ..db import DbSession
from ..models import CropRequirement, Plot
from ..services import twilio_gw
from ..services.alerts import detect_dry_spell, water_balance
from ..services.sms import render_all
from ..services.sms_router import detect_lang, route_sms
from ..services.weather import forecast_days, latest_soil_moisture

router = APIRouter(prefix="/api/twilio", tags=["twilio"])


def _plot_for(db: DbSession, from_number: str | None) -> Plot | None:
    """Map an inbound number to a plot. Unregistered numbers fall back to the
    demo plot so any handset works on stage. (A production build keys on a
    farmer-phone registry.)"""
    return db.get(Plot, settings.default_plot_id) or db.query(Plot).first()


@router.post("/inbound")
def inbound(db: DbSession, From: str = Form(default=""), Body: str = Form(default="")):
    plot = _plot_for(db, From)
    if not plot:
        return Response(twilio_gw.twiml("Service unavailable"), media_type="application/xml")
    lang = detect_lang(Body, default="te")
    reply, _ = route_sms(db, plot, Body, lang)
    return Response(twilio_gw.twiml(reply), media_type="application/xml")


@router.post("/send-alert")
def send_alert(db: DbSession, plot_id: str, to: str):
    if not twilio_gw.available():
        raise HTTPException(503, "Twilio not configured — set TWILIO_ACCOUNT_SID / AUTH_TOKEN")
    plot = db.get(Plot, plot_id)
    if not plot:
        raise HTTPException(404, "unknown plot")
    crop = db.get(CropRequirement, plot.crop_current)
    days = forecast_days(plot.lat, plot.lon)
    labels = (
        {"en": crop.label_en, "te": crop.label_te, "hi": crop.label_hi}
        if crop
        else {"en": plot.crop_current, "te": plot.crop_current, "hi": plot.crop_current}
    )
    spell = detect_dry_spell(days)
    if spell:
        body = render_all(
            "dry_spell", labels, village=plot.village, length=spell.length_days, start=spell.start
        )["te"]
    else:
        wb = water_balance(
            days, crop.kc_mid if crop else 1.0, latest_soil_moisture(db, plot.id), None
        )
        body = render_all(
            "irrigation",
            labels,
            action_key=wb.level if wb.level != "none" else "light",
            village=plot.village,
            mm=round(wb.irrigation_mm),
            rain=round(wb.rain_eff_mm),
        )["te"]
    try:
        return twilio_gw.send_message(to, body)
    except Exception as exc:  # noqa: BLE001 - surface gateway errors to the caller
        raise HTTPException(502, f"send failed: {type(exc).__name__}") from exc
