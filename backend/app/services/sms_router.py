"""Shared inbound-SMS keyword router: one code path for the in-app simulator
and the real Twilio/WhatsApp webhook. Deterministic engines only — the reply a
DLT-registered gateway would send."""

import re
from datetime import date

from sqlalchemy.orm import Session

from ..models import CropRequirement, Plot, SoilProfile
from .alerts import water_balance
from .recommend import current_season, recommend_for_plot
from .sms import ACTIONS, render, segments
from .weather import forecast_days, latest_soil_moisture

WATER_WORDS = ("PANI", "WATER", "నీరు", "पानी", "TADI", "తడి")
CROP_WORDS = ("FASAL", "CROP", "పంట", "फसल", "PANTA")

NO_IRRIGATION = {
    "en": "No irrigation needed.",
    "hi": "सिंचाई आवश्यक नहीं.",
    "te": "తడి అవసరం లేదు.",
}


def detect_lang(text: str, default: str = "en") -> str:
    """Infer reply language from the script the farmer texted in."""
    if re.search(r"[ఀ-౿]", text):  # Telugu block
        return "te"
    if re.search(r"[ऀ-ॿ]", text):  # Devanagari
        return "hi"
    return default


def route_sms(db: Session, plot: Plot, text: str, lang: str) -> tuple[str, int]:
    """Return (reply, sms_segments) for an inbound keyword."""
    lang = lang if lang in ("en", "hi", "te") else "en"
    upper = text.strip().upper()
    matches = lambda words: any(w in upper or w in text for w in words)  # noqa: E731

    if matches(WATER_WORDS):
        crop = db.get(CropRequirement, plot.crop_current)
        soil = db.get(SoilProfile, plot.id)
        wb = water_balance(
            forecast_days(plot.lat, plot.lon),
            crop.kc_mid if crop else 1.0,
            latest_soil_moisture(db, plot.id),
            soil.texture if soil else None,
        )
        crop_label = getattr(crop, f"label_{lang}", plot.crop_current)
        action = (
            NO_IRRIGATION[lang] if wb.level == "none" else ACTIONS.get(wb.level, {}).get(lang, "")
        )
        reply = render(
            "irrigation",
            lang,
            village=plot.village,
            crop=crop_label,
            mm=round(wb.irrigation_mm),
            rain=round(wb.rain_eff_mm),
            action=action,
        )
    elif matches(CROP_WORDS):
        season = current_season(date.today().month)
        rec = recommend_for_plot(db, plot, season)
        top = rec["recommendations"][:2]
        reply = render(
            "crops",
            lang,
            village=plot.village,
            season=season,
            c1=top[0]["labels"][lang],
            c2=top[1]["labels"][lang],
            avail=round(top[0]["water_available_mm"]),
        )
    else:
        reply = render("help", lang)

    return reply, segments(reply)
