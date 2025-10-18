# core/views_docs.py
from django.views.generic import TemplateView

# If you kept files under templates/docs/
DOC_PREFIX = "docs/"
# If you moved to templates/pages/docs/, flip the line above to:
# DOC_PREFIX = "pages/docs/"


class DocsIndexView(TemplateView):
    template_name = DOC_PREFIX + "index.html"


class DocsFrontendView(TemplateView):
    template_name = DOC_PREFIX + "frontend.html"


class DocsBackendView(TemplateView):
    template_name = DOC_PREFIX + "backend.html"


class DocsDatabaseView(TemplateView):
    template_name = DOC_PREFIX + "database.html"
