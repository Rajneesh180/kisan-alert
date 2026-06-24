from fastapi import APIRouter, HTTPException

from ..db import DbSession
from ..models import Plot
from ..services.ndvi_forecast import forecast_ndvi, get_eval_metrics
from ..services.weather import forecast_days

router = APIRouter(prefix="/api", tags=["forecast"])


@router.get("/forecast")
def get_forecast(plot_id: str, db: DbSession):
    plot = db.get(Plot, plot_id)
    if not plot:
        raise HTTPException(404, "unknown plot")
    return {"plot_id": plot.id, "days": forecast_days(plot.lat, plot.lon)}


@router.get("/forecast/ndvi")
def get_ndvi_forecast(plot_id: str, db: DbSession):
    plot = db.get(Plot, plot_id)
    if not plot:
        raise HTTPException(404, "unknown plot")
    result = forecast_ndvi(db, plot_id)
    if result is None:
        raise HTTPException(503, "NDVI model not trained or insufficient data")
    return result


@router.get("/forecast/ndvi/eval")
def ndvi_eval():
    metrics = get_eval_metrics()
    if metrics is None:
        raise HTTPException(503, "NDVI model not trained")
    return metrics
