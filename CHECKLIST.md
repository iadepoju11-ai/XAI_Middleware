# Project Checklist — XAI Compliance Middleware Dashboard

Tracks implementation progress against PRD v1.0. Check off each item as it is **done and tested**, not just coded.

---

## Phase 0 — Setup (Days 1–3)

### Environment
- [ ] Python 3.10+ confirmed (`python --version`)
- [ ] Node 18+ confirmed (`node --version`)
- [ ] Docker Desktop running and `docker compose up -d` succeeds
- [ ] Git repository initialised with `.gitignore` (Python + Node + `.env` + `*.pkl`)
- [ ] `.env.example` created with all variables from CLAUDE.md documented

### Backend Bootstrap
- [ ] `backend/requirements.txt` populated (Flask, XGBoost, SHAP, Fairlearn, SQLAlchemy, kafka-python, scikit-learn, pandas, numpy, marshmallow, pytest)
- [ ] `python -m venv .venv && pip install -r requirements.txt` completes without errors
- [ ] `backend/config.py` reads all env vars with sensible defaults
- [ ] `KAFKA_ENABLED=false` path works end-to-end without import errors

### Frontend Bootstrap
- [ ] `frontend/` scaffolded (`create-react-app` or Vite — confirm approach)
- [ ] `npm install` completes without errors
- [ ] `npm start` serves app on `localhost:3000`
- [ ] Proxy `/api/*` → `localhost:5000` configured in `package.json` or `vite.config.js`

---

## Phase 1 — Data Layer (Days 4–7)

### Legacy Simulator
- [ ] `legacy_simulator/seed_db.py` verified: creates `customers` table and inserts 1000 rows without error
- [ ] Column mapping confirmed: `personal_status_sex` → `sex`, all other fields correct
- [ ] Re-runnable: drops and recreates table on second run (or uses `ON CONFLICT DO NOTHING`)

### Audit Logger (`backend/audit_logger.py`)
- [ ] `AuditRecord` SQLAlchemy model defined with all required columns:
  - `id` (UUID primary key)
  - `application_id` (indexed)
  - `timestamp` (auto-set, indexed)
  - `input_features` (JSON)
  - `decision` (accept/deny)
  - `probability` (float)
  - `shap_values` (JSON)
  - `fairness_flags` (JSON)
  - `model_version` (string)
- [ ] Append-only enforced: `before_update` and `before_delete` SQLAlchemy events raise `RuntimeError`
- [ ] `log_decision()` function writes record and returns the persisted `application_id`
- [ ] `get_decision(application_id)` retrieves full record in <2s on 10,000 row table
- [ ] `list_decisions(page, filters)` returns paginated results
- [ ] `export_decisions(format)` returns CSV or JSON
- [ ] Write latency <50ms verified with timing assertion in test
- [ ] Tables survive app restart (persistent storage, not in-memory)

### Database
- [ ] `alembic` or raw DDL migration creates tables on first run
- [ ] SQLite dev path works (`DATABASE_URL=sqlite:///audit.db`)
- [ ] PostgreSQL prod path works (via docker-compose postgres service)
- [ ] `application_id` column has index for fast lookups

---

## Phase 2 — AI Engine (Days 8–12)

### Model Training (`backend/train_model.py` — create this file)
- [ ] German Credit dataset loaded via `sklearn.datasets.fetch_openml('german')`
- [ ] 80/20 stratified train/test split
- [ ] Features engineered: categorical encoding, scaling with `StandardScaler`
- [ ] `sex` / protected attributes **excluded** from model feature set
- [ ] XGBoost `XGBClassifier` trained with hyperparameter tuning (grid search or default + tuned)
- [ ] AUC-ROC on test set **> 0.80** — print and assert
- [ ] Confusion matrix, classification report printed
- [ ] Model saved to `backend/models/credit_model.pkl`
- [ ] Scaler saved to `backend/models/scaler.pkl`
- [ ] `MODEL_VERSION` env var (or hardcoded string) baked into saved artefact metadata

### Model Loading
- [ ] `app.py` loads model + scaler once at startup (module-level, not per-request)
- [ ] `GET /api/health` returns model version and load status
- [ ] Missing model file raises clear error at startup, not at first request

