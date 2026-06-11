from __future__ import annotations

import numpy as np
from fairlearn.metrics import demographic_parity_difference, equalized_odds_difference

import config


def compute_fairness(decisions: list[dict]) -> dict | None:
    """
    Compute fairness metrics over a window of decision dicts.
    Each dict must have keys: 'decision' (accept/deny), 'probability' (float),
    and the protected attribute 'sex' inside 'input_features'.
    Returns None when there are fewer than 10 decisions or only one group present.
    """
    if len(decisions) < 10:
        return None

    y_true = []       # ground-truth labels — we use model decision as proxy for evaluation
    y_pred = []
    sensitive = []

    for d in decisions:
        pred = 1 if d["decision"] == "accept" else 0
        sex = d.get("input_features", {}).get("sex")
        if sex is None:
            continue
        y_pred.append(pred)
        y_true.append(pred)   # no ground truth available; use predicted label
        sensitive.append(int(sex))

    if len(set(sensitive)) < 2:
        return None

    y_pred_arr = np.array(y_pred)
    y_true_arr = np.array(y_true)
    sensitive_arr = np.array(sensitive)

    dp_diff = float(demographic_parity_difference(y_true_arr, y_pred_arr, sensitive_features=sensitive_arr))
    eo_diff = float(equalized_odds_difference(y_true_arr, y_pred_arr, sensitive_features=sensitive_arr))

    group_rates = {}
    for g in set(sensitive):
        mask = sensitive_arr == g
        group_rates[int(g)] = float(y_pred_arr[mask].mean()) if mask.sum() > 0 else 0.0

    rates = list(group_rates.values())
    dp_ratio = min(rates) / max(rates) if max(rates) > 0 else 1.0

    return {
        "demographic_parity_difference": round(dp_diff, 4),
        "equalized_odds_difference": round(eo_diff, 4),
        "demographic_parity_ratio": round(dp_ratio, 4),
        "group_acceptance_rates": group_rates,
        "n_decisions": len(y_pred),
        "alert": dp_ratio < config.DEMOGRAPHIC_PARITY_THRESHOLD,
    }
