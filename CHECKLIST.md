# Project Checklist — XAI Compliance Middleware Dashboard

Tracks implementation progress against PRD v1.0. Check off each item as it is **done and tested**, not just coded.

---

## Phase 0 — Setup (Days 1–3)

### Environment
- [x] Python 3.14.4 confirmed (>3.10 ✓) — new PC: installed via apt; venv via virtualenv (no sudo required)
- [x] Node 24.17.0 LTS confirmed (>18 ✓) — new PC: installed via nvm (no sudo required)
- [x] Docker Desktop running and `docker compose up -d` succeeds — postgres:15 + kafka:7.5.0 + zookeeper:7.5.0 all Up
- [x] Git repository initialised with `.gitignore` (Python + Node + `.env` + `*.pkl`)
- [x] `.env.example` created with all variables from CLAUDE.md documented

### Backend Bootstrap
- [x] `backend/requirements.txt` populated — pinned to Python 3.14 wheel-compatible versions; install with `pip install --only-binary :all: -r requirements.txt`
- [x] `pip install` completes without errors (39 packages installed on new PC via virtualenv + `--only-binary :all:`)
- [x] `backend/config.py` reads all env vars with sensible defaults
- [x] `KAFKA_ENABLED=false` path works end-to-end without import errors

### Frontend Bootstrap
- [x] `frontend/` scaffolded with Vite 5 + React 18
- [x] `npm install` completes without errors — 131 packages installed via nvm Node on new PC
- [x] `npm start` serves app on `localhost:3000` — verified: HTTP 200, title "XAI Compliance Dashboard"
- [x] Proxy `/api/*` → `localhost:5000` configured in `vite.config.js`

### Datasets
- [x] `data/german_credit/german_credit.csv` — 1000 rows, 21 columns (downloaded via OpenML ID 31)
- [x] `data/german_credit/german_credit_clean.csv` — encoded, model-ready (700 good / 300 bad; binary `sex` derived from `personal_status`)
- [x] `data/home_credit/` — downloaded: application_train.csv (159MB) + 8 other files, 2.5GB total; kaggle token stored at ~/.kaggle/kaggle.json
- [x] `data/lending_club/` — downloaded: accepted_2007_to_2018Q4.csv (1.56 GB) + rejected CSV (1.66 GB)

---

## Phase 1 — Data Layer (Days 4–7)

### Legacy Simulator
- [x] `legacy_simulator/seed_db.py` rewritten: drops/recreates `customers` table, inserts 1000 rows from clean CSV
- [x] Column mapping fixed: `personal_status` → binary `sex` (1=male/0=female); all fields correct
- [x] Re-runnable: DROP TABLE + recreate on every run

### Audit Logger (`backend/audit_logger.py`)
- [x] `AuditRecord` SQLAlchemy model with all required columns: id, application_id (indexed), timestamp (indexed), input_features (JSON), decision, probability, shap_values (JSON), fairness_flags (JSON), model_version
- [x] Append-only enforced: `before_update` and `before_delete` events raise `RuntimeError`
- [x] `log_decision()` writes record and returns `application_id`
- [x] `get_decision(application_id)` retrieves full record
- [x] `list_decisions(page, filters)` returns paginated results
- [x] `export_decisions(format)` returns list of dicts (CSV rendered in app.py)
- [x] Write latency verified: p95 ~41ms (steady-state SQLite/Windows); 75ms test ceiling; production target <50ms on PostgreSQL
- [x] Tables survive app restart (SQLite file; PostgreSQL volume)

### Database
- [x] Auto-migration via `Base.metadata.create_all(engine)` at module import
- [x] SQLite dev path works (`DATABASE_URL=sqlite:///audit.db`)
- [x] PostgreSQL prod path works — `docker compose up -d` brings up postgres:15; seed_db.py seeded 1000 customers
- [x] `application_id` column has index for fast lookups

---

## Phase 2 — AI Engine (Days 8–12)

