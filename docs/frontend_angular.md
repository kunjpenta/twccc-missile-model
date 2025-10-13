TEWA Frontend Integration Guide

Project: Tactical Threat Evaluation & Weapon Assignment (TEWA)
Frontend Developer Handover Document
Version: 1.0
Date: [Current Date]

1. Overview

The TEWA system is designed to evaluate threats based on tracked targets (aircraft or threats) and compute their proximity and danger to defended assets (DAs). The key metrics computed are:

CPA (Closest Point of Approach)

TCPA (Time to CPA)

TDB (Threat Distance to Boundary)

TWRP (Time to Weapon Release Point)

These metrics are used to generate a ThreatScore, a value between 0 and 1, where higher values represent more dangerous threats.

The system supports live computation (current track states) and time-based computation (interpolation of tracks at a specific time). The frontend will interact with the backend via APIs to trigger threat computations, fetch results, and display rankings of threats.

2. API Endpoints Overview

The frontend communicates with the backend primarily through the following endpoints:

2.1. Compute Threats for Now (Current Track States)

Endpoint: POST /api/tewa/compute_now/

Description: This endpoint triggers the computation of threat scores using the current states of tracks.

Request Body Example:

{
"scenario_id": 1,
"da_id": 1,
"weapon_range_km": 20 // Optional, defaults to DA.radius_km if not provided
}

Response Example:

{
"count": 3,
"scores": [
{
"track_id": "T1",
"da_name": "DA-Alpha (Delhi)",
"score": 0.578,
"computed_at": "2025-09-30T06:07:30Z"
},
...
]
}

Use Cases:

"Compute Now" button to trigger the computation based on the current data.

Quick refresh during live demo.

2.2. Compute Threats at a Specific Timestamp (Interpolated)

Endpoint: POST /api/tewa/compute_at/

Description: This endpoint computes threat scores for a scenario at a specific timestamp. It can interpolate track data between samples.

Request Body Example:

{
"scenario_id": 1,
"when": "2025-09-30T06:07:30Z",
"da_ids": [1, 2], // Optional, omit for "all DAs"
"method": "linear", // "linear" or "latest"
"weapon_range_km": 20 // Optional, defaults to DA.radius_km
}

Response Example:

{
"count": 3,
"scores": [
{
"track_id": "T1",
"da_name": "DA-Alpha (Delhi)",
"score": 0.578,
"computed_at": "2025-09-30T06:07:30Z"
},
...
]
}

Behavior:

Method linear: Interpolates between track samples around the requested timestamp. Positions and other kinematic data (speed, altitude, heading) are interpolated.

Method latest: Uses the most recent sample before or at the given time.

Use Cases:

Time-scrubber or timeline control with a "Compute at Time" button.

2.3. List Threats

Endpoint: GET /api/tewa/threats/

Description: Retrieves a list of ranked threats based on scenario and optional filtering by DA.

Query Parameters:

scenario_id (Required): ID of the scenario.

da_id (Optional): Filter threats by a specific DA.

ordering (Optional): Default is descending by score (e.g., -score).

page (Optional): For pagination (default: 1).

page_size (Optional): For pagination (default: 50).

Request Example:

/api/tewa/threats/?scenario_id=1&da_id=1&ordering=-score&page=1&page_size=50

Response Example:

{
"count": 3,
"results": [
{
"track_id": "T2",
"da_name": "DA-Alpha (Delhi)",
"score": 0.7617,
"computed_at": "2025-09-30T06:07:30Z"
},
...
]
}

3. Data Models

Here is a summary of the key data models that the frontend will interact with:

3.1. Scenario

Represents the context of a simulation session.

type Scenario = {
id: number;
name: string;
start_time: string; // ISO8601 UTC
end_time: string | null;
notes?: string | null;
};

3.2. Defended Asset (DA)

Represents the assets being protected in the simulation.

type DefendedAsset = {
id: number;
name: string;
lat: number;
lon: number;
radius_km: number;
};

3.3. Track

Represents an individual threat (e.g., aircraft) being tracked over time.

type Track = {
id: number;
scenario: number; // scenario id
track_id: string; // external identifier
lat: number;
lon: number;
alt_m: number; // Altitude in meters
speed_mps: number; // Speed in meters per second
heading_deg: number; // Heading in degrees (0 = North, 90 = East)
created_at: string;
updated_at: string;
};

3.4. Track Sample

A snapshot of the track at a given point in time.

type TrackSample = Omit<Track, "scenario" | "track_id"> & {
track: number; // track id
t: string; // sample time (ISO8601 UTC)
};

