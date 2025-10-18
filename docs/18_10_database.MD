TEWA Backend Database Management Guide

Project: Tactical Threat Evaluation & Weapon Assignment (TEWA)
Prepared for: Database Manager
Prepared by: [Your Name]
Date: 2025-10-18
Stack: Django (DRF) + PostgreSQL (recommended ≥ 14), optional PostGIS (≥ 3.2)

1) Purpose & Scope

This guide explains how TEWA stores, indexes, and maintains data for:

Defended Assets (DAs) — protected sites.

Tracks & Track Samples — moving targets and their time-series states.

Threat Scores — per (Scenario × DA × Track) computations.

Scenarios & Model Parameters — context and doctrine (weights/scales).

You’ll find:

Canonical table shapes, constraints, and indexes.

Data-flow (ingest → compute → rank).

Retention/partitioning strategies for large time-series.

Backup/restore, integrity, and performance playbooks.

Safe migration patterns for production.

2) Schema (canonical)

Notes:
• All timestamps are UTC (timestamptz).
• Distances in km unless noted; altitudes in meters; speeds in m/s.
• Use double precision for computed/geo metrics that require floating-point.

2.1 Core Tables
tewa_defendedasset

Columns:
id (PK, serial/bigserial), name (text, unique),
lat (double precision, −90..90), lon (double precision, −180..180),
radius_km (double precision, ≥ 0),
created_at (timestamptz, default now()), updated_at (timestamptz).

Checks:
lat BETWEEN -90 AND 90, lon BETWEEN -180 AND 180, radius_km >= 0.

Indexes:
UNIQUE(name), optional functional index on lower(name) for case-insensitive lookup.

tewa_scenario

Columns:
id (PK), name (text, unique),
start_time (timestamptz), end_time (timestamptz NULLABLE),
notes (text NULLABLE), created_at, updated_at.

Checks:
end_time IS NULL OR end_time >= start_time.

tewa_track

Columns:
id (PK), scenario_id (FK → scenario ON DELETE CASCADE),
track_id (text) — external identifier scoped to scenario,
latest (denormalized view of current state):
lat, lon, alt_m (double/int), speed_mps (double), heading_deg (double, 0..360],
created_at, updated_at.

Constraints:
UNIQUE (scenario_id, track_id); heading_deg BETWEEN 0 AND 360.

Indexes:
(scenario_id); partial (scenario_id) WHERE updated_at > now() - interval '1 day' can help live ops.

tewa_tracksample (time-series)

Columns:
id (PK), track_id (FK → track ON DELETE CASCADE),
t (timestamptz, sample time),
lat, lon, alt_m, speed_mps, heading_deg,
created_at.

Constraints:
UNIQUE (track_id, t), same checks for lat/lon/heading as above.

Indexes (important):
(track_id, t DESC) for “latest sample” per track,
BRIN on (t) for range scans (historical queries),
Optional partial on recent: (track_id, t DESC) WHERE t > now() - interval '7 days'.

tewa_modelparams (per-scenario doctrine)

Columns:
id (PK), scenario_id (FK → scenario UNIQUE),
Weights: w_cpa, w_tcpa, w_tdb, w_twrp (double 0..1),
Scales: cpa_scale_km, tcpa_scale_s, tdb_scale_km, twrp_scale_s (double > 0),
clamp_0_1 (boolean, default true),
created_at, updated_at.

Constraints:
Each weight BETWEEN 0 AND 1; each scale > 0; UNIQUE (scenario_id).

tewa_threatscore (computed results; high write volume)

Columns:
id (PK),
scenario_id (FK → scenario ON DELETE CASCADE),
track_id (FK → track ON DELETE CASCADE),
da_id (FK → defendedasset ON DELETE CASCADE),
Components (raw):
cpa_km (double NULLABLE), tcpa_s (double NULLABLE, non-negative),
tdb_km (double NULLABLE), twrp_s (double NULLABLE; NULL = no opportunity),
Result: score (double NOT NULL),
computed_at (timestamptz NOT NULL),
created_at (timestamptz default now()).

Constraints:
CHECK (tcpa_s IS NULL OR tcpa_s >= 0), CHECK (cpa_km IS NULL OR cpa_km >= 0),
UNIQUE (scenario_id, track_id, da_id, computed_at).

Indexes (critical):
(1) (scenario_id, da_id, computed_at DESC) — latest by DA,
(2) (scenario_id, track_id, computed_at DESC) — latest by Track,
(3) BRIN on (computed_at) — time-range scans,
(4) Optional covering index INCLUDE (score) for ranking queries.

