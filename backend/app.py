import csv
import io
import json
import os
import pickle
import time
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request, Response
from flask_cors import CORS

import config
import audit_logger
import explainability
import kafka_producer
from compliance import compute_fairness
from schemas import ScoreInputSchema

# ---------------------------------------------------------------------------
# Application startup
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
CORS(app, resources={r"/api/*": {"origins": "*"}})

_startup_time = time.time()
_model = None
_scaler = None
_feature_names = []
_metadata = {}


def _load_models():
    global _model, _scaler, _feature_names, _metadata

    model_path = os.path.join(os.path.dirname(__file__), config.MODEL_PATH)
    scaler_path = os.path.join(os.path.dirname(__file__), config.SCALER_PATH)
    names_path = model_path.replace("credit_model.pkl", "feature_names.pkl")
    meta_path = model_path.replace("credit_model.pkl", "model_metadata.json")

    for p in [model_path, scaler_path, names_path]:
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            raise RuntimeError(
                f"Model artefact missing or empty: {p}\n"
                "Run: python train_model.py"
            )

    with open(model_path, "rb") as f:
        _model = pickle.load(f)
    with open(scaler_path, "rb") as f:
        _scaler = pickle.load(f)
    with open(names_path, "rb") as f:
        _feature_names = pickle.load(f)
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            _metadata = json.load(f)

    explainability.init_explainer(_model, _feature_names)
    print(f"Model loaded: {len(_feature_names)} features  version={config.MODEL_VERSION}")


_load_models()

# ---------------------------------------------------------------------------
# Request input → model feature vector
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd


def _build_feature_vector(data: dict) -> np.ndarray:
    """
    Convert API input dict to the same one-hot encoded feature vector used in training.
    Unrecognised categories become all-zero OHE columns (graceful degradation).
    """
    # Build a single-row DataFrame matching the raw feature columns (minus protected attrs)
    raw = {
        "duration":               data["duration"],
        "credit_amount":          data["credit_amount"],
        "installment_commitment": data.get("installment_commitment", 2),
        "residence_since":        1,        # not collected at API — use neutral default
        "age":                    data["age"],
        "existing_credits":       data.get("existing_credits", 1),
        "num_dependents":         1,        # not collected at API — use neutral default
        "checking_status":        "no checking",
        "credit_history":         "existing paid",
        "purpose":                data["purpose"],
        "savings_status":         "no known savings",
        "employment":             data["employment"],
        "other_parties":          "none",
        "property_magnitude":     "real estate",
        "other_payment_plans":    "none",
        "housing":                "own",
        "job":                    "skilled",
        "own_telephone":          "none",
        "foreign_worker":         "yes",
    }
    df = pd.DataFrame([raw])
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = [c for c in df.columns if c not in num_cols]
    df_ohe = pd.get_dummies(df, columns=cat_cols, drop_first=False, dtype=float)
    # Align to training feature space (fills missing OHE columns with 0)
    df_aligned = df_ohe.reindex(columns=_feature_names, fill_value=0)
    return _scaler.transform(df_aligned)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": str(e)}), 400


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/api/score", methods=["POST"])
def score():
    t0 = time.perf_counter()
    schema = ScoreInputSchema()
    errors = schema.validate(request.json or {})
    if errors:
        return jsonify({"error": errors}), 400

    data = schema.load(request.json)
    application_id = str(uuid.uuid4())

    features_vec = _build_feature_vector(data)
    probability = float(_model.predict_proba(features_vec)[0, 1])
    decision = "accept" if probability >= 0.5 else "deny"

    shap_dict = explainability.explain(features_vec)
    factors = explainability.top_factors(shap_dict)

    recent = audit_logger.get_recent_decisions(config.FAIRNESS_WINDOW_SIZE)
    # Append current decision to window for fairness computation
    window = recent + [{
        "decision": decision,
        "probability": probability,
        "input_features": {**data, "sex": data["sex"]},
    }]
    fairness = compute_fairness(window)

    input_for_log = {k: v for k, v in data.items() if k != "sex"}  # no PII in log
    input_for_log["sex"] = data["sex"]  # sex retained as fairness attribute only

    audit_logger.log_decision(
        application_id=application_id,
        input_features=input_for_log,
        decision=decision,
        probability=probability,
        shap_values=shap_dict,
        fairness_flags=fairness,
        model_version=config.MODEL_VERSION,
    )

    kafka_producer.publish_decision({
        "application_id": application_id,
        "decision": decision,
        "probability": probability,
        "model_version": config.MODEL_VERSION,
    })

    latency_ms = (time.perf_counter() - t0) * 1000
    return jsonify({
        "application_id": application_id,
        "decision": decision,
        "probability": round(probability, 4),
        "shap_values": shap_dict,
        "top_factors": factors,
        "fairness_flags": fairness,
        "model_version": config.MODEL_VERSION,
        "latency_ms": round(latency_ms, 2),
    })


@app.route("/api/audit", methods=["GET"])
def list_audit():
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    decision_filter = request.args.get("decision")
    date_from_str = request.args.get("date_from")
    date_to_str = request.args.get("date_to")

    date_from = datetime.fromisoformat(date_from_str) if date_from_str else None
    date_to = datetime.fromisoformat(date_to_str) if date_to_str else None

    result = audit_logger.list_decisions(
        page=page,
        page_size=page_size,
        decision_filter=decision_filter,
        date_from=date_from,
        date_to=date_to,
    )
    return jsonify(result)


@app.route("/api/audit/export", methods=["GET"])
def export_audit():
    fmt = request.args.get("format", "json")
    records = audit_logger.export_decisions(fmt=fmt)

    if fmt == "csv":
        if not records:
            return Response("", mimetype="text/csv")
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=records[0].keys())
        writer.writeheader()
        for r in records:
            flat = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in r.items()}
            writer.writerow(flat)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_export.csv"},
        )
    return jsonify(records)


@app.route("/api/audit/<application_id>", methods=["GET"])
def get_audit(application_id):
    record = audit_logger.get_decision(application_id)
    if record is None:
        return jsonify({"error": f"No record found for application_id={application_id}"}), 404
    return jsonify(record)


@app.route("/api/fairness", methods=["GET"])
def fairness():
    recent = audit_logger.get_recent_decisions(config.FAIRNESS_WINDOW_SIZE)
    metrics = compute_fairness(recent)
    return jsonify(metrics or {"message": "Insufficient data — need at least 10 decisions with both sex=0 and sex=1."})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "model_version": config.MODEL_VERSION,
        "model_name": _metadata.get("model_name", "unknown"),
        "cv_auc": _metadata.get("cv_auc"),
        "n_features": len(_feature_names),
        "kafka_enabled": config.KAFKA_ENABLED,
        "database_url": config.DATABASE_URL.split("://")[0],  # type only, no credentials
        "uptime_seconds": round(time.time() - _startup_time, 1),
    })


# ---------------------------------------------------------------------------
# Counterfactual (stub)
# ---------------------------------------------------------------------------
@app.route("/api/counterfactual", methods=["POST"])
def counterfactual():
    return jsonify(explainability.get_counterfactual(request.json or {}))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.FLASK_PORT, debug=(os.getenv("FLASK_ENV") == "development"))
