Missile Model / TEWA — Progress & Reference (as of 2025-09-30)

1. Project overview

We’re building a TEWA (Threat Evaluation & Weapon Assignment) backend in Python + Django + PostgreSQL that scores airborne tracks against defended assets (DAs) using deterministic, kinematics-only threat models inspired by Heyns & Van Vuuren (2010).

Core idea

Compute a per-(track, DA) threat score using:

CPA (Closest Point of Approach)

TCPA (Time to CPA)

TDB (distance to DA center, used as a spatial urgency proxy)

TWRP (time to reach weapon release range)

Then normalize/weight these into a 0–1 threat score.

2. Environment & scaffold

Django project created; admin and a minimal API root live.

PostgreSQL configured (via DATABASE_URL / settings).

Admin superuser created.

Health endpoint: /api/health returns 200.

Useful CLIs

# runserver

python manage.py runserver

# admin superuser

python manage.py createsuperuser

# migrations

python manage.py makemigrations
python manage.py migrate

# tests

python manage.py test -v 2

3. Data model (tewa app)

Key models (selected fields):

Scenario

name, start_time, end_time, notes

timestamps: created_at, updated_at

DefendedAsset

name, lat, lon, radius_km

constraints: radius_km >= 0

index on name

Track

belongs to Scenario

track_id, lat, lon, alt_m, speed_mps, heading_deg

timestamps: created_at, updated_at

indexes on (scenario, track_id) and (lat, lon)

TrackSample

belongs to Track

t (timestamp), lat, lon, alt_m, speed_mps, heading_deg

indexes: (track, t) and (lat, lon)

ModelParams

one per Scenario (created if missing)

weights: w_cpa, w_tcpa, w_tdb, w_twrp (constrained 0..1)

scales: cpa_scale_km, tcpa_scale_s, tdb_scale_km, twrp_scale_s (>0)

clamp_0_1 boolean

ThreatScore

belongs to Scenario, Track, DefendedAsset

raw components: cpa_km, tcpa_s, tdb_km, twrp_s

score in [0,1] (by default we clamp)

indexes to query by (scenario, da, computed_at) & (scenario, track, computed_at)

4. Units & geodesy baseline (core/utils)

core/utils/units.py

distance: m↔km↔nm, m↔ft

speed: m/s↔kt↔km/h

angles: deg↔rad, wrap helpers

core/utils/geodesy.py

WGS-84 constants

Haversine distance (spherical mean radius)

Initial bearing (forward azimuth)

Destination point along great circle

Local ENU small-angle mapping (lat/lon ↔ east/north meters), accurate for ~≤200 km

Why: All kinematics & scoring code uses these helpers for consistent math.

5. Kinematics (tewa/services/kinematics.py)

heading_unit_vector: aviation convention (0°=North, 90°=East)

CPA/TCPA (cpa_tcpa):

Model straight-line motion in local ENU.

Computes time of closest approach
𝑡
∗
=
−
(
𝑝
⋅
𝑣
)
/
∣
𝑣
∣
2
t∗=−(p⋅v)/∣v∣
2
and distance at CPA.

TDB (time_to_da_boundary_s):

Time to intersect DA boundary circle; quadratic in ENU.

TWRP (time_to_weapon_release_s):

Same math as TDB but radius = weapon range ring.

6. Normalization & scoring

tewa/services/normalize.py

inv1(x, scale) = 1 / (1 + x/scale) (monotone decreasing; smaller x ⇒ larger score contribution)

clamp01(v) to constrain final score

tewa/services/threat_compute.py

score_components_to_threat: applies inv1 to cpa_km, tcpa_s, tdb_km, twrp_s, then weighted sum via ModelParams.

TCPA < 0 (CPA in past) treated as low urgency (∞ ⇒ normalized 0).

compute_score_for_track: computes kinematics from current Track fields and persists a ThreatScore.

compute_score_for_state: same, but for an explicit (lat, lon, speed, heading) (used by the timestamp engine).

batch_compute_for_scenario: loops through tracks in a scenario for a given DA.

7. Time-aware scenario engine

tewa/services/sampling.py

sample_track_state_at(track, when, method)

latest: last sample ≤ when (fallback to Track snapshot)

linear: interpolate between bracketing samples in ENU (positions) and linearly mix speed/altitude; heading interpolated along shortest arc

tewa/services/engine.py

compute_scores_at_timestamp(scenario_id, when_iso, da_ids=None, method="linear", weapon_range_km=None)

Resolves when, pulls ModelParams, chooses DAs (all or subset), samples each track at T, computes & persists ThreatScore rows.

