"""Shared helpers for pipeline scripts.

Artifacts are committed to the repo so the deployed app never needs live
GEE/SoilGrids access — it rebuilds SQLite from data/ on every boot.
"""

import calendar
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
ARTIFACTS_DIR = DATA_DIR / "artifacts"


def load_env() -> None:
    """Minimal .env loader so pipeline scripts don't need python-dotenv."""
    import os

    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def load_plots() -> list[dict]:
    fc = json.loads((DATA_DIR / "plots.geojson").read_text())
    return fc["features"]


def centroid(feature: dict) -> tuple[float, float]:
    ring = feature["geometry"]["coordinates"][0]
    pts = ring[:-1]
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def months_back(d: date, n: int) -> date:
    month = d.month - n
    year = d.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


GRID_EPOCH = date(2025, 1, 1)


def ten_day_windows(months: int = 18, window_days: int = 10) -> list[tuple[str, str]]:
    """Aligned windows (start inclusive, end exclusive) shared by all pipeline
    scripts so the backend can merge satellite and climate series by date_start.

    Anchored to GRID_EPOCH, not to today: scripts run on different days must
    still produce identical date_start keys or the series never join.
    """
    today = date.today()
    bound = months_back(today, months)
    offset = (bound - GRID_EPOCH).days % window_days
    w = bound + timedelta(days=(window_days - offset) % window_days)
    windows = []
    while (w_end := w + timedelta(days=window_days)) <= today:
        windows.append((w.isoformat(), w_end.isoformat()))
        w = w_end
    return windows


def write_artifact(name: str, payload: dict) -> Path:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    out = ARTIFACTS_DIR / f"{name}.json"
    out.write_text(json.dumps({"fetched_at": datetime.now(UTC).isoformat(), **payload}, indent=1))
    print(f"wrote {out}")
    return out
