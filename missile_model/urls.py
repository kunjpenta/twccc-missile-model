# missile_model/urls.py


from django.contrib import admin
from django.http import HttpResponse, JsonResponse
from django.urls import include, path


def home(_request): return HttpResponse("Home")
def health(_request): return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/tewa/", include("tewa.api.urls")),  # API
    path("", include("tewa.urls")),               # HTML pages
    path("health/", health, name="health"),
    path("accounts/", include("django.contrib.auth.urls")),

]
