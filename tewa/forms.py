# tewa/forms.py
from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError

from tewa.models import DefendedAsset, ModelParams


# ------------------------------
# Defended Asset Form
# ------------------------------
class DefendedAssetForm(forms.ModelForm):
    class Meta:
        model = DefendedAsset
        fields = ["name", "lat", "lon", "radius_km"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter DA name"}),
            "lat": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001", "placeholder": "Latitude"}),
            "lon": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001", "placeholder": "Longitude"}),
            "radius_km": forms.NumberInput(attrs={"class": "form-control", "step": "0.1", "placeholder": "Radius in km"}),
        }

    def clean_radius_km(self):
        radius = self.cleaned_data.get("radius_km")
        if radius is None:
            raise ValidationError("Radius is required.")
        if radius <= 0 or radius > 1000:
            raise ValidationError("Radius must be between 0 and 1000 km.")
        return radius

    def clean_lat(self):
        lat = self.cleaned_data.get("lat")
        if lat is None:
            raise ValidationError("Latitude is required.")
        if lat < -90 or lat > 90:
            raise ValidationError(
                "Latitude must be between -90 and 90 degrees.")
        return lat

    def clean_lon(self):
        lon = self.cleaned_data.get("lon")
        if lon is None:
            raise ValidationError("Longitude is required.")
        if lon < -180 or lon > 180:
            raise ValidationError(
                "Longitude must be between -180 and 180 degrees.")
        return lon


# ------------------------------
# Track Upload Form
# ------------------------------
class UploadTrackForm(forms.Form):
    file = forms.FileField(required=True)
    scenario_id = forms.IntegerField(required=False)


# ------------------------------
# Scenario Parameters Form
# ------------------------------
class ScenarioParamsForm(forms.ModelForm):
    class Meta:
        model = ModelParams
        fields = [
            "R_W_m", "R_DA_m", "tick_s",
            "w_cpa", "w_tcpa", "w_tdb", "w_twrp",
            "sigma_cpa", "sigma_tcpa", "sigma_tdb", "sigma_twrp",
        ]
        widgets = {
            "R_W_m": forms.NumberInput(attrs={"min": 1, "step": 1}),
            "R_DA_m": forms.NumberInput(attrs={"min": 0, "step": 1}),
            "tick_s": forms.NumberInput(attrs={"min": 0.000001, "step": "any"}),
            "w_cpa": forms.NumberInput(attrs={"min": 0, "max": 1, "step": 0.01}),
            "w_tcpa": forms.NumberInput(attrs={"min": 0, "max": 1, "step": 0.01}),
            "w_tdb": forms.NumberInput(attrs={"min": 0, "max": 1, "step": 0.01}),
            "w_twrp": forms.NumberInput(attrs={"min": 0, "max": 1, "step": 0.01}),
            "sigma_cpa": forms.NumberInput(attrs={"min": 0, "step": "any"}),
            "sigma_tcpa": forms.NumberInput(attrs={"min": 0, "step": "any"}),
            "sigma_tdb": forms.NumberInput(attrs={"min": 0, "step": "any"}),
            "sigma_twrp": forms.NumberInput(attrs={"min": 0, "step": "any"}),
        }

    def clean(self):
        data = super().clean()

        # --- Weights sanity ---
        def f(x): return float(x) if x is not None else 0.0
        wsum = f(data.get("w_cpa")) + f(data.get("w_tcpa")) + \
            f(data.get("w_tdb")) + f(data.get("w_twrp"))
        if abs(wsum - 1.0) > 1e-6:
            raise forms.ValidationError("Weights must sum to 1.0")

        # --- Tick rate ---
        tick = data.get("tick_s")
        if tick is None or tick <= 0:
            self.add_error("tick_s", "Tick rate must be greater than 0")

        # --- Range consistency ---
        R_W, R_DA = data.get("R_W_m"), data.get("R_DA_m")
        if R_W is not None and R_DA is not None and R_DA >= R_W:
            self.add_error(
                "R_DA_m", "R_DA_m must be positive and less than R_W_m")

        return data
