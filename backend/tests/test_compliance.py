"""
Compliance / fairness metric tests — demographic parity, bias injection, alert logic.
"""
import pytest

from compliance import compute_fairness


# ── Guard conditions ──────────────────────────────────────────────────────────

def test_returns_none_when_too_few_decisions():
    decisions = [{"decision": "accept", "probability": 0.8, "input_features": {"sex": i % 2}} for i in range(9)]
    assert compute_fairness(decisions) is None


def test_returns_none_when_only_one_sex_group():
    decisions = [{"decision": "accept", "probability": 0.8, "input_features": {"sex": 0}} for _ in range(20)]
    assert compute_fairness(decisions) is None


def test_returns_none_when_sex_missing():
    decisions = [{"decision": "accept", "probability": 0.8, "input_features": {}} for _ in range(20)]
    assert compute_fairness(decisions) is None


# ── Correct output fields ─────────────────────────────────────────────────────

def test_output_has_all_required_fields(balanced_decisions):
    result = compute_fairness(balanced_decisions)
    assert result is not None
    for key in ("demographic_parity_difference", "equalized_odds_difference",
                "demographic_parity_ratio", "group_acceptance_rates", "n_decisions", "alert"):
        assert key in result, f"Missing key: {key}"


def test_n_decisions_matches_input(balanced_decisions):
    result = compute_fairness(balanced_decisions)
    assert result["n_decisions"] == len(balanced_decisions)


# ── Fair scenario ─────────────────────────────────────────────────────────────

def test_balanced_scenario_no_alert(balanced_decisions):
    """Equal accept rates for both groups → ratio = 1.0 → no alert."""
    result = compute_fairness(balanced_decisions)
    assert result is not None
    assert result["demographic_parity_ratio"] == pytest.approx(1.0, abs=0.01)
    assert result["alert"] is False


def test_balanced_dp_difference_near_zero(balanced_decisions):
    result = compute_fairness(balanced_decisions)
    assert abs(result["demographic_parity_difference"]) < 0.05


# ── Biased scenario ───────────────────────────────────────────────────────────

def test_biased_scenario_triggers_alert(biased_decisions):
    """All females denied, all males accepted → parity ratio = 0.0 → alert."""
    result = compute_fairness(biased_decisions)
    assert result is not None
    assert result["demographic_parity_ratio"] == pytest.approx(0.0, abs=0.01)
    assert result["alert"] is True


def test_biased_scenario_dp_difference(biased_decisions):
    result = compute_fairness(biased_decisions)
    assert abs(result["demographic_parity_difference"]) > 0.5


def test_biased_scenario_group_rates(biased_decisions):
    result = compute_fairness(biased_decisions)
    rates = result["group_acceptance_rates"]
    assert rates[0] == pytest.approx(0.0)   # sex=0 (female): 0% acceptance
    assert rates[1] == pytest.approx(1.0)   # sex=1 (male): 100% acceptance


# ── Rolling window ────────────────────────────────────────────────────────────

def test_fairness_uses_only_provided_window():
    """compute_fairness() is a pure function — output depends only on input list."""
    d1 = [{"decision": "accept", "probability": 0.8, "input_features": {"sex": i % 2}} for i in range(20)]
    d2 = [{"decision": "deny", "probability": 0.2, "input_features": {"sex": i % 2}} for i in range(20)]
    r1 = compute_fairness(d1)
    r2 = compute_fairness(d2)
    # Both balanced but different decisions — parity ratios differ
    assert r1 is not None and r2 is not None
    # Both should have identical ratio (both perfectly balanced)
    assert r1["demographic_parity_ratio"] == pytest.approx(r2["demographic_parity_ratio"], abs=0.01)
