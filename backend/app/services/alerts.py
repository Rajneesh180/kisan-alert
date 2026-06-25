"""Deterministic agronomy engines: dry-spell detection, FAO-56 water balance,
and NDVI crop-stress detection.

Pure functions over data series so they are unit-testable without network or
database. Sources: FAO Irrigation & Drainage Paper 56 (Allen et al., kc
approach, p=0.5 depletion); IMD rainy-day threshold (2.5 mm/day); Saxton &
Rawls (2006) for field capacity / wilting point by texture.
"""

from dataclasses import dataclass
from datetime import date, timedelta

RAINY_DAY_MM = 2.5  # IMD: a day with >= 2.5 mm counts as a rainy day
DRY_SPELL_MIN_DAYS = 7
EFFECTIVE_RAIN_FACTOR = 0.8  # FAO simplification for light-rain losses
ROOT_ZONE_MM = 300  # effective root-zone depth used for the soil buffer
DEPLETION_FRACTION = 0.5  # FAO-56 default allowable depletion p

NDVI_STALE_DAYS = 35  # no alert from a reading older than this (cloud gaps)
NDVI_ANOMALY_MODERATE = -0.10  # vs same-period-last-year baseline
NDVI_ANOMALY_SEVERE = -0.20
NDVI_TREND_THRESHOLD = -0.15  # vs mean of previous 3 valid windows

SOIL_WATER = {  # texture -> (field capacity, wilting point), volumetric m3/m3
    "sandy loam": (0.18, 0.08),
    "loam": (0.28, 0.14),
    "clay loam": (0.32, 0.18),
    "clay": (0.36, 0.22),
}


@dataclass
class DrySpell:
    start: str
    length_days: int
    total_rain_mm: float
    severity: str  # moderate | severe
    ongoing: bool  # run extends to the end of the horizon


@dataclass
class WaterBalance:
    etc_mm: float
    rain_eff_mm: float
    soil_buffer_mm: float
    irrigation_mm: float
    level: str  # none | light | urgent


@dataclass
class NdviStress:
    date: str
    ndvi: float
    baseline: float | None
    anomaly: float | None
    trend: float | None
    severity: str  # moderate | severe


def detect_ndvi_stress(windows: list[dict], as_of: date) -> NdviStress | None:
    """Satellite crop-stress signal from the plot's NDVI window series.

    windows: [{date_start: date, ndvi: float|None}] chronological.
    Anomaly compares the latest reading against the same-period-last-year
    baseline (mean of windows within +/-15 days of the anniversary), so normal
    seasonal senescence and fallow periods do not trigger alerts. Trend catches
    sharp in-season declines that have no anniversary analogue.
    """
    valid = [w for w in windows if w.get("ndvi") is not None and w["date_start"] <= as_of]
    if not valid:
        return None
    latest = valid[-1]
    if (as_of - latest["date_start"]).days > NDVI_STALE_DAYS:
        return None

    anniversary = latest["date_start"] - timedelta(days=365)
    base_vals = [w["ndvi"] for w in valid if abs((w["date_start"] - anniversary).days) <= 15]
    baseline = sum(base_vals) / len(base_vals) if base_vals else None
    anomaly = latest["ndvi"] - baseline if baseline is not None else None
    prev3 = [w["ndvi"] for w in valid[:-1]][-3:]
    trend = latest["ndvi"] - sum(prev3) / len(prev3) if prev3 else None

    severe = anomaly is not None and anomaly <= NDVI_ANOMALY_SEVERE
    moderate = (anomaly is not None and anomaly <= NDVI_ANOMALY_MODERATE) or (
        trend is not None and trend <= NDVI_TREND_THRESHOLD
    )
    if not (severe or moderate):
        return None
    return NdviStress(
        latest["date_start"].isoformat(),
        round(latest["ndvi"], 3),
        round(baseline, 3) if baseline is not None else None,
        round(anomaly, 3) if anomaly is not None else None,
        round(trend, 3) if trend is not None else None,
        "severe" if severe else "moderate",
    )


def detect_dry_spell(days: list[dict]) -> DrySpell | None:
    """Longest run of non-rainy days in a chronological daily series."""
    best: dict | None = None
    cur: dict | None = None
    for d in days:
        rain = d.get("rain_mm") or 0.0
        if rain < RAINY_DAY_MM:
            if cur is None:
                cur = {"start": d["date"], "length": 0, "rain": 0.0, "end": d["date"]}
            cur["length"] += 1
            cur["rain"] += rain
            cur["end"] = d["date"]
            if best is None or cur["length"] > best["length"]:
                best = dict(cur)
        else:
            cur = None
    if not best or best["length"] < DRY_SPELL_MIN_DAYS:
        return None
    ongoing = best["end"] == days[-1]["date"]
    severity = (
        "severe" if best["length"] >= 12 or (ongoing and best["length"] >= 10) else "moderate"
    )
    return DrySpell(best["start"], best["length"], round(best["rain"], 1), severity, ongoing)


def water_balance(
    days: list[dict],
    kc: float,
    soil_moisture: float | None,
    texture: str | None,
    horizon: int = 7,
) -> WaterBalance:
    """Irrigation need over the next `horizon` days: ETc - effective rain - soil buffer.

    The soil buffer is water held above the critical depletion level in the
    root zone; if current moisture is unknown we assume the crop sits exactly
    at the critical level (buffer 0) rather than inventing headroom.
    """
    window = days[:horizon]
    etc = sum(kc * (d.get("et0_mm") or 0.0) for d in window)
    rain_eff = sum(EFFECTIVE_RAIN_FACTOR * (d.get("rain_mm") or 0.0) for d in window)
    fc, wp = SOIL_WATER.get(texture or "loam", SOIL_WATER["loam"])
    theta_crit = wp + DEPLETION_FRACTION * (fc - wp)
    buffer_mm = (
        max(0.0, ((soil_moisture if soil_moisture is not None else theta_crit) - theta_crit))
        * ROOT_ZONE_MM
    )
    irrigation = max(0.0, etc - rain_eff - buffer_mm)
    level = "none" if irrigation < 10 else ("light" if irrigation < 35 else "urgent")
    return WaterBalance(
        round(etc, 1), round(rain_eff, 1), round(buffer_mm, 1), round(irrigation, 1), level
    )