Infinity policy: we do not store +inf in DB. Use NULL for “no TWRP opportunity” and let the API map to inf when requested.

3) Relationships (summary)

Scenario 1→N Tracks

Track 1→N TrackSamples

Scenario 1→1 ModelParams

Scenario 1→N ThreatScores

Track 1→N ThreatScores

DefendedAsset 1→N ThreatScores

Simplified ER:

Scenario ──< Track ──< TrackSample
   └─< ModelParams
   └─< ThreatScore >── DefendedAsset
                 ^
                 └──────── Track

4) Data Flow
4.1 Ingestion

CSV/API → tewa_track (create if missing) + tewa_tracksample (append).

Use UNIQUE (track_id, t) to dedupe accidental double-loads.

4.2 Compute

Triggered by:

POST /api/tewa/compute_now/ (latest state)

POST /api/tewa/compute_at/ (time-slice; interpolation)

Mgmt command compute_threats (batch/CLI)

Celery periodic task.

Scoring writes a row per (Scenario, DA, Track, computed_at) into tewa_threatscore.
Unique constraint guarantees idempotency for same inputs.

4.3 Ranking

Read path queries “latest per pair” or “top-N per DA”.

Consider materialized view (see §9.4) for low-latency “latest” queries.

4.4 Periodic Execution (Celery)

Task schedule updates ThreatScores at fixed cadence (e.g., 1–10 s).

Ensure batches commit frequently (see §8.2) and respect unique keys.

5) Constraints & Validation

Temporal: all timestamps timestamptz (UTC); application enforces UTC I/O.

Geo: lat/lon range checks; heading 0–360 (inclusive of 0, exclusive of >360).

Uniqueness:

track: (scenario_id, track_id),

tracksample: (track_id, t),

threatscore: (scenario_id, track_id, da_id, computed_at),

modelparams: (scenario_id).

Semantics:

tcpa_s >= 0 (negatives are zeroed at compute time),

twrp_s NULL = “no opportunity”.

6) Indexing Strategy (practical)
Table	Index	Why
tewa_track	(scenario_id, track_id) UNIQUE	Identity & joins
	(scenario_id)	Batch compute prefilter
tewa_tracksample	(track_id, t DESC)	Latest sample lookup
	BRIN (t)	Large history scans
tewa_threatscore	(scenario_id, da_id, computed_at DESC)	Ranking by DA
	(scenario_id, track_id, computed_at DESC)	Explain latest per track
	BRIN (computed_at)	Time windows
	INCLUDE (score)	Cover ranking SELECTs

For big tables, add indexes CONCURRENTLY (see §10.2).

7) Capacity Planning & Retention
7.1 Cardinalities (rules of thumb)

Tracks: 10³–10⁴ per scenario; samples at 1–5 Hz → millions/day.

ThreatScores: cadence × DAs × Tracks → also millions/day.

7.2 Retention tiers

Hot: last 24–72 hours in base tables (fast queries).

Warm: last 30–90 days in partitions, queried occasionally.

Cold/archive: >90 days offloaded (S3/Glacier/another DB).

7.3 Partitioning (recommended)

tewa_threatscore — RANGE partition by month on computed_at.

tewa_tracksample — RANGE partition by day or week on t.

Benefits: vacuum locality, fast DROP of old data, BRIN effectiveness, faster backups.

See §9.1 for DDL patterns.

8) Write Path & Concurrency
8.1 Idempotency

Unique (scenario_id, track_id, da_id, computed_at) prevents dupes from retried jobs.

8.2 Batching & Transactions

Batch inserts in 5k–20k rows per transaction for ThreatScores.

Keep transactions < 2–5 seconds to play nicely with autovacuum and reduce bloat.

8.3 Locking

Mostly INSERT-only. Avoid VACUUM FULL in business hours.

For heavy index maintenance, use CONCURRENTLY operations.

9) Advanced DBA Patterns
9.1 Native Partitioning (PostgreSQL)

ThreatScore (monthly):

-- Parent
CREATE TABLE tewa_threatscore (
  id BIGSERIAL PRIMARY KEY,
  scenario_id BIGINT NOT NULL REFERENCES tewa_scenario(id) ON DELETE CASCADE,
  track_id BIGINT NOT NULL REFERENCES tewa_track(id) ON DELETE CASCADE,
  da_id BIGINT NOT NULL REFERENCES tewa_defendedasset(id) ON DELETE CASCADE,
  cpa_km DOUBLE PRECISION,
  tcpa_s DOUBLE PRECISION CHECK (tcpa_s IS NULL OR tcpa_s >= 0),
  tdb_km DOUBLE PRECISION,
  twrp_s DOUBLE PRECISION,
  score DOUBLE PRECISION NOT NULL,
  computed_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (scenario_id, track_id, da_id, computed_at)
) PARTITION BY RANGE (computed_at);

