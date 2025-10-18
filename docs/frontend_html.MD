TEWA — Frontend Integration Brief (v1)

Date: 13 Oct 2025 • Audience: Angular/Frontend devs

This is a focused rewrite of the backend progress for you. It tells you exactly what to call, what the numbers mean, and how to render them without guesswork.

1. What’s ready (why you care)

Deterministic threat scoring for Track × Defended Asset (DA).

Stable, UTC-only API under /api/tewa/.

Consistent scoring semantics (edge cases fixed).

Useful shapes for dashboards: total score and component breakdowns.

ETag support for cheap polling.

2. Endpoints you’ll call (cheat sheet)

Base: /api/tewa/ (JSON)

GET /ranking/?scenario_id=1&top_n=10[&da_id=2]
Sorted by score desc, then track_id asc. Returns computed_at (UTC) and grouped lists per DA. Supports ETag.

POST /compute_now/
Body: {"scenario_id":1,"weapon_range_km":20}
Triggers immediate compute using latest snapshots; returns a success payload. (Use for manual “Recompute” button.)

POST /compute_at/
Body:

{
"scenario_id":1,
"when":"2025-09-30T06:07:30Z",
"da_ids":[1,2],
"method":"linear", // or "latest"
"weapon_range_km":20
}

Computes threat at a specific time (linear interpolation).

GET /score_breakdown?scenario_id=1&track_id=T1&da_id=3[&at=ISO-UTC]
Returns per-threat raw metrics, normalized components, weights, and final score for explainability panels.

GET /modelparams/?scenario_id=1
Current weights/scales/flags (so you can label charts).

GET /da/
Canonical DA list. (Legacy /defendedassets/, /das/ remain read-only.)

Note: CSV upload exists for ops, not typical UI: POST /upload_tracks/ (multipart).

3. Response shapes (examples)
   Ranking (example)
   {
   "scenario_id": 1,
   "computed_at": "2025-09-30T06:07:30Z",
   "results": [
   {
   "da": {"id": 1, "name": "Alpha", "lat": 12.3, "lon": 77.5, "radius_km": 50},
   "top": [
   {
   "track_id": "T1",
   "score": 0.83,
   "components": {"cpa": 0.90, "tcpa": 0.72, "tdb": 0.64, "twrp": 0.91}
   },
   { "track_id": "T2", "score": 0.61, "components": { "cpa": 0.70, "tcpa": 0.55, "tdb": 0.40, "twrp": 0.79 } }
   ]
   }
   ]
   }

Score breakdown (example)
{
"scenario_id": 1,
"track_id": "T1",
"da_id": 3,
"computed_at": "2025-10-14T10:02:00Z",
"metrics": { "cpa_m": 1234.5, "tcpa_s": 67.8, "tdb_s": 90.2, "twrp_s": 12.0 },
"normalized": { "cpa": 0.82, "tcpa": 0.61, "tdb": 0.34, "twrp": 0.74 },
"weights": { "cpa": 0.35, "tcpa": 0.25, "tdb": 0.20, "twrp": 0.20 },
"contributions": { "cpa": 0.287, "tcpa": 0.153, "tdb": 0.068, "twrp": 0.148 },
"score": 0.656,
"params": { "clamp_0_1": true }
}

4. Data semantics you’ll display

Score scale: by default 0–1 (clamped). Higher = more threatening.

Components (normalized): each in 0–1; combined with weights to make the final score.

TCPA (time to CPA): if negative, it’s a past event → contributes 0 (UI may show “past CPA”).

TWRP (time to weapon-release window): if no opportunity, backend returns +inf in metrics; its normalized contribution is 0. Display as “No release opportunity” instead of a number.

UTC only: inputs and outputs are UTC (...Z). You can localize for display, but send UTC to the API.

5. UX behavior (recommended)

Boards: sort by score DESC; tie-break by track_id ASC.

Color bands (example):

≥ 0.80 → Critical (red)

0.60–0.79 → High (orange)

0.40–0.59 → Medium (yellow)

< 0.40 → Low (green)

Explain: show a stacked bar of component contributions or a 4-bar breakdown with tooltips using normalized and weights.

Labels:

Negative TCPA → “Past CPA”

twrp_s = ∞ → “No release opportunity”

Actions:

“Recompute” → POST /compute_now/

“What-if at time T” → POST /compute_at/ then refresh /ranking/

