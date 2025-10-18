# core/urls_docs.py
from django.urls import path

from .views_docs import (
    DocsBackendView,
    DocsDatabaseView,
    DocsFrontendView,
    DocsIndexView,
)

app_name = "docs"

urlpatterns = [
    path("", DocsIndexView.as_view(), name="index"),
    path("frontend/", DocsFrontendView.as_view(), name="frontend"),
    path("backend/", DocsBackendView.as_view(), name="backend"),
    path("database/", DocsDatabaseView.as_view(), name="database"),
]
