from __future__ import annotations

import shap
import numpy as np
import pandas as pd


_explainer: shap.TreeExplainer | None = None
_feature_names: list[str] = []


def init_explainer(model, feature_names: list[str]) -> None:
    global _explainer, _feature_names
    _explainer = shap.TreeExplainer(model)
    _feature_names = feature_names


def explain(features_array: np.ndarray) -> dict:
    if _explainer is None:
        raise RuntimeError("Explainer not initialised — call init_explainer() at startup.")

    shap_values = _explainer.shap_values(features_array)

    # shap_values may be 2D (1 sample) or 1D — normalise to 1D
    if hasattr(shap_values, "ndim") and shap_values.ndim == 2:
        values = shap_values[0]
    else:
        values = shap_values

    return dict(zip(_feature_names, [float(v) for v in values]))


def top_factors(shap_dict: dict, n: int = 5) -> dict:
    sorted_items = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)
    positive = [(k, v) for k, v in sorted_items if v > 0][:n]
    negative = [(k, v) for k, v in sorted_items if v < 0][:n]
    return {
        "positive": [{"feature": k, "value": v} for k, v in positive],
        "negative": [{"feature": k, "value": v} for k, v in negative],
    }


def get_counterfactual(features: dict) -> dict:
    # Placeholder — DiCE-ML implementation deferred to stretch goal phase
    return {"status": "not_implemented", "message": "Counterfactual explanations are a stretch goal."}
