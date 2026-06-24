import json

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..db import DbSession
from ..models import GroundwaterLevel, IndicatorWindow, Plot, SoilProfile

router = APIRouter(prefix="/api", tags=["plots"])


@router.get("/regions")
def list_regions(db: DbSession):
    """Regions the app currently serves, each with a map center computed from
    its own plots — so a new constituency needs only its plots, no map config."""
    meta = json.loads((settings.data_dir / "regions.json").read_text())
    out = []
    for region_id in sorted({p.region for p in db.query(Plot).all()}):
        plots = db.query(Plot).filter_by(region=region_id).all()
        m = meta.get(region_id, {})
        out.append(
            {
                "id": region_id,
                "name": m.get("name", region_id.title()),
                "district": m.get("district"),
                "state": m.get("state"),
                "mp": m.get("mp"),
                "zoom": m.get("zoom", 10),
                "plot_count": len(plots),
                "center": [
                    sum(p.lat for p in plots) / len(plots),
                    sum(p.lon for p in plots) / len(plots),
                ],
            }
        )
    return out


@router.get("/plots")
def list_plots(db: DbSession, region: str | None = None):
    query = db.query(Plot)
    if region:
        query = query.filter_by(region=region)
    out = []
    for plot in query.all():
        soil = db.get(SoilProfile, plot.id)
        gw = db.get(GroundwaterLevel, plot.mandal)
        out.append(
            {
                "id": plot.id,
                "region": plot.region,
                "farmer": plot.farmer,
                "village": plot.village,
                "mandal": plot.mandal,
                "crop_current": plot.crop_current,
                "area_ha": plot.area_ha,
                "lon": plot.lon,
                "lat": plot.lat,
                "geometry": plot.geometry,
                "irrigation": plot.irrigation,
                "soil": soil
                and {
                    "ph": soil.ph,
                    "clay_pct": soil.clay_pct,
                    "sand_pct": soil.sand_pct,
                    "soc_g_kg": soil.soc_g_kg,
                    "texture": soil.texture,
                },
                "groundwater": gw
                and {
                    "pre_monsoon_dtw_m": gw.pre_monsoon_dtw_m,
                    "post_monsoon_dtw_m": gw.post_monsoon_dtw_m,
                    "category": gw.category,
                },
            }
        )
    return out


@router.get("/plots/{plot_id}/indicators")
def plot_indicators(plot_id: str, db: DbSession):
    if not db.get(Plot, plot_id):
        raise HTTPException(404, "unknown plot")
    rows = (
        db.query(IndicatorWindow)
        .filter_by(plot_id=plot_id)
        .order_by(IndicatorWindow.date_start)
        .all()
    )
    return [
        {
            "date": r.date_start.isoformat(),
            "ndvi": r.ndvi,
            "ndmi": r.ndmi,
            "rain_mm": r.rain_mm,
            "et0_mm": r.et0_mm,
            "soil_moisture": r.soil_moisture,
        }
        for r in rows
    ]