---

## Phase 3 — Explainability (Days 13–16)

### SHAP (`backend/explainability.py`)
- [ ] `shap.TreeExplainer(model)` instantiated once at module import
- [ ] `explain(features_array)` returns dict of `{feature_name: shap_value}`
- [ ] Top 5 positive and top 5 negative contributors identified by `|shap_value|`
- [ ] SHAP computation time <100ms per request (verified with timing test)
- [ ] SHAP values are deterministic: same input produces same output
- [ ] Perturbation test: perturb one feature, SHAP value for that feature changes directionally

### Counterfactual Stub
- [ ] `get_counterfactual(features)` exists and returns `{"status": "not_implemented"}` — clearly marked for Phase stretch goal
- [ ] DiCE-ML dependency noted in `requirements.txt` with comment

### Integration
- [ ] `POST /api/score` response includes `shap_values` and `top_factors` fields
- [ ] SHAP values stored in `AuditRecord.shap_values` JSON column

---

## Phase 4 — Compliance Monitoring (Days 17–20)

### Fairness Metrics (`backend/compliance.py`)
- [ ] Rolling window of last 500 decisions maintained in memory (or queried from audit log)
- [ ] `compute_fairness(decisions_window)` returns:
  - `demographic_parity_difference` (float)
  - `equalized_odds_difference` (float)
  - `demographic_parity_ratio` (float)
  - `alert` (bool: True when ratio < 0.80)
- [ ] Uses `fairlearn.metrics.demographic_parity_difference` and `equalized_odds_difference`
- [ ] `GET /api/fairness` endpoint returns current metrics
- [ ] Alert flag set correctly when demographic parity ratio < 0.80
- [ ] Fairness metrics computed per-decision and stored in `AuditRecord.fairness_flags`
- [ ] Handles edge case: <2 decisions in window returns `null` metrics gracefully

### Validation
- [ ] Inject 100 biased decisions (deny all `sex=1`): demographic parity ratio drops below 0.80
- [ ] Alert flag becomes `true` in that scenario

---

## Phase 5 — API & Orchestration (Days 21–25)

### Flask Routes (`backend/app.py`)
- [ ] `POST /api/score` — full pipeline: fetch features → score → explain → fairness → audit → return
- [ ] `GET /api/audit` — paginated list, filter by `decision`, `date_from`, `date_to`
- [ ] `GET /api/audit/<application_id>` — full decision record
- [ ] `GET /api/audit/export` — `?format=csv` or `?format=json`
- [ ] `GET /api/fairness` — current rolling window metrics
- [ ] `GET /api/health` — model version, uptime, Kafka status, DB status
- [ ] CORS configured for `localhost:3000`
- [ ] Request validation rejects malformed input with 400 + error message
- [ ] All errors return JSON `{"error": "message"}`, never HTML stack traces
- [ ] Response time logged for every request (for latency measurement)

### Kafka (`backend/kafka_producer.py`)
- [ ] `KAFKA_ENABLED=false` disables producer cleanly — no import errors, no connection attempts
- [ ] When enabled: decision events published to `credit-decisions` topic as JSON
- [ ] Kafka connection failure does not crash the app — logs warning, continues
- [ ] `kafka_consumer.py` demo: reads from topic and prints — used only for demonstration

### Request Schema (`backend/schemas.py` — create this)
- [ ] Input schema: `credit_amount` (int), `duration` (int), `age` (int), `purpose` (str), `employment_years` (float), `existing_credits` (int), `sex` (int 0/1)
- [ ] Output schema includes all fields from PRD canonical data schema

---

## Phase 6 — Dashboard UI (Days 26–32)

### Credit Scoring Page (`Dashboard.js`)
- [ ] Form inputs for all 7 features with labels and validation
- [ ] Submit button calls `POST /api/score` via `api.js`
- [ ] Decision result displays: ACCEPT/DENY badge, probability percentage
- [ ] SHAP waterfall chart renders top positive and negative factors (Recharts or D3)
- [ ] Fairness impact indicator: green checkmark (no flag) or amber warning (alert)
- [ ] Loading state shown during API call
- [ ] Error state shown if API call fails