-- One partition (October 2025)
CREATE TABLE tewa_threatscore_2025_10
  PARTITION OF tewa_threatscore
  FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

-- Repeat monthly. Automate with a cron/Celery beat job.


Indexes on parent (Postgres applies them to partitions if created on each child or via template in newer versions):

CREATE INDEX ON tewa_threatscore_2025_10 (scenario_id, da_id, computed_at DESC);
CREATE INDEX ON tewa_threatscore_2025_10 (scenario_id, track_id, computed_at DESC);
CREATE INDEX ON tewa_threatscore_2025_10 USING BRIN (computed_at);


Django doesn’t manage partitions natively; use RunSQL migrations or a separate DDL script. Keep model metadata aligned with the parent table.

9.2 BRIN Tuning

Set pages_per_range based on table size (e.g., 16–64).

Reindex BRIN after massive drops to keep it tight.

9.3 PostGIS (optional but useful)

If you need spatial queries:

SELECT PostGIS_Full_Version(); -- ensure installed

-- Columns:
-- defendedasset.geom geometry(Point, 4326)
-- track/ tracksample.geom geometry(Point, 4326)

CREATE INDEX tewa_da_geom_gix ON tewa_defendedasset USING GIST (geom);
CREATE INDEX tewa_tracksample_geom_gix ON tewa_tracksample USING GIST (geom);


Populate geom with ST_SetSRID(ST_MakePoint(lon, lat), 4326) and use ST_DWithin for proximity.

9.4 Materialized View for “Latest Score”
CREATE MATERIALIZED VIEW tewa_latest_threatscore AS
SELECT DISTINCT ON (scenario_id, da_id, track_id)
  scenario_id, da_id, track_id, score, computed_at,
  cpa_km, tcpa_s, tdb_km, twrp_s
FROM tewa_threatscore
ORDER BY scenario_id, da_id, track_id, computed_at DESC;

CREATE UNIQUE INDEX tewa_latest_threatscore_uniq
  ON tewa_latest_threatscore (scenario_id, da_id, track_id);

-- Refresh after compute cycles (non-blocking):
REFRESH MATERIALIZED VIEW CONCURRENTLY tewa_latest_threatscore;


Automate refresh with Celery beat. The API can read from this MV for low-latency ranking.

10) Migrations & Maintenance
10.1 Django Migrations (safety)

Adding NOT NULL columns: add as NULL first, backfill, then set NOT NULL in a second migration.

Long-running backfills: do in batches with custom RunPython and sleep() between chunks.

10.2 Concurrent Index Ops

Use Postgres-specific ops in migrations to avoid table locks:

django.contrib.postgres.operations.AddIndexConcurrently

…RemoveIndexConcurrently

Example:

from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models

class Migration(migrations.Migration):
    operations = [
        AddIndexConcurrently(
            model_name='threatscore',
            index=models.Index(
                name='ts_scen_da_comp_desc',
                fields=['scenario_id', 'da_id', 'computed_at'],
            ),
        ),
    ]

10.3 VACUUM/ANALYZE

Ensure autovacuum is on. For heavy inserts:

Lower autovacuum_vacuum_scale_factor (e.g., 0.1) on the largest tables.

Run ANALYZE after bulk loads.

Use VACUUM (VERBOSE, ANALYZE) tewa_threatscore_*; off-peak.

Avoid VACUUM FULL unless reclaiming space post-purge (it’s blocking).

10.4 Repacking

Use pg_repack for bloat without long locks (plan downtime if not available).

11) Backup, Restore, and PITR
11.1 Logical backups

Nightly:

pg_dump -Fc -d tewa_db -f /backups/tewa_$(date -u +%F).dump


Restore:

createdb tewa_restore
pg_restore -d tewa_restore --no-owner --no-privileges /backups/tewa_2025-10-18.dump

11.2 PITR (Point-in-Time)

Enable WAL archiving (archive_mode=on, archive_command=...).

Take weekly full base backups + keep WALs for retention window.

Test restores quarterly.

11.3 Fixtures (dev only)
python manage.py loaddata tewa_seed
python manage.py seed_demo

12) Security & Roles

Roles:

tewa_app (least privilege: CRUD on app tables only)

tewa_readonly (SELECT)

tewa_admin (DDL)

Network: limit DB access to app subnets; TLS if cross-AZ/region.