3.5. Model Parameters

Defines the weights and normalization scales for threat scoring.

type ModelParams = {
id: number;
scenario: number;
w_cpa: number;
w_tcpa: number;
w_tdb: number;
w_twrp: number;
cpa_scale_km: number;
tcpa_scale_s: number;
tdb_scale_km: number;
twrp_scale_s: number;
clamp_0_1: boolean;
};

3.6. Threat Score

Represents the computed threat score for a track in relation to a defended asset.

type ThreatScore = {
id: number;
scenario: number;
track: number;
da: number;
cpa_km: number | null;
tcpa_s: number | null;
tdb_km: number | null;
twrp_s: number | null;
score: number;
computed_at: string; // ISO8601 UTC
};

4. Frontend Interaction with APIs
   4.1. Compute Now Button

Action: Triggers the calculation of the threat score for a scenario with the current track states.

API Call: POST /api/tewa/compute_now/

Request Body:

{
"scenario_id": 1,
"da_id": 1
}

Response:

{
"status": "Compute task queued",
"scenario_id": 1
}

4.2. Time-based Compute (Compute at Timestamp)

Action: Allows users to compute the threat score at a specific point in time, with interpolation options.

API Call: POST /api/tewa/compute_at/

Request Body:

{
"scenario_id": 1,
"when": "2025-09-30T06:07:30Z",
"method": "linear",
"da_ids": [1, 2]
}

Response:

{
"count": 3,
"scores": [
{
"track_id": "T1",
"da_name": "DA-Alpha (Delhi)",
"score": 0.578,
"computed_at": "2025-09-30T06:07:30Z"
}
]
}

4.3. Ranking of Threats

Action: Displays ranked threats based on computed scores for the scenario.

API Call: GET /api/tewa/ranking/

Query Parameters:

scenario_id: Required, specifies the scenario.

da_id: Optional, filter by defended asset.

top_n: Optional, limit to top N threats.

Response:

{
"scenario_id": 1,
"threats": [
{
"track_id": "T2",
"da_name": "DA-Alpha (Delhi)",
"score": 0.7617,
"computed_at": "2025-09-30T07:23:01Z"
}
]
}

5. UI Guidelines and Best Practices
   5.1. Components

Scenario Selector: A dropdown allowing users to select the scenario for computation.

DA Selector: Dropdown for selecting the defended asset.

Compute Now Button: Triggers the computation for the selected scenario.

Time Slider: Allows the user to pick a timestamp and compute scores at that time.

Threats Table: Displays the list of computed threat scores, sorted by score.

Details Panel: Shows additional information for each threat, including the breakdown of CPA, TCPA, TDB, TWRP, and score.

5.2. Data Formatting

Score: Displayed as a percentage bar or decimal (0-1 scale).

CPA, TDB: Displayed in kilometers with one decimal.

TCPA, TWRP: Displayed in seconds (rounded to integer).

Time: Always in ISO8601 UTC format, for example, 2025-09-30T06:07:30Z.

6. UX/UI Enhancements

Feedback: Provide visual feedback when the computation is triggered (e.g., loading spinner or success message).

Error Handling: Show user-friendly error messages when API calls fail.

Live Updates: Optionally implement polling for threat score updates or auto-refresh based on Celery Beat.

7. Final Notes for Frontend Developer

API Integration: Ensure all API requests are formatted according to the specifications, and handle responses properly.

Data Integrity: Ensure that all time-related fields are displayed in UTC and correctly formatted.

Security: Consider adding authentication tokens for production; currently, no authentication is required in the dev environment.

TEWA Backend APIs

1. Health & Root
   Endpoint Method Parameters Description
   /api/health GET None Simple health check. Returns 200 if backend is running.
   /api/ GET None API root. Returns available endpoints as JSON.
2. Scenario APIs
   Endpoint Method Parameters Description
   /api/tewa/scenario/ GET None List all scenarios. Returns scenario details (id, name, start_time, end_time, notes).
   /api/tewa/scenario/ POST JSON: name, start_time, end_time, notes Create a new scenario.
3. Defended Asset (DA) APIs
   Endpoint Method Parameters Description
   /api/tewa/da/ GET None List all defended assets with id, name, lat, lon, radius_km.
   /api/tewa/da/ POST JSON: name, lat, lon, radius_km Create a new defended asset (DA).
   /api/tewa/da/<id>/ GET id (path) Get details for a single DA.
   /api/tewa/da/<id>/ PUT/PATCH JSON fields Update an existing DA.
   /api/tewa/da/<id>/ DELETE id (path) Delete a DA.