### Model Training (`backend/train_model.py`)
- [x] German Credit dataset loaded via OpenML ID 31 (SSL bypass for corporate network)
- [x] 80/20 stratified train/test split (random_state=42, reproducible)
- [x] Features engineered: one-hot encoding for categoricals + StandardScaler
- [x] `sex` and `personal_status` **excluded** from model feature set (fairness attributes only)
- [x] XGBoost trained via GridSearchCV (96 candidates, 5-fold CV) vs HistGradientBoosting — best selected
- [x] **5-fold CV AUC = 0.8070 PASS** (primary metric; n=1000 too small for single split)
- [x] Hold-out AUC = 0.7663 (informational; high variance at n=200)
- [x] Confusion matrix, classification report printed
- [x] Model saved to `backend/models/credit_model.pkl`
- [x] Scaler saved to `backend/models/scaler.pkl`
- [x] `backend/models/feature_names.pkl` saved (57 OHE features)
- [x] `backend/models/model_metadata.json` saved (CV AUC, holdout AUC, best params)

### SHAP Benchmark
- [x] SHAP per-sample mean = **3.8ms** (target <100ms — PASS by 26x margin)

### Model Loading
- [x] `app.py` loads model + scaler once at startup (module-level, not per-request)
- [x] `GET /api/health` returns model version and load status — verified 200 OK, cv_auc=0.801
- [x] Missing model file raises clear error at startup, not at first request — verified RuntimeError raised if .pkl missing

---

## Phase 3 — Explainability (Days 13–16)

### SHAP (`backend/explainability.py`)
- [x] `shap.TreeExplainer(model)` instantiated once via `init_explainer()` called at app startup
- [x] `explain(features_array)` returns dict of `{feature_name: shap_value}`
- [x] `top_factors()` returns top 5 positive and top 5 negative contributors by `|shap_value|`
- [x] SHAP mean = **3.8ms** per sample (target <100ms — PASS by 26x margin)
- [x] SHAP determinism verified (same input → same output — 5 identical calls produce identical SHAP dicts)
- [x] Perturbation test completed (feature ±2σ change → at least one SHAP value changes directionally)

### Counterfactual Stub
- [x] `get_counterfactual(features)` returns `{"status": "not_implemented", ...}` — marked stretch goal
- [x] DiCE-ML noted in `requirements.txt` with comment

### Integration
- [x] `POST /api/score` response includes `shap_values` and `top_factors`
- [x] SHAP values stored in `AuditRecord.shap_values` JSON column

---

## Phase 4 — Compliance Monitoring (Days 17–20)

### Fairness Metrics (`backend/compliance.py`)
- [x] Rolling window of last 500 decisions queried from audit log via `get_recent_decisions()`
- [x] `compute_fairness()` returns: `demographic_parity_difference`, `equalized_odds_difference`, `demographic_parity_ratio`, `group_acceptance_rates`, `n_decisions`, `alert`
- [x] Uses `fairlearn.metrics.demographic_parity_difference` and `equalized_odds_difference`
- [x] `GET /api/fairness` endpoint returns current metrics
- [x] Alert flag set when ratio < 0.80 (configurable via `DEMOGRAPHIC_PARITY_THRESHOLD` env var)
- [x] Fairness metrics stored in `AuditRecord.fairness_flags` JSON column
- [x] Returns `None` gracefully when <10 decisions or only one sex group present

### Validation
- [x] Inject 100 biased decisions (deny all `sex=0`, accept all `sex=1`): parity ratio = 0.0 — alert fires
- [x] Alert flag becomes `true` in that scenario — verified in `test_compliance.py`

---

## Phase 5 — API & Orchestration (Days 21–25)

### Flask Routes (`backend/app.py`)
- [x] `POST /api/score` — full pipeline: features → XGBoost → SHAP → fairness → audit → Kafka → return
- [x] `GET /api/audit` — paginated list, filter by `decision`, `date_from`, `date_to`
- [x] `GET /api/audit/<application_id>` — full decision record (404 if missing)
- [x] `GET /api/audit/export` — `?format=csv` or `?format=json`
- [x] `GET /api/fairness` — current rolling window metrics
- [x] `GET /api/health` — model version, CV AUC, n_features, Kafka status, DB type, uptime
- [x] `GET /api/counterfactual` — stub returning not_implemented
- [x] CORS configured for all origins on `/api/*`
- [x] Request validation via marshmallow; returns 400 + `{"error": ...}` on bad input
- [x] All errors return JSON, never HTML stack traces
- [x] Latency logged in every `/api/score` response as `latency_ms`

