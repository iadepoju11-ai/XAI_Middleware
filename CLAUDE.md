# CLAUDE.md — XAI Compliance Middleware Dashboard

## Session Start Instructions

**At the beginning of every session or request, read [CHECKLIST.md](CHECKLIST.md) in full before doing any work.** Use the current checkbox state to understand what has been completed, what is in progress, and what comes next. Do not rely on memory or prior context — the checklist is the authoritative record of project state.

---

## Project Overview

Master's dissertation artefact implementing a **Design Science Research (DSR)** prototype. The system wraps a legacy banking core (simulated via PostgreSQL) with an explainable AI credit-scoring pipeline that satisfies EU AI Act (2024/1689) Annex III and GDPR Article 22 obligations. Every credit decision is scored by XGBoost, explained by SHAP, evaluated for fairness by Fairlearn, and persisted to an immutable audit log — then surfaced through a React dashboard.

The project name is currently `tobenamed` — rename when confirmed.

---

## Architecture

```
legacy_simulator/   PostgreSQL "core banking" seeded from German Credit dataset
       │
       ▼
backend/            Python monolith (Flask REST API)
  ├── config.py         DB + Kafka connection strings, env overrides
  ├── app.py            Flask app, all /api/* routes
  ├── audit_logger.py   Append-only SQLAlchemy audit table (no UPDATE/DELETE)
  ├── compliance.py     Fairlearn demographic parity + equalised odds
  ├── explainability.py SHAP TreeExplainer wrapper, counterfactual stub
  ├── kafka_producer.py Publishes Avro decision events to `credit-decisions` topic
  ├── kafka_consumer.py Optional downstream consumer (demo only)
  └── models/           Serialised XGBoost model + StandardScaler (.pkl)

frontend/           React 18 SPA (Vite or CRA — confirm on scaffold)
  └── src/
      ├── App.js          Router, nav tabs
      ├── Dashboard.js    Credit scoring form + SHAP waterfall
      ├── AuditPanel.js   Audit search + decision timeline
      └── api.js          Axios base client pointed at Flask

docker-compose.yml  PostgreSQL 15 + Confluent Kafka 3.5 + Zookeeper
```

**Data flow:** `seed_db.py` → PostgreSQL → Flask pulls customer record → XGBoost scores → SHAP explains → Fairlearn checks fairness → audit_logger writes → React polls Flask → dashboard renders.

---

## Tech Stack

| Layer | Library | Why |
|---|---|---|
| ML model | XGBoost 1.7+ | AUC target >0.80 on German Credit; industry standard for tabular credit |
| Explainability | SHAP (TreeExplainer) | Exact Shapley values for tree models; <100ms overhead target |
| Fairness | Fairlearn 0.8+ | demographic_parity_difference, equalized_odds_difference |
| API | Flask 2.3+ | Thin; fits single-developer scope |
| ORM | SQLAlchemy 2.0+ | Audit table abstraction; supports both SQLite (dev) and PostgreSQL (prod) |
| Message queue | Apache Kafka 3.4+ (Confluent CP 7.5) | Event-driven architecture for RQ2; optional for MVP |
| Frontend | React 18 + Recharts/D3 | SHAP waterfall + fairness trend charts |
| DB (audit) | SQLite (dev) / PostgreSQL 15 (prod) | Switch via `DATABASE_URL` env var |
| Load testing | Locust | NFR1: <500ms p95 under 1000 concurrent |
| Unit testing | Pytest | Backend; React Testing Library for frontend |

---

## Development Setup

### Prerequisites
- Python 3.10+
- Node 18+
- Docker Desktop (for Kafka + PostgreSQL)
- Git

### Backend
```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Dev mode (SQLite, no Kafka)
DATABASE_URL=sqlite:///audit.db KAFKA_ENABLED=false python app.py
```

### Frontend
```bash
cd frontend
npm install
npm start     # proxies /api/* to localhost:5000
```

### Full stack (Docker)
```bash
docker compose up -d          # starts postgres + kafka + zookeeper
cd legacy_simulator && python seed_db.py   # seed legacy DB once
cd backend && python app.py
cd frontend && npm start
```

### Kafka topics (if enabled)
```bash
# Create topic after docker compose up
docker exec -it <kafka-container> kafka-topics --create \
  --topic credit-decisions --bootstrap-server localhost:9092 --partitions 1
```

---

## Key Commands

| Task | Command |
|---|---|
| Run all backend tests | `cd backend && pytest -v` |
| Train / retrain model | `cd backend && python train_model.py` (create this) |
| Seed legacy DB | `cd legacy_simulator && python seed_db.py` |
| Load test | `cd eval && locust -f locustfile.py --headless -u 1000 -r 50 -t 10m` |
| Check AUC | `cd backend && python evaluate_model.py` (create this) |
| Export audit CSV | `GET /api/audit/export?format=csv` |

---

## API Surface (Flask)

All routes prefixed `/api/`.

| Method | Path | Description |
|---|---|---|
| POST | `/score` | Submit application, returns decision + SHAP + fairness |
| GET | `/audit` | List decisions (paginated, filterable by date/decision) |
| GET | `/audit/<id>` | Full decision lineage for one application |
| GET | `/audit/export` | Bulk export CSV or JSON |
| GET | `/fairness` | Current demographic parity + equalised odds |
| GET | `/health` | System health, model version, uptime |

