TEWA Frontend Integration Guide (v1.0)

Project: Tactical Threat Evaluation & Weapon Assignment (TEWA)
Audience: Angular/Frontend engineers
Date: 2025-10-18
Back end: Django + DRF, base path /api/tewa/
Time policy: UTC only in requests and responses (ISO-8601)

1. Overview (what you’re building against)

TEWA computes threat scores for Track × Defended Asset (DA) pairs using four metrics:

CPA — Closest Point of Approach (distance)

TCPA — Time to CPA (seconds; negative means CPA already happened)

TDB — Distance/Time to DA boundary crossing

TWRP — Time to Weapon-Release ring (DA radius + weapon range)

Each metric is normalized (0–1, higher = worse). A ThreatScore (0–1, higher = more dangerous) is the weighted blend of the normalized components. Scores are deterministic for a given timestamp. You can compute using current track states (now) or at a specific time (with linear interpolation).

The FE calls compute endpoints to (re)generate scores, then reads ranking endpoints to render boards and detail views.

2. API surface the FE actually uses

Base prefix: /api/tewa/
Content-Type: JSON (CSV upload is multipart)
Auth: None in dev; JWT planned

2.1 Utility & reference

GET /health → { "status": "ok" }

GET /scenarios/ → list scenarios

GET /da/ → list DAs (canonical; legacy read-only aliases may exist)

Tracks/TrackSamples endpoints exist for debugging; the UI normally doesn’t need them.

2.2 Compute (create or update ThreatScore rows)

POST /compute_now/
Triggers compute using latest track snapshots.

{
"scenario_id": 1,
"weapon_range_km": 20 // optional; if omitted, DA radius is used where relevant
}

Typical response (summary):

{
"status": "computed",
"scenario_id": 1,
"computed_at": "2025-09-30T06:07:30Z",
"count": 42
}

POST /compute_at/
Computes at a time; supports interpolation and DA filtering. Persists results.

{
"scenario_id": 1,
"when": "2025-09-30T06:07:30Z",
"da_ids": [1, 2], // optional: compute only for these DAs
"method": "linear", // "linear" or "latest"
"weapon_range_km": 20 // optional
}

Typical response (summary): same shape as compute_now (count, computed_at).

When to use which:

“Recompute Now” button → POST /compute_now/

Time-scrubber “Compute at T” → POST /compute_at/ with method: "linear"

2.3 Ranking (what you render on the board)

GET /ranking/?scenario_id=1&top_n=10[&da_id=2]
Returns grouped-by-DA top threats with score and normalized components.
ETag header is set so you can poll cheaply.

{
"scenario_id": 1,
"computed_at": "2025-09-30T06:07:30Z",
"results": [
{
"da": { "id": 1, "name": "DA-Alpha", "lat": 28.61, "lon": 77.21, "radius_km": 50 },
"top": [
{
"track_id": "T2",
"score": 0.762,
"components": { "cpa": 0.91, "tcpa": 0.75, "tdb": 0.53, "twrp": 0.82 }
},
{
"track_id": "T1",
"score": 0.579,
"components": { "cpa": 0.71, "tcpa": 0.64, "tdb": 0.48, "twrp": 0.51 }
}
]
}
]
}

2.4 Score rows (details/explainability)

GET /score/?scenario_id=1[&da_id=1][&track_id=T1][&page=1]
Flat ThreatScore rows (historical, paginated). Rows include raw metrics, normalized components, weights, score, and computed_at.

{
"scenario_id": 1,
"page": 1,
"results": [
{
"track_id": "T1",
"computed_at": "2025-09-30T06:07:30Z",
"metrics": { "cpa_m": 1234.5, "tcpa_s": 67.8, "tdb_s": 90.2, "twrp_s": 12.0 },
"normalized": { "cpa": 0.82, "tcpa": 0.61, "tdb": 0.34, "twrp": 0.74 },
"weights": { "cpa": 0.25, "tcpa": 0.25, "tdb": 0.25, "twrp": 0.25 },
"score": 0.656,
"params": { "clamp_0_1": true }
}
]
}

2.5 Model parameters (for legends/labels)

GET /modelparams/?scenario_id=1
Returns weights/scales/flags so you can label charts (“CPA emphasized”, etc.).

