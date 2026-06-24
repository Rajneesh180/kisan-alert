"""IoT ingestion endpoint. In the demo a simulated probe posts here (clearly
labeled); ERA5-Land soil moisture in the indicator series is the real-data
proxy layer. Physical probes plug into this same interface."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import DbSession
from ..models import Plot, SensorReading

router = APIRouter(prefix="/api", tags=["sensors"])


class ReadingIn(BaseModel):
    plot_id: str
    metric: str
    value: float


@router.post("/sensors/reading")
def add_reading(payload: ReadingIn, db: DbSession):
    if not db.get(Plot, payload.plot_id):
        raise HTTPException(404, "unknown plot")
    row = SensorReading(
        plot_id=payload.plot_id,
        ts=datetime.now(UTC),
        metric=payload.metric,
        value=payload.value,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "ts": row.ts.isoformat()}


@router.get("/sensors")
def latest_readings(plot_id: str, db: DbSession, limit: int = 10):
    if not db.get(Plot, plot_id):
        raise HTTPException(404, "unknown plot")
    rows = (
        db.query(SensorReading)
        .filter_by(plot_id=plot_id)
        .order_by(SensorReading.ts.desc())
        .limit(min(limit, 50))
        .all()
    )
    return [{"ts": r.ts.isoformat(), "metric": r.metric, "value": r.value} for r in rows]
