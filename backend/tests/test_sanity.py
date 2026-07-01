from fastapi.testclient import TestClient

from app.main import app


def test_boot_and_seed():
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        plots = client.get("/api/plots").json()
        assert len(plots) >= 6
        assert {p["crop_current"] for p in plots} >= {"groundnut", "paddy"}
        assert all(p["groundwater"]["category"] for p in plots)


def test_regions_and_region_filter():
    with TestClient(app) as client:
        regions = {r["id"]: r for r in client.get("/api/regions").json()}
        assert {"anantapur", "narasaraopet"} <= set(regions)
        # each region's map center is computed from its own plots, not hardcoded
        assert 13 < regions["anantapur"]["center"][0] < 16
        assert 15 < regions["narasaraopet"]["center"][0] < 17
        nara = client.get("/api/plots", params={"region": "narasaraopet"}).json()
        assert nara and all(p["region"] == "narasaraopet" for p in nara)


def test_indicators_endpoint():
    with TestClient(app) as client:
        plots = client.get("/api/plots").json()
        rows = client.get(f"/api/plots/{plots[0]['id']}/indicators").json()
        # climate.json is committed, so seeded windows must carry real climate data
        assert len(rows) >= 50
        assert any(r["rain_mm"] is not None for r in rows)
        assert any(r["et0_mm"] is not None for r in rows)
        assert client.get("/api/plots/nope/indicators").status_code == 404