### Fairness Monitor Page
- [ ] Demographic parity ratio displayed as KPI card with threshold line
- [ ] Equalised odds difference displayed as KPI card
- [ ] Trend chart showing fairness metrics over last N decisions
- [ ] Alert banner when demographic parity ratio < 0.80
- [ ] Auto-refresh every 10 seconds (or manual refresh button)

### Audit Trail Page (`AuditPanel.js`)
- [ ] Search by `application_id` field
- [ ] Date range filter (from/to)
- [ ] Decision filter (all / accept / deny)
- [ ] Results table: ID, timestamp, decision, probability, model version
- [ ] Click row → expand to show SHAP values and fairness flags
- [ ] Export button: downloads CSV or JSON
- [ ] Pagination for large result sets

### System Health Page
- [ ] Model version displayed
- [ ] Uptime displayed
- [ ] Kafka status (connected / disabled)
- [ ] Database status (connected)
- [ ] Recent latency metrics (last 100 requests)

### General UI
- [ ] Navigation tabs work between all 4 pages
- [ ] Responsive layout (desktop-first is fine for dissertation context)
- [ ] No console errors in browser developer tools
- [ ] Tested in Chrome, Firefox, Edge (latest)

### API Client (`api.js`)
- [ ] Axios instance with `baseURL` pointing to Flask
- [ ] All API methods exported: `scoreApplication`, `getAuditList`, `getAuditById`, `exportAudit`, `getFairness`, `getHealth`
- [ ] Errors surface message to UI, not raw Axios error object

---

## Phase 7 — Integration (Days 33–36)

### End-to-End Flow
- [ ] Full flow works: fill form → submit → decision shown → audit log updated → audit search returns record
- [ ] SHAP values in UI match SHAP values in audit log for same `application_id`
- [ ] Fairness alert triggers correctly in UI when threshold breached
- [ ] Re-seeding legacy DB and re-submitting produces consistent results

### Error Scenarios
- [ ] Backend down: frontend shows graceful error message
- [ ] Kafka down (`KAFKA_ENABLED=true`, Kafka not running): API still scores and logs, logs warning
- [ ] Invalid form input: 400 error shown in UI, not uncaught exception
- [ ] Unknown `application_id` in audit search: returns 404 JSON, UI shows "not found"

### Performance Baseline
- [ ] Manual timing: `POST /api/score` round-trip measured in browser DevTools
- [ ] Single request end-to-end <500ms confirmed
- [ ] SHAP computation isolated and timed: <100ms confirmed

---

## Phase 8 — Evaluation (Days 37–42)

### Quantitative Benchmarks

#### Predictive Accuracy
- [ ] AUC-ROC on 20% hold-out: **target > 0.80** — result: ______
- [ ] Precision, recall, F1 recorded for dissertation

#### Latency (Locust load test)
- [ ] `eval/locustfile.py` created targeting `POST /api/score`
- [ ] 1000 concurrent users, 10-minute run
- [ ] p50 latency recorded: ______ms
- [ ] p95 latency: **target <500ms** — result: ______ms
- [ ] p99 latency recorded: ______ms
- [ ] 0% timeout rate confirmed
- [ ] All requests logged to audit confirmed (count audit rows = request count)

#### SHAP Fidelity
- [ ] Perturbation test: modify each feature ±10%, verify SHAP value moves directionally
- [ ] 50-sample consistency test: variance of SHAP values <10% across identical inputs

#### Fairness Compliance
- [ ] Inject synthetic biased dataset (100 applications, deny all female): parity ratio <0.80 detected
- [ ] Alert fires correctly
- [ ] Neutral dataset (balanced): parity ratio >0.80, no alert

#### Audit Completeness
- [ ] Inject 50 synthetic applications, verify all 50 appear in audit log
- [ ] Attempt direct SQL UPDATE on audit table: fails (permission or ORM guard)
- [ ] Attempt direct SQL DELETE on audit table: fails

#### Audit Retrieval Performance
- [ ] Seed 10,000+ audit records (script or load test residue)
- [ ] `GET /api/audit/<id>` query time **<2s** — result: ______ms

