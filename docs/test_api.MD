# TEWA API — What Each Endpoint Does

**Base URL (dev):** `http://127.0.0.1:8000/api/tewa/`

**Format:** JSON in, JSON out. Send `Content-Type: application/json` for POSTs.

**Time format:** UTC ISO‑8601 with `Z` (e.g., `2025-10-14T07:39:03Z`).

**Auth:** Not required in your local dev setup.

> ⚠️ Trailing slashes matter on some routes below (noted per endpoint).

---

## 1) API Root

**GET** `/`
Returns API name and a quick list of available endpoints.

**Example**

```bash
curl -s http://127.0.0.1:8000/api/tewa/
```

---

## 2) Core resources (CRUD via DRF viewsets)

These follow typical DRF patterns: `GET list`, `POST create`, `GET /{id}/` retrieve, `PUT/PATCH` update, `DELETE` delete.

### a) Scenarios

**GET** `/scenario/` (trailing slash)

### b) Defended Assets (DA)

**GET** `/da/`

### c) Tracks

**GET** `/track/`

### d) Track Samples

**GET** `/tracksample/`

### e) Threat Scores

**GET** `/threatscore/`

> Tip: List responses often include helpful fields like `track_public_id` and `da_name` to guide parameters you’ll pass to compute/analytics routes.

---

## 3) Compute & analytics endpoints

### a) Compute _now_

Triggers scoring with the current data snapshot.

**POST** `/compute_now/` _(trailing slash)_

**Body**

```json
{
  "scenario_id": 1,
  "method": "linear"
}
```

**Sample result**

```json
{
  "status": "ok",
  "scenario_id": 1,
  "method": "linear",
  "computed_at": "2025-10-14T07:38:38.621737Z",
  "batch_id": null
}
```

### b) Compute _at_ a specific time

Computes scores for a given timestamp.

**POST** `/compute_at` _(no trailing slash)_

**Body**

```json
{
  "scenario_id": 1,
  "when": "2025-10-14T00:00:00Z",
  "method": "linear"
}
```

**Sample result (abridged)**

```json
{
  "status": "ok",
  "scenario_id": 1,
  "when": "2025-10-14T00:00:00Z",
  "method": "linear",
  "count": 12,
  "scores": [ {"track_id": "T2", "da_id": 3, "score": 0.2564, ...}, ... ],
  "threats": [ ... ],
  "batch_id": null
}
```

### c) Ranking (top threats per DA)

Groups latest scores by DA and returns the top N (per DA).

**GET** `/ranking/` _(trailing slash)_

**Query params**

- `scenario_id` (int, **required**)
- `top_n` (int, optional; default shows several)

**Example**

```bash
curl -sG "http://127.0.0.1:8000/api/tewa/ranking/" \
  --data-urlencode "scenario_id=1" \
  --data-urlencode "top_n=5"
```

### d) Score breakdown (latest score(s))

Returns the **latest** `ThreatScore` either for a specific track vs DA, or all latest scores for a DA across tracks.

**GET** `/score-breakdown` _(no trailing slash)_

**Use 1 — Single track vs DA**

- **Query params:** `scenario_id` (int), `da_id` (int), `track_id` (**string** public ID like `T2`/`ABC123`)

**Example**

```bash
curl -sG "http://127.0.0.1:8000/api/tewa/score-breakdown" \
  --data-urlencode "scenario_id=1" \
  --data-urlencode "da_id=3" \
  --data-urlencode "track_id=T2"
```

**Use 2 — All latest scores for a DA**

- **Query params:** `scenario_id` (int), `da_id` (int)
- Returns `{ results: [...], count: N }`

**Example**

```bash
curl -sG "http://127.0.0.1:8000/api/tewa/score-breakdown" \
  --data-urlencode "scenario_id=1" \
  --data-urlencode "da_id=3"
```

### e) Track detail (with attached scores)

Fetches a track (by its **public** `track_id`) and appends its related scores (DA name, score, computed_at).

**GET** `/tracks/detail/` _(trailing slash)_

**Query params**

- `scenario_id` (int, **required**)
- `track_id` (**string** public ID, **required**)

