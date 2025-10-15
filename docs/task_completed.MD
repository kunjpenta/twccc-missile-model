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
Description: Connect Django to PostgreSQL, configure DATABASE*URL, and create/verify initial migrations.
Notes: Basic DB setup; ensure psycopg is installed and environment variables are loaded correctly.
Repo paths touched: missile_model/settings.py, tewa/migrations/*, core/migrations/\_, missile_db.sql

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
├─ readme.MD
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

This completes Tasks 11–20, matching the style and level of detail from Tasks 1–10.

You can hand this document to your frontend developers or AI teammate as a ready reference for API integration, HTML/CSS testing, and database access.
