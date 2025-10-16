missile_model/
├─ manage.py
├─ requirements.txt
├─ missile_db.sql
├─ pytest.ini
├─ docs/
├─ htmlcov/
├─ output/
├─ missile_model/ # project package
│ ├─ **init**.py
│ ├─ asgi.py
│ ├─ wsgi.py
│ ├─ celery.py
│ ├─ settings.py
│ ├─ urls.py
│ └─ static/
│ └─ favicon.ico
├─ core/ # common utilities + low-level tests
│ ├─ **init**.py
│ ├─ admin.py
│ ├─ apps.py
│ ├─ constants.py
│ ├─ dtos.py
│ ├─ enums.py
│ ├─ init.py
│ ├─ models.py
│ ├─ typing.py
│ ├─ urls.py
│ ├─ views.py
│ ├─ migrations/
│ ├─ utils/
│ │ ├─ **init**.py
│ │ ├─ geodesy.py
│ │ ├─ units.py
│ │ └─ utils.py
│ └─ tests/
│ ├─ **init**.py
│ ├─ quick_check.py
│ ├─ test_kinematics.py
│ ├─ test_scoring.py
│ ├─ test_tewa_kinematics.py
│ └─ test_units_geodesy.py
├─ templates/ # HTML/CSS-only UI (server-rendered)
│ ├─ base.html
│ ├─ home.html
│ ├─ about.html
│ ├─ contact.html
│ ├─ create_da.html
│ ├─ da_form.html
│ ├─ da_list.html
│ ├─ da_confirm_delete.html
│ ├─ ranking.html
│ ├─ scenario_detail.html # (root-level convenience template)
│ ├─ threat_board.html
│ ├─ track_browser.html
│ ├─ upload_tracks.html
│ ├─ debug/
│ ├─ boards/
│ │ └─ da_board.html
│ ├─ components/
│ │ ├─ score_breakdown.html
│ │ └─ boards/
│ ├─ registration/
│ │ └─ login.html
│ └─ scenarios/
│ ├─ detail.html
│ └─ assumptions.html
└─ tewa/ # TEWA app (models, services, API, views)
├─ **init**.py
├─ admin.py
├─ apps.py
├─ forms.py
├─ models.py # DefendedAsset, Scenario, Track, TrackSample, ThreatScore, ModelParams
├─ serializers.py
├─ tasks.py
├─ types.py
├─ urls.py # HTML routes (namespaced: tewa)
├─ utils.py
├─ views.py # HTML views
├─ templates/
│ ├─ score_breakdown.html
│ └─ track_browser.html
├─ fixtures/
│ └─ tewa_seed.json
├─ management/
│ ├─ **init**.py
│ └─ commands/
│ ├─ **init**.py
│ ├─ compute_threats.py
│ ├─ import_tracks.py
│ └─ seed_demo.py
├─ migrations/
│ ├─ **init**.py
│ ├─ 0001_initial.py
│ ├─ 0002_modelparams_scenario_tracksample_and_more.py
│ ├─ 0003_alter_modelparams_options.py
│ ├─ 0004_alter_scenario_options_and_more.py
│ ├─ 0005_scenario_end_time_scenario_notes_scenario_start_time.py
│ ├─ 0006_alter_modelparams_options_and_more.py
│ ├─ 0007_remove_defendedasset_da_radius_nonneg_and_more.py
│ ├─ 0008_modelparams_created_at_modelparams_updated_at.py
│ ├─ 0009_alter_defendedasset_id_alter_scenario_id.py
│ ├─ 0010_da_scenario_nullable.py
│ └─ 0011_alter_defendedasset_scenario.py
├─ services/ # computation, ranking, exports, charts
│ ├─ **init**.py
│ ├─ csv_import.py
│ ├─ export_csv.py
│ ├─ engine.py
│ ├─ kinematics.py
│ ├─ normalize.py
│ ├─ ranking.py
│ ├─ sampling.py
│ ├─ scoring.py
│ ├─ score_breakdown.py
│ ├─ score_breakdown_service.py
│ ├─ score_history.py
│ ├─ charting.py
│ ├─ serializers.py
│ └─ threat_compute.py
├─ api/ # REST API (namespaced: tewa_api)
│ ├─ **init**.py
│ ├─ query_schemas.py
│ ├─ serializers.py
│ ├─ urls.py # includes /ping, score-breakdown, charts PNG, export CSV, ranking, etc.
│ ├─ view_utils.py
│ ├─ views.py # score_breakdown, score_history_png_view, export CSV, scenario params
│ ├─ views_compute.py # compute_now, compute_at, ranking, upload_tracks
│ └─ views_read.py # DRF viewsets: Scenario/DA/Track/TrackSample/ThreatScore, simple reads
└─ tests/ # app-level tests
├─ **init**.py
├─ conftest.py
├─ test_api_compute_at.py
├─ test_api_scenario_params.py
├─ test_charts.py
├─ test_compute_multiple_scenarios.py
├─ test_compute_threats.py
├─ test_csv_import.py
├─ test_da_creation.py
├─ test_export_csv.py
├─ test_models.py
├─ test_models_more.py
├─ test_ranking.py
├─ test_score_breakdown_api.py
└─ test_templates_pages.py
