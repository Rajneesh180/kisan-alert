from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.services import ndvi_forecast as nf

PLOT = "plot-narasaraopet-01"


def test_forecast_returns_expected_shape():
    with TestClient(app) as client:
        res = client.get("/api/forecast/ndvi", params={"plot_id": PLOT})
        assert res.status_code == 200
        d = res.json()
        assert d["plot_id"] == PLOT
        for k in ("current_ndvi", "predicted_ndvi", "predicted_date", "delta", "stress_warning"):
            assert k in d
        assert -0.2 <= d["predicted_ndvi"] <= 1.2  # NDVI stays in a sane band
        assert isinstance(d["stress_warning"], bool)


def test_model_beats_persistence_baseline():
    """The point of the model is to do real work, not decorate. If it ever stops
    beating the naive persistence baseline (leakage-free, leave-one-plot-out),
    that is a regression worth failing on."""
    with TestClient(app) as client:
        m = client.get("/api/forecast/ndvi/eval").json()
        assert m["cv"] == "leave-one-plot-out"
        assert m["model_rmse"] < m["persistence_rmse"]
        assert m["skill_vs_persistence_pct"] > 0
        assert m["top_drivers"]  # interpretable leading indicators reported


def test_forecast_unknown_plot_404():
    with TestClient(app) as client:
        assert client.get("/api/forecast/ndvi", params={"plot_id": "nope"}).status_code == 404


def test_training_is_reproducible():
    with TestClient(app):  # boots + seeds
        with SessionLocal() as db:
            _, m1 = nf.train(db)
            _, m2 = nf.train(db)
        assert m1["model_rmse"] == m2["model_rmse"]
        assert m1["skill_vs_persistence_pct"] == m2["skill_vs_persistence_pct"]
