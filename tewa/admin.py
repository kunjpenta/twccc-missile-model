# tewa/admin.py
from __future__ import annotations

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import (
    DefendedAsset,
    ModelParams,
    Scenario,
    ThreatScore,
    Track,
    TrackSample,
)

# Try to use the nicer DefendedAssetForm if present (won't hard-crash admin if it's not)
try:
    from .forms import DefendedAssetForm  # optional
except Exception:
    DefendedAssetForm = None  # type: ignore


# ---------- Scenario ----------
@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")
    search_fields = ("name",)


# ---------- Track ----------
@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = (
        "track_id", "scenario", "lat", "lon",
        "alt_m", "speed_mps", "heading_deg", "updated_at",
    )
    search_fields = ("track_id", "scenario__name")
    list_filter = ("scenario",)


# ---------- TrackSample ----------
@admin.register(TrackSample)
class TrackSampleAdmin(admin.ModelAdmin):
    list_display = ("track", "t", "lat", "lon",
                    "alt_m", "speed_mps", "heading_deg")
    list_filter = ("track__scenario", "track")
    date_hierarchy = "t"


# ---------- ThreatScore ----------
@admin.register(ThreatScore)
class ThreatScoreAdmin(admin.ModelAdmin):
    list_display = ("scenario", "track", "da", "score", "computed_at")
    list_filter = ("scenario", "da", "computed_at")
    search_fields = ("track__track_id", "da__name", "scenario__name")


# ---------- DefendedAsset ----------
@admin.register(DefendedAsset)
class DefendedAssetAdmin(admin.ModelAdmin):
    form = DefendedAssetForm if DefendedAssetForm else None
    list_display = ("id", "name", "lat", "lon",
                    "radius_km", "created_at", "updated_at")
    search_fields = ("name",)


# ---------- ModelParams ----------
class ModelParamsForm(forms.ModelForm):
    class Meta:
        model = ModelParams
        fields = "__all__"

    # Per-field clamps (0..1)
    def _clamp01(self, name: str):
        val = self.cleaned_data.get(name)
        if val is None:
            return val
        if not (0 <= val <= 1):
            raise ValidationError(
                f"Weight for {name} must be between 0 and 1.")
        return val

    def clean_w_cpa(self):
        return self._clamp01("w_cpa")

    def clean_w_tcpa(self):
        return self._clamp01("w_tcpa")

    def clean_w_tdb(self):
        return self._clamp01("w_tdb")

    def clean_w_twrp(self):
        return self._clamp01("w_twrp")

    def clean(self):
        data = super().clean()

        # Sum-to-1 for weights (if present)
        w_keys = ["w_cpa", "w_tcpa", "w_tdb", "w_twrp"]
        if all(k in self.cleaned_data for k in w_keys):
            wsum = sum(float(self.cleaned_data.get(k) or 0.0) for k in w_keys)
            if abs(wsum - 1.0) > 1e-6:
                raise ValidationError("Weights must sum to 1.0")

        # Task-23 fields (if present on model): tick_s > 0, R_DA_m < R_W_m
        tick = self.cleaned_data.get("tick_s", None)
        if tick is not None and tick <= 0:
            self.add_error("tick_s", "Tick rate must be > 0")

        rw = self.cleaned_data.get("R_W_m", None)
        rda = self.cleaned_data.get("R_DA_m", None)
        if rw is not None and rda is not None and rda >= rw:
            self.add_error(
                "R_DA_m", "DA radius should be smaller than weapon range")

        return data


@admin.register(ModelParams)
class ModelParamsAdmin(admin.ModelAdmin):
    form = ModelParamsForm

    # Dynamically pick the right list_display based on available fields
    def get_list_display(self, request):
        base = ["scenario", "w_cpa", "w_tcpa", "w_tdb", "w_twrp"]

        # New Task-23 fields
        new_fields = ["R_W_m", "R_DA_m", "tick_s", "sigma_cpa",
                      "sigma_tcpa", "sigma_tdb", "sigma_twrp"]
        # Legacy scale fields (keep if your model still has them)
        legacy_fields = ["cpa_scale_km", "tcpa_scale_s",
                         "tdb_scale_km", "twrp_scale_s", "clamp_0_1"]

        def have(attr: str) -> bool:
            return hasattr(ModelParams, attr)

        dyn = base[:]
        dyn += [f for f in new_fields if have(f)]
        dyn += [f for f in legacy_fields if have(f)]
        # Common metadata if present
        for meta in ("updated_by", "updated_at", "created_at"):
            if have(meta):
                dyn.append(meta)
        return tuple(dyn)

    # Fieldsets adaptively include fields that exist on the model
    def get_fieldsets(self, request, obj=None):
        def have(attr: str) -> bool:
            return hasattr(ModelParams, attr)

        # Group 1: Scenario
        fs = [(None, {"fields": ("scenario",)})]

        # Group 2: Weights
        fs.append(("Weights (sum = 1)", {"fields": (
            "w_cpa", "w_tcpa", "w_tdb", "w_twrp")}))

        # Group 3: Ranges / Tick (Task-23)
        rng = [f for f in ("R_W_m", "R_DA_m", "tick_s") if have(f)]
        if rng:
            fs.append(("Ranges & Timing", {"fields": tuple(rng)}))

        # Group 4: Sigmas (Task-23)
        sig = [f for f in ("sigma_cpa", "sigma_tcpa",
                           "sigma_tdb", "sigma_twrp") if have(f)]
        if sig:
            fs.append(("Sigmas (optional)", {"fields": tuple(sig)}))

        # Group 5: Legacy scaling (if still present)
        legacy = [f for f in ("cpa_scale_km", "tcpa_scale_s",
                              "tdb_scale_km", "twrp_scale_s", "clamp_0_1") if have(f)]
        if legacy:
            fs.append(("Legacy Scaling", {"fields": tuple(legacy)}))

        # Group 6: Meta
        meta = [f for f in ("updated_by", "updated_at",
                            "created_at") if have(f)]
        if meta:
            fs.append(("Meta", {"fields": tuple(meta)}))

        return fs

    # Make scenario read-only after creation
    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj:
            ro.append("scenario")
        # meta fields (if present) are typically read-only from admin
        for meta in ("updated_at", "created_at"):
            if hasattr(ModelParams, meta) and meta not in ro:
                ro.append(meta)
        return tuple(ro)