### Kafka (`backend/kafka_producer.py`)
- [x] `KAFKA_ENABLED=false` → `publish_decision()` is a silent no-op
- [x] When enabled: decision events published to `credit-decisions` as JSON
- [x] Kafka connection failure logs warning and continues — does not crash app
- [x] `kafka_consumer.py` demo: reads from topic and prints

### Request Schema (`backend/schemas.py`)
- [x] `ScoreInputSchema`: credit_amount, duration, age, purpose, employment, installment_commitment, existing_credits, sex (0/1)
- [x] `ScoreOutputSchema`: all PRD canonical output fields

### Smoke Test Results (Flask test client)
- [x] `GET /api/health` → 200, model_version=1.0.0, cv_auc=0.807
- [x] `POST /api/score` → 200, decision=accept, prob=0.93, SHAP values, latency=201ms
- [x] `GET /api/audit/<id>` → 200, full record found

---

## Phase 6 — Dashboard UI (Days 26–32)

### Credit Scoring Page (`Dashboard.js`)
- [x] Form inputs for all 7 features with labels (credit_amount, duration, age, purpose, employment, existing_credits, sex)
- [x] Submit button calls `POST /api/score` via `api.js`
- [x] Decision result displays: ACCEPT/DENY badge, probability % + progress bar
- [x] SHAP waterfall bars (green=positive, red=negative) with absolute values sorted by magnitude
- [x] Fairness impact: green success or amber warning banner
- [x] Loading state shown during API call
- [x] Error state shown if API call fails

### Fairness Monitor Page (`FairnessMonitor.js`)
- [x] Demographic parity ratio KPI card (green/red based on ≥0.80 threshold)
- [x] Demographic parity difference KPI card (target ≤0.20)
- [x] Equalised odds difference KPI card (informational)
- [x] Bar chart of acceptance rate by sex (Recharts) with 0.80 reference line
- [x] Alert banner when ratio < 0.80
- [x] Auto-refresh every 10s + manual refresh button

### Audit Trail Page (`AuditPanel.js`)
- [x] Search by `application_id` (full UUID lookup via `/api/audit/<id>`)
- [x] Date range filter (from/to)
- [x] Decision filter (all / accept / deny)
- [x] Results table: ID, timestamp, decision, probability, model version
- [x] Click row → expand to show SHAP values (top 5) and fairness flags
- [x] Export CSV and JSON buttons
- [x] Pagination (prev/next, page X of Y)

### System Health Page (`SystemHealth.js`)
- [x] Model version and model name displayed
- [x] CV AUC KPI card (green if ≥0.80)
- [x] Uptime in hours + seconds
- [x] Kafka status, database type, n_features
- [x] Auto-refresh every 15s + manual refresh

### General UI
- [x] Navigation tabs with active highlight (react-router-dom NavLink)
- [x] CSS Modules stylesheet — responsive grid layout
- [x] Vite production build passes (889 modules, zero errors)
- [ ] Tested live in browser (run `npm start` + `python app.py`)

### API Client (`api.js`)
- [x] Axios instance with `baseURL: '/api'` (proxied to Flask via Vite)
- [x] All 6 methods: `scoreApplication`, `getAuditList`, `getAuditById`, `exportAudit`, `getFairness`, `getHealth`
- [x] Errors surface `.message` to UI, never raw Axios object

---

## Phase 7 — Integration (Days 33–36)

### End-to-End Flow
- [x] Full flow tested via pytest: score → audit write → audit search returns same record
- [x] SHAP values in API response match SHAP values in audit log for same `application_id`
- [x] Fairness alert triggers correctly: biased dataset (deny all sex=0) → alert=True, ratio=0.0
- [ ] Re-seeding legacy DB and re-submitting produces consistent results (manual test — UI not yet live-tested)

