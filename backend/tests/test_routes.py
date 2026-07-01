from fastapi.testclient import TestClient

from app.main import app


def test_alerts_replay_fires_dry_spell():
    """Replay mode runs entirely on committed data - no network - and must
    always produce the dry-spell alert (it replays a real recorded dry spell)."""
    with TestClient(app) as client:
        res = client.get(
            "/api/alerts", params={"plot_id": "plot-raptadu-01", "mode": "replay"}
        ).json()
        assert res["mode"] == "replay"
        assert res["replay_note"]
        assert res["dry_spell"] is not None
        assert res["dry_spell"]["length_days"] >= 7
        types = {a["type"] for a in res["alerts"]}
        assert "dry_spell" in types
        sms = next(a for a in res["alerts"] if a["type"] == "dry_spell")["sms"]
        assert set(sms) == {"en", "hi", "te"}
        assert "PANI" in sms["en"]


def test_recommend_ranks_with_breakdown():
    with TestClient(app) as client:
        res = client.get("/api/recommend", params={"plot_id": "plot-raptadu-01"}).json()
        recs = res["recommendations"]
        assert recs
        scores = [r["score"] for r in recs]
        assert scores == sorted(scores, reverse=True)
        by_crop = {r["crop"]: r for r in recs}
        assert by_crop["paddy"]["score"] < by_crop["groundnut"]["score"]
        assert all({"water", "groundwater", "ph", "texture"} <= set(r["breakdown"]) for r in recs)


def test_unknown_plot_404s():
    with TestClient(app) as client:
        assert client.get("/api/alerts", params={"plot_id": "nope"}).status_code == 404
        assert client.get("/api/recommend", params={"plot_id": "nope"}).status_code == 404


def test_twilio_inbound_returns_twiml():
    """The webhook returns valid TwiML with the engine's reply, even for an
    unregistered number (falls back to the demo plot). No credentials needed."""
    with TestClient(app) as client:
        r = client.post(
            "/api/twilio/inbound", data={"From": "whatsapp:+919999999999", "Body": "PANI"}
        )
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/xml")
        assert "<Response><Message>" in r.text
        # unregistered number falls back to the demo plot; reply names its village
        assert "Narasaraopet" in r.text


def test_twilio_send_alert_requires_config():
    with TestClient(app) as client:
        r = client.post(
            "/api/twilio/send-alert",
            params={"plot_id": "plot-raptadu-01", "to": "+919999999999"},
        )
        assert r.status_code == 503  # not configured in test env
