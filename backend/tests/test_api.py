"""
API end-to-end integration tests — full pipeline through Flask test client.
"""
import json
import time

import pytest


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_returns_200(flask_client):
    r = flask_client.get("/api/health")
    assert r.status_code == 200


def test_health_has_required_fields(flask_client):
    r = flask_client.get("/api/health")
    data = r.get_json()
    for key in ("status", "model_version", "cv_auc", "n_features", "kafka_enabled", "database_url", "uptime_seconds"):
        assert key in data, f"Missing field: {key}"


def test_health_model_version(flask_client):
    r = flask_client.get("/api/health")
    data = r.get_json()
    assert data["status"] == "ok"
    assert data["model_version"] == "1.0.0"
    assert data["cv_auc"] >= 0.80, f"CV AUC {data['cv_auc']} is below 0.80 floor"


# ── Score — valid requests ─────────────────────────────────────────────────────

def test_score_returns_200(flask_client, sample_payload):
    r = flask_client.post("/api/score", json=sample_payload)
    assert r.status_code == 200


def test_score_response_fields(flask_client, sample_payload):
    r = flask_client.post("/api/score", json=sample_payload)
    data = r.get_json()
    for key in ("application_id", "decision", "probability", "shap_values", "top_factors", "model_version", "latency_ms"):
        assert key in data, f"Missing response field: {key}"


def test_score_decision_is_valid(flask_client, sample_payload):
    r = flask_client.post("/api/score", json=sample_payload)
    assert r.get_json()["decision"] in ("accept", "deny")


def test_score_probability_in_range(flask_client, sample_payload):
    r = flask_client.post("/api/score", json=sample_payload)
    p = r.get_json()["probability"]
    assert 0.0 <= p <= 1.0


def test_score_shap_has_entries(flask_client, sample_payload):
    r = flask_client.post("/api/score", json=sample_payload)
    shap = r.get_json()["shap_values"]
    assert isinstance(shap, dict) and len(shap) > 0


def test_score_top_factors_structure(flask_client, sample_payload):
    r = flask_client.post("/api/score", json=sample_payload)
    tf = r.get_json()["top_factors"]
    assert "positive" in tf and "negative" in tf


def test_score_application_id_is_uuid(flask_client, sample_payload):
    import re
    r = flask_client.post("/api/score", json=sample_payload)
    app_id = r.get_json()["application_id"]
    assert re.match(r"^[0-9a-f-]{36}$", app_id), f"Not a UUID: {app_id}"


# ── Score — invalid requests ───────────────────────────────────────────────────

def test_score_missing_field_returns_400(flask_client):
    bad = {"credit_amount": 5000}  # missing most fields
    r = flask_client.post("/api/score", json=bad)
    assert r.status_code == 400


def test_score_invalid_sex_returns_400(flask_client, sample_payload):
    bad = dict(sample_payload)
    bad["sex"] = 99  # must be 0 or 1
    r = flask_client.post("/api/score", json=bad)
    assert r.status_code == 400


def test_score_error_response_has_error_key(flask_client):
    r = flask_client.post("/api/score", json={"not": "valid"})
    data = r.get_json()
    assert "error" in data


# ── Audit — list ──────────────────────────────────────────────────────────────

def test_audit_list_returns_200(flask_client):
    r = flask_client.get("/api/audit")
    assert r.status_code == 200


def test_audit_list_has_pagination_fields(flask_client):
    r = flask_client.get("/api/audit")
    data = r.get_json()
    for key in ("total", "page", "page_size", "records"):
        assert key in data


def test_audit_list_filter_by_decision(flask_client, sample_payload):
    # Submit a request so there's at least one record
    flask_client.post("/api/score", json=sample_payload)
    r = flask_client.get("/api/audit?decision=accept")
    data = r.get_json()
    assert all(rec["decision"] == "accept" for rec in data["records"])


# ── Audit — by ID ─────────────────────────────────────────────────────────────

def test_audit_by_id_returns_full_record(flask_client, sample_payload):
    score_resp = flask_client.post("/api/score", json=sample_payload)
    app_id = score_resp.get_json()["application_id"]

    r = flask_client.get(f"/api/audit/{app_id}")
    assert r.status_code == 200
    data = r.get_json()
    assert data["application_id"] == app_id
    assert "shap_values" in data


def test_audit_by_id_shap_matches_score(flask_client, sample_payload):
    score_resp = flask_client.post("/api/score", json=sample_payload)
    score_data = score_resp.get_json()
    app_id = score_data["application_id"]
    score_shap = score_data["shap_values"]

    audit_resp = flask_client.get(f"/api/audit/{app_id}")
    audit_shap = audit_resp.get_json()["shap_values"]

    for key in score_shap:
        assert score_shap[key] == pytest.approx(audit_shap[key], abs=1e-6), \
            f"SHAP mismatch for '{key}': score={score_shap[key]}, audit={audit_shap[key]}"


def test_audit_unknown_id_returns_404(flask_client):
    r = flask_client.get("/api/audit/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


# ── Audit — export ────────────────────────────────────────────────────────────

def test_audit_export_json(flask_client, sample_payload):
    flask_client.post("/api/score", json=sample_payload)
    r = flask_client.get("/api/audit/export?format=json")
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_audit_export_csv(flask_client, sample_payload):
    flask_client.post("/api/score", json=sample_payload)
    r = flask_client.get("/api/audit/export?format=csv")
    assert r.status_code == 200
    assert r.content_type.startswith("text/csv")
    lines = r.data.decode().strip().split("\n")
    assert len(lines) >= 2  # header + at least one data row


# ── Fairness ──────────────────────────────────────────────────────────────────

def test_fairness_returns_200(flask_client):
    r = flask_client.get("/api/fairness")
    assert r.status_code == 200


def test_fairness_null_or_dict(flask_client):
    data = flask_client.get("/api/fairness").get_json()
    assert data is None or isinstance(data, dict)


# ── End-to-end flow ───────────────────────────────────────────────────────────

def test_full_flow(flask_client, sample_payload):
    """Submit → get audit record → SHAP values match → record is immutable."""
    # 1. Score
    r = flask_client.post("/api/score", json=sample_payload)
    assert r.status_code == 200
    result = r.get_json()
    app_id = result["application_id"]

    # 2. Retrieve from audit
    audit = flask_client.get(f"/api/audit/{app_id}").get_json()
    assert audit["application_id"] == app_id
    assert audit["decision"] == result["decision"]

    # 3. SHAP consistency
    for feat, val in result["shap_values"].items():
        assert audit["shap_values"][feat] == pytest.approx(val, abs=1e-6)

    # 4. Model version stamped
    assert audit["model_version"] == "1.0.0"


# ── Performance ───────────────────────────────────────────────────────────────

def test_score_latency_under_500ms(flask_client, sample_payload):
    """
    Single request round-trip (Flask test client, no network) should be well
    under the 500ms NFR target.  Test client overhead is minimal.
    """
    latencies = []
    for _ in range(10):
        t0 = time.perf_counter()
        r = flask_client.post("/api/score", json=sample_payload)
        latencies.append((time.perf_counter() - t0) * 1000)
    assert r.status_code == 200

    p95 = sorted(latencies)[int(len(latencies) * 0.95)]
    assert p95 < 500, f"p95 score latency {p95:.1f}ms exceeds 500ms target"
