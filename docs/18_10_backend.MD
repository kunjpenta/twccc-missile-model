TEWA (Threat Evaluation & Weapon Assignment)
Backend Developer Guide (v1)

Last updated: 2025-10-18
Audience: Backend engineers & operators taking over TEWA
Scope: Deterministic threat scoring (CPA, TCPA, TDB, TWRP), authoritative data store, CSV ingest, on-demand/periodic compute, and ranking APIs. Angular/UI is out of scope—this is the backend contract & behavior.

0. Service Guarantees

Deterministic, per-timestamp Track × DefendedAsset (DA) scoring using CPA, TCPA, TDB, TWRP.

Authoritative storage for Scenario, DefendedAsset, Track, TrackSample, ModelParams, ThreatScore.

Robust CSV ingest of TrackSamples; idempotency via DB constraints.

Synchronous compute endpoints (dev scale). Async/periodic via Celery planned.

Stable HTTP contracts under /api/tewa/.

UTC everywhere. API accepts TZ-aware ISO-8601, normalizes to UTC.

1. Stack & Repo Layout

Runtime: Python 3.10+, Django 5.1+, DRF, PostgreSQL (PostGIS optional), Celery (optional).

missile_model/
├─ manage.py
├─ missile_model/ # settings.py | urls.py | asgi/wsgi.py | celery.py
├─ core/
│ ├─ utils/
│ │ ├─ units.py # conversions
│ │ └─ geodesy.py # haversine, ENU mapping
│ └─ tests/ # kinematics, scoring, geodesy
└─ tewa/
├─ models.py # Scenario, DA, Track, TrackSample, ModelParams, ThreatScore
├─ admin.py | serializers.py | urls.py | views.py | tasks.py
├─ services/
│ ├─ engine.py # time-aware compute orchestration
│ ├─ kinematics.py # CPA/TCPA/TDB/TWRP (ENU frame)
│ ├─ normalize.py # clamp01, inv1(), exp()
│ ├─ scoring.py # normalization + weighted score
│ ├─ threat_compute.py # per-track/DA compute + persistence
│ ├─ sampling.py # linear/latest sampling
│ └─ csv_import.py # CSV importer (tz-aware)
├─ management/commands/ # seed_demo.py | import_tracks.py | compute_threats.py
├─ fixtures/tewa_seed.json
└─ tests/

2. Data Model (DB Truth)

WGS84 lat/lon; UTC timestamps (timestamptz).

Uniqueness & indexes enforce idempotency and query speed.

Entity Key fields Notes
Scenario id, name, start_time?, end_time?, notes? Container for DAs/Tracks/params.
DefendedAsset id, scenario_id, name, lat, lon, radius_km Validate: lat ∈ [−90,90], lon ∈ [−180,180], 0 < radius_km ≤ 1000.
Track id, scenario_id, track_id Unique (scenario_id, track_id). Optional snapshot fields.
TrackSample id, track_id, t, lat, lon, alt_m, speed_mps, heading_deg Unique (track_id, t). Index (track_id, t).
ModelParams scenario_id (unique FK), weights & scales, flags w_cpa, w_tcpa, w_tdb, w_twrp; cpa_scale_km, tcpa_scale_s, tdb_scale_km, twrp_scale_s; clamp_0_1.
ThreatScore id, scenario_id, da_id, track_id, computed_at, components, score Unique (scenario_id, da_id, track_id, computed_at). Indexes for ranking & time-series.

Integrity: unique (scenario_id, track_id) and (track_id, t); all times stored as UTC.

3. Threat Math (Server Behavior)

Frames: coarse gating via haversine; precision in local ENU per DA/Track.

CPA/TCPA:

r0 = p_track − p_DA (ENU), v = v_track.

tcpa = − dot(r0, v) / ||v||² (if ||v|| ≈ 0 → +∞).

d_cpa = || r0 + v \* tcpa ||. tcpa < 0 ⇒ CPA passed → down-weight.

TDB (to DA boundary): quadratic for first positive root of || r0 + v t || = R_DA. No positive root while closing ⇒ +∞.

TWRP (to release ring): same as TDB with R_release = R_DA + weapon_range_km.

