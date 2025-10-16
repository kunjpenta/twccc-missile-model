ere’s a detailed, polished version of your document for Tasks 1–10, with added context and clarity for your frontend and database teams. I’ve also included key notes on testing, API access, and project structure for reference.

TEWA Backend Project Tasks Documentation
Task 1 — Project scaffold

Task Name: Project scaffold
Sub task: Setup Django Project
Sub Sub Task: Initialize project and configure settings
Description: Create Django project and apps, set up project settings, environment variables, and required tooling.
Notes: Basic project scaffolding including project root, apps, settings, WSGI/ASGI configuration.
Repo paths touched: manage.py, missile_model/settings.py, missile_model/asgi.py, missile_model/wsgi.py, requirements.txt

Task 2 — PostgreSQL wiring

Task Name: PostgreSQL wiring
Sub task: Database Setup
Sub Sub Task: Configure PostgreSQL DB and migrations
Description: Connect Django to PostgreSQL, configure DATABASE_URL, and create/verify initial migrations.
Notes: Basic DB setup; ensure psycopg is installed and environment variables are loaded correctly.
Repo paths touched: missile_model/settings.py, tewa/migrations/*, core/migrations/, missile_db.sql

Task 3 — Core domain models

Task Name: Core domain models
Sub task: Models
Sub Sub Task: Create core models (DefendedAsset, Scenario, Track)
Description: Define main entities: DefendedAsset, Scenario, Track, TrackSample, ThreatScore, ModelParams.
Notes: Core data models form the foundation of the TEWA threat evaluation pipeline.
Repo paths touched: tewa/models.py, tewa/migrations/0001*\* … 0011*_, core/models.py (if any), tests in tewa/tests/test_models_.py

Task 4 — Units & geodesy baseline

Task Name: Units & geodesy baseline
Sub task: Units Conversion
Sub Sub Task: Add conversion helpers (planar + geodesic)
Description: Define unit standards (meters, seconds) and implement helpers for planar and geodesic calculations.
Notes: Ensures consistent math across threat computations and kinematic modules.
Repo paths touched: core/utils/units.py, core/utils/geodesy.py, tests in core/tests/test_units_geodesy.py

Task 5 — Seed data fixtures

Task Name: Seed data fixtures
Sub task: Seed DA & Tracks
Sub Sub Task: Insert sample DA, scenario, and tracks
Description: Preload sample DefendedAssets, scenarios, and tracks to enable development, demos, and testing.
Notes: Initial dataset includes multiple scenarios (Scenario-2, Scenario-3, Demo-Scenario) and DA entries (DA-Alpha, DA-Bravo).
Repo paths touched: tewa/fixtures/tewa_seed.json, tewa/management/commands/seed_demo.py

Task 6 — Kinematics math module

Task Name: Kinematics math module
Sub task: Implement CPA/TCPA
Sub Sub Task: Write CPA, TCPA, TDB, TWRP functions
Description: Implement deterministic formulas to compute CPA (Closest Point of Approach), TCPA (Time to CPA), TDB (Time to DA Boundary), and TWRP (Time to Weapon Release).
Notes: Core kinematics calculations; vectorized and time-based for scenario computation.
Repo paths touched: tewa/services/kinematics.py, tests in core/tests/test_kinematics.py, tewa/tests/test_compute_threats.py

Task 7 — Normalization & scoring

Task Name: Normalization & scoring
Sub task: Threat Scoring
Sub Sub Task: Implement scoring and normalization functions
Description: Normalize metrics between 0–1 and compute weighted sum to derive a final threat score for each track–DA pair.
Notes: Allows adjustable weights per model metric (w_cpa, w_tcpa, w_tdb, w_twrp) for tuning threat evaluation.
Repo paths touched: tewa/services/normalize.py, tewa/services/scoring.py, tests in core/tests/test_scoring.py

Task 8 — Scenario engine

Task Name: Scenario engine
Sub task: Compute Scores
Sub Sub Task: Implement scenario engine logic
Description: Orchestrates threat scoring by combining kinematics, normalization, and scoring functions for all tracks and DAs in a scenario.
Notes: Supports batch computation, persistence, and triggers via management commands or API endpoints.
Repo paths touched: tewa/services/engine.py, tewa/services/threat_compute.py, tewa/services/ranking.py, tests in tewa/tests/test_compute_multiple_scenarios.py, tewa/tests/test_ranking.py

Task 9 — CSV import (tracks)

Task Name: CSV import (tracks)
Sub task: Upload CSV
Sub Sub Task: Parse CSV for track data
Description: Upload CSV files containing track data; parse and insert as Track and TrackSample rows.
Notes: Includes validation, error handling, timestamp parsing, and prevention of duplicate track entries. Used in frontend “Upload Tracks” UI.
Repo paths touched: tewa/services/csv_import.py, tewa/management/commands/import_tracks.py, tewa/api/serializers.py

Task 10 — DA geometry

Task Name: DA geometry
Sub task: DA Setup
Sub Sub Task: Implement DA geometry and validation
Description: Implement forms and server-side validation for DefendedAssets (point + radius). Supports backend threat computation checks.
Notes: Frontend form allows creating/editing DAs with a radius; ensures valid protected zone for threat scoring.
Repo paths touched: tewa/forms.py, tewa/serializers.py, tewa/views.py, tests in tewa/tests/test_da_creation.py

Project structure reference (relevant folders/files)
missile_model/
├─ manage.py
├─ README.md
├─ requirements.txt
├─ missile_db.sql
├─ core/
│ ├─ utils/
│ │ ├─ geodesy.py
│ │ ├─ units.py
│ └─ tests/
├─ missile_model/
│ ├─ settings.py
│ └─ urls.py
├─ tewa/
│ ├─ models.py
│ ├─ forms.py
│ ├─ serializers.py
│ ├─ views.py
│ ├─ fixtures/
│ ├─ management/commands/
│ ├─ services/
│ └─ tests/
├─ templates/

Additional Notes for Frontend & DB Team

APIs / Endpoints:

POST /api/tewa/upload_tracks/ → upload CSV tracks

POST /api/tewa/compute_now/ → compute threat scores for scenario

GET /api/tewa/ranking/?scenario_id=<id>&top_n=<n> → get top-N threats

GET /api/tewa/scenarios/ → list scenarios

GET /api/tewa/da/ → list DAs

Test Data:

Seeded scenarios (Scenario-2, Scenario-3, Demo-Scenario) and DAs (DA-Alpha, DA-Bravo)

Tracks with sample positions, speeds, and headings

Testing:

Run unit tests: python manage.py test tewa.tests

Manual testing via Django Admin or HTML pages (home.html, scenario_detail.html)

CSV uploads can be tested via upload_tracks API

Frontend Integration:

Initial frontend HTML pages are used for API checks.

Later Angular SPA will call these backend endpoints for full UI interactions.

Task 11 — Periodic compute command

Task Name: Periodic compute command
Sub task: Command Setup
Sub Sub Task: Implement compute_threats management command

Description:
Implement a Django management command compute_threats to compute threat scores for all tracks vs. DAs on a schedule (cron/systemd). Supports options like --scenario, --at <ISO timestamp>, and batch mode for multiple DAs.

Notes:

Logs summaries per scenario/DA run.

Returns non-zero exit code on errors.

Can be triggered manually or by system scheduler.

Repo paths touched:
tewa/management/commands/compute_threats.py, tewa/services/engine.py, tewa/services/threat_compute.py, tewa/services/ranking.py, tewa/models.py

Task 12 — Manual compute trigger

Task Name: Manual compute trigger
Sub task: Compute Now Button
Sub Sub Task: Implement compute trigger button in UI

Description:
Add a “Compute Now” button on Scenario detail pages to trigger immediate threat computation for the selected scenario and timestamp.

Notes:

Server POSTs compute job.

Returns success/failure with optional toast notification.

Refreshes board/UI on completion.

Repo paths touched:
tewa/views.py, tewa/urls.py, templates/scenarios/detail.html, tewa/api/views.py

Task 13 — Threat ranking service

Task Name: Threat ranking service
Sub task: Rank Threats
Sub Sub Task: Implement ranking for DA/Global threats

Description:
Provides top-N threat rankings per DA or global. Each entry includes detailed metrics (CPA/TCPA/TDB/TWRP) and final computed score. Supports sorting by score or timestamp.

Notes:

API endpoint for ?scenario_id=&top_n=&da_id= queries.

Pagination support and score breakdown optional.

Repo paths touched:
tewa/services/ranking.py, tewa/services/score_breakdown.py, tewa/api/views.py, tewa/api/serializers.py, tewa/api/urls.py

Task 14 — Model params admin UI

Task Name: Model params admin UI
Sub task: Admin Forms
Sub Sub Task: Implement forms for ModelParams edit

Description:
Admin interface to edit scoring weights, sigmas, DA radius (R_DA), weapon range (R_W), and scenario tick rate. Includes validation and persistence.

Notes:

Inline help and default values included.

Only admin-accessible.

Repo paths touched:
tewa/forms.py, tewa/admin.py, tewa/views.py, templates/modelparams/edit.html, tewa/serializers.py

Task 15 — Minimal HTML templates

Task Name: Minimal HTML templates
Sub task: Base Template
Sub Sub Task: Implement base layout with nav & table CSS

Description:
base.html provides consistent navbar, container, and table styling for all pages. Includes blocks for content and optional scripts.

Notes:

Pure HTML + CSS; no JS framework required.

Enables early frontend testing against APIs.

Repo paths touched:
templates/base.html, missile_model/settings.py (TEMPLATES), static/ (optional CSS), missile_model/static/favicon.ico

Task 16 — Pages: Home & Scenarios

Task Name: Pages: Home & Scenarios
Sub task: Scenario List
Sub Sub Task: Implement scenario listing page

Description:
Home page lists all scenarios (name, start/end times, notes) with links to scenario detail pages and optional quick actions.

Notes:

Supports server-side pagination.

Backend-driven template rendering.

Repo paths touched:
tewa/views.py, tewa/urls.py, templates/home.html, templates/scenarios/list.html

Task 17 — Scenario detail page

Task Name: Scenario detail page
Sub task: Threat Details
Sub Sub Task: Implement scenario detail page with DA/track info

Description:
Displays DA list, tracks, latest computed threat ranks, and “Compute Now” control. Optional drill-down into component scores.

Notes:

Supports CSV export of track and score data.

Backend-driven UI with template rendering.

Repo paths touched:
tewa/views.py, templates/scenarios/detail.html, tewa/services/score_breakdown_service.py

Task 18 — DA CRUD

Task Name: DA CRUD
Sub task: Create/Edit DA
Sub Sub Task: Implement create/edit forms for DefendedAsset (DA)

Description:
Create, edit, and delete DefendedAssets. Includes validation for coordinates, radius (>0), and scenario association. Optional map preview of DA radius.

Notes:

Prevents duplicate DA names per scenario.

Delete confirmation and safe redirect to DA list.

Repo paths touched:
tewa/forms.py, tewa/views.py, tewa/urls.py, templates/da/create.html, templates/da/edit.html, tewa/tests/test_da_creation.py

Task 19 — Track browser

Task Name: Track browser
Sub task: Track Search
Sub Sub Task: Implement search and per-track detail views

Description:
Search/filter tracks by ID, callsign, or source. Per-track detail view shows latest state and history of positions over time.

Notes:

Server-side filtering and pagination.

Supports CSV export for individual tracks.

Repo paths touched:
tewa/views.py, tewa/urls.py, templates/tracks/list.html, templates/tracks/detail.html, tewa/api/serializers.py, tewa/api/views.py

Task 20 — Threat board

Task Name: Threat board
Sub task: Threat List
Sub Sub Task: Implement per-DA threat board (sortable by score)

Description:
Board view per DA showing track, CPA, TCPA, TDB, TWRP, and computed score. Sortable, refreshable, and highlights “assigned” targets.

Notes:

Score color ramps for threat severity.

Frontend polling optional; template-driven view works for API testing.

Repo paths touched:
tewa/views.py, tewa/services/ranking.py, templates/boards/da_board.html, tewa/tests/test_ranking.py, tewa/tests/test_score_breakdown_api.py

Task 21 — Score breakdown view

Task Name: Score breakdown view
Sub task: Component Breakdown
Sub Sub Task: Implement breakdown for each score component

Description:
Expose a per-threat “score breakdown” that shows component values and contributions for CPA, TCPA, TDB, TWRP, including normalized values and weightings. Provide both an API and a minimal template UI (modal/side panel) from Scenario Detail and Threat Board.

Notes:

Include raw metric, normalized metric (0–1), weight, and weighted contribution.

Support ?scenario_id=, ?da_id=, ?track_id= filters and ?at= timestamp.

Keep the component math consistent with tewa/services/normalize.py and tewa/services/scoring.py.

Repo paths touched:

tewa/services/score_breakdown.py (new; core computation + formatting)

tewa/api/views.py (new endpoint)

tewa/api/serializers.py (ScoreBreakdownSerializer)

tewa/api/urls.py

tewa/services/ranking.py (helper hook)

templates/boards/score_breakdown.html (optional minimal UI)

tewa/tests/test_score_breakdown_api.py (API tests)

API (proposed):

GET /api/tewa/score_breakdown/?scenario_id=&da_id=&track_id=&at= → JSON list of components with {name, raw, normalized, weight, weighted} and final_score.

Acceptance Criteria:

Returns correct per-component breakdown that sums to final_score (±1e-6).

Filters work; 404/400 on invalid IDs; pagination not required but supported if list >50.

Unit tests cover at least 4 scenarios/edge cases (zero weights, missing metrics, extreme values).

Task 22 — CSV export (Threat Board)

Task Name: CSV export
Sub task: Export Threat Data
Sub Sub Task: Implement export of threat board to CSV

Description:
Export current Threat Board (per-DA or global) as CSV, including track metadata, CPA/TCPA/TDB/TWRP, normalized values, weights, and final_score.

Notes:

Use streaming responses for large exports.

Include header row with units and column notes.

Support the same filters as Threat Board: scenario_id, da_id, top_n, at.

Repo paths touched:

tewa/api/views.py (CSV endpoint)

tewa/services/export_csv.py (new; generator/streamer)

tewa/api/urls.py

templates/boards/da_board.html (Export button)

tewa/tests/test_csv_export.py

API (proposed):

GET /api/tewa/export/threats.csv?scenario_id=&da_id=&top_n=&at=

Acceptance Criteria:

CSV downloads with correct MIME/type, ordered by final_score desc by default.

Columns: scenario, da, track_id, callsign, time, cpa_m, tcpa_s, tdb_s, twrp_s, n_cpa, n_tcpa, n_tdb, n_twrp, w_cpa, w_tcpa, w_tdb, w_twrp, final_score.

Export of ≥100k rows works without timeout on target infra (document any limits).

Task 23 — Scenario assumptions page

Task Name: Scenario assumptions page
Sub task: Scenario Defaults
Sub Sub Task: Create page to set defaults for scenario parameters (weapon range, DA radius)

Description:
UI + API for setting and persisting scenario-level defaults: weapon range (R_W), DA radius (R_DA), tick rate, default model weights, sigma/scale factors. Values apply as defaults when creating DAs/Tracks or when parameters are absent.

Notes:

Staff-only access.

Show effective value resolution: scenario override → global default → code default.

Add server-side validation and help text.

Repo paths touched:

tewa/models.py (ScenarioSettings or extend ModelParams linkage)

tewa/forms.py, tewa/serializers.py

tewa/views.py, tewa/urls.py

templates/scenarios/assumptions.html

tewa/tests/test_scenario_assumptions.py

API (proposed):

GET/PUT /api/tewa/scenario_defaults/?scenario_id=
Body: { R_W, R_DA, tick_hz, weights: {cpa, tcpa, tdb, twrp}, sigmas: {...} }

Acceptance Criteria:

Values persist and affect new compute runs when explicit params are missing.

Validation: R_W, R_DA > 0, tick_hz in [1, 20] (tunable), weights sum not required.

Permission-guarded views and endpoints.

Task 24 — Basic plotting (server-side PNG)

Task Name: Basic plotting
Sub task: PNG Chart
Sub Sub Task: Generate basic PNG charts for score history using Matplotlib

Description:
Generate server-side PNG charts (no JS dependency) for score history per track, per DA, and per scenario time window. Return PNG bytes via HTTP and expose <img> tags in templates.

Notes:

Use Matplotlib Agg backend.

Anti-aliasing, axes labels (UTC), legend (final score + components).

Limit series to sane max points (downsample if needed).

Repo paths touched:

tewa/services/charting.py (new; data prep + plotting)

tewa/api/views.py (image endpoint)

tewa/api/urls.py

templates/boards/da_board.html (thumbnail chart)

tewa/tests/test_chart_endpoint.py

API (proposed):

GET /api/tewa/charts/score_history.png?scenario_id=&da_id=&track_id=&from=&to=

Acceptance Criteria:

Valid PNG returned with correct caching headers (ETag/Cache-Control).

Handles missing data gracefully with placeholder “No data” plot.

Unit test: PNG signature check + basic pixel size assert.

Task 25 — Validation tests (pytest)

Task Name: Validation tests (pytest)
Sub task: Unit Tests
Sub Sub Task: Write unit tests for kinematic functions and integration tests

Description:
Add thorough unit tests for CPA/TCPA/TDB/TWRP formulas and integration tests for the end-to-end pipeline (seed → compute → rank → breakdown).

Notes:

Include edge cases: parallel course, head-on, zero velocity, DA boundary grazing, negative TCPA.

Freeze time for determinism.

Repo paths touched:

tewa/tests/test_kinematics_units.py

tewa/tests/test_pipeline_integration.py

core/tests/test_units_geodesy.py (extend if needed)

Acceptance Criteria:

pytest -q passes; coverage for tewa/services/kinematics.py ≥ 90%.

Numeric tolerances documented (1e-6 float compare).

Task 26 — Data sanity checks (input validation)

Task Name: Data sanity checks
Sub task: Input Validation
Sub Sub Task: Add data validation for input forms

Description:
Introduce server-side sanity checks across forms/serializers for DAs, Tracks, and CSV imports to prevent invalid inputs.

Notes:

Validate lat ∈ [-90, 90], lon ∈ [-180, 180], radius > 0, speed ≥ 0, heading ∈ [0, 360).

CSV import: reject duplicates (track_id + timestamp), invalid timestamps, missing fields.

Display actionable error messages suitable for UI toast.

Repo paths touched:

tewa/forms.py (validators)

tewa/api/serializers.py (DRF validators)

tewa/services/csv_import.py (strict mode + report)

tewa/tests/test_validation.py (extend)

Acceptance Criteria:

Bad inputs are blocked with specific error messages; good inputs remain unaffected.

CSV import generates a per-row report for errors (line number + reason).

Task 27 — Performance pass (DB optimization)

Task Name: Performance pass
Sub task: Database Optimization
Sub Sub Task: Add indexes, optimize queries

Description:
Add sensible indexes and query improvements to accelerate Threat Board, Breakdown, and History queries.

Notes (proposed indexes):

TrackSample(track_id, timestamp) (BTREE)

ThreatScore(scenario_id, da_id, track_id, computed_at) (BTREE)

ThreatScore(final_score DESC) via composite index (scenario_id, da_id, final_score DESC) for top-N

Partition or timescale approach (optional phase-2) for very large histories.

Repo paths touched:

tewa/migrations/00xx_add_indexes.py

tewa/services/ranking.py (select_related / prefetch_related)

tewa/services/threat_compute.py (bulk_create, chunking)

tewa/tests/test_performance_smoke.py

Acceptance Criteria:

Threat Board query time improves (document baseline vs. optimized).

EXPLAIN ANALYZE screenshots or text noted in repo /docs/perf/.

No regressions on correctness.

Task 28 — Auth & roles

Task Name: Auth & roles
Sub task: Implement Login
Sub Sub Task: Implement basic user authentication and roles

Description:
Enable login/logout and role-gated access: Admin/Staff can edit parameters and assumptions; Operator can view boards and run compute; Viewer read-only.

Notes:

Use Django auth + DRF Session or Token Auth (document chosen path).

CSRF hardened; secure cookies; password policy; admin MFA (recommended).

Decorators/permissions on sensitive endpoints (assumptions, model params).

Repo paths touched:

missile_model/settings.py (auth backends, CSRF/session config)

tewa/permissions.py (new; DRF permissions)

tewa/api/views.py (guard edit endpoints)

templates/auth/login.html, templates/base.html (login status)

tewa/tests/test_auth_permissions.py

API / Routes (proposed):

POST /api/auth/login/ (if token based) or form login at /login/

Role checks applied to: scenario defaults, model params, CSV import, delete DA/Track.

Acceptance Criteria:

Unauthenticated users cannot access protected endpoints.

Role matrix enforced; tests cover each role/endpoint combo.

Task 29 — Docs & examples

Task Name: Docs & examples
Sub task: README
Sub Sub Task: Write project documentation and usage examples

Description:
Create a top-level README.md and /docs/ notes with formulas, CSV formats, example payloads, testing, and deployment quick start.

Notes (include):

Kinematics formulas (CPA/TCPA/TDB/TWRP) with symbol legend and units.

CSV column spec (sample files in /docs/examples/).

API table (endpoints, params, examples).

“How to run tests”, “How to seed demo data”.

Repo paths touched:

README.md

docs/kinematics.md, docs/api.md, docs/csv.md, docs/perf/, docs/deploy.md

docs/examples/\*.csv

Acceptance Criteria:

New developer can run seed → compute → export in <15 minutes using docs only.

Links between docs are valid (checked via CI lint if available).

Task 30 — Deployment basics

Task Name: Deployment basics
Sub task: Setup Deployment
Sub Sub Task: Configure Gunicorn/Nginx and backup scripts

Description:
Baseline production deployment on a single VM: Gunicorn app server, Nginx reverse proxy/SSL, systemd units, log rotation, and PostgreSQL backup scripts.

Notes:

Gunicorn: workers = CPU\*2+1, timeout 60–120s, health check endpoint.
Nginx: gzip, proxy_read_timeout tuned for CSV export; SSL/TLS 1.2+; HSTS optional.
Backups: nightly pg_dump to dated folder, 7–14 day retention; integrity check.
Environment via .env + SYSTEMD_ENVIRONMENT_FILE.

Repo paths touched:
deploy/gunicorn.service, deploy/nginx.conf (templates)
deploy/env.example
scripts/backup_pg.sh, scripts/restore_pg.sh

docs/deploy.md

tewa/tests/test_healthcheck.py (simple /healthz)

Acceptance Criteria:
systemctl units start cleanly; curl /healthz returns 200.
Nginx serves static files (if enabled) and proxies API.
Successful backup/restore dry run documented in docs/deploy.md.
