"""
Explainability tests — SHAP determinism, perturbation, latency, top_factors.
"""
import time

import numpy as np
import pytest

import explainability


@pytest.fixture(scope="module", autouse=True)
def _init(flask_client):
    """Ensure the explainer singleton is initialised (app startup does this)."""
    # Importing flask_client triggers app._load_models() which calls init_explainer()
    pass


def _single_feature_vector():
    """Return a realistic 57-feature vector (all zeros except a few values)."""
    # The model has 57 OHE features; we just need a shape-(1,57) array
    vec = np.zeros((1, 57), dtype=np.float64)
    vec[0, 0] = 1.0   # some OHE feature = 1
    vec[0, 1] = 0.5   # a scaled numeric
    return vec


# ── Correctness ───────────────────────────────────────────────────────────────

def test_explain_returns_dict_with_feature_names():
    vec = _single_feature_vector()
    result = explainability.explain(vec)
    assert isinstance(result, dict)
    assert len(result) == 57
    assert all(isinstance(v, float) for v in result.values())


def test_shap_determinism():
    """Same input must produce identical SHAP values every call."""
    vec = _single_feature_vector()
    first = explainability.explain(vec)
    for _ in range(5):
        repeat = explainability.explain(vec)
        for key in first:
            assert first[key] == repeat[key], f"SHAP value for '{key}' is non-deterministic"


def test_perturbation_directional():
    """
    Increasing credit_amount (a numeric feature scaled to the first position after
    the OHE columns) should change at least one SHAP value.  We verify that the
    SHAP dict is not identical between a baseline and a perturbed vector.
    """
    baseline = np.zeros((1, 57), dtype=np.float64)
    perturbed = baseline.copy()
    perturbed[0, 0] += 2.0   # perturb the first feature

    shap_base = explainability.explain(baseline)
    shap_pert = explainability.explain(perturbed)

    # At least one feature's SHAP value must change
    changed = any(abs(shap_base[k] - shap_pert[k]) > 1e-9 for k in shap_base)
    assert changed, "Perturbing a feature had no effect on any SHAP value"


def test_top_factors_structure():
    vec = _single_feature_vector()
    shap_dict = explainability.explain(vec)
    factors = explainability.top_factors(shap_dict, n=5)

    assert "positive" in factors and "negative" in factors
    assert len(factors["positive"]) <= 5
    assert len(factors["negative"]) <= 5
    for item in factors["positive"]:
        assert "feature" in item and "value" in item
        assert item["value"] > 0
    for item in factors["negative"]:
        assert item["value"] < 0


def test_top_factors_sorted_by_magnitude():
    """Positive factors must be sorted descending by |value|."""
    vec = _single_feature_vector()
    shap_dict = explainability.explain(vec)
    factors = explainability.top_factors(shap_dict, n=5)

    pos_vals = [abs(f["value"]) for f in factors["positive"]]
    neg_vals = [abs(f["value"]) for f in factors["negative"]]
    assert pos_vals == sorted(pos_vals, reverse=True)
    assert neg_vals == sorted(neg_vals, reverse=True)


# ── Latency ───────────────────────────────────────────────────────────────────

def test_shap_latency_under_100ms():
    """Single SHAP explanation must complete in < 100ms (target is <100ms; model averages ~4ms)."""
    vec = _single_feature_vector()
    # warm-up
    explainability.explain(vec)

    latencies = []
    for _ in range(20):
        t0 = time.perf_counter()
        explainability.explain(vec)
        latencies.append((time.perf_counter() - t0) * 1000)

    p95 = sorted(latencies)[int(len(latencies) * 0.95)]
    assert p95 < 100, f"SHAP p95 latency {p95:.1f}ms exceeds 100ms target"


# ── Error guard ───────────────────────────────────────────────────────────────

def test_explain_raises_without_init(monkeypatch):
    monkeypatch.setattr(explainability, "_explainer", None)
    with pytest.raises(RuntimeError, match="not initialised"):
        explainability.explain(_single_feature_vector())
