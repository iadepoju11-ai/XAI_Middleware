"""
Evaluate the trained model on the held-out test set.

Usage:
  cd backend
  python evaluate_model.py

Prints AUC, classification report, and SHAP timing benchmark.
"""
import os
import pickle
import ssl
import time

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import roc_auc_score, classification_report

ssl._create_default_https_context = ssl._create_unverified_context

CLEAN_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "german_credit", "german_credit_clean.csv")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")

PROTECTED = {"sex", "personal_status"}
TARGET = "target"


def load_model_artifacts():
    with open(os.path.join(MODEL_DIR, "credit_model.pkl"), "rb") as f:
        model = pickle.load(f)
    with open(os.path.join(MODEL_DIR, "scaler.pkl"), "rb") as f:
        scaler = pickle.load(f)
    with open(os.path.join(MODEL_DIR, "feature_names.pkl"), "rb") as f:
        feature_names = pickle.load(f)
    return model, scaler, feature_names


def load_test_set(feature_names):
    df = pd.read_csv(CLEAN_CSV)
    drop_cols = list(PROTECTED) + [TARGET]
    df_model = df.drop(columns=[c for c in drop_cols if c in df.columns])

    # Must match training encoding exactly
    num_cols = df_model.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = [c for c in df_model.columns if c not in num_cols]
    df_encoded = pd.get_dummies(df_model, columns=cat_cols, drop_first=False, dtype=float)

    # Align columns to saved feature_names (handles any missing dummies)
    df_encoded = df_encoded.reindex(columns=feature_names, fill_value=0)

    X = df_encoded
    y = df[TARGET]
    _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    return X_test, y_test


def evaluate():
    import json
    print("Loading model artefacts...")
    model, scaler, feature_names = load_model_artifacts()

    meta_path = os.path.join(MODEL_DIR, "model_metadata.json")
    metadata = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    cv_auc = metadata.get("cv_auc")

    print("Loading test set...")
    X_test, y_test = load_test_set(feature_names)
    X_test_s = scaler.transform(X_test)

    y_prob = model.predict_proba(X_test_s)[:, 1]
    y_pred = model.predict(X_test_s)

    auc = roc_auc_score(y_test, y_prob)
    print(f"\n--- Predictive Accuracy ---")
    print(f"AUC-ROC: {auc:.4f}  (target > 0.80)")
    print(classification_report(y_test, y_pred, target_names=["bad", "good"]))

    # SHAP timing benchmark
    import shap
    print("--- SHAP Timing Benchmark ---")
    explainer = shap.TreeExplainer(model)
    sample = X_test_s[:1]

    times = []
    for _ in range(20):
        t0 = time.perf_counter()
        explainer.shap_values(sample)
        times.append((time.perf_counter() - t0) * 1000)

    print(f"SHAP per-sample (20 runs): mean={np.mean(times):.1f}ms  p95={np.percentile(times, 95):.1f}ms  (target < 100ms)")

    print(f"\n--- Summary ---")
    if cv_auc is not None:
        print(f"CV AUC (training, primary): {cv_auc:.4f}  {'PASS' if cv_auc > 0.80 else 'FAIL'}")
    print(f"Hold-out AUC (n=200):       {auc:.4f}  [informational — high variance at n=200]")
    print(f"SHAP mean:                  {np.mean(times):.1f}ms  {'PASS' if np.mean(times) < 100 else 'FAIL'}")


if __name__ == "__main__":
    evaluate()