Normalization (configurable):
Default (exponential):

n_cpa = exp(− d_cpa_km / cpa_scale_km)
n_tcpa = exp(− max(tcpa_s,0) / tcpa_scale_s)
n_tdb = 1.0 if tdb_s ≤ 0 else exp(− tdb_km / tdb_scale_km)
n_twrp = exp(− max(twrp_s,0) / twrp_scale_s)

Alternative: inv1(x, σ) = 1 / (1 + x/σ).

Weighted score:

score = (w_cpa*n_cpa + w_tcpa*n_tcpa + w_tdb*n_tdb + w_twrp*n_twrp) / (w_cpa + w_tcpa + w_tdb + w_twrp)
if clamp_0_1: score, components ∈ [0,1]

Edge cases: stationary track; inside DA (tdb=0), negative tcpa; numeric guards; missing fields → row error.

4. API Contracts (Stable)

Base: /api/tewa/ (JSON; multipart for uploads).
Auth: none in dev; JWT planned.

4.1 Health & Lists

GET /health → { "status": "ok" }

GET /scenarios/ → list scenarios

4.2 Defended Assets

GET/POST/PATCH/DELETE /da/ (canonical; keep /defendedassets/ or /das/ read-only during deprecation)

4.3 Tracks & Samples

GET /tracks/?scenario_id=1

GET /tracksamples/?track_id=T1&from=...&to=...

4.4 CSV Upload (TrackSamples)

POST /upload_tracks/ (multipart)
Fields: file, scenario_id
CSV header (required): track_id,lat,lon,alt_m,speed_mps,heading_deg,timestamp
Response:

{"message":"ok","tracks_created":3,"samples_created":120,"rows_processed":120,"errors":[]}

CSV Validation & Failure Modes

Header/column count bad → 400.

Row validation errors → 200 with errors[] and success counts.

Constraints: lat∈[−90,90], lon∈[−180,180], alt_m ≥ −500, speed_mps ≥ 0, heading_deg∈[0,360), non-empty track_id, timestamp ISO-UTC (Z).

4.5 Compute

POST /compute_now/
Body: {"scenario_id":1,"da_id":null,"weapon_range_km":20}

POST /compute_at/
Body:

{
"scenario_id":1,
"when":"2025-10-14T07:38:00Z",
"da_ids":[1,2],
"method":"linear", // or "latest"
"weapon_range_km":20
}

Compute Semantics

HTTP 200 means computation finished & persisted.

After success, re-fetch /ranking/ (and/or /score/) to reflect fresh values.

Current scale: a short UI spinner is enough (no long polling necessary).

4.6 Ranking & Scores

GET /ranking/?scenario_id=1&top_n=10[&da_id=2]
Returns grouped results by DA; includes computed_at (UTC). Supports ETag; send If-None-Match for cheap polling (5–10 s).

GET /score/?... (optional flat feed; add pagination/ordering only if/when needed)

4.7 Score Breakdown (per-threat explain)

GET /score_breakdown?scenario_id=1&track_id=T1&da_id=3[&at=ISO-UTC] (no trailing slash)
track_id accepts PK or public string. Returns metrics, normalized, weights, contributions, final score, computed_at. If compute isn’t reconstructable, returns legacy flat fields from latest persisted row.

Example:

{
"scenario_id":1, "track_id":"TGT001", "da_id":3, "computed_at":"2025-10-14T10:02:00Z",
"metrics":{"cpa_m":1234.5,"tcpa_s":67.8,"tdb_s":90.2,"twrp_s":12.0},
"normalized":{"cpa":0.82,"tcpa":0.61,"tdb":0.34,"twrp":0.74},
"weights":{"cpa":0.35,"tcpa":0.25,"tdb":0.20,"twrp":0.20},
"contributions":{"cpa":0.287,"tcpa":0.153,"tdb":0.068,"twrp":0.148},
"score":0.656, "total_score":0.656,
"params":{},
"explain":[
"Lower CPA → higher normalized threat (inverted scale).",
"Shorter TCPA → higher immediacy risk.",
"TDB gauges time to DA boundary penetration.",
"TWRP indicates time to weapon release window."
],
"cpa_km":1.2345,"tcpa_s":67.8,"tdb_km":0.0902,"twrp_s":12.0
}

