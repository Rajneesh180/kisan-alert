"""Degraded-mode flows: everything here must pass with no GEMINI_API_KEY and
no network — the platform's floor is deterministic and offline-capable."""

from fastapi.testclient import TestClient

from app.main import app


def test_advisory_falls_back_deterministically():
    with TestClient(app) as client:
        res = client.post(
            "/api/advisory",
            json={"plot_id": "plot-raptadu-01", "question": "When should I water?", "lang": "te"},
        ).json()
        assert res["degraded"] is True
        assert res["answer"]  # plot-specific fallback, not an error
        assert "Raptadu" in res["answer"]
        assert res["grounding"]["village"] == "Raptadu"


def test_health_log_escalates_without_ai_and_expert_reply_closes_loop():
    with TestClient(app) as client:
        created = client.post(
            "/api/health-log",
            data={"plot_id": "plot-narpala-05", "lang": "te", "note": "leaves turning yellow"},
        ).json()
        assert created["escalated"] is True  # no AI available -> human loop

        cases = client.get("/api/rsk/cases").json()
        case = next(c for c in cases if c["id"] == created["id"])
        assert case["plot"]["village"] == "Narpala"

        replied = client.post(
            f"/api/rsk/cases/{created['id']}/reply",
            json={"reply": "Looks like nitrogen deficiency; apply urea top dressing."},
        ).json()
        assert replied["expert_reply"].startswith("Looks like")

        logs = client.get("/api/health-log", params={"plot_id": "plot-narpala-05"}).json()
        assert logs[0]["expert_reply"]


def test_sms_keywords_route_to_engines():
    with TestClient(app) as client:
        pani = client.post(
            "/api/sms/inbound",
            json={"plot_id": "plot-raptadu-01", "text": "PANI", "lang": "te"},
        ).json()
        assert pani["reply"] and pani["segments"] >= 1

        fasal = client.post(
            "/api/sms/inbound",
            json={"plot_id": "plot-raptadu-01", "text": "fasal", "lang": "hi"},
        ).json()
        assert "किसान" in fasal["reply"]

        other = client.post(
            "/api/sms/inbound",
            json={"plot_id": "plot-raptadu-01", "text": "hello", "lang": "en"},
        ).json()
        assert "PANI" in other["reply"] and "FASAL" in other["reply"]


def test_sensor_ingestion_roundtrip():
    with TestClient(app) as client:
        post = client.post(
            "/api/sensors/reading",
            json={"plot_id": "plot-atmakur-06", "metric": "soil_moisture_sim", "value": 0.19},
        )
        assert post.status_code == 200
        rows = client.get("/api/sensors", params={"plot_id": "plot-atmakur-06"}).json()
        assert rows[0]["metric"] == "soil_moisture_sim"
