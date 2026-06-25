from datetime import date

from fastapi import APIRouter, HTTPException

from ..db import DbSession
from ..models import Plot
from ..services.recommend import current_season, recommend_for_plot

router = APIRouter(prefix="/api", tags=["recommend"])


@router.get("/recommend")
def recommend(plot_id: str, db: DbSession, season: str = "auto"):
    plot = db.get(Plot, plot_id)
    if not plot:
        raise HTTPException(404, "unknown plot")
    if season == "auto":
        season = current_season(date.today().month)
    if season not in ("kharif", "rabi"):
        raise HTTPException(422, "season must be kharif, rabi or auto")
    return recommend_for_plot(db, plot, season)