6. Polling with ETag (cheap refresh)

Poll /ranking/?scenario_id=...&top_n=... every 5–10s with If-None-Match. Handle 304 to skip re-render.

TypeScript snippet:

let etag: string | undefined;

async function fetchRanking() {
const res = await fetch(`/api/tewa/ranking/?scenario_id=1&top_n=10`, {
headers: etag ? { "If-None-Match": etag } : {}
});

if (res.status === 304) return null;

etag = res.headers.get("ETag") ?? undefined;
return res.json(); // contains computed_at, results[…]
}

7. Error handling (UI rules)

Prefer detail when present: {"detail":"Not found."}

Otherwise show the first field error (DRF style).

For CSV upload, render all items in errors[].

Typical status codes:

400 validation (bad lat/lon, radius, CSV header, types)

404 not found (scenario/DA/track)

409 duplicate (track_id, t) on ingest

422 semantic (e.g., time outside scenario window)

8. Types you can use (quick draft)
   export type Normalized = { cpa: number; tcpa: number; tdb: number; twrp: number };

export interface RankingItem {
track_id: string;
score: number; // 0..1 (typical)
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

export interface ScoreBreakdown {
scenario_id: number;
track_id: string | number;
da_id: number;
computed_at: string;
metrics: { cpa_m: number; tcpa_s: number; tdb_s: number; twrp_s: number | "inf" };
normalized: Normalized;
weights: { cpa: number; tcpa: number; tdb: number; twrp: number };
contributions: { cpa: number; tcpa: number; tdb: number; twrp: number };
score: number;
params?: { clamp_0_1?: boolean };
}

9. Integration checklist

Use UTC ISO-8601 for any time you send (...Z).

Render score (0–1) and an explainable breakdown (normalized × weights).

Treat negative TCPA as “past” (display hint; contribution already zeroed).

Treat twrp_s = ∞ as “No release opportunity.”

Poll /ranking/ with ETag; handle 304.

Prefer /da/ (canonical).

On errors, show detail or first field error; for uploads show all errors[].

If you want a tiny mock JSON file for local UI work, I can generate one with a few DAs and a dozen tracks following the shapes above.

You said:
write in detailed
ChatGPT said:
Thought for 11s
TEWA — Frontend Developer Guide (detailed)

Audience: Angular/FE engineers
Back-end: Django + DRF, stable prefix /api/tewa/
All times: UTC in/out (ISO-8601). Frontend may localize for display.

This guide tells you exactly what to call, what the numbers mean, and how to render threat scores without guesswork.

1. What the FE can rely on

Deterministic threat scoring per Track × Defended Asset (DA).

Stable REST paths under /api/tewa/ (see §4).

JSON responses include a total score and component breakdown (CPA, TCPA, TDB, TWRP).

ETag on /ranking/ so you can poll cheaply.

All inputs/outputs timestamps are UTC; backend normalizes anything you send.

2. Threat score semantics (display rules)

A threat score is a weighted blend of four normalized components:

CPA (closest distance) — smaller distance ⇒ higher normalized value (worse).

TCPA (time to CPA) — closer in time ⇒ higher normalized value.
If negative (CPA happened in the past), its contribution is 0 (display tip: “Past CPA”).

TDB (to DA boundary) — time/distance to cross the asset’s ring. Already inside ⇒ treated as immediate (high).

TWRP (time to weapon-release window) — time to weapon-release ring.
If no opportunity, metrics may be +inf; its contribution is 0 (display “No release opportunity”).

Normalized component range: typically 0–1.
Final score range: 0–1 when clamped (default). Higher = more threatening.

The backend returns both raw metrics (e.g., meters/seconds) and normalized 0–1 values (when you fetch detailed rows). Use normalized values to render bars, and the raw ones for tooltips.

3. Common UI patterns (recommendations)

Threat board: per-DA lists, each item = {track_id, score, components}.

Sort by score desc, tie-break by track_id asc.

Bands (example):
≥0.80 critical, 0.60–0.79 high, 0.40–0.59 medium, <0.40 low.

Explainability panel: a stacked bar of contributions or four separate bars for CPA/TCPA/TDB/TWRP (values from components).

Tooltip for TCPA: show “Past CPA” if the returned raw TCPA < 0 in a detail row (the ranking payload already zeroes its contribution).

Tooltip for TWRP: show “No release opportunity” when metric is infinite.

Polling: /ranking/ every 5–10s with If-None-Match; skip re-render on 304.

4. REST endpoints you’ll actually use

Base: /api/tewa/ (JSON)

4.1 Lists & health

GET /health → { "status": "ok" }

GET /scenarios/ → list scenarios

GET /da/ → list Defended Assets (canonical; legacy read-only aliases exist)

4.2 Tracks & samples (debug/ops views)

GET /tracks/?scenario_id=1

GET /tracksamples/?track_id=T1&from=ISO&to=ISO

4.3 Upload (ops)

POST /upload_tracks/ (multipart)
fields: file, scenario_id
CSV headers (required): track_id,lat,lon,alt_m,speed_mps,heading_deg,timestamp
Response includes counts and errors[].

4.4 Compute (buttons in UI)

POST /compute_now/
Body: {"scenario_id":1,"weapon_range_km":20}
Uses latest track snapshots; returns a summary payload.

POST /compute_at/
Body:

{
"scenario_id": 1,
"when": "2025-09-30T06:07:30Z",
"da_ids": [1,2],
"method": "linear", // or "latest"
"weapon_range_km": 20
}

Computes at time T with linear interpolation. Returns a summary and persists results.

4.5 Ranking & detailed rows (what you render)

GET /ranking/?scenario_id=1&top_n=10[&da_id=2]
Returns grouped per-DA lists: each item has {track_id, score, components} and a computed_at (UTC). Response includes ETag header.

GET /score/?scenario_id=1[&da_id=2][&page=1]
Flat ThreatScore rows (historical feed). Each row includes raw metrics and normalized components plus the final score and computed_at.
Use this when you need a per-track/DA breakdown view; filter client-side to the track you’re explaining.

4.6 Model parameters (labels/legend)

GET /modelparams/?scenario_id=1
Returns weights/scales/flags so you can annotate charts and legends (“weights emphasize CPA”, etc.).

5. Response shapes (illustrative)
   5.1 /ranking/ (grouped per DA)
   {
   "scenario_id": 1,
   "computed_at": "2025-09-30T06:07:30Z",
   "results": [
   {
   "da": { "id": 1, "name": "Alpha", "lat": 12.97, "lon": 77.59, "radius_km": 50 },
   "top": [
   {
   "track_id": "T1",
   "score": 0.83,
   "components": { "cpa": 0.90, "tcpa": 0.72, "tdb": 0.64, "twrp": 0.91 }
   },
   {
   "track_id": "T2",
   "score": 0.61,
   "components": { "cpa": 0.70, "tcpa": 0.55, "tdb": 0.40, "twrp": 0.79 }
   }
   ]
   }
   ]
   }

Headers: ETag: "W/\"a1b2c3...\""

5.2 /score/ (flat rows, suitable for “Details”)
{
"scenario_id": 1,
"da_id": 1,
"page": 1,
"results": [
{
"track_id": "T1",
"computed_at": "2025-09-30T06:07:30Z",
"metrics": {
"cpa_m": 1234.5,
"tcpa_s": 67.8, // may be negative in history; contribution already 0 when negative
"tdb_s": 90.2,
"twrp_s": 12.0 // or "inf" if no release opportunity
},
"normalized": { "cpa": 0.82, "tcpa": 0.61, "tdb": 0.34, "twrp": 0.74 },
"weights": { "cpa": 0.25, "tcpa": 0.25, "tdb": 0.25, "twrp": 0.25 },
"score": 0.656,
"params": { "clamp_0_1": true }
}
]
}

Exact field names can vary slightly by build, but you will receive: a) score, b) components or normalized, c) raw metric values, d) computed_at.

