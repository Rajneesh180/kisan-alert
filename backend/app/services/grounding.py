"""Build the grounding context Gemini receives, and the deterministic advisory
fallback served whenever Gemini is unavailable (no key, quota, network).

The fallback is assembled purely from engine outputs so the answer is still
plot-specific and numeric — degraded, not useless.
"""

from datetime import date

from sqlalchemy.orm import Session

from ..models import CropRequirement, GroundwaterLevel, IndicatorWindow, Plot, SoilProfile
from .alerts import detect_dry_spell, water_balance
from .fertilizer import plan_fertilizer
from .rag import retrieve
from .recommend import current_season, recommend_for_plot
from .weather import forecast_days, latest_soil_moisture

WATER_LINES = {
    "none": {
        "en": "no irrigation needed this week",
        "hi": "इस सप्ताह सिंचाई आवश्यक नहीं",
        "te": "ఈ వారం తడి అవసరం లేదు",
    },
    "light": {
        "en": "give one light irrigation (~{mm} mm)",
        "hi": "एक हल्की सिंचाई करें (~{mm} mm)",
        "te": "ఒక తేలికపాటి తడి ఇవ్వండి (~{mm} mm)",
    },
    "urgent": {
        "en": "irrigate soon, about {mm} mm needed",
        "hi": "जल्द सिंचाई करें, लगभग {mm} mm आवश्यक",
        "te": "త్వరగా తడి ఇవ్వండి, సుమారు {mm} mm అవసరం",
    },
}

FALLBACK = {
    "en": (
        "{village} ({crop}): {water_line}. Best crops this {season}: {crops}. "
        "For plant problems send a photo — an RSK expert will review it."
    ),
    "hi": (
        "{village} ({crop}): {water_line}. इस {season} की उपयुक्त फसलें: {crops}. "
        "पौधों की समस्या के लिए फोटो भेजें — RSK विशेषज्ञ देखेंगे."
    ),
    "te": (
        "{village} ({crop}): {water_line}. ఈ {season} అనువైన పంటలు: {crops}. "
        "మొక్కల సమస్యలకు ఫోటో పంపండి — RSK నిపుణులు చూస్తారు."
    ),
}


def build_context(db: Session, plot: Plot, question: str | None = None) -> dict:
    soil = db.get(SoilProfile, plot.id)
    gw = db.get(GroundwaterLevel, plot.mandal)
    crop = db.get(CropRequirement, plot.crop_current)
    season = current_season(date.today().month)
    days = forecast_days(plot.lat, plot.lon)
    wb = water_balance(
        days,
        crop.kc_mid if crop else 1.0,
        latest_soil_moisture(db, plot.id),
        soil.texture if soil else None,
    )
    spell = detect_dry_spell(days)
    rec = recommend_for_plot(db, plot, season)
    fert = (
        plan_fertilizer(
            crop=crop.crop,
            n_kg_ha=crop.n_kg_ha,
            p_kg_ha=crop.p_kg_ha,
            k_kg_ha=crop.k_kg_ha,
            soc_g_kg=soil.soc_g_kg if soil else None,
            ph=soil.ph if soil else None,
        )
        if crop
        else None
    )
    latest = (
        db.query(IndicatorWindow)
        .filter(IndicatorWindow.plot_id == plot.id, IndicatorWindow.ndvi.isnot(None))
        .order_by(IndicatorWindow.date_start.desc())
        .first()
    )
    rag_passages = retrieve(question, plot.crop_current) if question else []

    return {
        "village": plot.village,
        "mandal": plot.mandal,
        "current_crop": plot.crop_current,
        "season": season,
        "soil": {
            "ph": soil.ph if soil else None,
            "texture": soil.texture if soil else None,
        },
        "groundwater_category": gw.category if gw else None,
        "water_balance_next_7d": {
            "crop_water_need_mm": wb.etc_mm,
            "expected_rain_mm": wb.rain_eff_mm,
            "irrigation_needed_mm": wb.irrigation_mm,
            "level": wb.level,
        },
        "dry_spell": (
            {"start": spell.start, "length_days": spell.length_days, "severity": spell.severity}
            if spell
            else None
        ),
        "latest_satellite": (
            {"date": latest.date_start.isoformat(), "ndvi": latest.ndvi, "ndmi": latest.ndmi}
            if latest
            else None
        ),
        "top_crop_recommendations": [
            {"crop": r["labels"]["en"], "score": r["score"], "reasons": r["reasons"]}
            for r in rec["recommendations"][:3]
        ],
        "fertilizer_plan": (
            {
                "npk_kg_ha": {d.nutrient: d.kg_ha for d in fert.doses},
                "urea_kg_ha": fert.urea_kg_ha,
                "dap_kg_ha": fert.dap_kg_ha,
                "mop_kg_ha": fert.mop_kg_ha,
                "organic_carbon_status": fert.oc_status,
                "amendments": fert.amendments,
            }
            if fert
            else None
        ),
        "reference_practices": rag_passages if rag_passages else None,
    }


def fallback_advisory(db: Session, plot: Plot, lang: str) -> str:
    ctx = build_context(db, plot)
    wb = ctx["water_balance_next_7d"]
    water_line = WATER_LINES[wb["level"]][lang].format(mm=round(wb["irrigation_needed_mm"]))
    season = ctx["season"]
    rec = recommend_for_plot(db, plot, season)
    crops = ", ".join(r["labels"][lang] for r in rec["recommendations"][:3])
    crop = db.get(CropRequirement, plot.crop_current)
    crop_label = getattr(crop, f"label_{lang}", plot.crop_current) if crop else plot.crop_current
    return FALLBACK[lang].format(
        village=plot.village, crop=crop_label, water_line=water_line, season=season, crops=crops
    )
