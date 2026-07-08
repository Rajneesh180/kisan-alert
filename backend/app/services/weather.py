"""Live 16-day forecast from Open-Meteo (keyless) with a small TTL cache, plus
a replay series rebuilt from the plot's own recorded history so the alert flow
can be demonstrated year-round regardless of the actual monsoon.
"""

import time
from datetime import date, timedelta

import httpx
from sqlalchemy.orm import Session

from ..models import IndicatorWindow

FORECAST_API = "https://api.open-meteo.com/v1/forecast"
DAILY_VARS = "precipitation_sum,et0_fao_evapotranspiration,temperature_2m_max,temperature_2m_min"
CACHE_TTL_S = 3600

WINDOW_DAYS = 10  # must match the pipeline window grid (pipeline/common.py)
# Deep inside the real recorded Dec 2025-Apr 2026 dry spell: by March soil
# moisture is depleted, so both the dry-spell and irrigation alerts fire.
REPLAY_START = date(2026, 3, 10)
REPLAY_LEN = 16
REPLAY_NOTE = (
    "Replay of real recorded conditions from the Dec 2025-Apr 2026 Anantapur dry "
    "spell (Open-Meteo ERA5 archive), so the alert flow can be demonstrated year-round."
)
LIVE_FALLBACK_NOTE = (
    "Live weather is unreachable from this demo host, so the alert flow is shown on "
    "real recorded conditions (Dec 2025-Apr 2026 Anantapur dry spell, Open-Meteo ERA5 "
    "archive). It uses the live Open-Meteo forecast wherever outbound access is open."
)

_cache: dict[tuple[float, float], tuple[float, list[dict]]] = {}


def forecast_days(lat: float, lon: float) -> list[dict]:
    key = (round(lat, 3), round(lon, 3))
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL_S:
        return hit[1]
    try:
        r = httpx.get(
            FORECAST_API,
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": DAILY_VARS,
                "forecast_days": 16,
                "timezone": "Asia/Kolkata",
            },
            timeout=30,
        )
        r.raise_for_status()
        daily = r.json()["daily"]
    except (httpx.HTTPError, KeyError):
        # Offline/outage: engines treat an empty series as "no data", and the
        # replay path stays fully functional from committed artifacts.
        return []
    days = [
        {"date": t, "rain_mm": p, "et0_mm": e, "tmax_c": tx, "tmin_c": tn}
        for t, p, e, tx, tn in zip(
            daily["time"],
            daily["precipitation_sum"],
            daily["et0_fao_evapotranspiration"],
            daily["temperature_2m_max"],
            daily["temperature_2m_min"],
            strict=True,
        )
    ]
    _cache[key] = (time.time(), days)
    return days


def replay_days(db: Session, plot_id: str) -> list[dict]:
    """Rebuild a daily series from the plot's recorded 10-day windows (rain and
    ET0 spread evenly within each window)."""
    end = REPLAY_START + timedelta(days=REPLAY_LEN)
    rows = (
        db.query(IndicatorWindow)
        .filter_by(plot_id=plot_id)
        .order_by(IndicatorWindow.date_start)
        .all()
    )
    days = []
    for row in rows:
        for i in range(WINDOW_DAYS):
            d = row.date_start + timedelta(days=i)
            if REPLAY_START <= d < end:
                days.append(
                    {
                        "date": d.isoformat(),
                        "rain_mm": (row.rain_mm or 0.0) / WINDOW_DAYS,
                        "et0_mm": (row.et0_mm or 0.0) / WINDOW_DAYS,
                        "soil_moisture": row.soil_moisture,
                    }
                )
    return days


def latest_soil_moisture(db: Session, plot_id: str) -> float | None:
    row = (
        db.query(IndicatorWindow)
        .filter(IndicatorWindow.plot_id == plot_id, IndicatorWindow.soil_moisture.isnot(None))
        .order_by(IndicatorWindow.date_start.desc())
        .first()
    )
    return row.soil_moisture if row else None


def ndvi_windows(db: Session, plot_id: str) -> list[dict]:
    """Chronological NDVI windows for the plot, for satellite crop-stress checks."""
    rows = (
        db.query(IndicatorWindow)
        .filter_by(plot_id=plot_id)
        .order_by(IndicatorWindow.date_start)
        .all()
    )
    return [{"date_start": r.date_start, "ndvi": r.ndvi} for r in rows]