6. Angular integration (practical code)
   6.1 Types
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
metrics: { cpa_m: number; tcpa_s: number; tdb_s: number; twrp_s: number | "inf" };
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

6.2 ETag polling helper
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

6.3 Angular service (RxJS)
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { interval, switchMap, startWith, map, distinctUntilChanged } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class TewaService {
private etag?: string;

constructor(private http: HttpClient) {}

pollRanking$(scenarioId: number, topN = 10, daId?: number, ms = 5000) {
const params: any = { scenario_id: scenarioId, top_n: topN };
if (daId) params.da_id = daId;

    return interval(ms).pipe(
      startWith(0),
      switchMap(() => this.http.get<RankingResponse>('/api/tewa/ranking/', {
        params, observe: 'response', headers: this.etag ? new HttpHeaders({ 'If-None-Match': this.etag }) : undefined
      })),
      map(resp => {
        if (resp.status === 200) this.etag = resp.headers.get('ETag') ?? undefined;
        return resp.body!;
      }),
      distinctUntilChanged((a, b) => a?.computed_at === b?.computed_at) // skip if not changed
    );

}

getScoreRows$(scenarioId: number, daId?: number, page = 1) {
const params: any = { scenario_id: scenarioId, page };
if (daId) params.da_id = daId;
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

getModelParams$(scenarioId: number) {
return this.http.get('/api/tewa/modelparams/', { params: { scenario_id: scenarioId } });
}

listDAs$() { return this.http.get('/api/tewa/da/'); }
}

6.4 Rendering hints (Angular template)

<!-- Per-DA section -->
<section *ngFor="let group of ranking?.results">
  <h3>{{ group.da.name }} ({{ ranking?.computed_at | date:'short':'UTC' }})</h3>
  <div *ngFor="let row of group.top" class="threat-card" [class.critical]="row.score >= 0.8">
    <div class="header">
      <span class="track">Track {{ row.track_id }}</span>
      <span class="score">{{ row.score | number:'1.2-2' }}</span>
    </div>
    <div class="bars">
      <app-bar label="CPA"  [value]="row.components.cpa"></app-bar>
      <app-bar label="TCPA" [value]="row.components.tcpa"></app-bar>
      <app-bar label="TDB"  [value]="row.components.tdb"></app-bar>
      <app-bar label="TWRP" [value]="row.components.twrp"></app-bar>
    </div>
  </div>
</section>

7. Time & timezone handling

Always send UTC (e.g., new Date().toISOString() which ends with Z).

The backend emits UTC (...Z).

If you show local time, label the timezone in the UI and keep UTC in API calls.

8. Error handling (DRF style)

400 (validation): show detail or the first key’s error message.

404 (not found): “Scenario/DA/Track not found.”

409 (duplicate on ingest): show row count and the first few errors[] entries.

422 (semantic): example “time outside scenario window.” Explain and keep the current board visible.

5xx: show a non-blocking toast; keep last known ranking.

For uploads, render all errors[] with row numbers if present.

9. Performance & polling

Poll /ranking/ every 5–10s with ETag; skip re-render on 304.

Don’t over-poll /score/; fetch on demand (e.g., when a user opens a details drawer).

Use virtualized lists for large DA groups.

Memoize color bands and bar widths to avoid layout thrash.

10. Security, CORS, throttling

Dev is open. In prod, JWT is planned (SimpleJWT). Your code should centralize auth headers in an HttpInterceptor so you can turn it on without large diffs.

CORS may be restricted in prod; keep all API calls behind a single base URL (e.g., /api/tewa/).

11. QA checklist (copy/paste)

UTC in/out: all requests with ISO Z.

Ranking sorted: score desc, track_id asc.

Explain panel: shows normalized bars and raw metric tooltips.

Negative TCPA: indicates “Past CPA”; contribution 0.

No TWRP: shows “No release opportunity”; contribution 0.

ETag polling: 304 respected; UI doesn’t flicker.

Errors: DRF messages surfaced; uploads show all errors[].

Accessibility: bars have text values and ARIA labels.

Responsiveness: cards wrap at ~600px; scores readable.

12. Glossary

DA (Defended Asset): thing we protect; circle with radius_km around lat/lon.

Track: moving object with time-stamped samples.

CPA/TCPA: distance/time to closest approach.

TDB: time/distance to DA boundary cross.

TWRP: time to weapon-release ring (DA radius + weapon range).

Normalized component: 0–1 “urgency” for a metric; higher is worse.

Clamping: final score limited to 0–1 (default true).

ETag: server’s version tag for a response; enables cheap “not changed” checks.

13. Example flows

Manual Recompute Button

Click “Recompute now” → POST /compute_now/.

On success, immediately fetch /ranking/ (ignore ETag the first time).

Resume ETag polling thereafter.

What-if at Time T

Pick ISO-UTC time → POST /compute_at/ with {method:"linear"}.

Fetch /ranking/ and re-render; allow switching back to “live” (current compute time).

Explain Row

User clicks track in board → fetch /score/?scenario_id=1&da_id=X.

Filter the returned rows for track_id, pick latest computed_at.

Display the row’s metrics, normalized, weights, score.
