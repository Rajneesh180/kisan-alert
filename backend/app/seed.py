"""Seed SQLite from data/ CSVs and pipeline artifacts.

Runs on every boot: HF Spaces storage is ephemeral, so the app must rebuild all
reference state from files committed to the repo.
"""

import csv
import json
from datetime import date

from sqlalchemy.orm import Session

from .config import settings
from .db import Base, engine
from .models import (
    CropRequirement,
    GroundwaterLevel,
    IndicatorWindow,
    Plot,
    SoilProfile,
)


def _centroid(geom: dict) -> tuple[float, float]:
    pts = geom["coordinates"][0][:-1]
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def seed() -> None:
    Base.metadata.create_all(engine)
    data = settings.data_dir
    with Session(engine) as db:
        for model in (IndicatorWindow, SoilProfile, Plot, GroundwaterLevel, CropRequirement):
            db.query(model).delete()

        fc = json.loads((data / "plots.geojson").read_text())
        for f in fc["features"]:
            p = f["properties"]
            lon, lat = _centroid(f["geometry"])
            db.add(
                Plot(
                    id=p["id"],
                    region=p.get("region", "anantapur"),
                    farmer=p["farmer"],
                    village=p["village"],
                    mandal=p["mandal"],
                    crop_current=p["crop_current"],
                    area_ha=p["area_ha"],
                    lon=lon,
                    lat=lat,
                    geometry=f["geometry"],
                    irrigation=p.get("irrigation"),
                )
            )

        with open(data / "groundwater.csv") as fh:
            for row in csv.DictReader(fh):
                db.add(
                    GroundwaterLevel(
                        mandal=row["mandal"],
                        district=row["district"],
                        pre_monsoon_dtw_m=float(row["pre_monsoon_dtw_m"]),
                        post_monsoon_dtw_m=float(row["post_monsoon_dtw_m"]),
                        category=row["category"],
                    )
                )

        with open(data / "crop_requirements.csv") as fh:
            for row in csv.DictReader(fh):
                db.add(
                    CropRequirement(
                        crop=row["crop"],
                        label_en=row["label_en"],
                        label_te=row["label_te"],
                        label_hi=row["label_hi"],
                        season=row["season"],
                        duration_days=int(row["duration_days"]),
                        water_need_mm=float(row["water_need_mm"]),
                        kc_mid=float(row["kc_mid"]),
                        soil_ph_min=float(row["soil_ph_min"]),
                        soil_ph_max=float(row["soil_ph_max"]),
                        soil_texture=row["soil_texture"],
                        min_temp_c=float(row["min_temp_c"]),
                        max_temp_c=float(row["max_temp_c"]),
                        rainfed_ok=row["rainfed_ok"],
                        groundwater_need=row["groundwater_need"],
                        n_kg_ha=float(row["n_kg_ha"]),
                        p_kg_ha=float(row["p_kg_ha"]),
                        k_kg_ha=float(row["k_kg_ha"]),
                        source=row["source"],
                    )
                )

        artifacts = data / "artifacts"
        soil_f = artifacts / "soil.json"
        if soil_f.exists():
            for pid, s in json.loads(soil_f.read_text())["plots"].items():
                db.add(
                    SoilProfile(
                        plot_id=pid,
                        ph=s.get("ph"),
                        clay_pct=s.get("clay_pct"),
                        sand_pct=s.get("sand_pct"),
                        soc_g_kg=s.get("soc_g_kg"),
                        texture=s.get("texture"),
                    )
                )

        windows: dict[tuple[str, str], dict] = {}
        sat_f = artifacts / "satellite.json"
        if sat_f.exists():
            for pid, series in json.loads(sat_f.read_text())["plots"].items():
                for w in series:
                    windows.setdefault((pid, w["date_start"]), {}).update(
                        ndvi=w.get("ndvi"), ndmi=w.get("ndmi")
                    )
        clim_f = artifacts / "climate.json"
        if clim_f.exists():
            for pid, series in json.loads(clim_f.read_text())["plots"].items():
                for w in series:
                    windows.setdefault((pid, w["date_start"]), {}).update(
                        rain_mm=w.get("rain_mm"),
                        et0_mm=w.get("et0_mm"),
                        soil_moisture=w.get("soil_moisture"),
                    )
        for (pid, ds), vals in sorted(windows.items()):
            db.add(IndicatorWindow(plot_id=pid, date_start=date.fromisoformat(ds), **vals))

        db.commit()