**Example**

```bash
curl -sG "http://127.0.0.1:8000/api/tewa/tracks/detail/" \
  --data-urlencode "scenario_id=1" \
  --data-urlencode "track_id=T2"
```

### f) Upload tracks

Accepts files (e.g., CSV) of track data.

**POST** `/upload_tracks/` _(trailing slash)_

**Headers**: `Content-Type: multipart/form-data`

**Form fields (typical)**

- `file`: the data file
- optional metadata fields depending on your importer

> A `GET` here will 405 (method not allowed).

### g) Recalculate scores (batch helper)

Triggers a batch recalculation (implementation-specific).

**POST** `/calculate_scores/` _(trailing slash)_

**Body (typical)**

```json
{
  "scenario_id": 1,
  "method": "linear"
}
```

> A `GET` here will 405 (method not allowed).

---

## 4) Notes on identifiers

- **`track_id` (string)** in read/lookup endpoints like `score-breakdown` (single-track mode) and `tracks/detail/` refers to the **public** track identifier (e.g., `"T2"`, `"ABC123"`).
- **Track/DA IDs (integers)** in compute POST endpoints (`compute_now`, `compute_at`, `calculate_scores`) refer to the **database primary keys** when sent inside nested objects; otherwise you pass `scenario_id` as plain int.

---

## 5) Common responses & errors

- `400 Bad Request` — missing or invalid parameters (e.g., calling `ranking/` without `scenario_id`).
- `405 Method Not Allowed` — wrong HTTP verb (e.g., `GET` on `upload_tracks/`).
- `404 Not Found` — no matching data (e.g., unknown track for given scenario).

---

## 6) Handy cURL cheat‑sheet

```bash
# API root
curl -s http://127.0.0.1:8000/api/tewa/

# ThreatScore list
curl -s http://127.0.0.1:8000/api/tewa/threatscore/

# Latest score for (scenario=1, DA=3, track=T2)
curl -sG "http://127.0.0.1:8000/api/tewa/score-breakdown" \
  --data-urlencode "scenario_id=1" \
  --data-urlencode "da_id=3" \
  --data-urlencode "track_id=T2"

# All latest scores for DA=3 in scenario=1
curl -sG "http://127.0.0.1:8000/api/tewa/score-breakdown" \
  --data-urlencode "scenario_id=1" \
  --data-urlencode "da_id=3"

# Ranking (top 5 per DA)
curl -sG "http://127.0.0.1:8000/api/tewa/ranking/" \
  --data-urlencode "scenario_id=1" \
  --data-urlencode "top_n=5"

# Compute now
curl -s -X POST http://127.0.0.1:8000/api/tewa/compute_now/ \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": 1, "method":"linear"}'

# Compute at a specific time
curl -s -X POST http://127.0.0.1:8000/api/tewa/compute_at \
  -H "Content-Type: application/json" \
  -d '{"scenario_id":1,"when":"2025-10-14T00:00:00Z","method":"linear"}'
```

---

## 7) Quick reference table

| Method | Path                 | Purpose                                        |
| ------ | -------------------- | ---------------------------------------------- |
| GET    | `/`                  | API root + endpoint list                       |
| GET    | `/scenario/`         | List scenarios                                 |
| GET    | `/da/`               | List defended assets                           |
| GET    | `/track/`            | List tracks                                    |
| GET    | `/tracksample/`      | List track samples                             |
| GET    | `/threatscore/`      | List threat scores                             |
| POST   | `/compute_now/`      | Compute scores using current data              |
| POST   | `/compute_at`        | Compute scores at a specific timestamp         |
| GET    | `/ranking/`          | Top N threats per DA (requires `scenario_id`)  |
| GET    | `/score-breakdown`   | Latest score(s): by DA (+ optional `track_id`) |
| GET    | `/tracks/detail/`    | Track details by public `track_id` + scores    |
| POST   | `/upload_tracks/`    | Upload track data file                         |
| POST   | `/calculate_scores/` | Batch recalculation helper                     |

---

If you want this exported to a README or PDF, say the word and I’ll format & generate it.