8. API endpoints (DRF views)

POST /api/tewa/compute (existing, batch compute “now” using current Track fields)
Body: {"scenario_id": 1, "da_id": 1, "weapon_range_km": 20}
Returns: {"count": N, ...}

POST /api/tewa/compute_at (new, time-aware)
Body:

{
"scenario_id": 1,
"when": "2025-09-30T06:07:30Z",
"da_ids": [1], // optional; default: all DAs
"method": "linear", // "linear" | "latest"
"weapon_range_km": 20 // optional; default: DA radius
}

Returns: {"count": N, "scores": [...]} (serialized ThreatScores)

URL wiring

missile_model/urls.py includes:
path("api/tewa/", include(("tewa.urls", "tewa"), namespace="tewa"))

tewa/urls.py has:

path("compute_at", compute_threats_at, name="compute_at")

(plus your existing compute/threats routes)

9. Seeding & fixtures

Idempotent command: python manage.py seed_demo
Creates:

Scenario: Demo-Scenario

DAs: DA-Alpha (Jaisalmer), DA-Bravo (Jodhpur)

Tracks: T1..T3 (+ one TrackSample per track)

ModelParams with balanced weights

Fixture: tewa/fixtures/tewa_seed.json
If you use loaddata, include created_at / updated_at fields (fixtures run in “raw” mode).

Dump current DB to fixture:

python manage.py dumpdata tewa --indent 2 > tewa/fixtures/tewa_seed.json

10. Admin polish

All models registered; can add:

verbose_name_plural = "Model params" on ModelParams (fix “paramss”)

Admin action on DefendedAsset: “Compute Threat Scores for latest Scenario”

Make ThreatScore mostly read-only in admin

11. Tests (green ✅)

Units & geodesy: conversions, haversine, ENU round-trip

Kinematics: CPA/TCPA basic, TDB entry, TWRP none when moving away

Scoring: normalization (inv1, clamp01), weights behavior, negative TCPA handling

API (time-aware): compute_at with method="linear" persists scores and returns 0–1 scores

Run:

python manage.py test core.tests -v 2
python manage.py test tewa.tests -v 2

12. Developer cookbook
    Compute threats now (batch)
    curl -X POST http://127.0.0.1:8000/api/tewa/compute \
     -H 'Content-Type: application/json' \
     -d '{"scenario_id":1,"da_id":1,"weapon_range_km":20}'

Compute threats at a timestamp (interpolated)
curl -X POST http://127.0.0.1:8000/api/tewa/compute_at \
 -H 'Content-Type: application/json' \
 -d '{
"scenario_id": 1,
"when": "2025-09-30T06:07:30Z",
"da_ids": [1],
"method": "linear",
"weapon_range_km": 20
}'

Verify threats list (if you exposed a list endpoint)
curl 'http://127.0.0.1:8000/api/tewa/threats?scenario_id=1&da_id=1'

13. Design choices & assumptions

Straight-line motion in local ENU for kinematics (fast, adequate for short horizons).

No aircraft type/intent required (deterministic, kinematics-only).

Normalization uses inv1 (smooth, bounded, scale-controlled).

TCPA < 0 treated as low urgency (closest approach already happened).

TDB stored as distance to DA center (km) for immediacy; time-to-boundary is also available via time_to_da_boundary_s if we need it later.

14. What’s next (suggested)

API smoke tests for /api/tewa/compute + threats list (persist + sort).

Dry-run mode for /api/tewa/compute_at (return scores without writing DB) for tuning.

More seed scenarios (night ops / high-speed ingress / multi-DA).

Weights tuning UI (pass ModelParams in request, don’t persist).

Performance: bulk create ThreatScores; pagination on list endpoint.

Docs site: convert this doc to mkdocs or Sphinx with diagrams.

15. File map (high-level)
    missile_model/
    ├─ missile_model/urls.py
    ├─ tewa/
    │ ├─ models.py
    │ ├─ admin.py
    │ ├─ urls.py
    │ ├─ views.py
    │ ├─ serializers.py
    │ ├─ fixtures/tewa_seed.json
    │ ├─ management/commands/seed_demo.py
    │ └─ services/
    │ ├─ kinematics.py
    │ ├─ normalize.py
    │ ├─ threat_compute.py
    │ ├─ sampling.py
    │ └─ engine.py
    ├─ core/
    │ └─ utils/
    │ ├─ units.py
    │ └─ geodesy.py
    └─ tests/
    └─ (core + tewa test packages)
