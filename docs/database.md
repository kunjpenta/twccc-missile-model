TEWA Backend Database Management Guide

Project: Tactical Threat Evaluation & Weapon Assignment (TEWA)
Prepared for: Database Manager
Prepared by: [Your Name]
Date: [Current Date]

1. Overview

The TEWA backend is built using Django and PostgreSQL as the database. It handles data related to:

Defended Assets (DA): Targets being protected (e.g., airbases, infrastructure).

Aircraft/Threat Tracks: Real-time positions and movements of targets.

Track Samples: Snapshots of track data over time.

Computed Threat Scores: Evaluation of threat levels for tracks in relation to DAs.

Scenario Definitions: Context for tracking, including time frames and parameters.

Normalization & Scoring Parameters: Used for threat evaluation and calculation.

Key features of the system include:

Periodic computation of threat scores via Celery tasks.

Manual computation triggers via APIs and UI.

Ranking and scoring of threats based on predefined metrics.

2. Database Structure

The TEWA system uses the following key tables:

2.1 Core Tables
Table Purpose Key Columns Constraints
tewa*defendedasset Stores defended assets (DAs) id (PK), name, lat, lon, radius_km, created_at, updated_at radius_km >= 0, unique name
tewa_scenario Stores simulation scenarios id (PK), name, start_time, end_time, notes, created_at, updated_at unique name
tewa_track Stores aircraft/threat tracks id (PK), scenario_id (FK), track_id, lat, lon, alt_m, speed_mps, heading_deg, created_at, updated_at unique scenario + track_id
tewa_tracksample Stores snapshots of track positions over time id (PK), track_id (FK), t (timestamp), lat, lon, alt_m, speed_mps, heading_deg unique track + timestamp
tewa_modelparams Stores normalization and weighting parameters id (PK), scenario_id (FK), w_cpa, w_tcpa, w_tdb, w_twrp, cpa_scale_km, tcpa_scale_s, tdb_scale_km, twrp_scale_s, clamp_0_1, created_at, updated_at w*_ in [0, 1], _\_scale > 0
tewa_threatscore Stores computed threat scores id (PK), scenario_id (FK), track_id (FK), da_id (FK), cpa_km, tcpa_s, tdb_km, twrp_s, score, computed_at unique scenario + track + da + computed_at, indexes on (scenario, da, computed_at)
2.2 Relationships

Scenario 1 → N Tracks

Track 1 → N TrackSamples

Scenario 1 → 1 ModelParams

Scenario 1 → N ThreatScores

Track 1 → N ThreatScores

DefendedAsset 1 → N ThreatScores

ER Diagram (simplified):

Scenario ──< Track ──< TrackSample
└─< ModelParams
└─< ThreatScore >── DefendedAsset

2.3 Key Indexes
Table Index Purpose
tewa_defendedasset tewa_defend_name_4f83f9_idx Search by name
tewa_scenario tewa_scenar_name_039e16_idx Search by scenario name
tewa_track tewa_track_scenari_a864d0_idx Find tracks per scenario quickly
tewa_track tewa_track_lat_d8954a_idx Spatial queries (lat/lon)
tewa_tracksample tewa_tracks_lat_2fbc59_idx Fast sample retrieval by location
tewa_threatscore tewa_threat_scenari_0cc5ee_idx Find threat scores per scenario/DA
tewa_threatscore tewa_threat_scenari_0277ed_idx Find threat scores per scenario/track 3. Data Workflow
3.1 Track Data Ingestion

Source: CSV upload or API.

Storage: Stored in Track and TrackSample.

3.2 Threat Computation

Process: Triggered via compute_scores_at_timestamp or the compute_threats management command.

Data: Computes CPA (Closest Point of Approach), TCPA (Time to Closest Point of Approach), TDB (Threat Distance to Boundary), TWRP (Threat Warning Response Time).

Normalization: Data normalized using ModelParams.

Storage: Results are stored in the ThreatScore table.

3.3 Ranking

Service: rank_threats ranks threats globally or per defended asset (DA).

Storage: Rankings are used for threat prioritization.

3.4 Periodic Execution

Task: The periodic_compute_threats task updates the ThreatScores table at regular intervals using Celery.

3.5 Manual Trigger

API: Manual compute trigger via /api/tewa/compute_now/ or UI button.

4. Constraints & Validations
   4.1 Data Integrity

Ensure that the created_at and updated_at fields are populated correctly using auto_now_add and auto_now to avoid errors.

4.2 Unique Constraints

Track: Must be unique per scenario + track_id.

TrackSample: Must be unique per track + timestamp.

ThreatScore: Must be unique per scenario + track + da + computed_at.

4.3 Weight and Scale Validation

Weights: All w\_\* values must be in the range [0,1].

Scales: All \*\_scale values must be greater than 0.

4.4 Timestamps

Timezone-aware UTC timestamps for computed_at, created_at, and updated_at.

5. Developer / DB Notes
   5.1 Scenario Changes

When adding a new scenario, remember to create corresponding ModelParams for normalization.

5.2 Threat Computation

Always trigger threat computations via Celery tasks or management commands to ensure computations are persisted correctly.

5.3 Scaling Considerations

ThreatScore table can grow large. Indexes ensure efficient retrieval for ranking and API calls.

Consider partitioning or pruning old scores if running simulations for extended periods.

5.4 Spatial Queries

Tracks and DefendedAssets use latitude and longitude stored in decimal degrees. If advanced geospatial queries are needed, consider enabling PostGIS.

5.5 Backups

Perform a full PostgreSQL backup after seeding tracks and scenarios.

For live threat computations, implement incremental backups daily.

6. Seed / Demo Data

To seed initial data for development, use the following commands:

Seed Demo Data:
python manage.py seed_demo

Load Fixture:
python manage.py loaddata tewa_seed

This will load demo data such as:

Scenario: Demo-Scenario

DefendedAssets: DA-Alpha (Delhi) and DA-Bravo (Jodhpur)

Tracks: T1, T2, T3

TrackSamples: Data points for the tracks

ModelParams: Default weights and scaling for the demo scenario.

7. APIs for DB Access / Verification
   Endpoint Method Purpose
   /api/tewa/compute_at/ POST Compute scores for a given timestamp (supports linear interpolation)
   /api/tewa/compute_now/ POST Trigger manual computation for a scenario
   /api/tewa/ranking/ GET Retrieve the top-N threat rankings, per DA or globally
8. Recommendations for DB Manager

Ensure indexes are maintained on ThreatScore and Track for optimal performance.

Regularly monitor the size of the ThreatScore table; consider archiving old computations if needed.

Ensure scenario integrity by maintaining corresponding ModelParams for each scenario.

Coordinate with developers on scheduling periodic Celery tasks to update the threat scores.

Consider enabling PostGIS for advanced spatial queries (e.g., for querying tracks or DAs based on proximity).

9. Conclusion

By following the guidelines for database management, including proper configuration, seeding, and maintaining data integrity, you can ensure that the TEWA system runs efficiently. Using best practices for indexing, performance monitoring, and backup strategies will also help manage growing data and ensure smooth operation of threat evaluation and weapon assignment processes.
