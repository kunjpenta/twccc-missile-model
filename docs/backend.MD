TEWA Backend Structure (as of now)

1. Project Root
   missile_model/
   ├─ core/
   ├─ tewa/
   ├─ templates/
   ├─ pg_excel_exports/
   ├─ manage.py
   ├─ readme.MD
   ├─ try.py

core/ – Common utilities, base models, tests, and views not specific to TEWA.

tewa/ – Main TEWA application containing all models, services, APIs, tasks, and management commands.

templates/ – Any Django template files for admin/UI.

pg_excel_exports/ – (Optional) CSV/Excel export utilities.

manage.py – Django management script.

try.py – Miscellaneous script (likely for testing).

2. core/
   core/
   ├─ admin.py
   ├─ apps.py
   ├─ models.py
   ├─ views.py
   ├─ urls.py
   ├─ utils/
   ├─ tests/
   │ ├─ test_kinematics.py
   │ ├─ test_scoring.py
   │ ├─ test_tewa_kinematics.py
   │ ├─ test_units_geodesy.py
   │ └─ quick_check.py

Provides common models, utilities, and test modules used across TEWA.

Tests include:

Kinematics computations (CPA/TCPA/TDB/TWRP)

Threat scoring

Units & geodesy conversions

utils/ – Geodesy, unit conversion, helper functions.

3. missile_model/
   missile_model/
   ├─ settings.py
   ├─ urls.py
   ├─ wsgi.py
   ├─ asgi.py
   ├─ celery.py

Core Django project configuration.

celery.py – Celery app for periodic tasks.

urls.py – Includes global URL patterns and TEWA API routes.

4. tewa/
   tewa/
   ├─ admin.py
   ├─ apps.py
   ├─ models.py
   ├─ serializers.py
   ├─ forms.py
   ├─ views.py
   ├─ urls.py
   ├─ types.py
   ├─ tasks.py
   ├─ services/
   │ ├─ engine.py
   │ ├─ threat_compute.py
   │ ├─ ranking.py
   │ ├─ kinematics.py
   │ ├─ scoring.py
   │ ├─ normalize.py
   │ ├─ sampling.py
   │ └─ csv_import.py
   ├─ management/
   │ └─ commands/
   │ ├─ compute_threats.py
   │ ├─ import_tracks.py
   │ └─ seed_demo.py
   ├─ fixtures/
   │ └─ tewa_seed.json
   ├─ migrations/
   └─ tests/
   ├─ test_api_compute_at.py
   ├─ test_compute_multiple_scenarios.py
   └─ test_csv_import.py

Purpose of Key Directories & Files

models.py – Core TEWA models (DefendedAsset, Track, TrackSample, ThreatScore, Scenario, ModelParams)

serializers.py – DRF serializers for TEWA models.

forms.py – Admin/UI forms, e.g., for DA creation and validation.

urls.py – API routes for TEWA endpoints.

views.py – API views (compute, ranking, DA/Track CRUD).

types.py – Type hinting for ParamsLike and other structures.

tasks.py – Celery tasks for periodic computation.

services/ – Core business logic:

engine.py – Scenario engine to compute scores.

threat_compute.py – Compute and persist threat scores.

ranking.py – Threat ranking logic.

kinematics.py – CPA/TCPA/TDB/TWRP calculations.

scoring.py – Normalization and scoring functions.

normalize.py – Helper math functions (clamp01, inv1).

sampling.py – Track interpolation at specific timestamps.

csv_import.py – CSV import for tracks and TrackSamples.

management/commands/ – Django management commands:

seed_demo.py – Seed sample scenarios, DAs, tracks.

compute_threats.py – Compute all threat scores (manual or periodic).

import_tracks.py – Import tracks from CSV.

fixtures/tewa_seed.json – Initial dataset for demo scenario.

tests/ – Unit tests for API, CSV import, compute engine.

5. APIs & Frontend Hints

/api/tewa/compute_at/ – Compute threat scores at a timestamp.

/api/tewa/compute_now/ – Trigger immediate compute via Celery.

/api/tewa/ranking/ – Get ranked threats (top-N, per-DA optional).