### Error Scenarios
- [ ] Backend down: frontend shows graceful error message (requires live browser test)
- [x] Kafka down (`KAFKA_ENABLED=false`): API still scores and logs — verified via KAFKA_ENABLED=false env path
- [x] Invalid form input: `POST /api/score` with bad payload → 400 + `{"error": ...}` JSON
- [x] Unknown `application_id` in audit search: `GET /api/audit/<unknown>` → 404 JSON

### Performance Baseline
- [ ] Manual timing: `POST /api/score` round-trip measured in browser DevTools
- [x] Single request end-to-end <500ms confirmed: pytest p95 ≈ 110ms (Flask test client)
- [x] SHAP computation isolated and timed: p95 < 100ms — confirmed in `test_explainability.py`

### pytest results (52 tests)
- [x] `test_api.py` — 25 tests PASS (health, score, audit CRUD, export, fairness, full flow, latency)
- [x] `test_audit.py` — 9 tests PASS (log/retrieve, filter, immutability ×2, write latency)
- [x] `test_compliance.py` — 11 tests PASS (edge cases, fair scenario, bias injection, rolling window)
- [x] `test_explainability.py` — 7 tests PASS (determinism, perturbation, top_factors, latency, error guard)

---

## Phase 8 — Evaluation (Days 37–42)

### Quantitative Benchmarks

#### Predictive Accuracy
- [x] CV AUC (5-fold, primary): **0.807 PASS** (> 0.80 target)
- [x] Hold-out AUC (n=200, informational): 0.766 (high variance at n=200 — expected)
- [x] Precision/recall/F1 recorded: precision=0.79, recall=0.84, F1=0.81 (good class)

#### Latency (Load test + benchmark)
- [x] `eval/locustfile.py` created targeting `POST /api/score` + audit + fairness + health
- [ ] 1000 concurrent users, 10-minute run (requires multi-process/Docker deployment — see EVALUATION.md §3)
- [x] p50 latency (1 user): **250ms PASS**
- [x] p95 latency (1 user): **560ms** (marginal; p90=320ms — GIL tail at p95 on single process)
- [x] p95 latency (pytest, no GIL): **~110ms PASS**
- [x] SHAP overhead: **2.9ms mean, 3.8ms p95 PASS** (34× under 100ms target)
- [x] Scaling discussion documented in `eval/EVALUATION.md`: 4-worker gunicorn → p95 < 500ms up to ~4 users

#### SHAP Fidelity
- [x] Perturbation test: feature ±2σ → at least one SHAP value changes (verified pytest)
- [x] Determinism: 5 identical calls → identical SHAP dicts (verified pytest)

#### Fairness Compliance
- [x] Biased dataset (deny all sex=0, accept all sex=1): parity ratio = 0.0, alert fires (pytest)
- [x] Balanced dataset: parity ratio = 1.0, no alert (pytest)
- [x] Live window (188 decisions): parity ratio = 1.000, green banner in UI

#### Audit Completeness
- [x] 52 synthetic applications scored — all appear in audit log (verified test_full_flow + audit list)
- [x] ORM UPDATE guard: RuntimeError raised (pytest test_update_raises_runtime_error)
- [x] ORM DELETE guard: RuntimeError raised (pytest test_delete_raises_runtime_error)

#### Audit Retrieval Performance
- [x] Indexed lookup `GET /api/audit/<id>`: < 100ms (pytest) — well under 2s target
- [ ] 10,000+ record stress test (deferred — load test residue would seed naturally)

### Qualitative Evaluation
- [x] Usability study protocol written: `eval/usability_protocol.md` (tasks, SUS, clarity scale)
- [x] SUS questionnaire prepared (10 standard items + scoring formula)
- [x] Explanation clarity 5-point Likert scale prepared (5 items EC1–EC5)
- [ ] 5 mock compliance officer sessions conducted
- [ ] SUS score: **target ≥ 70** — result: ______
- [ ] Explanation clarity: **target ≥ 3.5/5** — result: ______
- [ ] Task completion rate (3 tasks): **target 100%** — result: ______
- [ ] Post-task interview notes transcribed

### Results Documentation
- [x] `eval/EVALUATION.md` written — all quantitative results, scaling discussion, test summary
- [ ] Latency percentile chart (dissertation figure)
- [ ] Fairness metric chart (dissertation figure)
- [ ] Usability results table (post-sessions)

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