4.8 Error Shapes (DRF)

Generic: {"detail":"Not found."}

Field errors: {"lat":["Ensure this value is less than or equal to 90."]}

Frontend rule: prefer detail; else join the first field’s error strings. For uploads, display the full errors[] list.

5. UI Empty States (for reference)

Tracks: “No tracks yet. Upload CSV to begin.”

Ranking: “No scores. Click Compute Now.”

Errors: prefer DRF detail; else first field error; for uploads show every item in errors[].

6. Sorting, Paging, Polling (current phase)

Lists are small; backend returns full arrays.

If you need paging/sorting, add DRF pagination/ordering (?ordering=...&page=...&page_size=...).

Optional polling /ranking/ every 5–10 s for live dashboards (use ETag).

7. Compute Engine & Sampling (flow)
   engine.compute_at(scenario, when, method, da_filter, weapon_range_km):
   samples = fetch samples around `when`
   state = sample(method): - linear: interpolate between bracketing samples - latest: last sample at/≤ when
   for each DA:
   for each Track state:
   components = kinematics(state, DA, weapon_range_km)
   score = scoring(components, ModelParams)
   persist ThreatScore(...)

compute_now uses Track snapshots that ingest updates.

8. Performance & Indexing

Bulk ingest: stream → bulk_create (5–10k batches).

Indexes:

Track(scenario_id, track_id) unique

TrackSample(track_id, t) unique + index on t

ThreatScore(scenario_id, da_id, score DESC) + computed_at

Short-circuiting: coarse range gate by weapon_range_km / DA circle before ENU math.

Retention: ThreatScore is time-series—consider partitioning/pruning.

9. Time & Timezone Policy

API accepts TZ-aware ISO-8601 (e.g., +05:30) or Z.

DB + compute persist UTC; responses return ISO-UTC (...Z).

Naive timestamps in CSV are treated as UTC by importer (prefer explicit Z).

10. Security & Ops

Dev: open on localhost; permissive CORS behind Angular proxy.

Next: JWT (SimpleJWT)—viewer (ranking), operator (compute), admin (DA CRUD).

Restrict CORS in prod; throttle compute\_\*.

Health: /api/health; consider /ready for readiness.

11. CLI / Batch

# Compute threats (now or at timestamp)

python manage.py compute_threats [--scenario_id N] [--timestamp ISO] [--weapon_range_km X]

# Import tracks from CSV

python manage.py import_tracks --scenario_id 1 --file /path/to/tracks.csv

# Seed demo data

python manage.py seed_demo

12. Dev Setup & Quickstart
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    createdb tewa
    python manage.py migrate
    python manage.py seed_demo # optional
    python manage.py runserver

Smoke test:

curl -s http://127.0.0.1:8000/api/tewa/scenarios/

13. Testing (Essentials)

Upload: valid CSV (with Z) → 201; counts correct; errors[] empty.

Naive timestamps: accepted; normalized to UTC.

Duplicate (track_id,t): rejected if unique enforced (or de-duped by policy).

Compute now/at: persists ThreatScore; ranking non-empty.

Sampling: linear within bounds; latest uses last ≤ when.

Negative TCPA: contribution down-weighted.

Ranking: ordered by score DESC; top_n respected; ETag stable if content unchanged.

14. Observability

Logs: API boundary; compute start/finish with scenario/when/counts.

Metrics (future): compute duration histogram; samples/sec; ingest error counter.

Tracing (future): OpenTelemetry around engine.compute_at.

15. Frontend Contract (What We Promise)

Stable response shapes; deterministic ordering by score desc, then track_id asc.

computed_at is ISO-UTC.

ETag on /ranking/ to enable 304 on polling.

16. Roadmap (Backend-Owned)

/calculate_scores/ — non-persisting compute (what-ifs).

Celery Beat periodic compute; /compute\_\* can 202 + job id.

DA UI & validation hardening (0 < radius_km ≤ 1000).

/score export: pagination + CSV renderer.

Upload error surfacing: richer row-level details.