Request/response schemas are defined in `backend/schemas.py` (create with Marshmallow or Pydantic).

---

## Audit Log Immutability

The `AuditRecord` table is **append-only**. Enforce this at two levels:

1. SQLAlchemy `before_update` / `before_delete` event listeners raise `RuntimeError`.
2. PostgreSQL role used by the app has `REVOKE UPDATE, DELETE ON audit_records FROM app_user;`.

For SQLite dev mode, only the ORM-level guard applies — document this limitation.

---

## SHAP Integration Notes

- Use `shap.TreeExplainer(model)` — exact values, ~5–20ms per sample on German Credit features.
- Cache the `Explainer` object at app startup (module-level singleton); do not re-instantiate per request.
- Return top 5 positive and top 5 negative contributions sorted by `|shap_value|`.
- `shap_values` stored in audit log as JSON column: `{"credit_amount": 0.32, "duration": -0.15, ...}`.
- Counterfactual stub: placeholder endpoint using DiCE-ML — mark clearly as `NOT_IMPLEMENTED` until Phase 3.

---

## Fairness Metrics

Computed per-decision using a **rolling window** (last 500 decisions) to avoid stale batch results:

- `demographic_parity_difference` — target: difference ≤ 0.20 (ratio ≥ 0.80)
- `equalized_odds_difference` — informational, no hard threshold

Protected attribute: `sex` (binary 0/1 from German Credit encoding). Note in dissertation that this is a proxy; real deployments require verified demographic data.

Alert threshold: flag in dashboard when `demographic_parity_difference > 0.20`.

---

## Dataset Notes

| Dataset | Location | Use |
|---|---|---|
| German Credit (UCI) | Auto-downloaded via `sklearn.datasets.fetch_openml('german')` | Model training + fairness eval |
| Home Credit | Manual download from Kaggle → `data/home_credit/` | Scale testing only |
| LendingClub | Manual download from Kaggle → `data/lending_club/` | Load test seed data |

Sensitive fields: `personal_status_sex`, `age` — used as protected attributes for fairness only; excluded from model features in production-intent design (note in thesis).

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///audit.db` | SQLAlchemy connection string |
| `KAFKA_ENABLED` | `false` | Set `true` to enable producer |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker address |
| `MODEL_PATH` | `models/credit_model.pkl` | Path to serialised XGBoost model |
| `SCALER_PATH` | `models/scaler.pkl` | Path to serialised StandardScaler |
| `MODEL_VERSION` | `1.0.0` | Stamped into every audit record |
| `FLASK_ENV` | `development` | Set `production` for gunicorn |
| `SECRET_KEY` | `dev-secret` | Flask session key — override in prod |

---

## Non-Negotiable Constraints

- **Audit log**: no `UPDATE` or `DELETE` ever — this is the core regulatory claim.
- **No PII**: German Credit `personal_status_sex` is used only as a fairness attribute, never logged as PII.
- **Latency budget**: SHAP must complete in <100ms; total API response <500ms at p95.
- **Model version**: every `AuditRecord` row must carry `model_version` — required for reproducibility under EU AI Act Article 13.
- **AUC floor**: model must achieve >0.80 on held-out 20% of German Credit; if not, try Random Forest or tune hyperparameters before shipping.

---

## Known Gaps (Start-of-Project)

- All backend Python files are empty stubs — implement Phase 1 → 6 in order.
- `frontend/package.json` is empty — scaffold with `create-react-app` or Vite.
- `backend/requirements.txt` is empty — populate before any `pip install`.
- `models/` `.pkl` files are 0-byte placeholders — generated by `train_model.py`.
- Kafka is optional for MVP; `KAFKA_ENABLED=false` must be a valid path with no errors.
- Docker-compose Kafka `KAFKA_ADVERTISED_LISTENERS` is set to `localhost:9092` — works for host-to-container but not container-to-container; fix if services need to talk internally.

---

## Evaluation Targets (Hard Criteria)

| Metric | Target | Measured by |
|---|---|---|
| AUC-ROC | > 0.80 | `evaluate_model.py` on 20% hold-out |
| p95 latency | < 500ms | Locust 1000-user test |
| SHAP overhead | < 100ms | A/B timing in `app.py` |
| Audit write latency | < 50ms | SQLAlchemy timing hook |
| Audit query (10k rows) | < 2s | Indexed `application_id` lookup |
| Demographic parity ratio | > 0.80 | `compliance.py` rolling window |
| SUS score | ≥ 70 | 5-participant usability session |

---

## Dissertation Phase Map

| Phase | Days | Files to Implement |
|---|---|---|
| 0 — Setup | 1-3 | `requirements.txt`, `config.py`, venv, git |
| 1 — Data layer | 4-7 | `audit_logger.py`, `seed_db.py` (extend), DB schema |
| 2 — AI Engine | 8-12 | `train_model.py` (new), `models/*.pkl` |
| 3 — Explainability | 13-16 | `explainability.py` |
| 4 — Compliance | 17-20 | `compliance.py` |
| 5 — API | 21-25 | `app.py`, `kafka_producer.py` |
| 6 — Dashboard | 26-32 | `frontend/src/*` |
| 7 — Integration | 33-36 | End-to-end tests |
| 8 — Evaluation | 37-42 | Locust, usability protocol |
| 9 — Write-up | 43-56 | `dissertation/` |