Note on legacy paths: If you see old docs referencing /threats/ or /scenario/, prefer the canonical /ranking/ and /scenarios/ paths above.

3. Semantics you should reflect in the UI

Normalized components (0–1): Higher = worse (more urgent). Use these for bars.

Final ThreatScore (0–1): Weighted blend. Higher ranks higher.

TCPA negative: Means CPA occurred in the past → contribution 0 (show a tooltip “Past CPA” if you display raw tcpa_s from /score/).

TWRP no opportunity: Backend may return twrp_s = "inf" or omit → contribution 0 (tooltip “No release opportunity”).

Determinism: Same inputs at time T → same outputs. The computed_at in responses is the reference.

Units (display):

CPA, TDB as km (1 decimal is fine)

TCPA, TWRP as seconds (whole seconds or mm:ss if >60 s)

All times ISO-UTC (...Z)

4. Polling & caching (ETag pattern)

Poll the ranking board every 5–10 s using the last ETag.

Send If-None-Match: <etag> on the next request.

If the server returns 304, nothing changed → skip re-render.

When 200, store the new ETag and update the board.

5. Angular integration (types & helpers)
   5.1 TypeScript types
   export type Normalized = { cpa: number; tcpa: number; tdb: number; twrp: number };

export interface RankingItem {
track_id: string;
score: number; // 0..1
components: Normalized; // 0..1 each
}

export interface DARanking {
da: { id: number; name: string; lat: number; lon: number; radius_km: number };
top: RankingItem[];
}

export interface RankingResponse {
scenario_id: number;
computed_at: string; // ISO-UTC
results: DARanking[];
}

export interface ScoreRow {
track_id: string;
computed_at: string; // ISO-UTC
metrics: { cpa_m: number; tcpa_s: number | "inf"; tdb_s: number | "inf"; twrp_s: number | "inf" };
normalized: Normalized;
weights: { cpa: number; tcpa: number; tdb: number; twrp: number };
score: number;
params?: { clamp_0_1?: boolean };
}

export interface ScoreResponse {
scenario_id: number;
da_id?: number;
page: number;
results: ScoreRow[];
}

5.2 ETag polling helper (fetch)
let etag: string | undefined;

export async function fetchRanking(scenarioId: number, topN = 10, daId?: number) {
const q = new URLSearchParams({ scenario_id: String(scenarioId), top_n: String(topN) });
if (daId) q.set("da_id", String(daId));

const res = await fetch(`/api/tewa/ranking/?${q.toString()}`, {
headers: etag ? { "If-None-Match": etag } : {}
});

if (res.status === 304) return { changed: false } as const;

etag = res.headers.get("ETag") ?? undefined;
const data = (await res.json()) as RankingResponse;
return { changed: true, data } as const;
}

5.3 Angular service (HttpClient + RxJS)
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { interval, startWith, switchMap, map, distinctUntilChanged } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class TewaService {
private etag?: string;

constructor(private http: HttpClient) {}

pollRanking$(scenarioId: number, topN = 10, daId?: number, periodMs = 5000) {
const params: any = { scenario_id: scenarioId, top_n: topN };
if (daId != null) params.da_id = daId;

    return interval(periodMs).pipe(
      startWith(0),
      switchMap(() => this.http.get('/api/tewa/ranking/', {
        params, observe: 'response', responseType: 'json'
      })),
      map(resp => {
        const newEtag = resp.headers.get('ETag') ?? undefined;
        const changed = newEtag && newEtag !== this.etag;
        if (newEtag) this.etag = newEtag;
        return changed ? (resp.body as any as RankingResponse) : null;
      }),
      distinctUntilChanged((a, b) => (a?.computed_at ?? '') === (b?.computed_at ?? ''))
    );

}

getScoreRows$(scenarioId: number, daId?: number, trackId?: string, page = 1) {
const params: any = { scenario_id: scenarioId, page };
if (daId != null) params.da_id = daId;
if (trackId) params.track_id = trackId;
return this.http.get<ScoreResponse>('/api/tewa/score/', { params });
}

computeNow$(scenarioId: number, weaponRangeKm = 20) {
return this.http.post('/api/tewa/compute_now/', { scenario_id: scenarioId, weapon_range_km: weaponRangeKm });
}

computeAt$(scenarioId: number, whenIsoUtc: string, daIds?: number[], method: 'linear'|'latest' = 'linear', weaponRangeKm = 20) {
return this.http.post('/api/tewa/compute_at/', {
scenario_id: scenarioId, when: whenIsoUtc, da_ids: daIds, method, weapon_range_km: weaponRangeKm
});
}

listScenarios$() { return this.http.get('/api/tewa/scenarios/'); }
  listDAs$() { return this.http.get('/api/tewa/da/'); }
getModelParams$(scenarioId: number) { return this.http.get('/api/tewa/modelparams/', { params: { scenario_id: scenarioId } }); }
}