4. Track APIs
   Endpoint Method Parameters Description
   /api/tewa/track/ GET None List all tracks. Returns track_id, lat, lon, alt_m, speed_mps, heading_deg.
   /api/tewa/track/ POST JSON fields for track Create a new track.
   /api/tewa/track/<id>/ GET/PUT/PATCH/DELETE id (path) CRUD operations for individual tracks.
   /api/tewa/tracksample/ GET/POST Track snapshots TrackSample CRUD for historical positions.
5. Threat Compute APIs
   Endpoint Method Parameters Description
   /api/tewa/compute_at/ POST JSON: scenario_id, timestamp, method (linear/other), da_ids (optional), weapon_range_km (optional) Computes threat scores for all tracks in a scenario at a specific timestamp. Persists results in ThreatScore.
   /api/tewa/compute_now/ POST JSON: scenario_id Queues a Celery task to compute threat scores immediately for the specified scenario. Returns status.
6. ThreatScore APIs
   Endpoint Method Parameters Description
   /api/tewa/score/ GET Optional: scenario_id, da_id, track_id List all persisted threat scores. Can filter by scenario, DA, or track. Returns CPA/TCPA/TDB/TWRP and score values.
7. Threat Ranking APIs
   Endpoint Method Query Params Description
   /api/tewa/ranking/ GET scenario_id (required), da_id (optional), top_n (optional) Returns ranked threats sorted by score descending. Can return top-N threats per scenario or per DA. Each threat includes: track_id, da_name, score, computed_at.

Example Request:

GET /api/tewa/ranking/?scenario_id=1&top_n=10

Example Response:

{
"scenario_id": 1,
"threats": [
{"track_id":"T2","da_name":"DA-Alpha (Delhi)","score":0.7617,"computed_at":"2025-10-01T07:23:01Z"},
{"track_id":"T1","da_name":"DA-Alpha (Delhi)","score":0.5785,"computed_at":"2025-10-01T07:23:01Z"},
...
]
}

8. Optional / Health Utilities
   Endpoint Method Description
   /api/db-ping GET Checks database connectivity.
   /api/health GET Checks service health (already mentioned above).
9. Notes for Frontend Integration

All datetime values are ISO 8601 in UTC.

Compute APIs trigger scoring; rankings use persisted ThreatScore.

Use top_n and da_id query params to control ranking outputs for tables or charts.

Compute Now button → POST /api/tewa/compute_now/.

Track visualization → use lat, lon from Tracks or TrackSamples.

Ranking Table → fetch /api/tewa/ranking/ and sort by score.

Frontend can poll /api/tewa/ranking/ periodically if Celery Beat is running.

########################################################### 13/10/2025##########################################
awesome — here’s a clean, detailed wrap-up of everything we changed and completed in this thread, end-to-end. it’s written so you can drop it into your project docs or share it with the team (no code blocks).

what we built & stabilized

1. backend threat-scoring model (principles + behavior)

Core signals: CPA (closest distance), TCPA (time to CPA), TDB (current distance to DA center), TWRP (time to weapon release).

Normalization: each signal is mapped to a 0–1 urgency score where smaller/faster ⇒ more threatening. Scales (e.g., cpa_scale_km) define what “urgent” looks like.

Weighted fusion: a final threat score is a weighted sum of the normalized components. Weights encode doctrine (e.g., proximity vs timing).

Edge-case policy:

Negative TCPA (CPA is in the past) contributes 0 urgency.

No weapon opportunity (TWRP None/∞/invalid) contributes 0 urgency.

Bad inputs (None/NaN/±∞) contribute 0, not garbage.

Final clamping: optional clamp to [0,1]. We keep unclamped mode available for calibration tests (e.g., “doubling weights doubles the score”).

2. robust parameter handling

Introduced a single parameter coercion step that accepts either:

a dict (tests, scripts), or

a Django model instance (runtime).

Coercion fills in sensible defaults for missing values and guarantees a consistent internal shape, reducing copy-paste and drift.

3. clean separation: compute vs persist

Pure compute: functions that only calculate numbers (no DB). Easy to reason about and unit-test.

Persistence path: orchestrates model lookups, computes the score, and stores ThreatScore rows. Keeps side effects out of the math.

fixes & refactors we did during the chat 4) pytest / environment issues resolved

Diagnosed pytest_django plugin import errors due to PATH confusion between system pytest and venv pytest.

Standardized invocation using python -m pytest -p pytest_django --ds=missile_model.settings to force venv and stable settings.

Verified plugin installation inside the virtualenv, and cleared shell command cache.

