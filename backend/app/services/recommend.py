"""Crop suitability scorer.

Transparent weighted factors — no ML, no LLM. Every recommendation carries a
per-factor breakdown and, where a crop scores poorly, a plain reason ("needs
~1250 mm, only ~470 mm likely available"). Gemini's only job later is
translation and narration. Requirement norms: data/crop_requirements.csv
(ICAR/TNAU/FAO-56); irrigation-capacity heuristic pending real CGWB stage data.
"""

from sqlalchemy.orm import Session

from ..models import CropRequirement, GroundwaterLevel, IndicatorWindow, Plot, SoilProfile

SEASON_MONTHS = {"kharif": {6, 7, 8, 9, 10}, "rabi": {11, 12, 1, 2, 3}}
EFFECTIVE_RAIN_FACTOR = 0.8

# Assured-irrigation capacity (mm/season) by CGWB groundwater category — demo
# heuristic; production would use stage-of-development percentages per mandal.
IRRIGATION_CAPACITY_MM = {
    "safe": 300.0,
    "semi-critical": 150.0,
    "critical": 75.0,
    "over-exploited": 0.0,
}
TANK_FED_BONUS_MM = 200.0

GW_SUSTAINABILITY = {
    "low": {"safe": 1.0, "semi-critical": 1.0, "critical": 0.9, "over-exploited": 0.8},
    "medium": {"safe": 1.0, "semi-critical": 0.7, "critical": 0.4, "over-exploited": 0.2},
    "high": {"safe": 0.8, "semi-critical": 0.4, "critical": 0.2, "over-exploited": 0.0},
}

TEXTURE_NEIGHBORS = {
    "sandy loam": {"loam"},
    "loam": {"sandy loam", "clay loam"},
    "clay loam": {"loam", "clay", "black"},
    "clay": {"clay loam", "black"},
}

WEIGHTS = {"water": 0.35, "groundwater": 0.25, "ph": 0.20, "texture": 0.20}


def current_season(month: int) -> str:
    return "kharif" if month in SEASON_MONTHS["kharif"] else "rabi"


def season_rain_mm(rows: list[IndicatorWindow], season: str) -> float:
    """Season rainfall from the plot's own recorded history (latest ~12 months)."""
    months = SEASON_MONTHS[season]
    return round(sum(r.rain_mm or 0.0 for r in rows[-37:] if r.date_start.month in months), 1)


def score_crop(
    crop: CropRequirement,
    *,
    season: str,
    rain_mm: float,
    capacity_mm: float,
    ph: float | None,
    texture: str | None,
    gw_category: str,
) -> dict | None:
    """Score one crop for one plot-season; None if out of season."""
    in_season = crop.season in (season, "both") or (
        crop.season == "late_kharif" and season == "kharif"
    )
    if not in_season:
        return None

    reasons: list[str] = []

    if ph is None:
        ph_score = 0.7  # unknown pH — mild uncertainty penalty
    elif crop.soil_ph_min <= ph <= crop.soil_ph_max:
        ph_score = 1.0
    else:
        dist = (crop.soil_ph_min - ph) if ph < crop.soil_ph_min else (ph - crop.soil_ph_max)
        ph_score = max(0.0, round(1.0 - dist, 2))
        if dist >= 0.5:
            reasons.append(f"soil pH {ph} vs preferred {crop.soil_ph_min}-{crop.soil_ph_max}")

    prefs = [t.strip() for t in crop.soil_texture.split("/")]
    if texture is None:
        texture_score = 0.7
    elif texture in prefs:
        texture_score = 1.0
    elif any(
        texture in TEXTURE_NEIGHBORS.get(p, set()) or p in TEXTURE_NEIGHBORS.get(texture, set())
        for p in prefs
    ):
        texture_score = 0.6
    else:
        texture_score = 0.3
        reasons.append(f"{texture} soil vs preferred {crop.soil_texture}")

    available = EFFECTIVE_RAIN_FACTOR * rain_mm + capacity_mm
    ratio = available / crop.water_need_mm if crop.water_need_mm else 1.0
    water_score = min(1.0, round(ratio, 2))
    if ratio < 0.6:
        water_score = round(water_score * 0.5, 2)
        reasons.append(
            f"needs ~{crop.water_need_mm:.0f} mm, only ~{available:.0f} mm likely available"
        )

    gw_score = GW_SUSTAINABILITY[crop.groundwater_need].get(gw_category, 0.5)
    if gw_score <= 0.2:
        reasons.append(f"{crop.groundwater_need} groundwater demand in {gw_category} mandal")

    total = (
        WEIGHTS["water"] * water_score
        + WEIGHTS["groundwater"] * gw_score
        + WEIGHTS["ph"] * ph_score
        + WEIGHTS["texture"] * texture_score
    )
    return {
        "crop": crop.crop,
        "labels": {"en": crop.label_en, "te": crop.label_te, "hi": crop.label_hi},
        "score": round(total, 3),
        "breakdown": {
            "water": water_score,
            "groundwater": gw_score,
            "ph": ph_score,
            "texture": texture_score,
        },
        "water_need_mm": crop.water_need_mm,
        "water_available_mm": round(available),
        "duration_days": crop.duration_days,
        "rainfed_ok": crop.rainfed_ok,
        "reasons": reasons,
        "source": crop.source,
    }


def recommend_for_plot(db: Session, plot: Plot, season: str) -> dict:
    soil = db.get(SoilProfile, plot.id)
    gw = db.get(GroundwaterLevel, plot.mandal)
    rows = (
        db.query(IndicatorWindow)
        .filter_by(plot_id=plot.id)
        .order_by(IndicatorWindow.date_start)
        .all()
    )
    rain = season_rain_mm(rows, season)
    capacity = IRRIGATION_CAPACITY_MM.get(gw.category if gw else "", 75.0)
    if plot.irrigation == "tank-fed":
        capacity += TANK_FED_BONUS_MM

    scored = []
    for crop in db.query(CropRequirement).all():
        s = score_crop(
            crop,
            season=season,
            rain_mm=rain,
            capacity_mm=capacity,
            ph=soil.ph if soil else None,
            texture=soil.texture if soil else None,
            gw_category=gw.category if gw else "critical",
        )
        if s:
            s["is_current"] = crop.crop == plot.crop_current
            scored.append(s)
    scored.sort(key=lambda s: s["score"], reverse=True)
    return {
        "plot_id": plot.id,
        "season": season,
        "season_rain_mm": rain,
        "irrigation_capacity_mm": capacity,
        "groundwater_category": gw.category if gw else None,
        "recommendations": scored,
    }