6. UI building blocks (recommended)

Scenario selector (dropdown) → drives all requests.

DA selector (optional filter) → passes da_id into /ranking/.

Recompute Now button → POST /compute_now/ then refresh ranking.

Time slider + “Compute at T” → POST /compute_at/ (method "linear"), then fetch ranking.

Threat board (per-DA group):

Sort items by score desc, tie-break track_id asc (the API already does this).

Badge/band by thresholds: ≥0.80 critical, 0.60–0.79 high, 0.40–0.59 med, <0.40 low.

For each item show:

track_id, score (0–1), four bars for normalized cpa, tcpa, tdb, twrp.

Details drawer for a selected item:

Fetch /score/ (filter by da_id, optionally track_id).

Use latest computed_at row for that track/DA.

Show raw metrics with units + normalized bars + weights (legend).

If tcpa_s negative in any historical row → label “Past CPA”.
If twrp_s === "inf" → “No release opportunity”.

7. Time & formatting rules

Always send UTC: new Date().toISOString() (ends with Z).

Display: you may localize for users, but keep API calls in UTC.

Numbers: show score with 2 decimals; distances 1 decimal km; seconds integer (or mm:ss).

8. Errors & resilience (DRF style)

400 Validation → show detail or the first field error.

404 Not found → “Scenario/DA/Track not found.”

409 Duplicate (CSV ingest) → surface errors[] with row numbers.

422 Semantic → e.g., “time outside scenario window.”

5xx → non-blocking toast; keep last board.

Polling robustness:

Respect 304 to avoid flicker.

When network fails, keep last successful ranking in view and retry.

9. Performance tips

ETag polling (5–10 s) to limit payloads/repaints.

Virtualize long lists; memoize bar widths/colors.

Don’t poll /score/; fetch on demand when the detail drawer opens.

Debounce “Compute at T” by ~300–500 ms if driven by a slider.

10. QA checklist (copy/paste)

All requests use ISO-UTC (...Z).

Ranking shows score desc, tie-break track_id asc.

Components render as 0–1 bars with units in tooltips.

Negative TCPA displays “Past CPA”; contributes 0.

No TWRP opportunity displays “No release opportunity”; contributes 0.

ETag respected; 304 causes no UI flicker.

Errors surfaced clearly (DRF messages, ingest errors[]).

Accessible labels for bars and numeric values.

Responsive cards at small widths; scores remain readable.

11. Example flows

A) Recompute now

Click “Recompute Now” → POST /compute_now/.

On success, immediately GET /ranking/ (ignore ETag once), then resume ETag polling.

B) What-if at time T

Choose UTC time → POST /compute_at/ with method: "linear".

GET /ranking/ → render new board for that computed_at.

C) Explain this row

Click item → GET /score/?scenario_id=..&da_id=..&track_id=...

Pick latest computed_at → show metrics + normalized + weights.

12. Glossary

DA (Defended Asset): Protected entity; circle at (lat,lon) with radius_km.

Track: Moving entity with timestamped samples.

CPA/TCPA/TDB/TWRP: Core metrics feeding the score.

Normalized component: 0–1 urgency for a metric (higher = worse).

ThreatScore: Weighted blend of normalized components (0–1).

ETag: Response version tag used for efficient polling.

13. Notes on legacy naming

Prefer /ranking/ (replaces older /threats/ concepts).

Prefer /scenarios/ (not /scenario/).

DA canonical path is /da/. Old aliases (/defendedassets/, /das/) may exist as read-only during deprecation.

Final reminders

Keep UTC end-to-end.

Use ETag to poll efficiently.

Render normalized components for explanation; score for rank.

Treat negative TCPA and no TWRP as zero-contribution components with clear labels.
