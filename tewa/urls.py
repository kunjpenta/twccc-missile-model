# tewa/urls.py


from django.urls import path
from django.urls import include, path

from . import views
from .views import upload_tracks_form

app_name = 'tewa'

urlpatterns = [
    path('', views.home, name='home'),
    path('upload_tracks/', views.upload_tracks, name='upload_tracks'),
    path('scenarios/', views.list_scenarios, name='list_scenarios'),
    path('compute_now/', views.compute_now, name='compute_now'),
    path('scenario/<int:scenario_id>/',
         views.scenario_detail, name='scenario_detail'),
    path('scenario/<int:scenario_id>/compute_now/',
         views.compute_now_scenario, name='compute_now_scenario'),

    # DA CRUD
    path('das/', views.da_list, name='da_list'),
    path('das/create/', views.da_create, name='da_create'),
    path('das/<int:da_id>/edit/', views.da_edit, name='da_edit'),
    path('das/<int:da_id>/delete/', views.da_delete, name='da_delete'),

    # API
    path('api/', include('tewa.api.urls')),
    path('upload_tracks_form/', upload_tracks_form, name='upload_tracks_form'),
    path('tracks/<str:track_id>/', views.track_detail, name='track_detail'),
    path('tracks/', views.tracks_list, name='tracks_list'),


]


app_name = "tewa"

urlpatterns = [
    path('threat_board/', views.threat_board, name='threat_board'),
    # existing endpoints...
]