/api/tewa/da/ – CRUD for defended assets.

/api/tewa/track/ – CRUD for tracks.

/api/tewa/tracksample/ – Track sample snapshots.

/api/tewa/score/ – Get persisted ThreatScores.

Data flows:

Track + DA + Scenario → Compute Scores → Persist ThreatScore → Rank Threats → Frontend fetches via /ranking/.

TEWA Backend — Full Technical Overview

1. Project Purpose

The TEWA (Threat Evaluation & Weapon Assignment) backend is a deterministic, high-fidelity simulation engine that computes threat scores for aircraft tracks relative to defended assets (DAs) in various scenarios. Its primary function is:

Track aircraft movement over time.

Compute kinematics-based threat scores (CPA/TCPA/TDB/TWRP) relative to DAs.

Persist results for ranking and historical analysis.

Support automated and periodic computation for training, decision-making, or wargaming applications.

The backend is designed to be agnostic of the frontend, which is Angular-based. The backend exposes RESTful APIs for data access, CSV uploads, computation requests, and threat rankings.

2. Tech Stack
   Layer Technology / Library Role
   Backend Python 3.10, Django 5.1.x Web framework, ORM, management commands
   Database PostgreSQL (+ PostGIS optional) Stores scenarios, DAs, tracks, track samples, model parameters, and threat scores
   Asynchronous Tasks Celery (optional) Scheduled periodic computation (e.g., hourly updates)
   Serialization / API Django REST Framework style JSON-based REST endpoints for frontend integration
   Time & Dates UTC everywhere, ISO8601 Ensures consistent computation and timestamping
3. Project Structure
   missile_model/
   ├─ manage.py
   ├─ missile_model/
   │ ├─ settings.py # Django settings, DB config, timezone = UTC
   │ ├─ urls.py # Root URLs, includes /api/tewa/
   │ ├─ celery.py # Celery app definition
   ├─ core/ # Utilities and test modules
   │ ├─ utils/
   │ │ ├─ geodesy.py # Distance, bearing, ENU conversions
   │ │ └─ units.py # Unit conversions: m/s, km, etc.
   │ └─ tests/ # Unit tests for kinematics, scoring, conversions
   └─ tewa/
   ├─ models.py # Core models: Scenario, Track, TrackSample, DA, ModelParams, ThreatScore
   ├─ serializers.py # DRF serializers for API endpoints
   ├─ api/
   │ ├─ views.py # API endpoints: compute_now, compute_at, score, ranking, upload_tracks
   │ └─ urls.py
   ├─ services/
   │ ├─ kinematics.py # CPA, TCPA, TDB, TWRP computations
   │ ├─ normalize.py # Normalization functions (inv1, clamp01)
   │ ├─ scoring.py # Weighting & final threat score calculation
   │ ├─ threat_compute.py # Computes & persists ThreatScore for tracks × DAs
   │ ├─ engine.py # Time-aware compute engine
   │ ├─ sampling.py # Interpolates TrackSamples (linear/latest)
   │ └─ csv_import.py # Robust CSV importer (tz-aware)
   ├─ management/commands/
   │ ├─ seed_demo.py # Seeds scenarios, tracks, DAs, model params
   │ ├─ import_tracks.py
   │ └─ compute_threats.py # Periodic threat score computation
   └─ fixtures/tewa_seed.json # Default seed data

4. Data Model Overview
   Model Purpose Key Fields
   Scenario Represents a TEWA simulation scenario name, start_time, end_time, notes
   DefendedAsset (DA) Represents a fixed defended location name, lat, lon, radius_km
   Track Represents an aircraft / moving object track_id, lat, lon, alt_m, speed_mps, heading_deg, scenario
   TrackSample Snapshot of Track at a specific time track, t (timestamp), lat, lon, alt_m, speed_mps, heading_deg
   ModelParams Scenario-specific scoring weights & normalization w_cpa, w_tcpa, w_tdb, w_twrp, cpa_scale_km, etc.
   ThreatScore Persisted threat score per (Track × DA × Scenario) track, da, scenario, score, computed_at, raw_components

Key Features:

