# TEWA — Threat Evaluation & Weapon Assignment (Backend)

Backend service for computing threat scores between **Tracks** and **Defended Assets (DAs)** across **Scenarios**.

**Stack:** Python 3.10+, **Django 5** + **DRF**, **PostgreSQL 14+**
**Apps:** `core` (utils), `tewa` (domain, services, API)

---

## Contents
- [Features](#features)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [Data Model](#data-model)
- [Kinematics & Scoring](#kinematics--scoring)
- [CSV Formats](#csv-formats)
- [API Usage](#api-usage)
- [Management Commands](#management-commands)
- [Server-Side Charts](#server-side-charts)
- [Testing](#testing)
- [Repo Layout](#repo-layout)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Features
- Deterministic kinematics: **CPA**, **TCPA**, **TDB**, **TWRP**
- Per-metric **normalization** and **weighted** composite scoring
- Scenario engine for batch compute & ranking
- CSV import for tracks; export for boards
- Minimal HTML for early UI; **API-first** design
- **Admin-editable** model parameters (staff-only)
- Input validation & **performance indexes**

---

## Quickstart

### 1) Prereqs
- Python **3.10+**
- PostgreSQL **14+**
- `virtualenv` (recommended)

### 2) Clone & Install
```bash
git clone https://github.com/<org>/missile_model.git
cd missile_model
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
3) Configure DB & Env
Create a database (example):

sql
Copy code
CREATE DATABASE missile_db;
CREATE USER missile_user WITH ENCRYPTED PASSWORD 'change-me';
GRANT ALL PRIVILEGES ON DATABASE missile_db TO missile_user;
Create .env (or export env vars):

bash
Copy code
# .env (for django-environ or similar) — change values for your setup
DATABASE_URL=postgres://missile_user:change-me@127.0.0.1:5432/missile_db
DJANGO_SETTINGS_MODULE=missile_model.settings
DJANGO_SECRET_KEY=dev-secret-change-me
DEBUG=1
ALLOWED_HOSTS=127.0.0.1,localhost
4) Migrate & Seed
bash
Copy code
python manage.py migrate
python manage.py loaddata tewa/fixtures/tewa_seed.json   # if available
python manage.py seed_demo                               # demo scenario, DAs, tracks
5) Run Server
bash
Copy code
python manage.py runserver
# http://127.0.0.1:8000/
Configuration
Key settings live in missile_model/settings.py.

DATABASES: auto-configured from DATABASE_URL if present

INSTALLED_APPS: includes tewa, core

REST_FRAMEWORK: DRF config (pagination, renderer, etc.)

TEMPLATES: minimal HTML pages under templates/

Environment variables (dev):

bash
Copy code
export DATABASE_URL=postgres://missile_user:change-me@127.0.0.1:5432/missile_db
export DJANGO_SECRET_KEY=dev-secret-change-me
export DJANGO_SETTINGS_MODULE=missile_model.settings
export DEBUG=1
export ALLOWED_HOSTS=127.0.0.1,localhost
Optional:

CORS_ALLOWED_ORIGINS=http://localhost:4200 (Angular dev)

TIME_ZONE=UTC (default)

Data Model
Core entities (simplified):

Model	Purpose	Key Fields (examples)
Scenario	Time-bounded container for compute runs	name, start_time, end_time, notes
DefendedAsset	Protected point + radius	name, lat, lon, radius_m, scenario
Track	Logical identity of a moving object	track_id (str), scenario
TrackSample	Time-series state of a Track	track, ts (ISO UTC), lat, lon, alt_m, speed_mps, heading_deg
ThreatScore	Result per (Scenario, DA, Track, time)	scenario, da, track, computed_at, raw & normalized metrics, score
ModelParams	Tunable weights & ranges	w_cpa, w_tcpa, w_tdb, w_twrp, R_DA_m, R_W_m, bounds/sigmas

Admin can manage ModelParams (staff-only). Add DB indexes exist on hot paths (e.g., TrackSample(ts), ThreatScore(computed_at)).

Kinematics & Scoring
Conventions

Units: meters (m), seconds (s), radians (rad) unless noted

Positions: geodetic (lat, lon, alt) → local ENU for planar calcs

Velocity: ground speed (m/s) with course (deg)

Let:

r = relative position vector track − DA (ENU at time t0)

v = relative velocity vector (track w.r.t. DA; DA static in v0)

‖·‖ = Euclidean norm, · = dot product

TCPA (Time to Closest Point of Approach)

ini
Copy code
t_cpa = - (r · v) / ‖v‖²     (clamp to [0, +∞) for forward-only)
CPA distance

ini
Copy code
d_cpa = ‖ r + v * t_cpa ‖
TDB (Time to DA Boundary, radius R_DA)

Solve ‖ r + v t ‖² = R_DA² with:

makefile
Copy code
a = ‖v‖²
b = 2 (r · v)
c = ‖r‖² - R_DA²
Δ = b² - 4ac
Smallest non-negative root → TDB; none if Δ < 0.

TWRP (Time to Weapon Release/Range, radius R_W)

Same quadratic as TDB, replacing R_DA with R_W.

Normalization (examples)

Distance-like (smaller is worse):

ini
Copy code
n_d = 1 - min(d, D_max) / D_max   ∈ [0,1]
Time-like (sooner is worse):

ini
Copy code
n_t = 1 - min(t, T_max) / T_max   ∈ [0,1]
(Choose bounds per scenario or via σ-like tunables.)

Final Score (weights sum to 1)

ini
Copy code
score = w_cpa*n_cpa + w_tcpa*n_tcpa + w_tdb*n_tdb + w_twrp*n_twrp
Implementation locations:

tewa/services/kinematics.py

tewa/services/normalize.py

tewa/services/scoring.py

CSV Formats
Tracks CSV (tracks.csv)
Header:

Copy code
track_id,scenario_name,ts,lat,lon,alt_m,ground_speed_mps,course_deg
Example rows:

makefile
Copy code
T-001,Demo-Scenario,2025-10-01T10:00:00Z,23.0359,72.5850,1500,220,45
T-001,Demo-Scenario,2025-10-01T10:00:05Z,23.0365,72.5857,1500,220,45
T-002,Demo-Scenario,2025-10-01T10:00:00Z,23.1200,72.6000,2000,250,10
Rules

ts: ISO-8601 UTC (YYYY-MM-DDTHH:MM:SSZ)

lat ∈ [-90,90], lon ∈ [-180,180], alt_m ≥ 0

Monotonic ts per (scenario_name, track_id)

De-dup keyed by (track_id, ts)

Import via API

bash
Copy code
curl -F "file=@tracks.csv" \
     "http://127.0.0.1:8000/api/tewa/upload_tracks/?scenario_id=1"
API Usage
Base: http://127.0.0.1:8000

Health
bash
Copy code
curl http://127.0.0.1:8000/api/tewa/ping
List Scenarios / DAs
bash
Copy code
curl http://127.0.0.1:8000/api/tewa/scenarios/
curl http://127.0.0.1:8000/api/tewa/da/
Compute Threats (Now)
bash
Copy code
curl -X POST http://127.0.0.1:8000/api/tewa/compute_now/ \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": 1, "at": "2025-10-01T10:00:05Z"}'
Ranking (Global or per-DA)
bash
Copy code
curl "http://127.0.0.1:8000/api/tewa/ranking/?scenario_id=1&top_n=10"
curl "http://127.0.0.1:8000/api/tewa/ranking/?scenario_id=1&da_id=2&top_n=10"
Response (example):

json
Copy code
[
  {
    "track_id": "T-001",
    "da_id": 2,
    "score": 0.842,
    "metrics": { "cpa_m": 1540.2, "tcpa_s": 23.5, "tdb_s": 41.7, "twrp_s": 12.1 },
    "timestamp": "2025-10-01T10:00:05Z"
  }
]
Score Breakdown (both paths supported)
bash
Copy code
curl "http://127.0.0.1:8000/api/tewa/score-breakdown?scenario_id=1&da_id=2&track_id=T-001"
# or
curl "http://127.0.0.1:8000/api/tewa/score_breakdown/?scenario_id=1&da_id=2&track_id=T-001"
Scenario Params (read/update)
bash
Copy code
# read
curl "http://127.0.0.1:8000/api/tewa/scenarios/1/params/"

# update (weights must sum to 1)
curl -X PATCH "http://127.0.0.1:8000/api/tewa/scenarios/1/params/" \
  -H "Content-Type: application/json" \
  -d '{
        "R_W_m": 45000, "R_DA_m": 8000, "tick_s": 1.0,
        "w_cpa": 0.25, "w_tcpa": 0.25, "w_tdb": 0.25, "w_twrp": 0.25
      }'
Management Commands
Batch Compute
bash
Copy code
python manage.py compute_threats --scenario 1 --at 2025-10-01T10:00:05Z
Seed Demo
bash
Copy code
python manage.py seed_demo
Import Tracks (CLI)
bash
Copy code
python manage.py import_tracks --file ./docs/examples/tracks.csv --scenario "Demo-Scenario"
Server-Side Charts
Score history PNG for (scenario_id, da_id, track_id):

bash
Copy code
open "http://127.0.0.1:8000/api/tewa/charts/score_history.png?scenario_id=1&da_id=1&track_id=T-001&width=800&height=300&smooth=3"
# Content-Type: image/png
Optional query params: from, to (ISO), width, height, smooth.

Uses Matplotlib Agg backend; no GUI required.

Testing
Run unit & integration tests:

bash
Copy code
pytest -q
pytest -v tewa/tests/test_validation.py
pytest -v tewa/tests/test_ranking.py
pytest -v tewa/tests/test_compute_threats.py
Coverage (optional):

bash
Copy code
pytest --cov=tewa --cov=core
Lint (if configured):

bash
Copy code
flake8 tewa core
Repo Layout
bash
Copy code
missile_model/
├─ manage.py
├─ requirements.txt
├─ pytest.ini
├─ missile_model/
│  ├─ __init__.py  settings.py  urls.py  asgi.py  wsgi.py
│  └─ static/favicon.ico
├─ core/
│  ├─ utils/ (geodesy.py, units.py, utils.py)
│  └─ tests/
├─ tewa/
│  ├─ models.py  serializers.py  views.py  urls.py  forms.py
│  ├─ services/
│  │  ├─ kinematics.py  normalize.py  scoring.py
│  │  ├─ engine.py  threat_compute.py  ranking.py
│  │  ├─ score_breakdown.py  export_csv.py  csv_import.py
│  │  ├─ score_history.py  charting.py
│  ├─ api/ (DRF endpoints: urls.py, views_*.py)
│  ├─ fixtures/tewa_seed.json
│  ├─ management/commands/ (seed_demo, import_tracks, compute_threats)
│  └─ tests/
├─ templates/
│  ├─ base.html  home.html
│  └─ components/ boards/ scenarios/
└─ docs/ (examples, diagrams)
Troubleshooting
Issue	Possible Cause	Fix
DB connection errors	Wrong DATABASE_URL, Postgres not running, no privileges	Verify .env, credentials, and systemctl status postgresql; re-migrate
Migrations mismatch	Local model changes vs DB	python manage.py makemigrations && python manage.py migrate
CSV 400/422	Missing headers, invalid ts/coords	Match schema; ts ISO-8601 Z; lat/lon bounds; no empty cells
No scores computed	Missing data or wrong compute time	Ensure Scenario + DA + TrackSample exist for --at; check ModelParams
Weights invalid	Sum ≠ 1 or bad ranges	Ensure w_* sum to 1; R_DA_m > 0, R_W_m > R_DA_m, tick_s > 0
Matplotlib/Agg error	Missing deps	Ensure matplotlib installed by requirements.txt
CORS with Angular	Browser blocked	Add http://localhost:4200 to CORS_ALLOWED_ORIGINS

Contributing
Create a feature branch.

Add/adjust tests.

pytest -q (all green).

Open PR with summary and any perf notes.

Keep API & CSV docs in sync (update README when endpoints change).

License
Internal / project-specific. Add your license text or link here.

Appendix: Handy Admin

bash
Copy code
# Create superuser (Django admin)
python manage.py createsuperuser

# Dump demo data snapshot
python manage.py dumpdata tewa --indent 2 > docs/tewa_dump.json

# Import all CSVs in a folder
for f in ./docs/examples/*.csv; do \
  python manage.py import_tracks --file "$f" --scenario "Demo-Scenario"; \
done
