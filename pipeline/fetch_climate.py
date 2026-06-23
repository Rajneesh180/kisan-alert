"""Fetch 18 months of daily rainfall, ET0 and soil moisture per plot from the
Open-Meteo historical archive (ERA5/ERA5-Land), aggregated to the same 10-day
windows as fetch_satellite.py.

Keyless by design: the climate stream must never block on Earth Engine
registration. ~9-11 km resolution — each plot inherits its enclosing grid
cell, the best freely available "ground sensor proxy" until physical IoT
probes are deployed.
"""

import time

import httpx

from common import centroid, load_plots, ten_day_windows, write_artifact

API = "https://archive-api.open-meteo.com/v1/archive"
DAILY_VARS = "precipitation_sum,et0_fao_evapotranspiration,soil_moisture_0_to_7cm_mean"

WINDOW_DAYS = 10
MONTHS_BACK = 18


def fetch_daily(client: httpx.Client, lat: float, lon: float, start: str, end: str) -> dict:
    r = client.get(
        API,
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": start,
            "end_date": end,
            "daily": DAILY_VARS,
            "timezone": "Asia/Kolkata",
        },
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["daily"]


def aggregate(daily: dict, windows: list[tuple[str, str]]) -> list[dict]:
    days = daily["time"]
    rain = daily["precipitation_sum"]
    et0 = daily["et0_fao_evapotranspiration"]
    sm = daily["soil_moisture_0_to_7cm_mean"]
    out = []
    for w_start, w_end in windows:
        idx = [i for i, d in enumerate(days) if w_start <= d < w_end]
        rains = [rain[i] for i in idx if rain[i] is not None]
        et0s = [et0[i] for i in idx if et0[i] is not None]
        sms = [sm[i] for i in idx if sm[i] is not None]
        out.append(
            {
                "date_start": w_start,
                "rain_mm": round(sum(rains), 2) if rains else None,
                "et0_mm": round(sum(et0s), 2) if et0s else None,
                "soil_moisture": round(sum(sms) / len(sms), 4) if sms else None,
            }
        )
    return out


def main() -> None:
    windows = ten_day_windows(MONTHS_BACK, WINDOW_DAYS)
    start, end = windows[0][0], windows[-1][1]
    results = {}
    with httpx.Client() as client:
        for f in load_plots():
            pid = f["properties"]["id"]
            lon, lat = centroid(f)
            daily = fetch_daily(client, lat, lon, start, end)
            results[pid] = aggregate(daily, windows)
            valid = sum(1 for w in results[pid] if w["rain_mm"] is not None)
            print(f"{pid}: {len(results[pid])} windows, {valid} with data")
            time.sleep(0.5)

    write_artifact(
        "climate",
        {
            "source": "Open-Meteo historical archive (ERA5/ERA5-Land): daily precipitation, "
            "FAO-56 ET0 and 0-7cm soil moisture, aggregated to 10-day windows",
            "window_days": WINDOW_DAYS,
            "plots": results,
        },
    )


if __name__ == "__main__":
    main()
