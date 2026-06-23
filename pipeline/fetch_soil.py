"""Fetch point soil properties for each plot from ISRIC SoilGrids v2 REST API.

Runs without credentials. Values: pH (H2O), clay %, sand %, SOC g/kg,
averaged over the 0-5cm and 5-15cm depth layers.
"""

import time

import httpx

from common import centroid, load_plots, write_artifact

API = "https://rest.isric.org/soilgrids/v2.0/properties/query"
PROPS = ["phh2o", "clay", "sand", "soc"]
# SoilGrids serves scaled integer "mapped units"; divide to get conventional units
D_FACTOR = {"phh2o": 10, "clay": 10, "sand": 10, "soc": 10}


def texture_class(clay_pct: float, sand_pct: float) -> str:
    if clay_pct >= 35:
        return "clay"
    if sand_pct >= 60:
        return "sandy loam"
    if clay_pct >= 25:
        return "clay loam"
    return "loam"


def fetch_point(client: httpx.Client, lon: float, lat: float) -> dict:
    params = [("lon", lon), ("lat", lat), ("value", "mean")]
    params += [("property", p) for p in PROPS]
    params += [("depth", d) for d in ("0-5cm", "5-15cm")]
    r = client.get(API, params=params, timeout=60)
    r.raise_for_status()
    out = {}
    for layer in r.json()["properties"]["layers"]:
        vals = [d["values"]["mean"] for d in layer["depths"] if d["values"].get("mean") is not None]
        if vals:
            out[layer["name"]] = round(sum(vals) / len(vals) / D_FACTOR[layer["name"]], 2)
    return out


def main() -> None:
    results = {}
    with httpx.Client() as client:
        for f in load_plots():
            pid = f["properties"]["id"]
            lon, lat = centroid(f)
            raw = fetch_point(client, lon, lat)
            results[pid] = {
                "ph": raw.get("phh2o"),
                "clay_pct": raw.get("clay"),
                "sand_pct": raw.get("sand"),
                "soc_g_kg": raw.get("soc"),
                "texture": texture_class(raw.get("clay") or 0, raw.get("sand") or 0),
                "lon": round(lon, 5),
                "lat": round(lat, 5),
            }
            print(pid, results[pid])
            time.sleep(1.5)  # SoilGrids rate limit is strict
    write_artifact("soil", {"source": "ISRIC SoilGrids v2.0 (0-15cm mean)", "plots": results})


if __name__ == "__main__":
    main()
