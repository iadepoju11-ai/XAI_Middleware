"""
Train XGBoost credit scoring model on German Credit dataset.

Usage:
  cd backend
  python train_model.py

Outputs:
  models/credit_model.pkl   — trained XGBClassifier
  models/scaler.pkl         — fitted StandardScaler
  models/feature_names.pkl  — ordered feature name list (required by explainability.py)
"""
import os
import pickle
import ssl
import sys

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
from xgboost import XGBClassifier

ssl._create_default_https_context = ssl._create_unverified_context

CLEAN_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "german_credit", "german_credit_clean.csv")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
AUC_FLOOR = 0.80

# Features excluded from model (protected attributes used only for fairness monitoring)
PROTECTED = {"sex", "personal_status"}
TARGET = "target"


def load_and_encode(path: str) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    df = pd.read_csv(path)

    # Drop protected attributes — used only for fairness, not model features
    drop_cols = list(PROTECTED) + [TARGET]
    df_model = df.drop(columns=[c for c in drop_cols if c in df.columns])

    # One-hot encode all non-numeric columns (pandas 3.x uses StringDtype, not object)
    num_cols = df_model.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = [c for c in df_model.columns if c not in num_cols]
    df_encoded = pd.get_dummies(df_model, columns=cat_cols, drop_first=False, dtype=float)

    feature_names = list(df_encoded.columns)
    X = df_encoded
    y = df[TARGET]
    return X, y, feature_names


def train():
    print("Loading data...")
    X, y, feature_names = load_and_encode(CLEAN_CSV)
    print(f"Features ({len(feature_names)}): {feature_names[:5]} ... (one-hot encoded)")
    print(f"Target distribution: {y.value_counts().to_dict()}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    print(f"Train: {len(X_train)}  Test: {len(X_test)}")

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    print("\nTraining XGBoost (grid search, 5-fold CV)...")
    xgb_grid = {
        "n_estimators": [300, 500],
        "max_depth": [3, 4],
        "learning_rate": [0.03, 0.05, 0.1],
        "subsample": [0.7, 0.9],
        "colsample_bytree": [0.7, 0.9],
        "min_child_weight": [1, 3],
    }
    xgb_base = XGBClassifier(eval_metric="auc", random_state=42, n_jobs=-1)
    xgb_search = GridSearchCV(xgb_base, xgb_grid, cv=5, scoring="roc_auc", n_jobs=-1, verbose=1)
    xgb_search.fit(X_train_s, y_train)
    xgb_auc_cv = xgb_search.best_score_
    print(f"XGBoost CV AUC: {xgb_auc_cv:.4f}  params: {xgb_search.best_params_}")

    # HistGradientBoosting — often stronger on small datasets with many categoricals
    from sklearn.ensemble import HistGradientBoostingClassifier
    hgb_grid = {
        "max_iter": [300, 500],
        "max_depth": [3, 4, None],
        "learning_rate": [0.03, 0.05, 0.1],
        "min_samples_leaf": [10, 20],
        "l2_regularization": [0, 0.1, 1.0],
    }
    hgb_base = HistGradientBoostingClassifier(random_state=42)
    hgb_search = GridSearchCV(hgb_base, hgb_grid, cv=5, scoring="roc_auc", n_jobs=-1, verbose=1)
    hgb_search.fit(X_train_s, y_train)
    hgb_auc_cv = hgb_search.best_score_
    print(f"HGB CV AUC:     {hgb_auc_cv:.4f}  params: {hgb_search.best_params_}")

    # Pick the better of the two
    if hgb_auc_cv >= xgb_auc_cv:
        model = hgb_search.best_estimator_
        model_name = "HistGradientBoosting"
    else:
        model = xgb_search.best_estimator_
        model_name = "XGBoost"
    print(f"\nSelected: {model_name}")

    # PRIMARY: GridSearchCV best_score_ is already the 5-fold CV AUC on the training set
    cv_auc = xgb_search.best_score_ if model_name == "XGBoost" else hgb_search.best_score_
    print(f"\n5-fold CV AUC (grid search):   {cv_auc:.4f}  [PRIMARY — used for pass/fail gate]")

    # SECONDARY: single held-out test set (informational; high variance at n=200)
    y_prob = model.predict_proba(X_test_s)[:, 1]
    holdout_auc = roc_auc_score(y_test, y_prob)
    print(f"Hold-out AUC (n=200 test set): {holdout_auc:.4f}  [informational — high variance at n=200]")
    print(classification_report(y_test, model.predict(X_test_s), target_names=["bad", "good"], zero_division=0))
    print("Confusion matrix:")
    print(confusion_matrix(y_test, model.predict(X_test_s)))

    auc = cv_auc
    if auc < AUC_FLOOR:
        print(f"\nWARNING: CV AUC {auc:.4f} is below target {AUC_FLOOR}.")
        print("Consider tuning hyperparameters or using a different model.")

    import json
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(os.path.join(MODEL_DIR, "credit_model.pkl"), "wb") as f:
        pickle.dump(model, f)
    with open(os.path.join(MODEL_DIR, "scaler.pkl"), "wb") as f:
        pickle.dump(scaler, f)
    with open(os.path.join(MODEL_DIR, "feature_names.pkl"), "wb") as f:
        pickle.dump(feature_names, f)

    # Save evaluation metadata for evaluate_model.py and /api/health
    metadata = {
        "model_name": model_name,
        "model_version": os.getenv("MODEL_VERSION", "1.0.0"),
        "cv_auc": round(float(cv_auc), 4),
        "holdout_auc": round(float(holdout_auc), 4),
        "n_features": len(feature_names),
        "best_params": xgb_search.best_params_ if model_name == "XGBoost" else hgb_search.best_params_,
    }
    with open(os.path.join(MODEL_DIR, "model_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nSaved model, scaler, feature_names, model_metadata.json to {MODEL_DIR}/")
    return auc


if __name__ == "__main__":
    auc = train()
    if auc < AUC_FLOOR:
        sys.exit(1)   # non-zero exit signals CI failure
