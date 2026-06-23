"""Fetch 18 months of Sentinel-2 NDVI/NDMI 10-day composites per plot via Google Earth Engine.

One-time prereqs:
  1. Register a Cloud project for noncommercial Earth Engine (earthengine.google.com)
  2. uv run python -c "import ee; ee.Authenticate()"
  3. Set GEE_PROJECT in .env

NDVI (B8,B4) tracks canopy vigour; NDMI (B8A,B11) tracks vegetation water content.
SCL classes 3/8/9/10/11 (shadow, clouds, cirrus, snow) are masked before compositing.
"""

import os

import ee

from common import load_env, load_plots, ten_day_windows, write_artifact

WINDOW_DAYS = 10
MONTHS_BACK = 18


def s2_masked(region: ee.Geometry, start: ee.Date, end: ee.Date) -> ee.ImageCollection:
    def mask_scl(img: ee.Image) -> ee.Image:
        scl = img.select("SCL")
        bad = scl.eq(3).Or(scl.eq(8)).Or(scl.eq(9)).Or(scl.eq(10)).Or(scl.eq(11))
        return img.updateMask(bad.Not())

    return (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 60))
        .map(mask_scl)
    )


def window_series(region: ee.Geometry, windows: list[tuple[str, str]]) -> ee.FeatureCollection:
    coll = s2_masked(region, ee.Date(windows[0][0]), ee.Date(windows[-1][1]))

    def per_window(s: ee.String) -> ee.Feature:
        w_start = ee.Date(s)
        w_end = w_start.advance(WINDOW_DAYS, "day")
        window = coll.filterDate(w_start, w_end)
        med = window.median()
        ndvi = med.normalizedDifference(["B8", "B4"]).rename("ndvi")
        ndmi = med.normalizedDifference(["B8A", "B11"]).rename("ndmi")
        stats = ndvi.addBands(ndmi).reduceRegion(
            reducer=ee.Reducer.mean(), geometry=region, scale=20, maxPixels=1e8
        )
        filled = ee.Feature(
            None,
            {
                "date_start": w_start.format("YYYY-MM-dd"),
                "ndvi": stats.get("ndvi"),
                "ndmi": stats.get("ndmi"),
                "n_images": window.size(),
            },
        )
        empty = ee.Feature(None, {"date_start": w_start.format("YYYY-MM-dd"), "n_images": 0})
        return ee.Feature(ee.Algorithms.If(window.size().gt(0), filled, empty))

    return ee.FeatureCollection(ee.List([w[0] for w in windows]).map(per_window))


def main() -> None:
    load_env()
    ee.Initialize(project=os.environ.get("GEE_PROJECT") or None)
    windows = ten_day_windows(MONTHS_BACK, WINDOW_DAYS)

    results = {}
    for f in load_plots():
        pid = f["properties"]["id"]
        region = ee.Geometry.Polygon(f["geometry"]["coordinates"])
        feats = window_series(region, windows).getInfo()["features"]
        series = sorted((x["properties"] for x in feats), key=lambda r: r["date_start"])
        results[pid] = series
        valid = sum(1 for r in series if r.get("ndvi") is not None)
        print(f"{pid}: {len(series)} windows, {valid} with data")

    write_artifact(
        "satellite",
        {
            "source": "Sentinel-2 SR Harmonized via Google Earth Engine; "
            "SCL cloud-masked, 10-day median composites, 20 m",
            "window_days": WINDOW_DAYS,
            "plots": results,
        },
    )


if __name__ == "__main__":
    main()