Audit: consider pgaudit for privileged ops.

RL S (optional): if multi-tenant scenarios are introduced.

13) Monitoring & Observability

Enable pg_stat_statements and track top queries:

SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 20;


Table growth:

SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 20;


Index usage:

SELECT relname, idx_scan, seq_scan
FROM pg_stat_user_tables
ORDER BY (seq_scan - idx_scan) DESC
LIMIT 20;


Autovacuum activity:

SELECT relname, last_vacuum, last_autovacuum, vacuum_count, autovacuum_count
FROM pg_stat_user_tables
ORDER BY last_autovacuum NULLS LAST
LIMIT 50;

14) Data Integrity & Quality Checks

Foreign keys with ON DELETE CASCADE prevent orphans.

Daily checks:

Tracks with no samples in last X minutes.

ThreatScores without a matching Track/DA (shouldn’t happen; indicates FK disabled).

Stale ModelParams (missing for a new Scenario).

Example:

SELECT t.id, t.track_id
FROM tewa_track t
LEFT JOIN tewa_tracksample s ON s.track_id = t.id AND s.t > now() - interval '5 minutes'
WHERE s.id IS NULL;

15) API Endpoints (DB-relevant)

POST /api/tewa/compute_now/ — writes ThreatScore rows for latest states.

POST /api/tewa/compute_at/ — time-slice compute; persists.

GET /api/tewa/ranking/ — often hits “latest” per pair; optimize with MV (§9.4).

GET /api/tewa/score/ — paginated historical reads; ensure (scenario_id, da_id/track_id, computed_at) indexes.

16) Playbooks
16.1 Create next month’s partition (cron monthly)
-- Example for November 2025
CREATE TABLE IF NOT EXISTS tewa_threatscore_2025_11
  PARTITION OF tewa_threatscore
  FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE INDEX ON tewa_threatscore_2025_11 (scenario_id, da_id, computed_at DESC);
CREATE INDEX ON tewa_threatscore_2025_11 (scenario_id, track_id, computed_at DESC);
CREATE INDEX ON tewa_threatscore_2025_11 USING BRIN (computed_at);

16.2 Drop partitions older than retention
DROP TABLE IF EXISTS tewa_threatscore_2025_06; -- safe & instant metadata operation

16.3 Refresh “latest” MV after compute
REFRESH MATERIALIZED VIEW CONCURRENTLY tewa_latest_threatscore;

16.4 Rebuild BRIN after major purge
REINDEX INDEX tewa_threatscore_2025_10_computed_at_brin;

17) Seed / Demo Data (dev)

python manage.py seed_demo — creates:

Scenario: Demo-Scenario

DAs: DA-Alpha (Delhi), DA-Bravo (Jodhpur)

Tracks: T1, T2, T3 with samples

ModelParams with default weights/scales

python manage.py loaddata tewa_seed — loads fixture set.

18) Common Questions (DBA FAQ)

Q: Why NULL for twrp_s instead of +inf?
A: Infinity complicates comparisons and indexes. NULL is clean and the API presents “∞”.

Q: Why both BRIN and btree indexes on ThreatScore?
A: BRIN serves large time-range scans; btree serves “latest per entity” lookups.

Q: Can we store geometry?
A: Yes (PostGIS). Keep numeric lat/lon for simplicity; add geom columns for spatial ops.

Q: How to avoid table bloat?
A: Partitioning + tuned autovacuum + repack during maintenance.

Q: Safe way to change weights/scales?
A: Update tewa_modelparams; recompute as needed. No schema change required.

19) Recommendations (actionable)

Enable partitioning for tewa_threatscore (monthly) and tewa_tracksample (daily/weekly).

Create the indexes listed in §6 for your expected read patterns.

Adopt MV for latest scores and refresh after compute cycles.

Tune autovacuum for large partitions; monitor with pg_stat_user_tables.

Establish retention: e.g., keep 90 days hot/warm; archive older.

Backups + PITR: nightly dumps + WAL archiving; test restores quarterly.

Use concurrent index migrations to avoid downtime.

Grant least privilege roles to the app; separate admin/DDL roles.

Consider PostGIS if proximity/containment queries expand.

Document units & ranges (this doc) and enforce with CHECKs.

20) Conclusion

With the constraints, indexes, and maintenance routines above, TEWA’s PostgreSQL layer remains:

Correct (FKs, CHECKs, unique keys),

Fast (btree for “latest”, BRIN for history, MV for ranking),

Scalable (native partitioning, batched inserts), and

Operable (autovacuum tuned, backups, PITR, observability).
