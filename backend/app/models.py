from datetime import date, datetime

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Plot(Base):
    __tablename__ = "plots"

    id: Mapped[str] = mapped_column(primary_key=True)
    region: Mapped[str] = mapped_column(index=True, default="anantapur")
    farmer: Mapped[str]
    village: Mapped[str]
    mandal: Mapped[str]
    crop_current: Mapped[str]
    area_ha: Mapped[float]
    lon: Mapped[float]
    lat: Mapped[float]
    geometry: Mapped[dict] = mapped_column(JSON)
    irrigation: Mapped[str | None]


class SoilProfile(Base):
    __tablename__ = "soil_profiles"

    plot_id: Mapped[str] = mapped_column(ForeignKey("plots.id"), primary_key=True)
    ph: Mapped[float | None]
    clay_pct: Mapped[float | None]
    sand_pct: Mapped[float | None]
    soc_g_kg: Mapped[float | None]
    texture: Mapped[str | None]


class IndicatorWindow(Base):
    __tablename__ = "indicator_windows"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plot_id: Mapped[str] = mapped_column(ForeignKey("plots.id"), index=True)
    date_start: Mapped[date]
    ndvi: Mapped[float | None]
    ndmi: Mapped[float | None]
    rain_mm: Mapped[float | None]
    et0_mm: Mapped[float | None]
    soil_moisture: Mapped[float | None]


class GroundwaterLevel(Base):
    __tablename__ = "groundwater_levels"

    mandal: Mapped[str] = mapped_column(primary_key=True)
    district: Mapped[str]
    pre_monsoon_dtw_m: Mapped[float]
    post_monsoon_dtw_m: Mapped[float]
    category: Mapped[str]


class CropRequirement(Base):
    __tablename__ = "crop_requirements"

    crop: Mapped[str] = mapped_column(primary_key=True)
    label_en: Mapped[str]
    label_te: Mapped[str]
    label_hi: Mapped[str]
    season: Mapped[str]
    duration_days: Mapped[int]
    water_need_mm: Mapped[float]
    kc_mid: Mapped[float]
    soil_ph_min: Mapped[float]
    soil_ph_max: Mapped[float]
    soil_texture: Mapped[str]
    min_temp_c: Mapped[float]
    max_temp_c: Mapped[float]
    rainfed_ok: Mapped[str]
    groundwater_need: Mapped[str]
    n_kg_ha: Mapped[float]
    p_kg_ha: Mapped[float]
    k_kg_ha: Mapped[float]
    source: Mapped[str]


class HealthLog(Base):
    __tablename__ = "health_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plot_id: Mapped[str] = mapped_column(ForeignKey("plots.id"), index=True)
    created_at: Mapped[datetime]
    source: Mapped[str]  # photo | voice | text
    language: Mapped[str]
    transcript: Mapped[str | None]
    media_path: Mapped[str | None]
    diagnosis: Mapped[str | None]
    confidence: Mapped[float | None]
    severity: Mapped[str | None]
    treatment: Mapped[str | None]
    escalated: Mapped[bool] = mapped_column(default=False)
    expert_reply: Mapped[str | None]
    replied_at: Mapped[datetime | None]


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plot_id: Mapped[str] = mapped_column(ForeignKey("plots.id"), index=True)
    ts: Mapped[datetime]
    metric: Mapped[str]
    value: Mapped[float]
