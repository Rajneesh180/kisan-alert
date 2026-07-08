from dataclasses import asdict
from datetime import date

from fastapi import APIRouter, HTTPException

from ..db import DbSession
from ..models import CropRequirement, Plot, SoilProfile
from ..services.alerts import detect_dry_spell, detect_ndvi_stress, water_balance
from ..services.sms import render_all
from ..services.weather import (
    LIVE_FALLBACK_NOTE,
    REPLAY_NOTE,
    REPLAY_START,
    forecast_days,
    latest_soil_moisture,
    ndvi_windows,
    replay_days,
)

router = APIRouter(prefix="/api", tags=["alerts"])


def _friendly_date(iso: str) -> str:
    """Render an ISO date as a farmer-readable '10 Jul' for SMS copy."""
    d = date.fromisoformat(iso)
    return f"{d.day} {d:%b}"


@router.get("/alerts")
def get_alerts(plot_id: str, db: DbSession, mode: str = "live"):
    plot = db.get(Plot, plot_id)
    if not plot:
        raise HTTPException(404, "unknown plot")
    if mode not in ("live", "replay"):
        raise HTTPException(422, "mode must be live or replay")

    crop = db.get(CropRequirement, plot.crop_current)
    soil = db.get(SoilProfile, plot.id)
    # Live weather is unreachable from some hosts (e.g. HF Spaces blocks the shared
    # egress IP at Open-Meteo). Rather than go blank, fall back to the recorded
    # replay and flag it — the same degraded-mode contract the LLM features use.
    live_unavailable = False
    if mode == "live":
        days = forecast_days(plot.lat, plot.lon)
        live_unavailable = not days
    if mode == "replay" or live_unavailable:
        days = replay_days(db, plot.id)
        sm = next((d["soil_moisture"] for d in days if d.get("soil_moisture") is not None), None)
    else:
        sm = latest_soil_moisture(db, plot.id)

    on_recorded = mode == "replay" or live_unavailable
    spell = detect_dry_spell(days)
    wb = water_balance(days, crop.kc_mid if crop else 1.0, sm, soil.texture if soil else None)
    as_of = REPLAY_START if on_recorded else date.today()
    stress = detect_ndvi_stress(ndvi_windows(db, plot.id), as_of)
    crop_labels = (
        {"en": crop.label_en, "te": crop.label_te, "hi": crop.label_hi}
        if crop
        else {"en": plot.crop_current, "te": plot.crop_current, "hi": plot.crop_current}
    )

    alerts = []
    if spell:
        alerts.append(
            {
                "type": "dry_spell",
                "severity": spell.severity,
                "start": spell.start,
                "length_days": spell.length_days,
                "total_rain_mm": spell.total_rain_mm,
                "ongoing": spell.ongoing,
                "sms": render_all(
                    "dry_spell",
                    crop_labels,
                    village=plot.village,
                    length=spell.length_days,
                    start=_friendly_date(spell.start),
                ),
            }
        )
    if wb.level != "none":
        alerts.append(
            {
                "type": "irrigation",
                "severity": wb.level,
                "irrigation_mm": wb.irrigation_mm,
                "sms": render_all(
                    "irrigation",
                    crop_labels,
                    action_key=wb.level,
                    village=plot.village,
                    mm=round(wb.irrigation_mm),
                    rain=round(wb.rain_eff_mm),
                ),
            }
        )
    if stress:
        alerts.append(
            {
                "type": "crop_stress",
                "severity": stress.severity,
                "ndvi": stress.ndvi,
                "baseline": stress.baseline,
                "anomaly": stress.anomaly,
                "date": stress.date,
                "sms": render_all(
                    "crop_stress", crop_labels, village=plot.village, ndvi=stress.ndvi
                ),
            }
        )

    note = LIVE_FALLBACK_NOTE if live_unavailable else REPLAY_NOTE if mode == "replay" else None
    return {
        "plot_id": plot.id,
        "mode": mode,
        "live_unavailable": live_unavailable,
        "replay_note": note,
        "days": days,
        "dry_spell": asdict(spell) if spell else None,
        "water_balance": asdict(wb),
        "ndvi_stress": asdict(stress) if stress else None,
        "alerts": alerts,
    }
