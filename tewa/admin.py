# tewa/admin.py

from django import forms
from django.contrib import admin

from tewa.forms import DefendedAssetForm

from .models import (
    DefendedAsset,
    ModelParams,
    Scenario,
    ThreatScore,
    Track,
    TrackSample,
)


# Register Scenario in the Admin
@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at", "updated_at"]
    search_fields = ["name"]

# Register Track in the Admin


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ("track_id", "scenario", "lat", "lon",
                    "alt_m", "speed_mps", "heading_deg", "updated_at")
    search_fields = ("track_id", "scenario__name")
    list_filter = ("scenario",)

# Register TrackSample in the Admin


@admin.register(TrackSample)
class TrackSampleAdmin(admin.ModelAdmin):
    list_display = ("track", "t", "lat", "lon",
                    "alt_m", "speed_mps", "heading_deg")
    list_filter = ("track__scenario", "track")
    date_hierarchy = "t"

# Register ThreatScore in the Admin


@admin.register(ThreatScore)
class ThreatScoreAdmin(admin.ModelAdmin):
    list_display = ("scenario", "track", "da", "score", "computed_at")
    list_filter = ("scenario", "da", "computed_at")
    search_fields = ("track__track_id", "da__name", "scenario__name")

# Register DefendedAsset in the Admin


@admin.register(DefendedAsset)
class DefendedAssetAdmin(admin.ModelAdmin):
    form = DefendedAssetForm
    list_display = ['name', 'lat', 'lon',
                    'radius_km', 'created_at', 'updated_at']
    search_fields = ['name']

# ModelParams Form with custom validation


class ModelParamsForm(forms.ModelForm):
    class Meta:
        model = ModelParams
        fields = '__all__'

    def clean_w_cpa(self):
        value = self.cleaned_data.get('w_cpa')
        if value < 0 or value > 1:
            raise forms.ValidationError(
                "Weight for CPA must be between 0 and 1.")
        return value

    def clean_w_tcpa(self):
        value = self.cleaned_data.get('w_tcpa')
        if value < 0 or value > 1:
            raise forms.ValidationError(
                "Weight for TCPA must be between 0 and 1.")
        return value

    def clean_w_tdb(self):
        value = self.cleaned_data.get('w_tdb')
        if value < 0 or value > 1:
            raise forms.ValidationError(
                "Weight for TDB must be between 0 and 1.")
        return value

    def clean_w_twrp(self):
        value = self.cleaned_data.get('w_twrp')
        if value < 0 or value > 1:
            raise forms.ValidationError(
                "Weight for TWRP must be between 0 and 1.")
        return value


# Register ModelParams in the Admin
@admin.register(ModelParams)
class ModelParamsAdmin(admin.ModelAdmin):
    form = ModelParamsForm  # Use custom form for validation

    list_display = (
        "scenario", "w_cpa", "w_tcpa", "w_tdb", "w_twrp",
        "cpa_scale_km", "tcpa_scale_s", "tdb_scale_km", "twrp_scale_s", "clamp_0_1"
    )

    search_fields = ("scenario__name",)
    list_filter = ("scenario",)

    fieldsets = (
        (None, {
            'fields': ('scenario',)
        }),
        ('Weights', {
            'fields': ('w_cpa', 'w_tcpa', 'w_tdb', 'w_twrp')
        }),
        ('Scaling Factors', {
            'fields': ('cpa_scale_km', 'tcpa_scale_s', 'tdb_scale_km', 'twrp_scale_s')
        }),
        ('Other Settings', {
            'fields': ('clamp_0_1',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('scenario',)
        return super().get_readonly_fields(request, obj)
