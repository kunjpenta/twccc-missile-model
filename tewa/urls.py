# tewa/urls.py  — HTML routes only

# tewa/urls.py — HTML routes only
from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import TemplateView

from . import views
from .views import scenario_assumptions_view

app_name = "tewa"

urlpatterns = [
     
    path("", views.home, name="home"),
    path("about/", TemplateView.as_view(template_name="about.html"), name="about"),
    path("contact/", TemplateView.as_view(template_name="contact.html"), name="contact"),

    # Auth
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    path("scenarios/<int:scenario_id>/",
         views.scenario_detail, name="scenario_detail"),
    path("scenarios/<int:scenario_id>/compute-now/",
         views.compute_now_scenario, name="compute_now_scenario"),

    path("da/", views.da_list, name="da_list"),
    path("da/create/", views.da_create, name="da_create"),
    path("da/<int:da_id>/edit/", views.da_edit, name="da_edit"),
    path("da/<int:da_id>/delete/", views.da_delete, name="da_delete"),

    path("upload-tracks/", views.upload_tracks_form, name="upload_tracks_form"),
    path("tracks/browser/", views.track_browser_page, name="track_browser_page"),

    path("score_breakdown/<int:scenario_id>/<int:da_id>/<int:track_id>/",
         views.score_breakdown_page, name="score_breakdown_page"),

    path("scenarios/<int:scenario_id>/assumptions/",
         scenario_assumptions_view, name="scenario_assumptions"),


]
