from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from ..db import DbSession
from ..models import CropRequirement, Plot, SoilProfile
from ..services.fertilizer import plan_fertilizer

router = APIRouter(prefix="/api", tags=["fertilizer"])


@router.get("/fertilizer")
def get_fertilizer(plot_id: str, db: DbSession, crop: str | None = None):
    plot = db.get(Plot, plot_id)
    if not plot:
        raise HTTPException(404, "unknown plot")
    crop_id = crop or plot.crop_current
    req = db.get(CropRequirement, crop_id)
    if not req:
        raise HTTPException(404, "unknown crop")
    soil = db.get(SoilProfile, plot.id)
    plan = plan_fertilizer(
        crop=crop_id,
        n_kg_ha=req.n_kg_ha,
        p_kg_ha=req.p_kg_ha,
        k_kg_ha=req.k_kg_ha,
        soc_g_kg=soil.soc_g_kg if soil else None,
        ph=soil.ph if soil else None,
    )
    return {
        "plot_id": plot.id,
        "crop_label": {"en": req.label_en, "te": req.label_te, "hi": req.label_hi},
        "source": req.source,
        **asdict(plan),
    }
