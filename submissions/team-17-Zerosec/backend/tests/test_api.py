import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers import make_campaign_df


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "app": "PS-04 Campaign Anomaly Alerting", "version": "0.1.0"}


def test_cors_allows_vite_origin(client):
    r = client.options("/api/health", headers={"Origin": "http://localhost:5173",
                                               "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_rejects_unknown_origin(client):
    r = client.options("/api/health", headers={"Origin": "http://evil.example",
                                               "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in r.headers


def test_cors_origins_from_env(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test")
    from app.config import get_settings
    assert get_settings().cors_origins == ["http://a.test", "http://b.test"]


# ---- analysis endpoints ------------------------------------------------------
DEMO = Path("data/demo_campaigns.csv").read_bytes()


def strict_json(r):
    def reject(c):
        raise ValueError(f"non-JSON constant {c}")
    return json.loads(r.text, parse_constant=reject)


def test_analyze_demo_upload(client):
    r = client.post("/api/analyze", files={"file": ("demo.csv", DEMO, "text/csv")})
    assert r.status_code == 200
    body = strict_json(r)
    s = body["summary"]
    assert s["campaigns_analyzed"] == 20 and s["records_analyzed"] == 3600
    assert s["notifications_sent"] < s["anomalies_detected"]
    assert body["evaluation"]["available"] is True and body["evaluation"]["naive_baseline"]["alerts_fired"] > 0
    assert all(a["explanation"] and a["diagnostic_steps"] for a in body["alerts"])
    assert len(body["timeline"]) == 20


def test_analyze_demo_endpoint_matches_upload(client):
    a = client.post("/api/analyze/demo").json()
    b = client.post("/api/analyze", files={"file": ("d.csv", DEMO)}).json()
    assert a["summary"] == b["summary"]


def test_rejects_non_csv(client):
    assert client.post("/api/analyze", files={"file": ("x.txt", b"a")}).status_code == 400


def test_rejects_empty(client):
    assert client.post("/api/analyze", files={"file": ("x.csv", b"")}).status_code == 400


def test_rejects_too_large(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "0.0001")
    c = TestClient(create_app())
    assert c.post("/api/analyze", files={"file": ("x.csv", b"a" * 1000)}).status_code == 413


def test_no_valid_records_is_422(client):
    r = client.post("/api/analyze", files={"file": ("x.csv", b"campaign_id,date,spend\nA,bad,1\n")})
    assert r.status_code == 422 and "no valid records" in r.json()["detail"]


def test_bad_params_422(client):
    assert client.post("/api/analyze/demo?z_threshold=0").status_code == 422
    assert client.post("/api/analyze/demo?window_days=10&min_history=20").status_code == 422


def test_no_labels_means_null_metrics(client):
    csv = make_campaign_df(days=40).drop(columns=["row_present"]).to_csv(index=False).encode()
    ev = client.post("/api/analyze", files={"file": ("x.csv", csv)}).json()["evaluation"]
    assert ev["available"] is False and ev["precision"] is None


def test_demo_data_is_labeled_synthetic(client):
    body = client.get("/api/demo-data?limit=5").json()
    assert body["synthetic"] is True and "SYNTHETIC" in body["notice"] and len(body["records"]) == 5


OFFICIAL = sorted(Path("data/official").glob("*.csv"))


@pytest.mark.skipif(not OFFICIAL, reason="official dataset not provided yet")
def test_official_dataset_sample(client):
    r = client.post("/api/analyze", files={"file": (OFFICIAL[0].name, OFFICIAL[0].read_bytes())})
    assert r.status_code == 200 and strict_json(r)["summary"]["records_analyzed"] > 0