### Qualitative Evaluation
- [ ] Usability study protocol document written (`eval/usability_protocol.md`)
- [ ] SUS questionnaire prepared (10 standard questions)
- [ ] Explanation clarity 5-point Likert scale prepared
- [ ] 5 mock compliance officer sessions conducted
- [ ] SUS score calculated: **target ≥ 70** — result: ______
- [ ] Explanation clarity average: **target ≥ 3.5/5** — result: ______
- [ ] Task completion rate (retrieve 3 decisions): **target 100%** — result: ______
- [ ] Post-task interview notes transcribed for thematic analysis

### Results Documentation
- [ ] `docs/EVALUATION.md` written with all quantitative results and charts
- [ ] Latency percentile chart (p50/p95/p99) created
- [ ] Fairness metric chart created
- [ ] Usability results table created

---

## Phase 9 — Dissertation Write-up (Days 43–56)

### Documentation
- [ ] `README.md` completed (installation, usage, quick start)
- [ ] `docs/INSTALL.md` step-by-step for fresh machine setup
- [ ] `docs/API.md` all endpoints with request/response examples
- [ ] `docs/EVALUATION.md` full evaluation results

### Dissertation Chapters
- [ ] Chapter 1: Introduction — problem statement, RQs, objectives
- [ ] Chapter 2: Literature Review — ≥50 sources, gap matrix
- [ ] Chapter 3: Methodology — DSR justification, evaluation design
- [ ] Chapter 4: System Design — architecture diagrams, component specs
- [ ] Chapter 5: Implementation — code walkthrough, key decisions
- [ ] Chapter 6: Evaluation — quantitative + qualitative results, discussion
- [ ] Chapter 7: Conclusion — RQ answers, limitations, future work

### Final Checks
- [ ] All evaluation targets met or deviations documented with justification
- [ ] Prototype demo script prepared (10-minute walkthrough for viva)
- [ ] All code pushed to Git with meaningful commit history
- [ ] Docker compose `docker compose up && seed && npm start && python app.py` confirmed working on clean machine

---

## Stretch Goals (Post-MVP)

- [ ] **FR9** Counterfactual explanations via DiCE-ML — full implementation
- [ ] **FR10** Real-time fairness alert toast notifications in dashboard
- [ ] **FR11** Kafka streaming verified with consumer reading decisions
- [ ] **FR12** Model versioning — A/B test between model v1 and v2 with audit comparison
- [ ] **FR13** Bulk export tested with 10,000+ records
- [ ] **FR14** SHAP force plot (D3 waterfall) polished for dissertation screenshots
- [ ] **FR16** LIME as alternative explainer — comparative evaluation section
- [ ] SHAP vs LIME explanation agreement metric

---

## Acceptance Tests

### Test 1 — End-to-End Decision Flow
- [ ] Submit: amount=5000, duration=12, age=30, purpose=car, employment=2, credits=1, sex=0
- [ ] Response received within 500ms
- [ ] Decision (accept or deny) shown with probability
- [ ] SHAP waterfall shows ≥3 features
- [ ] `application_id` from response found in audit search

### Test 2 — Audit Retrieval
- [ ] Copy `application_id` from Test 1
- [ ] Enter in Audit Trail search
- [ ] Full record returned: input features, decision, SHAP values, fairness flags, model version
- [ ] SHAP values match what was displayed in Test 1

### Test 3 — Fairness Alert
- [ ] Submit 20+ applications with identical features except `sex` alternating 0/1
- [ ] Manipulate to produce biased outcomes (or test with injected data)
- [ ] When demographic parity ratio < 0.80, alert banner appears in Fairness Monitor

### Test 4 — Immutability
- [ ] Connect to SQLite/PostgreSQL with a DB client
- [ ] Attempt `UPDATE audit_records SET decision='accept' WHERE id=...` — should fail or be blocked
- [ ] Attempt `DELETE FROM audit_records WHERE id=...` — should fail or be blocked

### Test 5 — Load Test Pass
- [ ] Locust 1000-user run completes with 0% failures
- [ ] p95 latency < 500ms
- [ ] All 1000+ requests present in audit log
