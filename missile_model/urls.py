# missile_model/urls.py

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    # Home & TEWA app
    path('', include('tewa.urls', namespace='tewa')),

    # Admin
    path('admin/', admin.site.urls),

    # API root & health
    path('api/', lambda r: JsonResponse({"ok": True}), name='api_root'),

    # Redirects
    path('api', RedirectView.as_view(url='/api/', permanent=False)),
    path('api/tewa/', include('tewa.urls', namespace='tewa')),

]