Idempotent ingest: unique (track_id, t) + ON CONFLICT DO NOTHING.

Canonicalize /da/; keep legacy aliases read-only during migration.

17. Troubleshooting

Empty Ranking: run compute_now/compute_at; verify ModelParams exist.

Datetime warnings: check importer & \_parse_ts_aware_utc().

CSV 400: header mismatch or wrong count—must match required header exactly.

200 with errors[]: show all row errors; partial success persisted.

UI blanks (FYI): Angular routes/Leaflet CSS order—frontend concern.

18. Examples (Copy/Paste)

Sample CSV

track_id,lat,lon,alt_m,speed_mps,heading_deg,timestamp
T1,12.9716,77.5946,1500,220,045,2025-09-30T06:05:00Z
T1,12.9800,77.6000,1500,220,045,2025-09-30T06:06:00Z
T2,13.0000,77.6200,2000,250,030,2025-09-30T06:05:30Z

cURL Quickstarts

# Upload tracks

curl -F "file=@/path/to/tracks.csv" -F "scenario_id=1" \
 http://127.0.0.1:8000/api/tewa/upload_tracks/

# Compute now

curl -X POST -H 'Content-Type: application/json' \
 -d '{"scenario_id":1, "weapon_range_km":20}' \
 http://127.0.0.1:8000/api/tewa/compute_now/

# Compute at time (linear, 2 DAs)

curl -X POST -H 'Content-Type: application/json' \
 -d '{"scenario_id":1,"when":"2025-09-30T06:07:30Z","da_ids":[1,2],"method":"linear","weapon_range_km":20}' \
 http://127.0.0.1:8000/api/tewa/compute_at/

# Ranking (top 10) with ETag

ETAG=$(curl -sI "http://127.0.0.1:8000/api/tewa/ranking/?scenario_id=1&top_n=10" | sed -n 's/^ETag: //p' | tr -d '\r')
curl -s -H "If-None-Match: $ETAG" "http://127.0.0.1:8000/api/tewa/ranking/?scenario_id=1&top_n=10" -i

19. Minimal DRF Skeleton (Reference Only)

# tewa/api/views.py

class ScenarioViewSet(ReadOnlyModelViewSet):
queryset = Scenario.objects.all()
serializer_class = ScenarioSerializer

@api_view(["POST"]) # /upload_tracks/
def upload_tracks(request):
scenario_id = int(request.POST.get("scenario_id", 0))
csv_file = request.FILES.get("file")
summary = import_csv_to_tracks(scenario_id, csv_file)
return Response({"status": "ok", \*\*summary}, status=201)

@api_view(["POST"]) # /compute_now/
def compute_now(request):
scenario_id = request.data.get("scenario_id")
weapon_range_km = float(request.data.get("weapon_range_km", 0))
payload = engine.compute_at(scenario_id, timezone.now(),
method="latest", da_filter=None,
weapon_range_km=weapon_range_km)
return Response({"status": "computed", \*\*payload})

@api_view(["GET"]) # /ranking/
def ranking(request):
scenario_id = int(request.GET.get("scenario_id"))
top_n = int(request.GET.get("top_n", 10))
payload, etag = build_ranking_payload(scenario_id, top_n)
if request.headers.get("If-None-Match") == etag:
return Response(status=304)
resp = Response(payload)
resp["ETag"] = etag
return resp

20. Owner Knobs (Fast Tweaks)

# Tune model parameters

python manage.py shell -c "from tewa.models import ModelParams; mp=ModelParams.objects.get(scenario_id=1); \
mp.cpa_scale_km=300; mp.tcpa_scale_s=600; mp.tdb_scale_km=50; mp.twrp_scale_s=1200; \
mp.w_cpa=mp.w_tcpa=mp.w_tdb=mp.w_twrp=0.25; mp.clamp_0_1=True; mp.save(); print('OK')"

# Recompute & verify

python manage.py compute_threats --scenario_id 1
curl -s 'http://127.0.0.1:8000/api/tewa/ranking/?scenario_id=1&top_n=10'

Canonical paths: Prefer /da/ for Defended Assets. Keep /defendedassets/ and /das/ read-only until clients migrate.