Indexes exist on track_id, scenario, da to optimize queries.

Timestamps are always UTC-aware; frontend passes ISO8601 strings with Z.

5. CSV Upload Pipeline

Purpose: Bulk import tracks and samples.

API Endpoint: POST /api/tewa/upload_tracks/

CSV Format Required:

track_id,lat,lon,alt_m,speed_mps,heading_deg,timestamp

Backend Workflow:

CSV is read line by line (csv.DictReader).

Timestamps are parsed via \_parse_ts_aware_utc() → UTC-aware datetimes.

Track: created if not exists (unique per scenario + track_id).

TrackSample: created for each row.

Latest track snapshot updated for real-time compute.

Returns summary JSON:

{
"message":"Upload processed",
"tracks_created":3,
"samples_created":3,
"errors":[]
}

6. Kinematics & Threat Scoring
   CPA/TCPA/TDB/TWRP

CPA: Closest point of approach (distance to DA).

TCPA: Time to CPA (seconds).

TDB: Distance to DA boundary circle.

TWRP: Time to weapon release (based on weapon range).

Normalization

normalize.inv1(x, scale) → 1 / (1 + x/scale)

Values are clamped [0,1].

Negative TCPA (past events) is down-weighted.

Scoring

Weighted sum of normalized CPA, TCPA, TDB, TWRP using ModelParams.

Result persisted in ThreatScore.

7. Compute Engine (engine.py)

Input: Scenario, timestamp (when), method (linear/latest), optional DAs.

Steps:

Interpolate TrackSamples to requested time.

Compute kinematics for each Track × DA pair.

Normalize and weight using ModelParams.

Persist ThreatScore.

Output: Threats ready for ranking or historical view.

API Exposure:

POST /compute_now/ → current snapshot computation.

POST /compute_at/ → timestamped computation.

GET /score/ → list persisted scores (filterable).

GET /ranking/ → top-N threats per scenario.

8. Periodic Threat Computation

Implemented as management command: compute_threats.py.

Loops through all active scenarios.

Computes ThreatScore for each scenario using the two constant DAs (DA-Alpha, DA-Bravo).

Optional integration with Celery Beat for hourly/daily scheduled computation.

9. Data Flow
   [Frontend] ---> [Django API] ---> [Database]
   Upload CSV POST /upload_tracks Insert Tracks/TrackSamples
   Compute Now POST /compute_now Calculate ThreatScore & persist
   Compute At POST /compute_at Interpolate + Compute + Persist
   Fetch Ranking GET /ranking Fetch top-N ThreatScore per scenario

Internal Flow (Compute):

TrackSamples → interpolated to requested timestamp

Kinematics → CPA/TCPA/TDB/TWRP

Normalize & Weight → ThreatScore

Persist → DB for frontend query

10. Fixtures & Seed Data

tewa/fixtures/tewa_seed.json contains:

3 Scenarios (Demo-Scenario, Scenario-2, Scenario-3)

2 constant DAs (DA-Alpha, DA-Bravo)

Tracks & TrackSamples for each scenario

ModelParams for scoring

Benefit: Running loaddata instantly seeds backend with functional data.

11. Best Practices Implemented

Timezone-safe: all timestamps UTC-aware, frontend sends ISO8601-Z.

Deterministic: fixed kinematics, fixed DAs → reproducible threat scores.

Idempotent seed: loading fixture multiple times doesn’t duplicate tracks/DA.

Indexes: optimized queries for scenario × DA × track.

Unit-tested: CSV import, kinematics, scoring, geodesy conversions.

12. Outstanding / Next Features

Pagination and filtering on /score/.

Optional scenario-scoped DA lists (/scenarios/{id}/das/).

Celery Beat integration for fully automated periodic computation.

Optional “calculate_scores” endpoint for pure compute without persistence.

Enhanced CSV error reporting (row-level messages).

✅ Summary

The backend is fully operational:

Tracks, track samples, scenarios, DAs are seeded and persisted.

Threat computation is deterministic, reproducible, and logged.

APIs support upload, compute, and ranking.

Ready for frontend integration or periodic automated execution.
