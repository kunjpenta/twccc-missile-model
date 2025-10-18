# tewa/admin.py
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import List, Optional, Tuple, cast

from django import forms
from django.contrib import admin
from django.core.exceptions import FieldDoesNotExist, ValidationError

from .models import (
    DefendedAsset,
    ModelParams,
    Scenario,
    ThreatScore,
    Track,
    TrackSample,
)

# ---------------------------------------------------------------------
# Optional imports (admin should not crash if custom forms are missing)
# ---------------------------------------------------------------------
try:
    from .forms import DefendedAssetForm  # optional nicer form for DA
except Exception:  # pragma: no cover - defensive fallback
    DefendedAssetForm = None  # type: ignore[assignment]


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def model_has_field(model, name: str) -> bool:
    """True if the ORM model defines a concrete field with this name."""
    try:
        model._meta.get_field(name)
        return True
    except FieldDoesNotExist:
        return False


# ---------------------------------------------------------------------
# Scenario
# ---------------------------------------------------------------------
@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")
    search_fields = ("name",)


# ---------------------------------------------------------------------
# Track
# ---------------------------------------------------------------------
@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ("track_id", "scenario", "lat", "lon",
                    "alt_m", "speed_mps", "heading_deg", "updated_at")
    search_fields = ("track_id", "scenario__name")
    list_filter = ("scenario",)
    list_select_related = ("scenario",)
    autocomplete_fields = ("scenario",)  # if Track.scenario is FK


# ---------------------------------------------------------------------
# TrackSample
# ---------------------------------------------------------------------
@admin.register(TrackSample)
class TrackSampleAdmin(admin.ModelAdmin):
    list_display = ("track", "t", "lat", "lon",
                    "alt_m", "speed_mps", "heading_deg")
    # keep both; “scenario via track” is useful
    list_filter = ("track", "track__scenario")
    date_hierarchy = "t"
    list_select_related = ("track", "track__scenario")
    autocomplete_fields = ("track",)
    ordering = ("-t",)


# ---------------------------------------------------------------------
# ThreatScore
# ---------------------------------------------------------------------
@admin.register(ThreatScore)
class ThreatScoreAdmin(admin.ModelAdmin):
    list_display = ("scenario", "track", "da", "score", "computed_at")
    list_filter = ("scenario", "da", "computed_at")
    search_fields = ("track__track_id", "da__name", "scenario__name")
    list_select_related = ("scenario", "track", "da")
    ordering = ("-computed_at",)


# ---------------------------------------------------------------------
# DefendedAsset
# ---------------------------------------------------------------------
@admin.register(DefendedAsset)
class DefendedAssetAdmin(admin.ModelAdmin):
    # Do not assign None to .form in the class body (type checkers expect type[BaseForm])
    list_display = ("id", "name", "lat", "lon",
                    "radius_km", "created_at", "updated_at")
    search_fields = ("name",)


# Assign the optional form only if present (keeps type-checkers happy)
if DefendedAssetForm is not None:
    # type: ignore[attr-defined]
    DefendedAssetAdmin.form = cast(type[forms.BaseForm], DefendedAssetForm)


# ---------------------------------------------------------------------
# ModelParams + Admin Form
# ---------------------------------------------------------------------
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

        # Sum-to-1 (Decimal-safe; human-friendly tolerance)
        TOL = Decimal("0.001")
        w_keys = ["w_cpa", "w_tcpa", "w_tdb", "w_twrp"]
        try:
            weights = [
                self.cleaned_data.get(k) if self.cleaned_data.get(
                    k) is not None else Decimal("0")
                for k in w_keys
            ]
            weights = [Decimal(str(w)) for w in weights]
            s = sum(weights)
            if abs(s - Decimal("1.0")) > TOL:
                raise ValidationError("Weights must sum to 1.0 (±0.001).")
        except (InvalidOperation, TypeError):
            raise ValidationError("Weights must be numeric and sum to 1.0.")

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

        dyn: List[str] = base[:]
        dyn += [f for f in new_fields if model_has_field(ModelParams, f)]
        dyn += [f for f in legacy_fields if model_has_field(ModelParams, f)]

        # Common metadata if present
        for meta in ("updated_by", "updated_at", "created_at"):
            if model_has_field(ModelParams, meta):
                dyn.append(meta)
        return tuple(dyn)

    # Fieldsets adaptively include fields that exist on the model
    def get_fieldsets(self, request, obj=None):
        # list[tuple[Optional[str], dict[str, tuple[str, ...]]]]
        fs: List[Tuple[Optional[str], dict[str, Tuple[str, ...]]]] = []

        # Group 1: Scenario
        fs.append((None, {"fields": ("scenario",)}))

        # Group 2: Weights
        fs.append(("Weights (sum = 1)", {"fields": (
            "w_cpa", "w_tcpa", "w_tdb", "w_twrp")}))

        # Group 3: Ranges / Tick (Task-23)
        rng = tuple([f for f in ("R_W_m", "R_DA_m", "tick_s")
                    if model_has_field(ModelParams, f)])
        if rng:
            fs.append(("Ranges & Timing", {"fields": rng}))

        # Group 4: Sigmas (Task-23)
        sig = tuple([f for f in ("sigma_cpa", "sigma_tcpa", "sigma_tdb",
                    "sigma_twrp") if model_has_field(ModelParams, f)])
        if sig:
            fs.append(("Sigmas (optional)", {"fields": sig}))

        # Group 5: Legacy scaling (if still present)
        legacy = tuple(
            [f for f in ("cpa_scale_km", "tcpa_scale_s", "tdb_scale_km", "twrp_scale_s", "clamp_0_1")
             if model_has_field(ModelParams, f)]
        )
        if legacy:
            fs.append(("Legacy Scaling", {"fields": legacy}))

        # Group 6: Meta
        meta = tuple([f for f in ("updated_by", "updated_at",
                     "created_at") if model_has_field(ModelParams, f)])
        if meta:
            fs.append(("Meta", {"fields": meta}))

        return fs

    # Make scenario read-only after creation; keep meta read-only if present
    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj:
            ro.append("scenario")
        for meta in ("updated_at", "created_at"):
            if model_has_field(ModelParams, meta) and meta not in ro:
                ro.append(meta)
        return tuple(ro)

    # Optional: stamp updated_by if model supports it
    def save_model(self, request, obj, form, change):
        if model_has_field(ModelParams, "updated_by") and getattr(request, "user", None) and request.user.is_authenticated:
            try:
                setattr(obj, "updated_by", request.user)
            except Exception:
                pass
        super().save_model(request, obj, form, change)