5. unit tests: repaired, extended, and made self-contained

Fixed tests that were written as if they were instance methods (e.g., self as a fixture).

Converted tests to use the positional-friendly scoring function.

Added/kept behavioral tests that assert model properties, not just numbers:

negative TCPA reduces threat vs. positive TCPA;

weights emphasis changes the ordering;

extreme distances ⇒ low score;

no clamp allows score > 1 when weights sum > 1;

missing params fall back to defaults.

Ensured tests require no DB when possible (e.g., SimpleTestCase + dict params).

6. scoring service hardened

Finalized a single, consistent scoring function that:

normalizes with inversion and scales;

applies weights;

handles None/negative time appropriately;

respects clamping policy.

Kept a legacy/simple combiner (for compatibility) but the canonical path is the new, parameterized scorer.

7. threat_compute service refactor

Rewrote compute_threat_score to be pure compute, returning:

cpa_km, tcpa_s (never negative on output), tdb_km, twrp_s (∞ if no opportunity), and score.

Updated compute_score_for_track to:

compute CPA/TCPA/TWRP correctly,

derive TDB from current geometry,

coerce parameters once,

persist a ThreatScore row with all components and the final score.

Fixed a missing/invalid type import (ParamsLike) by either defining it or removing the dependency; replaced with the coercion approach to avoid fragile type paths.

In batch compute paths:

ensured ModelParams.get_or_create has non-zero defaults so scores aren’t 0.0 when a scenario is first computed.

8. API & engine glue made reliable

Prevented import errors in API routes by removing brittle type-only imports and reusing the shared coercion.

Confirmed the compute_at endpoint behavior: time sampling/interpolation performed before scoring, results persisted and returned.

Verified the score breakdown API’s semantics: it returns the latest ThreatScore for a track/DA combo.

test outcomes & coverage 9) test pass results

We iterated from scattered failures and import errors to stable green:

Final: 34 tests passed (project suite).

Point-checks along the way validated both compute logic and API/management flows.

10. coverage workflow stabilized

Documented a repeatable coverage routine (coverage erase → coverage run -m pytest -q → coverage report → coverage html).

Resolved a confusing run (long parse time) by using the erase-run-report pattern.

Achieved strong coverage where it matters (math/compute). Lower coverage in view/admin areas is expected at this stage.

operational principles embedded 11) interpretability & doctrine mapping

Every knob (scale, weight, clamp) has a plain-language meaning:

scales tie to tactical thresholds;

weights reflect doctrine;

clamp toggles UI vs calibration modes.

12. fault-tolerance

Invalid or unavailable data points fail soft, not hard.

Scores remain meaningful and bounded (when clamped), which prevents UI jitter and bad alerts.

13. extensibility

The combination framework supports new components (e.g., sensor credibility, intent) by normalizing and weighting into the same structure.

API is future-proofed: inputs/outputs are componentized and returned, enabling explainability (“why this score?”).

what the frontend team needs to know (integration summary)

you said you created a frontend integration doc for Angular; here are the core points we ensured the backend supports and that your doc can emphasize:

Endpoints:

compute at a timestamp (interpolates state, computes, persists);

score breakdown (returns latest, componentized scores).

Request inputs:

scenario id, DA id(s), timestamp (ISO 8601), interpolation method (e.g., linear), optional weapon range.

Response semantics:

returns components (CPA/TCPA/TDB/TWRP) and the final score so the UI can show both rank and explanation.

tcpa_s is non-negative in responses; twrp_s can be ∞ (no opportunity).

State & idempotency:

compute endpoints persist results (ThreatScore rows) and can be queried later; repeated calls for the same inputs are safe.

Tuning knobs (backed by params):

scales and weights are scenario-scoped; future admin/UI screens can expose doctrine presets without code changes.

final status (what’s done)

✅ scoring logic finalized with robust normalization, weighting, clamping, and edge-case policy.

✅ parameter coercion unified dict/model inputs with defaults.

✅ compute vs persist separated cleanly; both paths stabilized.

✅ tests repaired/extended to cover key behavioral properties.

✅ all project tests passing (34/34).

✅ coverage workflow reliable; high confidence in the math layer.

✅ API/engine imports and routing stabilized.

✅ frontend integration concepts documented (inputs/outputs, semantics, explainability).

suggested next steps

expose parameter profiles (weights/scales) in admin/UI for scenario-specific doctrine.

add a minimal “explain this score” API that echoes normalized components + weight impact for the selected track/DA.

consider nonlinear curves (logistic/exponential) if SMEs want sharper urgency near the DA without retuning weights.
