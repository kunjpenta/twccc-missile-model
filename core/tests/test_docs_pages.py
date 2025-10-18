# core/tests/test_docs_pages.py
import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_docs_pages_ok(client):
    for name in ("core:docs-index", "core:docs-frontend", "core:docs-backend", "core:docs-database"):
        resp = client.get(reverse(name))
        assert resp.status_code == 200
