# tewa/tests/test_templates_pages.py

from django.urls import reverse


def test_home_page(client, db):
    r = client.get(reverse("home"))
    assert r.status_code == 200
    assert b"Scenarios" in r.content


def test_scenario_detail_page(client, db, seeded_scenario_with_scores):
    sid = seeded_scenario_with_scores["scenario"].id
    r = client.get(reverse("scenario_detail", args=[sid]))
    assert r.status_code == 200


def test_assumptions_page(client, db, seeded_scenario_with_scores):
    sid = seeded_scenario_with_scores["scenario"].id
    r = client.get(reverse("scenario_assumptions", args=[sid]))
    assert r.status_code == 200
